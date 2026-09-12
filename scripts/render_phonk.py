"""scripts/render_phonk.py — ORF-5 "phonk cut": 40s, loud, extraordinary.

Real phonk beat (cowbell melody, 808 glides, kick/snare/hats, vinyl crackle)
+ maximalist visuals: parallax starfield, drifting grids, shockwave rings,
chromatic aberration, speedlines, spinning 3D wireframe radar globe,
glitch bursts, slam captions, beat-synced pulses.

Run:  python scripts/render_phonk.py
Outputs social/phonk_vertical.mp4 (1080x1920) and social/phonk_horizontal.mp4 (1280x720).
"""
from __future__ import annotations

import math
import random
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOCIAL = ROOT / "social"
SOCIAL.mkdir(exist_ok=True)

F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
F_SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

REPO_URL = "github.com/mohittt-vermaa/osint-recon-framework"
HANDLE = "@mohittt-vermaa"

FPS = 24
DUR = 40.0
BPM = 140.0
BEAT = 60.0 / BPM

TEAL = (125, 219, 232)
CYAN = (88, 166, 255)
GREEN = (63, 185, 80)
YELLOW = (240, 198, 90)
RED = (248, 81, 73)
MAGENTA = (200, 140, 255)
WHITE = (240, 246, 252)
DIM = (150, 160, 172)
COL = {"w": WHITE, "d": DIM, "g": GREEN, "c": CYAN, "y": YELLOW, "r": RED, "m": MAGENTA}

rng = random.Random(42)
STARS = [(rng.random(), rng.random(), rng.random() * 1.6 + 0.4, rng.random()) for _ in range(140)]

# ---------------------------------------------------------------------------
# timeline (seconds)
# ---------------------------------------------------------------------------
SC = dict(hook=(0.0, 3.5), user=(3.5, 9.5), game=(9.5, 15.0), meta=(15.0, 20.5),
          globe=(20.5, 26.5), breach=(26.5, 32.0), cards=(32.0, 36.0), end=(36.0, 40.0))


def font(p, s):
    return ImageFont.truetype(p, max(9, int(s)))


def ease(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def seg(text, color="w", bold=False):
    return (text, color, bold)


def beat_phase(t):
    return (t / BEAT) % 1.0


def pulse(t, strength=0.5):
    return 1.0 + strength * max(0.0, 1.0 - beat_phase(t)) ** 3


# ---------------------------------------------------------------------------
# background layers
# ---------------------------------------------------------------------------
class Backdrop:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.grid = self._grid()
        self.glow = self._nebula()

    def _grid(self):
        g = Image.new("RGBA", (self.W, self.H * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(g)
        step = max(46, self.W // 22)
        for x in range(0, self.W + step, step):
            d.line((x, 0, x, self.H * 2), fill=(60, 140, 220, 26), width=1)
        for y in range(0, self.H * 2, step):
            d.line((0, y, self.W, y), fill=(60, 140, 220, 26), width=1)
        return g

    def _nebula(self):
        g = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(g)
        for (fx, fy, fr, col, al) in ((0.25, 0.2, 0.5, (30, 90, 180), 60),
                                      (0.8, 0.75, 0.6, (20, 120, 160), 46),
                                      (0.6, 0.35, 0.35, (120, 40, 160), 30)):
            r = fr * max(self.W, self.H)
            d.ellipse((fx * self.W - r, fy * self.H - r, fx * self.W + r, fy * self.H + r),
                      fill=col + (al,))
        return g.filter(ImageFilter.GaussianBlur(90))

    def frame(self, img, t, hue_shift=0):
        W, H = self.W, self.H
        d = ImageDraw.Draw(img)
        img.paste(self.glow, (0, 0), self.glow)
        # drifting grid (parallax slow)
        off = int(t * 26) % (H // 2)
        img.paste(self.grid, (int(10 * math.sin(t * 0.3)), -off), self.grid)
        # starfield parallax + warp streaks
        speed = 0.02 + 0.25 * max(0.0, math.sin(t * 0.18)) ** 6
        for fx, fy, sz, ph in STARS:
            x = (fx + t * speed * (0.3 + sz * 0.25)) % 1.0 * W
            y = fy * H
            a = int(90 + 130 * abs(math.sin(t * 1.7 + ph * 9)))
            c = (a, min(255, a + 40), min(255, a + 80))
            if speed > 0.12:  # warp streaks on drops
                d.line((x - 60 * sz, y, x, y), fill=c, width=max(1, int(sz)))
            else:
                d.ellipse((x, y, x + sz * 2, y + sz * 2), fill=c)
        return img


# ---------------------------------------------------------------------------
# effect helpers
# ---------------------------------------------------------------------------
def chroma_text(d, x, y, text, fnt, fill, shift, anchor=None):
    kw = {"anchor": anchor} if anchor else {}
    d.text((x - shift, y), text, font=fnt, fill=(255, 60, 90), **kw)
    d.text((x + shift, y), text, font=fnt, fill=(60, 210, 255), **kw)
    d.text((x, y), text, font=fnt, fill=fill, **kw)


def glitch(img, amount):
    W, H = img.size
    for _ in range(amount):
        gy = rng.randint(0, H - 50)
        gh = rng.randint(8, 44)
        dx = rng.randint(-70, 70)
        band = img.crop((0, gy, W, gy + gh))
        img.paste(band, (dx, gy))
    return img


def rings(d, cx, cy, t, t0, n=3):
    for i in range(n):
        age = t - t0 - i * 0.12
        if age <= 0:
            continue
        r = int(age * 900)
        a = max(0, 150 - int(age * 160))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(80, 200, 255, a), width=3)


def speedlines(d, W, H, t):
    for i in range(14):
        y = (i * 137 + int(t * 900)) % H
        ln = rng.randint(80, 260)
        x = rng.randint(0, W)
        d.line((x, y, x + ln, y), fill=(120, 200, 255, 70), width=2)


def terminal_box(img, d, box, title):
    x0, y0, x1, y1 = [int(v) for v in box]
    s = (y1 - y0) / 700
    d.rounded_rectangle((x0, y0, x1, y1), radius=16 * s, fill=(13, 17, 23, 235), outline=(70, 160, 255, 160), width=2)
    bar = 44 * s
    d.rounded_rectangle((x0, y0, x1, y0 + bar), radius=15 * s, fill=(22, 27, 34, 255))
    d.rectangle((x0, y0 + bar - 10 * s, x1, y0 + bar), fill=(22, 27, 34, 255))
    for i, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
        d.ellipse((x0 + 20 * s + i * 26 * s, y0 + 13 * s, x0 + 34 * s + i * 26 * s, y0 + 27 * s), fill=c)
    d.text(((x0 + x1) / 2, y0 + bar / 2), title, font=font(F_MONO, 15 * s), fill=DIM, anchor="mm")
    return bar, s


def type_lines(d, x, y, lines, t, lh, fs, cps=26):
    """lines: (segments, delay, typed). returns y after last."""
    f = font(F_MONO, fs)
    fb = font(F_MONO_B, fs)
    for segments, delay, typed in lines:
        if t >= delay:
            local = t - delay
            xx = x
            for text, color, bold in segments:
                shown = text if not typed else text[: min(len(text), int(local * cps))]
                fnt = fb if bold else f
                d.text((xx, y), shown, font=fnt, fill=COL[color])
                xx += fnt.getlength(text)
            if typed and local * cps < len(segments[0][0]) and int(t * 3) % 2 == 0:
                d.rectangle((xx + 4, y, xx + 4 + fs * 0.6, y + fs), fill=GREEN)
        y += lh
    return y


def slam_word(img, d, W, H, word, tl, s):
    p = ease(min(1.0, tl / 0.18))
    size = int(150 * s * (2.2 - 1.2 * p))
    fade = min(1.0, (1.0 - tl) / 0.2 + 0.001) if tl < 1.0 else 1.0
    col = tuple(int(c * fade) for c in WHITE)
    chroma_text(d, W / 2, H / 2, word, font(F_SANS_B, size), col, int(8 * s * (1.4 - p)), anchor="mm")


# ---------------------------------------------------------------------------
# globe (numpy wireframe)
# ---------------------------------------------------------------------------
def globe_layer(size, rot):
    n = 600
    lat = np.linspace(-1.35, 1.35, 10)
    pts = []
    for la in lat:  # latitude circles
        th = np.linspace(0, 2 * np.pi, 60)
        pts.append(np.stack([np.cos(th) * np.cos(la), np.sin(th) * np.cos(la), np.sin(la) * np.ones_like(th)]))
    for lo in np.linspace(0, np.pi, 6, endpoint=False):  # meridians
        th = np.linspace(0, 2 * np.pi, 60)
        pts.append(np.stack([np.cos(th) * np.cos(lo), np.sin(th) * np.sin(lo) * 0 + np.sin(th) * np.cos(lo) * 0 + np.sin(th) * 0 + np.cos(lo) * np.sin(th) * 0 + np.sin(th) * np.cos(lo) * 0, np.cos(lo) * np.sin(th) * 0 + np.sin(lo) * np.cos(th)]))
    # (fix meridian formula properly below)
    pts = pts[:10]
    for lo in np.linspace(0, np.pi, 6, endpoint=False):
        th = np.linspace(0, 2 * np.pi, 60)
        x = np.cos(th) * np.cos(lo)
        y = np.sin(th)
        z = np.cos(th) * np.sin(lo)
        pts.append(np.stack([x, y, z]))
    R = np.array([[math.cos(rot), 0, math.sin(rot)], [0, 1, 0], [-math.sin(rot), 0, math.cos(rot)]])
    tilt = np.array([[1, 0, 0], [0, math.cos(0.4), -math.sin(0.4)], [0, math.sin(0.4), math.cos(0.4)]])
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size * 0.42
    for P in pts:
        Q = (tilt @ R @ P).T
        xs = (Q[:, 0] * 0.5 + 0.5) * size
        ys = (-Q[:, 1] * 0.5 + 0.5) * size
        z = Q[:, 2]
        for i in range(len(xs) - 1):
            a = int(40 + 150 * max(0, (z[i] + 1) / 2))
            d.line((xs[i], ys[i], xs[i + 1], ys[i + 1]), fill=(70, 210, 255, a), width=2)
    # pings
    for k in range(3):
        ang = rot * 1.7 + k * 2.1
        la = 0.6 * math.sin(k * 2.4)
        P = np.array([math.cos(ang) * math.cos(la), math.sin(la), math.sin(ang) * math.cos(la)])
        Q = tilt @ R @ P
        if Q[2] > 0.1:
            x, y = (Q[0] * 0.5 + 0.5) * size, (-Q[1] * 0.5 + 0.5) * size
            d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(255, 220, 120, 230))
            d.ellipse((x - 14, y - 14, x + 14, y + 14), outline=(255, 220, 120, 120), width=2)
    return img


# ---------------------------------------------------------------------------
# scene painters (take img+draw, local time tl, global t, scale s, W, H)
# ---------------------------------------------------------------------------
class Painter:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.s = min(W / 1080, H / 1920) if W < H else H / 720
        self.bd = Backdrop(W, H)

    def frame(self, t):
        W, H, s = self.W, self.H, self.s
        img = Image.new("RGB", (W, H), (4, 6, 10))
        self.bd.frame(img, t)
        d = ImageDraw.Draw(img, "RGBA")

        for name, (a, b) in SC.items():
            if a <= t < b:
                getattr(self, "sc_" + name)(img, d, t - a, t)
                break

        # beat flash on every downbeat (subtle) + hard flash at drops
        drops = [SC["user"][0], SC["globe"][0], SC["breach"][0], SC["cards"][0]]
        if any(abs(t - dd) < 0.09 for dd in drops):
            d.rectangle((0, 0, W, H), fill=(160, 220, 255, 60))
            img = glitch(img, 10)
        elif beat_phase(t) < 0.06:
            d.rectangle((0, 0, W, H), fill=(120, 200, 255, 18))

        # chromatic edge vignette + scanlines
        for y in range(0, H, 5):
            d.line((0, y, W, y), fill=(0, 0, 0, 20))
        return img

    # -- scenes -------------------------------------------------------------
    def sc_hook(self, img, d, tl, t):
        W, H, s = self.W, self.H, self.s
        p = ease(min(1.0, tl / 0.5))
        size = int(230 * s * (0.6 + 0.4 * p) * pulse(t, 0.06))
        chroma_text(d, W / 2, H * 0.34, "ORF-5", font(F_SANS_B, size), WHITE, int(10 * s), anchor="mm")
        d.text((W / 2, H * 0.34 + 150 * s), "FIVE MODULES · ONE COMMAND", font=font(F_MONO_B, 40 * s), fill=TEAL, anchor="mm")
        d.text((W / 2, H * 0.34 + 210 * s), HANDLE + "  ·  open source", font=font(F_MONO, 26 * s), fill=DIM, anchor="mm")
        rings(d, W / 2, H * 0.34, tl, 0.1)
        speedlines(d, W, H, t)

    def sc_user(self, img, d, tl, t):
        W, H, s = self.W, self.H, self.s
        chroma_text(d, W * 0.06, H * 0.045, "01 · USERNAME RECON", font(F_SANS_B, 64 * s), WHITE, int(5 * s))
        d.line((W * 0.06, H * 0.045 + 80 * s, W * 0.06 + 420 * s, H * 0.045 + 80 * s), fill=TEAL, width=4)
        box = (W * 0.05, H * 0.17, W * 0.95, H * 0.17 + 620 * s)
        bar, ts = terminal_box(img, d, box, "orf-5 · recon")
        lines = [
            ([seg("$ ", "g", True), seg("python main.py username octocat", "w", True)], 0.2, True),
            ([seg("[+] ", "g"), seg("GitHub     ", "w", True), seg("FOUND  ", "g", True), seg("200·276ms", "d")], 1.4, False),
            ([seg("[+] ", "g"), seg("HackerNews ", "w", True), seg("FOUND  ", "g", True), seg("200·175ms", "d")], 1.8, False),
            ([seg("[+] ", "g"), seg("Chess.com  ", "w", True), seg("FOUND  ", "g", True), seg("200·173ms", "d")], 2.2, False),
            ([seg("[+] ", "g"), seg("Steam      ", "w", True), seg("FOUND  ", "g", True), seg("200·388ms", "d")], 2.6, False),
            ([seg("[!] ", "y"), seg("GitLab     ", "w", True), seg("BLOCKED", "y", True), seg("403", "d")], 3.0, False),
            ([seg("[-] ", "r"), seg("Twitch     ", "w", True), seg("NOT_FOUND", "r", True), seg("404", "d")], 3.4, False),
            ([seg("[+] ", "g"), seg("6 found · 4 blocked · 10 clean", "w", True)], 4.0, False),
        ]
        type_lines(d, box[0] + 30 * ts, box[1] + bar + 26 * ts, lines, tl, 62 * ts, 28 * ts)
        # stat counters
        if tl > 4.2:
            for i, (num, lab, col) in enumerate((("20", "NETWORKS", TEAL), ("6", "FOUND", GREEN), ("~1s", "TOTAL", YELLOW))):
                cx = W * (0.22 + 0.28 * i)
                pp = pulse(t, 0.12)
                chroma_text(d, cx, H * 0.86, num, font(F_SANS_B, 90 * s * pp), col, int(4 * s), anchor="mm")
                d.text((cx, H * 0.86 + 70 * s), lab, font=font(F_MONO, 24 * s), fill=DIM, anchor="mm")
        rings(d, W * 0.9, H * 0.2, tl, 0.3, 2)

    def sc_game(self, img, d, tl, t):
        W, H, s = self.W, self.H, self.s
        chroma_text(d, W * 0.06, H * 0.045, "02 · GAME STATS", font(F_SANS_B, 64 * s), WHITE, int(5 * s))
        box = (W * 0.05, H * 0.17, W * 0.95, H * 0.17 + 520 * s)
        bar, ts = terminal_box(img, d, box, "orf-5 · free fire max")
        lines = [
            ([seg("$ ", "g", True), seg("python main.py gamestats --game freefire", "w", True)], 0.2, True),
            ([seg("  nickname ", "d"), seg("SHADOW-OP", "w", True)], 1.3, False),
            ([seg("  level    ", "d"), seg("71", "y", True)], 1.7, False),
            ([seg("  region   ", "d"), seg("IND", "c", True)], 2.1, False),
            ([seg("  likes    ", "d"), seg("12,408", "g", True)], 2.5, False),
        ]
        type_lines(d, box[0] + 30 * ts, box[1] + bar + 26 * ts, lines, tl, 62 * ts, 28 * ts)
        # player card
        if tl > 2.8:
            cx, cy = W * 0.72, H * 0.82
            pp = pulse(t, 0.1)
            d.rounded_rectangle((cx - 210 * s, cy - 90 * s, cx + 210 * s, cy + 90 * s), radius=20 * s,
                                fill=(16, 20, 30, 220), outline=(240, 198, 90, 200), width=3)
            d.text((cx, cy - 34 * s), "SHADOW-OP", font=font(F_SANS_B, 44 * s * pp), fill=YELLOW, anchor="mm")
            d.text((cx, cy + 34 * s), "LVL 71 · IND · 12.4K LIKES", font=font(F_MONO, 24 * s), fill=DIM, anchor="mm")
        speedlines(d, W, H, t)

    def sc_meta(self, img, d, tl, t):
        W, H, s = self.W, self.H, self.s
        chroma_text(d, W * 0.06, H * 0.045, "03 · METADATA", font(F_SANS_B, 64 * s), WHITE, int(5 * s))
        box = (W * 0.05, H * 0.17, W * 0.95, H * 0.17 + 520 * s)
        bar, ts = terminal_box(img, d, box, "orf-5 · og scraper")
        lines = [
            ([seg("$ ", "g", True), seg("python main.py metadata github.com/octocat", "w", True)], 0.2, True),
            ([seg("  og:title ", "d"), seg("octocat - Overview", "w")], 1.3, False),
            ([seg("  og:image ", "d"), seg("avatars.githubusercontent.com/…", "c")], 1.7, False),
            ([seg("  og:type  ", "d"), seg("profile", "g")], 2.1, False),
            ([seg("  og:site  ", "d"), seg("GitHub", "w")], 2.5, False),
        ]
        type_lines(d, box[0] + 30 * ts, box[1] + bar + 26 * ts, lines, tl, 62 * ts, 28 * ts)
        # floating OG cards
        cards = [("og:image", 0.78, -8), ("og:title", 0.88, 6), ("og:type", 0.96, -4)]
        for i, (lab, fy, rot) in enumerate(cards):
            if tl > 2.6 + i * 0.35:
                cx, cy = W * (0.25 + 0.25 * i), H * fy + 6 * math.sin(t * 2 + i)
                card = Image.new("RGBA", (int(240 * s), int(90 * s)), (0, 0, 0, 0))
                cd = ImageDraw.Draw(card)
                cd.rounded_rectangle((0, 0, 240 * s, 90 * s), radius=14 * s, fill=(20, 26, 40, 230), outline=(88, 166, 255, 200), width=2)
                cd.text((20 * s, 24 * s), lab, font=font(F_MONO_B, 30 * s), fill=CYAN)
                cd.text((20 * s, 58 * s), "extracted", font=font(F_MONO, 20 * s), fill=DIM)
                card = card.rotate(rot, expand=True, resample=Image.BICUBIC)
                img.paste(card, (int(cx - card.width / 2), int(cy - card.height / 2)), card)
        d = ImageDraw.Draw(img, "RGBA")
        rings(d, W * 0.5, H * 0.86, tl, 2.6, 2)

    def sc_globe(self, img, d, tl, t):
        W, H, s = self.W, self.H, self.s
        chroma_text(d, W * 0.06, H * 0.045, "LIVE SWEEP · 20 NETWORKS", font(F_SANS_B, 60 * s), WHITE, int(5 * s))
        size = int(min(W, H) * 0.85 * pulse(t, 0.05))
        g = globe_layer(size, t * 0.9)
        img.paste(g, (int((W - size) / 2), int(H * 0.42 - size / 2)), g)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse((W / 2 - size * 0.46, H * 0.42 - size * 0.46, W / 2 + size * 0.46, H * 0.42 + size * 0.46),
                  outline=(70, 210, 255, 60), width=2)
        rings(d, W / 2, H * 0.42, tl, 0.4)
        found = ["github", "steam", "chess.com", "hackernews", "telegram", "medium"]
        for i, name in enumerate(found):
            if tl > 0.8 + i * 0.7:
                d.text((W * 0.06, H * 0.80 + i * 34 * s), "[+] " + name, font=font(F_MONO_B, 26 * s), fill=GREEN)
        d.text((W * 0.94, H * 0.86), "6 / 20 …", font=font(F_MONO, 30 * s), fill=YELLOW, anchor="rm")

    def sc_breach(self, img, d, tl, t):
        W, H, s = self.W, self.H, self.s
        chroma_text(d, W * 0.06, H * 0.045, "04 · BREACH CHECK", font(F_SANS_B, 64 * s), WHITE, int(5 * s))
        box = (W * 0.05, H * 0.17, W * 0.95, H * 0.17 + 430 * s)
        bar, ts = terminal_box(img, d, box, "orf-5 · k-anonymity")
        lines = [
            ([seg("$ ", "g", True), seg("python main.py breach password123", "w", True)], 0.2, True),
            ([seg("  sha1 prefix ", "d"), seg("5BAA6… ", "c", True), seg("sent — nothing more", "d")], 1.3, False),
        ]
        type_lines(d, box[0] + 30 * ts, box[1] + bar + 26 * ts, lines, tl, 62 * ts, 28 * ts)
        if tl > 2.0:
            flash = (255, 90, 90) if int(t * 6) % 2 == 0 else (240, 198, 90)
            chroma_text(d, W / 2, H * 0.62, "EXPOSED", font(F_SANS_B, 170 * s * pulse(t, 0.1)), flash, int(9 * s), anchor="mm")
            d.text((W / 2, H * 0.62 + 120 * s), "2,266,543 occurrences in breached data", font=font(F_MONO, 28 * s), fill=DIM, anchor="mm")
            rings(d, W / 2, H * 0.62, tl, 2.0, 4)
        d.text((W / 2, H * 0.88), "k-anonymity · your value never leaves the machine", font=font(F_MONO, 26 * s), fill=TEAL, anchor="mm")

    def sc_cards(self, img, d, tl, t):
        W, H, s = self.W, self.H, self.s
        for i, word in enumerate(("SCAN.", "SURFACE.", "VERIFY.")):
            a, b = i * 1.33, i * 1.33 + 1.33
            if a <= tl < b:
                slam_word(img, d, W, H, word, tl - a, s)
                if (tl - a) < 0.12:
                    glitch(img, 6)

    def sc_end(self, img, d, tl, t):
        W, H, s = self.W, self.H, self.s
        p = ease(min(1.0, tl / 0.4))
        chroma_text(d, W / 2, H * 0.30, "ORF-5", font(F_SANS_B, 200 * s * (0.7 + 0.3 * p)), WHITE, int(8 * s), anchor="mm")
        d.text((W / 2, H * 0.30 + 130 * s), "five modules · one command", font=font(F_MONO, 30 * s), fill=TEAL, anchor="mm")
        if tl > 0.8:
            d.rounded_rectangle((W * 0.08, H * 0.55, W * 0.92, H * 0.55 + 90 * s), radius=45 * s,
                                outline=(88, 166, 255, 230), width=3, fill=(10, 16, 28, 200))
            d.text((W / 2, H * 0.55 + 45 * s), REPO_URL, font=font(F_MONO_B, 30 * s), fill=CYAN, anchor="mm")
        d.text((W / 2, H * 0.74), "windows · linux · macos · termux", font=font(F_MONO, 28 * s), fill=DIM, anchor="mm")
        d.text((W / 2, H * 0.80), "free & open source · MIT", font=font(F_MONO_B, 30 * s), fill=YELLOW, anchor="mm")
        d.text((W / 2, H * 0.90), HANDLE, font=font(F_MONO, 26 * s), fill=DIM, anchor="mm")
        rings(d, W / 2, H * 0.30, tl, 0.2)


# ---------------------------------------------------------------------------
# PHONK AUDIO
# ---------------------------------------------------------------------------
def make_phonk(path: Path, dur: float, sr: int = 44100):
    r = np.random.default_rng(5)
    n = int(dur * sr)
    buf = np.zeros(n)

    def add(sig, at, gain=1.0):
        i0 = int(at * sr)
        i1 = min(n, i0 + len(sig))
        if 0 <= i0 < n:
            buf[i0:i1] += sig[: i1 - i0] * gain

    tk = np.arange(int(0.28 * sr)) / sr
    kick = np.sin(2 * np.pi * (42 * tk + 130 * np.exp(-30 * tk) * tk)) * np.exp(-8 * tk)
    ts = np.arange(int(0.18 * sr)) / sr
    snr = r.standard_normal(len(ts)) * np.exp(-18 * ts)
    snr -= np.roll(snr, 1) * 0.5
    th = np.arange(int(0.05 * sr)) / sr
    hat = r.standard_normal(len(th)) * np.exp(-70 * th)
    tc = np.arange(int(0.3 * sr)) / sr

    def cow(f1, f2, g=0.2):
        return (np.sign(np.sin(2 * np.pi * f1 * tc)) + np.sign(np.sin(2 * np.pi * f2 * tc))) * np.exp(-10 * tc) * g

    tb = np.arange(int(BEAT * 2 * sr)) / sr

    # drums
    t = 0.0
    i = 0
    while t < dur:
        add(kick, t, 1.0)
        if i % 2 == 1:
            add(snr, t, 0.5)
        add(hat, t, 0.22 if i % 2 == 0 else 0.13)
        add(hat, t + BEAT / 2, 0.1)
        t += BEAT
        i += 1

    # cowbell melody (A-minor, phonk style) per 2 beats
    seq = [0, 0, 3, 0, 5, 3, 7, 5, 0, 0, 3, 0, 10, 7, 5, 3]
    t = 0.0
    k = 0
    while t < dur:
        st = seq[k % len(seq)]
        f = 587.33 * 2 ** (st / 12)
        add(cow(f, f * 1.44), t, 0.16)
        t += BEAT
        k += 1

    # 808 glide bass, pattern per bar (2 beats)
    roots = [55.0, 55.0, 43.65, 49.0]
    t = 0.0
    bar = 0
    while t < dur:
        f0 = roots[bar % 4]
        b = np.sin(2 * np.pi * (f0 * tb + (f0 * 0.5) * np.exp(-6 * tb) * tb)) * np.exp(-1.6 * tb)
        add(np.tanh(b * 2.0), t, 0.75)
        t += BEAT * 2
        bar += 1

    # vinyl crackle
    crack = (r.random(n) < 0.0004) * r.standard_normal(n) * 0.06
    buf += crack

    env = np.clip(np.minimum(t_arr := np.arange(n) / sr, (dur - t_arr)) / 0.8, 0, 1)
    buf *= env
    buf /= np.max(np.abs(buf)) * 1.06
    pcm = (buf * 32767).astype("<i2")
    stereo = np.repeat(pcm, 2).tobytes()
    hdr = (b"RIFF" + (36 + len(stereo)).to_bytes(4, "little") + b"WAVEfmt " + (16).to_bytes(4, "little")
           + (1).to_bytes(2, "little") + (2).to_bytes(2, "little") + sr.to_bytes(4, "little")
           + (sr * 4).to_bytes(4, "little") + (4).to_bytes(2, "little") + (16).to_bytes(2, "little")
           + b"data" + len(stereo).to_bytes(4, "little"))
    path.write_bytes(hdr + stereo)
    print("wrote", path)
    return path


# ---------------------------------------------------------------------------
def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if not exe:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
    return exe


def render(W, H, out, wav):
    painter = Painter(W, H)
    cmd = [ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", str(wav), "-c:v", "libx264", "-crf", "19", "-preset", "fast",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           "-t", str(DUR), str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    frames = int(DUR * FPS)
    for i in range(frames):
        try:
            proc.stdin.write(painter.frame(i / FPS).tobytes())
        except BrokenPipeError:
            print(proc.stderr.read().decode(errors="replace")[-3000:])
            raise
    proc.stdin.close()
    err = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0:
        print(err[-3000:])
        raise SystemExit("ffmpeg failed")
    print("wrote", out)


def main():
    wav = make_phonk(SOCIAL / "phonk.wav", DUR)
    render(1080, 1920, SOCIAL / "phonk_vertical.mp4", wav)
    render(1280, 720, SOCIAL / "phonk_horizontal.mp4", wav)


if __name__ == "__main__":
    main()
