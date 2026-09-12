"""scripts/render_cine.py — cinematic promo videos for ORF-5.

Style study of the reference reel: near-black frame, slow-drifting blue
aurora/earth-glow, a floating dark prompt bar with a typed question and a
model-picker popup, then minimal single-word mono title cards, gentle
camera drift, film grain and an ambient synth score.

Run:  python scripts/render_cine.py
Outputs social/promo_horizontal.mp4 (1280x720) and social/promo_vertical.mp4
(1080x1920) with synthesized ambient audio.
"""
from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOCIAL = ROOT / "social"
SOCIAL.mkdir(exist_ok=True)

F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
F_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

REPO_URL = "github.com/mohittt-vermaa/osint-recon-framework"

FPS = 24
DUR = 14.0

QUESTION = "where does @octocat exist online?"

BAR = (20, 20, 22)
BAR_EDGE = (42, 42, 46)
POP = (26, 26, 28)
WHITE = (245, 246, 248)
DIM = (150, 152, 158)
TEAL = (125, 200, 232)


def font(path, size):
    return ImageFont.truetype(path, max(10, int(size)))


def ease(p):
    return p * p * (3 - 2 * p)


# ---------------------------------------------------------------------------
# aurora background
# ---------------------------------------------------------------------------
class Aurora:
    def __init__(self, W, H):
        self.W, self.H = W, H
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        self.x, self.y = x, y

    def frame(self, t) -> np.ndarray:
        W, H = self.W, self.H
        # earth-glow: huge circle centred far below the frame
        cx = W * (0.5 + 0.10 * math.sin(t * 0.21))
        cy = H * 2.05
        r = H * 1.45
        d = np.sqrt((self.x - cx) ** 2 + (self.y - cy) ** 2)
        glow = np.clip((r - d) / (H * 0.55), 0, 1) ** 2.2
        # drifting comet blob
        bx = W * (0.42 + 0.16 * math.sin(t * 0.35 + 1.2))
        by = H * (0.16 + 0.05 * math.cos(t * 0.27))
        db = np.sqrt(((self.x - bx) / (W * 0.16)) ** 2 + ((self.y - by) / (H * 0.075)) ** 2)
        blob = np.exp(-db * db) * (0.55 + 0.2 * math.sin(t * 0.6))
        val = np.clip(glow * 0.9 + blob, 0, 1)
        fade = min(1.0, t / 1.4)  # intro fade-in
        img = np.zeros((H, W, 3), dtype=np.float32)
        img[..., 0] = val * 62 * fade
        img[..., 1] = val * 128 * fade
        img[..., 2] = val * 214 * fade
        return img


# ---------------------------------------------------------------------------
# UI painting
# ---------------------------------------------------------------------------
def draw_plus(d, x, y, r, color, w=3):
    d.line((x - r, y, x + r, y), fill=color, width=w)
    d.line((x, y - r, x, y + r), fill=color, width=w)


def draw_chevron(d, x, y, r, color, w=4):
    d.line((x + r * 0.5, y - r, x - r * 0.5, y), fill=color, width=w)
    d.line((x - r * 0.5, y, x + r * 0.5, y + r), fill=color, width=w)


def draw_mic(d, x, y, s, color, w=3):
    d.rounded_rectangle((x - s * 0.32, y - s, x + s * 0.32, y + s * 0.25), radius=int(s * 0.32), outline=color, width=w)
    d.arc((x - s * 0.62, y - s * 0.55, x + s * 0.62, y + s * 0.7), start=0, end=180, fill=color, width=w)
    d.line((x, y + s * 0.7, x, y + s * 1.05), fill=color, width=w)
    d.line((x - s * 0.4, y + s * 1.05, x + s * 0.4, y + s * 1.05), fill=color, width=w)


def draw_send(d, x, y, r):
    w = max(3, int(r // 5))
    d.ellipse((x - r, y - r, x + r, y + r), fill=WHITE)
    d.line((x, y + r * 0.45, x, y - r * 0.4), fill=(10, 10, 12), width=w)
    d.line((x - r * 0.32, y - r * 0.12, x, y - r * 0.45), fill=(10, 10, 12), width=w)
    d.line((x + r * 0.32, y - r * 0.12, x, y - r * 0.45), fill=(10, 10, 12), width=w)


def draw_sparkle(d, x, y, r, color):
    pts = [(x, y - r), (x + r * 0.28, y - r * 0.28), (x + r, y), (x + r * 0.28, y + r * 0.28),
           (x, y + r), (x - r * 0.28, y + r * 0.28), (x - r, y), (x - r * 0.28, y - r * 0.28)]
    d.polygon(pts, fill=color)
    d.ellipse((x + r * 0.7, y - r * 1.1, x + r * 1.1, y - r * 0.7), fill=color)


def draw_check(d, x, y, r, color, w=3):
    d.line((x - r, y, x - r * 0.2, y + r * 0.8), fill=color, width=w)
    d.line((x - r * 0.2, y + r * 0.8, x + r, y - r * 0.8), fill=color, width=w)


class CinePainter:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.us = W / 1280.0   # UI scale
        self.ws = H / 720.0    # word/title scale
        self.aurora = Aurora(W, H)
        self.rng = np.random.default_rng(3)

    # -- scenes ---------------------------------------------------------------
    def prompt_scene(self, img, t):
        """floating prompt bar + typing + module picker popup"""
        if t < 0:
            return
        W, H, s = self.W, self.H, self.us
        d = ImageDraw.Draw(img)

        slide = ease(min(1.0, max(0.0, (t - 0.2) / 0.5)))
        bw, bh = min(W * 0.9, 870 * s), 100 * s
        bx0 = (W - bw) / 2
        by0 = H * 0.48 + (1 - slide) * 60 * s

        d.rounded_rectangle((bx0, by0, bx0 + bw, by0 + bh), radius=26 * s, fill=BAR, outline=BAR_EDGE, width=2)
        draw_plus(d, bx0 + 46 * s, by0 + bh - 38 * s, 13 * s, DIM)
        draw_chevron(d, bx0 + bw - 150 * s, by0 + bh - 38 * s, 12 * s, WHITE)
        draw_mic(d, bx0 + bw - 96 * s, by0 + bh - 44 * s, 15 * s, WHITE)
        draw_send(d, bx0 + bw - 42 * s, by0 + bh - 40 * s, 21 * s)

        # typed question
        type_t = max(0.0, t - 0.9)
        n = min(len(QUESTION), int(type_t * 22))
        shown = QUESTION[:n]
        tf = font(F_SANS, 30 * s)
        d.text((bx0 + 86 * s, by0 + 26 * s), shown, font=tf, fill=WHITE)
        if n < len(QUESTION) or int(t * 2.4) % 2 == 0 and t < 4.6:
            tw = tf.getlength(shown)
            d.rectangle((bx0 + 86 * s + tw + 4 * s, by0 + 26 * s, bx0 + 90 * s + tw, by0 + 26 * s + 34 * s), fill=WHITE)

        # module picker popup
        pop_t = (t - 3.1) / 0.45
        if pop_t > 0:
            p = ease(min(1.0, pop_t))
            pw, ph = 300 * s, 120 * s
            px1 = bx0 + bw - 10 * s
            px0 = px1 - pw
            py1 = by0 - 10 * s - (1 - p) * 20 * s
            py0 = py1 - ph
            d.rounded_rectangle((px0, py0, px1, py1), radius=18 * s, fill=POP, outline=BAR_EDGE, width=2)
            draw_sparkle(d, px0 + 34 * s, py0 + 34 * s, 11 * s, WHITE)
            d.text((px0 + 62 * s, py0 + 18 * s), "ORF-5 · full sweep", font=font(F_SANS, 20 * s), fill=WHITE)
            d.text((px0 + 62 * s, py0 + 40 * s), "all five modules", font=font(F_SANS, 15 * s), fill=DIM)
            d.line((px0 + 16 * s, py0 + 60 * s, px1 - 16 * s, py0 + 60 * s), fill=BAR_EDGE, width=2)
            d.text((px0 + 24 * s, py0 + 74 * s), ">_", font=font(F_MONO_B, 20 * s), fill=TEAL)
            d.text((px0 + 62 * s, py0 + 72 * s), "username recon", font=font(F_SANS, 20 * s), fill=WHITE)
            d.text((px0 + 62 * s, py0 + 94 * s), "20 networks", font=font(F_SANS, 15 * s), fill=DIM)
            draw_check(d, px1 - 30 * s, py0 + 86 * s, 9 * s, DIM)

    def word_card(self, img, word, t_local, size=64):
        W, H, s = self.W, self.H, self.ws
        d = ImageDraw.Draw(img)
        a = min(1.0, t_local / 0.35) * min(1.0, (1.8 - t_local) / 0.35 + 0.001)
        col = tuple(int(c * max(0, min(1, a))) for c in WHITE)
        d.text((W / 2, H / 2), word, font=font(F_MONO, size * s), fill=col, anchor="mm")

    def final_card(self, img, t_local):
        W, H = self.W, self.H
        s = self.ws * min(1.0, W / (self.ws * 1150))  # shrink long lines on narrow frames
        d = ImageDraw.Draw(img)
        a = min(1.0, t_local / 0.5)
        d.text((W / 2, H * 0.42), "ORF-5", font=font(F_MONO_B, 90 * s),
               fill=tuple(int(c * a) for c in WHITE), anchor="mm")
        d.text((W / 2, H * 0.42 + 90 * s), "five modules · one command", font=font(F_MONO, 24 * s),
               fill=tuple(int(c * a) for c in TEAL), anchor="mm")
        d.text((W / 2, H * 0.78), REPO_URL, font=font(F_MONO, 26 * s),
               fill=tuple(int(c * a) for c in (110, 170, 235)), anchor="mm")
        d.text((W / 2, H * 0.78 + 44 * s), "free & open source · MIT", font=font(F_MONO, 20 * s),
               fill=tuple(int(c * a) for c in DIM), anchor="mm")

    # -- master ---------------------------------------------------------------
    def frame(self, t) -> Image.Image:
        W, H = self.W, self.H
        arr = self.aurora.frame(t)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")

        if t < 6.2:
            self.prompt_scene(img, t - 1.2 if t >= 1.2 else -1)
        elif 6.6 <= t < 8.4:
            self.word_card(img, "Scan.", t - 6.6)
        elif 8.4 <= t < 10.2:
            self.word_card(img, "Surface.", t - 8.4)
        elif 10.2 <= t < 12.0:
            self.word_card(img, "Verify.", t - 10.2)
        elif t >= 12.0:
            self.final_card(img, t - 12.0)

        # dips to black between scenes
        for boundary in (6.2, 6.6, 8.4, 10.2, 12.0):
            dt = abs(t - boundary)
            if dt < 0.25:
                k = dt / 0.25
                img = Image.fromarray((np.asarray(img).astype(np.float32) * (0.15 + 0.85 * k)).astype(np.uint8))

        # slow camera drift (zoom-in)
        zoom = 1.0 + 0.045 * (t / DUR)
        zw, zh = int(W * zoom), int(H * zoom)
        img = img.resize((zw, zh)).crop(((zw - W) // 2, (zh - H) // 2, (zw - W) // 2 + W, (zh - H) // 2 + H))

        # film grain + vignette
        g = self.rng.integers(-4, 5, (H, W, 1), dtype=np.int16)
        a = np.asarray(img).astype(np.int16) + g
        y, x = np.mgrid[0:H, 0:W]
        vig = 1 - 0.35 * (((x - W / 2) / (W * 0.72)) ** 2 + ((y - H / 2) / (H * 0.72)) ** 2)
        a = a * np.clip(vig, 0.55, 1)[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


# ---------------------------------------------------------------------------
# ambient score
# ---------------------------------------------------------------------------
def make_ambient(path: Path, dur: float, sr: int = 44100) -> Path:
    rng = np.random.default_rng(11)
    n = int(dur * sr)
    buf = np.zeros(n, dtype=np.float64)
    t = np.arange(n) / sr

    # warm pad: Am(add9) — A2 E3 A3 B3 C4, detuned pairs, slow tremolo
    for i, f in enumerate((110.0, 164.81, 220.0, 246.94, 261.63)):
        det = 1 + 0.0012 * (i - 2)
        amp = 0.16 if i < 3 else 0.09
        trem = 0.75 + 0.25 * np.sin(2 * np.pi * (0.07 + 0.02 * i) * t + i)
        buf += np.sin(2 * np.pi * f * det * t) * amp * trem
    # slow filter opening (fake lowpass via blending in brightness)
    bright = np.clip(t / dur, 0, 1)
    buf *= 0.6 + 0.5 * bright

    # sub swells at word cards / final
    for at in (6.6, 8.4, 10.2, 12.0):
        i0 = int(at * sr)
        ln = int(1.6 * sr)
        lt = np.arange(ln) / sr
        env = np.exp(-2.2 * lt) * np.minimum(1, lt / 0.08)
        if i0 + ln <= n:
            buf[i0:i0 + ln] += np.sin(2 * np.pi * 55 * lt) * env * 0.5

    # typing ticks
    for k in range(int(2.1 * 22)):
        at = 2.1 + k / 22.0
        i0 = int(at * sr)
        ln = int(0.03 * sr)
        tick = rng.standard_normal(ln) * np.exp(-ln / (0.008 * sr)) * 0.05
        if i0 + ln <= n:
            buf[i0:i0 + ln] += tick

    # airy shimmer sweep at send (6.2s)
    i0 = int(6.0 * sr)
    ln = int(1.2 * sr)
    lt = np.arange(ln) / sr
    sweep = np.sin(2 * np.pi * (400 + 900 * lt) * lt) * np.exp(-2.5 * lt) * 0.10
    if i0 + ln <= n:
        buf[i0:i0 + ln] += sweep

    # gentle fade in/out
    env = np.minimum(np.minimum(t / 1.2, (dur - t) / 1.5), 1)
    buf *= np.clip(env, 0, 1)

    buf /= np.max(np.abs(buf)) * 1.08
    pcm = (buf * 32767).astype("<i2")
    stereo = np.repeat(pcm, 2)
    raw = stereo.tobytes()
    header = (b"RIFF" + (36 + len(raw)).to_bytes(4, "little") + b"WAVEfmt "
              + (16).to_bytes(4, "little") + (1).to_bytes(2, "little") + (2).to_bytes(2, "little")
              + sr.to_bytes(4, "little") + (sr * 4).to_bytes(4, "little")
              + (4).to_bytes(2, "little") + (16).to_bytes(2, "little")
              + b"data" + len(raw).to_bytes(4, "little"))
    path.write_bytes(header + raw)
    print("wrote", path)
    return path


# ---------------------------------------------------------------------------
def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    return exe


def render(W, H, out, wav):
    painter = CinePainter(W, H)
    cmd = [ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", str(wav),
           "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(DUR), str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    frames = int(DUR * FPS)
    for i in range(frames):
        img = painter.frame(i / FPS)
        try:
            proc.stdin.write(img.tobytes())
        except BrokenPipeError:
            print(proc.stderr.read().decode(errors="replace")[-2500:])
            raise
    proc.stdin.close()
    err = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0:
        print(err[-2500:])
        raise SystemExit("ffmpeg failed")
    print("wrote", out)


def main():
    wav = make_ambient(SOCIAL / "ambient.wav", DUR)
    render(1280, 720, SOCIAL / "promo_horizontal.mp4", wav)
    render(1080, 1920, SOCIAL / "promo_vertical.mp4", wav)


if __name__ == "__main__":
    main()
