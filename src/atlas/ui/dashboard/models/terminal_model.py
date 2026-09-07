"""Terminal model & CLI process controller for Atlas OS Dashboard.

Provides interactive embedded command-line execution for Atlas CLI
and system commands directly inside the QML dashboard.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

logger = logging.getLogger(__name__)


class TerminalModel(QObject):
    """Interactive CLI terminal model exposed to QML."""

    outputChanged = Signal(str)
    outputAppended = Signal(str)
    commandExecuted = Signal(str, int)  # command, return_code
    busyChanged = Signal(bool)
    historyIndexChanged = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._output_lines: list[str] = [
            "============================================================",
            "  Atlas OS Embedded Terminal [Version 0.1.0]",
            "  Type 'help' or 'atlas --help' for available commands.",
            "============================================================",
            "",
        ]
        self._history: list[str] = []
        self._history_idx: int = -1
        self._is_busy: bool = False
        self._proc: subprocess.Popen[str] | None = None

    @Property(str, notify=outputChanged)
    def output(self) -> str:
        return "\n".join(self._output_lines)

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(str, constant=True)
    def prompt(self) -> str:
        return "atlas@os:~$ "

    @Slot(str)
    def executeCommand(self, cmd_line: str) -> None:
        """Execute a CLI command asynchronously and capture output."""
        clean_cmd = cmd_line.strip()
        if not clean_cmd:
            return

        # Record history
        if not self._history or self._history[-1] != clean_cmd:
            self._history.append(clean_cmd)
        self._history_idx = len(self._history)

        # Handle 'clear' or 'cls' internally
        if clean_cmd.lower() in ("clear", "cls"):
            self.clear()
            return

        # Print command echo
        echo_line = f"{self.prompt}{clean_cmd}"
        self._append_line(echo_line)

        # Build execution args
        import shlex
        posix_mode = platform.system() != "Windows"

        try:
            tokens = shlex.split(clean_cmd, posix=posix_mode)
        except Exception:
            tokens = clean_cmd.split()

        first = tokens[0].lower() if tokens else ""
        if first == "atlas":
            sub_args = tokens[1:] if len(tokens) > 1 else ["--help"]
            full_cmd = [sys.executable, "-m", "atlas"] + sub_args
            use_shell = False
        elif first == "help":
            full_cmd = [sys.executable, "-m", "atlas", "--help"]
            use_shell = False
        elif first in ("python", "python3", "py"):
            if len(tokens) > 1 and tokens[1] == "-m":
                sub_args = tokens[2:] if len(tokens) > 2 else ["atlas", "--help"]
                full_cmd = [sys.executable, "-m"] + sub_args
                use_shell = False
            else:
                sub_args = tokens[1:]
                full_cmd = [sys.executable] + sub_args
                use_shell = False
        else:
            # General shell execution
            full_cmd = clean_cmd
            use_shell = True

        self._is_busy = True
        self.busyChanged.emit(True)

        def _run_worker():
            try:
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                # Ensure src is on PYTHONPATH regardless of current working directory
                src_path = str(Path(__file__).resolve().parents[4])
                repo_dir = str(Path(__file__).resolve().parents[5])
                existing_pythonpath = env.get("PYTHONPATH", "")
                env["PYTHONPATH"] = (
                    f"{src_path}{os.pathsep}{existing_pythonpath}"
                    if existing_pythonpath
                    else src_path
                )

                proc = subprocess.Popen(
                    full_cmd,
                    shell=use_shell,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env,
                    cwd=repo_dir,
                )
                self._proc = proc

                assert proc.stdout is not None
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        cleaned = line.rstrip("\r\n")
                        self._append_line(cleaned)

                proc.stdout.close()
                rc = proc.wait()
                self.commandExecuted.emit(clean_cmd, rc)
            except Exception as exc:
                self._append_line(f"[Error: {exc}]")
                self.commandExecuted.emit(clean_cmd, 1)
            finally:
                self._is_busy = False
                self.busyChanged.emit(False)
                self._proc = None

        thread = threading.Thread(target=_run_worker, daemon=True)
        thread.start()

    def _append_line(self, line: str) -> None:
        self._output_lines.append(line)
        # Retain maximum 2000 lines
        if len(self._output_lines) > 2000:
            self._output_lines = self._output_lines[-2000:]
        self.outputChanged.emit(self.output)
        self.outputAppended.emit(line)

    @Slot()
    def clear(self) -> None:
        """Clear terminal history buffer."""
        self._output_lines = []
        self.outputChanged.emit("")

    @Slot(int, result=str)
    def getHistory(self, direction: int) -> str:
        """Navigate command history. direction: -1 (older/up), +1 (newer/down)."""
        if not self._history:
            return ""

        new_idx = self._history_idx + direction
        if 0 <= new_idx < len(self._history):
            self._history_idx = new_idx
            return self._history[self._history_idx]
        elif new_idx >= len(self._history):
            self._history_idx = len(self._history)
            return ""
        return self._history[0] if self._history else ""

    @Slot()
    def interrupt(self) -> None:
        """Send SIGINT or terminate active process."""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._append_line("^C")
            except Exception as exc:
                logger.debug("Failed to interrupt terminal process: %s", exc)
