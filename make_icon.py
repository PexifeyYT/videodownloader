"""Generate icon.ico for Video Downloader — blue pill with download arrow."""
from PIL import Image, ImageDraw, ImageFont
import os

BASE = os.path.dirname(os.path.abspath(__file__))

BLUE   = (0, 122, 255, 255)   # #007aff
WHITE  = (255, 255, 255, 255)
TRANSP = (0, 0, 0, 0)

SIZES = [16, 32, 48, 64, 128, 256]


def make_frame(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), TRANSP)
    draw = ImageDraw.Draw(img)

    pad = max(1, size // 16)
    draw.ellipse([pad, pad, size - pad - 1, size - pad - 1], fill=BLUE)

    # Arrow dimensions scale with size
    cx   = size / 2
    cy   = size / 2
    aw   = size * 0.28   # arrow shaft width
    ah   = size * 0.22   # shaft height
    hw   = size * 0.50   # arrowhead width
    hh   = size * 0.24   # arrowhead height
    bar  = size * 0.10   # bottom bar height
    gap  = size * 0.04   # gap between arrow tip and bar

    # Shaft (rectangle above arrowhead)
    shaft_top  = cy - ah - hh / 2
    shaft_left = cx - aw / 2
    draw.rectangle(
        [shaft_left, shaft_top, shaft_left + aw, cy - hh / 2],
        fill=WHITE
    )

    # Arrowhead (triangle pointing down)
    tip_y = cy + hh / 2
    draw.polygon(
        [(cx - hw / 2, cy - hh / 2),
         (cx + hw / 2, cy - hh / 2),
         (cx,           tip_y)],
        fill=WHITE
    )

    # Bottom bar
    bar_y = tip_y + gap
    bar_left = cx - hw / 2
    draw.rectangle(
        [bar_left, bar_y, bar_left + hw, bar_y + bar],
        fill=WHITE
    )

    return img


def main():
    frames = [make_frame(s) for s in SIZES]
    out = os.path.join(BASE, "icon.ico")
    frames[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[1:],
    )
    print(f"icon.ico created: {out}  ({len(SIZES)} sizes: {SIZES})")


if __name__ == "__main__":
    main()
