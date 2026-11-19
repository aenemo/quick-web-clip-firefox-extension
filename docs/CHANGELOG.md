# Changelog

## 1.5.1 (19/11/2026)
- The Chrome and Edge versions moved to their own repositories (https://github.com/aenemo/quick-web-clip-chrome-extension and https://github.com/aenemo/quick-web-clip-edge-extension). This repository is now Firefox only: `tools/build_chromium.py` and the Chrome and Edge store files are removed.
- The helper registers only for Firefox. `helper/extension_ids.json` names the browser and the add-on ID; the same `install_host.py` serves all three repositories. Uninstalling removes only the Firefox registration, and the `quick_web_clip_chromium.json` file left by 1.4.0 to 1.5.0.
- `tools/package_stores.py` builds the Firefox zip and the helper zip; `tools/make_store_images.py` draws the 128 px icon.
- MIT licence (`LICENSE`).
- The store listings use the GitHub project for the homepage, support (issues), privacy policy and helper download. No support email address is listed.
- `tools/package_stores.py` also builds `quick-web-clip-helper-<version>.zip` for the GitHub release, with new install notes (`helper/INSTALL.txt`). The listings now say the helper needs Python 3.10 or later.

## 1.5.0 (19/11/2026)
- Ready for the browser stores: `tools/package_stores.py` builds the upload zips for Firefox, Chrome and Edge into `dist/store` (the Chrome and Edge zips have no `key`, so the stores assign their own IDs).
- The helper reads the extension IDs it accepts from `helper/extension_ids.json`. Add the Chrome and Edge store IDs there once known and run `install.bat` again.
- 128 px icon added to the manifest. `tools/make_store_images.py` draws it with the store icon, the Edge logo and the promo tile.
- New `store` folder: privacy policy, listing text, permission reasons, reviewer notes and version notes for each store.

## 1.4.1 (19/11/2026)
- The minimum Firefox version is now 140 (Firefox for Android 142), the first versions that support the data collection setting in the manifest. This clears two Mozilla validation warnings. Firefox 140 ESR is supported.

## 1.4.0 (19/11/2026)
- Chrome and Edge versions: `tools/build_chromium.py` builds `dist/chrome` and `dist/edge` from the same source, to load unpacked with Developer mode on. A fixed key in the built manifest keeps the extension ID the same on every machine.
- `install.bat` now also registers the helper for Chrome and Edge (`helper/quick_web_clip_chromium.json`), and `uninstall.bat` removes those keys too. Run `install.bat` again after updating.
- `compat.js` lets the same scripts run in Chrome and Edge, which name the extension API `chrome` and the context menu API `contextMenus`.

## 1.3.0 (19/11/2026)
- The clip time is saved with the date: in the "clipped" property (`2026-11-19 2:05 pm`) and in the file name (`Title 2026-11-19 2.05 pm.md`). File names use a dot in place of the colon, which Windows does not allow.
- New setting "Time format": 12-hour (2:05 pm, the default) or 24-hour (14:05).
- New icon: a dark-edged red down arrow with "MD" in white on the same purple. The letters are drawn at each size so they stay sharp, and 16 and 32 px sizes are included for the toolbar. `design/icon-options/make_icons2.py` redraws it (option G).

## 1.2.0 (19/11/2026)
- Clip a selection: when text or images are selected on the page, only the selection is saved, as it is (no article clean-up, and no video transcript). With nothing selected, the whole page is clipped as before. This works on any site, including Teams chats, where selected images are saved and linked to their originals.
- The right-click "Save to" menu now also appears when right-clicking a selection or an image.
- A Teams chat selection is tidied: each message gets one "**Sender** date time" line, and the hidden preview line, profile picture and reaction description Teams adds to every message are left out. Profile pictures only load while signed in to Teams, so they showed as broken images.
- Fixed: saved images did not show in Obsidian when the note name had a comma (as Teams chat names do). Links now keep commas and similar characters as they are, and characters that break Obsidian links (# ^ [ ] |) are left out of image file names.

## 1.1.1 (19/11/2026)
- Fixed Teams images that had already loaded on screen: they were not recognised, so the note kept placeholder `qwc-attachment:0` links and no files were saved. The image is now read from the copy already in the tab.
- An image that cannot be downloaded no longer leaves a placeholder link: a Teams image keeps its online link and other `blob:` images are left out.

## 1.1.0 (19/11/2026)
- Microsoft Teams chat images are now saved with the note. Each image is stored in an `attachments` folder beside the note and links to the original image online (opens when signed in to Teams). Previously the note held a `blob:` link that only worked inside the Teams tab.
- Other `blob:` images are saved the same way, or dropped when they cannot be read.
- Reload the extension to update. The helper runs from this folder, so it updates without reinstalling.

## 1.0.2 (13/11/2026)
- Added this changelog.

## 1.0.1 (13/11/2026)
- Ignore the AMO upload id file.

## 1.0.0 (06/11/2026)
- First release.
