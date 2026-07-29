"""Locate the wireproxy executable used by the package."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from ._exceptions import BinaryNotFoundError

_ENV_NAME = "WG_HTTPX_WIREPROXY"


def platform_tag() -> str:
    """Return the package binary directory tag for this interpreter."""
    systems = {
        "windows": "windows",
        "linux": "linux",
        "darwin": "macos",
    }
    machines = {
        "amd64": "amd64",
        "x86_64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    system = systems.get(platform.system().lower())
    machine = machines.get(platform.machine().lower())
    if system is None or machine is None:
        raise BinaryNotFoundError(
            f"Unsupported platform: {platform.system()} {platform.machine()}. "
            f"Set {_ENV_NAME} to a compatible wireproxy executable."
        )
    return f"{system}-{machine}"


def _validate_binary(path: Path, source: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise BinaryNotFoundError(f"wireproxy from {source} is not a file: {resolved}")
    if os.name != "nt" and not os.access(resolved, os.X_OK):
        raise BinaryNotFoundError(f"wireproxy from {source} is not executable: {resolved}")
    return resolved


def resolve_wireproxy(binary: str | os.PathLike[str] | None = None) -> Path:
    """Resolve an explicit, packaged, environment, or PATH wireproxy executable."""
    if binary is not None:
        return _validate_binary(Path(binary), "the binary argument")

    configured = os.environ.get(_ENV_NAME)
    if configured:
        return _validate_binary(Path(configured), _ENV_NAME)

    executable = "wireproxy.exe" if os.name == "nt" else "wireproxy"
    packaged = Path(__file__).parent / "_bin" / platform_tag() / executable
    if packaged.is_file():
        return _validate_binary(packaged, "the wg-httpx package")

    found = shutil.which("wireproxy")
    if found:
        return _validate_binary(Path(found), "PATH")

    raise BinaryNotFoundError(
        f"No wireproxy executable is available for {platform_tag()}. "
        f"Install a platform wheel that bundles wireproxy or set {_ENV_NAME}."
    )
