from __future__ import annotations

import ipaddress
import socket
from pathlib import Path

import pytest

from atlas.config import load_config

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def thaijo_dir() -> Path:
    return FIXTURES / "thaijo_md"


@pytest.fixture
def make_cfg(tmp_path):
    """cfg factory with all dirs inside tmp_path; usage: cfg = make_cfg(input_path, "thaijo_md")."""
    def _make(input_path: Path, fmt: str = "thaijo_md") -> dict:
        cfg = load_config(None)
        cfg["pipeline"].update(work_dir=str(tmp_path / "work"), output_dir=str(tmp_path / "out"),
                               state_dir=str(tmp_path / "state"))
        cfg["input"].update(path=str(input_path), format=fmt, workers=1)
        cfg["embedding"]["provider"] = "lite"           # CPU-only test embeddings (production default: local)
        return cfg
    return _make


def _loopback(address) -> bool:
    """True for a loopback address (127.0.0.0/8, ::1, IPv4-mapped loopback, "localhost")."""
    host = address[0] if isinstance(address, tuple) and address else address
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    host = str(host).split("%", 1)[0]                 # IPv6 zone id
    if host.lower() == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False                                   # any other host name is remote
    mapped = getattr(ip, "ipv4_mapped", None)
    return ip.is_loopback or bool(mapped and mapped.is_loopback)


def _guarded(real):
    def connect(self, address):
        if self.family != getattr(socket, "AF_UNIX", None) and not _loopback(address):
            raise OSError(f"network disabled in tests (ATLAS_OFFLINE): {address!r}")
        return real(self, address)
    return connect


@pytest.fixture(autouse=True, scope="session")
def _offline():
    """No test touches the network: OpenAlex calls raise OpenAlexUnavailable → taxonomy falls back, and
    every socket connect to a non-loopback address raises OSError (stub servers on 127.0.0.1 keep working).

    Session scope, so it is already active while module-scoped fixtures run the pipeline.
    """
    mp = pytest.MonkeyPatch()
    mp.setenv("ATLAS_OFFLINE", "1")
    mp.setattr(socket.socket, "connect", _guarded(socket.socket.connect))
    mp.setattr(socket.socket, "connect_ex", _guarded(socket.socket.connect_ex))
    yield
    mp.undo()
