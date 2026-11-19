# Quick Web Clip for Firefox: version notes

## Version notes

Paste this section into the "Version notes" field for version 1.5.1.

---

**1.5.1 (19/11/2026): first listed release on addons.mozilla.org**

Quick Web Clip is now listed on Firefox Add-ons. If you used an earlier self-installed copy, this version replaces it and keeps your settings, because the add-on ID is the same.

New in this version
- A 128 px icon for the Add-ons Manager and the add-on page.
- The helper now registers only for Firefox. The Chrome and Edge versions have their own projects and helpers.

Changed
- Needs Firefox 140 or later (Firefox 140 ESR is supported). This is the first Firefox version that supports the add-on's "no data collection" declaration.

Helper
- Update the helper as well (helper version 1.5.1, from https://github.com/aenemo/quick-web-clip-firefox-extension/releases/latest) and run install.bat again. The options page shows the helper version that is connected.

---

## Full history

### 1.5.1 (19/11/2026)
- MIT licence added.
- The helper is published as a zip on GitHub (Releases), with install notes, and the listing links to the GitHub project for support and the privacy policy.
- The Chrome and Edge versions moved to their own repositories; the helper here registers only for Firefox.

### 1.5.0 (19/11/2026)
- Prepared for listing on addons.mozilla.org (not published).
- 128 px icon added.
- Helper reads the allowed extension IDs from `extension_ids.json`.

### 1.4.1 (19/11/2026)
- Minimum Firefox version raised from 128 to 140 (Firefox for Android 142), clearing two Mozilla validation warnings.

### 1.4.0 (19/11/2026)
- Chrome and Edge versions built from the same source. No change for Firefox users, apart from the helper installer now registering for all three browsers.

### 1.3.0 (19/11/2026)
- The clip time is saved with the date, in the "clipped" property (`2026-11-19 2:05 pm`) and the file name (`Title 2026-11-19 2.05 pm.md`). File names use a dot instead of the colon, which Windows does not allow.
- New "Time format" setting: 12-hour (the default) or 24-hour.
- New icon: a red down arrow with "MD" in white on purple, drawn sharp at every size.

### 1.2.0 (19/11/2026)
- Clip a selection: select text or images first and only the selection is saved, exactly as it is. With nothing selected the whole page is clipped as before.
- The right-click "Save to" menu also appears on selections and images.
- Microsoft Teams chats: each selected message gets one "**Sender** date time" line; Teams' hidden preview lines, profile pictures and reaction descriptions are left out.
- Fixed: images did not show in Obsidian when the note name had a comma. Links keep commas, and characters that break Obsidian links (# ^ [ ] |) are left out of image file names.

### 1.1.1 (19/11/2026)
- Fixed Teams images that had already loaded on screen not being saved.
- An image that cannot be downloaded no longer leaves a broken placeholder link.

### 1.1.0 (19/11/2026)
- Microsoft Teams chat images and other images that only the open tab can show are saved into an `attachments` folder beside the note. Teams images also link to the original online.

### 1.0.0 to 1.0.2 (06/11/2026 to 13/11/2026)
- First release: one-click clipping of articles (Readability, converted to Markdown) and videos (YouTube, Vimeo, Dailymotion, TED, with details, description and a timestamped transcript with chapter headings), several destinations with a default, the right-click "Save to" menu, the Alt+Shift+C shortcut, and notes that never overwrite an existing file.
