from __future__ import annotations

import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from wg_httpx._binary import platform_tag as runtime_platform_tag

ROOT = Path(__file__).resolve().parents[1]
wheel_platform_tag = cast(
    Callable[[], str],
    runpy.run_path(str(ROOT / "hatch_build.py"))["wheel_platform_tag"],
)
build_platform_tag = cast(
    Callable[[], str],
    runpy.run_path(str(ROOT / "scripts" / "build_wireproxy.py"))["platform_tag"],
)


@pytest.mark.parametrize(
    ("target", "wheel_tag"),
    [
        ("windows-amd64", "win_amd64"),
        ("windows-arm64", "win_arm64"),
        ("linux-amd64", "manylinux_2_17_x86_64"),
        ("linux-arm64", "manylinux_2_17_aarch64"),
        ("macos-amd64", "macosx_11_0_x86_64"),
        ("macos-arm64", "macosx_11_0_arm64"),
    ],
)
def test_explicit_build_platform(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    wheel_tag: str,
) -> None:
    monkeypatch.setenv("WG_HTTPX_BUILD_PLATFORM", target)

    assert build_platform_tag() == target
    assert runtime_platform_tag() == target
    assert wheel_platform_tag() == wheel_tag
