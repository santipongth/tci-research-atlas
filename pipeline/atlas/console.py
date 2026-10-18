"""UTF-8 console output for every entry point (Windows consoles and redirects default to cp1252)."""
from __future__ import annotations

import sys


def use_utf8_stdio(*streams) -> None:
    """Switch the given text streams (default: stdout and stderr) to UTF-8.

    Streams without `reconfigure` (StringIO, pytest capture, None) are left alone.
    """
    for stream in streams or (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
