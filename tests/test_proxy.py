from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from wg_httpx import ConfigError, WireGuardProxy

SAMPLE_CONFIG = """\
[Interface]
Address = 10.0.0.2/32
PrivateKey = private-key
DNS = 10.0.0.1

[Peer]
PublicKey = public-key
Endpoint = 192.0.2.1:51820
AllowedIPs = 0.0.0.0/0
"""


class FakeProcess:
    def __init__(self) -> None:
        self.return_code: int | None = None
        self.terminated = False

    def poll(self) -> int | None:
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True
        self.return_code = 0

    def wait(self, timeout: float | None = None) -> int:
        return self.return_code or 0

    def kill(self) -> None:
        self.return_code = -9


def install_fake_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    binary = tmp_path / "wireproxy.exe"
    binary.touch()
    captured: dict[str, Any] = {}

    def spawn(proxy: WireGuardProxy, _binary: Path, config: Path) -> None:
        captured["proxy_config"] = config.read_text(encoding="utf-8")
        captured["wg_config"] = (config.parent / "wireguard.conf").read_text(encoding="utf-8")
        process = FakeProcess()
        captured["process"] = process
        proxy._process = process

    monkeypatch.setattr(WireGuardProxy, "_spawn", spawn)
    monkeypatch.setattr(WireGuardProxy, "_wait_until_ready", lambda _proxy: None)
    captured["binary"] = binary
    return captured


def test_proxy_generates_an_isolated_random_listener(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured = install_fake_process(monkeypatch, tmp_path)
    config = tmp_path / "wg.conf"
    config.write_text(SAMPLE_CONFIG, encoding="utf-8")
    proxy = WireGuardProxy(config, binary=captured["binary"])

    proxy.start()

    assert proxy.started
    assert proxy.proxy_url.startswith("socks5://")
    assert "@127.0.0.1:" in proxy.proxy_url
    assert captured["wg_config"] == SAMPLE_CONFIG
    assert captured["proxy_config"].count("[Socks5]") == 1
    assert "BindAddress = 127.0.0.1:" in captured["proxy_config"]
    assert "Username = " in captured["proxy_config"]
    assert "Password = " in captured["proxy_config"]

    proxy.close()
    assert captured["process"].terminated
    assert not proxy.started


def test_raw_config_is_supported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured = install_fake_process(monkeypatch, tmp_path)

    with WireGuardProxy(SAMPLE_CONFIG, binary=captured["binary"]):
        assert captured["wg_config"] == SAMPLE_CONFIG


def test_missing_config_is_rejected(tmp_path: Path) -> None:
    binary = tmp_path / "wireproxy.exe"
    binary.touch()
    proxy = WireGuardProxy(tmp_path / "missing.conf", binary=binary)

    with pytest.raises(ConfigError, match="does not exist"):
        proxy.start()

    assert not proxy.started
