"""Atlas OS CLI package.

This package provides the command-line interface for Atlas OS.
"""

__all__ = ["cli"]


def __getattr__(name: str):
    """Lazy import to avoid loading the full CLI chain on package init."""
    if name == "cli":
        from atlas.cli.main import cli
        return cli
    raise AttributeError(f"module 'atlas.cli' has no attribute {name!r}")
