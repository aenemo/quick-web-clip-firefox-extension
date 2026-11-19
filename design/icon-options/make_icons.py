"""Draws the three icon options (red down arrow with white MD on purple) and a comparison sheet."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
S = 768  # drawn large, then scaled down
PURPLE = (124, 58, 237, 255)  # current icon colour #7C3AED
RED = (220, 38, 38, 255)  # #DC2626: white text on it passes contrast
DARK_RED = (127, 29, 29, 255)
WHITE = (255, 255, 255, 255)
FONTS = ["C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/arialbd.ttf"]


def font(size):
    for f in FONTS:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def draw_md(d, box):
    """Biggest MD that fits box (x0, y0, x1, y1), centred."""
    x0, y0, x1, y1 = box
    size = 10
    while True:
        b = d.textbbox((0, 0), "MD", font=font(size + 4))
        if b[2] - b[0] > x1 - x0 or b[3] - b[1] > y1 - y0:
            break
        size += 4
    f = font(size)
    b = d.textbbox((0, 0), "MD", font=f)
    x = (x0 + x1) / 2 - (b[0] + b[2]) / 2
    y = (y0 + y1) / 2 - (b[1] + b[3]) / 2
    d.text((x, y), "MD", font=f, fill=WHITE)


def option_a():
    """Full purple square, wide pentagon arrow (badge shape): the most room for the letters."""
    im = Image.new("RGBA", (S, S), PURPLE)
    d = ImageDraw.Draw(im)
    poly = [(96, 70), (672, 70), (672, 440), (384, 712), (96, 440)]
    d.polygon(poly, fill=RED)
    draw_md(d, (140, 120, 628, 420))
    return im


def option_b():
    """Rounded purple tile, classic arrow: wide shaft holding MD over a broad head."""
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=150, fill=PURPLE)
    d.polygon([(150, 60), (618, 60), (618, 420), (730, 420), (384, 724), (38, 420), (150, 420)], fill=RED)
    draw_md(d, (178, 110, 590, 400))
    return im


def option_c():
    """Purple circle, rounded arrow with a white outline so it stands out on purple."""
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, S - 1, S - 1), fill=PURPLE)
    poly = [(150, 110), (618, 110), (618, 420), (384, 690), (150, 420)]
    d.polygon(poly, fill=WHITE)
    d.line(poly + [poly[0]], fill=WHITE, width=56, joint="curve")
    inner = [(178, 138), (590, 138), (590, 408), (384, 646), (178, 408)]
    d.polygon(inner, fill=RED)
    draw_md(d, (200, 160, 568, 390))
    return im


def save(im, name):
    out = {}
    for px in (96, 48, 32, 16):
        small = im.resize((px, px), Image.LANCZOS)
        small.save(HERE / f"{name}-{px}.png")
        out[px] = small
    return out


def sheet(options):
    """Each option at 96, 48, 32 and 16 px, on a light and a dark toolbar."""
    cols = [96, 48, 32, 16]
    w, h = 40 + 2 * sum(c + 30 for c in cols) + 40, 60 + len(options) * 140
    im = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    d = ImageDraw.Draw(im)
    half = w // 2
    d.rectangle((half, 0, w, h), fill=(43, 42, 51, 255))
    d.text((40, 15), "Light toolbar", font=font(22), fill=(0, 0, 0, 255))
    d.text((half + 20, 15), "Dark toolbar", font=font(22), fill=WHITE)
    for row, (label, sizes) in enumerate(options):
        y = 70 + row * 140
        d.text((10, y + 30), label, font=font(30), fill=(0, 0, 0, 255))
        for side in (0, 1):
            x = 50 + side * (half - 30)
            for c in cols:
                im.alpha_composite(sizes[c], (x, y + (96 - c) // 2))
                x += c + 30
    im.save(HERE / "compare.png")


if __name__ == "__main__":
    opts = [("A", save(option_a(), "option-a")), ("B", save(option_b(), "option-b")), ("C", save(option_c(), "option-c"))]
    sheet(opts)
