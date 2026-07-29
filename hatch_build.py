"""Hatch hook that marks the wheel for the bundled wireproxy platform."""

from __future__ import annotations

import os
import platform

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

BUILD_PLATFORM_ENV = "WG_HTTPX_BUILD_PLATFORM"


def wheel_platform_tag() -> str:
    """Map the Go binary platform to a Python wheel platform tag."""
    tags = {
        "windows-amd64": "win_amd64",
        "windows-arm64": "win_arm64",
        "linux-amd64": "manylinux_2_17_x86_64",
        "linux-arm64": "manylinux_2_17_aarch64",
        "macos-amd64": "macosx_11_0_x86_64",
        "macos-arm64": "macosx_11_0_arm64",
    }
    target = os.environ.get(BUILD_PLATFORM_ENV)
    if target is None:
        systems = {"windows": "windows", "linux": "linux", "darwin": "macos"}
        machines = {
            "amd64": "amd64",
            "x86_64": "amd64",
            "arm64": "arm64",
            "aarch64": "arm64",
        }
        system = systems.get(platform.system().lower())
        machine = machines.get(platform.machine().lower())
        target = f"{system}-{machine}" if system and machine else ""
    try:
        return tags[target]
    except KeyError as error:
        raise RuntimeError(f"Unsupported wheel platform: {target or 'unknown'}") from error


class CustomBuildHook(BuildHookInterface):
    """Set a platform-specific, Python-ABI-independent wheel tag."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        if self.target_name == "wheel":
            build_data["pure_python"] = False
            build_data["tag"] = f"py3-none-{wheel_platform_tag()}"
