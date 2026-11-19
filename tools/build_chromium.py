"""Build the Chrome and Edge versions of the extension from the Firefox source.

Usage: python tools/build_chromium.py
Writes dist/chrome and dist/edge (the same files). Load either folder unpacked:
chrome://extensions or edge://extensions, Developer mode on, Load unpacked.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "extension"
DIST = ROOT / "dist"
TARGETS = ("chrome", "edge")

# Public key that fixes the unpacked extension ID, so the helper can allow it.
# Its ID is CHROMIUM_ID; helper/install_host.py allows the same ID.
KEY = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmlXUsMZGWSmq/fq2bgXF2hZrR0aA6H4UPuzQiZWbgzYw"
    "H6vUXZjBVDnKd2iqc9KKTpLRD6rCNO0+RHv2tKwsnU62mrk3Yf+H93POCirX8djm6GI5bY09T5jRJ/zv6FijSztt"
    "RuqtwPJF38PCaEjEVaQnttL2Q8zWX85kBrAr65vDTSwWIYOX9WZYkrfiH3oxJ5j9u2GCs23uI6BGFbUNWTb2L6wn"
    "F2H3HiM29S0qTtUEyFhav4D+OrJxe6E7Rf63tGIRx6ejJZcdOtyon7lDoMudvTCwzMw+Xl/iL5dUPbCYT6LAopbd"
    "4La/UfCO8joMtWcIwg6D825lEeLWP7l8BwIDAQAB"
)
CHROMIUM_ID = "kcdeoockaleljccbljbelmpehlnnceop"


def chromium_manifest(firefox: dict) -> dict:
    """The Firefox manifest, changed where Chrome and Edge differ."""
    m = json.loads(json.dumps(firefox))
    m.pop("browser_specific_settings", None)
    m["background"] = {"service_worker": "background.js", "type": "module"}
    m["permissions"] = ["contextMenus" if p == "menus" else p for p in m.get("permissions", [])]
    m["minimum_chrome_version"] = "120"
    m["key"] = KEY
    return m


def build(dist: Path = DIST) -> list[Path]:
    firefox = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    manifest = chromium_manifest(firefox)
    out = []
    for target in TARGETS:
        folder = dist / target
        if folder.exists():
            shutil.rmtree(folder)
        shutil.copytree(SOURCE, folder, ignore=shutil.ignore_patterns(".amo-upload-uuid", "web-ext-artifacts"))
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        out.append(folder)
    return out


if __name__ == "__main__":
    for folder in build():
        print("Built", folder)
    print("Extension ID:", CHROMIUM_ID)
    sys.exit(0)
