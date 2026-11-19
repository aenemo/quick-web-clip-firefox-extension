# Quick Web Clip privacy policy

Last updated: 19/11/2026

Quick Web Clip is a Firefox add-on that saves web pages as Markdown notes in a folder on your own computer, such as an Obsidian vault. It works together with a small helper program that you install on the same computer.

## Summary

- Quick Web Clip does not collect, store, sell or share any of your data with the developer or with anyone else.
- Everything you clip is written only to folders on your own computer that you choose.
- There are no accounts, no analytics, no tracking, no advertising and no remote code.

## What the extension reads

When you click the toolbar button, press the shortcut, or choose "Save to" from the right-click menu, the extension reads the page in the current tab:

- the page address, title, author, publish date and description;
- the main text of the page, or only the part you selected;
- images in the clipped content that only the open tab can show (for example images in a Microsoft Teams chat).

It reads a page only when you ask it to clip that page. It does not watch your browsing and does not read any other tab.

## Where that information goes

The extension sends what it read to the Quick Web Clip helper on your computer through the browser's native messaging feature. This connection never leaves your computer. The helper:

- writes the note (a Markdown file) and any images into the folder you set up in the extension options;
- keeps a log file (`clipper.log` in the helper folder) with the time, the action, the page address and the result of each clip, so problems can be traced. The log never contains the note text. It is kept on your computer, limited to about 4 MB, and you can delete it at any time.

## Network requests

Quick Web Clip makes no requests to the developer or to any analytics or advertising service. The only network requests are made on your behalf, to the site you are clipping:

- For images that only the open tab can show, the extension fetches the image from the same site, the same way the page itself does.
- For videos (YouTube, Vimeo, Dailymotion and TED), the helper uses the open source tool yt-dlp to ask the video site for the video details and captions, so the note can include a transcript. This request goes only to that video site.

## What is stored in the browser

The extension stores its settings in the browser's own extension storage on your computer: the destinations you add (a label, a folder path and an optional subfolder), which one is the default, where the date goes in file names, and the time format. These settings are not synced or sent anywhere by the extension.

## Permissions and why they are needed

- **Native messaging:** to pass the clip to the helper on your computer, which writes the files.
- **Active tab and scripting:** to read the page in the current tab, only when you clip it.
- **Context menus:** for the right-click "Save to" menu.
- **Storage:** to keep your settings.
- **Notifications:** to tell you when a clip was saved with a warning or could not be saved.

## Children

Quick Web Clip is a general productivity tool and is not directed at children.

## Changes to this policy

If this policy changes, the new version will be published at the same address with a new "Last updated" date.

## Contact

Questions about this policy: open an issue at https://github.com/aenemo/quick-web-clip-firefox-extension/issues
