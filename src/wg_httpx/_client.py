"""Drop-in HTTPX clients backed by a managed userspace WireGuard proxy."""

from __future__ import annotations

import os
from types import TracebackType
from typing import Any

import httpx

from ._proxy import ConfigInput, WireGuardProxy


def _reserved_arguments(kwargs: dict[str, Any]) -> None:
    reserved = {"proxy", "transport"}.intersection(kwargs)
    if reserved:
        names = ", ".join(sorted(reserved))
        raise TypeError(f"wg-httpx manages the following HTTPX argument(s): {names}")


class Client(httpx.Client):
    """A synchronous HTTPX client whose connections go through WireGuard."""

    def __init__(
        self,
        config: ConfigInput,
        *,
        wireproxy_binary: str | os.PathLike[str] | None = None,
        startup_timeout: float = 10.0,
        **kwargs: Any,
    ) -> None:
        _reserved_arguments(kwargs)
        self.wireguard = WireGuardProxy(
            config,
            binary=wireproxy_binary,
            startup_timeout=startup_timeout,
        )
        self.wireguard.start()
        kwargs.setdefault("trust_env", False)
        try:
            super().__init__(proxy=self.wireguard.proxy_url, **kwargs)
        except Exception:
            self.wireguard.close()
            raise

    def close(self) -> None:
        try:
            super().close()
        finally:
            self.wireguard.close()

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        try:
            super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.wireguard.close()


class AsyncClient(httpx.AsyncClient):
    """An asynchronous HTTPX client whose connections go through WireGuard."""

    def __init__(
        self,
        config: ConfigInput,
        *,
        wireproxy_binary: str | os.PathLike[str] | None = None,
        startup_timeout: float = 10.0,
        **kwargs: Any,
    ) -> None:
        _reserved_arguments(kwargs)
        self.wireguard = WireGuardProxy(
            config,
            binary=wireproxy_binary,
            startup_timeout=startup_timeout,
        )
        self.wireguard.start()
        kwargs.setdefault("trust_env", False)
        try:
            super().__init__(proxy=self.wireguard.proxy_url, **kwargs)
        except Exception:
            self.wireguard.close()
            raise

    async def aclose(self) -> None:
        try:
            await super().aclose()
        finally:
            self.wireguard.close()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        try:
            await super().__aexit__(exc_type, exc_value, traceback)
        finally:
            self.wireguard.close()
