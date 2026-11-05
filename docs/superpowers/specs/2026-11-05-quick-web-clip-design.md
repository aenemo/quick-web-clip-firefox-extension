# Quick Web Clip (Firefox) - Design Spec

Date: 2026-11-05
Status: Draft for review

## 1. Purpose

Save the current web page into an Obsidian vault as a Markdown note with a single action (toolbar click or keyboard shortcut), with no popup and no Save dialog.

The official Obsidian Web Clipper for Firefox lacks a one-action "Quick Clip", so saving takes three clicks. This tool closes that gap and adds video transcripts.

### What the user asked for

- One click or one shortcut saves the page to a default vault folder.
- Vault folders are outside the Downloads folder.
- Several destinations (vault + folder) can be configured, with one marked as default.
- Non-default destinations are reached through a right-click "Save to" menu.
- Only the main article content is saved (Readability), not the whole page.
- Clipping a YouTube (or other video platform) page saves the video's transcript, with timestamps and chapter headings where available.
- Saving must work whether or not Obsidian is running.

### Assumptions (confirm or correct)

- Single user, Windows 11, standard Firefox release channel, Python 3 already installed (3.14.7 present).
- Personal tool: distributed as a self-installed, unlisted-signed `.xpi`, not published on the public add-on store.
- English is the preferred transcript language.

### Success criteria

1. On a normal article page, one click or Alt+Shift+C writes a clean Markdown note into the default destination within about 2 seconds, and the toolbar shows success.
2. Right-click > "Save to" > any configured destination writes the note there instead.
3. On a YouTube video page, the same action writes a video note containing details, description and a timestamped transcript with chapter headings when the video has chapters.
4. No clip ever overwrites an existing file, writes outside the chosen vault folder, or leaves a half-written file.
5. Every failure produces a visible, specific message.

### Out of scope

- Downloading images into the vault (images stay as remote links).
- User-editable note templates.
- Highlighting or annotating before saving.
- Chrome or other browsers.
- Syncing settings between machines.
- Publishing to the public Firefox add-on store.

## 2. Architecture

Two parts connected by Firefox native messaging (Firefox launches the helper as a child process and exchanges length-prefixed JSON over stdin/stdout).

```
Firefox extension                          Python helper (native host)
-----------------                          ---------------------------
toolbar / shortcut / right-click
  -> background script
       - resolves destination
       - injects content script
  -> content script
       - classify page (article / video)
       - Readability + Turndown -> Markdown
       - page metadata
  -> sendNativeMessage(save request) ---->  - video: yt-dlp details + transcript
                                            - render frontmatter + note body
                                            - build safe file name
                                            - write file atomically
  <- {ok, path} or {ok:false, error} <---
  -> badge + notification
options page: destinations, default, date position, helper status (ping)
```

Responsibility split:
- The extension never touches the disk.
- The helper never parses HTML.
- The helper owns file naming and frontmatter rendering for both note types, so YAML escaping and file-name rules live in one place.

## 3. Components

### 3.1 Extension (Manifest V3, Firefox 128 or later)

- **`manifest.json`**
  - Gecko ID `quick-web-clip@local`
  - Permissions: `nativeMessaging`, `menus`, `activeTab`, `scripting`, `storage`, `notifications`
  - No broad host permissions. `activeTab` is granted by the toolbar click, the shortcut command and the context-menu click, which is enough to inject the content script.
  - Command `clip-default`, suggested key `Alt+Shift+C`.
  - Toolbar action with no popup.

- **`background.js`**
  - Handles `action.onClicked`, `commands.onCommand` and `menus.onClicked`.
  - Builds the "Save to" submenu (contexts `page` and `action`) from storage and rebuilds it on `storage.onChanged`.
  - Runs the clip flow (section 5) and shows the result (section 6).
  - Rejects pages that cannot be clipped (`about:`, `moz-extension:`, `view-source:`, the built-in PDF viewer, addons.mozilla.org) before injecting anything.

- **`content/extract.js`** (injected along with the vendored libraries)
  - Clones the document, runs Readability, then converts the result to Markdown with Turndown and the GFM plugin (tables, strikethrough, fenced code).
  - If Readability returns nothing, converts `document.body` instead.
  - Collects metadata: `url` (canonical if present), `title`, `author`, `published`, `siteName`, `description` (from Readability, `og:*`, `article:*` and JSON-LD).
  - Image `src` values are made absolute so remote links work in Obsidian.
  - Returns `{kind, page, bodyMarkdown}`.

- **`lib/classify.js`** (pure, unit-tested)
  - Decides `kind` from the URL: `video` for known video URL patterns, otherwise `article`.
  - Initial patterns:
    - YouTube: `youtube.com/watch`, `youtube.com/shorts/`, `youtube.com/live/`, `youtu.be/`, `m.youtube.com`
    - Vimeo video IDs
    - Dailymotion `/video/`
    - TED `/talks/`
  - A page whose `og:type` starts with `video` is also treated as `video`.

- **`lib/settings.js`** (pure, unit-tested)
  - Settings schema, defaults and validation.
  - Picking the default destination.
  - Building the menu model.

- **`lib/dates.js`** (pure, unit-tested)
  - Local date as `YYYY-MM-DD`.
  - Normalising published dates to `YYYY-MM-DD`.

- **`options/`**
  - Lists destinations, with add, edit, delete, reorder and a "default" radio button.
  - Date-position setting.
  - Helper status line from a `ping` request, e.g. "Helper connected, yt-dlp 2026.x" or "Helper not found".
  - Validation: label and vault folder are required, and exactly one destination is the default.

- **`vendor/`**
  - Pinned copies of `Readability.js` (Mozilla), `turndown.js` and `turndown-plugin-gfm.js`.
  - No build step and no bundler.

### 3.2 Settings model (`browser.storage.local`)

```json
{
  "destinations": [
    {
      "id": "uuid",
      "label": "Work vault / Clippings",
      "vaultPath": "C:\\Users\\gcoburn\\Documents\\WorkVault",
      "subfolder": "Clippings\\Web",
      "isDefault": true
    }
  ],
  "datePosition": "end"
}
```

`datePosition` is one of `end` (default), `start` or `none`.

### 3.3 Python helper

- **`clipper_host.py`**
  - Native messaging loop: reads one message from stdin in binary mode (a 4-byte little-endian length followed by UTF-8 JSON), dispatches it, and writes one reply.
  - Exits when stdin closes.

- **`notes.py`** (pure apart from writing files, unit-tested)
  - `make_filename(title, date, position)`
    - Removes characters Windows does not allow in file names (`<>:"/\|?*` and control characters) and Windows reserved names (`CON`, `NUL`, ...).
    - Collapses whitespace, strips trailing dots and spaces, and trims the title to 100 characters.
    - Falls back to `Untitled`.
  - `render_frontmatter(fields)`
    - Writes YAML with every string value double-quoted and escaped.
    - Leaves out fields that are empty.
    - Writes `tags` as a list.
  - `safe_write(vault, subfolder, filename, text)`
    - Resolves the target and requires it to be inside the resolved vault path, otherwise returns `outside_vault`.
    - Requires the vault folder to exist, otherwise returns `vault_not_found`.
    - Creates the subfolder if it is missing.
    - Writes to a temporary file in the target folder, then renames it to `name.md`. If that name exists, it tries `name (2).md`, `name (3).md` and so on, up to 99 attempts. On Windows the rename fails rather than overwrites, so a race can never overwrite a file.
    - Text is written as UTF-8 with LF line endings.

- **`transcript.py`** (unit-tested with saved samples)
  - `fetch_video(url, timeout=60)`
    - Calls `yt_dlp.YoutubeDL({...}).extract_info(url, download=False)` on a worker thread, with a 60-second limit.
    - Returns the details (title, channel or uploader, upload date, duration, description, chapters, original language) and the selected caption track.
  - Caption selection:
    - Manual subtitles first, then automatic captions.
    - Language order: `en`, then `en-*`, then the video's original language, then the first available.
    - Format order: `json3`, then `vtt`.
    - The track is downloaded through the yt-dlp opener so cookies and headers match.
  - `parse_captions(data, fmt)`: produces a list of `(start_seconds, text)` cues and removes the rolling duplicates that auto-generated captions contain.
  - `build_paragraphs(cues, chapters)`
    - Groups cues into paragraphs of about 30 to 60 seconds, breaking at sentence ends when punctuation exists, otherwise at about 45 seconds.
    - Never lets a paragraph cross a chapter boundary.
  - `render_transcript(paragraphs, chapters, url)`
    - Writes a `### Chapter` heading for each chapter and `[m:ss](url&t=N)` (or `h:mm:ss` for videos over an hour) before each paragraph.
    - For YouTube, timestamp links use `https://www.youtube.com/watch?v=ID&t=N`. For other sites, they use the original URL plus a `t` parameter where the site supports it, otherwise plain timestamp text without a link.

- **`clipper_host.bat`**: `@"%~dp0venv\Scripts\python.exe" "%~dp0clipper_host.py"`. Firefox on Windows needs a `.bat` or `.exe` as the host path.

- **`install.bat`**
  - Checks that Python 3.10 or later is present.
  - Creates `helper\venv` and installs `yt-dlp` into it.
  - Writes `quick_web_clip.json` (host name `quick_web_clip`, type `stdio`, path to `clipper_host.bat`, `allowed_extensions: ["quick-web-clip@local"]`).
  - Sets `HKCU\Software\Mozilla\NativeMessagingHosts\quick_web_clip` (default value = the manifest path). No admin rights are needed.

- **`uninstall.bat`**: removes the registry key, the host manifest and the venv.

- **Log**: `helper\clipper.log`, rotating at 1 MB with 3 files kept. It records timestamps, action, URL, result and error stack traces. Note bodies are never logged.

## 4. Message protocol (version 1)

### Requests (extension to helper)

```json
{ "v": 1, "action": "ping" }
```

```json
{
  "v": 1,
  "action": "save",
  "kind": "article",
  "destination": { "vaultPath": "C:\\...\\WorkVault", "subfolder": "Clippings" },
  "datePosition": "end",
  "clippedDate": "2026-11-05",
  "page": {
    "url": "https://...",
    "title": "...",
    "author": "...",
    "published": "2026-03-14",
    "siteName": "...",
    "description": "..."
  },
  "bodyMarkdown": "..."
}
```

`kind` is `article` or `video`. For `kind: "video"`, `bodyMarkdown` is the article conversion of the page, kept as a fallback.

### Replies (helper to extension)

```json
{ "ok": true, "version": "1.0.0", "ytDlp": "2026.10.xx" }
```

`ytDlp` is `null` when yt-dlp is not installed.

```json
{ "ok": true, "path": "C:\\...\\Note 2026-11-05.md", "kind": "video", "transcript": "auto", "warning": null }
```

`kind` is the kind actually saved. `transcript` is `manual`, `auto` or `none`.

```json
{ "ok": false, "error": "vault_not_found", "message": "Folder not found: C:\\..." }
```

Error codes: `vault_not_found`, `outside_vault`, `write_failed`, `bad_request`, `internal`.

Video-specific problems are not errors. The note is still saved, with a `warning`.

## 5. Clip flow

1. The trigger (toolbar, shortcut or menu) gives the tab plus a destination ID (menu) or nothing (default).
2. Load settings. If there are no destinations, open the options page and stop.
3. If the URL cannot be clipped, show "This page can't be clipped" and stop.
4. Set the badge to `...` (working).
5. Inject the vendored libraries and `extract.js` with `scripting.executeScript`, and receive `{kind, page, bodyMarkdown}`.
6. Send a `save` request with `runtime.sendNativeMessage("quick_web_clip", ...)`.
7. In the helper:
   - **article**: render frontmatter `{title, source, author, published, clipped, tags:[clipping]}`, then the body, then `safe_write`.
   - **video**: call `fetch_video`.
     - Success: render frontmatter `{title, source, channel, published, duration, clipped, transcript, tags:[clipping, video]}`, then `## Description`, then `## Transcript`. If there is no caption track, the transcript section says "No transcript available".
     - yt-dlp reports the URL as unsupported: save as an article using `bodyMarkdown`, with reply `kind: "article"`.
     - yt-dlp is missing, times out or fails in another way: save a video note using the page metadata, with "Transcript unavailable: <reason>" and a `warning`.
8. Show the result (section 6).

## 6. Feedback and errors

- **Success**: green badge `OK` for 2 seconds.
- **Success with warning**: amber badge `!` and a notification with the warning (e.g. "Saved without transcript: yt-dlp not installed").
- **Failure**: red badge `ERR` and a notification with the message.

| Situation | Message |
|---|---|
| Native host missing or not registered (`sendNativeMessage` rejects) | "Helper not found. Run install.bat in the helper folder." |
| No destinations | Opens the options page |
| `vault_not_found` | "Folder not found: <path>" |
| `outside_vault` | "Refused: subfolder points outside the vault" |
| `write_failed` | "Could not write file: <OS error>" |
| Unclippable page | "This page can't be clipped" |
| Content script injection fails | "Could not read this page" |
| Readability finds nothing | Whole page converted (silent) |

## 7. Note formats

### File name

`<clean title> <YYYY-MM-DD>.md` (date at the end, the default), `<YYYY-MM-DD> <clean title>.md` (date at the start) or `<clean title>.md` (no date). If the name exists, a number is added: ` (2)`, ` (3)` and so on.

### Article note

```markdown
---
title: "How Rust Lifetimes Work"
source: "https://example.com/rust-lifetimes"
author: "Jane Smith"
published: "2026-03-14"
clipped: "2026-11-05"
tags:
  - clipping
---

<article Markdown>
```

### Video note

```markdown
---
title: "Rust Lifetimes Explained"
source: "https://www.youtube.com/watch?v=abc123"
channel: "Some Channel"
published: "2026-02-01"
duration: "1:02:15"
clipped: "2026-11-05"
transcript: "manual"
tags:
  - clipping
  - video
---

## Description

<description text>

## Transcript

### Introduction

[0:00](https://www.youtube.com/watch?v=abc123&t=0) So today we're going to look at...

[0:42](https://www.youtube.com/watch?v=abc123&t=42) The first thing to understand is...
```

Empty fields are left out of the frontmatter. Dates in the frontmatter are always `YYYY-MM-DD`. Obsidian shows them in the user's locale format.

## 8. Testing

### Helper (pytest, offline)

- `make_filename`: illegal characters, reserved names, trailing dots, length trimming, empty title, each date position.
- `render_frontmatter`: quotes, colons, newlines and Unicode in values, and empty fields left out.
- `safe_write`:
  - writes into a temporary vault
  - creates the subfolder
  - numbers duplicate names
  - rejects `..\..` subfolders and absolute subfolders
  - errors when the vault is missing
  - leaves no temporary file behind on failure
- `parse_captions` and `build_paragraphs`: saved `json3` and `vtt` samples (manual, auto with rolling duplicates, with chapters, without chapters, over an hour).
- `render_transcript`: timestamp formats and links.
- Protocol: encoding and decoding the length-prefixed frames, and dispatching `ping` and `save` with a fake stdin and stdout.

### Extension (`node --test`, Node 24 present)

- `classify.js`: URL patterns and `og:type`.
- `settings.js`: defaults, validation, picking the default destination, the menu model.
- `dates.js`: local date, and normalising published dates in common formats.

### Manual end-to-end checklist (temporary load through `about:debugging`)

- News article, blog post and Wikipedia page using the toolbar, the shortcut and the right-click menu to a second destination.
- YouTube video with chapters, YouTube video without captions, a YouTube Short, and a Vimeo video.
- Vault folder missing, helper not installed, and an `about:` page.
- A duplicate clip of the same page produces the `(2)` file.

## 9. Install and distribution

1. Run `helper\install.bat` once.
2. Development: load `extension\manifest.json` through `about:debugging` > This Firefox > Load Temporary Add-on. It is removed when Firefox restarts.
3. Permanent use: sign as an unlisted add-on with `web-ext sign --channel=unlisted`. This needs a free addons.mozilla.org account and API credentials, which the user creates. Install the returned `.xpi`.
4. The shortcut can be changed under Add-ons > gear icon > Manage Extension Shortcuts.

Risk: a Firefox managed by company policy may block unlisted add-ons or native messaging. Check this before relying on the tool at work.

## 10. Project layout

```
quick-web-clip-firefox-extension/
  extension/
    manifest.json
    background.js
    content/extract.js
    lib/classify.js
    lib/settings.js
    lib/dates.js
    options/options.html
    options/options.js
    options/options.css
    vendor/Readability.js
    vendor/turndown.js
    vendor/turndown-plugin-gfm.js
    icons/
  helper/
    clipper_host.py
    notes.py
    transcript.py
    clipper_host.bat
    install.bat
    uninstall.bat
    requirements.txt
    tests/
  tests/                # node tests for extension/lib
  docs/superpowers/specs/
  README.md
```
