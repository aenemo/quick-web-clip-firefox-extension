import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from notes import NoteError, safe_write


def test_safe_write_creates_subfolder_and_file(tmp_path):
    text = "line one\nline two\n"
    path = safe_write(str(tmp_path), r"Clippings\Web", "Note", text)
    assert os.path.isfile(path)
    data = open(path, "rb").read()
    assert b"\r\n" not in data
    assert data.decode("utf-8") == text
    assert os.path.dirname(path) == str(tmp_path.resolve() / "Clippings" / "Web")


def test_safe_write_numbers_duplicates(tmp_path):
    p1 = safe_write(str(tmp_path), "", "Note", "first\n")
    p2 = safe_write(str(tmp_path), "", "Note", "second\n")
    p3 = safe_write(str(tmp_path), "", "Note", "third\n")
    assert [os.path.basename(p) for p in (p1, p2, p3)] == [
        "Note.md",
        "Note (2).md",
        "Note (3).md",
    ]
    assert open(p1, encoding="utf-8").read() == "first\n"


@pytest.mark.parametrize("sub", [r"..\..\x", r"C:\Windows", r"\\server\share"])
def test_safe_write_rejects_escape(tmp_path, sub):
    with pytest.raises(NoteError) as exc:
        safe_write(str(tmp_path), sub, "Note", "x")
    assert exc.value.code == "outside_vault"
    assert exc.value.message == "Refused: subfolder points outside the vault"


def test_safe_write_missing_vault(tmp_path):
    missing = str(tmp_path / "nope")
    with pytest.raises(NoteError) as exc:
        safe_write(missing, "", "Note", "x")
    assert exc.value.code == "vault_not_found"
    assert exc.value.message == "Folder not found: " + missing


def test_safe_write_no_temp_left_on_failure(tmp_path, monkeypatch):
    def boom(src, dst):
        raise PermissionError("denied")

    monkeypatch.setattr(os, "rename", boom)
    with pytest.raises(NoteError) as exc:
        safe_write(str(tmp_path), "", "Note", "x")
    assert exc.value.code == "write_failed"
    assert exc.value.message.startswith("Could not write file: ")
    assert list(tmp_path.glob("*.tmp")) == []


def test_safe_write_unicode_and_spaces_path(tmp_path):
    vault = tmp_path / "OneDrive - Contoso" / "Vault Notes \u00e9"
    vault.mkdir(parents=True)
    path = safe_write(str(vault), "", "Caf\u00e9 note", "body\n")
    assert os.path.exists(path)
    assert path.startswith(str(vault.resolve()))


def test_safe_write_gives_up_after_99(tmp_path):
    (tmp_path / "Note.md").write_text("x")
    for i in range(2, 100):
        (tmp_path / f"Note ({i}).md").write_text("x")
    with pytest.raises(NoteError) as exc:
        safe_write(str(tmp_path), "", "Note", "y")
    assert exc.value.code == "write_failed"
    assert list(tmp_path.glob("*.tmp")) == []
