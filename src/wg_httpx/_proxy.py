"""Lifecycle management for an isolated wireproxy process."""

from __future__ import annotations

import atexit
import os
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from types import TracebackType
from typing import IO

from ._binary import resolve_wireproxy
from ._exceptions import ConfigError, StartupError

ConfigInput = str | os.PathLike[str]


class WireGuardProxy:
    """Run wireproxy on a private, randomly selected localhost SOCKS5 port."""

    def __init__(
        self,
        config: ConfigInput,
        *,
        binary: str | os.PathLike[str] | None = None,
        startup_timeout: float = 10.0,
    ) -> None:
        if startup_timeout <= 0:
            raise ValueError("startup_timeout must be greater than zero")
        self._config = config
        self._binary_arg = binary
        self._startup_timeout = startup_timeout
        self._process: subprocess.Popen[str] | None = None
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self._stderr_lines: deque[str] = deque(maxlen=50)
        self._stderr_thread: threading.Thread | None = None
        self._port: int | None = None
        self._username: str | None = None
        self._password: str | None = None
        self._registered_at_exit = False

    @property
    def started(self) -> bool:
        """Whether the managed process is currently alive."""
        return self._process is not None and self._process.poll() is None

    @property
    def port(self) -> int:
        """The local SOCKS5 port, available after :meth:`start`."""
        if self._port is None:
            raise RuntimeError("WireGuardProxy has not been started")
        return self._port

    @property
    def proxy_url(self) -> str:
        """The local SOCKS5 URL consumed by HTTPX."""
        if self._username is None or self._password is None:
            raise RuntimeError("WireGuardProxy has not been started")
        return f"socks5://{self._username}:{self._password}@127.0.0.1:{self.port}"

    def start(self) -> WireGuardProxy:
        """Start wireproxy and wait until its SOCKS5 listener accepts connections."""
        if self.started:
            return self
        if self._process is not None:
            self.close()

        binary = resolve_wireproxy(self._binary_arg)
        self._stderr_lines.clear()
        self._temp_dir = tempfile.TemporaryDirectory(prefix="wg-httpx-")
        temp_path = Path(self._temp_dir.name)

        try:
            wg_config = temp_path / "wireguard.conf"
            wg_config.write_text(self._read_config(), encoding="utf-8")
            self._make_private(wg_config)

            self._port = self._pick_port()
            self._username = secrets.token_urlsafe(18)
            self._password = secrets.token_urlsafe(24)
            proxy_config = temp_path / "wireproxy.conf"
            proxy_config.write_text(
                f"WGConfig = {wg_config}\n\n"
                "[Socks5]\n"
                f"BindAddress = 127.0.0.1:{self._port}\n"
                f"Username = {self._username}\n"
                f"Password = {self._password}\n",
                encoding="utf-8",
            )
            self._make_private(proxy_config)
            self._spawn(binary, proxy_config)
            self._wait_until_ready()
        except Exception:
            self.close()
            raise

        atexit.register(self.close)
        self._registered_at_exit = True
        return self

    def close(self) -> None:
        """Stop wireproxy and remove all temporary configuration files."""
        process, self._process = self._process, None
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            except OSError:
                pass

        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=1)
            self._stderr_thread = None

        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None

        self._port = None
        self._username = None
        self._password = None
        if self._registered_at_exit:
            atexit.unregister(self.close)
            self._registered_at_exit = False

    def __enter__(self) -> WireGuardProxy:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _read_config(self) -> str:
        if isinstance(self._config, os.PathLike):
            return self._read_config_path(Path(self._config))

        value = self._config
        if "\n" in value or "\r" in value or value.lstrip().startswith("["):
            if not value.strip():
                raise ConfigError("WireGuard configuration is empty")
            return value
        return self._read_config_path(Path(value))

    @staticmethod
    def _read_config_path(path: Path) -> str:
        resolved = path.expanduser().resolve()
        if not resolved.is_file():
            raise ConfigError(f"WireGuard configuration file does not exist: {resolved}")
        try:
            value = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ConfigError(f"Cannot read WireGuard configuration: {resolved}") from error
        if not value.strip():
            raise ConfigError(f"WireGuard configuration is empty: {resolved}")
        return value

    @staticmethod
    def _make_private(path: Path) -> None:
        if os.name != "nt":
            path.chmod(0o600)

    @staticmethod
    def _pick_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            return int(listener.getsockname()[1])

    def _spawn(self, binary: Path, config: Path) -> None:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self._process = subprocess.Popen(
                [str(binary), "--config", str(config), "--silent"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creation_flags,
            )
        except OSError as error:
            raise StartupError(f"Could not start wireproxy: {error}") from error

        assert self._process.stderr is not None
        self._stderr_thread = threading.Thread(
            target=self._collect_stderr,
            args=(self._process.stderr,),
            name="wg-httpx-wireproxy-stderr",
            daemon=True,
        )
        self._stderr_thread.start()

    def _collect_stderr(self, stream: IO[str]) -> None:
        try:
            for line in stream:
                self._stderr_lines.append(line.rstrip())
        finally:
            stream.close()

    def _wait_until_ready(self) -> None:
        assert self._process is not None
        deadline = time.monotonic() + self._startup_timeout
        while time.monotonic() < deadline:
            return_code = self._process.poll()
            if return_code is not None:
                details = self._error_details()
                raise StartupError(f"wireproxy exited during startup ({return_code}).{details}")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    return
            except OSError:
                time.sleep(0.05)

        details = self._error_details()
        raise StartupError(
            f"wireproxy did not open its SOCKS5 port within {self._startup_timeout:g}s.{details}"
        )

    def _error_details(self) -> str:
        if not self._stderr_lines:
            return ""
        return "\nwireproxy output:\n" + "\n".join(self._stderr_lines)
