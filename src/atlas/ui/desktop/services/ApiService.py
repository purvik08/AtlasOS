"""API Service for Qt/QML integration - connects to real backend API."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QThread

# Import existing models from kiosk - reuse the same data models
from atlas.ui.kiosk.models import (
    SystemInfo,
    ModelRegistry,
    ModelInfo,
    ProviderHealth,
    ChatSession,
    ProviderStatus,
)

from atlas.api.sdk import AtlasSDK


class ApiWorker(QThread):
    """Worker thread for async API calls."""
    
    data_ready = Signal(object)
    error_occurred = Signal(str)
    
    def __init__(self, sdk: AtlasSDK):
        super().__init__()
        self.sdk = sdk
        self._running = True
    
    def run(self):
        """Run the async event loop."""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._fetch_all())
    
    async def _fetch_all(self):
        """Fetch all data from backend API."""
        try:
            # Fetch system info
            system_info = await SystemInfo.fetch(self.sdk)
            self.data_ready.emit(("system", system_info))
            
            # Fetch model registry
            model_registry = await ModelRegistry.fetch(self.sdk)
            self.data_ready.emit(("models", model_registry))
            
            # Fetch providers
            try:
                provider_list = await self.sdk.list_providers()
                if provider_list:
                    provider_names = [p.get("name", "") for p in provider_list if p.get("name")]
                    providers_health = await self._check_providers_health(provider_names)
                    self.data_ready.emit(("providers", providers_health))
            except Exception as e:
                self.error_occurred.emit(f"Providers error: {e}")
            
            # Fetch sessions
            try:
                sessions = await ChatSession.fetch_all(self.sdk)
                self.data_ready.emit(("sessions", sessions))
            except Exception as e:
                self.error_occurred.emit(f"Sessions error: {e}")
                
            # Fetch memory conversations
            try:
                from atlas.api.sdk import AtlasSDK
                # This would need a proper endpoint
                # conversations = await self.sdk.get_conversations()
            except Exception as e:
                self.error_occurred.emit(f"Memory error: {e}")
                
        except Exception as e:
            self.error_occurred.emit(f"API error: {e}")
    
    async def _check_providers_health(self, provider_names: list[str]) -> list[ProviderHealth]:
        """Check health for all providers."""
        results = []
        for name in provider_names:
            try:
                health = await ProviderHealth.fetch(self.sdk, name)
                results.append(health)
            except Exception as e:
                results.append(ProviderHealth(
                    name=name,
                    status=ProviderStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    error=str(e),
                ))
        return results


class ApiService(QObject):
    """Main API service exposed to QML - handles all backend communication."""
    
    # Signals for QML binding
    system_info_changed = Signal(object)
    model_registry_changed = Signal(object)
    providers_changed = Signal(list)
    sessions_changed = Signal(list)
    error_occurred = Signal(str)
    connection_status_changed = Signal(bool)
    
    # Memory signals
    conversations_changed = Signal(list)
    search_results_changed = Signal(list)
    rag_results_changed = Signal(object)
    
    # Network signals
    network_interfaces_changed = Signal(list)
    wifi_scan_results_changed = Signal(list)
    ap_status_changed = Signal(object)
    
    # Voice signals
    voice_devices_changed = Signal(list)
    wake_word_detected = Signal(str)
    transcript_received = Signal(str)
    
    # Plugin signals
    plugins_changed = Signal(list)
    
    # Log signals
    log_lines_changed = Signal(list)
    
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
        self._worker: ApiWorker | None = None
        self._connected = False
        
        # Timer for periodic refresh
        self._timer = QTimer()
        self._timer.timeout.connect(self.refresh_all)
        self._timer.setInterval(5000)  # 5 seconds
        
        # Initial data
        self._system_info: SystemInfo | None = None
        self._model_registry: ModelRegistry | None = None
        self._providers: list[ProviderHealth] = []
        self._sessions: list[ChatSession] = []
        self._conversations: list[Any] = []
        self._network_interfaces: list[Any] = []
        self._wifi_networks: list[Any] = []
        self._ap_status: dict[str, Any] = {}
        self._voice_devices: list[Any] = []
        self._plugins: list[Any] = []
        self._log_lines: list[str] = []
    
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
    
    @property
    def conversations(self) -> list[Any]:
        return self._conversations
    
    @property
    def network_interfaces(self) -> list[Any]:
        return self._network_interfaces
    
    @property
    def wifi_networks(self) -> list[Any]:
        return self._wifi_networks
    
    @property
    def ap_status(self) -> dict[str, Any]:
        return self._ap_status
    
    @property
    def voice_devices(self) -> list[Any]:
        return self._voice_devices
    
    @property
    def plugins(self) -> list[Any]:
        return self._plugins
    
    @property
    def log_lines(self) -> list[str]:
        return self._log_lines
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    @Slot()
    def refresh_all(self) -> None:
        """Refresh all data from backend API."""
        # Stop any existing worker
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(1000)
        
        # Create new worker
        self._worker = ApiWorker(self._sdk)
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
    
    def _on_data_ready(self, data: tuple[str, Any]) -> None:
        """Handle incoming data from worker."""
        data_type, payload = data
        
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
        elif data_type == "conversations":
            self._conversations = payload
            self.conversations_changed.emit(payload)
        elif data_type == "search_results":
            self.search_results_changed.emit(payload)
        elif data_type == "rag_results":
            self.rag_results_changed.emit(payload)
        elif data_type == "network_interfaces":
            self._network_interfaces = payload
            self.network_interfaces_changed.emit(payload)
        elif data_type == "wifi_scan":
            self._wifi_networks = payload
            self.wifi_scan_results_changed.emit(payload)
        elif data_type == "ap_status":
            self._ap_status = payload
            self.ap_status_changed.emit(payload)
        elif data_type == "voice_devices":
            self._voice_devices = payload
            self.voice_devices_changed.emit(payload)
        elif data_type == "plugins":
            self._plugins = payload
            self.plugins_changed.emit(payload)
        elif data_type == "log_lines":
            self._log_lines = payload
            self.log_lines_changed.emit(payload)
    
    def _on_error(self, error: str) -> None:
        """Handle error from worker."""
        self.error_occurred.emit(error)
    
    def _on_worker_finished(self) -> None:
        """Handle worker completion."""
        self._connected = True
        self.connection_status_changed.emit(True)
    
    @Slot()
    def start_auto_refresh(self) -> None:
        """Start periodic auto-refresh."""
        self._timer.start()
    
    @Slot()
    def stop_auto_refresh(self) -> None:
        """Stop periodic auto-refresh."""
        self._timer.stop()
    
    @Slot()
    def shutdown(self) -> None:
        """Clean shutdown."""
        self.stop_auto_refresh()
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(2000)
        # Note: AtlasSDK doesn't have explicit close in current version
    
    # ===== Chat Operations =====
    
    @Slot(str, str, str, str, result=bool)
    def send_chat_message(
        self,
        session_id: str,
        model: str,
        message: str,
        provider: str = "",
    ) -> bool:
        """Send a chat message via API."""
        try:
            # Use worker thread for async operation
            async def _send():
                return await self._sdk.chat_completion(
                    messages=[{"role": "user", "content": message}],
                    model=model,
                    provider=provider or None,
                )
            
            # For now, use a simple approach
            self.error_occurred.emit("Chat sending requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Chat error: {e}")
            return False
    
    @Slot(str, str, result=bool)
    def create_session(self, provider: str, model: str) -> bool:
        """Create a new chat session."""
        try:
            # Use worker thread for async operation
            async def _create():
                return await ChatSession.create(
                    self._sdk,
                    provider=provider,
                    model=model,
                )
            
            self.error_occurred.emit("Session creation requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Session error: {e}")
            return False
    
    @Slot(str, result=bool)
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        try:
            self.error_occurred.emit("Session deletion not fully implemented yet")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Session error: {e}")
            return False
    
    # ===== Model Operations =====
    
    @Slot(str, result=bool)
    def load_model(self, model_id: str) -> bool:
        """Load a model into memory."""
        try:
            # Use worker thread for async operation
            async def _load():
                model_info = await ModelInfo.fetch(self._sdk, model_id)
                if not model_info.loaded:
                    # This would need a proper load endpoint
                    pass
            
            self.error_occurred.emit("Model loading requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Load model error: {e}")
            return False
    
    @Slot(str, result=bool)
    def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory."""
        try:
            self.error_occurred.emit("Model unloading requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Unload model error: {e}")
            return False
    
    @Slot(str, str, str, result=bool)
    def download_model(self, provider: str, model_id: str, quantization: str = "") -> bool:
        """Download a model from a provider."""
        try:
            self.error_occurred.emit("Model download requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Download model error: {e}")
            return False
    
    @Slot(str, result=bool)
    def remove_model(self, model_id: str) -> bool:
        """Remove a model from the registry (not the file)."""
        try:
            self.error_occurred.emit("Model removal not fully implemented yet")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Remove model error: {e}")
            return False
    
    # ===== Memory Operations =====
    
    @Slot(str, result=bool)
    def create_conversation(self, title: str) -> bool:
        """Create a new conversation."""
        try:
            self.error_occurred.emit("Conversation creation requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Conversation error: {e}")
            return False
    
    @Slot(str, result=bool)
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        try:
            self.error_occurred.emit("Conversation deletion requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Conversation error: {e}")
            return False
    
    @Slot(str, int, float, result=bool)
    def search_memory(self, query: str, top_k: int = 5, min_score: float = 0.0) -> bool:
        """Search memory for relevant conversations/documents."""
        try:
            self.error_occurred.emit("Memory search requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Search error: {e}")
            return False
    
    @Slot(str, str, int, float, result=bool)
    def rag_query(self, query: str, conversation_id: str = "", top_k: int = 5, min_score: float = 0.3) -> bool:
        """RAG query with context retrieval."""
        try:
            self.error_occurred.emit("RAG query requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"RAG error: {e}")
            return False
    
    @Slot(str, str, int, int, result=bool)
    def ingest_document(self, content: str, source: str, chunk_size: int = 512, chunk_overlap: int = 50) -> bool:
        """Ingest a document for RAG."""
        try:
            self.error_occurred.emit("Document ingestion requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Ingestion error: {e}")
            return False
    
    # ===== Network Operations =====
    
    @Slot(result=bool)
    def fetch_network_interfaces(self) -> bool:
        """Fetch all network interfaces."""
        try:
            self.error_occurred.emit("Network interfaces fetch requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Network error: {e}")
            return False
    
    @Slot(str, result=bool)
    def scan_wifi(self, interface: str = "") -> bool:
        """Scan for WiFi networks."""
        try:
            self.error_occurred.emit("WiFi scan requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"WiFi scan error: {e}")
            return False
    
    @Slot(str, str, str, result=bool)
    def connect_wifi(self, ssid: str, password: str = "", interface: str = "") -> bool:
        """Connect to a WiFi network."""
        try:
            self.error_occurred.emit("WiFi connect requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"WiFi connect error: {e}")
            return False
    
    @Slot(str, result=bool)
    def disconnect_wifi(self, interface: str = "") -> bool:
        """Disconnect from WiFi."""
        try:
            self.error_occurred.emit("WiFi disconnect requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"WiFi disconnect error: {e}")
            return False
    
    @Slot(str, str, int, str, result=bool)
    def start_ap(self, ssid: str, password: str = "", channel: int = 6, security: str = "WPA2") -> bool:
        """Start Access Point mode."""
        try:
            self.error_occurred.emit("AP start requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"AP start error: {e}")
            return False
    
    @Slot(result=bool)
    def stop_ap(self) -> bool:
        """Stop Access Point mode."""
        try:
            self.error_occurred.emit("AP stop requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"AP stop error: {e}")
            return False
    
    @Slot(result=bool)
    def fetch_ap_status(self) -> bool:
        """Fetch AP status."""
        try:
            self.error_occurred.emit("AP status fetch requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"AP status error: {e}")
            return False
    
    # ===== Voice Operations =====
    
    @Slot(result=bool)
    def fetch_voice_devices(self) -> bool:
        """Fetch available audio devices."""
        try:
            self.error_occurred.emit("Voice devices fetch requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Voice devices error: {e}")
            return False
    
    @Slot(int, result=bool)
    def detect_wake_word(self, timeout: int = 10) -> bool:
        """Detect wake word."""
        try:
            self.error_occurred.emit("Wake word detection requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Wake word error: {e}")
            return False
    
    @Slot(int, result=bool)
    def transcribe(self, duration: int = 5) -> bool:
        """Record and transcribe audio."""
        try:
            self.error_occurred.emit("Transcription requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Transcription error: {e}")
            return False
    
    @Slot(str, str, result=bool)
    def speak(self, text: str, voice: str = "") -> bool:
        """Text-to-speech."""
        try:
            self.error_occurred.emit("TTS requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"TTS error: {e}")
            return False
    
    # ===== Plugin Operations =====
    
    @Slot(result=bool)
    def fetch_plugins(self) -> bool:
        """Fetch installed plugins."""
        try:
            self.error_occurred.emit("Plugins fetch requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Plugins error: {e}")
            return False
    
    @Slot(str, str, result=bool)
    def install_plugin(self, name: str, version: str = "") -> bool:
        """Install a plugin."""
        try:
            self.error_occurred.emit("Plugin install requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Plugin install error: {e}")
            return False
    
    @Slot(str, result=bool)
    def uninstall_plugin(self, name: str) -> bool:
        """Uninstall a plugin."""
        try:
            self.error_occurred.emit("Plugin uninstall requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Plugin uninstall error: {e}")
            return False
    
    @Slot(str, result=bool)
    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        try:
            self.error_occurred.emit("Plugin enable requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Plugin enable error: {e}")
            return False
    
    @Slot(str, result=bool)
    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        try:
            self.error_occurred.emit("Plugin disable requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Plugin disable error: {e}")
            return False
    
    # ===== Config Operations =====
    
    @Slot(str, str, result=bool)
    def set_config(self, key: str, value: str) -> bool:
        """Set a configuration value."""
        try:
            self.error_occurred.emit("Config set requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Config error: {e}")
            return False
    
    @Slot(str, result=str)
    def get_config(self, key: str) -> str:
        """Get a configuration value."""
        try:
            return ""
        except Exception as e:
            self.error_occurred.emit(f"Config error: {e}")
            return ""
    
    # ===== Logs Operations =====
    
    @Slot(int, result=bool)
    def fetch_logs(self, lines: int = 100) -> bool:
        """Fetch recent log lines."""
        try:
            self.error_occurred.emit("Logs fetch requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Logs error: {e}")
            return False
    
    # ===== Runtime Operations =====
    
    @Slot(result=bool)
    def runtime_status(self) -> bool:
        """Get runtime status."""
        try:
            self.error_occurred.emit("Runtime status requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Runtime error: {e}")
            return False
    
    @Slot(result=bool)
    def runtime_start(self) -> bool:
        """Start the runtime."""
        try:
            self.error_occurred.emit("Runtime start requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Runtime error: {e}")
            return False
    
    @Slot(result=bool)
    def runtime_stop(self) -> bool:
        """Stop the runtime."""
        try:
            self.error_occurred.emit("Runtime stop requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Runtime error: {e}")
            return False
    
    # ===== API Key Operations =====
    
    @Slot(str, result=bool)
    def create_api_key(self, name: str) -> bool:
        """Create a new API key."""
        try:
            self.error_occurred.emit("API key creation requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"API key error: {e}")
            return False
    
    @Slot(result=bool)
    def list_api_keys(self) -> bool:
        """List API keys."""
        try:
            self.error_occurred.emit("API key list requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"API key error: {e}")
            return False
    
    @Slot(str, result=bool)
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        try:
            self.error_occurred.emit("API key revoke requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"API key error: {e}")
            return False
    
    # ===== Doctor/Health =====
    
    @Slot(result=bool)
    def run_doctor(self) -> bool:
        """Run system diagnostics."""
        try:
            self.error_occurred.emit("Doctor requires async implementation")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Doctor error: {e}")
            return False