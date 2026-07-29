# wg-httpx

Route one HTTPX client through WireGuard without creating a system network
interface or changing the machine's routing table.

`wg-httpx` starts an isolated [wireproxy](https://github.com/windtf/wireproxy)
process, exposes it only on a random `127.0.0.1` SOCKS5 port, and manages that
process for the lifetime of the HTTPX client.

## Usage

```python
import wg_httpx

with wg_httpx.Client("wg.conf") as client:
    response = client.get("https://api.ipify.org")
    print(response.text)
```

The async API has the same shape:

```python
import asyncio

import wg_httpx


async def main() -> None:
    async with wg_httpx.AsyncClient("wg.conf") as client:
        response = await client.get("https://api.ipify.org")
        print(response.text)


asyncio.run(main())
```

All normal HTTPX options except `proxy` and `transport` can be passed through:

```python
with wg_httpx.Client(
    "wg.conf",
    timeout=20,
    follow_redirects=True,
    http2=True,
) as client:
    ...
```

Raw WireGuard configuration text is also accepted:

```python
client = wg_httpx.Client(
    """
    [Interface]
    Address = 10.0.0.2/32
    PrivateKey = ...
    DNS = 10.0.0.1

    [Peer]
    PublicKey = ...
    Endpoint = vpn.example.com:51820
    AllowedIPs = 0.0.0.0/0
    """
)
```

Always close clients, preferably with `with` or `async with`. Closing the client
stops wireproxy and deletes its temporary copy of the private configuration.

## Binary handling

Published platform wheels are intended to include a matching wireproxy binary,
so end users do not start or install anything manually. During source
development, build it with:

```console
uv run python scripts/build_wireproxy.py
```

For custom builds, set `WG_HTTPX_WIREPROXY` or pass
`wireproxy_binary="/path/to/wireproxy"`.

Resolution order:

1. `wireproxy_binary`
2. `WG_HTTPX_WIREPROXY`
3. binary bundled in the package
4. `wireproxy` found on `PATH`

## Development

The project is managed by [uv](https://docs.astral.sh/uv/):

```console
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build --wheel
```

Unit tests do not require a real WireGuard peer. An end-to-end request requires a
working WireGuard configuration whose peer routes the requested destination.

## Releases

GitHub Actions builds platform wheels for:

- Windows x86-64 and ARM64
- Linux x86-64 and ARM64
- macOS Intel and Apple Silicon

Every pushed `v*` tag builds and tests all six wheels, then creates a GitHub
Release, attaches them, and publishes the same artifacts to PyPI using OIDC
Trusted Publishing. No PyPI API token is stored.

Before the first tag, configure the PyPI trusted publisher with:

- PyPI project: `wg-httpx`
- GitHub owner: `henrikxyz`
- GitHub repository: `wg-httpx`
- Workflow: `release.yml`
- Environment: `pypi`

Normal branch pushes and pull requests run Ruff and pytest through the CI
workflow.

## Security notes

- The SOCKS5 listener binds only to `127.0.0.1` and uses random per-client
  credentials.
- The supplied configuration is copied into a private temporary directory.
- Only the `[Interface]` and `[Peer]` data are imported. Extra listeners from an
  existing wireproxy configuration are not started.
- Environment proxy variables are disabled by default for managed clients.
- WireGuard private keys remain visible to the wireproxy subprocess and to users
  who already have permission to inspect the current process.

## License

The Python wrapper is MIT licensed. Bundled wireproxy binaries retain wireproxy's
ISC license; see `THIRD_PARTY_NOTICES.md`.
