"""Minimal manual smoke test for the Atlas OS Runtime Core.

Run with:

    python scripts/demo_runtime.py

This is not part of the CLI (that lands with the CLI module); it's a
lightweight way to see the runtime lifecycle, health monitor, and heartbeat
working end-to-end before the rest of Atlas OS exists.
"""

from __future__ import annotations

import asyncio
import logging

from atlas.config import AtlasConfig
from atlas.logging import configure_logging
from atlas.runtime import AtlasApplication, HealthStatus, IService, ServiceHealth

logger = logging.getLogger("atlas.demo")


class EchoService(IService):
    """A trivial service used to demonstrate the lifecycle."""

    @property
    def name(self) -> str:
        return "echo"

    async def start(self) -> None:
        logger.info("EchoService started.")

    async def stop(self) -> None:
        logger.info("EchoService stopped.")

    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(name=self.name, status=HealthStatus.HEALTHY, message="ok")


async def main() -> None:
    config = AtlasConfig(heartbeat_interval_seconds=2, health_check_interval_seconds=5)
    configure_logging(config.log_level, json_format=config.log_json)

    app = AtlasApplication(config)
    app.register_service(EchoService())

    async with app:
        logger.info("Atlas OS is running. state=%s", app.state.value)
        await asyncio.sleep(3)
        report = app.health_monitor.latest_report
        logger.info(
            "Health report: status=%s services=%d", report.status.value, len(report.services)
        )
        beat = app.heartbeat.last_beat
        if beat is not None:
            logger.info("Last heartbeat: #%d", beat.sequence)

    logger.info("Atlas OS shut down cleanly. state=%s", app.state.value)


if __name__ == "__main__":
    asyncio.run(main())
