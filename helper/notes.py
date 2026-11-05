"""File name cleaning and YAML frontmatter for clipped notes."""
import os
import re
import tempfile
from pathlib import Path, PureWindowsPath

_ILLEGAL = re.compile("[<>:\"/" + re.escape(chr(92)) + "|?*]")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")
_RESERVED = {"CON", "PRN", "AUX", "NUL"}
_RESERVED |= {f"COM{i}" for i in range(1, 10)}
_RESERVED |= {f"LPT{i}" for i in range(1, 10)}
_MAX_TITLE = 100


def _clean_title(title: str) -> str:
    title = _CONTROL.sub(" ", title or "")
    title = _ILLEGAL.sub(" ", title)
    title = _WHITESPACE.sub(" ", title).strip()
    title = title[:_MAX_TITLE].rstrip(" .")
    return title or "Untitled"


def _avoid_reserved(stem: str) -> str:
    base, dot, rest = stem.partition(".")
    if base.upper() in _RESERVED:
        return base + "_" + dot + rest
    return stem


def make_filename(title: str, date: str, position: str) -> str:
    """Return the note file stem (no .md) for a title, date and date position."""
    clean = _clean_title(title)
    if position == "start":
        stem = f"{date} {clean}"
    elif position == "none":
        stem = clean
    else:
        stem = f"{clean} {date}"
    return _avoid_reserved(stem)


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    return f'"{escaped}"'


def render_frontmatter(fields: list[tuple[str, object]]) -> str:
    """Render a YAML frontmatter block, skipping None and empty values."""
    lines = ["---"]
    for key, value in fields:
        if value is None or value == "":
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"{key}: {_quote(str(value))}")
    lines.append("---")
    return "\n".join(lines) + "\n"


class NoteError(Exception):
    """A note could not be saved. code is a stable machine-readable reason."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


_MAX_DUPLICATES = 99


def safe_write(vault: str, subfolder: str, stem: str, text: str) -> str:
    """Write text to <vault>/<subfolder>/<stem>.md without overwriting.

    Returns the absolute path written. Duplicates get " (2)" to " (99)".
    """
    vault_path = Path(vault)
    if not vault_path.is_dir():
        raise NoteError("vault_not_found", f"Folder not found: {vault}")
    vault_resolved = vault_path.resolve()

    outside = NoteError("outside_vault", "Refused: subfolder points outside the vault")
    if PureWindowsPath(subfolder).anchor:
        raise outside
    target = (vault_resolved / subfolder).resolve()
    if not target.is_relative_to(vault_resolved):
        raise outside

    tmp_name = None
    try:
        target.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n",
            dir=target, suffix=".tmp", delete=False,
        ) as handle:
            tmp_name = handle.name
            handle.write(text)
        for n in range(1, _MAX_DUPLICATES + 1):
            name = f"{stem}.md" if n == 1 else f"{stem} ({n}).md"
            final = target / name
            try:
                os.rename(tmp_name, final)
            except FileExistsError:
                continue
            return str(final)
        raise OSError("too many files with the same name")
    except (OSError, ValueError) as exc:
        if tmp_name:
            try:
                os.remove(tmp_name)
            except OSError:
                pass
        raise NoteError("write_failed", f"Could not write file: {exc}") from exc
