import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compose import build_article_note, build_video_note  # noqa: E402
from transcript import Cue, VideoInfo  # noqa: E402

YT = "https://www.youtube.com/watch?v=abc123"


def article_req(**page):
    base = {
        "url": "https://example.com/rust-lifetimes",
        "title": "How Rust Lifetimes Work",
        "author": "Jane Smith",
        "published": "2026-03-14",
    }
    base.update(page)
    return {
        "kind": "article",
        "datePosition": "end",
        "clippedDate": "2026-11-05",
        "page": base,
        "bodyMarkdown": "<article Markdown>",
    }


def video_req():
    return {
        "kind": "video",
        "datePosition": "end",
        "clippedDate": "2026-11-05",
        "page": {
            "url": YT,
            "title": "Page Title",
            "author": "Page Channel",
            "published": "2026-01-01",
            "description": "Page description",
        },
        "bodyMarkdown": "fallback",
    }


def test_article_note_layout():
    stem, text = build_article_note(article_req())
    assert stem == "How Rust Lifetimes Work 2026-11-05"
    assert text == (
        "---\n"
        'title: "How Rust Lifetimes Work"\n'
        'source: "https://example.com/rust-lifetimes"\n'
        'author: "Jane Smith"\n'
        'published: "2026-03-14"\n'
        'clipped: "2026-11-05"\n'
        "tags:\n"
        "  - clipping\n"
        "---\n"
        "\n"
        "<article Markdown>\n"
    )


def test_article_note_omits_empty():
    _, text = build_article_note(article_req(author=None))
    assert "author:" not in text
    assert 'published: "2026-03-14"' in text


def test_video_note_layout():
    video = VideoInfo(
        title="Rust Lifetimes Explained",
        channel="Some Channel",
        published="2026-02-01",
        duration="1:02:15",
        description="<description text>",
        chapters=[{"start_time": 0, "title": "Introduction"}],
        cues=[Cue(0.0, "So today we're going to look at..."), Cue(42.0, "The first thing to understand is...")],
        transcript="manual",
    )
    stem, text, kind = build_video_note(video_req(), video, None)
    assert kind == "manual"
    assert stem == "Rust Lifetimes Explained 2026-11-05"
    assert text.startswith(
        "---\n"
        'title: "Rust Lifetimes Explained"\n'
        f'source: "{YT}"\n'
        'channel: "Some Channel"\n'
        'published: "2026-02-01"\n'
        'duration: "1:02:15"\n'
        'clipped: "2026-11-05"\n'
        'transcript: "manual"\n'
        "tags:\n"
        "  - clipping\n"
        "  - video\n"
        "---\n"
        "\n"
        "## Description\n\n<description text>\n\n## Transcript\n\n### Introduction\n\n"
        f"[0:00]({YT}&t=0) "
    )
    assert "[0:42]" in text
    assert text.endswith("\n")


def test_video_note_no_captions():
    video = VideoInfo("T", "C", None, None, "", None, [], "none")
    _, text, kind = build_video_note(video_req(), video, None)
    assert kind == "none"
    assert 'transcript: "none"' in text
    assert "No transcript available" in text
    assert "## Description" not in text


def test_video_note_fallback_reason():
    stem, text, kind = build_video_note(video_req(), None, "yt-dlp not installed")
    assert kind == "none"
    assert stem == "Page Title 2026-11-05"
    assert 'channel: "Page Channel"' in text
    assert "## Description\n\nPage description" in text
    assert "Transcript unavailable: yt-dlp not installed" in text


def test_clip_time_in_property_and_file_name():
    req = article_req()
    req["clippedTime"] = "2:05 pm"
    stem, text = build_article_note(req)
    assert stem == "How Rust Lifetimes Work 2026-11-05 2.05 pm"
    assert 'clipped: "2026-11-05 2:05 pm"\n' in text
    req["clippedTime"] = "14:05"
    req["datePosition"] = "start"
    stem, text = build_article_note(req)
    assert stem == "2026-11-05 14.05 How Rust Lifetimes Work"
    assert 'clipped: "2026-11-05 14:05"\n' in text


def test_clip_time_is_optional_but_checked():
    from compose import _validate
    req = article_req()
    req["destination"] = {"vaultPath": r"C:\Vault"}
    assert _validate(req) is None
    for bad in ["14:05/..", "2pm", 5, ""]:
        req["clippedTime"] = bad
        assert _validate(req) == "clippedTime must look like 14:05 or 2:05 pm", bad
