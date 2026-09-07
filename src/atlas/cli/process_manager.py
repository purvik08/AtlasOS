"""Process manager for Atlas OS - handles backend and desktop processes with
proper signal handling."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, IO

import httpx
from rich.console import Console

from atlas.utils import get_python_executable

console = Console()


class ProcessManager:
    """Manages Atlas OS backend and desktop processes with proper signal handling."""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        heartbeat_interval: float = 5.0,
    ) -> None:
        self.backend_process: subprocess.Popen[Any] | None = None
        self.desktop_process: subprocess.Popen[Any] | None = None
        self._shutdown_event = asyncio.Event()
        self._shutdown_requested = False
        self._signal_handlers_installed = False
        self._backend_log_handle: IO[Any] | None = None
        self._desktop_log_handle: IO[Any] | None = None
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._heartbeat_interval = heartbeat_interval
        self._desktop_retry_count = 0
        self._monitor_task: asyncio.Task[None] | None = None

    def _get_backend_url(self) -> str:
        """Get the backend URL from environment or default."""
        return os.environ.get("ATLAS_API_URL", "http://127.0.0.1:8000")

    def _get_backend_log_file(self) -> Path:
        """Get the backend log file path."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        return log_dir / "backend.log"

    def _get_desktop_log_file(self) -> Path:
        """Get the desktop log file path."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        return log_dir / "desktop.log"

    def _install_signal_handlers(self) -> None:
        """Install async-safe signal handlers for graceful shutdown."""
        if self._signal_handlers_installed:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, can't install async signal handlers
            console.print(
                "[yellow]Warning: No running event loop, signal handlers not installed[/]"
            )
            return

        def _request_shutdown() -> None:
            """Thread-safe shutdown request from signal handler."""
            self._shutdown_requested = True
            self._shutdown_event.set()

        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, _request_shutdown)
            loop.add_signal_handler(signal.SIGTERM, _request_shutdown)
            self._signal_handlers_installed = True
        except (NotImplementedError, RuntimeError):
            # Windows or no event loop - fall back to synchronous handlers
            def _sync_signal_handler(signum: int, frame: Any) -> None:
                self._shutdown_requested = True
                self._shutdown_event.set()

            signal.signal(signal.SIGINT, _sync_signal_handler)
            signal.signal(signal.SIGTERM, _sync_signal_handler)
            self._signal_handlers_installed = True

    def _get_backend_url(self) -> str:
        """Get the backend URL from environment or default."""
        return os.environ.get("ATLAS_API_URL", "http://127.0.0.1:8000")

    def _get_backend_log_file(self) -> Path:
        """Get the backend log file path."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        return log_dir / "backend.log"

    def _get_desktop_log_file(self) -> Path:
        """Get the desktop log file path."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        return log_dir / "desktop.log"

    async def wait_for_health(self, url: str, timeout: float = 30.0) -> bool:
        """Wait for backend health endpoint to become available."""
        try:
            async with asyncio.timeout(timeout):
                while True:
                    try:
                        async with httpx.AsyncClient(timeout=2.0) as client:
                            response = await client.get(f"{url}/v1/health", timeout=2.0)
                            if response.status_code == 200:
                                return True
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)
        except TimeoutError:
            return False
        return False

    def start_backend(
        self, url: str = "http://127.0.0.1:8000", api_key: str | None = None, log_file: str | None = None
    ) -> subprocess.Popen[Any]:
        """Start the FastAPI backend server."""
        env = os.environ.copy()
        env["ATLAS_API_URL"] = url
        if api_key:
            env["ATLAS_API_KEY"] = api_key

        log_path = log_file or self._get_backend_log_file()
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        self._backend_log_handle = open(log_path, "a")

        console.print(f"[cyan]Starting backend server at {url}...[/]")
        console.print(f"[dim]Backend logs: {log_path}[/]")

        proc = subprocess.Popen(
            [get_python_executable(), "-m", "atlas.api.server"],
            env=env,
            stdout=self._backend_log_handle,
            stderr=subprocess.STDOUT,
        )

        self.backend_process = proc
        return proc

    def start_desktop(
        self,
        url: str = "http://127.0.0.1:8000",
        api_key: str | None = None,
        log_file: str | None = None,
    ) -> subprocess.Popen[Any]:
        """Start the Qt desktop application."""
        env = os.environ.copy()
        env["ATLAS_API_URL"] = url
        if api_key:
            env["ATLAS_API_KEY"] = api_key
        # Ensure Quick Controls 2 style is set for the subprocess (Qt 6.5+)
        env["QT_QUICK_CONTROLS_STYLE"] = "Basic"

        log_path = Path(log_file) if log_file else self._get_desktop_log_file()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        self._desktop_log_handle = open(log_path, "a")

        console.print("[cyan]Starting desktop UI...[/]")
        console.print(f"[dim]Desktop logs: {log_path}[/]")

        # Resolve PySide6's bundled QML directory so Qt can locate
        # QtQuick.Controls and other QML plugins without a system Qt install.
        try:
            import importlib.util
            pyside6_spec = importlib.util.find_spec("PySide6")
            if pyside6_spec is None:
                console.print(
                    "[yellow]Warning: PySide6 not found in this environment. "
                    "Install it with: pip install PySide6[/]"
                )
            else:
                pyside6_dir = os.path.dirname(pyside6_spec.origin)
                # PySide6 ships its QML modules under PySide6/Qt/qml (Linux wheels)
                # Some builds use PySide6/qml directly.
                qml_candidates = [
                    os.path.join(pyside6_dir, "Qt", "qml"),
                    os.path.join(pyside6_dir, "qml"),
                    os.path.join(pyside6_dir, "Qt6", "qml"),
                ]
                existing_qml = [q for q in qml_candidates if os.path.isdir(q)]
                if existing_qml:
                    # Prepend to any existing QML2_IMPORT_PATH
                    existing = env.get("QML2_IMPORT_PATH", "")
                    extra = os.pathsep.join(existing_qml)
                    env["QML2_IMPORT_PATH"] = f"{extra}{os.pathsep}{existing}" if existing else extra
                else:
                    console.print(
                        "[yellow]Warning: Could not locate PySide6 QML directory. "
                        "QtQuick.Controls may not load. Try: pip install PySide6-Addons[/]"
                    )
        except Exception:
            pass  # Non-fatal

        # Resolve dashboard script path directly — avoids launching via
        # `python -m atlas.ui.dashboard.main` which triggers atlas/__init__.py
        # and chain-imports the entire CLI/AI stack in the subprocess.
        dashboard_script = os.path.join(
            os.path.dirname(__file__),
            "..", "ui", "dashboard", "main.py"
        )
        dashboard_script = os.path.abspath(dashboard_script)
        
        proc = subprocess.Popen(
            [get_python_executable(), dashboard_script],
            env=env,
            stdout=self._desktop_log_handle,
            stderr=subprocess.STDOUT,
        )

        self.desktop_process = proc
        # Do NOT reset retry count here; it's managed by _monitor_desktop

        return proc

    async def _monitor_desktop(self) -> None:
        """Monitor desktop process and restart on crash (up to max_retries)."""
        while not self._shutdown_requested:
            await asyncio.sleep(1.0)

            if self.desktop_process and self.desktop_process.poll() is not None:
                # Desktop process has exited
                exit_code = self.desktop_process.poll()
                if self._shutdown_requested:
                    console.print("[dim]Desktop stopped due to user shutdown[/]")
                    return

                if self._desktop_retry_count < self._max_retries:
                    self._desktop_retry_count += 1
                    console.print(
                        f"[yellow]Desktop crashed (exit={exit_code}), "
                        f"restarting ({self._desktop_retry_count}/{self._max_retries})...[/]"
                    )
                    await asyncio.sleep(self._retry_delay)
                    self.start_desktop(
                        url=self._get_backend_url(),
                        api_key=os.environ.get("ATLAS_API_KEY"),
                    )
                else:
                    console.print(
                        f"[red]Desktop crashed {self._max_retries} times. "
                        "Check logs at logs/desktop.log[/]"
                    )
                    await self.shutdown()
                    return

    async def shutdown(self) -> None:
        """Gracefully shut down all managed processes."""
        if self._shutdown_event.is_set():
            return

        self._shutdown_event.set()
        console.print("[dim]Shutting down processes...[/]")

        # Stop desktop first (UI should close first)
        if self.desktop_process and self.desktop_process.poll() is None:
            console.print("[dim]Stopping desktop...[/]")
            self.desktop_process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self.desktop_process.wait),
                    timeout=10.0,
                )
            except TimeoutError:
                console.print("[yellow]Desktop didn't stop gracefully, forcing...[/]")
                self.desktop_process.kill()
                await asyncio.to_thread(self.desktop_process.wait)

        # Stop backend
        if self.backend_process and self.backend_process.poll() is None:
            console.print("[dim]Stopping backend...[/]")
            self.backend_process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self.backend_process.wait),
                    timeout=10.0,
                )
            except TimeoutError:
                console.print("[yellow]Backend didn't stop gracefully, forcing...[/]")
                self.backend_process.kill()
                await asyncio.to_thread(self.backend_process.wait)

        console.print("[green][+] All processes stopped[/]")

    async def run(
        self,
        url: str = "http://127.0.0.1:8000",
        api_key: str | None = None,
        no_gui: bool = False,
        once: bool = False,
    ) -> None:
        """Run the full Atlas OS stack: backend + desktop."""
        self._install_signal_handlers()

        # Create logs directory
        await asyncio.to_thread(Path("logs").mkdir, exist_ok=True)

        # Start backend with api_key
        self.start_backend(url=url, api_key=api_key)

        # Wait for backend to be ready
        console.print("[dim]Waiting for backend to be ready...[/]")
        if not await self.wait_for_health(self._get_backend_url()):
            console.print("[red]Backend failed to start within timeout[/]")
            await self.shutdown()
            return

        console.print("[green][+] Backend is ready[/]")

        if no_gui or once:
            # Console mode - use dashboard logic to fetch data once
            console.print("[cyan]Running in console mode...[/]")
            from atlas.ui.dashboard.models import SystemInfo, ModelRegistry, ProviderHealth, ChatSession
            from atlas.api.sdk import AtlasSDK
            
            sdk = AtlasSDK(base_url=url, api_key=api_key)
            async with sdk:
                # Fetch system info
                system = await SystemInfo.fetch(sdk)
                console.print(f"\n[bold]Backend Status:[/] {url}")
                console.print(f"[bold]System:[/] OK")
                console.print(f"  CPU: {system.cpu_percent:.1f}%")
                console.print(f"  Memory: {system.memory_percent:.1f}% ({system.memory_used_gb:.1f}/{system.memory_total_gb:.1f} GB)")
                console.print(f"  Disk: {system.disk_percent:.1f}%")
                console.print(f"  Uptime: {system.uptime_seconds:.0f}s")
                
                # Models
                models = await ModelRegistry.fetch(sdk)
                console.print(f"\n[bold]Models:[/] {len(models.models)} total, {sum(1 for m in models.models if m.loaded)} loaded")
                for m in models.models:
                    status = "loaded" if m.loaded else "unloaded"
                    console.print(f"  {m.display_name} ({m.model_id}) - {status} - {m.size_gb:.2f} GB")
                
                # Providers
                providers = []
                for p_name in ["llama_cpp", "gemini", "deepseek", "kimi", "qwen"]:
                    health = await ProviderHealth.fetch(sdk, p_name)
                    providers.append(health)
                
                console.print(f"\n[bold]Providers:[/] {len(providers)} configured")
                for p in providers:
                    status_color = {
                        "healthy": "green",
                        "degraded": "yellow",
                        "unhealthy": "red",
                        "unloaded": "dim",
                    }.get(p.status, "white")
                    loaded_info = f" ({', '.join(p.loaded_models)})" if p.loaded_models else ""
                    console.print(f"  [{status_color}]{p.name}: {p.status}{loaded_info}[/]")
                
                # Sessions
                sessions = await ChatSession.fetch_all(sdk)
                console.print(f"\n[bold]Sessions:[/] {len(sessions)} active")
                for s in sessions[:5]:
                    console.print(f"  {s.session_id[:8]}... - {s.provider_name}/{s.model_id} - {len(s.history)} msgs")
            
            if once:
                return
            
            return

        console.print("[green][+] Backend is ready[/]")

        # Create monitor task once before starting desktop
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_desktop())

        # Start desktop with api_key
        self.start_desktop(url=url, api_key=api_key)

        console.print("[green][+] Atlas OS is running![/]")
        console.print("[dim]Press Ctrl+C to stop[/]")

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Graceful shutdown
        await self.shutdown()


async def run_atlas_start(
    url: str = "http://127.0.0.1:8000",
    api_key: str | None = None,
    no_gui: bool = False,
    once: bool = False,
) -> None:
    """Entry point for `atlas start` command."""
    manager = ProcessManager()
    await manager.run(url=url, api_key=api_key, no_gui=no_gui, once=once)