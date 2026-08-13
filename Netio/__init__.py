from importlib.metadata import PackageNotFoundError, version

from Netio.Device import JsonDevice
from Netio.Device import JsonDevice as Netio  # Default device

try:
    __version__ = version("Netio")
except PackageNotFoundError:  # the package is not installed, e.g. a source checkout
    __version__ = "unknown"

__all__ = ["Netio", "JsonDevice", "__version__"]
