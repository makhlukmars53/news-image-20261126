"""Draw the 26 Nov 2026 world-news image (1024x1024 PNG), stdlib only.

Layout (fresh: header + left hero column + right 2x2 grid):
  header y 0..100: title + date, gold rule
  hero x 8..492, y 108..1016: Asia shares bounce (rising bars, stats, facts)
  grid x 500..1016, two columns, two rows:
    top-left: Indonesia mine rescue resumes
    top-right: Bank of Korea hikes to 3.25%
    bottom-left: dollar steady
    bottom-right: Indian shares extend gains
All five stories were read in full from Reuters pages first published
Thu 26 Nov 2026; every number on the image comes from those pages.
Deterministic: no time, no randomness, no network, no files read.
Run twice and the output bytes are identical.
"""
import binascii
import hashlib
import math
import os
import struct
import zlib
from pathlib import Path

W, H = 1024, 1024

# 5x7 bitmap font. Each glyph is 7 rows of 5 bits, written as 7 strings
# of 5 characters ('1' = ink). Only capitals, digits and the punctuation
# the image text uses; everything on the image is upper-case.
FONT = {
    "A": ("01110" "10001" "10001" "11111" "10001" "10001" "10001"),
    "B": ("11110" "10001" "10001" "11110" "10001" "10001" "11110"),
    "C": ("01110" "10001" "10000" "10000" "10000" "10001" "01110"),
    "D": ("11110" "10001" "10001" "10001" "10001" "10001" "11110"),
    "E": ("11111" "10000" "10000" "11110" "10000" "10000" "11111"),
    "F": ("11111" "10000" "10000" "11110" "10000" "10000" "10000"),
    "G": ("01110" "10001" "10000" "10111" "10001" "10001" "01111"),
    "H": ("10001" "10001" "10001" "11111" "10001" "10001" "10001"),
    "I": ("01110" "00100" "00100" "00100" "00100" "00100" "01110"),
    "J": ("00111" "00010" "00010" "00010" "00010" "10010" "01100"),
    "K": ("10001" "10010" "10100" "11000" "10100" "10010" "10001"),
    "L": ("10000" "10000" "10000" "10000" "10000" "10000" "11111"),
    "M": ("10001" "11011" "10101" "10101" "10001" "10001" "10001"),
    "N": ("10001" "11001" "10101" "10011" "10001" "10001" "10001"),
    "O": ("01110" "10001" "10001" "10001" "10001" "10001" "01110"),
    "P": ("11110" "10001" "10001" "11110" "10000" "10000" "10000"),
    "Q": ("01110" "10001" "10001" "10001" "10101" "10010" "01101"),
    "R": ("11110" "10001" "10001" "11110" "10100" "10010" "10001"),
    "S": ("01111" "10000" "10000" "01110" "00001" "00001" "11110"),
    "T": ("11111" "00100" "00100" "00100" "00100" "00100" "00100"),
    "U": ("10001" "10001" "10001" "10001" "10001" "10001" "01110"),
    "V": ("10001" "10001" "10001" "10001" "10001" "01010" "00100"),
    "W": ("10001" "10001" "10001" "10101" "10101" "10101" "01010"),
    "X": ("10001" "10001" "01010" "00100" "01010" "10001" "10001"),
    "Y": ("10001" "10001" "01010" "00100" "00100" "00100" "00100"),
    "Z": ("11111" "00001" "00010" "00100" "01000" "10000" "11111"),
    "0": ("01110" "10001" "10011" "10101" "11001" "10001" "01110"),
    "1": ("00100" "01100" "00100" "00100" "00100" "00100" "01110"),
    "2": ("01110" "10001" "00001" "00110" "01000" "10000" "11111"),
    "3": ("11111" "00010" "00100" "00010" "00001" "10001" "01110"),
    "4": ("00010" "00110" "01010" "10010" "11111" "00010" "00010"),
    "5": ("11111" "10000" "11110" "00001" "00001" "10001" "01110"),
    "6": ("00110" "01000" "10000" "11110" "10001" "10001" "01110"),
    "7": ("11111" "00001" "00010" "00100" "01000" "01000" "01000"),
    "8": ("01110" "10001" "10001" "01110" "10001" "10001" "01110"),
    "9": ("01110" "10001" "10001" "01111" "00001" "00010" "01100"),
    " ": ("00000" "00000" "00000" "00000" "00000" "00000" "00000"),
    ".": ("00000" "00000" "00000" "00000" "00000" "01100" "01100"),
    ",": ("00000" "00000" "00000" "00000" "01100" "00100" "01000"),
    "%": ("11001" "11010" "00010" "00100" "01000" "01011" "10011"),
    "+": ("00000" "00100" "00100" "11111" "00100" "00100" "00000"),
    "-": ("00000" "00000" "00000" "11111" "00000" "00000" "00000"),
    "/": ("00001" "00010" "00010" "00100" "01000" "01000" "10000"),
    "$": ("00100" "01111" "10100" "01110" "00101" "11110" "00100"),
    ":": ("00000" "01100" "01100" "00000" "01100" "01100" "00000"),
    "(": ("00010" "00100" "01000" "01000" "01000" "00100" "00010"),
    ")": ("01000" "00100" "00010" "00010" "00010" "00100" "01000"),
    "'": ("00100" "00100" "01000" "00000" "00000" "00000" "00000"),
    "&": ("01100" "10010" "10100" "01000" "10101" "10010" "01101"),
    "!": ("00100" "00100" "00100" "00100" "00100" "00000" "00100"),
    "?": ("01110" "10001" "00001" "00110" "00100" "00000" "00100"),
    "=": ("00000" "00000" "11111" "00000" "11111" "00000" "00000"),
    "#": ("01010" "01010" "11111" "01010" "11111" "01010" "01010"),
    '"': ("01010" "01010" "00000" "00000" "00000" "00000" "00000"),
}


def _c(hexs):
    hexs = hexs.lstrip("#")
    return bytes((int(hexs[0:2], 16), int(hexs[2:4], 16), int(hexs[4:6], 16)))


class Img:
    """RGB canvas as a list of bytearray rows; fills use slice assignment
    (C speed) so a full 1024x1024 render takes seconds, not minutes."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.rows = [bytearray(_c(bg) * w) for _ in range(h)]

    def rect(self, x0, y0, x1, y1, color):
        fill = _c(color) * (x1 - x0)
        for y in range(y0, y1):
            self.rows[y][x0 * 3:x1 * 3] = fill

    def circle(self, cx, cy, r, color):
        b = _c(color)
        for dy in range(-r, r + 1):
            dx = math.isqrt(r * r - dy * dy)
            y = cy + dy
            self.rows[y][(cx - dx) * 3:(cx + dx + 1) * 3] = b * (2 * dx + 1)

    def poly(self, pts, color):
        """Scanline-filled polygon (convex or concave, non-intersecting)."""
        b = _c(color)
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                xa, xb = int(math.ceil(xs[i])), int(math.floor(xs[i + 1]))
                if xb >= xa:
                    self.rows[y][xa * 3:(xb + 1) * 3] = b * (xb - xa + 1)

    def text(self, x, y, s, scale, color):
        """Stamp text left-aligned at (x, y). One glyph is 5x7 cells; each
        cell is scale x scale pixels; advance is 6 cells."""
        b = _c(color)
        for ci, ch in enumerate(s):
            g = FONT.get(ch)
            if g is None:
                raise SystemExit("no glyph for %r" % ch)
            cx = x + ci * 6 * scale
            for r in range(7):
                bits = g[r * 5:(r + 1) * 5]
                c = 0
                while c < 5:
                    if bits[c] == "1":
                        c0 = c
                        while c < 5 and bits[c] == "1":
                            c += 1
                        run = (c - c0) * scale
                        x0 = cx + c0 * scale
                        for dy in range(scale):
                            row = self.rows[y + r * scale + dy]
                            row[x0 * 3:(x0 + run) * 3] = b * run
                    else:
                        c += 1

    def text_w(self, s, scale):
        return len(s) * 6 * scale - scale if s else 0

    def text_c(self, cx, y, s, scale, color):
        self.text(cx - self.text_w(s, scale) // 2, y, s, scale, color)

    def text_checked(self, x, y, s, scale, color, box):
        """Draw text only after proving it fits inside box (x0, y0, x1, y1);
        fail loudly instead of silently overflowing a panel."""
        x0, y0, x1, y1 = box
        if (x < x0 or y < y0 or x + self.text_w(s, scale) > x1
                or y + 7 * scale > y1):
            raise SystemExit("text %r overflows box %r" % (s, box))
        self.text(x, y, s, scale, color)

    def png(self):
        raw = b"".join(b"\x00" + bytes(r) for r in self.rows)
        comp = zlib.compress(raw, 6)

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF))

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def draw_header(img):
    img.text(24, 16, "WORLD NEWS IN ONE IMAGE", 4, "#FFFFFF")
    img.text(24, 60, "THURSDAY 26 NOVEMBER 2026", 2, "#9FB3C8")
    # Gold "5 STORIES" tag, right side of the header.
    img.rect(876, 28, 1000, 31, "#F1C40F")
    img.rect(876, 69, 1000, 72, "#F1C40F")
    img.rect(876, 28, 879, 72, "#F1C40F")
    img.rect(997, 28, 1000, 72, "#F1C40F")
    img.text(885, 43, "5 STORIES", 2, "#F1C40F")
    img.rect(0, 100, W, 104, "#F1C40F")


def draw_hero(img):
    # Asia shares bounce. Hero column x 8..492, y 108..1016.
    img.rect(8, 108, 492, 1016, "#0B2E1F")
    img.rect(8, 108, 492, 112, "#2ECC71")
    img.text(32, 128, "MARKETS", 2, "#7FE3A8")
    img.text_checked(32, 160, "ASIA SHARES", 4, "#FFFFFF", (8, 108, 492, 1016))
    img.text_checked(32, 196, "BOUNCE", 4, "#FFFFFF", (8, 108, 492, 1016))
    # Rising bars, tallest last; white up arrow above the final bar.
    base = 500
    heights = [60, 100, 140, 185, 235, 285]
    x = 40
    for h in heights:
        img.rect(x, base - h, x + 52, base, "#2ECC71")
        img.rect(x, base - h, x + 52, base - h + 12, "#7FE3A8")
        x += 66
    img.poly([(447, 228), (470, 262), (458, 262), (458, 300),
              (436, 300), (436, 262), (424, 262)], "#FFFFFF")
    img.text(32, 540, "NIKKEI +1.6%", 2, "#FFFFFF")
    img.text(32, 572, "KOREA +1.9%", 2, "#FFFFFF")
    img.text(32, 604, "S&P FUT +0.5%", 2, "#FFFFFF")
    img.text(32, 636, "NVIDIA -3.9%  $149.30", 2, "#FF8A7A")
    img.rect(32, 680, 460, 683, "#1E5B38")
    img.text(32, 700, "AT A GLANCE", 2, "#7FE3A8")
    img.text(32, 732, "BRENT $94.81", 2, "#FFFFFF")
    img.text(32, 764, "GOLD $3,566", 2, "#FFFFFF")
    img.text(32, 796, "DOLLAR 103.71", 2, "#FFFFFF")
    img.text(280, 732, "GDP 4.3%", 2, "#FFFFFF")
    img.text(280, 764, "CORE PCE 3.3%", 2, "#FFFFFF")
    img.text(280, 796, "FED HIKE 98%", 2, "#FFFFFF")
    img.text(32, 840, "NOV SO FAR", 2, "#7FE3A8")
    img.text(32, 872, "NIKKEI -8% NOV", 2, "#FF8A7A")
    img.text(32, 904, "KOREA -16% NOV", 2, "#FF8A7A")
    img.text(32, 936, "TAIWAN -15% NOV", 2, "#FF8A7A")
    img.text(32, 968, "ASIA-PAC EX-JAPAN +0.6%", 2, "#FFFFFF")


def draw_mine(img):
    # Indonesia mine rescue resumes. Top-left cell x 500..754, y 108..556.
    img.rect(500, 108, 754, 556, "#3A2415")
    img.rect(500, 108, 754, 112, "#C98A3D")
    img.text(524, 128, "INDONESIA", 2, "#E8C9A8")
    img.text_checked(524, 160, "MINE RESCUE", 3, "#FFFFFF", (500, 108, 754, 556))
    img.text_checked(524, 192, "RESUMES", 3, "#FFFFFF", (500, 108, 754, 556))
    # Mine shaft: arch (circle + rect) with a hanging lamp.
    img.circle(627, 280, 60, "#1A0F08")
    img.rect(567, 280, 687, 420, "#1A0F08")
    img.rect(625, 252, 629, 286, "#8A6A45")
    img.circle(627, 310, 24, "#FFD94D")
    img.circle(627, 310, 11, "#FFF3B0")
    img.text(524, 436, "13 DEAD", 3, "#FFB3A7")
    img.text(524, 468, "13 TRAPPED", 3, "#FFFFFF")
    img.text(524, 508, "100M DEEP", 2, "#E8C9A8")
    img.text(524, 536, "PONGKOR, BOGOR", 2, "#E8C9A8")


def draw_bok(img):
    # Bank of Korea hikes 25 bps to 3.25%. Top-right cell x 762..1016.
    img.rect(762, 108, 1016, 556, "#12294D")
    img.rect(762, 108, 1016, 112, "#4D7DD1")
    img.text(786, 128, "SOUTH KOREA", 2, "#9DB8E8")
    img.text_checked(786, 160, "BOK HIKES", 3, "#FFFFFF", (762, 108, 1016, 556))
    img.text_checked(786, 192, "+25 BPS", 3, "#FFFFFF", (762, 108, 1016, 556))
    img.text(786, 248, "3.25%", 5, "#F1C40F")
    img.text(786, 300, "HIGHEST SINCE", 2, "#FFFFFF")
    img.text(786, 328, "NOV 2024", 2, "#FFFFFF")
    img.text(786, 360, "AFTER OCT PAUSE", 2, "#9DB8E8")
    # Three rising steps: the tightening cycle resumes.
    img.rect(786, 440, 810, 470, "#2ECC71")
    img.rect(820, 410, 844, 470, "#2ECC71")
    img.rect(854, 380, 878, 470, "#2ECC71")
    img.text(786, 484, "FORECAST BY", 2, "#FFFFFF")
    img.text(786, 512, "32 OF 34 ANALYSTS", 2, "#FFFFFF")


def draw_dollar(img):
    # Dollar steady. Bottom-left cell x 500..754, y 564..1016.
    img.rect(500, 564, 754, 1016, "#0E2F1A")
    img.rect(500, 564, 754, 568, "#7FB069")
    img.text(524, 584, "CURRENCIES", 2, "#A8D5A2")
    img.text_checked(524, 616, "DOLLAR", 3, "#FFFFFF", (500, 564, 754, 1016))
    img.text_checked(524, 648, "STEADY", 3, "#FFFFFF", (500, 564, 754, 1016))
    img.circle(627, 780, 52, "#CFE8B8")
    img.circle(627, 780, 40, "#2E7D32")
    img.text(617, 766, "$", 4, "#FFFFFF")
    img.text(524, 856, "INDEX 103.7", 2, "#FFFFFF")
    img.text(524, 888, "10Y 4.8%", 2, "#FFFFFF")
    img.text(524, 920, "YEN 159.06", 2, "#FFFFFF")
    img.text(524, 952, "EURO $1.097", 2, "#FFFFFF")
    img.text(524, 984, "THANKSGIVING", 2, "#A8D5A2")


def draw_india(img):
    # Indian shares extend gains. Bottom-right cell x 762..1016, y 564..1016.
    img.rect(762, 564, 1016, 1016, "#1B2340")
    img.rect(762, 564, 1016, 568, "#E8A33D")
    img.text(786, 584, "INDIA", 2, "#B9C4E8")
    img.text_checked(786, 612, "SHARES", 3, "#FFFFFF", (762, 564, 1016, 1016))
    img.text_checked(786, 644, "EXTEND", 3, "#FFFFFF", (762, 564, 1016, 1016))
    img.text_checked(786, 676, "GAINS", 3, "#FFFFFF", (762, 564, 1016, 1016))
    img.text(786, 716, "GIFT NIFTY", 2, "#B9C4E8")
    img.text(786, 740, "26,061.5", 4, "#F1C40F")
    img.text(786, 796, "+12% IN NOV", 3, "#FFFFFF")
    img.text(786, 844, "FPI $15.16BN", 2, "#FFFFFF")
    img.text(786, 872, "RECORD INFLOW", 2, "#B9C4E8")
    img.text(786, 916, "TARIFF CAP", 2, "#FFFFFF")
    img.text(786, 944, "17% IF DEAL", 2, "#FFFFFF")
    img.text(786, 972, "25% IF NOT", 2, "#FFFFFF")


def main():
    for g in FONT.values():
        if len(g) != 35 or set(g) - {"0", "1"}:
            raise SystemExit("bad glyph in FONT")
    img = Img(W, H, "#0E1626")
    draw_header(img)
    draw_hero(img)
    draw_mine(img)
    draw_bok(img)
    draw_dollar(img)
    draw_india(img)
    data = img.png()
    out = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out.mkdir(parents=True, exist_ok=True)
    dest = out / "entry.png"
    dest.write_bytes(data)
    if dest.stat().st_size != len(data) or len(data) < 10000:
        raise SystemExit("bad output")
    print("wrote", dest, len(data), "bytes",
          hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
