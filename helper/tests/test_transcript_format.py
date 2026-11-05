import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from transcript import (
    Cue,
    Section,
    build_paragraphs,
    format_ts,
    parse_captions,
    render_transcript,
    timestamp_link,
)

FIX = Path(__file__).parent / "fixtures"
YT = "https://www.youtube.com/watch?v=abc123"


def load(name):
    return (FIX / name).read_text(encoding="utf-8")


def has_adjacent_repeat(text, min_len=3):
    words = text.split()
    for size in range(min_len, len(words) // 2 + 1):
        for i in range(len(words) - 2 * size + 1):
            if words[i:i + size] == words[i + size:i + 2 * size]:
                return True
    return False


def test_format_ts():
    assert format_ts(0) == "0:00"
    assert format_ts(754) == "12:34"
    assert format_ts(3735) == "1:02:15"


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=abc123&list=PL1",
    "https://youtu.be/abc123",
    "https://www.youtube.com/shorts/abc123",
    "https://www.youtube.com/live/abc123",
    "https://m.youtube.com/watch?v=abc123",
])
def test_timestamp_link_youtube_variants(url):
    assert timestamp_link(url, 42) == "https://www.youtube.com/watch?v=abc123&t=42"


def test_timestamp_link_vimeo_and_other():
    assert timestamp_link("https://vimeo.com/123", 42) == "https://vimeo.com/123#t=42s"
    assert timestamp_link("https://vimeo.com/123#t=5s", 42) == "https://vimeo.com/123#t=42s"
    assert timestamp_link("https://example.com/v", 42) is None


def test_parse_json3_manual():
    events = json.loads(load("manual.json3"))["events"]
    expected = [e for e in events if "".join(s["utf8"] for s in e.get("segs", [])).strip()]
    cues = parse_captions(load("manual.json3"), "json3")
    assert len(cues) == len(expected) == 10
    assert cues[0] == Cue(0.0, "Welcome to the channel.")
    assert cues[2].text == "First, you will need a flat patch of ground, some timber and a few hours."


def test_parse_vtt_manual():
    cues = parse_captions(load("manual.vtt"), "vtt")
    assert len(cues) == 10
    assert cues[0] == Cue(0.0, "Welcome to the channel.")
    assert cues[2].text == "First, you will need a flat patch of ground, some timber and a few hours."
    assert cues[1].start == 4.2


@pytest.mark.parametrize("name,fmt", [("auto_rolling.json3", "json3"), ("auto_rolling.vtt", "vtt")])
def test_parse_auto_removes_rolling_duplicates(name, fmt):
    cues = parse_captions(load(name), fmt)
    assert cues[0] == Cue(0.0, "welcome to the channel")
    joined = " ".join(c.text for c in cues)
    assert "<" not in joined
    assert not has_adjacent_repeat(joined)
    assert joined.startswith("welcome to the channel today we are building a small garden shed")
    assert all(c.text for c in cues)


def make_cues(n, step=10.0, punct_every=None):
    cues = []
    for i in range(n):
        text = f"word{i}"
        if punct_every and i % punct_every == punct_every - 1:
            text += "."
        cues.append(Cue(i * step, text))
    return cues


def test_paragraphs_respect_chapters():
    cues = make_cues(20, step=10.0, punct_every=3)
    chapters = [
        {"start_time": 0, "end_time": 100, "title": "Intro"},
        {"start_time": 100, "end_time": 200, "title": "Main"},
    ]
    sections = build_paragraphs(cues, chapters)
    assert [s.title for s in sections] == ["Intro", "Main"]
    assert all(start >= 100 for start, _ in sections[1].paragraphs)
    assert all(start < 100 for start, _ in sections[0].paragraphs)


def test_empty_chapter_left_out_and_early_cues_go_to_first():
    cues = [Cue(2.0, "a"), Cue(150.0, "b")]
    chapters = [
        {"start_time": 10, "end_time": 100, "title": "One"},
        {"start_time": 100, "end_time": 120, "title": "Empty"},
        {"start_time": 120, "end_time": 200, "title": "Three"},
    ]
    sections = build_paragraphs(cues, chapters)
    assert [s.title for s in sections] == ["One", "Three"]
    assert sections[0].paragraphs == [(2, "a")]


def test_paragraphs_no_chapters_single_section():
    cues = make_cues(40, step=10.0)
    sections = build_paragraphs(cues, None)
    assert len(sections) == 1 and sections[0].title is None
    starts = [s for s, _ in sections[0].paragraphs]
    assert all(b - a <= 60 for a, b in zip(starts, starts[1:]))
    # no punctuation anywhere, so the 45 s rule applies: break at the first cue at or past 45 s
    assert starts[:3] == [0, 50, 100]


def test_paragraph_breaks_on_sentence_end_after_30s():
    cues = [Cue(0, "a"), Cue(10, "b."), Cue(20, "c"), Cue(31, "d."), Cue(40, "e")]
    paras = build_paragraphs(cues, None)[0].paragraphs
    assert [s for s, _ in paras] == [0, 40]
    assert paras[0][1] == "a b. c d."


def test_paragraph_hard_cap_60s_with_punctuation_elsewhere():
    cues = [Cue(0, "a"), Cue(30, "b"), Cue(60, "c"), Cue(70, "d.")]
    paras = build_paragraphs(cues, None)[0].paragraphs
    assert [s for s, _ in paras] == [0, 60]


def test_render_with_chapters():
    sections = [
        Section("Intro", [(0, "hello there."), (35, "second para.")]),
        Section("Next", [(100, "third.")]),
    ]
    out = render_transcript(sections, YT)
    assert out.startswith(f"### Intro\n\n[0:00]({YT}&t=0) hello there.\n\n[0:35]({YT}&t=35) second para.")
    assert "\n\n### Next\n\n[1:40](" in out


def test_render_other_site_plain_timestamps():
    sections = [Section(None, [(0, "hello."), (754, "later.")])]
    out = render_transcript(sections, "https://example.com/v")
    assert out == "0:00 hello.\n\n12:34 later."
    assert "](" not in out
