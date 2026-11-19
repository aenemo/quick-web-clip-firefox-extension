"""Register (or remove) the Quick Web Clip native messaging host for one browser.

The browser and the extension IDs the helper answers to come from extension_ids.json
beside this file, so the same script serves the Firefox, Chrome and Edge repositories.
"""
import argparse
import json
import re
import winreg
from pathlib import Path

HOST_NAME = "quick_web_clip"
MANIFEST_NAME = HOST_NAME + ".json"
# Written by helper versions 1.4.0 to 1.5.0, which registered every browser at once.
OLD_CHROMIUM_MANIFEST_NAME = HOST_NAME + "_chromium.json"
BROWSERS = {
    "firefox": ("Firefox", r"Software\Mozilla\NativeMessagingHosts" + "\\" + HOST_NAME),
    "chrome": ("Chrome", r"Software\Google\Chrome\NativeMessagingHosts" + "\\" + HOST_NAME),
    "edge": ("Edge", r"Software\Microsoft\Edge\NativeMessagingHosts" + "\\" + HOST_NAME),
}
# Fill in the store ID once the store has assigned it (shown in the store's dashboard
# after the first upload), then run install.bat again.
IDS_FILE = Path(__file__).resolve().parent / "extension_ids.json"
_CHROMIUM_ID = re.compile(r"[a-p]{32}")


def load_ids(path: Path = IDS_FILE) -> dict:
    ids = json.loads(path.read_text(encoding="utf-8"))
    browser = ids.get("browser")
    if browser not in BROWSERS:
        raise ValueError(f"{path.name}: browser must be one of {', '.join(BROWSERS)}, not {browser!r}")
    for name, value in ids["ids"].items():
        if value and browser != "firefox" and not _CHROMIUM_ID.fullmatch(value):
            raise ValueError(f"{path.name}: {name} is not a valid extension ID: {value!r}")
    if not allowed_ids(ids):
        raise ValueError(f"{path.name}: no extension ID filled in")
    return ids


def allowed_ids(ids: dict) -> list[str]:
    """Every ID that is filled in, in file order, no repeats."""
    return list(dict.fromkeys(v for v in ids["ids"].values() if v))


def build_manifest(helper_dir: Path, ids: dict | None = None) -> dict:
    ids = ids or load_ids()
    m = {
        "name": HOST_NAME,
        "description": "Quick Web Clip helper",
        "path": str(helper_dir / "clipper_host.bat"),
        "type": "stdio",
    }
    if ids["browser"] == "firefox":
        m["allowed_extensions"] = allowed_ids(ids)
    else:
        # Chrome and Edge name the allowed extensions by origin, not by add-on ID.
        m["allowed_origins"] = [f"chrome-extension://{i}/" for i in allowed_ids(ids)]
    return m


def install(helper_dir: Path, reg=winreg, ids: dict | None = None) -> Path:
    ids = ids or load_ids()
    manifest_path = helper_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(build_manifest(helper_dir, ids), indent=2), encoding="utf-8")
    key = reg.CreateKey(reg.HKEY_CURRENT_USER, BROWSERS[ids["browser"]][1])
    reg.SetValue(key, "", reg.REG_SZ, str(manifest_path))
    return manifest_path


def uninstall(helper_dir: Path, reg=winreg, ids: dict | None = None) -> None:
    ids = ids or load_ids()
    try:
        reg.DeleteKey(reg.HKEY_CURRENT_USER, BROWSERS[ids["browser"]][1])
    except OSError:
        pass  # FileNotFoundError: key not present
    (helper_dir / MANIFEST_NAME).unlink(missing_ok=True)
    (helper_dir / OLD_CHROMIUM_MANIFEST_NAME).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    helper_dir = Path(__file__).resolve().parent
    label = BROWSERS[load_ids()["browser"]][0]
    if args.uninstall:
        uninstall(helper_dir)
        print(f"Helper uninstalled for {label}.")
    else:
        print(f"Registered for {label}:", install(helper_dir))


if __name__ == "__main__":
    main()
