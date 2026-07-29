"""Build the pinned wireproxy executable into the Python package."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

WIREPROXY_VERSION = "v1.1.2"
WIREPROXY_PACKAGE = "github.com/windtf/wireproxy/cmd/wireproxy"
ROOT = Path(__file__).resolve().parents[1]
BUILD_PLATFORM_ENV = "WG_HTTPX_BUILD_PLATFORM"


def platform_tag() -> str:
    configured = os.environ.get(BUILD_PLATFORM_ENV)
    supported = {
        "windows-amd64",
        "windows-arm64",
        "linux-amd64",
        "linux-arm64",
        "macos-amd64",
        "macos-arm64",
    }
    if configured:
        if configured not in supported:
            raise SystemExit(f"Unsupported {BUILD_PLATFORM_ENV}: {configured}")
        return configured

    systems = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}
    machines = {
        "AMD64": "amd64",
        "x86_64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    try:
        return f"{systems[platform.system()]}-{machines[platform.machine()]}"
    except KeyError as error:
        raise SystemExit(
            f"Unsupported build platform: {platform.system()} {platform.machine()}"
        ) from error


def main() -> None:
    if shutil.which("go") is None:
        raise SystemExit("Go is required to build wireproxy")

    target = platform_tag()
    go_targets = {
        "windows-amd64": ("windows", "amd64"),
        "windows-arm64": ("windows", "arm64"),
        "linux-amd64": ("linux", "amd64"),
        "linux-arm64": ("linux", "arm64"),
        "macos-amd64": ("darwin", "amd64"),
        "macos-arm64": ("darwin", "arm64"),
    }
    goos, goarch = go_targets[target]
    executable = "wireproxy.exe" if goos == "windows" else "wireproxy"
    binary_root = ROOT / "src" / "wg_httpx" / "_bin"
    if binary_root.exists():
        shutil.rmtree(binary_root)
    destination = binary_root / target / executable
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="wg-httpx-build-") as temp_dir:
        environment = os.environ.copy()
        environment["GOBIN"] = temp_dir
        environment["CGO_ENABLED"] = "0"
        environment["GOOS"] = goos
        environment["GOARCH"] = goarch
        subprocess.run(
            [
                "go",
                "install",
                "-trimpath",
                "-ldflags",
                f"-s -w -X main.version={WIREPROXY_VERSION.removeprefix('v')}",
                f"{WIREPROXY_PACKAGE}@{WIREPROXY_VERSION}",
            ],
            check=True,
            env=environment,
        )
        shutil.copy2(Path(temp_dir) / executable, destination)

    if goos != "windows":
        destination.chmod(0o755)
    print(f"Built {destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
