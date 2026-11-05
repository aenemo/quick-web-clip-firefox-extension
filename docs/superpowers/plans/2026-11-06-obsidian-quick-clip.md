# Obsidian Quick Clip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Firefox extension plus a Python native-messaging helper that saves the current page (article or video transcript) into a chosen Obsidian vault folder with one action.

**Architecture:** The extension (Manifest V3, no build step) extracts the page with Readability and Turndown and sends a JSON `save` request to the helper over native messaging. The helper (Python 3, venv with yt-dlp) fetches video details and captions when needed, renders the note, names the file and writes it atomically inside the vault. Pure logic on both sides sits in small modules with unit tests. Browser glue and the stdin/stdout loop stay thin.

**Tech Stack:** Firefox 128 or later (MV3, ES module background), vanilla JS, `node --test` (Node 24), Python 3.10 or later (3.14.7 on this machine), pytest, yt-dlp, Mozilla Readability, Turndown and turndown-plugin-gfm (vendored), web-ext (via `npx`, only for lint and signing).

**Spec:** `docs/superpowers/specs/2026-11-05-obsidian-quick-clip-design.md`. Read it before starting any task. Section numbers below refer to it.

## Global Constraints

- Gecko ID `obsidian-quick-clip@local`. Native host name `obsidian_quick_clip`. Protocol version `v: 1`.
- Command `clip-default`, suggested key `Alt+Shift+C`.
- Permissions are exactly `nativeMessaging`, `menus`, `activeTab`, `scripting`, `storage` and `notifications`. No host permissions.
- Every date written anywhere is `YYYY-MM-DD`. The clipped date is the local date.
- `datePosition` is one of `end` (default), `start` or `none`.
- File-name title trimmed to 100 characters. The duplicate suffix is ` (2)` up to ` (99)`.
- yt-dlp timeout is 60 seconds. The log is `helper\clipper.log`, rotating at 1 MB with 3 files kept, and never contains note bodies.
- Badge text: `...` while working, `OK` green for 2 s, `!` amber, `ERR` red.
- User-facing message wording must match the spec section 6 table exactly.
- No em dashes and no emojis in any file, UI string or commit message.
- Git identity is already set in the repository (`aenemo <gmcoburn@hotmail.com>`). Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Run every Python command through `helper\venv\Scripts\python.exe` (in Git Bash: `helper/venv/Scripts/python.exe`).

## Review Focus

1. **Anything printed to stdout corrupts native messaging.** yt-dlp and stray `print` calls write to stdout, which is the message channel. Expected: no output reaches the channel except framed replies. Pinned by `test_handler_print_does_not_corrupt_stdout` (Task 1) and the `quiet`/`logger` options test (Task 5).
2. **A YouTube URL with `&list=` (watching inside a playlist).** Expected: only that video is clipped, not the playlist. Pinned by `test_fetch_video_uses_noplaylist` (Task 5).
3. **A title made only of emoji, illegal characters, a reserved name or trailing dots.** Expected: a valid, non-empty Windows file name. Pinned by `test_make_filename_degenerate_titles` (Task 2).
4. **Deleting the default destination.** Expected: the first remaining destination becomes the default and the menu updates. Pinned by `test removeDestination reassigns default` (Task 8).
5. **A vault path with spaces and non-ASCII characters (e.g. `OneDrive - Contoso\Vault Notes é`).** Expected: the save works and the path comes back unchanged. Pinned by `test_safe_write_unicode_and_spaces_path` (Task 3).

---

## File Structure

```
.gitignore                     venv, logs, generated host manifest, node_modules, web-ext-artifacts
package.json                   {"type":"module"}, scripts: test, lint
README.md                      install, dev load, signing, shortcut, manual checklist
helper/
  requirements.txt             yt-dlp (runtime)
  requirements-dev.txt         -r requirements.txt, pytest
  clipper_host.py              framing, stdout guard, dispatch (ping/save), logging, main()
  notes.py                     make_filename, render_frontmatter, safe_write, NoteError
  compose.py                   build_article_note, build_video_note (request -> stem + text)
  transcript.py                select_track, parse_captions, build_paragraphs, render_transcript, fetch_video
  install_host.py              writes host manifest + HKCU registry key; --uninstall
  clipper_host.bat             launcher Firefox runs
  install.bat / uninstall.bat  user-facing wrappers
  tests/                       pytest, plus tests/fixtures/ caption samples
extension/
  manifest.json
  background.js                browser wiring only: listeners, menus, badge, notifications
  lib/dates.js                 localDate, normalisePublished
  lib/classify.js              isClippable, classifyUrl
  lib/settings.js              settings model functions
  lib/clip.js                  runClip orchestration with injected deps, errorMessage
  content/extract.js           defines window.__oqcExtract()
  vendor/                      Readability.js, turndown.js, turndown-plugin-gfm.js (+ LICENSE files)
  options/options.html|js|css
  icons/icon-48.png, icon-96.png
tests/                         node tests for extension/lib
```

---

### Task 1: Repository scaffold and helper message loop

**Files:**
- Create: `.gitignore`, `helper/requirements.txt`, `helper/requirements-dev.txt`, `helper/clipper_host.py`
- Test: `helper/tests/test_host.py`

**Interfaces:**
- Produces:
  - `read_message(stream: BinaryIO) -> dict | None` returns `None` on EOF.
  - `write_message(stream: BinaryIO, obj: dict) -> None` writes a 4-byte little-endian length followed by UTF-8 JSON, then flushes.
  - `handle(msg: dict) -> dict` dispatches `ping` now. `save` is added in Task 6. Any other action, or `v != 1`, returns `{"ok": False, "error": "bad_request", "message": ...}`. An unexpected exception returns `error: "internal"` and is logged with its stack trace.
  - `serve(stdin: BinaryIO, stdout: BinaryIO) -> None` loops until EOF. While `handle` runs, `sys.stdout` is redirected to `sys.stderr` so stray prints never reach the channel.
  - `main()` uses `sys.stdin.buffer` and `sys.stdout.buffer`.
  - `HOST_VERSION = "1.0.0"`.
  - `ping` replies `{"ok": True, "version": HOST_VERSION, "ytDlp": <yt_dlp.version.__version__ or None>}`.
  - Logging: `RotatingFileHandler(helper/clipper.log, maxBytes=1_000_000, backupCount=3)`.

- [ ] **Step 1: Set up the environment.** Create `.gitignore` (`helper/venv/`, `helper/*.log*`, `helper/obsidian_quick_clip.json`, `node_modules/`, `web-ext-artifacts/`, `__pycache__/`) and the requirements files (`yt-dlp`, then `-r requirements.txt` + `pytest`). Run `py -m venv helper/venv && helper/venv/Scripts/python.exe -m pip install -r helper/requirements-dev.txt`. Expected: pytest and yt-dlp install without errors.
- [ ] **Step 2: Write the failing tests** in `helper/tests/test_host.py`, using `io.BytesIO`:
  - `test_roundtrip_frame`: `write_message` then `read_message` returns an equal dict containing `"é"` and `"C:\\x"`.
  - `test_read_eof_returns_none`
  - `test_ping_reports_version`: `handle({"v":1,"action":"ping"})["ok"] is True` and `"version"` equals `"1.0.0"`.
  - `test_unknown_action_bad_request` and `test_wrong_version_bad_request`
  - `test_handler_exception_is_internal`: monkeypatch the dispatch table so `ping` raises, then `error == "internal"`.
  - `test_handler_print_does_not_corrupt_stdout`: monkeypatch `ping` to `print("noise")` and return `{"ok":True}`. Run `serve` on one framed ping. `read_message(out)` returns `{"ok": True}` and the output has nothing after the frame.
- [ ] **Step 3: Run** `helper/venv/Scripts/python.exe -m pytest helper/tests/test_host.py -v`. Expected: FAIL (module missing).
- [ ] **Step 4: Implement** `helper/clipper_host.py` to the interface above. Use `contextlib.redirect_stdout(sys.stderr)` around `handle`.
- [ ] **Step 5: Run** the same command. Expected: 7 passed.
- [ ] **Step 6: Commit** with the message `feat(helper): native messaging loop with ping`.

### Task 2: File names and frontmatter

**Files:**
- Create: `helper/notes.py`
- Test: `helper/tests/test_notes_format.py`

**Interfaces:**
- Produces:
  - `make_filename(title: str, date: str, position: str) -> str` returns the stem without `.md`.
  - `render_frontmatter(fields: list[tuple[str, object]]) -> str` returns the block from `---\n` to `---\n`. Values that are `None` or `""` are left out. Strings are double-quoted with `\` and `"` escaped and newlines written as `\n`. A `list` value is rendered as a block list (`tags:\n  - clipping`).

- [ ] **Step 1: Write the failing tests:**
  - `test_make_filename_positions`: `make_filename("How Rust Lifetimes Work", "2026-11-05", "end") == "How Rust Lifetimes Work 2026-11-05"`. The `start` position gives `"2026-11-05 How Rust Lifetimes Work"` and `none` gives `"How Rust Lifetimes Work"`.
  - `test_make_filename_strips_illegal`: `'a<b>c:d"e/f\\g|h?i*j'` becomes `"a b c d e f g h i j"` (illegal characters replaced by spaces, then whitespace collapsed). Control characters are removed.
  - `test_make_filename_trims_to_100`: a 300-character title produces a title part of exactly 100 characters, with trailing spaces and dots stripped after trimming.
  - `test_make_filename_degenerate_titles`: each of `""`, `"???"`, `"CON"`, `"nul.txt"`, `"..."` and `"   "` with `position="none"` gives a non-empty stem that is not a reserved name (`"CON"` becomes `"CON_"`, empty or all-illegal becomes `"Untitled"`). A title made only of emoji, e.g. `"\U0001F600\U0001F680"`, is kept as is (emoji are legal on NTFS) and stays non-empty.
  - `test_frontmatter_quotes_and_order`: `[("title", 'He said "hi": ok'), ("author", None), ("tags", ["clipping","video"])]` renders exactly as `'---\ntitle: "He said \\"hi\\": ok"\ntags:\n  - clipping\n  - video\n---\n'`.
  - `test_frontmatter_newlines_and_unicode`: the value `"line1\nline2 é"` is rendered as `"line1\\nline2 é"` (escaped newline, Unicode kept).
- [ ] **Step 2: Run** `helper/venv/Scripts/python.exe -m pytest helper/tests/test_notes_format.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** both functions in `helper/notes.py`. The reserved names are `CON PRN AUX NUL COM1-9 LPT1-9`, checked case-insensitively against the part before the first dot.
- [ ] **Step 4: Run** the tests again. Expected: all pass.
- [ ] **Step 5: Commit** with the message `feat(helper): file name cleaning and YAML frontmatter`.

### Task 3: Safe atomic write

**Files:**
- Modify: `helper/notes.py`
- Test: `helper/tests/test_safe_write.py`

**Interfaces:**
- Produces:
  - `class NoteError(Exception)` with `.code: str` (`vault_not_found` | `outside_vault` | `write_failed`) and `.message: str`.
  - `safe_write(vault: str, subfolder: str, stem: str, text: str) -> str` returns the absolute path written.
- Messages:
  - `vault_not_found` uses `"Folder not found: <vault>"`.
  - `outside_vault` uses `"Refused: subfolder points outside the vault"`.
  - `write_failed` uses `"Could not write file: <OS error>"`.

- [ ] **Step 1: Write the failing tests** (`tmp_path`):
  - `test_safe_write_creates_subfolder_and_file`: writes `Clippings\Web\Note.md`, and the content is read back identical with LF only (`b"\r\n" not in bytes`).
  - `test_safe_write_numbers_duplicates`: three writes of the stem `Note` produce `Note.md`, `Note (2).md` and `Note (3).md`. The first file's content is unchanged.
  - `test_safe_write_rejects_escape`: subfolders `..\..\x`, `C:\Windows` and `\\server\share` raise `NoteError` with code `outside_vault`.
  - `test_safe_write_missing_vault`: raises `vault_not_found` with the message `"Folder not found: <path>"`.
  - `test_safe_write_no_temp_left_on_failure`: monkeypatch `os.rename` so it always raises `PermissionError`. This raises `write_failed`, and the folder contains no `.tmp` files.
  - `test_safe_write_unicode_and_spaces_path`: the vault is `tmp_path / "OneDrive - Contoso" / "Vault Notes é"` with an empty subfolder. The returned path exists and starts with the vault path.
  - `test_safe_write_gives_up_after_99`: with `Note.md` and `Note (2).md` through `Note (99).md` already present, it raises `write_failed`.
- [ ] **Step 2: Run** `helper/venv/Scripts/python.exe -m pytest helper/tests/test_safe_write.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `safe_write`.** Resolve `Path(vault).resolve()`. Reject an absolute or UNC `subfolder` (`PureWindowsPath(subfolder).anchor` is not empty). Resolve the target folder and require `target.is_relative_to(vault_resolved)`. Write `tempfile.NamedTemporaryFile(dir=target, suffix=".tmp", delete=False)` with `newline="\n"`, encoding `utf-8`. Then loop over candidate names with `os.rename`, catching `FileExistsError` and moving to the next candidate. On any other `OSError`, remove the temporary file and raise `write_failed`.
- [ ] **Step 4: Run** the tests again. Expected: all pass.
- [ ] **Step 5: Commit** with the message `feat(helper): atomic, vault-contained note writes`.

### Task 4: Caption parsing and transcript rendering

**Files:**
- Create: `helper/transcript.py`
- Create: `helper/tests/fixtures/` containing `manual.json3`, `auto_rolling.json3`, `manual.vtt` and `auto_rolling.vtt`. Build them by hand as small, realistic samples of about 10 to 20 cues. The auto samples must contain the rolling-duplicate pattern, where each cue repeats the previous line plus new words.
- Test: `helper/tests/test_transcript_format.py`

**Interfaces:**
- Produces:
  - `Cue = NamedTuple("Cue", [("start", float), ("text", str)])`
  - `parse_captions(data: str, fmt: str) -> list[Cue]`, where `fmt` is `"json3"` or `"vtt"`. Strips tags, removes empty cues and removes rolling duplicates (the text of each cue is only the words not already in the previous cue).
  - `Section = NamedTuple("Section", [("title", str | None), ("paragraphs", list[tuple[int, str]])])`
  - `build_paragraphs(cues: list[Cue], chapters: list[dict] | None) -> list[Section]`. Chapters are yt-dlp dicts with `start_time`, `end_time` and `title`.
  - `format_ts(seconds: int) -> str` gives `m:ss`, or `h:mm:ss` from 3600 seconds.
  - `timestamp_link(url: str, seconds: int) -> str | None`
  - `render_transcript(sections: list[Section], url: str) -> str`

**Paragraph rule:** start a new paragraph when the current one is at least 30 s long and the last cue ends with `.`, `?` or `!`. Also start one when it reaches 45 s with no punctuation in the whole transcript, or when it reaches 60 s in any case. A paragraph never crosses a chapter start. The paragraph start is `int(first cue start)`.

**Links:**
- For YouTube (`youtube.com`, `youtu.be`, `m.youtube.com`, including `/shorts/ID` and `/live/ID`), the link is `https://www.youtube.com/watch?v=ID&t=N`.
- For Vimeo, the link is `<url without fragment>#t=Ns`.
- For other sites it is `None`. The renderer then writes plain `m:ss` text with no link.

- [ ] **Step 1: Write the failing tests:**
  - `test_format_ts`: `0` gives `"0:00"`, `754` gives `"12:34"` and `3735` gives `"1:02:15"`.
  - `test_timestamp_link_youtube_variants`: `watch?v=abc123&list=PL1`, `youtu.be/abc123`, `/shorts/abc123` and `/live/abc123` all give `https://www.youtube.com/watch?v=abc123&t=42` at 42 seconds.
  - `test_timestamp_link_vimeo_and_other`: Vimeo gives `https://vimeo.com/123#t=42s`, and `https://example.com/v` gives `None`.
  - `test_parse_json3_manual` and `test_parse_vtt_manual`: the cue count and the first cue `(0.0, ...)` match the fixture.
  - `test_parse_auto_removes_rolling_duplicates` (both formats): no word sequence of three or more words appears twice in a row in the joined text.
  - `test_paragraphs_respect_chapters`: two chapters (0 to 100 s and 100 to 200 s) produce two Sections with the chapter titles, and every paragraph start in Section 2 is 100 or more.
  - `test_paragraphs_no_chapters_single_section`: one Section with `title is None`, and every paragraph is 60 s or shorter.
  - `test_render_with_chapters`: the output contains `### Intro\n\n[0:00](https://www.youtube.com/watch?v=abc123&t=0) ` and paragraphs are separated by a blank line.
  - `test_render_other_site_plain_timestamps`: lines start with `0:00 ` and contain no `](`.
- [ ] **Step 2: Run** `helper/venv/Scripts/python.exe -m pytest helper/tests/test_transcript_format.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the functions to the rules above.
- [ ] **Step 4: Run** the tests again. Expected: all pass.
- [ ] **Step 5: Commit** with the message `feat(helper): caption parsing and timestamped transcript rendering`.

### Task 5: yt-dlp fetch and caption selection

**Files:**
- Modify: `helper/transcript.py`
- Test: `helper/tests/test_transcript_fetch.py`

**Interfaces:**
- Consumes: `parse_captions` (Task 4).
- Produces:
  - `select_track(info: dict) -> tuple[str, str, str] | None` returns `(url, fmt, kind)` where `kind` is `"manual"` or `"auto"`. It searches `info["subtitles"]` then `info["automatic_captions"]`, with the language order `en`, then `en-*`, then `info.get("language")`, then the first key, and the format order `json3` then `vtt`.
  - `class Unsupported(Exception)` for when yt-dlp raises `UnsupportedError`, or a `DownloadError` whose message contains "Unsupported URL".
  - `class VideoError(Exception)` with `.reason: str` for a timeout (`"timed out after 60 seconds"`), any other yt-dlp failure, or `"yt-dlp not installed"`.
  - `VideoInfo = NamedTuple` with the fields `title`, `channel`, `published` (`YYYY-MM-DD` or `None`, from `upload_date` `YYYYMMDD`), `duration` (`format_ts` or `None`), `description`, `chapters`, `cues` (`list[Cue]`) and `transcript` (`"manual" | "auto" | "none"`).
  - `fetch_video(url: str, timeout: float = 60, ydl_factory=None) -> VideoInfo`. The `ydl_factory(opts) -> context manager` defaults to `yt_dlp.YoutubeDL`.
- Required yt-dlp options: `{"skip_download": True, "noplaylist": True, "quiet": True, "no_warnings": True, "logger": <logger that writes to the helper log>, "noprogress": True}`. Run `extract_info(url, download=False)` on a `concurrent.futures` thread and wait for at most `timeout`. Fetch the caption track with `ydl.urlopen(track_url).read().decode("utf-8")`.

- [ ] **Step 1: Write the failing tests** using a `FakeYDL` (records `opts`, returns a canned `info`, `urlopen` returns `io.BytesIO(fixture bytes)`):
  - `test_select_prefers_manual_en_json3`: with manual `en` (json3 and vtt) and auto `en` present, the result is the manual json3 URL with `kind="manual"`.
  - `test_select_falls_back`: only auto `en-GB` vtt present gives `kind="auto"`, `fmt="vtt"`. Only `fr` (which matches `language="fr"`) gives the `fr` track. With nothing present, the result is `None`.
  - `test_fetch_video_uses_noplaylist`: `opts["noplaylist"] is True`, `opts["quiet"] is True` and `"logger" in opts`.
  - `test_fetch_video_maps_fields`: `upload_date="20260201"` gives `published="2026-02-01"`, and `duration=3735` gives `"1:02:15"`. The cues come from the fixture and `transcript="manual"`.
  - `test_fetch_video_no_captions`: `cues == []` and `transcript == "none"`.
  - `test_fetch_video_unsupported`: the fake raises `yt_dlp.utils.UnsupportedError("x")`, so `Unsupported` is raised.
  - `test_fetch_video_timeout`: the fake sleeps 2 s with `timeout=0.2`, so `VideoError` is raised with the reason `"timed out after 60 seconds"`. The reason text always uses the module constant `TIMEOUT_SECONDS = 60`, whatever `timeout` was passed.
- [ ] **Step 2: Run** `helper/venv/Scripts/python.exe -m pytest helper/tests/test_transcript_fetch.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the functions. Import `yt_dlp` lazily inside `fetch_video`. An `ImportError` raises `VideoError("yt-dlp not installed")`.
- [ ] **Step 4: Run** the tests again. Expected: all pass.
- [ ] **Step 5: Commit** with the message `feat(helper): yt-dlp video details and caption selection`.

### Task 6: Note composition and the `save` action

**Files:**
- Create: `helper/compose.py`
- Modify: `helper/clipper_host.py` (register `save`)
- Test: `helper/tests/test_compose.py`, `helper/tests/test_save.py`

**Interfaces:**
- Consumes:
  - `make_filename`, `render_frontmatter`, `safe_write` and `NoteError` (Tasks 2 and 3)
  - `fetch_video`, `Unsupported`, `VideoError`, `build_paragraphs` and `render_transcript` (Tasks 4 and 5)
- Produces:
  - `build_article_note(req: dict) -> tuple[str, str]` returns `(stem, text)`.
    - Frontmatter order: `title`, `source` (`page.url`), `author`, `published`, `clipped` (`req.clippedDate`), `tags` (`["clipping"]`).
    - The text is the frontmatter, a blank line, then `bodyMarkdown` with a trailing newline.
  - `build_video_note(req: dict, video: VideoInfo | None, reason: str | None) -> tuple[str, str, str]` returns `(stem, text, transcript_kind)`.
    - Frontmatter order (spec section 7): `title`, `source`, `channel`, `published`, `duration`, `clipped`, `transcript`, `tags` (`["clipping","video"]`).
    - When `video` is `None`, it uses `page.title`, `page.author` as the channel, `page.published` and `page.description`. Then `transcript="none"` and the body says `Transcript unavailable: <reason>`.
    - When `video.cues` is empty, the body says `No transcript available`.
    - The body is `## Description\n\n<description>\n\n## Transcript\n\n<render_transcript or message>`. `## Description` is left out when the description is empty.
  - `handle` for `save`:
    - Validate the required keys (`destination.vaultPath`, `kind`, `page.url`, `clippedDate`, `datePosition`). Anything missing gives `bad_request`.
    - **article**: build the note, then `safe_write`.
    - **video**: call `fetch_video`.
      - `Unsupported`: save as an article and reply with `kind: "article"`.
      - `VideoError`: call `build_video_note(req, None, e.reason)` and reply with `warning: "Saved without transcript: <reason>"`.
    - Success reply: `{"ok": True, "path", "kind", "transcript", "warning"}`. Articles reply with `transcript: None`.
    - `NoteError` replies `{"ok": False, "error": e.code, "message": e.message}`.
    - Log one line per save (action, url, result). Never log the body.

- [ ] **Step 1: Write the failing tests:**
  - `test_compose.py`:
    - `test_article_note_layout`: an exact string comparison against the spec section 7 article example (with `author` and `published` present).
    - `test_article_note_omits_empty`: no `author:` line when the author is `None`.
    - `test_video_note_layout`: a `VideoInfo` with one chapter and two cues produces the spec section 7 video example structure (frontmatter keys in order, `## Description`, `## Transcript`, `### <chapter>`).
    - `test_video_note_no_captions`: the body contains `No transcript available` and `transcript: "none"`.
    - `test_video_note_fallback_reason`: `video=None, reason="yt-dlp not installed"` gives a body containing `Transcript unavailable: yt-dlp not installed`.
  - `test_save.py` (monkeypatch `transcript.fetch_video`, using `tmp_path` as the vault):
    - `test_save_article_writes_file`: the reply is `ok`, the path exists and the name ends with ` 2026-11-05.md`.
    - `test_save_video_success`: the reply has `kind == "video"` and `transcript == "manual"`.
    - `test_save_video_unsupported_falls_back_to_article`: the reply has `kind == "article"`, and the file contains `bodyMarkdown`.
    - `test_save_video_error_saves_with_warning`: the reply has `warning == "Saved without transcript: timed out after 60 seconds"`.
    - `test_save_missing_vault`: `error == "vault_not_found"`.
    - `test_save_bad_request`: no `destination` gives `error == "bad_request"`.
    - `test_log_has_no_body`: after a save with `bodyMarkdown="SECRET-BODY"`, the log file does not contain `SECRET-BODY`. Point the log at `tmp_path` with a fixture.
- [ ] **Step 2: Run** `helper/venv/Scripts/python.exe -m pytest helper/tests -v`. Expected: the new tests FAIL and the earlier tests pass.
- [ ] **Step 3: Implement** `compose.py` and the `save` handler.
- [ ] **Step 4: Run** `helper/venv/Scripts/python.exe -m pytest helper/tests -v`. Expected: all pass.
- [ ] **Step 5: Commit** with the message `feat(helper): compose article and video notes, save action`.

### Task 7: Helper install and uninstall

**Files:**
- Create: `helper/install_host.py`, `helper/clipper_host.bat`, `helper/install.bat`, `helper/uninstall.bat`
- Test: `helper/tests/test_install_host.py`

**Interfaces:**
- Produces:
  - `build_manifest(helper_dir: Path) -> dict` returns `{"name": "obsidian_quick_clip", "description": "Obsidian Quick Clip helper", "path": str(helper_dir / "clipper_host.bat"), "type": "stdio", "allowed_extensions": ["obsidian-quick-clip@local"]}`.
  - `install(helper_dir: Path, reg=winreg) -> Path` writes `helper_dir/obsidian_quick_clip.json` and sets the default value of `HKCU\Software\Mozilla\NativeMessagingHosts\obsidian_quick_clip` to that path.
  - `uninstall(helper_dir: Path, reg=winreg) -> None` deletes the key (ignoring "not found") and the manifest file.
  - The CLI is `python install_host.py [--uninstall]`.
- `clipper_host.bat` is exactly `@"%~dp0venv\Scripts\python.exe" "%~dp0clipper_host.py" %*`.
- `install.bat`:
  1. Checks that `py -3 --version` works and is 3.10 or later, otherwise prints "Python 3.10 or later is required" and exits with code 1.
  2. Creates `venv` if it is missing and runs `pip install -r requirements.txt`.
  3. Runs `venv\Scripts\python.exe install_host.py`.
  4. Prints "Helper installed." plus the next step: load the extension.
- `uninstall.bat`: runs `install_host.py --uninstall`, then removes `venv`.

- [ ] **Step 1: Write the failing tests** with a fake `reg` object that records `CreateKey` and `SetValue` calls:
  - `test_build_manifest_fields` checks the exact dict above.
  - `test_install_writes_manifest_and_registry`: the JSON file parses equal to the manifest, and the fake registry recorded the key path and value.
  - `test_uninstall_tolerates_missing`: does not raise when the key and file are absent.
- [ ] **Step 2: Run** `helper/venv/Scripts/python.exe -m pytest helper/tests/test_install_host.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `install_host.py` and the three `.bat` files.
- [ ] **Step 4: Run** the tests again. Expected: pass. Then run `cmd //c helper\\install.bat`. Expected: "Helper installed.", and `reg query "HKCU\Software\Mozilla\NativeMessagingHosts\obsidian_quick_clip"` shows the manifest path.
- [ ] **Step 5: Check the helper end to end.** Run a one-off Python snippet that spawns `helper\clipper_host.bat`, writes a framed ping and reads the reply. Expected: `{"ok": true, "version": "1.0.0", "ytDlp": "<version>"}`.
- [ ] **Step 6: Commit** with the message `feat(helper): installer and native host registration`.

### Task 8: Extension pure modules

**Files:**
- Create: `package.json`, `extension/lib/dates.js`, `extension/lib/classify.js`, `extension/lib/settings.js`
- Test: `tests/dates.test.js`, `tests/classify.test.js`, `tests/settings.test.js`

**Interfaces:**
- Produces (ES modules):
  - `localDate(d = new Date()): string` returns `YYYY-MM-DD` from local time.
  - `normalisePublished(s: string | null): string | null` accepts ISO date-times, `YYYY-MM-DD`, and anything `Date.parse` understands. It returns the local `YYYY-MM-DD`, or `null`.
  - `isClippable(url: string): boolean` is true only for `http:`, `https:` and `file:` URLs. It is false for those too when the host is `addons.mozilla.org`, or when the path ends in `.pdf` (case-insensitive), because Firefox's PDF viewer can't be scripted.
  - `classifyUrl(url: string, ogType: string | null = null): "video" | "article"` uses the spec section 3.1 patterns, and `ogType?.startsWith("video")`.
  - `DEFAULT_SETTINGS = { destinations: [], datePosition: "end" }`
  - `normaliseSettings(raw): Settings` fills defaults. If no destination has `isDefault`, the first one becomes the default. If several do, only the first keeps it.
  - `validateDestination(d): string[]` returns error strings: `"Label is required"`, `"Vault folder is required"`, and `"Vault folder must be a full path"` unless it matches `/^[A-Za-z]:\\|^\\\\/`.
  - `getDefaultDestination(s): Destination | null`
  - `setDefault(s, id): Settings`, `removeDestination(s, id): Settings`, `upsertDestination(s, d): Settings` and `moveDestination(s, id, delta): Settings` are all immutable (they return new objects).
  - `buildMenuModel(s): {id: string, title: string}[]` returns one entry per destination with `id = "dest:" + d.id` and the title `d.label`. The default is suffixed ` (default)`.

- [ ] **Step 1: Write the failing tests:**
  - `dates`: `localDate(new Date(2026, 10, 5, 23, 59))` gives `"2026-11-05"`. `normalisePublished("2026-03-14T08:00:00+10:00")` gives `"2026-03-14"` (run with `TZ=Australia/Sydney`), and `"garbage"` gives `null`.
  - `classify`:
    - Each YouTube, Vimeo, Dailymotion and TED pattern gives `"video"`.
    - `https://www.youtube.com/` and `https://vimeo.com/about` give `"article"`.
    - `ogType "video.other"` on any URL gives `"video"`.
    - `isClippable` is false for `about:blank`, `https://addons.mozilla.org/en-US/firefox/` and `https://x.com/a.pdf`, and true for `https://example.com`.
  - `settings`:
    - `test removeDestination reassigns default`: deleting the default leaves the first remaining destination as the default.
    - Deleting the last destination leaves an empty list and `getDefaultDestination` returning `null`.
    - `normaliseSettings` with two defaults keeps only the first. With `{}` it equals `DEFAULT_SETTINGS`.
    - The `validateDestination` messages match the list above exactly.
    - `buildMenuModel` titles include ` (default)` on exactly one item.
- [ ] **Step 2: Run** `npm test` (the script is `node --test tests/`). The first line of `tests/dates.test.js` sets `process.env.TZ = "Australia/Sydney"`, so no environment syntax is needed in the npm script. Expected: FAIL.
- [ ] **Step 3: Implement** the three modules.
- [ ] **Step 4: Run** `npm test`. Expected: all pass.
- [ ] **Step 5: Commit** with the message `feat(ext): dates, page classification and settings model`.

### Task 9: Clip orchestration

**Files:**
- Create: `extension/lib/clip.js`
- Test: `tests/clip.test.js`

**Interfaces:**
- Consumes: Task 8 modules.
- Produces:
  - `async runClip({ tab, destinationId = null }, deps): Promise<{ status: "ok" | "warning" | "error" | "skipped", message?: string, path?: string }>`
  - `deps` is `{ getSettings(): Promise<raw>, extract(tabId): Promise<{page, ogType, bodyMarkdown}>, sendNative(msg): Promise<reply>, openOptions(): Promise<void>, setBadge(tabId, state: "working"|"ok"|"warning"|"error"): void, notify(message: string): void, today(): string }`
  - `errorMessage(errOrReply): string` maps to the spec section 6 wording.
    - A thrown native error (no reply) gives `"Helper not found. Run install.bat in the helper folder."`
    - Reply codes use `reply.message` (the helper already formats it).
    - An extract failure gives `"Could not read this page"`.
- Flow (spec section 5):
  1. Normalise the settings. With no destinations, call `openOptions` and return `skipped`.
  2. If the page is not clippable, notify and return `skipped` with `"This page can't be clipped"`.
  3. Set the badge to `working`, then `extract`, then `classifyUrl(page.url || tab.url, ogType)`, then `sendNative` with the spec section 4 request built using `today()` and the destination's `vaultPath` and `subfolder`.
  4. Set the final badge. A warning or error also calls `notify`.
- An unknown `destinationId` falls back to the default.

- [ ] **Step 1: Write the failing tests** with fakes that record calls:
  - `test no destinations opens options`
  - `test unclippable page notifies and skips` (exact message)
  - `test default destination request shape`: `sendNative` receives `{v:1, action:"save", kind:"article", destination:{vaultPath, subfolder}, datePosition:"end", clippedDate:"2026-11-06", page:{...}, bodyMarkdown}`.
  - `test menu destination used`: the `destinationId` selects that vault.
  - `test youtube classified as video`
  - `test helper missing message`: `sendNative` rejects, so the result is `error` with the exact helper-not-found text and the badge is `error`.
  - `test reply error uses helper message`
  - `test warning path`: the badge is `warning` and `notify` receives the warning text.
  - `test extract failure`: `"Could not read this page"`
- [ ] **Step 2: Run** `npm test`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement** `clip.js`.
- [ ] **Step 4: Run** `npm test`. Expected: all pass.
- [ ] **Step 5: Commit** with the message `feat(ext): clip orchestration with error mapping`.

### Task 10: Content extraction, manifest and background wiring

**Files:**
- Create: `extension/vendor/*` (with LICENSE files), `extension/content/extract.js`, `extension/manifest.json`, `extension/background.js`, `extension/icons/icon-48.png`, `extension/icons/icon-96.png`

**Interfaces:**
- Consumes: `runClip`, `buildMenuModel`, `normaliseSettings` and `isClippable`.
- `extract.js` defines `window.__oqcExtract = () => ({ page: {url, title, author, published, siteName, description}, ogType, bodyMarkdown })`.
  - It runs `new Readability(document.cloneNode(true)).parse()`. When the result is null or its content is empty, it uses `document.body.innerHTML`.
  - Before converting, it makes `img[src]` and `a[href]` absolute.
  - Conversion uses `new TurndownService({headingStyle:"atx", codeBlockStyle:"fenced", bulletListMarker:"-"}).use(turndownPluginGfm.gfm)`.
  - `url` comes from `link[rel=canonical]` or `location.href`.
  - Metadata comes from Readability (`byline`, `siteName`, `publishedTime`), then the `og:*`, `article:published_time` and JSON-LD `datePublished` / `author.name` fields.
  - `published` is passed through as is. `background.js` normalises it with `normalisePublished` before calling `runClip`, by wrapping the `extract` dependency.
- `background.js` (`"background": {"scripts": ["background.js"], "type": "module"}`):
  - `deps.extract` runs `browser.scripting.executeScript({target:{tabId}, files:["vendor/Readability.js","vendor/turndown.js","vendor/turndown-plugin-gfm.js","content/extract.js"]})` and then `executeScript({target:{tabId}, func: () => window.__oqcExtract()})`, returning `[0].result`.
  - `deps.sendNative` is `browser.runtime.sendNativeMessage("obsidian_quick_clip", msg)`.
  - `setBadge` uses the global constraints' text and colours (`#2e7d32`, `#f9a825`, `#c62828`) and clears `OK` after 2000 ms.
  - `notify` is `browser.notifications.create({type:"basic", title:"Obsidian Quick Clip", message, iconUrl:"icons/icon-96.png"})`.
  - It rebuilds the menus: a parent "Save to" in contexts `["page","action"]`, with children from `buildMenuModel`. It rebuilds on startup and on `storage.onChanged`.
  - Listeners: `action.onClicked`, `commands.onCommand("clip-default")` and `menus.onClicked` (strip the `dest:` prefix).

- [ ] **Step 1: Vendor the libraries.** In the scratchpad, run `npm pack @mozilla/readability@0.6.0 turndown@7.2.0 turndown-plugin-gfm@1.0.2`, extract the packages, then copy `Readability.js`, `lib/turndown.browser.umd.js` (saved as `vendor/turndown.js`) and `dist/turndown-plugin-gfm.js` plus each LICENSE file into `extension/vendor/`. Record the versions in `extension/vendor/VERSIONS.txt`. Expected: the globals `Readability`, `TurndownService` and `turndownPluginGfm` are defined when the files are loaded in order.
- [ ] **Step 2: Write** `extract.js`, `manifest.json` (name "Obsidian Quick Clip", version "1.0.0", `browser_specific_settings.gecko` with `id` and `strict_min_version: "128.0"`, `options_ui.page: "options/options.html"`, `action.default_title: "Save page to Obsidian"`) and `background.js`. Icons: generate solid purple (`#7c3aed`) 48 and 96 px PNGs with a short Python script in the scratchpad that uses only the standard library (`zlib` and `struct`). Commit the PNGs, not the script.
- [ ] **Step 3: Lint** with `npx web-ext@8 lint --source-dir extension`. Expected: 0 errors. Warnings about the vendored code are acceptable if they're listed in the commit message.
- [ ] **Step 4: Smoke test (manual).** Load the extension through `about:debugging`. Add a destination in `about:debugging` > Inspect > the console, using `browser.storage.local.set(...)`, pointing at a temporary folder. Open an article and press Alt+Shift+C. Expected: the badge shows `OK` and the note file appears with the spec section 7 article layout.
- [ ] **Step 5: Commit** with the message `feat(ext): content extraction, manifest and background wiring`.

### Task 11: Options page

**Files:**
- Create: `extension/options/options.html`, `options.js`, `options.css`

**Interfaces:**
- Consumes:
  - `normaliseSettings`, `validateDestination`, `upsertDestination`, `removeDestination`, `setDefault` and `moveDestination` (Task 8)
  - `ping` (spec section 4)
- Behaviour:
  - A table of destinations with label, vault folder, subfolder, a "Default" radio button, Up/Down/Edit/Delete buttons and an Add form.
  - Validation errors appear inline under the field (strings from `validateDestination`).
  - A "Date in file name" select (At the end / At the start / None).
  - Every change saves to `browser.storage.local` immediately. The background script rebuilds the menus through `storage.onChanged`.
  - Helper status line:
    - `"Helper connected (v1.0.0), yt-dlp <version>"`
    - `"Helper connected (v1.0.0), yt-dlp not installed"`
    - `"Helper not found. Run install.bat in the helper folder."`
  - Delete asks for confirmation inline ("Delete <label>? Yes / No"), not with `confirm()`.
  - Plain CSS that follows `prefers-color-scheme`, works at 400 px width and has no external resources.

- [ ] **Step 1: Implement** the three files.
- [ ] **Step 2: Manual check.**
  1. Add two destinations, then confirm that the right-click "Save to" menu shows both with ` (default)` on one.
  2. Switch the default, delete the default and reorder the destinations, confirming the menu follows each time.
  3. An invalid vault path shows `"Vault folder must be a full path"`.
  4. The status line shows the connected text.
  5. Reload the extension and confirm that the settings persist.
- [ ] **Step 3: Commit** with the message `feat(ext): options page for destinations and helper status`.

### Task 12: README and end-to-end verification

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md** covering:
  - what the tool does
  - prerequisites (Python 3.10 or later, Firefox 128 or later)
  - `helper\install.bat`
  - loading through `about:debugging`
  - unlisted signing (`npx web-ext@8 sign --channel=unlisted --source-dir extension --api-key ... --api-secret ...`, with the credentials from addons.mozilla.org created by the user)
  - changing the shortcut
  - updating yt-dlp (`helper\venv\Scripts\python.exe -m pip install -U yt-dlp`)
  - uninstalling
  - troubleshooting (`helper\clipper.log`)
  - the managed-Firefox caveat from spec section 9
- [ ] **Step 2: Run** the spec section 8 manual checklist against real pages: a news article, a blog, Wikipedia, YouTube with chapters, YouTube without captions, a YouTube Short, a YouTube watch URL with `&list=`, Vimeo, a missing vault folder, the helper uninstalled, an `about:` page, and a duplicate clip. Record each result as a table in the README's "Verified" section, with the date in `DD/MM/YYYY` format and a pass or fail.
- [ ] **Step 3: Run** `helper/venv/Scripts/python.exe -m pytest helper/tests -q` and `npm test`. Expected: both pass with 0 failures.
- [ ] **Step 4: Commit** with the message `docs: README and verification results`.
