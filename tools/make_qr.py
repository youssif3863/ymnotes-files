"""Generate a static (permanent, ad-free) YMnotes-branded QR code.

Usage: python3 make_qr.py <url> <output.png> [title]
Requires: pip install segno pillow
"""
import io
import sys

import segno
from PIL import Image, ImageDraw, ImageFont

GREEN = (11, 90, 52)      # YMnotes logo green
TEAL = (0, 122, 135)      # UC teal
ORANGE = (234, 96, 20)    # Crohn's orange
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def centered(draw, y, text, fnt, fill, width):
    w = draw.textlength(text, font=fnt)
    draw.text(((width - w) / 2, y), text, font=fnt, fill=fill)


def main(url, out, title="Ulcerative Colitis vs Crohn's Disease"):
    # Error correction H (30%) leaves room for the centre logo.
    qr = segno.make(url, error="h", micro=False)
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=24, border=4, dark=GREEN, light="white")
    code = Image.open(buf).convert("RGB")
    size = code.width

    # Centre badge: white rounded box with "YM" + "notes" (~22% of width).
    badge = int(size * 0.24)
    bx = by = (size - badge) // 2
    d = ImageDraw.Draw(code)
    d.rounded_rectangle([bx, by, bx + badge, by + badge], radius=badge // 6,
                        fill="white", outline=GREEN, width=max(6, badge // 30))
    ym = font(BOLD, int(badge * 0.42))
    nt = font(BOLD, int(badge * 0.20))
    ym_w = d.textlength("YM", font=ym)
    nt_w = d.textlength("notes", font=nt)
    d.text((bx + (badge - ym_w) / 2, by + badge * 0.14), "YM", font=ym, fill=GREEN)
    d.text((bx + (badge - nt_w) / 2, by + badge * 0.62), "notes", font=nt, fill=ORANGE)

    # Card with header + caption around the code.
    pad, head, foot = size // 14, size // 5, size // 4
    W, H = size + 2 * pad, size + head + foot
    card = Image.new("RGB", (W, H), "white")
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([8, 8, W - 9, H - 9], radius=W // 18, outline=GREEN, width=14)
    centered(cd, head * 0.22, "YMnotes", font(BOLD, int(head * 0.42)), GREEN, W)
    card.paste(code, (pad, head))
    y = head + size + foot * 0.05
    centered(cd, y, title, font(BOLD, int(foot * 0.17)), TEAL, W)
    centered(cd, y + foot * 0.28, "Scan to open the one-page comparison",
             font(REG, int(foot * 0.14)), (60, 60, 60), W)
    cd.rectangle([W * 0.3, y + foot * 0.55, W * 0.7, y + foot * 0.57], fill=ORANGE)
    card.save(out, dpi=(300, 300))


if __name__ == "__main__":
    main(*sys.argv[1:])
