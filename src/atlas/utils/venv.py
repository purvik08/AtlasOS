"""Virtual environment detection utilities for Atlas OS."""

from __future__ import annotations

import os
import sys
from pathlib import Path

def get_python_executable() -> str:
    """Resolve the best Python executable for running subprocesses.

    Prioritizes the active virtual environment, then any local .venv/venv directory,
    and finally falls back to sys.executable.
    """
    current = sys.executable
    if current and ("venv" in current or ".venv" in current):
        return current

    # Search for a virtual environment in the project root
    # src/atlas/utils/venv.py -> 4 levels up is the project root (D:\AtlasOS)
    cwd = Path.cwd()
    for base in (cwd, Path(__file__).resolve().parent.parent.parent.parent):
        for venv_name in (".venv", "venv"):
            venv_dir = base / venv_name
            if os.name == "nt":
                candidate = venv_dir / "Scripts" / "python.exe"
            else:
                candidate = venv_dir / "bin" / "python"
            if candidate.exists():
                return str(candidate)

    return current
