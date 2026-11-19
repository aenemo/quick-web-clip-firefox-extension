"""Save images sent with a clip next to the note and point the Markdown at them."""
import base64
import binascii
import re
from pathlib import Path
from urllib.parse import quote

FOLDER = "attachments"
_TOKEN = re.compile(r"qwc-attachment:(\d+)(?!\d)")
_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/bmp": "bmp",
    "image/avif": "avif",
    "image/svg+xml": "svg",
}
_MAX_FILES = 999
# Obsidian reads link paths with decodeURI, which leaves %-escapes of these characters
# undecoded, so they stay as they are in links.
_LINK_SAFE = "/;,@&=+$!'~*"
# Characters that break an Obsidian link even when escaped.
_LINK_UNSAFE = re.compile(r"[#^\[\]|]")


def _write_new(folder: Path, stem: str, ext: str, data: bytes, start: int) -> tuple[Path, int]:
    for n in range(start, _MAX_FILES + 1):
        path = folder / f"{stem} {n}.{ext}"
        try:
            with open(path, "xb") as handle:
                handle.write(data)
        except FileExistsError:
            continue
        return path, n
    raise OSError("too many attachments with the same name")


def save_attachments(target: Path, stem: str, items) -> tuple[dict[str, str], list[Path], int]:
    """Write each valid image to <target>/attachments.

    Returns (token -> relative Markdown link, files written, number of items skipped).
    """
    links: dict[str, str] = {}
    written: list[Path] = []
    skipped = 0
    if not isinstance(items, list):
        return links, written, 0
    folder = target / FOLDER
    stem = " ".join(_LINK_UNSAFE.sub(" ", stem).split()) or "image"
    number = 1
    for item in items:
        try:
            token = item["token"]
            match = _TOKEN.fullmatch(token)
            ext = _EXT.get(str(item["mime"]).lower())
            if not match or not ext or token in links:
                raise ValueError("bad attachment")
            data = base64.b64decode(item["data"], validate=True)
            if not data:
                raise ValueError("empty attachment")
            folder.mkdir(parents=True, exist_ok=True)
            path, used = _write_new(folder, stem, ext, data, number)
        except (KeyError, TypeError, ValueError, binascii.Error, OSError):
            skipped += 1
            continue
        number = used + 1
        written.append(path)
        links[token] = f"{FOLDER}/{quote(path.name, safe=_LINK_SAFE)}"
    return links, written, skipped


def link_attachments(text: str, links: dict[str, str]) -> str:
    """Swap every known token in the Markdown for its saved file."""
    return _TOKEN.sub(lambda m: links.get(m.group(0), m.group(0)), text)


def remove_files(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink()
        except OSError:
            pass
