#!/usr/bin/env python3
"""Render the animated price card for a brand segment: a glass card on a sparkling purple background,
the old price crossed out in red, then the new price popping in green. 2.4 s, 1080x1920, 30 fps, no audio.
usage: price_card.py --old 180 --new 100 --out price_card.mp4 [--seconds 2.4]
The new price is a claim - only use a number the client has approved (or the source beat already showed)."""
import argparse, math, os, random, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--old", required=True, help="old monthly price, e.g. 180")
ap.add_argument("--new", required=True, help="new monthly price, e.g. 100")
ap.add_argument("--out", required=True)
ap.add_argument("--seconds", type=float, default=2.4)
a = ap.parse_args()

W, H, FPS = 1080, 1920, 30
N = round(a.seconds * FPS)
FONT = next((p for p in ("/System/Library/Fonts/Avenir Next.ttc", "/System/Library/Fonts/Helvetica.ttc") if os.path.exists(p)))
F = lambda s: ImageFont.truetype(FONT, s, index=2 if "Avenir" in FONT else 1)
random.seed(3)
bg = Image.new("RGB", (W, H)); px = bg.load()
for y in range(H):
    for x in range(W):
        d = math.hypot(x - W * 0.5, y - H * 0.42) / 1300
        px[x, y] = (max(int(120 - 80 * d), 20), max(int(70 - 55 * d), 10), max(int(230 - 120 * d), 80))
stars = [(random.randint(40, W - 40), random.randint(80, H - 80), random.uniform(14, 40), random.uniform(0, 6.28)) for _ in range(26)]


def star(d, cx, cy, s):
    if s >= 2:
        d.polygon([(cx, cy - s), (cx + s * .22, cy - s * .22), (cx + s, cy), (cx + s * .22, cy + s * .22), (cx, cy + s),
                   (cx - s * .22, cy + s * .22), (cx - s, cy), (cx - s * .22, cy - s * .22)], fill=(255, 255, 255))


def glow_text(img, xy, txt, font, col, fill):
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).text(xy, txt, font=font, fill=col + (255,), anchor="mm", stroke_width=10, stroke_fill=col + (255,))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(22)))
    ImageDraw.Draw(img).text(xy, txt, font=font, fill=fill, anchor="mm")


with tempfile.TemporaryDirectory() as tmp:
    for i in range(N):
        t = i / FPS
        fr = bg.convert("RGBA"); d = ImageDraw.Draw(fr)
        for (x, y, s, ph) in stars:
            star(d, x, y, s * (0.5 + 0.5 * math.sin(t * 5 + ph)))
        k = min(1, t / 0.25); sc = 0.7 + 0.3 * (1 - (1 - k) ** 3) + 0.04 * math.sin(min(1, t / 0.4) * math.pi)
        cw, ch = int(520 * sc), int(700 * sc); cx, cy = W // 2, int(H * 0.45)
        card = Image.new("RGBA", fr.size, (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle((cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2), radius=int(70 * sc),
                                               fill=(245, 245, 255, 235), outline=(255, 255, 255, 255), width=6)
        fr.alpha_composite(card.filter(ImageFilter.GaussianBlur(1)))
        if t > 0.12:  # old price
            pan = Image.new("RGBA", fr.size, (0, 0, 0, 0))
            ImageDraw.Draw(pan).rounded_rectangle((cx - cw // 2 + 30, cy - ch // 2 + 40, cx + cw // 2 - 30, cy - 20), radius=40, fill=(255, 120, 140, 120))
            fr.alpha_composite(pan)
            glow_text(fr, (cx, cy - ch // 4), f"${a.old}", F(int(150 * sc)), (255, 40, 80), (255, 255, 255, 255))
        if t > 0.5:  # red X draws in
            p = min(1, (t - 0.5) / 0.25); d = ImageDraw.Draw(fr); p0 = (cx - 150, cy - ch // 4 - 90); p1 = (cx + 150, cy - ch // 4 + 90)
            d.line((p0[0], p0[1], p0[0] + (p1[0] - p0[0]) * p, p0[1] + (p1[1] - p0[1]) * p), fill=(235, 20, 40), width=26)
            if p == 1:
                p2 = min(1, (t - 0.75) / 0.2)
                d.line((p1[0], p0[1], p1[0] - (p1[0] - p0[0]) * p2, p0[1] + (p1[1] - p0[1]) * p2), fill=(235, 20, 40), width=26)
        if t > 1.0:  # new price pops in
            k2 = min(1, (t - 1.0) / 0.2); s2 = int(150 * sc * (0.6 + 0.4 * k2 + 0.08 * math.sin(k2 * math.pi)))
            pan = Image.new("RGBA", fr.size, (0, 0, 0, 0))
            ImageDraw.Draw(pan).rounded_rectangle((cx - cw // 2 + 30, cy + 20, cx + cw // 2 - 30, cy + ch // 2 - 40), radius=40, fill=(120, 255, 160, 110))
            fr.alpha_composite(pan)
            glow_text(fr, (cx, cy + ch // 4), f"${a.new}", F(s2), (60, 255, 120), (170, 255, 190, 255))
        fr.convert("RGB").save(f"{tmp}/f{i:03d}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/f%03d.png", "-c:v", "libx264", "-crf", "14",
                    "-pix_fmt", "yuv420p", a.out], check=True)
print(a.out)
