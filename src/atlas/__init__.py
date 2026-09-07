"""Atlas OS - AI Edge Operating System."""

__version__ = "0.1.0"

__all__ = ["cli"]


def __getattr__(name: str):
    """Lazy import to avoid loading the full CLI chain on package init."""
    if name == "cli":
        from atlas.cli.main import cli
        return cli
    raise AttributeError(f"module 'atlas' has no attribute {name!r}")
