"""scripts/render_reel.py — high-energy terminal-style promo videos for ORF-5.

Reel aesthetic: live terminal typing, glitch cuts, scanlines, chromatic
caption slabs and a synthesized phonk-style beat. No "star if you like it"
copy anywhere — clean, professional end card.

Run:  python scripts/render_reel.py
Outputs: social/promo_vertical.mp4, social/promo_horizontal.mp4, social/beat.wav
"""
from __future__ import annotations

import hashlib
import random
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOCIAL = ROOT / "social"
ASSETS = ROOT / "docs" / "assets"
SOCIAL.mkdir(exist_ok=True)

F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
F_SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

REPO_URL = "github.com/mohittt-vermaa/osint-recon-framework"
HANDLE = "@mohittt-vermaa"

FPS = 24
DUR = 24.0

BG = (8, 10, 14)
TERM_BG = (13, 17, 23)
TERM_BAR = (22, 27, 34)
TEXT = (230, 237, 243)
DIM = (139, 148, 158)
GREEN = (63, 185, 80)
CYAN = (88, 166, 255)
YELLOW = (210, 153, 34)
RED = (248, 81, 73)
MAGENTA = (188, 140, 255)
TEAL = (125, 219, 232)

COL = {"w": TEXT, "d": DIM, "g": GREEN, "c": CYAN, "y": YELLOW, "r": RED, "m": MAGENTA}

BREACH_PREFIX = hashlib.sha1(b"password123").hexdigest()[:5].upper()


def seg(text, color="w", bold=False):
    return (text, color, bold)


# ---------------------------------------------------------------------------
# timeline
# ---------------------------------------------------------------------------
SCENES = [
    dict(kind="hook", dur=2.5),
    dict(kind="term", cap="01 · USERNAME RECON", dur=5.0, lines=[
        ([seg("$ ", "g", True), seg("python main.py username octocat", "w", True)], 0.0, True),
        ([seg("[+] ", "g"), seg("GitHub       ", "w", True), seg("FOUND   ", "g", True), seg("200·276ms", "d")], 1.3, False),
        ([seg("[+] ", "g"), seg("HackerNews   ", "w", True), seg("FOUND   ", "g", True), seg("200·175ms", "d")], 1.75, False),
        ([seg("[+] ", "g"), seg("Chess.com    ", "w", True), seg("FOUND   ", "g", True), seg("200·173ms", "d")], 2.2, False),
        ([seg("[+] ", "g"), seg("Steam        ", "w", True), seg("FOUND   ", "g", True), seg("200·388ms", "d")], 2.65, False),
        ([seg("[!] ", "y"), seg("GitLab       ", "w", True), seg("BLOCKED ", "y", True), seg("403", "d")], 3.1, False),
        ([seg("[-] ", "r"), seg("Twitch       ", "w", True), seg("NOT_FOUND ", "r", True), seg("404", "d")], 3.55, False),
        ([seg("[+] ", "g"), seg("done · 6 found · 4 blocked · 10 clean", "w", True)], 4.1, False),
    ]),
    dict(kind="term", cap="02 · GAME STATS", dur=4.5, lines=[
        ([seg("$ ", "g", True), seg("python main.py gamestats --game freefire", "w", True)], 0.0, True),
        ([seg("  nickname ", "d"), seg(": SHADOW-OP", "w", True)], 1.4, False),
        ([seg("  level    ", "d"), seg(": 71", "w", True)], 1.8, False),
        ([seg("  region   ", "d"), seg(": IND", "w", True)], 2.2, False),
        ([seg("  likes    ", "d"), seg(": 12,408", "w", True)], 2.6, False),
    ]),
    dict(kind="term", cap="03 · METADATA", dur=4.5, lines=[
        ([seg("$ ", "g", True), seg("python main.py metadata github.com/octocat", "w", True)], 0.0, True),
        ([seg("  og:title ", "d"), seg("octocat - Overview", "w")], 1.4, False),
        ([seg("  og:image ", "d"), seg("avatars.githubusercontent.com/…", "w")], 1.85, False),
        ([seg("  og:type  ", "d"), seg("profile", "w")], 2.3, False),
        ([seg("  og:site  ", "d"), seg("GitHub", "w")], 2.75, False),
    ]),
    dict(kind="term", cap="04 · BREACH CHECK", dur=4.0, lines=[
        ([seg("$ ", "g", True), seg("python main.py breach password123", "w", True)], 0.0, True),
        ([seg("  sha1 prefix sent ", "d"), seg(f"{BREACH_PREFIX}… ", "c", True), seg("(k-anonymity)", "d")], 1.3, False),
        ([seg("[!] ", "y"), seg("EXPOSED · 2,266,543 occurrences", "y", True)], 2.1, False),
    ]),
    dict(kind="end", dur=3.5),
]
assert abs(sum(sc["dur"] for sc in SCENES) - DUR) < 1e-6


def font(path, size):
    return ImageFont.truetype(path, max(10, int(size)))


# ---------------------------------------------------------------------------
# audio — synthesized phonk-style beat
# ---------------------------------------------------------------------------
def make_beat(path: Path, dur: float, sr: int = 44100) -> Path:
    rng = np.random.default_rng(7)
    n = int(dur * sr)
    buf = np.zeros(n, dtype=np.float64)
    beat = 60.0 / 132.0

    def add(sig, at):
        i0 = int(at * sr)
        i1 = min(n, i0 + len(sig))
        if i0 < n:
            buf[i0:i1] += sig[: i1 - i0]

    t_k = np.arange(int(0.30 * sr)) / sr
    kick = np.sin(2 * np.pi * (45 * t_k + 120 * np.exp(-28 * t_k) * t_k)) * np.exp(-7 * t_k)
    t_s = np.arange(int(0.20 * sr)) / sr
    snare = (rng.standard_normal(len(t_s)) * np.exp(-16 * t_s)) * 0.5
    snare -= np.roll(snare, 1) * 0.4  # crude high-pass
    t_h = np.arange(int(0.06 * sr)) / sr
    hat = rng.standard_normal(len(t_h)) * np.exp(-60 * t_h) * 0.18
    t_c = np.arange(int(0.35 * sr)) / sr
    cow_freqs = [(587.33, 845.0)]

    def cowbell(f1, f2):
        sq = np.sign(np.sin(2 * np.pi * f1 * t_c)) + np.sign(np.sin(2 * np.pi * f2 * t_c))
        return sq * np.exp(-9 * t_c) * 0.22

    t_b = np.arange(int(beat * sr)) / sr
    bass_roots = [55.0, 43.65, 65.41, 49.0]  # A1 F1 C2 G1

    t = 0.0
    bar = 0
    while t < dur:
        add(kick, t)
        if int(round(t / beat)) % 2 == 1:
            add(snare, t)
        add(hat * (1.0 if int(round(t / (beat / 2))) % 2 == 0 else 0.6), t)
        t += beat / 2

    t = 0.0
    bar = 0
    while t < dur:
        root = bass_roots[bar % 4]
        bass = np.sin(2 * np.pi * root * t_b) * np.exp(-2.2 * t_b) * 0.8
        bass = np.tanh(bass * 1.6)  # 808 saturation
        add(bass, t)
        melody = [0, None, 3, 0, 5, None, 3, 2]
        for i, st in enumerate(melody):
            if st is None:
                continue
            f1 = 587.33 * (2 ** (st / 12.0))
            f2 = 845.0 * (2 ** (st / 12.0))
            sq = np.sign(np.sin(2 * np.pi * f1 * t_c)) + np.sign(np.sin(2 * np.pi * f2 * t_c))
            add(sq * np.exp(-9 * t_c) * 0.16, t + i * beat / 2)
        t += beat * 4
        bar += 1

    buf /= np.max(np.abs(buf)) * 1.05
    pcm = (buf * 32767).astype("<i2")
    stereo = np.repeat(pcm, 2)
    path.write_bytes(b"RIFF" + b"\0\0\0\0" + b"WAVEfmt " + (16).to_bytes(4, "little")
                     + (1).to_bytes(2, "little") + (2).to_bytes(2, "little")
                     + sr.to_bytes(4, "little") + (sr * 4).to_bytes(4, "little")
                     + (4).to_bytes(2, "little") + (16).to_bytes(2, "little")
                     + b"data" + (len(stereo) * 2).to_bytes(4, "little") + stereo.tobytes())
    # fix RIFF size header
    data = bytearray(path.read_bytes())
    size = len(data) - 8
    data[4:8] = size.to_bytes(4, "little")
    path.write_bytes(bytes(data))
    print("wrote", path)
    return path


# ---------------------------------------------------------------------------
# frame painting
# ---------------------------------------------------------------------------
class Painter:
    def __init__(self, W: int, H: int):
        self.W, self.H = W, H
        self.s = H / 1920.0
        self.scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.scan)
        for y in range(0, H, 4):
            d.line([(0, y), (W, y)], fill=(0, 0, 0, 26))
        self.glow = Image.new("RGBA", (W, 220), (0, 0, 0, 0))
        dg = ImageDraw.Draw(self.glow)
        for y in range(220):
            a = int(14 * np.sin(np.pi * y / 220))
            dg.line([(0, y), (W, y)], fill=(140, 220, 255, a))

    # -- pieces -------------------------------------------------------------
    def chrome_text(self, d, x, y, text, fnt, fill, chroma=0, anchor=None):
        kw = {"anchor": anchor} if anchor else {}
        if chroma:
            d.text((x - chroma, y), text, font=fnt, fill=(255, 60, 80), **kw)
            d.text((x + chroma, y), text, font=fnt, fill=(60, 200, 255), **kw)
        d.text((x, y), text, font=fnt, fill=fill, **kw)

    def caption_slab(self, img, text):
        W, H, s = self.W, self.H, self.s
        d = ImageDraw.Draw(img)
        f = font(F_SANS_B, 60 * s)
        bb = f.getbbox(text)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x0 = (W - tw) / 2 - 40 * s
        y0 = H * 0.055
        d.rounded_rectangle((x0, y0, x0 + tw + 80 * s, y0 + th + 44 * s),
                            radius=14 * s, fill=(10, 14, 20, 210), outline=TEAL, width=3)
        self.chrome_text(d, (W - tw) / 2, y0 + 16 * s, text, f, TEXT, chroma=int(3 * s))

    def bottom_strip(self, d):
        W, H, s = self.W, self.H, self.s
        if W <= H:  # vertical — stack so nothing overlaps
            d.text((W * 0.95, H * 0.895), HANDLE, font=font(F_MONO, 26 * s), fill=DIM, anchor="rm")
            d.text((W * 0.05, H * 0.925), REPO_URL, font=font(F_MONO_B, 28 * s), fill=CYAN)
        else:
            d.text((W * 0.05, H * 0.925), REPO_URL, font=font(F_MONO_B, 30 * s), fill=CYAN)
            d.text((W * 0.95, H * 0.925), HANDLE, font=font(F_MONO, 28 * s), fill=DIM, anchor="rm")

    def draw_hook(self, img, t):
        W, H, s = self.W, self.H, self.s
        d = ImageDraw.Draw(img)
        self.chrome_text(d, W / 2, H * 0.30, "ORF-5", font(F_SANS_B, 210 * s), TEXT, chroma=int(6 * s), anchor="mm")
        d.text((W / 2, H * 0.30 + 230 * s), "5-IN-1 ASYNC OSINT FRAMEWORK",
               font=font(F_SANS_B, 46 * s), fill=TEAL, anchor="mm")
        d.text((W / 2, H * 0.30 + 310 * s), "python · asyncio · aiohttp",
               font=font(F_MONO, 34 * s), fill=DIM, anchor="mm")
        d.text((W / 2, H * 0.78), "username · gamestats · metadata · breach · bot",
               font=font(F_MONO, 32 * s), fill=DIM, anchor="mm")

    def draw_end(self, img, t):
        W, H, s = self.W, self.H, self.s
        d = ImageDraw.Draw(img)
        import qrcode
        q = qrcode.QRCode(border=2, box_size=10)
        q.add_data("https://" + REPO_URL)
        q.make(fit=True)
        qr_img = q.make_image(fill_color="black", back_color="white").convert("RGB")
        qsize = int(330 * s)
        qr_img = qr_img.resize((qsize, qsize), Image.NEAREST)

        self.chrome_text(d, W / 2, H * 0.16, "ORF-5", font(F_SANS_B, 130 * s), TEXT, chroma=int(5 * s), anchor="mm")
        d.text((W / 2, H * 0.16 + 160 * s), "free & open source · MIT", font=font(F_MONO, 34 * s), fill=TEAL, anchor="mm")
        pad = int(16 * s)
        qx, qy = (W - qsize) // 2, int(H * 0.36)
        d.rounded_rectangle((qx - pad, qy - pad, qx + qsize + pad, qy + qsize + pad), radius=20, fill=(255, 255, 255))
        img.paste(qr_img, (qx, qy))
        d.text((W / 2, qy + qsize + pad + 60 * s), "scan · clone · run", font=font(F_MONO, 32 * s), fill=DIM, anchor="mm")
        d.text((W / 2, H * 0.80), REPO_URL, font=font(F_MONO_B, 33 * s), fill=CYAN, anchor="mm")
        d.text((W / 2, H * 0.86), "windows · linux · macos · termux", font=font(F_MONO, 32 * s), fill=DIM, anchor="mm")

    def draw_term(self, img, scene, t):
        W, H, s = self.W, self.H, self.s
        d = ImageDraw.Draw(img)
        self.caption_slab(img, scene["cap"])

        x0, x1 = W * 0.05, W * 0.95
        y0, y1 = H * 0.16, H * 0.86
        bar = 52 * s
        d.rounded_rectangle((x0, y0, x1, y1), radius=16 * s, fill=TERM_BG, outline=(48, 54, 61), width=2)
        d.rounded_rectangle((x0, y0, x1, y0 + bar), radius=15 * s, fill=TERM_BAR)
        d.rectangle((x0, y0 + bar - 12 * s, x1, y0 + bar), fill=TERM_BAR)
        for i, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
            d.ellipse((x0 + 22 * s + i * 28 * s, y0 + 15 * s, x0 + 38 * s + i * 28 * s, y0 + 31 * s), fill=c)
        tf = font(F_MONO, 17 * s)
        d.text(((x0 + x1) / 2, y0 + bar / 2), "mohit@zorin-os: ~/orf-5", font=tf, fill=DIM, anchor="mm")

        f = font(F_MONO, 32 * s)
        fb = font(F_MONO_B, 32 * s)
        lh = 58 * s
        y = y0 + bar + 34 * s
        for segments, delay, typed in scene["lines"]:
            if t < delay:
                y += lh
                continue
            local = t - delay
            x = x0 + 30 * s
            pop = max(0.0, 0.12 - local) / 0.12 if not typed else 0
            xoff = int(10 * pop * s)
            for text, color, bold in segments:
                shown = text
                if typed:
                    cps = 30.0
                    nchars = min(len(text), int(local * cps))
                    shown = text[:nchars]
                fnt = fb if bold else f
                self.chrome_text(d, x + xoff, y, shown, fnt, COL[color])
                x += fnt.getlength(text)
            if typed and local < len(segments[0][0].replace("$ ", "")) / 30.0 + 0.6:
                if int(t * 3) % 2 == 0:
                    d.rectangle((x + 4 * s, y, x + 4 * s + 18 * s, y + 34 * s), fill=GREEN)
            y += lh

        # exposed flash for breach scene
        if "BREACH" in scene["cap"] and t > 2.1 and int(t * 4) % 2 == 0:
            d.rectangle((x0, y1 - 6 * s, x1, y1), fill=YELLOW)

        self.bottom_strip(d)

    # -- master ---------------------------------------------------------------
    def frame(self, t: float, scene, t_scene: int) -> Image.Image:
        W, H = self.W, self.H
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        for y in range(0, H, 8):  # subtle vertical gradient
            a = int(6 * (y / H))
            d.line([(0, y), (W, y)], fill=(10 + a, 12 + a, 16 + a))

        if scene["kind"] == "hook":
            self.draw_hook(img, t)
            self.bottom_strip(ImageDraw.Draw(img))
        elif scene["kind"] == "end":
            self.draw_end(img, t)
        else:
            self.draw_term(img, scene, t_scene)

        # glitch cut at scene start
        if t_scene < 0.28:
            rng = random.Random(int(t * 1000) // 3)
            for _ in range(7):
                gy = rng.randint(0, H - 60)
                gh = rng.randint(10, 46)
                dx = rng.randint(-60, 60)
                band = img.crop((0, gy, W, gy + gh))
                img.paste(band, (dx, gy))
            gd = ImageDraw.Draw(img)
            for _ in range(3):
                gx0, gx1 = sorted((rng.randint(0, W), rng.randint(0, W)))
                gy0, gy1 = sorted((rng.randint(0, H), rng.randint(0, H)))
                gd.rectangle((gx0, gy0, gx1, gy1), outline=(60, 200, 255))

        img = img.convert("RGBA")
        img.alpha_composite(self.scan)
        gy = int((t * 260) % (H + 300)) - 250
        img.alpha_composite(self.glow, (0, gy))
        return img.convert("RGB")


# ---------------------------------------------------------------------------
# encode
# ---------------------------------------------------------------------------
def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    return exe


def render_video(W: int, H: int, out: Path, wav: Path) -> None:
    painter = Painter(W, H)
    exe = ffmpeg_exe()
    cmd = [exe, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", str(wav),
           "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(DUR), str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)

    t = 0.0
    frame_i = 0
    starts = []
    acc = 0.0
    for sc in SCENES:
        starts.append(acc)
        acc += sc["dur"]

    while t < DUR - 1e-9:
        scene = next(sc for sc, st in zip(SCENES, starts) if st <= t < st + sc["dur"])
        t_scene = t - starts[SCENES.index(scene)]
        img = painter.frame(t, scene, t_scene)
        try:
            proc.stdin.write(img.tobytes())
        except BrokenPipeError:
            break
        frame_i += 1
        t = frame_i / FPS

    proc.stdin.close()
    err = proc.stderr.read().decode(errors="replace")
    rc = proc.wait()
    if rc != 0:
        print(err[-2000:])
        raise SystemExit(f"ffmpeg failed for {out}")
    print("wrote", out)


def main() -> None:
    wav = make_beat(SOCIAL / "beat.wav", DUR)
    render_video(1080, 1920, SOCIAL / "promo_vertical.mp4", wav)
    render_video(1920, 1080, SOCIAL / "promo_horizontal.mp4", wav)


if __name__ == "__main__":
    main()
