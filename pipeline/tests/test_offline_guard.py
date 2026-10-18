"""The session-wide offline guard (conftest._offline): no test reaches the network; loopback still works."""
import socket
import urllib.request

import pytest


def test_real_network_is_blocked():
    with pytest.raises(OSError):
        urllib.request.urlopen("http://example.com", timeout=5)
    with pytest.raises(OSError, match="network disabled in tests"):
        urllib.request.urlopen("http://192.0.2.1/", timeout=5)          # TEST-NET-1 literal: no DNS involved
    with socket.socket() as s, pytest.raises(OSError, match="network disabled in tests"):
        s.connect_ex(("192.0.2.1", 80))


def test_loopback_still_works():
    with socket.create_server(("127.0.0.1", 0)) as srv:
        port = srv.getsockname()[1]
        for host in ("127.0.0.1", "localhost"):
            with socket.create_connection((host, port), timeout=5):
                pass
