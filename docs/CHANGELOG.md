# Changelog

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
