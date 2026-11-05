"""Compose note text for article and video clips, and the save action."""
import logging

import transcript
from notes import NoteError, make_filename, render_frontmatter, safe_write
from transcript import Unsupported, VideoError, VideoInfo, build_paragraphs, render_transcript

log = logging.getLogger("oqc.save")


def build_article_note(req: dict) -> tuple[str, str]:
    page = req["page"]
    front = render_frontmatter([
        ("title", page.get("title")),
        ("source", page["url"]),
        ("author", page.get("author")),
        ("published", page.get("published")),
        ("clipped", req["clippedDate"]),
        ("tags", ["clipping"]),
    ])
    stem = make_filename(page.get("title") or "", req["clippedDate"], req["datePosition"])
    return stem, front + "\n" + (req.get("bodyMarkdown") or "") + "\n"


def build_video_note(
    req: dict, video: VideoInfo | None, reason: str | None
) -> tuple[str, str, str]:
    page = req["page"]
    url = page["url"]
    if video is None:
        title = page.get("title")
        channel = page.get("author")
        published = page.get("published")
        duration = None
        description = page.get("description") or ""
        kind = "none"
        transcript_text = f"Transcript unavailable: {reason}"
    else:
        title = video.title or page.get("title")
        channel = video.channel
        published = video.published
        duration = video.duration
        description = video.description or ""
        kind = video.transcript
        if video.cues:
            sections = build_paragraphs(video.cues, video.chapters)
            transcript_text = render_transcript(sections, url)
        else:
            transcript_text = "No transcript available"

    front = render_frontmatter([
        ("title", title),
        ("source", url),
        ("channel", channel),
        ("published", published),
        ("duration", duration),
        ("clipped", req["clippedDate"]),
        ("transcript", kind),
        ("tags", ["clipping", "video"]),
    ])
    parts = []
    if description.strip():
        parts.append(f"## Description\n\n{description.strip()}")
    parts.append(f"## Transcript\n\n{transcript_text}")
    stem = make_filename(title or "", req["clippedDate"], req["datePosition"])
    return stem, front + "\n" + "\n\n".join(parts) + "\n", kind


def _bad_request(message: str) -> dict:
    return {"ok": False, "error": "bad_request", "message": message}


def _validate(req: dict) -> str | None:
    dest = req.get("destination")
    page = req.get("page")
    if not isinstance(dest, dict) or not dest.get("vaultPath"):
        return "missing destination.vaultPath"
    if req.get("kind") not in ("article", "video"):
        return "kind must be article or video"
    if not isinstance(page, dict) or not page.get("url"):
        return "missing page.url"
    if not req.get("clippedDate"):
        return "missing clippedDate"
    if req.get("datePosition") not in ("end", "start", "none"):
        return "datePosition must be end, start or none"
    return None


def save(req: dict) -> dict:
    problem = _validate(req)
    if problem:
        page = req.get("page")
        log.info("save url=%s result=bad_request", page.get("url") if isinstance(page, dict) else None)
        return _bad_request(problem)

    url = req["page"]["url"]
    dest = req["destination"]
    kind = req["kind"]
    transcript_kind = None
    warning = None
    try:
        if kind == "video":
            try:
                video = transcript.fetch_video(url)
                stem, text, transcript_kind = build_video_note(req, video, None)
            except Unsupported:
                kind = "article"
            except VideoError as e:
                stem, text, transcript_kind = build_video_note(req, None, e.reason)
                warning = f"Saved without transcript: {e.reason}"
        if kind == "article":
            stem, text = build_article_note(req)
        path = safe_write(dest["vaultPath"], dest.get("subfolder") or "", stem, text)
    except NoteError as e:
        log.info("save url=%s kind=%s result=%s", url, kind, e.code)
        return {"ok": False, "error": e.code, "message": e.message}

    log.info("save url=%s kind=%s transcript=%s result=ok", url, kind, transcript_kind)
    return {
        "ok": True,
        "path": str(path),
        "kind": kind,
        "transcript": transcript_kind,
        "warning": warning,
    }
