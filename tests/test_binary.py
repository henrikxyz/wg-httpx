from __future__ import annotations

from pathlib import Path

import pytest

from wg_httpx._binary import resolve_wireproxy
from wg_httpx._exceptions import BinaryNotFoundError


def test_explicit_binary_is_resolved(tmp_path: Path) -> None:
    binary = tmp_path / "wireproxy.exe"
    binary.touch()
    binary.chmod(0o755)

    assert resolve_wireproxy(binary) == binary.resolve()


def test_missing_explicit_binary_has_clear_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing-wireproxy"

    with pytest.raises(BinaryNotFoundError, match="binary argument"):
        resolve_wireproxy(missing)
