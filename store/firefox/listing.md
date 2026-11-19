# Firefox Add-ons (AMO) listing

Paste each section into the matching field on addons.mozilla.org (Developer Hub, Submit a New Version, "On this site").

Upload: `dist/store/quick-web-clip-firefox-<version>.zip` (made by `py -3 tools/package_stores.py`).
Platforms: Firefox only. Untick Firefox for Android: the helper cannot run on Android.

## Name

Quick Web Clip

## Add-on URL (slug)

quick-web-clip

## Summary (250 characters at most)

Save the page you are reading to your Obsidian vault as a clean Markdown note in one click. Articles, video transcripts, selections and Teams chats. Works with a small helper you install on Windows; nothing leaves your computer.

## Description

Quick Web Clip saves the current page into your Obsidian vault (or any folder) as a Markdown note, with one click on the toolbar button or the shortcut Alt+Shift+C. There is no popup and no Save dialog, and Obsidian does not need to be running.

**What it saves**

- **Articles:** the main content only (using Mozilla's Readability), converted to clean Markdown with a properties block: title, source address, author, published date, clip date and time, and a "clipping" tag.
- **Videos** (YouTube, Vimeo, Dailymotion, TED): the video details, the description, and a timestamped transcript with links that open the video at that moment. Videos with chapters get one heading per chapter.
- **Selections:** select part of a page first and only that part is saved, text and images as they are.
- **Microsoft Teams chats:** select the messages you want. Each message is saved under one "Sender date time" line, and chat images are saved into an attachments folder beside the note.

**How it works for you**

- Add one or more destinations (a vault folder plus an optional subfolder) and mark one as the default. The toolbar button saves to the default; right-click, "Save to" reaches the others.
- The clip date and time go in the note properties and the file name, with a 12-hour or 24-hour time option, and the date at the start or end of the name.
- A clip never overwrites an existing note: a duplicate name gets a number.
- The toolbar badge shows progress and the result, and a notification explains any warning or error.

**Requirements**

- Windows (tested on Windows 11).
- Python 3.10 or later (from python.org), which the helper runs on.
- The Quick Web Clip helper, installed once from https://github.com/aenemo/quick-web-clip-firefox-extension/releases/latest. The extension uses it to write files to your vault (browsers cannot write to your folders by themselves). The options page shows whether the helper is connected.

**Privacy**

Nothing you clip is sent to the developer or to any other service. Notes and images are written only to folders on your computer. There is no account, no analytics and no tracking. Video transcripts are requested from the video site itself. Full policy: https://github.com/aenemo/quick-web-clip-firefox-extension/blob/main/store/PRIVACY.md

Quick Web Clip is not made by or affiliated with Obsidian or Microsoft.

## Categories

- Firefox: Other (also suitable: Bookmarks)

## Tags

obsidian, markdown, clipper, notes, transcript

## Support website

https://github.com/aenemo/quick-web-clip-firefox-extension/issues

## License

MIT License (the `LICENSE` file in the repository).

## Privacy policy

Tick "This add-on has a privacy policy" and paste the whole of `store/PRIVACY.md`.

## Data collection

The manifest declares `data_collection_permissions: required: ["none"]`. That is correct: the add-on transmits no data to the developer or third parties.

## Version notes

Paste the "Version notes" section of `store/firefox/version-notes.md`.

## Notes to reviewer

Quick Web Clip uses native messaging to talk to a helper program (Python, Windows) that writes Markdown files into a folder the user chooses. The helper's source is in the same repository as the add-on: https://github.com/aenemo/quick-web-clip-firefox-extension, folder `helper`, installed with `helper\install.bat`, which registers the native host `quick_web_clip` under HKCU\Software\Mozilla\NativeMessagingHosts.

To test without the helper: click the toolbar button on any article. The badge shows ERR and a notification says "Helper not found. Run install.bat in the helper folder."; the options page says the same. This is the expected behaviour without the helper.

To test with the helper: run `helper\install.bat` (needs Python 3.10 or later), open the add-on options, add a destination such as C:\Temp\qwc-test (create the folder first), then clip an article. A Markdown file appears in that folder.

Third-party libraries, copied unmodified from npm (see `vendor/VERSIONS.txt`):
- vendor/Readability.js: @mozilla/readability 0.6.0. The two innerHTML warnings from the validator are in this library.
- vendor/turndown.js: turndown 7.2.0 (lib/turndown.browser.umd.js).
- vendor/turndown-plugin-gfm.js: turndown-plugin-gfm 1.0.2 (dist/turndown-plugin-gfm.js).

No code is minified, bundled or generated, so no separate source upload is needed. The add-on loads no remote code.
