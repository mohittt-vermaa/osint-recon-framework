"""scripts/render_assets.py — regenerate the README/website visuals.

Draws the ORF-5 banner (over docs/assets/banner_bg.jpg) and pixel-accurate
terminal screenshots of real CLI sessions using Pillow. Run from the repo root:

    python scripts/render_assets.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
F_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# GitHub-dark terminal palette
BG = (13, 17, 23)
TITLEBAR = (22, 27, 34)
TEXT = (230, 237, 243)
DIM = (139, 148, 158)
GREEN = (63, 185, 80)
CYAN = (88, 166, 255)
YELLOW = (210, 153, 34)
RED = (248, 81, 73)
MAGENTA = (188, 140, 255)

COLORS = {
    "w": TEXT, "d": DIM, "g": GREEN, "c": CYAN,
    "y": YELLOW, "r": RED, "m": MAGENTA,
}


# ---------------------------------------------------------------------------
# banner
# ---------------------------------------------------------------------------
def render_banner() -> None:
    bg = Image.open(ASSETS / "banner_bg.jpg").convert("RGB")
    # cover-crop to 1280x640
    tw, th = 1280, 640
    scale = max(tw / bg.width, th / bg.height)
    bg = bg.resize((int(bg.width * scale), int(bg.height * scale)))
    left = (bg.width - tw) // 2
    top = (bg.height - th) // 2
    bg = bg.crop((left, top, left + tw, top + th))

    # left-side darkening gradient for text readability
    overlay = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for x in range(tw):
        alpha = int(205 * (1 - x / tw) ** 1.25)
        od.line([(x, 0), (x, th)], fill=(5, 8, 14, alpha))
    img = Image.alpha_composite(bg.convert("RGBA"), overlay)

    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(F_SANS_B, 168)
    sub = ImageFont.truetype(F_SANS, 34)
    small = ImageFont.truetype(F_MONO, 24)
    tag = ImageFont.truetype(F_MONO_B, 22)

    # shadow + title
    d.text((74, 164), "ORF-5", font=big, fill=(0, 0, 0, 170))
    d.text((70, 158), "ORF-5", font=big, fill=(240, 246, 252, 255))

    d.text((74, 372), "Async 5-in-1 OSINT & Reconnaissance Framework", font=sub, fill=(125, 219, 232, 255))
    d.text((74, 428), "username · gamestats · metadata · breach · telegram", font=small, fill=(170, 180, 192, 255))

    # version pill
    pill_text = "v1.1.0 · asyncio + aiohttp"
    bbox = tag.getbbox(pill_text)
    pw, ph = bbox[2] - bbox[0] + 36, bbox[3] - bbox[1] + 22
    py = 500
    d.rounded_rectangle((74, py, 74 + pw, py + ph), radius=ph // 2, outline=(88, 166, 255, 255), width=2)
    d.text((92, py + 9), pill_text, font=tag, fill=(150, 200, 255, 255))

    img.convert("RGB").save(ASSETS / "banner.png", optimize=True)
    print("wrote", ASSETS / "banner.png")


# ---------------------------------------------------------------------------
# terminal screenshots
# ---------------------------------------------------------------------------
def draw_terminal(title: str, lines: list, path: Path) -> None:
    font = ImageFont.truetype(F_MONO, 22)
    bold = ImageFont.truetype(F_MONO_B, 22)
    lh = 36
    pad_x, pad_y = 36, 30
    title_h = 54

    # auto-width so long lines never clip
    longest = 0.0
    for segments in lines:
        x = 0.0
        for seg_text, _seg_color, seg_bold in segments:
            x += (bold if seg_bold else font).getlength(seg_text)
        longest = max(longest, x)
    width = max(1180, int(longest) + pad_x * 2)

    height = title_h + pad_y * 2 + lh * len(lines) + 12

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)

    # window chrome
    d.rounded_rectangle((0, 0, width - 1, height - 1), radius=14, fill=BG, outline=(48, 54, 61), width=2)
    d.rounded_rectangle((1, 1, width - 2, title_h), radius=13, fill=TITLEBAR)
    d.rectangle((1, title_h - 16, width - 2, title_h), fill=TITLEBAR)

    for i, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
        d.ellipse((24 + i * 26, 18, 40 + i * 26, 34), fill=c)
    tf = ImageFont.truetype(F_MONO, 16)
    d.text((width / 2, 26), title, font=tf, fill=DIM, anchor="mm")

    y = title_h + pad_y
    for segments in lines:
        x = pad_x
        for seg_text, seg_color, seg_bold in segments:
            d.text((x, y), seg_text, font=bold if seg_bold else font, fill=COLORS[seg_color])
            x += font.getlength(seg_text)
        y += lh

    img.save(path, optimize=True)
    print("wrote", path)


def s(text: str, color: str = "w", bold: bool = False):
    return (text, color, bold)


def prompt(cmd: str):
    return [s("$ ", "g", True), s(cmd, "w", True)]


def render_shots() -> None:
    draw_terminal(
        "mohit@zorin-os: ~/osint-recon-framework",
        [
            prompt("python main.py username octocat"),
            [s("[*] ", "c"), s("Scanning username 'octocat' across 20 platforms …")],
            [s("[>] ", "m"), s("[+] ", "g"), s("GitHub            ", "w", True), s("FOUND    ", "g", True), s("(HTTP 200, 276 ms)  ", "d"), s("https://github.com/octocat", "c")],
            [s("[>] ", "m"), s("[+] ", "g"), s("HackerNews        ", "w", True), s("FOUND    ", "g", True), s("(HTTP 200, 175 ms)  ", "d"), s("https://news.ycombinator.com/user?id=octocat", "c")],
            [s("[>] ", "m"), s("[+] ", "g"), s("Chess.com         ", "w", True), s("FOUND    ", "g", True), s("(HTTP 200, 173 ms)  ", "d"), s("https://api.chess.com/pub/player/octocat", "c")],
            [s("[>] ", "m"), s("[+] ", "g"), s("Steam Community   ", "w", True), s("FOUND    ", "g", True), s("(HTTP 200, 388 ms)  ", "d"), s("https://steamcommunity.com/id/octocat", "c")],
            [s("[>] ", "m"), s("[!] ", "y"), s("GitLab            ", "w", True), s("BLOCKED  ", "y", True), s("(HTTP 403, 301 ms)  ", "d"), s("https://gitlab.com/octocat", "c")],
            [s("[>] ", "m"), s("[!] ", "y"), s("Instagram         ", "w", True), s("BLOCKED  ", "y", True), s("(HTTP 403, 214 ms)  ", "d"), s("https://www.instagram.com/octocat/", "c")],
            [s("[>] ", "m"), s("[-] ", "r"), s("Twitch            ", "w", True), s("NOT_FOUND", "r", True), s("(HTTP 404, 240 ms)  ", "d"), s("https://www.twitch.tv/octocat", "c")],
            [s("")],
            [s("[+] ", "g"), s("Done.  BLOCKED: 4  FOUND: 6  NOT_FOUND: 10", "w", True)],
            [s("[+] ", "g"), s("Profiles found:")],
            [s("      https://github.com/octocat", "c")],
            [s("      https://api.chess.com/pub/player/octocat", "c")],
        ],
        ASSETS / "shot_username.png",
    )

    draw_terminal(
        "mohit@zorin-os: ~/osint-recon-framework",
        [
            prompt("python main.py metadata https://github.com/octocat"),
            [s("[*] ", "c"), s("Extracting metadata from https://github.com/octocat …")],
            [s("")],
            [s("[+] ", "g"), s("Title: ", "w", True), s("octocat (The Octocat) · GitHub")],
            [s("[*] ", "c"), s("Canonical: https://github.com/octocat")],
            [s("  og:title:       ", "d"), s("octocat - Overview")],
            [s("  og:description: ", "d"), s("octocat has 8 repositories available. Follow their code on GitHub.")],
            [s("  og:image:       ", "d"), s("https://avatars.githubusercontent.com/u/583231?v=4?s=400")],
            [s("  og:url:         ", "d"), s("https://github.com/octocat")],
            [s("  og:type:        ", "d"), s("profile")],
            [s("  og:site_name:   ", "d"), s("GitHub")],
        ],
        ASSETS / "shot_metadata.png",
    )

    draw_terminal(
        "mohit@zorin-os: ~/osint-recon-framework",
        [
            prompt("python main.py breach password123"),
            [s("[*] ", "c"), s("Checking breach exposure for 'password123' (k-anonymity, no plaintext leaves this machine) …")],
            [s("")],
            [s("[!] ", "y"), s("EXPOSED — value appears in the HIBP breached-data corpus (up to 2266543 occurrence(s)).", "y", True)],
            [s("")],
            prompt("python main.py breach xk9q7zz-notreal-8821"),
            [s("[*] ", "c"), s("Checking breach exposure for 'xk9q7zz-notreal-8821' (k-anonymity, no plaintext leaves this machine) …")],
            [s("")],
            [s("[+] ", "g"), s("No match found in the HIBP breached-data corpus.", "g")],
        ],
        ASSETS / "shot_breach.png",
    )


if __name__ == "__main__":
    render_banner()
    render_shots()
