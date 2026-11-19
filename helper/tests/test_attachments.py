import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import clipper_host as host  # noqa: E402
from attachments import link_attachments, save_attachments  # noqa: E402

PNG = base64.b64encode(b"\x89PNG fake bytes").decode()
JPG = base64.b64encode(b"\xff\xd8 fake jpeg").decode()
AMS = "https://au-prod.asyncgw.teams.microsoft.com/v1/objects/0-sau-d1-0857ec2277af3f3b5876d79e5986896e/views/imgo"


def test_save_attachments_writes_files_and_links(tmp_path):
    items = [
        {"token": "qwc-attachment:0", "mime": "image/png", "data": PNG},
        {"token": "qwc-attachment:1", "mime": "image/jpeg", "data": JPG},
    ]
    links, written, skipped = save_attachments(tmp_path, "Chat (A) 2026-11-19", items)
    assert skipped == 0
    assert [p.name for p in written] == ["Chat (A) 2026-11-19 1.png", "Chat (A) 2026-11-19 2.jpg"]
    assert (tmp_path / "attachments" / "Chat (A) 2026-11-19 1.png").read_bytes() == b"\x89PNG fake bytes"
    assert links == {
        "qwc-attachment:0": "attachments/Chat%20%28A%29%202026-11-19%201.png",
        "qwc-attachment:1": "attachments/Chat%20%28A%29%202026-11-19%202.jpg",
    }


def test_save_attachments_never_overwrites(tmp_path):
    (tmp_path / "attachments").mkdir()
    (tmp_path / "attachments" / "Note 1.png").write_bytes(b"old")
    links, written, _ = save_attachments(tmp_path, "Note", [{"token": "qwc-attachment:0", "mime": "image/png", "data": PNG}])
    assert written[0].name == "Note 2.png"
    assert (tmp_path / "attachments" / "Note 1.png").read_bytes() == b"old"


def test_save_attachments_skips_invalid_items(tmp_path):
    items = [
        {"token": "qwc-attachment:0", "mime": "text/html", "data": PNG},
        {"token": "evil:0", "mime": "image/png", "data": PNG},
        {"token": "qwc-attachment:2", "mime": "image/png", "data": "not base64!"},
        {"token": "qwc-attachment:3", "mime": "image/png"},
        "junk",
        {"token": "qwc-attachment:5", "mime": "image/png", "data": PNG},
    ]
    links, written, skipped = save_attachments(tmp_path, "N", items)
    assert skipped == 5
    assert list(links) == ["qwc-attachment:5"]
    assert len(written) == 1


def test_save_attachments_ignores_non_list(tmp_path):
    assert save_attachments(tmp_path, "N", {"token": "x"}) == ({}, [], 0)
    assert not (tmp_path / "attachments").exists()


def test_link_attachments_replaces_whole_tokens_only():
    text = "![a](qwc-attachment:1) ![b](qwc-attachment:10) ![c](qwc-attachment:7)"
    out = link_attachments(text, {"qwc-attachment:1": "attachments/x%201.png", "qwc-attachment:10": "attachments/y.png"})
    assert out == "![a](attachments/x%201.png) ![b](attachments/y.png) ![c](qwc-attachment:7)"


def save_req(vault, **over):
    r = {
        "v": 1,
        "action": "save",
        "kind": "article",
        "destination": {"vaultPath": str(vault), "subfolder": "Clippings"},
        "datePosition": "end",
        "clippedDate": "2026-11-19",
        "page": {"url": "https://teams.cloud.microsoft/", "title": "Chat"},
        "bodyMarkdown": f'Look:\n\n[![image](qwc-attachment:0 "image")]({AMS})',
        "attachments": [{"token": "qwc-attachment:0", "mime": "image/jpeg", "data": JPG}],
    }
    r.update(over)
    return r


def test_save_embeds_image_linked_to_original(tmp_path):
    r = host.handle(save_req(tmp_path))
    assert r["ok"] is True
    assert r["warning"] is None
    note = Path(r["path"]).read_text(encoding="utf-8")
    assert f'[![image](attachments/Chat%202026-11-19%201.jpg "image")]({AMS})' in note
    assert (tmp_path / "Clippings" / "attachments" / "Chat 2026-11-19 1.jpg").read_bytes() == b"\xff\xd8 fake jpeg"


def test_save_warns_when_an_image_is_skipped(tmp_path):
    bad = [{"token": "qwc-attachment:0", "mime": "image/jpeg", "data": "%%%"}]
    r = host.handle(save_req(tmp_path, attachments=bad))
    assert r["ok"] is True
    assert r["warning"] == "Saved, but 1 image(s) could not be saved"


def test_save_without_attachments_creates_no_folder(tmp_path):
    r = host.handle(save_req(tmp_path, attachments=[]))
    assert r["ok"] is True
    assert not (tmp_path / "Clippings" / "attachments").exists()


def test_failed_note_write_removes_images(tmp_path, monkeypatch):
    import compose
    from notes import NoteError

    def boom(*a, **k):
        raise NoteError("write_failed", "Could not write file: disk full")

    monkeypatch.setattr(compose, "safe_write", boom)
    r = host.handle(save_req(tmp_path))
    assert r["ok"] is False
    assert list((tmp_path / "Clippings" / "attachments").iterdir()) == []
