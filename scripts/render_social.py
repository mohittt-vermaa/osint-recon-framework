"""scripts/render_social.py — render the ORF-5 social promo kit.

Produces, under social/:
  post_square.png    1080x1080  Instagram / X post
  story_reel.png     1080x1920  Instagram story / reel cover
  twitter_card.png   1600x900   X / link-preview card
  frames_v/*.png     video slides (vertical 1080x1920)
  frames_h/*.png     video slides (horizontal 1920x1080)
  promo_vertical.mp4 15s reel/shorts cut
  promo_horizontal.mp4 15s YouTube cut
  qr.png             repo QR code

Run: python scripts/render_social.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import qrcode

ROOT = Path(__file__).resolve().parents[1]
SOCIAL = ROOT / "social"
ASSETS = ROOT / "docs" / "assets"
FR_V = SOCIAL / "frames_v"
FR_H = SOCIAL / "frames_h"
for p in (SOCIAL, FR_V, FR_H):
    p.mkdir(parents=True, exist_ok=True)

F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
F_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BG_RAW = ASSETS / "banner_bg.jpg"
REPO_URL = "github.com/mohittt-vermaa/osint-recon-framework"
FULL_URL = "https://" + REPO_URL
HANDLE = "@mohittt-vermaa"

TEAL = (125, 219, 232)
GREEN = (63, 185, 80)
CYAN = (88, 166, 255)
YELLOW = (240, 198, 90)
DIM = (170, 180, 192)
WHITE = (240, 246, 252)

FEATURES = [
    ("[+]", "username recon across 20 networks", GREEN),
    ("[+]", "free fire & pubg public stats", GREEN),
    ("[+]", "open-graph metadata scraper", GREEN),
    ("[+]", "k-anonymity breach checker", GREEN),
    ("[+]", "cli + async telegram bot", GREEN),
]

DURS = [3.0, 3.0, 3.5, 3.5, 4.0]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def bg(W: int, H: int, dim_top: int = 90, dim_bottom: int = 170) -> Image.Image:
    img = Image.open(BG_RAW).convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)))
    l = (img.width - W) // 2
    t = (img.height - H) // 2
    img = img.crop((l, t, l + W, t + H)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(H):
        fy = y / H
        a = int(dim_bottom * fy ** 1.1 + dim_top * (1 - fy) ** 2)
        d.line([(0, y), (W, y)], fill=(5, 8, 14, min(a, 235)))
    return Image.alpha_composite(img, ov).convert("RGB")


def pill(d: ImageDraw.ImageDraw, x: int, y: int, text: str, fnt, color, outline):
    bb = fnt.getbbox(text)
    w, h = bb[2] - bb[0] + 40, bb[3] - bb[1] + 24
    d.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, outline=outline, width=3)
    d.text((x + 20, y + 10), text, font=fnt, fill=color)
    return w, h


def qr(size: int) -> Image.Image:
    q = qrcode.QRCode(border=2, box_size=10)
    q.add_data(FULL_URL)
    q.make(fit=True)
    img = q.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.NEAREST)


def put_shot(slide: Image.Image, shot: str, box, caption: str | None = None):
    """Paste a terminal screenshot into a rounded frame, centered in box."""
    im = Image.open(ASSETS / shot).convert("RGB")
    bw, bh, bx, by = box
    scale = min(bw / im.width, bh / im.height)
    im = im.resize((int(im.width * scale), int(im.height * scale)))
    d = ImageDraw.Draw(slide)
    px, py = bx + (bw - im.width) // 2, by + (bh - im.height) // 2
    pad = 10
    d.rounded_rectangle((px - pad, py - pad, px + im.width + pad, py + im.height + pad),
                        radius=18, outline=(48, 54, 61), width=3, fill=(13, 17, 23))
    slide.paste(im, (px, py))
    if caption:
        cf = font(F_MONO, 30)
        d.text((slide.width / 2, py + im.height + pad + 34), caption,
               font=cf, fill=DIM, anchor="mm")


# ---------------------------------------------------------------------------
# slide builders (resolution-independent)
# ---------------------------------------------------------------------------
def slide_hook(W: int, H: int) -> Image.Image:
    img = bg(W, H)
    d = ImageDraw.Draw(img)
    s = H / 1920
    d.text((W * 0.07, H * 0.16), HANDLE + " presents", font=font(F_MONO, int(30 * s)), fill=DIM)
    d.text((W * 0.068, H * 0.215), "I BUILT A 5-IN-1", font=font(F_SANS_B, int(120 * s)), fill=WHITE)
    d.text((W * 0.07, H * 0.215 + 130 * s), "OSINT FRAMEWORK", font=font(F_SANS_B, int(120 * s)), fill=TEAL)
    d.text((W * 0.07, H * 0.215 + 290 * s), "async  ·  open source  ·  free forever",
           font=font(F_MONO, int(38 * s)), fill=DIM)
    pill(d, int(W * 0.07), int(H * 0.62), "ORF-5  ·  asyncio + aiohttp", font(F_MONO_B, int(34 * s)), CYAN, CYAN)
    d.text((W * 0.07, H * 0.80), "open source · runs on windows / linux / termux",
           font=font(F_MONO, int(32 * s)), fill=YELLOW)
    return img


def slide_features(W: int, H: int) -> Image.Image:
    img = bg(W, H)
    d = ImageDraw.Draw(img)
    s = H / 1920
    d.text((W * 0.07, H * 0.12), "WHAT IT DOES", font=font(F_SANS_B, int(92 * s)), fill=WHITE)
    d.line((W * 0.07, H * 0.12 + 120 * s, W * 0.42, H * 0.12 + 120 * s), fill=TEAL, width=4)
    y = H * 0.30
    for tag, text, color in FEATURES:
        d.text((W * 0.07, y), tag, font=font(F_MONO_B, int(46 * s)), fill=color)
        d.text((W * 0.07 + 90 * s, y), text, font=font(F_MONO, int(44 * s)), fill=WHITE)
        y += 95 * s
    d.text((W * 0.07, H * 0.86), "one command. all of it. zero auth.", font=font(F_MONO, int(34 * s)), fill=DIM)
    return img


def slide_shot(W: int, H: int, shot: str, caption: str) -> Image.Image:
    img = bg(W, H, dim_top=120, dim_bottom=120)
    put_shot(img, shot, (int(W * 0.06), int(H * 0.16), int(W * 0.88), int(H * 0.62)), caption)
    d = ImageDraw.Draw(img)
    d.text((W / 2, H * 0.90), REPO_URL, font=font(F_MONO_B, int(38 * (H / 1920))), fill=CYAN, anchor="mm")
    return img


def slide_cta(W: int, H: int) -> Image.Image:
    img = bg(W, H)
    d = ImageDraw.Draw(img)
    s = H / 1920
    d.text((W / 2, H * 0.16), "FREE & OPEN SOURCE", font=font(F_SANS_B, int(88 * s)), fill=YELLOW,           anchor="mm")
    d.text((W / 2, H * 0.235), "fork it · run it · make it yours — MIT license",
           font=font(F_MONO, int(34 * s)), fill=DIM, anchor="mm")
    q = qr(int(360 * s))
    pad = 18
    qx, qy = (W - q.width) // 2, int(H * 0.31)
    d.rounded_rectangle((qx - pad, qy - pad, qx + q.width + pad, qy + q.height + pad),
                        radius=22, fill=(255, 255, 255))
    img.paste(q, (qx, qy))
    d.text((W / 2, qy + q.height + pad + 50 * s), "scan  ·  clone  ·  run", font=font(F_MONO, int(32 * s)), fill=DIM, anchor="mm")
    d.text((W / 2, H * 0.80), REPO_URL, font=font(F_MONO_B, int(40 * s)), fill=CYAN, anchor="mm")
    d.text((W / 2, H * 0.87), HANDLE, font=font(F_MONO, int(34 * s)), fill=DIM, anchor="mm")
    return img


def build_slides(W: int, H: int) -> list:
    return [
        slide_hook(W, H),
        slide_features(W, H),
        slide_shot(W, H, "shot_username.png", "username recon — 20 platforms, ~1 second"),
        slide_shot(W, H, "shot_breach.png", "breach check — k-anonymity, nothing leaks"),
        slide_cta(W, H),
    ]


# ---------------------------------------------------------------------------
# stills
# ---------------------------------------------------------------------------
def still_square() -> Image.Image:
    W = H = 1080
    img = bg(W, H)
    d = ImageDraw.Draw(img)
    d.text((60, 70), "// open source · MIT · free", font=font(F_MONO, 26), fill=DIM)
    d.text((56, 150), "ORF-5", font=font(F_SANS_B, 130), fill=WHITE)
    d.text((60, 300), "5-in-1 ASYNC OSINT & RECON KIT", font=font(F_SANS_B, 40), fill=TEAL)
    y = 400
    for tag, text, color in FEATURES:
        d.text((60, y), tag, font=font(F_MONO_B, 30), fill=color)
        d.text((120, y), text, font=font(F_MONO, 29), fill=WHITE)
        y += 52
    q = qr(200)
    d.rounded_rectangle((W - 200 - 26 - 14, H - 200 - 110 - 14, W - 14, H - 96), radius=16, fill=(255, 255, 255))
    img.paste(q, (W - 200 - 26, H - 200 - 110))
    pill(d, 60, H - 150, REPO_URL, font(F_MONO_B, 26), CYAN, CYAN)
    d.text((60, H - 78), HANDLE + "  ·  free & open source · MIT", font=font(F_MONO, 26), fill=YELLOW)
    return img


def still_story() -> Image.Image:
    W, H = 1080, 1920
    img = bg(W, H)
    d = ImageDraw.Draw(img)
    d.text((60, 120), HANDLE, font=font(F_MONO, 30), fill=DIM)
    d.text((56, 200), "ORF-5", font=font(F_SANS_B, 170), fill=WHITE)
    d.text((62, 400), "5-IN-1 ASYNC OSINT", font=font(F_SANS_B, 62), fill=TEAL)
    d.text((62, 480), "& RECON FRAMEWORK", font=font(F_SANS_B, 62), fill=TEAL)
    y = 640
    for tag, text, color in FEATURES:
        d.text((60, y), tag, font=font(F_MONO_B, 40), fill=color)
        d.text((140, y), text, font=font(F_MONO, 38), fill=WHITE)
        y += 86
    q = qr(300)
    d.rounded_rectangle(((W - 300) // 2 - 16, 1180 - 16, (W + 300) // 2 + 16, 1180 + 300 + 16), radius=20, fill=(255, 255, 255))
    img.paste(q, ((W - 300) // 2, 1180))
    d.text((W / 2, 1560), "scan · clone · run", font=font(F_MONO, 32), fill=DIM, anchor="mm")
    d.text((W / 2, 1650), REPO_URL, font=font(F_MONO_B, 34), fill=CYAN, anchor="mm")
    d.text((W / 2, 1740), "FREE & OPEN SOURCE · MIT", font=font(F_SANS_B, 44), fill=YELLOW, anchor="mm")
    return img


def still_wide() -> Image.Image:
    W, H = 1600, 900
    img = bg(W, H)
    d = ImageDraw.Draw(img)
    d.text((70, 90), "// open source · MIT · free", font=font(F_MONO, 26), fill=DIM)
    d.text((66, 160), "ORF-5", font=font(F_SANS_B, 150), fill=WHITE)
    d.text((72, 340), "5-IN-1 ASYNC OSINT & RECON FRAMEWORK", font=font(F_SANS_B, 44), fill=TEAL)
    y = 450
    for tag, text, color in FEATURES:
        d.text((72, y), tag, font=font(F_MONO_B, 30), fill=color)
        d.text((140, y), text, font=font(F_MONO, 30), fill=WHITE)
        y += 52
    q = qr(230)
    d.rounded_rectangle((W - 230 - 90, 120, W - 70, 120 + 230 + 20), radius=18, fill=(255, 255, 255))
    img.paste(q, (W - 230 - 80, 130))
    d.text((W - 230 - 80 + 115, 400), "scan me", font=font(F_MONO, 28), fill=DIM, anchor="mm")
    pill(d, 72, H - 130, REPO_URL, font(F_MONO_B, 30), CYAN, CYAN)
    d.text((700, H - 92), HANDLE + "  ·  free & open source", font=font(F_MONO, 28), fill=YELLOW)
    return img


# ---------------------------------------------------------------------------
# video
# ---------------------------------------------------------------------------
def encode(frames: list[Path], out: Path, W: int, H: int) -> None:
    try:
        import shutil
        ffmpeg = shutil.which("ffmpeg")
    except Exception:
        ffmpeg = None
    if not ffmpeg:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    inputs, filters, prev = [], [], None
    off = 0.0
    for i, (fp, dur) in enumerate(zip(frames, DURS)):
        inputs += ["-loop", "1", "-framerate", "24", "-t", f"{dur:.2f}", "-i", str(fp)]
        filters.append(f"[{i}:v]zoompan=z='min(zoom+0.0007,1.12)':d=1:s={W}x{H},format=yuv420p[v{i}]")
    chain = []
    cur = "v0"
    acc = DURS[0]
    for i in range(1, len(frames)):
        acc += DURS[i]
        off = acc - 0.5 * i
        nxt = f"x{i}"
        chain.append(f"[{cur}][v{i}]xfade=transition=fade:duration=0.5:offset={off - DURS[i]:.2f}[{nxt}]")
        cur = nxt
    fc = ";".join(filters + chain)
    cmd = [ffmpeg, "-y", *inputs, "-filter_complex", fc, "-map", f"[{cur}]",
           "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", "-an", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    print("wrote", out)


def main() -> None:
    still_square().save(SOCIAL / "post_square.png", optimize=True)
    still_story().save(SOCIAL / "story_reel.png", optimize=True)
    still_wide().save(SOCIAL / "twitter_card.png", optimize=True)
    qr(480).save(SOCIAL / "qr.png")
    print("wrote stills + qr")

    # videos are produced by scripts/render_reel.py (terminal-style reel cut)


if __name__ == "__main__":
    main()
