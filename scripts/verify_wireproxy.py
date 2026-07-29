"""Verify that exactly one native wireproxy binary is packaged and runnable."""

from __future__ import annotations

import subprocess

from wg_httpx._binary import resolve_wireproxy

EXPECTED_VERSION = "1.1.2"


def main() -> None:
    binary = resolve_wireproxy()
    output = subprocess.check_output(
        [binary, "--version"],
        text=True,
        encoding="utf-8",
        errors="replace",
    ).strip()
    expected = f"wireproxy, version {EXPECTED_VERSION}"
    if output != expected:
        raise SystemExit(f"Unexpected wireproxy version: {output!r}; expected {expected!r}")
    print(f"Verified {binary}: {output}")


if __name__ == "__main__":
    main()
