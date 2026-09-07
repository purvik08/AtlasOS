"""Graceful shutdown signal handling for Atlas OS.

Wraps the platform differences between POSIX (SIGINT/SIGTERM handled via the
event loop) and Windows (which does not support ``loop.add_signal_handler``)
behind a single, testable interface.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

ShutdownCallback = Callable[[], Coroutine[Any, Any, None]]

_HANDLED_SIGNALS = (signal.SIGINT, signal.SIGTERM)


class ShutdownSignalHandler:
    """Installs OS signal handlers that trigger an async shutdown callback.

    On POSIX platforms this uses ``loop.add_signal_handler`` for a clean,
    async-native handler. On Windows, where that API is unavailable, it falls
    back to ``signal.signal``. Both paths funnel through
    ``call_soon_threadsafe`` so the shutdown coroutine is always scheduled
    safely on the running event loop.
    """

    def __init__(self, on_shutdown: ShutdownCallback) -> None:
        self._on_shutdown = on_shutdown
        self._installed = False
        self._triggered = False

    def install(self) -> None:
        """Register signal handlers on the running event loop."""

        if self._installed:
            return
        loop = asyncio.get_running_loop()

        if sys.platform != "win32":
            for sig in _HANDLED_SIGNALS:
                loop.add_signal_handler(sig, self._handle, sig, loop)
        else:
            for sig in _HANDLED_SIGNALS:
                def make_handler(s: int):
                    def handler(_signum: int, _frame: Any) -> None:
                        self._handle(s, loop)
                    return handler
                signal.signal(sig, make_handler(sig))

        self._installed = True
        logger.debug("Shutdown signal handlers installed.")

    def reset(self) -> None:
        """Reset the triggered flag. Intended for tests."""

        self._triggered = False

    def _handle(self, sig: int, loop: asyncio.AbstractEventLoop) -> None:
        if self._triggered:
            logger.warning(
                "Received signal %s again; shutdown already in progress.", sig
            )
            return
        self._triggered = True
        logger.info(
            "Received signal %s; initiating graceful shutdown.",
            signal.Signals(sig).name,
        )
        loop.call_soon_threadsafe(lambda: loop.create_task(self._on_shutdown()))
