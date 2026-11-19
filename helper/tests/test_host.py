import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import clipper_host as host  # noqa: E402


def frame(obj):
    buf = io.BytesIO()
    host.write_message(buf, obj)
    return buf.getvalue()


def test_roundtrip_frame():
    obj = {"v": 1, "text": "é", "path": "C:" + chr(92) + "x"}
    buf = io.BytesIO()
    host.write_message(buf, obj)
    buf.seek(0)
    assert host.read_message(buf) == obj


def test_read_eof_returns_none():
    assert host.read_message(io.BytesIO(b"")) is None


def test_ping_reports_version():
    r = host.handle({"v": 1, "action": "ping"})
    assert r["ok"] is True
    assert r["version"] == "1.1.1"


def test_unknown_action_bad_request():
    r = host.handle({"v": 1, "action": "nope"})
    assert r["ok"] is False and r["error"] == "bad_request"


def test_wrong_version_bad_request():
    r = host.handle({"v": 2, "action": "ping"})
    assert r["ok"] is False and r["error"] == "bad_request"


def test_handler_exception_is_internal(monkeypatch):
    def boom(msg):
        raise RuntimeError("boom")

    monkeypatch.setitem(host.ACTIONS, "ping", boom)
    r = host.handle({"v": 1, "action": "ping"})
    assert r["ok"] is False and r["error"] == "internal"


def test_handler_print_does_not_corrupt_stdout(monkeypatch):
    def noisy(msg):
        print("noise")
        return {"ok": True}

    monkeypatch.setitem(host.ACTIONS, "ping", noisy)
    stdin = io.BytesIO(frame({"v": 1, "action": "ping"}))
    out = io.BytesIO()
    host.serve(stdin, out)
    out.seek(0)
    assert host.read_message(out) == {"ok": True}
    assert out.read() == b""
