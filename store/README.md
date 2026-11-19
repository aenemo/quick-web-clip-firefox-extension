# Publishing to the browser stores

Everything needed to submit Quick Web Clip to Firefox Add-ons (addons.mozilla.org, AMO). The Chrome and Edge versions have their own repositories: https://github.com/aenemo/quick-web-clip-chrome-extension and https://github.com/aenemo/quick-web-clip-edge-extension.

| File | Use |
|---|---|
| `PRIVACY.md` | Privacy policy, linked from GitHub. AMO also takes the text directly. |
| `firefox/listing.md` | Every AMO field, plus notes to the reviewer. |
| `firefox/version-notes.md` | A short "Version notes" section to paste, then the full history. |

AMO uses the 128 px icon from the add-on itself (`extension/icons/icon-128.png`, drawn by `tools/make_store_images.py`).

## 1. Addresses used in the listings

The listings already use these GitHub addresses. There is no support email address; support is through GitHub issues.

| Field | Address |
|---|---|
| Homepage and source | https://github.com/aenemo/quick-web-clip-firefox-extension |
| Support | https://github.com/aenemo/quick-web-clip-firefox-extension/issues |
| Privacy policy | https://github.com/aenemo/quick-web-clip-firefox-extension/blob/main/store/PRIVACY.md |
| Helper download | https://github.com/aenemo/quick-web-clip-firefox-extension/releases/latest (attach the helper zip to each GitHub release) |

The repository must be public for these addresses to work for the stores and their reviewers.

## 2. Build the upload zips

```
py -3 tools\package_stores.py
```

This writes to `dist\store\`:
- `quick-web-clip-firefox-<version>.zip`
- `quick-web-clip-helper-<version>.zip` (the helper, for the GitHub release)

Run the tests and the Firefox lint first (see the main README, Development).

## 3. Take screenshots

AMO screenshots are optional but recommended (1280 x 800 works well). Suggested set:
1. An article in the browser, with the green OK badge on the toolbar button.
2. The saved note open in Obsidian, showing the properties and clean Markdown.
3. The right-click "Save to" menu with two destinations.
4. The options page with destinations, date position and time format.
5. A YouTube note in Obsidian with the transcript and chapter headings.

Use a test vault, not real notes, and avoid showing names, emails or chat content.

## 4. Submit

Firefox (addons.mozilla.org, free):
1. Developer Hub, the existing Quick Web Clip add-on (same ID `quick-web-clip@local`), Upload New Version, choose "On this site".
2. Upload the Firefox zip; untick Android.
3. Fill in the listing from `firefox/listing.md`, the version notes and the notes to reviewer.
4. Create a GitHub release for the same version and attach the helper zip, so the "releases/latest" link in the listing finds it.

The add-on ID stays `quick-web-clip@local` (`helper/extension_ids.json`), so the helper needs no change for the listed version.

## Updating a published version

1. Bump the version everywhere (manifest, `helper/clipper_host.py`, `helper/tests/test_host.py`, README, changelog) and add a "Version notes" section to each `version-notes.md`.
2. Run `py -3 tools\package_stores.py`.
3. Upload the new Firefox zip, and attach the new helper zip to the GitHub release.
