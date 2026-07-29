"""HTTPX clients whose traffic is isolated inside userspace WireGuard."""

from ._client import AsyncClient, Client
from ._exceptions import (
    BinaryNotFoundError,
    ConfigError,
    StartupError,
    WgHttpxError,
)
from ._proxy import WireGuardProxy

__all__ = [
    "AsyncClient",
    "BinaryNotFoundError",
    "Client",
    "ConfigError",
    "StartupError",
    "WgHttpxError",
    "WireGuardProxy",
]

__version__ = "0.1.0"
