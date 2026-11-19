"""Draw the 128 px extension icon and this browser's store images from the chosen icon (option G).

Usage: py -3 tools/make_store_images.py   (needs Pillow and Windows fonts)
The browser comes from helper/extension_ids.json. Writes:
  extension/icons/icon-128.png            manifest icon (every browser)
  store/images/chrome-store-icon-128.png  Chrome only: 96 px artwork, 16 px clear border
  store/images/edge-logo-300.png          Edge only: store logo (1:1, 300 px)
  store/images/promo-small-440x280.png    Chrome and Edge: small promo tile
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "design" / "icon-options"))
import make_icons2  # noqa: E402

STORE = ROOT / "store" / "images"
FONTS = "C:/Windows/Fonts/"


def chrome_store_icon():
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    im.alpha_composite(make_icons2.option_g(96), (16, 16))
    return im


def promo_tile():
    im = Image.new("RGBA", (440, 280), make_icons2.PURPLE)
    im.alpha_composite(make_icons2.option_g(128), (36, 76))
    d = ImageDraw.Draw(im)
    title = ImageFont.truetype(FONTS + "segoeuib.ttf", 34)
    sub = ImageFont.truetype(FONTS + "segoeui.ttf", 19)
    d.text((186, 92), "Quick Web", font=title, fill=make_icons2.WHITE)
    d.text((186, 132), "Clip", font=title, fill=make_icons2.WHITE)
    d.text((186, 184), "Pages to Markdown", font=sub, fill=make_icons2.WHITE)
    d.text((186, 208), "in your Obsidian vault", font=sub, fill=make_icons2.WHITE)
    return im


def main():
    browser = json.loads((ROOT / "helper" / "extension_ids.json").read_text(encoding="utf-8"))["browser"]
    outputs = {ROOT / "extension" / "icons" / "icon-128.png": make_icons2.option_g(128)}
    if browser == "chrome":
        outputs[STORE / "chrome-store-icon-128.png"] = chrome_store_icon()
    if browser == "edge":
        outputs[STORE / "edge-logo-300.png"] = make_icons2.option_g(300)
    if browser in ("chrome", "edge"):
        outputs[STORE / "promo-small-440x280.png"] = promo_tile()
    for path, img in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        print("Wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
