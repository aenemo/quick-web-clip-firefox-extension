"""Round 2: five icon options built for legible MD at toolbar sizes.

Changes from round 1: the arrow fills more of the icon, the red is darker (more contrast
with white), and the letters are drawn at each real size (hinted) instead of shrunk
from a large drawing. Option F uses hand-set pixel letters.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
SIZES = (96, 48, 32, 16)
SS = 8  # supersampling for the shapes only
PURPLE = (124, 58, 237, 255)  # #7C3AED, the current icon colour
RED = (185, 28, 28, 255)  # #B91C1C: white text contrast 6.5:1
EDGE = (69, 10, 10, 255)
WHITE = (255, 255, 255, 255)
F = "C:/Windows/Fonts/"


def shape(px, polys, edge=False):
    """Purple square with red polygons (coordinates in icon pixels), drawn smooth."""
    big = Image.new("RGBA", (px * SS, px * SS), PURPLE)
    d = ImageDraw.Draw(big)
    for poly in polys:
        pts = [(x * SS, y * SS) for x, y in poly]
        if edge:
            d.polygon(pts, fill=RED, outline=EDGE, width=max(SS, px * SS // 32))
        else:
            d.polygon(pts, fill=RED)
    return big.resize((px, px), Image.LANCZOS)


def text_fit(im, box, font_file, text="MD"):
    """Draw the biggest text that fits box, at the icon's real size (hinted, sharp)."""
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    best = None
    for size in range(4, 200):
        f = ImageFont.truetype(font_file, size)
        b = d.textbbox((0, 0), text, font=f)
        if b[2] - b[0] > x1 - x0 or b[3] - b[1] > y1 - y0:
            break
        best = (f, b)
    f, b = best
    x = round((x0 + x1 - (b[0] + b[2])) / 2)
    y = round((y0 + y1 - (b[1] + b[3])) / 2)
    d.text((x, y), text, font=f, fill=WHITE)
    return im


def badge(px):
    """Badge arrow edge to edge: body down to 68%, point at the bottom."""
    m = max(1, round(px * 0.04))
    bottom = round(px * 0.68)
    poly = [(m, m), (px - m, m), (px - m, bottom), (px / 2, px), (m, bottom)]
    return poly, (m + max(1, px // 24), m + max(1, px // 24), px - m - max(1, px // 24), bottom)


def option_d(px):
    """D: wide badge, Verdana Bold (a font made for small screens)."""
    poly, box = badge(px)
    return text_fit(shape(px, [poly]), box, F + "verdanab.ttf")


def option_e(px):
    """E: wide badge, Arial Black (the heaviest strokes)."""
    poly, box = badge(px)
    return text_fit(shape(px, [poly]), box, F + "ariblk.ttf")


GLYPHS = {
    "M": ["X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"],
    "D": ["XXXX.", "X...X", "X...X", "X...X", "X...X", "X...X", "XXXX."],
}


def option_f(px):
    """F: wide badge with pixel letters: every stroke lands on whole pixels, so no blur."""
    poly, _ = badge(px)
    im = shape(px, [poly])
    d = ImageDraw.Draw(im)
    m = max(1, round(px * 0.04))
    bottom = round(px * 0.68)
    width, height = 11, 7  # M, gap, D
    k = max(1, min((px - 2 * m - 2) // width, (bottom - m - 1) // height))
    x0 = (px - width * k) // 2
    y0 = m + (bottom - m - height * k) // 2 + (1 if px <= 16 else 0)
    for i, ch in enumerate("MD"):
        for r, row in enumerate(GLYPHS[ch]):
            for c, cell in enumerate(row):
                if cell == "X":
                    x = x0 + (i * 6 + c) * k
                    y = y0 + r * k
                    d.rectangle((x, y, x + k - 1, y + k - 1), fill=WHITE)
    return im


def option_g(px):
    """G: badge with a dark edge so the arrow stands off the purple; Tahoma Bold."""
    poly, box = badge(px)
    return text_fit(shape(px, [poly], edge=True), box, F + "tahomabd.ttf")


def option_h(px):
    """H: tall block with a short notch point, giving the letters the most height; Segoe UI Black."""
    m = max(1, round(px * 0.04))
    bottom = round(px * 0.74)
    notch = px * 0.2
    poly = [(m, m), (px - m, m), (px - m, bottom), (px / 2 + notch, bottom), (px / 2, px), (px / 2 - notch, bottom), (m, bottom)]
    pad = max(1, px // 24)
    return text_fit(shape(px, [poly]), (m + pad, m + pad, px - m - pad, bottom - pad), F + "seguibl.ttf")


OPTIONS = {"D": option_d, "E": option_e, "F": option_f, "G": option_g, "H": option_h}


def sheet(rows):
    """Each option at 96, 48, 32, 16 px on light and dark, plus 32 px blown up 3x."""
    font = ImageFont.truetype(F + "seguibl.ttf", 28)
    cell = [96, 48, 32, 16]
    side = 60 + sum(c + 26 for c in cell) + 96 + 30
    w, h = 50 + 2 * side, 70 + len(rows) * 130
    im = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((50 + side, 0, w, h), fill=(43, 42, 51, 255))
    d.text((60, 18), "Light toolbar          (32 px enlarged)", font=ImageFont.truetype(F + "seguibl.ttf", 18), fill=(0, 0, 0, 255))
    d.text((60 + side, 18), "Dark toolbar           (32 px enlarged)", font=ImageFont.truetype(F + "seguibl.ttf", 18), fill=WHITE)
    for n, (label, imgs) in enumerate(rows):
        y = 60 + n * 130
        d.text((12, y + 30), label, font=font, fill=(0, 0, 0, 255))
        for s in (0, 1):
            x = 60 + s * side
            for c in cell:
                im.alpha_composite(imgs[c], (x, y + (96 - c) // 2))
                x += c + 26
            im.alpha_composite(imgs[32].resize((96, 96), Image.NEAREST), (x, y))
    im.save(HERE / "compare-round2.png")


if __name__ == "__main__":
    rows = []
    import make_icons  # round 1 option A, for comparison
    a = make_icons.option_a()
    rows.append(("A", {s: a.resize((s, s), Image.LANCZOS) for s in SIZES}))
    for label, fn in OPTIONS.items():
        imgs = {s: fn(s) for s in SIZES}
        for s, img in imgs.items():
            img.save(HERE / f"option-{label.lower()}-{s}.png")
        rows.append((label, imgs))
    sheet(rows)
