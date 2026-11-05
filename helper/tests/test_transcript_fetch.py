import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import yt_dlp.utils

from transcript import Unsupported, VideoError, VideoInfo, _short, fetch_video, parse_captions, select_track

FIX = Path(__file__).parent / "fixtures"
URL = "https://www.youtube.com/watch?v=abc123"


class FakeYDL:
    last = None

    def __init__(self, opts, info=None, data=None, sleep=0, error=None, url_error=None):
        self.opts = opts
        self._info = info
        self._data = data
        self._sleep = sleep
        self._error = error
        self._url_error = url_error
        FakeYDL.last = self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        if self._sleep:
            time.sleep(self._sleep)
        if self._error:
            raise self._error
        return self._info

    def urlopen(self, url):
        if self._url_error:
            raise self._url_error
        return io.BytesIO(self._data)


def factory(**kw):
    return lambda opts: FakeYDL(opts, **kw)


def base_info(**extra):
    info = {"title": "T", "channel": "C", "upload_date": "20260201", "duration": 3735,
            "description": "D", "chapters": None}
    info.update(extra)
    return info


MANUAL = {"en": [{"ext": "vtt", "url": "m-vtt"}, {"ext": "json3", "url": "m-json3"}]}
AUTO = {"en": [{"ext": "json3", "url": "a-json3"}]}


def test_select_prefers_manual_en_json3():
    assert select_track({"subtitles": MANUAL, "automatic_captions": AUTO}) == ("m-json3", "json3", "manual")


def test_select_falls_back():
    info = {"automatic_captions": {"en-GB": [{"ext": "vtt", "url": "u"}]}}
    assert select_track(info) == ("u", "vtt", "auto")
    info = {"subtitles": {"de": [{"ext": "vtt", "url": "d"}], "fr": [{"ext": "vtt", "url": "f"}]}, "language": "fr"}
    assert select_track(info) == ("f", "vtt", "manual")
    assert select_track({}) is None
    assert select_track({"subtitles": {}, "automatic_captions": None}) is None


def test_fetch_video_uses_noplaylist():
    fetch_video(URL, ydl_factory=factory(info=base_info()))
    opts = FakeYDL.last.opts
    assert opts["noplaylist"] is True
    assert opts["quiet"] is True
    assert "logger" in opts
    assert opts["skip_download"] is True
    for name in ("debug", "info", "warning", "error"):
        getattr(opts["logger"], name)("x")


def test_fetch_video_maps_fields():
    data = (FIX / "manual.json3").read_bytes()
    vi = fetch_video(URL, ydl_factory=factory(info=base_info(subtitles=MANUAL), data=data))
    assert isinstance(vi, VideoInfo)
    assert vi.title == "T" and vi.channel == "C" and vi.description == "D"
    assert vi.published == "2026-02-01"
    assert vi.duration == "1:02:15"
    assert vi.cues == parse_captions(data.decode("utf-8"), "json3")
    assert vi.transcript == "manual"


def test_channel_falls_back_to_uploader():
    info = base_info(uploader="U")
    del info["channel"]
    assert fetch_video(URL, ydl_factory=factory(info=info)).channel == "U"


def test_fetch_video_no_captions():
    vi = fetch_video(URL, ydl_factory=factory(info=base_info()))
    assert vi.cues == [] and vi.transcript == "none"


def test_fetch_video_unsupported():
    with pytest.raises(Unsupported):
        fetch_video(URL, ydl_factory=factory(error=yt_dlp.utils.UnsupportedError("x")))
    with pytest.raises(Unsupported):
        fetch_video(URL, ydl_factory=factory(error=yt_dlp.utils.DownloadError("ERROR: Unsupported URL: x")))


def test_fetch_video_other_error():
    with pytest.raises(VideoError) as ei:
        fetch_video(URL, ydl_factory=factory(error=yt_dlp.utils.DownloadError("boom\nsecond line")))
    assert ei.value.reason == "boom"
    with pytest.raises(VideoError) as ei:
        fetch_video(URL, ydl_factory=factory(error=RuntimeError("x" * 500)))
    assert len(ei.value.reason) <= 200


def test_fetch_video_timeout():
    start = time.monotonic()
    with pytest.raises(VideoError) as ei:
        fetch_video(URL, timeout=0.2, ydl_factory=factory(info=base_info(), sleep=2))
    assert ei.value.reason == "timed out after 60 seconds"
    assert time.monotonic() - start < 1.5


def test_caption_download_failure():
    with pytest.raises(VideoError) as ei:
        fetch_video(URL, ydl_factory=factory(info=base_info(subtitles=MANUAL), url_error=OSError("net down")))
    assert ei.value.reason == "could not download captions: net down"


def test_caption_parse_failure():
    with pytest.raises(VideoError) as ei:
        fetch_video(URL, ydl_factory=factory(info=base_info(subtitles=MANUAL), data=b"not json"))
    assert ei.value.reason.startswith("could not download captions: ")


def test_short_strips_error_prefix_and_ansi():
    assert _short(RuntimeError("ERROR: boom")) == "boom"
    ansi = "\x1b[0;31mERROR:\x1b[0m boom \x1b[1mbold\x1b[0m"
    assert _short(RuntimeError(ansi)) == "boom bold"
    assert _short(RuntimeError("ERROR: first\nsecond")) == "first"


def test_short_truncates_at_word_boundary():
    msg = "ERROR: [vimeo] 76979871: " + " ".join(["word"] * 60)
    out = _short(RuntimeError(msg))
    assert out.endswith("...")
    body = out[:-3]
    assert len(out) <= 163
    assert body.endswith("word") and not body.endswith(" ")
    assert msg[len("ERROR: "):].startswith(body)
    assert len(_short(RuntimeError("x" * 500))) <= 163


def test_generic_extractor_without_captions_is_unsupported():
    with pytest.raises(Unsupported):
        fetch_video(URL, ydl_factory=factory(info=base_info(extractor_key="Generic")))
    data = (FIX / "manual.json3").read_bytes()
    vi = fetch_video(URL, ydl_factory=factory(info=base_info(extractor_key="Generic", subtitles=MANUAL), data=data))
    assert vi.transcript == "manual"
