"""Bounded Joern analysis for coding agents."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("joern-agent-bridge")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["__version__"]
