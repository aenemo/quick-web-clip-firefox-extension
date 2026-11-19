"""Register (or remove) the Quick Web Clip native messaging host for Firefox, Chrome and Edge."""
import argparse
import json
import winreg
from pathlib import Path

HOST_NAME = "quick_web_clip"
KEY_PATH = r"Software\Mozilla\NativeMessagingHosts" + "\\" + HOST_NAME
CHROMIUM_KEY_PATHS = (
    r"Software\Google\Chrome\NativeMessagingHosts" + "\\" + HOST_NAME,
    r"Software\Microsoft\Edge\NativeMessagingHosts" + "\\" + HOST_NAME,
)
MANIFEST_NAME = HOST_NAME + ".json"
CHROMIUM_MANIFEST_NAME = HOST_NAME + "_chromium.json"
# The Chrome and Edge extension ID, fixed by the key in tools/build_chromium.py.
CHROMIUM_ID = "kcdeoockaleljccbljbelmpehlnnceop"


def build_manifest(helper_dir: Path) -> dict:
    return {
        "name": HOST_NAME,
        "description": "Quick Web Clip helper",
        "path": str(helper_dir / "clipper_host.bat"),
        "type": "stdio",
        "allowed_extensions": ["quick-web-clip@local"],
    }


def build_chromium_manifest(helper_dir: Path) -> dict:
    """Chrome and Edge name the allowed extension by origin, not by add-on ID."""
    m = build_manifest(helper_dir)
    del m["allowed_extensions"]
    m["allowed_origins"] = [f"chrome-extension://{CHROMIUM_ID}/"]
    return m


def _register(reg, key_path: str, manifest_path: Path) -> None:
    key = reg.CreateKey(reg.HKEY_CURRENT_USER, key_path)
    reg.SetValue(key, "", reg.REG_SZ, str(manifest_path))


def install(helper_dir: Path, reg=winreg) -> Path:
    manifest_path = helper_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(build_manifest(helper_dir), indent=2), encoding="utf-8")
    _register(reg, KEY_PATH, manifest_path)
    chromium_path = helper_dir / CHROMIUM_MANIFEST_NAME
    chromium_path.write_text(json.dumps(build_chromium_manifest(helper_dir), indent=2), encoding="utf-8")
    for key_path in CHROMIUM_KEY_PATHS:
        _register(reg, key_path, chromium_path)
    return manifest_path


def uninstall(helper_dir: Path, reg=winreg) -> None:
    for key_path in (KEY_PATH, *CHROMIUM_KEY_PATHS):
        try:
            reg.DeleteKey(reg.HKEY_CURRENT_USER, key_path)
        except OSError:
            pass  # FileNotFoundError: key not present
    (helper_dir / MANIFEST_NAME).unlink(missing_ok=True)
    (helper_dir / CHROMIUM_MANIFEST_NAME).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    helper_dir = Path(__file__).resolve().parent
    if args.uninstall:
        uninstall(helper_dir)
        print("Helper uninstalled.")
    else:
        print("Registered for Firefox:", install(helper_dir))
        print("Registered for Chrome and Edge:", helper_dir / CHROMIUM_MANIFEST_NAME)


if __name__ == "__main__":
    main()
