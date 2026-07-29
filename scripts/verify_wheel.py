"""Verify that a built wheel contains the expected native wireproxy binary."""

from __future__ import annotations

import os
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BUILD_PLATFORM_ENV = "WG_HTTPX_BUILD_PLATFORM"
MINIMUM_BINARY_SIZE = 1_000_000


def main() -> None:
    target = os.environ.get(BUILD_PLATFORM_ENV)
    if not target:
        raise SystemExit(f"{BUILD_PLATFORM_ENV} must identify the wheel target")

    wheels = list((ROOT / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected exactly one wheel, found {len(wheels)}")

    executable = "wireproxy.exe" if target.startswith("windows-") else "wireproxy"
    expected = f"wg_httpx/_bin/{target}/{executable}"
    with ZipFile(wheels[0]) as archive:
        binaries = [
            info for info in archive.infolist() if info.filename.startswith("wg_httpx/_bin/")
        ]

    if [info.filename for info in binaries] != [expected]:
        raise SystemExit(
            f"Expected only {expected!r} in the wheel, found "
            f"{[info.filename for info in binaries]!r}"
        )
    if binaries[0].file_size < MINIMUM_BINARY_SIZE:
        raise SystemExit(
            f"Bundled wireproxy is unexpectedly small: {binaries[0].file_size:,} bytes"
        )

    print(f"Verified {wheels[0].name}: {expected} ({binaries[0].file_size:,} bytes)")


if __name__ == "__main__":
    main()
