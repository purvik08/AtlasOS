"""Unified API Service for Atlas OS Dashboard.

Provides high-performance, non-blocking asynchronous communication with the
AtlasOS backend via AtlasSDK. Real data only — single source of truth with CLI.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from PySide6.QtCore import Property, QObject, QThread, QTimer, Signal, Slot

from atlas.api.sdk import AtlasSDK
from atlas.ui.dashboard.models import (
    ChatSession,
    ModelRegistry,
    ProviderHealth,
    ProviderStatus,
    SystemInfo,
)

logger = logging.getLogger(__name__)


class _WorkerRequest:
    """Represents a queued async request for the worker thread."""

    def __init__(
        self,
        coro_factory: Callable[[], Awaitable[Any]],
        result_signal: Signal | None = None,
        error_signal: Signal | None = None,
    ) -> None:
        self.coro_factory = coro_factory
        self.result_signal = result_signal
        self.error_signal = error_signal


class ApiWorker(QThread):
    """Dedicated background worker thread for non-blocking Atlas SDK operations."""

    data_ready = Signal(object)
    error_occurred = Signal(str)
    chat_message_sent = Signal(object)
    session_created = Signal(object)
    model_load_result = Signal(str, bool, str)
    model_unload_result = Signal(str, bool, str)
    model_download_result = Signal(str, bool, str)
    model_delete_result = Signal(str, bool, str)
    streaming_chunk = Signal(str)
    streaming_finished = Signal()
    wifi_scan_results = Signal(list)
    wifi_connect_result = Signal(str, bool, str)
    voice_status_ready = Signal(object)
    memories_ready = Signal(list)
    memory_added_signal = Signal(dict)
    memory_deleted_signal = Signal(str)
    plugins_ready = Signal(list)

    def __init__(self, sdk: AtlasSDK) -> None:
        super().__init__()
        self.sdk = sdk
        self._running = True
        self._request_queue: deque[_WorkerRequest] = deque()
        self._cancel_streaming = False

    def enqueue(self, request: _WorkerRequest) -> None:
        """Add an operation to the request queue."""
        self._request_queue.append(request)

    def cancel_current_stream(self) -> None:
        """Cancel ongoing stream."""
        self._cancel_streaming = True

    def run(self) -> None:
        """Run the async event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_loop())
        finally:
            loop.close()

    async def _run_loop(self) -> None:
        """Process API fetch and incoming requests."""
        while self._running:
            try:
                await self._process_queue()
            except Exception as exc:
                logger.error("ApiWorker error: %s", exc)
                self.error_occurred.emit(str(exc))
            await asyncio.sleep(0.05)

    async def _process_queue(self) -> None:
        """Drain queued async requests."""
        while self._request_queue and self._running:
            request = self._request_queue.popleft()
            try:
                result = await request.coro_factory()
                if request.result_signal:
                    request.result_signal.emit(result)
            except Exception as exc:
                err_msg = str(exc)
                logger.warning("API request failed: %s", err_msg)
                if request.error_signal:
                    request.error_signal.emit(err_msg)
                else:
                    self.error_occurred.emit(err_msg)

    async def fetch_all_data(self) -> None:
        """Fetch system info, model registry, providers, chat sessions, and memories."""
        try:
            # 1. System Info
            sys_info = await SystemInfo.fetch(self.sdk)
            self.data_ready.emit(("system", sys_info))
        except Exception as e:
            logger.debug("SystemInfo fetch skipped: %s", e)

        try:
            # 2. Model Registry
            model_reg = await ModelRegistry.fetch(self.sdk)
            self.data_ready.emit(("models", model_reg))
        except Exception as e:
            logger.debug("ModelRegistry fetch skipped: %s", e)

        try:
            # 3. Providers Health
            provider_list = await self.sdk.list_providers()
            if provider_list:
                results: list[ProviderHealth] = []
                for p in provider_list:
                    name = p.get("name", "")
                    if name:
                        try:
                            health = await ProviderHealth.fetch(self.sdk, name)
                            results.append(health)
                        except Exception as p_err:
                            results.append(ProviderHealth(
                                name=name,
                                status=ProviderStatus.UNHEALTHY,
                                last_check=datetime.now(),
                                error=str(p_err),
                            ))
                self.data_ready.emit(("providers", results))
        except Exception as e:
            logger.debug("Providers fetch skipped: %s", e)

        try:
            # 4. Chat Sessions
            sessions = await ChatSession.fetch_all(self.sdk)
            self.data_ready.emit(("sessions", sessions))
        except Exception as e:
            logger.debug("Sessions fetch skipped: %s", e)

        try:
            # 5. Persistent Memories
            mem_res = await self.sdk.list_memories()
            if mem_res and "entries" in mem_res:
                self.data_ready.emit(("memories", mem_res["entries"]))
        except Exception as e:
            logger.debug("Memories fetch skipped: %s", e)

        try:
            network_status = await self.sdk.network_status()
            self.data_ready.emit(("network", network_status))
        except Exception as e:
            logger.debug("Network status fetch skipped: %s", e)

        try:
            voice_status = await self.sdk.voice_status()
            self.data_ready.emit(("voice", voice_status))
        except Exception as e:
            logger.debug("Voice status fetch skipped: %s", e)

        try:
            voice_devices = await self.sdk.voice_devices()
            self.data_ready.emit(("voice_devices", voice_devices))
        except Exception as e:
            logger.debug("Voice devices fetch skipped: %s", e)

        try:
            plugins = await self.sdk.list_plugins()
            self.plugins_ready.emit(plugins.get("plugins", []))
        except Exception as e:
            logger.debug("Plugins fetch skipped: %s", e)

    async def _stream_chat(
        self, session_id: str, model: str, message: str, provider: str = ""
    ) -> None:
        """Stream real-time tokens from backend AI."""
        self._cancel_streaming = False
        try:
            async for chunk in self.sdk.stream_chat(
                model=model,
                messages=[{"role": "user", "content": message}],
                session_id=session_id or None,
            ):
                if self._cancel_streaming:
                    break
                if "choices" in chunk and chunk["choices"]:
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        self.streaming_chunk.emit(content)
        except Exception as exc:
            self.error_occurred.emit(f"Streaming error: {exc}")
        finally:
            self.streaming_finished.emit()


class ApiService(QObject):
    """Main API service exposed to QML — manages backend data communication."""

    # QML Signals
    system_info_changed = Signal(object)
    model_registry_changed = Signal(object)
    providers_changed = Signal(list)
    sessions_changed = Signal(list)
    error_occurred = Signal(str)
    connection_status_changed = Signal(bool)
    session_messages_fetched = Signal(list)
    chat_message_received = Signal(object)
    session_created_signal = Signal(object)
    model_operation_result = Signal(str, bool, str)
    model_download_completed = Signal(str, bool, str)
    model_delete_completed = Signal(str, bool, str)
    streaming_chunk = Signal(str)
    streaming_finished = Signal()
    wifi_scan_completed = Signal(list)
    wifi_connect_completed = Signal(str, bool, str)
    voice_status_changed = Signal(object)
    voice_devices_ready = Signal(dict)
    speak_completed = Signal(bool, str)
    memories_changed = Signal(list)
    memory_added_signal = Signal(dict)
    memory_deleted_signal = Signal(str)
    plugins_changed = Signal(list)
    network_status_changed = Signal(dict)
    voice_devices_changed = Signal(dict)

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._base_url = base_url
        self._api_key = api_key
        self._sdk = AtlasSDK(base_url=base_url, api_key=api_key)
        self._worker = ApiWorker(self._sdk)
        self._connected = False

        # Connect worker signals
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.chat_message_sent.connect(self._on_chat_message_sent)
        self._worker.session_created.connect(self._on_session_created)
        self._worker.model_load_result.connect(self.model_operation_result)
        self._worker.model_unload_result.connect(self.model_operation_result)
        self._worker.model_download_result.connect(self.model_download_completed)
        self._worker.model_delete_result.connect(self.model_delete_completed)
        self._worker.streaming_chunk.connect(self.streaming_chunk)
        self._worker.streaming_finished.connect(self.streaming_finished)
        self._worker.wifi_scan_results.connect(self.wifi_scan_completed)
        self._worker.wifi_connect_result.connect(self.wifi_connect_completed)
        self._worker.voice_status_ready.connect(self.voice_status_changed)
        self._worker.voice_status_ready.connect(self._on_voice_status_changed)
        self._worker.memories_ready.connect(self.memories_changed)
        self._worker.memory_added_signal.connect(self.memory_added_signal)
        self._worker.memory_deleted_signal.connect(self.memory_deleted_signal)
        self._worker.plugins_ready.connect(self.plugins_changed)
        self._worker.plugins_ready.connect(self._on_plugins_changed)
        self._worker.start()

        # Periodic refresh timer (every 4 seconds)
        self._timer = QTimer(self)
        self._timer.setInterval(4000)
        self._timer.timeout.connect(self.refresh_all)

        # Data cache
        self._system_info: SystemInfo | None = None
        self._model_registry: ModelRegistry | None = None
        self._providers: list[ProviderHealth] = []
        self._sessions: list[ChatSession] = []
        self._session_messages: list[dict[str, Any]] = []
        self._network_status: dict[str, Any] = {}
        self._voice_status: dict[str, Any] = {}
        self._voice_devices: dict[str, Any] = {"inputs": [], "outputs": []}
        self._plugins: list[dict[str, Any]] = []

    @property
    def system_info(self) -> SystemInfo | None:
        return self._system_info

    @property
    def model_registry(self) -> ModelRegistry | None:
        return self._model_registry

    @property
    def providers(self) -> list[ProviderHealth]:
        return self._providers

    @property
    def sessions(self) -> list[ChatSession]:
        return self._sessions

    @Property("QVariantList", notify=providers_changed)
    def providerList(self) -> list[dict[str, Any]]:
        return [
            p.model_dump(mode="json") if hasattr(p, "model_dump") else dict(p)
            for p in self._providers
        ]

    @Property("QVariantList", notify=sessions_changed)
    def sessionList(self) -> list[dict[str, Any]]:
        return [
            s.model_dump(mode="json") if hasattr(s, "model_dump") else dict(s)
            for s in self._sessions
        ]

    @Property("QVariantMap", notify=network_status_changed)
    def networkStatus(self) -> dict[str, Any]:
        return self._network_status

    @Property("QVariantMap", notify=voice_status_changed)
    def voiceStatus(self) -> dict[str, Any]:
        return self._voice_status

    @Property("QVariantMap", notify=voice_devices_changed)
    def voiceDevices(self) -> dict[str, Any]:
        return self._voice_devices

    @Property("QVariantList", notify=plugins_changed)
    def pluginList(self) -> list[dict[str, Any]]:
        return self._plugins

    @property
    def session_messages(self) -> list[dict[str, Any]]:
        return self._session_messages

    @Property(bool, notify=connection_status_changed)
    def connected(self) -> bool:
        return self._connected

    @Property("QVariant", notify=system_info_changed)
    def systemInfo(self) -> Any:
        if self._system_info is None:
            return {}
        return self._system_info.model_dump(mode="json")

    # -----------------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------------

    @Slot()
    def refresh_all(self) -> None:
        """Trigger non-blocking fetch of all backend status."""
        if self._worker and self._worker.isRunning():
            req = _WorkerRequest(
                coro_factory=self._worker.fetch_all_data,
                result_signal=None,
                error_signal=self.error_occurred,
            )
            self._worker.enqueue(req)

    @Slot()
    def startAutoRefresh(self) -> None:
        self._timer.start()
        self.refresh_all()

    @Slot()
    def stopAutoRefresh(self) -> None:
        self._timer.stop()

    @Slot()
    def shutdown(self) -> None:
        self.stopAutoRefresh()
        if self._worker and self._worker.isRunning():
            self._worker._running = False
            self._worker.wait(1000)

    @Slot(str, str, str, str, result=bool)
    def stream_chat_message(
        self,
        session_id: str,
        model: str,
        message: str,
        provider: str = "",
    ) -> bool:
        """Send chat message with real-time token streaming."""
        if not self._worker or not self._worker.isRunning():
            self.error_occurred.emit("API service offline")
            return False

        async def do_stream():
            return await self._worker._stream_chat(session_id, model, message, provider)

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_stream,
            result_signal=None,
            error_signal=self.error_occurred,
        ))
        return True

    @Slot(result=bool)
    def cancel_streaming(self) -> bool:
        if not self._worker or not self._worker.isRunning():
            return False
        self._worker.cancel_current_stream()
        return True

    @Slot(str, str, str, str, result=bool)
    def send_chat_message(
        self,
        session_id: str,
        model: str,
        message: str,
        provider: str = "",
    ) -> bool:
        """Send non-streaming chat completion."""
        if not self._worker or not self._worker.isRunning():
            return False

        async def do_chat():
            return await self._sdk.chat(
                model=model,
                messages=[{"role": "user", "content": message}],
                session_id=session_id or None,
            )

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_chat,
            result_signal=self.chat_message_received,
            error_signal=self.error_occurred,
        ))
        return True

    @Slot(str)
    def fetch_session_messages(self, session_id: str) -> None:
        """Fetch chat message history for a session."""
        if not session_id:
            return

        async def do_fetch():
            res = await self._sdk.get_session(session_id)
            return res.get("messages", [])

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_fetch,
            result_signal=self.session_messages_fetched,
            error_signal=self.error_occurred,
        ))

    @Slot(str, str, result=bool)
    def create_session(self, provider: str, model: str) -> bool:
        """Create a new chat session."""
        async def do_create():
            return await self._sdk.create_session(
                provider=provider or None,
                model=model or None,
            )

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_create,
            result_signal=self.session_created_signal,
            error_signal=self.error_occurred,
        ))
        return True

    @Slot(str, result=bool)
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        async def do_delete():
            return await self._sdk.delete_session(session_id)

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_delete,
            result_signal=self.sessions_changed,
            error_signal=self.error_occurred,
        ))
        return True

    @Slot(str, result=bool)
    def load_model(self, model_id: str) -> bool:
        """Load a model into memory."""
        async def do_load():
            res = await self._sdk.load_model(model_id)
            self.model_operation_result.emit(model_id, True, "Model loaded")
            self.refresh_all()
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_load,
            result_signal=None,
            error_signal=self.error_occurred,
        ))
        return True

    @Slot(str, result=bool)
    def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory."""
        async def do_unload():
            res = await self._sdk.unload_model(model_id)
            self.model_operation_result.emit(model_id, True, "Model unloaded")
            self.refresh_all()
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_unload,
            result_signal=None,
            error_signal=self.error_occurred,
        ))
        return True

    @Slot(str, str, str, str, str, bool)
    def download_model(
        self,
        model_id: str,
        url: str = "",
        repo: str = "",
        filename: str = "",
        token: str = "",
        overwrite: bool = False,
    ) -> None:
        """Download a model from HF repo or URL."""
        async def do_download():
            res = await self._sdk.download_model(
                model_id=model_id,
                url=url or None,
                repo=repo or None,
                filename=filename or None,
                token=token or None,
                overwrite=overwrite,
            )
            success = res.get("success", False)
            msg = (
                res.get("error", "Download complete")
                if not success
                else f"Downloaded to {res.get('path', '')}"
            )
            self.model_download_completed.emit(model_id, success, msg)
            self.refresh_all()
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_download,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    @Slot(str, bool)
    def delete_model(self, model_id: str, delete_file: bool = False) -> None:
        """Delete / unregister a model."""
        async def do_delete():
            res = await self._sdk.delete_model(model_id, delete_file=delete_file)
            self.model_delete_completed.emit(model_id, True, "Model removed")
            self.refresh_all()
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_delete,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    @Slot()
    def rescan_models(self) -> None:
        """Rescan models directory."""
        async def do_rescan():
            res = await self._sdk.scan_models()
            self.refresh_all()
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_rescan,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    # ------------------------------------------------------------------
    # Network Slots
    # ------------------------------------------------------------------
    @Slot(str)
    def scan_wifi(self, iface: str = "") -> None:
        """Scan for Wi-Fi networks."""
        async def do_scan():
            nets = await self._sdk.scan_wifi(iface or None)
            self._worker.wifi_scan_results.emit(nets)
            return nets

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_scan,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    @Slot(str, str, str)
    def connect_wifi(self, ssid: str, password: str = "", iface: str = "") -> None:
        """Connect to Wi-Fi network."""
        async def do_connect():
            res = await self._sdk.connect_wifi(ssid, password=password or None, iface=iface or None)
            success = res.get("success", False)
            msg = res.get("message", "")
            self._worker.wifi_connect_result.emit(ssid, success, msg)
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_connect,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    @Slot(str)
    def disconnect_wifi(self, iface: str = "") -> None:
        """Disconnect active Wi-Fi connection."""
        async def do_disconnect():
            res = await self._sdk.disconnect_wifi(iface or None)
            success = res.get("success", False)
            msg = res.get("message", "")
            self._worker.wifi_connect_result.emit("", success, msg)
            self.refresh_all()
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_disconnect,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    # ------------------------------------------------------------------
    # Memory Slots
    # ------------------------------------------------------------------
    @Slot()
    def fetch_memories(self) -> None:
        """Fetch all persistent memories."""
        async def do_fetch():
            res = await self._sdk.list_memories()
            entries = res.get("entries", [])
            self._worker.memories_ready.emit(entries)
            return entries

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_fetch,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    @Slot(str, str, str)
    def remember_memory(self, text: str, category: str = "general", source: str = "user") -> None:
        """Store a new memory."""
        async def do_remember():
            res = await self._sdk.remember_memory(text, category, source)
            self._worker.memory_added_signal.emit(res)
            # Resync memory list
            mems = await self._sdk.list_memories()
            self._worker.memories_ready.emit(mems.get("entries", []))
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_remember,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    @Slot(str)
    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory entry."""
        async def do_delete():
            res = await self._sdk.delete_memory(memory_id)
            self._worker.memory_deleted_signal.emit(memory_id)
            # Resync memory list
            mems = await self._sdk.list_memories()
            self._worker.memories_ready.emit(mems.get("entries", []))
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_delete,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    # ------------------------------------------------------------------
    # Voice Slots
    # ------------------------------------------------------------------
    @Slot()
    def fetch_voice_devices(self) -> None:
        """Fetch available microphone and speaker devices."""
        async def do_fetch():
            devs = await self._sdk.voice_devices()
            self._worker.voice_devices_ready.emit(devs)
            return devs

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_fetch,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    @Slot(str)
    def speak_text(self, text: str) -> None:
        """Synthesize and speak text via Piper TTS."""
        async def do_speak():
            res = await self._sdk.speak_text(text)
            ok = res.get("success", False)
            msg = res.get("message", "Speaking" if ok else "TTS unavailable")
            self._worker.speak_completed.emit(ok, msg)
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_speak,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    # ------------------------------------------------------------------
    # Plugin Slots
    # ------------------------------------------------------------------
    @Slot()
    def fetch_plugins(self) -> None:
        async def do_fetch():
            res = await self._sdk.list_plugins()
            plugins = res.get("plugins", [])
            self._worker.plugins_ready.emit(plugins)
            return plugins

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_fetch,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    @Slot(str)
    def enable_plugin(self, plugin_name: str) -> None:
        async def do_enable():
            res = await self._sdk.enable_plugin(plugin_name)
            self.refresh_all()
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_enable,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    @Slot(str)
    def disable_plugin(self, plugin_name: str) -> None:
        async def do_disable():
            res = await self._sdk.disable_plugin(plugin_name)
            self.refresh_all()
            return res

        self._worker.enqueue(_WorkerRequest(
            coro_factory=do_disable,
            result_signal=None,
            error_signal=self.error_occurred,
        ))

    # -----------------------------------------------------------------------
    # Signal handlers
    # -----------------------------------------------------------------------

    def _on_data_ready(self, data: tuple[str, Any]) -> None:
        data_type, payload = data
        if not self._connected:
            self._connected = True
            self.connection_status_changed.emit(True)

        if data_type == "system":
            self._system_info = payload
            self.system_info_changed.emit(payload)
        elif data_type == "models":
            self._model_registry = payload
            self.model_registry_changed.emit(payload)
        elif data_type == "providers":
            self._providers = payload
            self.providers_changed.emit(payload)
        elif data_type == "sessions":
            self._sessions = payload
            self.sessions_changed.emit(payload)
        elif data_type == "memories":
            self.memories_changed.emit(payload)
        elif data_type == "network":
            self._network_status = payload
            self.network_status_changed.emit(payload)
        elif data_type == "voice":
            self._voice_status = payload
            self.voice_status_changed.emit(payload)
        elif data_type == "voice_devices":
            self._voice_devices = payload
            self.voice_devices_changed.emit(payload)

    def _on_error(self, err: str) -> None:
        logger.debug("ApiService error reported: %s", err)
        if "connect" in err.lower() or "503" in err:
            if self._connected:
                self._connected = False
                self.connection_status_changed.emit(False)
        self.error_occurred.emit(err)

    def _on_chat_message_sent(self, response: dict) -> None:
        if "choices" in response and response["choices"]:
            msg = response["choices"][0].get("message", {})
            content = msg.get("content", "")
            if content:
                self.chat_message_received.emit({
                    "role": "assistant",
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                })

    def _on_session_created(self, session_data: dict) -> None:
        self.session_created_signal.emit(session_data)
        self.refresh_all()

    def _on_voice_status_changed(self, status: dict) -> None:
        self._voice_status = status

    def _on_plugins_changed(self, plugins: list) -> None:
        self._plugins = plugins
