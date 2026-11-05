import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from notes import make_filename, render_frontmatter

RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


def test_make_filename_positions():
    assert make_filename("How Rust Lifetimes Work", "2026-11-05", "end") == "How Rust Lifetimes Work 2026-11-05"
    assert make_filename("How Rust Lifetimes Work", "2026-11-05", "start") == "2026-11-05 How Rust Lifetimes Work"
    assert make_filename("How Rust Lifetimes Work", "2026-11-05", "none") == "How Rust Lifetimes Work"


def test_make_filename_strips_illegal():
    title = 'a<b>c:d"e/f' + chr(92) + 'g|h?i*j'
    assert make_filename(title, "2026-11-05", "none") == "a b c d e f g h i j"
    assert make_filename("a\x00b\x1fc\x7fd", "2026-11-05", "none") == "abcd"


def test_make_filename_trims_to_100():
    stem = make_filename("a" * 300, "2026-11-05", "end")
    assert stem == "a" * 100 + " 2026-11-05"
    stem = make_filename("a" * 99 + " " + "b" * 50, "2026-11-05", "none")
    assert stem == "a" * 99
    stem = make_filename("a" * 99 + "." + "b" * 50, "2026-11-05", "none")
    assert stem == "a" * 99


@pytest.mark.parametrize("title", ["", "???", "CON", "nul.txt", "...", "   "])
def test_make_filename_degenerate_titles(title):
    stem = make_filename(title, "2026-11-05", "none")
    assert stem
    assert stem.split(".")[0].upper() not in RESERVED
    assert stem == stem.strip(" .")


def test_make_filename_degenerate_values():
    assert make_filename("CON", "2026-11-05", "none") == "CON_"
    assert make_filename("nul.txt", "2026-11-05", "none") == "nul_.txt"
    assert make_filename("???", "2026-11-05", "none") == "Untitled"
    assert make_filename("...", "2026-11-05", "none") == "Untitled"
    assert make_filename("   ", "2026-11-05", "end") == "Untitled 2026-11-05"


def test_make_filename_emoji_kept():
    assert make_filename("\U0001F600\U0001F680", "2026-11-05", "none") == "\U0001F600\U0001F680"


def test_frontmatter_quotes_and_order():
    fields = [("title", 'He said "hi": ok'), ("author", None), ("tags", ["clipping", "video"])]
    assert render_frontmatter(fields) == '---\ntitle: "He said \\"hi\\": ok"\ntags:\n  - clipping\n  - video\n---\n'


def test_frontmatter_newlines_and_unicode():
    out = render_frontmatter([("note", "line1\nline2 é")])
    assert out == '---\nnote: "line1\\nline2 é"\n---\n'


def test_frontmatter_backslash_and_empty():
    out = render_frontmatter([("p", "a" + chr(92) + "b"), ("e", "")])
    assert out == '---\np: "a' + chr(92) * 2 + 'b"\n---\n'
