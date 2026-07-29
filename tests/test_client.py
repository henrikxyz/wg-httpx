from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pytest

import wg_httpx
from wg_httpx import _client


class FakeProxy:
    instances: ClassVar[list[FakeProxy]] = []

    def __init__(self, config: object, **kwargs: Any) -> None:
        self.config = config
        self.kwargs = kwargs
        self.started = False
        self.closed = False
        self.instances.append(self)

    @property
    def proxy_url(self) -> str:
        return "socks5://127.0.0.1:32123"

    def start(self) -> FakeProxy:
        self.started = True
        return self

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def fake_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeProxy.instances.clear()
    monkeypatch.setattr(_client, "WireGuardProxy", FakeProxy)


def test_client_starts_and_closes_wireproxy(tmp_path: Path) -> None:
    with wg_httpx.Client(tmp_path / "wg.conf", timeout=12) as client:
        proxy = FakeProxy.instances[-1]
        assert proxy.started
        assert not proxy.closed
        assert client.timeout.connect == 12

    assert proxy.closed
    assert client.is_closed


@pytest.mark.asyncio
async def test_async_client_starts_and_closes_wireproxy(tmp_path: Path) -> None:
    async with wg_httpx.AsyncClient(tmp_path / "wg.conf") as client:
        proxy = FakeProxy.instances[-1]
        assert proxy.started
        assert not proxy.closed

    assert proxy.closed
    assert client.is_closed


@pytest.mark.parametrize("argument", ["proxy", "transport"])
def test_managed_httpx_arguments_are_rejected(tmp_path: Path, argument: str) -> None:
    with pytest.raises(TypeError, match=argument):
        wg_httpx.Client(tmp_path / "wg.conf", **{argument: None})
