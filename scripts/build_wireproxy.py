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


def platform_tag() -> str:
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

    executable = "wireproxy.exe" if os.name == "nt" else "wireproxy"
    binary_root = ROOT / "src" / "wg_httpx" / "_bin"
    if binary_root.exists():
        shutil.rmtree(binary_root)
    destination = binary_root / platform_tag() / executable
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="wg-httpx-build-") as temp_dir:
        environment = os.environ.copy()
        environment["GOBIN"] = temp_dir
        environment["CGO_ENABLED"] = "0"
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

    if os.name != "nt":
        destination.chmod(0o755)
    print(f"Built {destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
