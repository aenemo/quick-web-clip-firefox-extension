import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

import clipper_host as host  # noqa: E402
import transcript  # noqa: E402
from transcript import Cue, Unsupported, VideoError, VideoInfo  # noqa: E402

YT = "https://www.youtube.com/watch?v=abc123"


@pytest.fixture
def logfile(tmp_path):
    path = tmp_path / "clipper.log"
    host.setup_logging(path)
    yield path
    for h in list(host.log.handlers):
        host.log.removeHandler(h)
        h.close()


def req(vault, kind="article", **over):
    r = {
        "v": 1,
        "action": "save",
        "kind": kind,
        "destination": {"vaultPath": str(vault), "subfolder": "Clippings"},
        "datePosition": "end",
        "clippedDate": "2026-11-05",
        "page": {"url": YT if kind == "video" else "https://example.com/a", "title": "A Title"},
        "bodyMarkdown": "body text",
    }
    r.update(over)
    return r


def video_info(transcript_kind="manual"):
    return VideoInfo("Vid", "Chan", "2026-02-01", "1:00", "desc", None,
                     [Cue(0.0, "Hello there.")], transcript_kind)


def test_save_article_writes_file(tmp_path):
    r = host.handle(req(tmp_path))
    assert r["ok"] is True
    assert r["kind"] == "article"
    assert r["transcript"] is None
    assert r["warning"] is None
    p = Path(r["path"])
    assert p.exists()
    assert p.name.endswith(" 2026-11-05.md")


def test_save_video_success(tmp_path, monkeypatch):
    monkeypatch.setattr(transcript, "fetch_video", lambda url, *a, **k: video_info())
    r = host.handle(req(tmp_path, "video"))
    assert r["ok"] is True
    assert r["kind"] == "video"
    assert r["transcript"] == "manual"
    assert r["warning"] is None


def test_save_video_unsupported_falls_back_to_article(tmp_path, monkeypatch):
    def boom(url, *a, **k):
        raise Unsupported()

    monkeypatch.setattr(transcript, "fetch_video", boom)
    r = host.handle(req(tmp_path, "video"))
    assert r["ok"] is True
    assert r["kind"] == "article"
    assert "body text" in Path(r["path"]).read_text(encoding="utf-8")


def test_save_video_error_saves_with_warning(tmp_path, monkeypatch):
    def boom(url, *a, **k):
        raise VideoError("timed out after 60 seconds")

    monkeypatch.setattr(transcript, "fetch_video", boom)
    r = host.handle(req(tmp_path, "video"))
    assert r["ok"] is True
    assert r["kind"] == "video"
    assert r["transcript"] == "none"
    assert r["warning"] == "Saved without transcript: timed out after 60 seconds"
    assert "Transcript unavailable: timed out after 60 seconds" in Path(r["path"]).read_text(encoding="utf-8")


def test_save_missing_vault(tmp_path):
    r = host.handle(req(tmp_path / "nope"))
    assert r["ok"] is False
    assert r["error"] == "vault_not_found"


def test_save_bad_request(tmp_path):
    r = req(tmp_path)
    del r["destination"]
    out = host.handle(r)
    assert out["ok"] is False
    assert out["error"] == "bad_request"


def test_log_has_no_body(tmp_path, logfile):
    vault = tmp_path / "vault"
    vault.mkdir()
    r = host.handle(req(vault, bodyMarkdown="SECRET-BODY"))
    assert r["ok"] is True
    for h in host.log.handlers:
        h.flush()
    content = logfile.read_text(encoding="utf-8")
    assert "save" in content
    assert "SECRET-BODY" not in content


@pytest.mark.parametrize("bad_page", ["x", [1]])
def test_save_non_dict_page_is_bad_request(tmp_path, bad_page):
    out = host.handle(req(tmp_path, page=bad_page))
    assert out["ok"] is False
    assert out["error"] == "bad_request"
