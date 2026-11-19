# Changelog

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
