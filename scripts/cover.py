#!/usr/bin/env python3
"""Make a 1280×720 cover / thumbnail: a picture, a soft dark band on the left, and two short lines of text.

Usage: cover.py <episode_dir> [--image art/01.png] [--line1 "紅髮會"] [--line2 "一則奇怪的廣告"] [--font PATH]
Defaults: the first illustration (or episode.json "image"), line 1 = title, line 2 = episode.json "hook".
Needs Pillow (pip install pillow). Writes build/cover.jpg.
Thumbnail rules that worked: at most ~7 characters per line, curiosity not fear, never give the twist away.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Episode, die, load  # noqa: E402

FONTS = [  # first one that exists wins; CJK-capable first
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", "C:/Windows/Fonts/msjhbd.ttc", "C:/Windows/Fonts/msjh.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode"); ap.add_argument("--image"); ap.add_argument("--line1"); ap.add_argument("--line2")
    ap.add_argument("--font")
    a = ap.parse_args()
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        die("cover.py needs Pillow: pip install pillow")
    ep = Episode(a.episode)
    img = a.image
    if not img:
        spec = ep.dir / "art/prompts.json"
        if spec.exists():
            first = load(spec)["images"][0]["id"]
            img = next((str(p) for p in (ep.dir / "art").glob(f"{first}.*")), None)
        img = img or ep.cfg.get("image")
    if not img:
        die("no picture — pass --image or draw the illustrations first")
    p = Path(img).expanduser()
    p = p if p.is_absolute() else ep.dir / p
    font = a.font or next((f for f in FONTS if Path(f).exists()), None)
    if not font:
        die("no font found — pass --font /path/to/a/font.ttf (use one with CJK glyphs for Chinese/Japanese)")
    l1 = a.line1 or ep.cfg.get("title", "")
    l2 = a.line2 if a.line2 is not None else ep.cfg.get("hook", "")

    W, H = 1280, 720
    im = Image.open(p).convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
    shade = Image.new("L", (W, H))
    sd = ImageDraw.Draw(shade)
    for x in range(W):                      # dark on the left 45 %, fading out by 70 %
        sd.line([(x, 0), (x, H)], fill=int(190 * max(0.0, min(1.0, (0.70 - x / W) / 0.25))))
    im = Image.composite(Image.new("RGB", (W, H), (12, 10, 9)), im, shade)
    d = ImageDraw.Draw(im)
    x0, maxw = 64, int(W * 0.46)

    def fit(text, size):
        while size > 28:
            f = ImageFont.truetype(font, size)
            if d.textlength(text, font=f) <= maxw:
                return f
            size -= 4
        return ImageFont.truetype(font, size)

    f1 = fit(l1, 112)
    y = H // 2 - (f1.size + (70 if l2 else 0)) // 2 - 20
    d.text((x0, y), l1, font=f1, fill=(255, 244, 228), stroke_width=3, stroke_fill=(0, 0, 0))
    if l2:
        f2 = fit(l2, 64)
        d.text((x0, y + f1.size + 28), l2, font=f2, fill=(245, 196, 120), stroke_width=2, stroke_fill=(0, 0, 0))
    out = ep.build / "cover.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=92)
    print(f"{out}  ({l1} / {l2})")


if __name__ == "__main__":
    main()
