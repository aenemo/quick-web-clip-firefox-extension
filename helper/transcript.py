"""Caption parsing and timestamped transcript rendering (pure functions)."""
import concurrent.futures
import json
import logging
import re
from typing import NamedTuple
from urllib.parse import parse_qs, urldefrag, urlparse


class Cue(NamedTuple):
    start: float
    text: str


class Section(NamedTuple):
    title: str | None
    paragraphs: list[tuple[int, str]]


_TAG_RE = re.compile(r"<[^>]*>")
_VTT_TIME_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
_ENTITIES = (("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"), ("&amp;", "&"))
_MIN_OVERLAP = 2


def _clean(text: str) -> str:
    text = _TAG_RE.sub("", text)
    for entity, char in _ENTITIES:
        text = text.replace(entity, char)
    return " ".join(text.split())


def _vtt_seconds(match: "re.Match[str]") -> float:
    hours, minutes, seconds, millis = match.groups()
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + int(millis.ljust(3, "0")) / 1000


def _raw_json3(data: str) -> list[tuple[float, str]]:
    out = []
    for event in json.loads(data).get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        text = _clean("".join(seg.get("utf8", "") for seg in segs))
        if text:
            out.append((event.get("tStartMs", 0) / 1000.0, text))
    return out


def _raw_vtt(data: str) -> list[tuple[float, str]]:
    out = []
    start = None
    lines: list[str] = []

    def flush():
        if start is not None:
            text = _clean(" ".join(lines))
            if text:
                out.append((start, text))

    for line in data.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if "-->" in line:
            flush()
            match = _VTT_TIME_RE.search(line.split("-->")[0])
            start = _vtt_seconds(match) if match else None
            lines = []
        elif line == "":
            flush()
            start = None
            lines = []
        elif start is not None:
            lines.append(line)
    flush()
    return out


def parse_captions(data: str, fmt: str) -> list[Cue]:
    """Parse json3 or vtt captions into cues with tags, empty cues and rolling duplicates removed."""
    if fmt == "json3":
        raw = _raw_json3(data)
    elif fmt == "vtt":
        raw = _raw_vtt(data)
    else:
        raise ValueError(f"unsupported caption format: {fmt}")

    cues: list[Cue] = []
    prev_words: list[str] = []
    for start, text in raw:
        words = text.split()
        overlap = 0
        for k in range(min(len(prev_words), len(words)), _MIN_OVERLAP - 1, -1):
            if prev_words[-k:] == words[:k]:
                overlap = k
                break
        prev_words = words
        new_text = " ".join(words[overlap:])
        if new_text:
            cues.append(Cue(start, new_text))
    return cues


def format_ts(seconds: int) -> str:
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def timestamp_link(url: str, seconds: int) -> str | None:
    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    seconds = int(seconds)
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"):
        segments = [s for s in parts.path.split("/") if s]
        video_id = None
        if host == "youtu.be":
            video_id = segments[0] if segments else None
        elif len(segments) >= 2 and segments[0] in ("shorts", "live"):
            video_id = segments[1]
        else:
            video_id = (parse_qs(parts.query).get("v") or [None])[0]
        if not video_id:
            return None
        return f"https://www.youtube.com/watch?v={video_id}&t={seconds}"
    if host == "vimeo.com" or host.endswith(".vimeo.com"):
        base, _ = urldefrag(url)
        return f"{base}#t={seconds}s"
    return None


def _split_paragraphs(cues: list[Cue], any_punct: bool) -> list[tuple[int, str]]:
    paragraphs: list[tuple[int, str]] = []
    first = None
    texts: list[str] = []
    for cue in cues:
        if texts:
            length = cue.start - first
            ends_sentence = texts[-1][-1] in ".?!"
            if (
                (length >= 30 and ends_sentence)
                or (length >= 45 and not any_punct)
                or length >= 60
            ):
                paragraphs.append((int(first), " ".join(texts)))
                texts = []
        if not texts:
            first = cue.start
        texts.append(cue.text)
    if texts:
        paragraphs.append((int(first), " ".join(texts)))
    return paragraphs


def build_paragraphs(cues: list[Cue], chapters: list[dict] | None) -> list[Section]:
    any_punct = any(ch in cue.text for cue in cues for ch in ".?!")
    if not chapters:
        return [Section(None, _split_paragraphs(cues, any_punct))] if cues else []

    ordered = sorted(chapters, key=lambda c: c.get("start_time", 0))
    buckets: list[list[Cue]] = [[] for _ in ordered]
    for cue in cues:
        index = 0
        for i, chapter in enumerate(ordered):
            if chapter.get("start_time", 0) <= cue.start:
                index = i
        buckets[index].append(cue)

    sections = []
    for chapter, bucket in zip(ordered, buckets):
        if bucket:
            sections.append(Section(chapter.get("title") or None, _split_paragraphs(bucket, any_punct)))
    return sections


def render_transcript(sections: list[Section], url: str) -> str:
    blocks = []
    for section in sections:
        if section.title:
            blocks.append(f"### {section.title}")
        for start, text in section.paragraphs:
            link = timestamp_link(url, start)
            stamp = f"[{format_ts(start)}]({link})" if link else format_ts(start)
            blocks.append(f"{stamp} {text}")
    return "\n\n".join(blocks)


TIMEOUT_SECONDS = 60
_log = logging.getLogger("qwc.ytdlp")


class Unsupported(Exception):
    """yt-dlp does not support this URL."""


class VideoError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class VideoInfo(NamedTuple):
    title: str
    channel: str
    published: str | None
    duration: str | None
    description: str
    chapters: list | None
    cues: list[Cue]
    transcript: str


def _pick_track(tracks: dict | None, language: str | None) -> tuple[str, str] | None:
    if not tracks:
        return None
    keys = [k for k in tracks if k == "en"]
    keys += [k for k in tracks if k.startswith("en-")]
    if language and language in tracks:
        keys.append(language)
    keys += list(tracks)
    for key in keys:
        by_ext = {t.get("ext"): t.get("url") for t in tracks[key] or [] if t.get("url")}
        for fmt in ("json3", "vtt"):
            if fmt in by_ext:
                return by_ext[fmt], fmt
    return None


def select_track(info: dict) -> tuple[str, str, str] | None:
    language = info.get("language")
    for field, kind in (("subtitles", "manual"), ("automatic_captions", "auto")):
        found = _pick_track(info.get(field), language)
        if found:
            return found[0], found[1], kind
    return None


_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_REASON_MAX = 160


def _short(exc: BaseException) -> str:
    text = _ANSI.sub("", str(exc)).strip()
    lines = text.splitlines()
    first = lines[0].strip() if lines else ""
    if first.startswith("ERROR: "):
        first = first[len("ERROR: "):].strip()
    if len(first) > _REASON_MAX:
        cut = first[:_REASON_MAX]
        if first[_REASON_MAX] != " " and " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        first = cut.rstrip(" ,;:") + "..."
    return first or type(exc).__name__


def _fetch(url: str, ydl_factory) -> VideoInfo:
    opts = {
        "skip_download": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "logger": _log,
        "noprogress": True,
    }
    with ydl_factory(opts) as ydl:
        info = ydl.extract_info(url, download=False) or {}
        cues: list[Cue] = []
        transcript = "none"
        track = select_track(info)
        if track:
            track_url, fmt, kind = track
            try:
                data = ydl.urlopen(track_url).read().decode("utf-8")
                cues = parse_captions(data, fmt)
            except Exception as exc:
                raise VideoError(f"could not download captions: {_short(exc)[:170]}") from exc
            transcript = kind if cues else "none"
        elif info.get("extractor_key") == "Generic":
            raise Unsupported("not a video page")
    upload = info.get("upload_date") or ""
    published = f"{upload[:4]}-{upload[4:6]}-{upload[6:8]}" if len(upload) == 8 and upload.isdigit() else None
    duration = info.get("duration")
    return VideoInfo(
        title=info.get("title") or "",
        channel=info.get("channel") or info.get("uploader") or "",
        published=published,
        duration=format_ts(duration) if duration else None,
        description=info.get("description") or "",
        chapters=info.get("chapters"),
        cues=cues,
        transcript=transcript,
    )


def fetch_video(url: str, timeout: float = 60, ydl_factory=None) -> VideoInfo:
    try:
        import yt_dlp
        import yt_dlp.utils as ydl_utils
    except ImportError as exc:
        raise VideoError("yt-dlp not installed") from exc
    if ydl_factory is None:
        ydl_factory = yt_dlp.YoutubeDL

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_fetch, url, ydl_factory)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        raise VideoError(f"timed out after {TIMEOUT_SECONDS} seconds") from None
    except (VideoError, Unsupported):
        raise
    except ydl_utils.UnsupportedError as exc:
        raise Unsupported(_short(exc)) from exc
    except ydl_utils.DownloadError as exc:
        if "Unsupported URL" in str(exc):
            raise Unsupported(_short(exc)) from exc
        raise VideoError(_short(exc)) from exc
    except Exception as exc:
        raise VideoError(_short(exc)) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
