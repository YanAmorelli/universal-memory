"""Universal Memory package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("universal-memory")
except PackageNotFoundError:
    __version__ = "0.4.0"
