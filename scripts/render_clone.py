"""scripts/render_clone.py — "reel clone" of the reference format, for ORF-5.

Reference format: black 9:16 canvas; a centred 16:9 content band that cycles
through product shots (splash screen, agent typing, code views); subtle
slow zoom; hard cuts; music. The reference's burned-in headline + watermark
above the video are NOT reproduced — the frame stays clean, per request.

All band content is ORF-5: splash, username recon, game stats, metadata,
breach check, GitHub repo card, QR end frame.

Run:  python scripts/render_clone.py
Output: social/clone_vertical.mp4 (1080x1920, ~32s, phonk beat)
"""
from __future__ import annotations

import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_phonk as PK  # beat + terminal helpers

SOCIAL = ROOT / "social"
ASSETS = ROOT / "docs" / "assets"

F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
F_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

REPO_URL = "github.com/mohittt-vermaa/osint-recon-framework"
HANDLE = "@mohittt-vermaa"

FPS = 24
DUR = 32.0
W, H = 1080, 1920
BW, BH = 1080, 608          # content band (16:9)
BY = (H - BH) // 2

WHITE = (240, 246, 252)
DIM = (150, 156, 164)
GRAY = (110, 116, 124)
TEAL = (125, 219, 232)
CYAN = (88, 166, 255)
GREEN = (63, 185, 80)
YELLOW = (240, 198, 90)
RED = (248, 81, 73)


def font(p, s):
    return ImageFont.truetype(p, max(9, int(s)))


def ease(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


# ---------------------------------------------------------------------------
# clip renderers — each returns a BW x BH RGB image
# ---------------------------------------------------------------------------
def clip_splash(t):
    img = Image.new("RGB", (BW, BH), (0, 0, 0))
    d = ImageDraw.Draw(img)
    a = min(1.0, t / 0.5)
    d.text((BW / 2, 90), "Available on every platform today",
           font=font(F_SANS, 26), fill=tuple(int(c * a) for c in WHITE), anchor="mm")
    # left list (CLI bright, bot dim — like the reference's CLI/SDK)
    d.text((110, 240), "ORF-5 CLI", font=font(F_SANS_B, 30), fill=WHITE)
    d.text((110, 296), "ORF-5 Telegram Bot", font=font(F_SANS, 28), fill=GRAY)
    d.text((110, 352), "20 platform adapters", font=font(F_SANS, 28), fill=GRAY)
    # glowing icon
    ix, iy, ir = 640, 300, 86
    glow = Image.new("RGB", (BW, BH), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for col, rad, al in (((30, 120, 255), 150, 120), ((255, 140, 60), 120, 90), ((60, 220, 160), 100, 80)):
        gd.rounded_rectangle((ix - rad + 40, iy - rad, ix + rad, iy + rad - 20), radius=60, fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img.paste(Image.blend(img, glow, 0.55), (0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((ix - ir, iy - ir, ix + ir, iy + ir), radius=34, fill=(10, 12, 18), outline=(70, 80, 95), width=2)
    d.text((ix, iy), ">_", font=font(F_MONO_B, 74), fill=TEAL, anchor="mm")
    d.text((BW / 2, 500), "async · open source · free", font=font(F_MONO, 24), fill=DIM, anchor="mm")
    return img


def clip_terminal(t, title, lines, accent):
    img = Image.new("RGB", (BW, BH), (10, 13, 18))
    d = ImageDraw.Draw(img, "RGBA")
    bar, s = PK.terminal_box(img, d, (24, 20, BW - 24, BH - 20), title)
    PK.type_lines(d, 60, 20 + bar + 22, lines, t, 52, 25)
    return img


def clip_repo_card(t):
    img = Image.new("RGB", (BW, BH), (13, 17, 23))
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 70, 90, BW - 70, BH - 90
    d.rounded_rectangle((x0, y0, x1, y1), radius=18, fill=(22, 27, 34), outline=(48, 54, 61), width=2)
    d.text((x0 + 36, y0 + 44), "mohittt-vermaa / ", font=font(F_MONO, 30), fill=DIM)
    w0 = font(F_MONO, 30).getlength("mohittt-vermaa / ")
    d.text((x0 + 36 + w0, y0 + 44), "osint-recon-framework", font=font(F_MONO_B, 30), fill=CYAN)
    d.text((x0 + 36, y0 + 106), "Async 5-in-1 OSINT & reconnaissance framework —", font=font(F_SANS, 26), fill=WHITE)
    d.text((x0 + 36, y0 + 144), "username recon · game stats · metadata · breach · telegram bot", font=font(F_SANS, 26), fill=DIM)
    y = y0 + 220
    for label, val, col in (("language", "Python", CYAN), ("license", "MIT", GREEN),
                            ("platforms", "win · linux · macos · termux", WHITE),
                            ("topics", "osint · recon · asyncio", YELLOW)):
        d.ellipse((x0 + 36, y + 8, x0 + 48, y + 20), fill=col)
        d.text((x0 + 60, y), f"{label}: {val}", font=font(F_MONO, 24), fill=DIM)
        y += 46
    d.rounded_rectangle((x1 - 260, y1 - 90, x1 - 40, y1 - 34), radius=28, outline=GREEN, width=2)
    d.text(((x1 - 260 + x1 - 40) / 2, y1 - 62), "pip install -r requirements", font=font(F_MONO, 20), fill=GREEN, anchor="mm")
    return img


def clip_end(t):
    img = Image.new("RGB", (BW, BH), (0, 0, 0))
    d = ImageDraw.Draw(img)
    import qrcode
    q = qrcode.QRCode(border=2, box_size=8)
    q.add_data("https://" + REPO_URL)
    q.make(fit=True)
    qr = q.make_image(fill_color="black", back_color="white").convert("RGB").resize((260, 260), Image.NEAREST)
    qx, qy = 130, (BH - 260) // 2
    d.rounded_rectangle((qx - 14, qy - 14, qx + 274, qy + 274), radius=18, fill=(255, 255, 255))
    img.paste(qr, (qx, qy))
    d.text((450, BH / 2 - 70), REPO_URL, font=font(F_MONO_B, 22), fill=CYAN)
    d.text((450, BH / 2 - 14), "five modules · one command", font=font(F_MONO, 24), fill=DIM)
    d.text((450, BH / 2 + 34), "windows · linux · macos · termux", font=font(F_MONO, 22), fill=GRAY)
    d.text((450, BH / 2 + 88), "free & open source · MIT", font=font(F_MONO_B, 24), fill=YELLOW)
    return img


# ---------------------------------------------------------------------------
# timeline
# ---------------------------------------------------------------------------
USER_LINES = [
    [(PK.seg("$ ", "g", True), PK.seg("python main.py username octocat", "w", True)), 0.2, True],
    [(PK.seg("[+] ", "g"), PK.seg("GitHub     ", "w", True), PK.seg("FOUND  ", "g", True), PK.seg("200·276ms", "d")), 1.2, False],
    [(PK.seg("[+] ", "g"), PK.seg("HackerNews ", "w", True), PK.seg("FOUND  ", "g", True), PK.seg("200·175ms", "d")), 1.6, False],
    [(PK.seg("[+] ", "g"), PK.seg("Chess.com  ", "w", True), PK.seg("FOUND  ", "g", True), PK.seg("200·173ms", "d")), 2.0, False],
    [(PK.seg("[!] ", "y"), PK.seg("GitLab     ", "w", True), PK.seg("BLOCKED", "y", True), PK.seg("403", "d")), 2.4, False],
    [(PK.seg("[+] ", "g"), PK.seg("6 found · 4 blocked · 10 clean", "w", True)), 3.0, False],
]

CLIPS = [
    (0.0, 4.0, lambda t: clip_splash(t)),
    (4.0, 9.0, lambda t: clip_terminal(t, "orf-5 · username recon", USER_LINES, TEAL)),
    (9.0, 13.5, lambda t: clip_terminal(t, "orf-5 · game stats", [
        [(PK.seg("$ ", "g", True), PK.seg("python main.py gamestats --game freefire", "w", True)), 0.2, True],
        [(PK.seg("  nickname ", "d"), PK.seg("SHADOW-OP", "w", True)), 1.2, False],
        [(PK.seg("  level    ", "d"), PK.seg("71", "y", True)), 1.6, False],
        [(PK.seg("  region   ", "d"), PK.seg("IND", "c", True)), 2.0, False],
        [(PK.seg("  likes    ", "d"), PK.seg("12,408", "g", True)), 2.4, False],
    ], GREEN)),
    (13.5, 18.0, lambda t: clip_terminal(t, "orf-5 · metadata", [
        [(PK.seg("$ ", "g", True), PK.seg("python main.py metadata github.com/octocat", "w", True)), 0.2, True],
        [(PK.seg("  og:title ", "d"), PK.seg("octocat - Overview", "w")), 1.2, False],
        [(PK.seg("  og:image ", "d"), PK.seg("avatars.githubusercontent.com/…", "c")), 1.6, False],
        [(PK.seg("  og:type  ", "d"), PK.seg("profile", "g")), 2.0, False],
    ], CYAN)),
    (18.0, 23.0, lambda t: clip_terminal(t, "orf-5 · breach check", [
        [(PK.seg("$ ", "g", True), PK.seg("python main.py breach password123", "w", True)), 0.2, True],
        [(PK.seg("  sha1 prefix ", "d"), PK.seg("5BAA6… ", "c", True), PK.seg("sent — nothing more", "d")), 1.2, False],
        [(PK.seg("[!] ", "y"), PK.seg("EXPOSED · 2,266,543 occurrences", "y", True)), 2.2, False],
    ], YELLOW)),
    (23.0, 27.5, lambda t: clip_repo_card(t)),
    (27.5, 32.0, lambda t: clip_end(t)),
]


def zoomed(img, t0, t1, t):
    p = (t - t0) / (t1 - t0)
    z = 1.0 + 0.06 * ease(p)
    zw, zh = int(BW * z), int(BH * z)
    img = img.resize((zw, zh))
    return img.crop(((zw - BW) // 2, (zh - BH) // 2, (zw - BW) // 2 + BW, (zh - BH) // 2 + BH))


def frame(t):
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    for t0, t1, fn in CLIPS:
        if t0 <= t < t1:
            clip = zoomed(fn(t - t0), t0, t1, t)
            canvas.paste(clip, (0, BY))
            # 2-frame white flash at each cut
            if t - t0 < 0.09 and t0 > 0:
                d = ImageDraw.Draw(canvas)
                d.rectangle((0, BY, W, BY + BH), outline=(255, 255, 255), width=3)
            break
    return canvas


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if not exe:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
    return exe


def main():
    wav = PK.make_phonk(SOCIAL / "clone_beat.wav", DUR)
    out = SOCIAL / "clone_vertical.mp4"
    cmd = [ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", str(wav), "-c:v", "libx264", "-crf", "19", "-preset", "fast",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           "-t", str(DUR), str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        try:
            proc.stdin.write(frame(i / FPS).tobytes())
        except BrokenPipeError:
            print(proc.stderr.read().decode(errors="replace")[-2500:])
            raise
    proc.stdin.close()
    err = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0:
        print(err[-2500:])
        raise SystemExit("ffmpeg failed")
    print("wrote", out)


if __name__ == "__main__":
    main()
