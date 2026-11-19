# Quick Web Clip

A Firefox, Chrome and Edge extension that saves the current page into an Obsidian vault as a Markdown note with one action: a toolbar click or the keyboard shortcut Alt+Shift+C. There is no popup and no Save dialog. It works whether or not Obsidian is running.

- Articles are reduced to the main content (Readability) and converted to Markdown.
- Videos (YouTube, Vimeo, Dailymotion, TED) are saved with details, description and a timestamped transcript, with chapter headings where the video has chapters.
- Several destinations (vault plus subfolder) can be configured, one marked as default. The others are reached from the right-click "Save to" menu.
- Select part of a page first to save only the selection (text and images, as they are). With nothing selected, the whole page is clipped. This suits Teams chats, where you can select just the messages you want: each message is saved under a "**Sender** date time" line.
- Images that only the open tab can show (Microsoft Teams chat images and other `blob:` images) are saved into an `attachments` folder beside the note. Teams images also link to the original image online, which opens in a browser signed in to Teams.
- The clip date and time go in the "clipped" property and the file name, for example `Title 2026-11-06 2.05 pm.md`. Choose 12-hour or 24-hour time in Options.
- A clip never overwrites an existing file: a duplicate name gets a number, for example `Title 2026-11-06 2.05 pm (2).md`.

The extension talks to a small Python helper through native messaging. The helper writes the files and calls yt-dlp for video transcripts.

## Prerequisites

- Windows 11
- Python 3.10 or later, available through the `py` launcher
- Firefox 128 or later, Chrome 120 or later, or Edge 120 or later
- Node 20 or later, only needed to run the tests or to sign the extension

## Install the helper

Run once from the repository folder:

```
helper\install.bat
```

This creates `helper\venv`, installs yt-dlp into it, writes `helper\quick_web_clip.json` and `helper\quick_web_clip_chromium.json`, and registers the native host for Firefox, Chrome and Edge under `HKCU\Software\Mozilla\NativeMessagingHosts\quick_web_clip`, `HKCU\Software\Google\Chrome\NativeMessagingHosts\quick_web_clip` and `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\quick_web_clip`. No administrator rights are needed.

## Load the extension (temporary)

1. In Firefox open `about:debugging#/runtime/this-firefox`.
2. Click "Load Temporary Add-on" and select `extension\manifest.json`.
3. Open the extension options page, add at least one destination (label, full vault folder path, optional subfolder) and mark one as default. The status line on that page confirms that the helper is connected.

A temporary add-on is removed when Firefox restarts.

## Chrome and Edge

The Chrome and Edge versions are built from the same source. Build them from the repository folder:

```
py -3 tools\build_chromium.py
```

This writes `dist\chrome` and `dist\edge` (the same files, one folder for each browser). Then:

1. Open `chrome://extensions` (Chrome) or `edge://extensions` (Edge).
2. Turn on Developer mode.
3. Click "Load unpacked" and select `dist\chrome` or `dist\edge`.
4. Open the extension options page (Details, Extension options), add a destination and check that the helper is connected.

The extension ID is always `kcdeoockaleljccbljbelmpehlnnceop`, fixed by the `key` in the built manifest, which is the ID the helper allows. An unpacked extension stays installed when the browser restarts. After changing the source, run the build again and click the reload button on the extensions page. Run `helper\install.bat` again if the helper was installed before version 1.4.0, so that Chrome and Edge are registered.

In Chrome and Edge the shortcut is changed at `chrome://extensions/shortcuts` or `edge://extensions/shortcuts`.

## Permanent install in Firefox (unlisted signing)

Sign the extension as an unlisted add-on, then install the returned `.xpi`. You need a free addons.mozilla.org account. Create an API key and secret yourself under Tools > Manage API Keys, then run:

```
npx web-ext@8 sign --channel=unlisted --source-dir extension --api-key <YOUR_JWT_ISSUER> --api-secret <YOUR_JWT_SECRET>
```

Replace the two placeholders with your own credentials and never commit them. The signed file is written to `web-ext-artifacts\`. Open it in Firefox to install it.

## Using it

- Toolbar button or Alt+Shift+C: save to the default destination.
- Right-click the page, a selection, an image or the toolbar button, then "Save to": save to any configured destination.
- The toolbar badge shows `...` while working, then `OK` (green), `!` (amber, saved with a warning) or `ERR` (red). Warnings and errors also appear as notifications.

### Change the shortcut

Open `about:addons`, click the gear icon, choose "Manage Extension Shortcuts" and change the shortcut for Quick Web Clip.

## Update yt-dlp

Video sites change often. If transcripts stop working, update yt-dlp:

```
helper\venv\Scripts\python.exe -m pip install -U yt-dlp
```

yt-dlp may warn that no JavaScript runtime is installed. Installing deno (https://deno.com) is optional but recommended for YouTube.

## Uninstall

```
helper\uninstall.bat
```

This removes the registry keys, the host manifests and the venv. Then remove the extension in `about:addons`, `chrome://extensions` or `edge://extensions`.

## Troubleshooting

- The helper log is `helper\clipper.log` (rotates at 1 MB, 3 files kept). It records timestamps, actions, URLs, results and error stack traces, never note bodies.
- "Helper not found. Run install.bat in the helper folder.": the native host is not registered. Run `helper\install.bat` again.
- "Folder not found: ...": the vault folder in the destination does not exist. Create it or fix the path in the options page.
- "Refused: subfolder points outside the vault": the subfolder contains `..` or is an absolute path.
- Saved without a transcript: the badge turns amber and the notification says why (yt-dlp missing, timed out, site needs a login, or the video has no captions). Updating yt-dlp fixes many cases.
- Some sites, Vimeo in particular, can require a logged-in session for yt-dlp. The note is still saved with the page metadata and a "Transcript unavailable" line.
- `about:` pages, `moz-extension:` pages, `view-source:`, the built-in PDF viewer and addons.mozilla.org cannot be clipped.

### Managed Firefox caveat

A Firefox managed by company policy may block unlisted add-ons or native messaging. Check this before relying on the tool at work.

## Development

```
helper\venv\Scripts\python.exe -m pytest helper -q
npm test
npx web-ext@8 lint --source-dir extension
py -3 tools\build_chromium.py
```

## Verified

### Helper checks (automated)

These were run on 06/11/2026 by driving the installed helper (`helper\clipper_host.bat`) with framed native messages, writing to a temporary vault that was deleted afterwards. YouTube checks used yt-dlp 2026.10.26 over the network.

| Check | Steps | Expected | Date | Result |
|---|---|---|---|---|
| Ping | Send `{"v":1,"action":"ping"}` | `ok`, version 1.0.0, yt-dlp version | 06/11/2026 | Pass |
| Article save | Send a `save` request, kind article, subfolder `Clippings`, date at end, title containing `:`, `/` and `?` | File `How Rust Lifetimes Work A B 2026-11-06.md` in `Clippings`, frontmatter title, source, author, published, clipped, tags, then the body (spec section 7) | 06/11/2026 | Pass |
| Duplicate article save | Send the same request again | Second file `... 2026-11-06 (2).md`, first file untouched | 06/11/2026 | Pass |
| Missing vault folder | Save to a vault path that does not exist | `ok:false`, `vault_not_found`, "Folder not found: <path>", nothing created | 06/11/2026 | Pass |
| YouTube video with chapters | Save kind video, `youtube.com/watch?v=aya4NsO177A&list=PLfoo` | Video frontmatter (channel, duration 5:07, transcript auto, tags clipping and video), Description, Transcript with one `###` heading per chapter (8) and `[m:ss](...&t=N)` links, `&list=` not carried into links | 06/11/2026 | Pass |
| YouTube Short | Save kind video, `youtube.com/shorts/GR9lNJISviw` | Note saved, transcript none, "No transcript available" | 06/11/2026 | Pass |
| Vimeo | Save kind video, `vimeo.com/76979871` | Transcript from Vimeo if available | 06/11/2026 | Not tested (site): Vimeo requires a login for yt-dlp. The fallback was verified: note saved from page metadata, transcript none, `warning` returned, "Transcript unavailable" line written |

### Manual checks in Firefox (not run yet)

These checks have not been run yet. They need a real Firefox, which could not be driven when this README was written. Fill in the Date (DD/MM/YYYY) and Result columns as you work through them. Load the extension first and add a destination such as `C:\Temp\qwc-test` (create the folder first) with subfolder `Clippings`.

| Check | Steps | Expected | Date | Result |
|---|---|---|---|---|
| News article, toolbar | Open a news article, click the toolbar button | Badge `...` then green `OK`, then clears after 2 s. Note in the destination with article layout and tags `clipping` | | |
| News article, shortcut | Open a news article, press Alt+Shift+C | Same as above | | |
| Blog post | Open a blog post, press Alt+Shift+C | Main content only, no navigation or comments | | |
| Wikipedia page | Open a Wikipedia article, press Alt+Shift+C | Clean Markdown with headings, tables and links, absolute image links | | |
| Right-click to second destination | Configure two destinations, right-click the page, Save to, choose the non-default one | Note written to the chosen destination, not the default | | |
| Toolbar right-click menu | Right-click the toolbar button, Save to, choose a destination | Note written to the chosen destination | | |
| YouTube video with chapters | Open a YouTube video with chapters, press Alt+Shift+C | Video note with description, chapter headings and timestamped transcript. Timestamp links open the video at that time | | |
| YouTube video without captions | Open a YouTube video with no captions | Note saved with "No transcript available", badge `OK` | | |
| YouTube Short | Open a `youtube.com/shorts/` URL, press Alt+Shift+C | Note saved as a video note | | |
| YouTube watch URL with list | Open a `watch?v=...&list=...` URL, press Alt+Shift+C | Video note for that video only, links without the `list` parameter | | |
| Vimeo video | Open a Vimeo video page, press Alt+Shift+C | Note saved. If Vimeo blocks yt-dlp, amber `!` and a "Saved without transcript" notification | | |
| YouTube in-page navigation | Open a video, click another video in the sidebar, press Alt+Shift+C | The note is for the second video | | |
| Missing vault folder | Set a destination to a folder that does not exist, clip a page | Red `ERR` and notification "Folder not found: <path>" | | |
| Helper not installed | Run `helper\uninstall.bat`, clip a page, then run `helper\install.bat` again | Red `ERR` and notification "Helper not found. Run install.bat in the helper folder." | | |
| Clip time | Clip any article with Time format set to 12-hour, then again with 24-hour | First file `Title 2026-11-19 2.05 pm.md` with `clipped: "2026-11-19 2:05 pm"`; second `Title 2026-11-19 14.05.md` with `clipped: "2026-11-19 14:05"` | | |
| about: page | Open `about:preferences`, press Alt+Shift+C | Notification "This page can't be clipped" | | |
| Duplicate clip | Clip the same page twice | Second file has the ` (2)` suffix and the first is unchanged | | |
| No destinations | Clear the destinations in storage, press the shortcut | The options page opens | | |
| Options: menu list | Add two destinations, open the right-click Save to menu | Both are listed, one marked " (default)" | | |
| Options: default and order | Switch the default, delete the default, reorder | The menu follows each change | | |
| Options: invalid path | Enter a relative vault path | Message "Vault folder must be a full path" | | |
| Options: helper status | Open the options page | "Helper connected (v1.4.0), yt-dlp <version>" (or "yt-dlp not installed", or "Helper not found. Run install.bat in the helper folder.") | | |
| Options: persistence | Reload the extension | Settings are still present | | |
| Teams chat with images | Open a Teams chat (teams.cloud.microsoft) that shows pasted images, press Alt+Shift+C | Images saved in `attachments` beside the note, each shown in Obsidian and linked to its `asyncgw.teams.microsoft.com` URL. No `blob:` links in the note | | |
| Teams selection | In a Teams chat, select a few messages including an image, press Alt+Shift+C | Note holds only the selected messages. The image is saved in `attachments` and linked to its original | | |
| Selection on a video page | On a YouTube page, select some description text, press Alt+Shift+C | Note holds only the selected text, saved as an article (no transcript) | | |
| Options: two tabs | Open the options page in two tabs, change a setting in one | The change appears in the other | | |
