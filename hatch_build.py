"""Hatch hook that marks the wheel for the bundled wireproxy platform."""

from __future__ import annotations

import platform

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def wheel_platform_tag() -> str:
    """Map the Go binary platform to a Python wheel platform tag."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    tags = {
        ("windows", "amd64"): "win_amd64",
        ("windows", "x86_64"): "win_amd64",
        ("windows", "arm64"): "win_arm64",
        ("linux", "amd64"): "linux_x86_64",
        ("linux", "x86_64"): "linux_x86_64",
        ("linux", "arm64"): "linux_aarch64",
        ("linux", "aarch64"): "linux_aarch64",
        ("darwin", "amd64"): "macosx_11_0_x86_64",
        ("darwin", "x86_64"): "macosx_11_0_x86_64",
        ("darwin", "arm64"): "macosx_11_0_arm64",
        ("darwin", "aarch64"): "macosx_11_0_arm64",
    }
    try:
        return tags[(system, machine)]
    except KeyError as error:
        raise RuntimeError(f"Unsupported wheel platform: {system} {machine}") from error


class CustomBuildHook(BuildHookInterface):
    """Set a platform-specific, Python-ABI-independent wheel tag."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        if self.target_name == "wheel":
            build_data["pure_python"] = False
            build_data["tag"] = f"py3-none-{wheel_platform_tag()}"
