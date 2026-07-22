#!/usr/bin/env python3
"""Turn the source logo PNG into a macOS AppIcon.icns.

The source art sits on a light background; macOS does NOT auto-round or trim app
icons, so we (1) crop to the artwork, (2) reshape it to the standard rounded
"squircle" with transparent corners and a small margin, then (3) emit every
size iconutil needs. Run: python3 make-icon.py <source.png> <out.icns>
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

TARGET = 1024          # full canvas
INNER = 824            # artwork size within it (Apple leaves ~10% margin)
RADIUS = int(INNER * 0.2237)   # macOS continuous-corner ratio
# iconutil wants these exact names/sizes in a .iconset directory
SIZES = [
    ("icon_16x16.png", 16), ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32), ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128), ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256), ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512), ("icon_512x512@2x.png", 1024),
]


def build_master(src: str) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    # crop away the flat background: mask pixels that differ from a corner sample
    bg = Image.new("RGB", im.size, im.convert("RGB").getpixel((2, 2)))
    diff = ImageChops.difference(im.convert("RGB"), bg).convert("L")
    bbox = diff.point(lambda p: 255 if p > 24 else 0).getbbox()
    if bbox:
        # inset a hair to drop the antialiased rim where navy met the background
        inset = round(min(bbox[2] - bbox[0], bbox[3] - bbox[1]) * 0.012)
        bbox = (bbox[0] + inset, bbox[1] + inset,
                bbox[2] - inset, bbox[3] - inset)
    art = im.crop(bbox) if bbox else im
    # square it (center on transparent) so the reshape isn't distorted
    side = max(art.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(art, ((side - art.size[0]) // 2, (side - art.size[1]) // 2))
    # reshape to the standard rounded rect with transparent corners
    art_r = sq.resize((INNER, INNER), Image.LANCZOS)
    mask = Image.new("L", (INNER, INNER), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, INNER - 1, INNER - 1], radius=RADIUS, fill=255)
    art_r.putalpha(mask)
    canvas = Image.new("RGBA", (TARGET, TARGET), (0, 0, 0, 0))
    off = (TARGET - INNER) // 2
    canvas.paste(art_r, (off, off), art_r)
    return canvas


def main() -> None:
    src, out = sys.argv[1], Path(sys.argv[2])
    master = build_master(src)
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "AppIcon.iconset"
        iconset.mkdir()
        for name, size in SIZES:
            master.resize((size, size), Image.LANCZOS).save(iconset / name)
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)],
                       check=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
