"""Terminal WebSocket route — Atlas CLI embedded terminal.

Provides a full-duplex WebSocket session that connects a web/dashboard
client to an interactive Atlas CLI subprocess. Supports PTY on POSIX
and pipe-based fallback on Windows.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/terminal", tags=["terminal"])

_CMD = [sys.executable, "-m", "atlas"]
_IS_POSIX = platform.system() != "Windows"


@router.get("/ping")
async def terminal_ping() -> dict[str, Any]:
    """Health-check for the terminal endpoint."""
    return {"status": "ok", "platform": platform.system()}


@router.websocket("/ws")
async def terminal_ws(websocket: WebSocket) -> None:
    """WebSocket terminal — bidirectional Atlas CLI session."""
    await websocket.accept()
    logger.info("Terminal WebSocket connected")

    proc: asyncio.subprocess.Process | None = None
    master_fd: int | None = None

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    src_path = str(Path.cwd() / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else src_path
    )

    try:
        if _IS_POSIX:
            # Full PTY — preserves ANSI colour codes, readline, etc.
            import pty
            master_fd, slave_fd = pty.openpty()
            proc = await asyncio.create_subprocess_exec(
                *_CMD,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env=env,
                cwd=os.getcwd(),
            )
            os.close(slave_fd)


            loop = asyncio.get_event_loop()

            async def _read_pty() -> None:
                while proc.returncode is None:
                    try:
                        data = await loop.run_in_executor(
                            None, lambda: os.read(master_fd, 4096)
                        )
                        if data:
                            await websocket.send_text(data.decode("utf-8", errors="replace"))
                    except OSError:
                        break

            async def _write_pty() -> None:
                while proc.returncode is None:
                    try:
                        msg = await websocket.receive_text()
                        os.write(master_fd, msg.encode("utf-8", errors="replace"))
                    except WebSocketDisconnect:
                        break
                    except Exception:
                        break

            await asyncio.gather(_read_pty(), _write_pty(), return_exceptions=True)

        else:
            # Windows: pipe-based fallback
            proc = await asyncio.create_subprocess_exec(
                *_CMD,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                cwd=os.getcwd(),
            )


            async def _read_pipe() -> None:
                assert proc.stdout is not None
                while proc.returncode is None:
                    try:
                        data = await proc.stdout.read(4096)
                        if not data:
                            break
                        await websocket.send_text(data.decode("utf-8", errors="replace"))
                    except Exception:
                        break

            async def _write_pipe() -> None:
                assert proc.stdin is not None
                while proc.returncode is None:
                    try:
                        msg = await websocket.receive_text()
                        proc.stdin.write(msg.encode("utf-8", errors="replace"))
                        await proc.stdin.drain()
                    except WebSocketDisconnect:
                        break
                    except Exception:
                        break

            await asyncio.gather(_read_pipe(), _write_pipe(), return_exceptions=True)

    except WebSocketDisconnect:
        logger.info("Terminal WebSocket disconnected")
    except Exception as exc:
        logger.error("Terminal error: %s", exc)
        try:
            await websocket.send_text(f"\r\n[Terminal error: {exc}]\r\n")
        except Exception:
            pass
    finally:
        if proc and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
        if master_fd is not None:
            try:
                os.close(master_fd)
            except OSError:
                pass
        logger.info("Terminal session closed")
