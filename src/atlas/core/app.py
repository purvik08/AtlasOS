"""Core application module for Atlas OS."""

from __future__ import annotations

from typing import Any


class AtlasApplication:
    """Main Atlas application class.

    This is a stub implementation for LSP/type checking purposes.
    The actual implementation will be provided in a future version.
    """

    def __init__(self) -> None:
        """Initialize the Atlas application."""
        self.config: Any = None
        self.container: Any = None
        self.health_monitor: Any = None
        self.uptime_seconds: float = 0.0
        self.heartbeat: Any = None

    def is_healthy(self) -> bool:
        """Check if the application is healthy.

        Returns:
            True if healthy, False otherwise

        """
        return True
