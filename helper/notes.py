"""File name cleaning and YAML frontmatter for clipped notes."""
import re

_ILLEGAL = re.compile("[<>:\"/" + re.escape(chr(92)) + "|?*]")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")
_RESERVED = {"CON", "PRN", "AUX", "NUL"}
_RESERVED |= {f"COM{i}" for i in range(1, 10)}
_RESERVED |= {f"LPT{i}" for i in range(1, 10)}
_MAX_TITLE = 100


def _clean_title(title: str) -> str:
    title = _CONTROL.sub("", title or "")
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
