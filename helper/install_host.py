"""Register (or remove) the Obsidian Quick Clip native messaging host."""
import argparse
import json
import winreg
from pathlib import Path

HOST_NAME = "obsidian_quick_clip"
KEY_PATH = r"Software\Mozilla\NativeMessagingHosts" + "\\" + HOST_NAME
MANIFEST_NAME = HOST_NAME + ".json"


def build_manifest(helper_dir: Path) -> dict:
    return {
        "name": HOST_NAME,
        "description": "Obsidian Quick Clip helper",
        "path": str(helper_dir / "clipper_host.bat"),
        "type": "stdio",
        "allowed_extensions": ["obsidian-quick-clip@local"],
    }


def install(helper_dir: Path, reg=winreg) -> Path:
    manifest_path = helper_dir / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(build_manifest(helper_dir), indent=2), encoding="utf-8"
    )
    key = reg.CreateKey(reg.HKEY_CURRENT_USER, KEY_PATH)
    reg.SetValue(key, "", reg.REG_SZ, str(manifest_path))
    return manifest_path


def uninstall(helper_dir: Path, reg=winreg) -> None:
    try:
        reg.DeleteKey(reg.HKEY_CURRENT_USER, KEY_PATH)
    except OSError:
        pass  # FileNotFoundError: key not present
    (helper_dir / MANIFEST_NAME).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    helper_dir = Path(__file__).resolve().parent
    if args.uninstall:
        uninstall(helper_dir)
        print("Helper uninstalled.")
    else:
        print("Registered:", install(helper_dir))


if __name__ == "__main__":
    main()
