"""Make the store upload zip and the helper zip for this repository's browser.

Usage: py -3 tools/package_stores.py
Writes dist/store/quick-web-clip-<browser>-<version>.zip (to upload to the store) and
quick-web-clip-helper-<version>.zip (to attach to the GitHub release). The browser
comes from helper/extension_ids.json. The store zip has manifest.json at its root and
no "key": the Chrome and Edge stores refuse one and assign their own IDs.
"""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "extension"
HELPER = ROOT / "helper"
OUT = ROOT / "dist" / "store"
SKIP = {".amo-upload-uuid"}
SKIP_SUFFIXES = {".zip", ".xpi"}  # packages saved into the source folder by hand
HELPER_FILES = [
    "INSTALL.txt", "install.bat", "uninstall.bat", "requirements.txt", "extension_ids.json",
    "clipper_host.bat", "clipper_host.py", "install_host.py",
    "attachments.py", "compose.py", "notes.py", "transcript.py",
]


def browser() -> str:
    return json.loads((HELPER / "extension_ids.json").read_text(encoding="utf-8"))["browser"]


def source_files() -> list[Path]:
    files = [p for p in SOURCE.rglob("*") if p.is_file()]
    return sorted(
        (p for p in files if p.name not in SKIP and p.suffix.lower() not in SKIP_SUFFIXES and "web-ext-artifacts" not in p.parts and "__pycache__" not in p.parts),
        key=lambda p: p.relative_to(SOURCE).as_posix(),
    )


def store_manifest() -> dict:
    m = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    m.pop("key", None)
    return m


def write_zip(path: Path, manifest: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for f in source_files():
            name = f.relative_to(SOURCE).as_posix()
            if name != "manifest.json":
                z.write(f, name)
    return path


def write_helper_zip(path: Path) -> Path:
    """The helper for the GitHub release, in a quick-web-clip-helper folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in HELPER_FILES:
            z.write(HELPER / name, f"quick-web-clip-helper/{name}")
        z.write(ROOT / "LICENSE", "quick-web-clip-helper/LICENSE")
    return path


def package(out: Path = OUT) -> list[Path]:
    manifest = store_manifest()
    version = manifest["version"]
    return [
        write_zip(out / f"quick-web-clip-{browser()}-{version}.zip", manifest),
        write_helper_zip(out / f"quick-web-clip-helper-{version}.zip"),
    ]


if __name__ == "__main__":
    for z in package():
        print("Wrote", z.relative_to(ROOT), f"({z.stat().st_size // 1024} KB)")
