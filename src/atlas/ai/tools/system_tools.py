"""System and hardware introspection tools for Atlas OS AI."""

from __future__ import annotations

import logging
import platform
import socket
import time
from typing import Any

import psutil

from atlas.ai.tools.base import BaseTool, ToolPermissionLevel, ToolResult

logger = logging.getLogger(__name__)


class GetSystemMetricsTool(BaseTool):
    """Tool to inspect real-time CPU, RAM, Disk, Temperature, and Uptime."""

    name = "get_system_metrics"
    description = "Get real-time system performance metrics including CPU usage, RAM memory usage, disk storage, and uptime."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = []

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            disk_root = "C:\\" if platform.system() == "Windows" else "/"
            disk = psutil.disk_usage(disk_root)
            boot_time = psutil.boot_time()
            uptime_sec = int(time.time() - boot_time)
            hours, remainder = divmod(uptime_sec, 3600)
            minutes, seconds = divmod(remainder, 60)

            data = {
                "cpu_percent": cpu,
                "ram_percent": mem.percent,
                "ram_used_gb": round((mem.total - mem.available) / (1024**3), 2),
                "ram_total_gb": round(mem.total / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "uptime": f"{hours}h {minutes}m {seconds}s",
                "uptime_seconds": uptime_sec,
            }
            return ToolResult(success=True, data=data)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))


class GetSystemInfoTool(BaseTool):
    """Tool to retrieve hostname, OS details, Python version, and system architecture."""

    name = "get_system_info"
    description = "Get operating system details, hostname, architecture, platform version, and Python runtime info."
    permission_level = ToolPermissionLevel.READ_ONLY
    parameters = []

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            data = {
                "os": "Atlas OS",
                "version": "0.1.0",
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor() or platform.machine(),
                "python_version": platform.python_version(),
            }
            return ToolResult(success=True, data=data)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))
