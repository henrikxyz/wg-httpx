"""Public exceptions raised by wg-httpx."""


class WgHttpxError(Exception):
    """Base exception for wg-httpx."""


class BinaryNotFoundError(WgHttpxError):
    """Raised when a compatible wireproxy executable cannot be found."""


class ConfigError(WgHttpxError):
    """Raised when the WireGuard configuration cannot be used."""


class StartupError(WgHttpxError):
    """Raised when wireproxy exits or does not become ready in time."""
