import io

import pytest

from atlas.console import use_utf8_stdio

TEXT = "\N{LESS-THAN OR EQUAL TO} \N{THAI CHARACTER KO KAI}"


def test_use_utf8_stdio_switches_a_cp1252_stream_to_utf8():
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252")
    with pytest.raises(UnicodeEncodeError):
        stream.write(TEXT)
        stream.flush()
    use_utf8_stdio(stream)
    assert stream.encoding.lower().replace("-", "") == "utf8"
    stream.write(TEXT)
    stream.flush()
    assert raw.getvalue().decode("utf-8").endswith(TEXT)


def test_use_utf8_stdio_ignores_streams_that_cannot_be_reconfigured():
    use_utf8_stdio(io.StringIO(), None)             # no reconfigure() / not a stream: no error


def test_pipeline_main_reconfigures_stdio(monkeypatch):
    import atlas.pipeline as pl

    calls = []
    monkeypatch.setattr(pl, "use_utf8_stdio", lambda *s: calls.append(s))
    with pytest.raises(SystemExit):
        pl.main(["--steps", "no-such-step"])
    assert calls == [()]
