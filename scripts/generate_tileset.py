#!/usr/bin/env python3
"""Build-time pixel-art tileset generator for the Silicon Polis map.

Draws every tile, prop, building and citizen spritesheet pixel-by-pixel on a
small logical canvas (16px-based, no anti-aliasing, limited palette), then
upscales x2 with nearest-neighbor and writes PNGs into
``frontend/public/tileset/``. The frontend loads these as plain Phaser
image/spritesheet assets — this script is a repo-local art tool, NOT a runtime
or project dependency.

Usage (any Python 3.10+ with Pillow):

    backend/.venv/bin/python scripts/generate_tileset.py [--preview DIR]

``--preview DIR`` additionally writes 8x-upscaled copies for human inspection.

Design direction: cozy SNES-era top-down JRPG plaza on a dark, muted palette
that sits well next to the dashboard's console theme (bg #0a0e14, teal accent
#2dd4bf, amber #fbbf24), with subtle sci-fi accents (server rack, antenna,
solar panels, a holographic obelisk) for the "AI colony" flavor.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image

SCALE = 2  # logical pixel -> screen pixel (16px logical tile -> 32px tile)
OUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public" / "tileset"

Color = tuple[int, int, int, int]


def rgb(hex_str: str, alpha: int = 255) -> Color:
    hex_str = hex_str.lstrip("#")
    return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16), alpha)


# ---------------------------------------------------------------------------
# Palette (limited & intentional — tuned against the dark console UI)
# ---------------------------------------------------------------------------
OUT = rgb("10151f")          # universal dark outline
# grass
G_DK = rgb("18301f")
G_BASE = rgb("21402b")
G_LT = rgb("2c5238")
G_HI = rgb("3a6a45")
# dirt path
P_DK = rgb("3c3022")
P_BASE = rgb("52422d")
P_LT = rgb("63523a")
P_HI = rgb("766349")
# plaza cobblestone
C_GAP = rgb("1d2431")
C_BASE = rgb("38425a")
C_BASE2 = rgb("343e54")
C_HI = rgb("475473")
C_SH = rgb("2b3347")
# wood
W_DK = rgb("2e2014")
W_BASE = rgb("5e4026")
W_LT = rgb("7a5632")
W_HI = rgb("926c42")
# stone (bank)
S_SH = rgb("4c5464")
S_BASE = rgb("6c7488")
S_LT = rgb("848ca0")
S_HI = rgb("9aa2b6")
# metal / tech
M_DK = rgb("262d3a")
M_BASE = rgb("3a4456")
M_LT = rgb("546178")
M_HI = rgb("76849c")
# accents
TEAL = rgb("2dd4bf")
TEAL_DIM = rgb("1a7a70")
TEAL_PALE = rgb("9ff5e8")
AMBER = rgb("fbbf24")
AMBER_DIM = rgb("b08420")
WARM = rgb("f0c46d")        # warm window glow
WARM_DIM = rgb("a8873e")
RED = rgb("d85858")
GREEN_LED = rgb("34d399")
SLATE_BODY = rgb("343c50")   # judicial hall walls
SLATE_DK = rgb("262d3e")
WINDOW_DK = rgb("121826")


class Px:
    """Tiny pixel canvas: putpixel helpers over an RGBA Pillow image."""

    def __init__(self, w: int, h: int, fill: Color = (0, 0, 0, 0)) -> None:
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w, h), fill)
        self.px = self.img.load()

    def p(self, x: int, y: int, col: Color) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[x, y] = col

    def rect(self, x: int, y: int, w: int, h: int, col: Color) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.p(xx, yy, col)

    def hline(self, x0: int, x1: int, y: int, col: Color) -> None:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.p(x, y, col)

    def vline(self, x: int, y0: int, y1: int, col: Color) -> None:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.p(x, y, col)

    def disc(self, cx: int, cy: int, r: int, col: Color) -> None:
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r + r // 2:
                    self.p(xx, yy, col)

    def outline(self, col: Color = OUT) -> None:
        """Pixel-art outline: transparent px with an opaque 4-neighbour."""
        edge = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[x, y][3] != 0:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and self.px[nx, ny][3] != 0:
                        edge.append((x, y))
                        break
        for x, y in edge:
            self.px[x, y] = col

    def paste(self, other: "Px", x: int, y: int) -> None:
        self.img.alpha_composite(other.img, (x, y))

    def scaled(self, factor: int = SCALE) -> Image.Image:
        return self.img.resize((self.w * factor, self.h * factor), Image.NEAREST)


GENERATED: dict[str, tuple[int, int]] = {}  # name -> expected final (w, h)


def save(canvas: Px, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = canvas.scaled()
    img.save(OUT_DIR / f"{name}.png")
    GENERATED[name] = img.size


def sheet(frames: list[Px], name: str) -> None:
    fw, fh = frames[0].w, frames[0].h
    strip = Px(fw * len(frames), fh)
    for i, frame in enumerate(frames):
        strip.paste(frame, i * fw, 0)
    save(strip, name)


# ---------------------------------------------------------------------------
# Ground tiles (16x16 logical -> 32x32)
# ---------------------------------------------------------------------------

def grass_tile(variant: str) -> Px:
    t = Px(16, 16, G_BASE)
    rng = random.Random(f"grass-{variant}")
    # mottled noise: dark clumps + light specks
    for _ in range(22):
        x, y = rng.randrange(16), rng.randrange(16)
        t.p(x, y, G_DK if rng.random() < 0.55 else G_LT)
    # short grass blades (2px, light over highlight tip)
    for _ in range(5):
        x, y = rng.randrange(15), rng.randrange(1, 15)
        t.p(x, y, G_LT)
        t.p(x, y - 1, G_HI)
    if variant == "b":  # tufts
        for _ in range(3):
            x, y = rng.randrange(2, 13), rng.randrange(3, 14)
            t.p(x - 1, y, G_LT)
            t.p(x + 1, y, G_LT)
            t.p(x, y - 1, G_HI)
            t.p(x, y, G_DK)
    elif variant == "c":  # tiny amber wildflowers
        for _ in range(2):
            x, y = rng.randrange(2, 13), rng.randrange(2, 13)
            t.p(x, y, AMBER)
            t.p(x + 1, y, rgb("e8e2d0"))
            t.p(x, y + 1, G_HI)
    elif variant == "d":  # rare bioluminescent "data sprout" (sci-fi accent)
        x, y = 6, 8
        t.p(x, y, TEAL_DIM)
        t.p(x, y - 1, TEAL)
        t.p(x + 1, y - 2, TEAL_DIM)
        t.p(x - 1, y + 1, G_DK)
        t.p(x + 1, y + 1, G_DK)
    return t


def path_tile(variant: str) -> Px:
    t = Px(16, 16, P_BASE)
    rng = random.Random(f"path-{variant}")
    for _ in range(26):
        x, y = rng.randrange(16), rng.randrange(16)
        t.p(x, y, P_DK if rng.random() < 0.5 else P_LT)
    # pebbles: 2x1 light stones with a shadow px underneath
    n_pebbles = 2 if variant == "a" else 4
    for _ in range(n_pebbles):
        x, y = rng.randrange(1, 13), rng.randrange(1, 14)
        t.p(x, y, P_HI)
        t.p(x + 1, y, P_LT)
        t.p(x, y + 1, P_DK)
    if variant == "b":  # dry crack
        x, y = 3, 12
        for _ in range(6):
            t.p(x, y, P_DK)
            x += rng.choice((1, 1, 0))
            y += rng.choice((-1, 0, 0))
    # ragged grass fringe on the border so seams against grass read blended
    for i in range(16):
        for x, y in ((i, 0), (i, 15), (0, i), (15, i)):
            if rng.random() < 0.18:
                t.p(x, y, G_BASE)
    return t


def plaza_tile(variant: str) -> Px:
    t = Px(16, 16, C_GAP)
    rng = random.Random(f"plaza-{variant}")
    for i, y0 in enumerate((0, 4, 8, 12)):
        xoff = 0 if i % 2 == 0 else -2
        for x0 in range(xoff, 16, 5):
            base = C_BASE if rng.random() < 0.7 else C_BASE2
            t.rect(x0, y0, 4, 3, base)
            t.hline(x0, x0 + 2, y0, C_HI)       # top-left light catch
            t.p(x0, y0 + 1, C_HI)
            t.hline(x0 + 1, x0 + 3, y0 + 2, C_SH)  # bottom shade
    if variant == "b":
        # cracked stone
        x, y = 2, 5
        for _ in range(5):
            t.p(x, y, C_GAP)
            x += rng.choice((0, 1))
            y += rng.choice((0, 1))
        # faint data conduit glowing through a gap
        t.p(9, 11, TEAL_DIM)
        t.p(10, 11, TEAL)
        t.p(11, 11, TEAL_DIM)
    return t


def plaza_emblem() -> Px:
    """Transparent 32x32 circuit-ring emblem laid over the plaza center."""
    t = Px(32, 32)
    cx, cy = 16, 16
    for y in range(32):
        for x in range(32):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if 132 <= d2 <= 182:  # outer ring (~r 11.5..13.5)
                t.p(x, y, C_HI if (x + y) % 5 else TEAL_DIM)
            elif 40 <= d2 <= 62:  # inner ring (~r 6.5..7.8)
                t.p(x, y, TEAL_DIM if (x + y) % 3 else C_HI)
    # circuit traces with node dots (cardinal directions)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for step in range(2, 6):
            t.p(cx + dx * step, cy + dy * step, TEAL_DIM)
        t.p(cx + dx * 10, cy + dy * 10, TEAL)
    t.rect(15, 15, 2, 2, TEAL)
    t.p(15, 15, TEAL_PALE)
    return t


# ---------------------------------------------------------------------------
# Scenery props (transparent PNGs)
# ---------------------------------------------------------------------------

def tree(variant: str) -> Px:
    t = Px(16, 24)
    rng = random.Random(f"tree-{variant}")
    # trunk + roots
    t.rect(7, 15, 2, 7, W_BASE)
    t.vline(7, 15, 21, W_DK)
    t.p(6, 21, W_DK)
    t.p(9, 21, W_BASE)
    # canopy: layered discs, darker rim -> lit top-left
    cy = 8 if variant == "a" else 9
    t.disc(8, cy, 7, G_DK)
    t.disc(7, cy - 1, 6, G_BASE)
    t.disc(6, cy - 2, 4, G_LT)
    for _ in range(7):  # leaf-cluster highlights
        x, y = rng.randrange(3, 11), rng.randrange(cy - 5, cy + 1)
        t.p(x, y, G_HI)
        t.p(x + 1, y, G_LT)
    for _ in range(5):  # dark leaf holes on the shaded side
        x, y = rng.randrange(8, 14), rng.randrange(cy, cy + 5)
        t.p(x, y, G_DK)
    if variant == "b":  # a couple of amber fruits
        t.p(5, cy + 2, AMBER)
        t.p(11, cy - 1, AMBER_DIM)
    t.outline()
    return t


def lamp_post() -> Px:
    t = Px(8, 24)
    t.rect(2, 21, 4, 2, M_BASE)          # base
    t.hline(2, 5, 21, M_LT)
    t.vline(3, 8, 20, M_BASE)            # pole
    t.vline(4, 8, 20, M_DK)
    t.hline(2, 5, 7, M_BASE)             # crossarm
    t.rect(2, 3, 4, 4, M_DK)             # lamp housing
    t.rect(3, 4, 2, 2, TEAL)             # teal light
    t.p(3, 4, TEAL_PALE)
    t.p(1, 4, TEAL_DIM)                  # faint glow spill
    t.p(6, 4, TEAL_DIM)
    t.hline(3, 4, 2, M_BASE)             # cap
    t.outline()
    return t


def server_rack_frames() -> list[Px]:
    frames = []
    led_sets = (
        ((GREEN_LED, TEAL, AMBER), (TEAL, GREEN_LED, M_DK), (GREEN_LED, M_DK, TEAL)),
        ((M_DK, TEAL, GREEN_LED), (TEAL, RED, GREEN_LED), (M_DK, GREEN_LED, TEAL)),
    )
    for leds in led_sets:
        t = Px(12, 20)
        t.rect(1, 1, 10, 18, M_DK)           # cabinet
        t.rect(2, 2, 8, 16, M_BASE)          # front panel
        t.hline(1, 10, 1, M_LT)              # top light catch
        for row, (a, b, c) in zip((4, 9, 14), leds):
            t.hline(2, 9, row - 1, M_DK)     # unit seam
            t.p(3, row, a)
            t.p(5, row, b)
            t.p(7, row, c)
            t.hline(3, 8, row + 2, rgb("2c3444"))  # vent slit
        t.rect(2, 18, 2, 2, M_DK)            # feet
        t.rect(8, 18, 2, 2, M_DK)
        t.outline()
        frames.append(t)
    return frames


def antenna() -> Px:
    t = Px(16, 24)
    t.vline(8, 8, 21, M_BASE)            # mast
    t.vline(9, 9, 21, M_DK)
    t.hline(5, 8, 22, M_DK)              # tripod feet
    t.hline(9, 12, 22, M_DK)
    t.p(6, 21, M_BASE)
    t.p(11, 21, M_BASE)
    # dish (tilted up-right)
    t.disc(7, 6, 4, M_HI)
    t.disc(6, 7, 3, M_LT)
    t.p(4, 3, M_HI)
    t.vline(10, 3, 5, M_DK)              # feed arm
    t.p(11, 2, RED)                       # feed tip
    t.p(9, 12, TEAL)                      # status light on the mast
    t.outline()
    return t


def solar_panel() -> Px:
    t = Px(16, 12)
    cell = rgb("1e3a5c")
    cell_lt = rgb("2c5480")
    grid = rgb("14263c")
    t.rect(2, 1, 12, 7, cell)
    t.hline(2, 13, 1, cell_lt)           # sky sheen on the top row
    for gx in (5, 9):                    # cell grid
        t.vline(gx, 1, 7, grid)
    t.hline(2, 13, 4, grid)
    t.p(3, 2, rgb("6ea0cc"))             # specular glint
    t.hline(1, 14, 8, M_DK)              # frame edge
    t.vline(4, 9, 10, M_DK)              # legs
    t.vline(11, 9, 10, M_DK)
    t.outline()
    return t


def crates() -> Px:
    t = Px(16, 14)
    # big crate
    t.rect(1, 4, 8, 8, W_LT)
    t.hline(1, 8, 4, W_HI)
    for i in range(8):                   # diagonal brace
        t.p(1 + i, 4 + i if 4 + i < 12 else 11, W_BASE)
    t.hline(1, 8, 11, W_DK)
    t.vline(8, 4, 11, W_DK)
    # small crate leaning on it
    t.rect(10, 7, 6, 5, W_BASE)
    t.hline(10, 15, 7, W_LT)
    t.vline(15, 7, 11, W_DK)
    t.p(12, 9, W_DK)
    t.p(13, 9, W_DK)
    t.outline()
    return t


def holo_obelisk_frames() -> list[Px]:
    """Plaza centerpiece: dark monolith + floating holographic diamond."""
    frames = []
    for i, (dia_y, ring_y) in enumerate(((2, 18), (3, 15), (4, 12), (3, 9))):
        t = Px(16, 24)
        t.rect(4, 21, 8, 3, M_BASE)      # base plinth
        t.hline(4, 11, 21, M_LT)
        t.rect(6, 7, 4, 14, M_DK)        # monolith
        t.vline(6, 7, 20, M_BASE)        # lit left edge
        t.p(7, 7, M_LT)
        # rising energy ring on the monolith
        t.hline(6, 9, ring_y, TEAL_DIM)
        t.p(7, ring_y, TEAL)
        # floating holo diamond (bobs across frames)
        t.p(8, dia_y - 1, TEAL_DIM)
        t.hline(7, 9, dia_y, TEAL)
        t.p(8, dia_y, TEAL_PALE)
        t.p(8, dia_y + 1, TEAL_DIM)
        if i % 2 == 0:                   # sparkle
            t.p(11, dia_y, TEAL_DIM)
        else:
            t.p(5, dia_y - 1, TEAL_DIM)
        t.outline()
        frames.append(t)
    return frames


def soft_shadow() -> Px:
    t = Px(12, 5)
    for y in range(5):
        for x in range(12):
            d = ((x - 5.5) / 5.5) ** 2 + ((y - 2.0) / 2.2) ** 2
            if d <= 0.55:
                t.p(x, y, (0, 0, 0, 95))
            elif d <= 1.0:
                t.p(x, y, (0, 0, 0, 45))
    return t


# ---------------------------------------------------------------------------
# Buildings (transparent PNGs, front-facing)
# ---------------------------------------------------------------------------

def market() -> Px:
    t = Px(32, 28)
    # timber back wall with plank seams
    t.rect(2, 10, 28, 17, W_BASE)
    for y in (13, 17, 21, 25):
        t.hline(2, 29, y, W_DK)
    t.vline(2, 10, 26, W_DK)
    t.vline(29, 10, 26, W_DK)
    # dark stall interior with a shelf of goods
    t.rect(5, 12, 22, 7, rgb("1b1610"))
    t.hline(6, 25, 15, W_DK)
    for x, col in ((8, AMBER), (12, rgb("c46a3a")), (16, TEAL_DIM), (21, AMBER_DIM)):
        t.p(x, 14, col)
        t.p(x + 1, 14, col)
    # counter with produce
    t.rect(4, 19, 24, 4, W_LT)
    t.hline(4, 27, 19, W_HI)
    t.hline(4, 27, 22, W_DK)
    for x, col in ((7, rgb("d88a3c")), (8, rgb("c46a3a")), (14, AMBER), (15, AMBER_DIM), (21, rgb("8fb04a")), (22, rgb("6d8c38"))):
        t.p(x, 18, col)
    # striped awning with scalloped hem
    for y in range(3, 9):
        for x in range(1, 31):
            t.p(x, y, AMBER_DIM if (x // 4) % 2 == 0 else rgb("46331c"))
    t.hline(1, 30, 3, rgb("46331c"))
    for x in range(1, 31):  # scallops: drop an extra px mid-stripe
        if x % 4 == 2:
            t.p(x, 9, AMBER_DIM if (x // 4) % 2 == 0 else rgb("46331c"))
    # awning support posts
    t.vline(3, 9, 26, W_DK)
    t.vline(28, 9, 26, W_DK)
    # hanging sign with a SimCoin mark
    t.rect(23, 10, 5, 4, W_HI)
    t.p(25, 10, W_DK)
    t.p(25, 11, AMBER)
    t.p(25, 12, AMBER_DIM)
    t.outline()
    return t


def bank() -> Px:
    t = Px(32, 32)
    # steps
    t.rect(3, 30, 26, 2, S_SH)
    t.rect(4, 28, 24, 2, S_BASE)
    t.hline(4, 27, 28, S_LT)
    # facade
    t.rect(4, 11, 24, 17, S_BASE)
    # pediment
    for i in range(5):
        t.hline(6 + i * 2, 25 - i * 2, 9 - i, S_LT)
    t.hline(4, 27, 10, S_HI)             # cornice
    t.hline(4, 27, 11, S_SH)
    # coin emblem in the pediment
    t.p(15, 7, AMBER)
    t.p(16, 7, AMBER)
    t.p(15, 6, AMBER_DIM)
    t.p(16, 8, AMBER_DIM)
    # columns (light face, shaded right edge)
    for cx in (6, 12, 19, 25):
        t.rect(cx, 13, 3, 14, S_LT)
        t.vline(cx, 13, 26, S_HI)
        t.vline(cx + 2, 13, 26, S_SH)
        t.hline(cx - 1, cx + 3, 12, S_HI)   # capital
        t.hline(cx - 1, cx + 3, 27, S_SH)   # plinth
    # doorway (center, warm glow inside)
    t.rect(15, 20, 3, 8, WINDOW_DK)
    t.vline(16, 22, 27, rgb("0c1018"))
    t.p(15, 21, WARM_DIM)
    t.p(17, 21, WARM_DIM)
    t.hline(14, 18, 19, S_SH)
    # windows between columns, warm-lit
    for wx in (9, 22):
        t.rect(wx, 15, 2, 4, WINDOW_DK)
        t.p(wx, 16, WARM)
        t.p(wx + 1, 17, WARM_DIM)
    t.outline()
    return t


def hall() -> Px:
    """Judicial hall — the sci-fi civic building with teal neon trim."""
    t = Px(32, 32)
    # main slab
    t.rect(3, 9, 26, 22, SLATE_BODY)
    t.rect(3, 9, 26, 3, SLATE_DK)        # roof band
    t.hline(3, 28, 9, M_LT)
    # neon edge trim
    t.vline(4, 12, 29, TEAL_DIM)
    t.vline(27, 12, 29, TEAL_DIM)
    t.p(4, 13, TEAL)
    t.p(27, 13, TEAL)
    t.hline(4, 27, 12, TEAL_DIM)
    # roof sign: glowing scales-of-justice glyph on a dark board
    t.rect(10, 2, 12, 6, rgb("161c2a"))
    t.hline(12, 19, 4, TEAL)             # beam
    t.vline(15, 3, 6, TEAL)              # post (center pixel pale)
    t.p(15, 3, TEAL_PALE)
    t.p(12, 5, TEAL_DIM)                 # left pan chain + pan
    t.hline(11, 13, 6, TEAL_DIM)
    t.p(19, 5, TEAL_DIM)                 # right pan chain + pan
    t.hline(18, 20, 6, TEAL_DIM)
    # rooftop antenna nub
    t.vline(24, 5, 8, M_BASE)
    t.p(24, 4, RED)
    # two rows of teal-lit windows
    for wy in (15, 21):
        for wx in (7, 12, 18, 23):
            t.rect(wx, wy, 3, 3, WINDOW_DK)
            t.hline(wx, wx + 2, wy + 2, TEAL_DIM)
            t.p(wx + 1, wy + 2, TEAL)
    # doorway
    t.rect(14, 25, 4, 6, WINDOW_DK)
    t.p(14, 25, TEAL)
    t.p(17, 25, TEAL)
    t.vline(15, 27, 30, rgb("0c1018"))
    t.hline(13, 18, 24, SLATE_DK)
    t.outline()
    return t


# ---------------------------------------------------------------------------
# Citizens: 6-frame grayscale spritesheets (tinted by status at runtime)
# frames: [0] idle A, [1] idle B (breath), [2] step-L, [3] pass, [4] step-R, [5] pass'
# ---------------------------------------------------------------------------

SKIN = rgb("e4e4e4")
EYE = rgb("1e1e1e")
BOOT = rgb("606060")
CITIZEN_OUTLINE = rgb("1a1a1a")

STYLES = ("ada", "boris", "clio", "dorian", "elena")


def citizen_frame(style: str, pose: str) -> Px:
    t = Px(16, 20)
    dy = 1 if pose in ("idle_b", "walk_l", "walk_r") else 0  # contact/breath squash
    shirt = {
        "ada": rgb("cecece"),
        "boris": rgb("aaaaaa"),
        "clio": rgb("d8d8d8"),
        "dorian": rgb("bcbcbc"),
        "elena": rgb("d2d2d2"),
    }[style]
    shirt_sh = tuple(max(0, v - 34) for v in shirt[:3]) + (255,)
    arm = rgb("b4b4b4")
    pants = rgb("929292")
    coat = style == "dorian"

    # --- legs (feet always anchored to the ground line y=19) ---
    leg_top = (16 + dy) if coat else (14 + dy)
    if pose == "walk_l":     # left leg lifted forward, right planted
        t.rect(5, leg_top + 1, 2, 17 - leg_top, pants)
        t.rect(5, 16, 2, 2, BOOT)                       # lifted boot
        t.p(4, 17, BOOT)                                # toe pointing forward
        t.rect(9, leg_top, 2, 19 - leg_top, pants)
        t.rect(9, 18, 2, 2, BOOT)
    elif pose == "walk_r":   # mirror
        t.rect(9, leg_top + 1, 2, 17 - leg_top, pants)
        t.rect(9, 16, 2, 2, BOOT)
        t.p(11, 17, BOOT)
        t.rect(5, leg_top, 2, 19 - leg_top, pants)
        t.rect(5, 18, 2, 2, BOOT)
    else:                    # standing / passing
        t.rect(5, leg_top, 2, 19 - leg_top, pants)
        t.rect(9, leg_top, 2, 19 - leg_top, pants)
        t.rect(5, 18, 2, 2, BOOT)
        t.rect(9, 18, 2, 2, BOOT)
        if pose == "pass_b":  # tiny asymmetry so the two pass frames differ
            t.p(4, 18, BOOT)

    # --- torso ---
    torso_bottom = 15 if coat else 13
    t.rect(5, 8 + dy, 6, torso_bottom - 7, shirt)
    t.vline(10, 8 + dy, torso_bottom + dy, shirt_sh)     # right-side shade
    if coat:                                             # open coat lapels
        t.vline(7, 8 + dy, 14 + dy, shirt_sh)
        t.p(8, 9 + dy, shirt_sh)
    t.hline(5, 10, (torso_bottom + 1 + dy) if not coat else 15 + dy, rgb("6e6e6e"))  # belt/hem

    # --- arms (swing on walk frames) ---
    if pose == "walk_l":
        t.vline(4, 8 + dy, 11 + dy, arm)   # left arm back (short)
        t.vline(11, 9 + dy, 13 + dy, arm)  # right arm swung (long)
        t.p(11, 14 + dy, SKIN)
    elif pose == "walk_r":
        t.vline(11, 8 + dy, 11 + dy, arm)
        t.vline(4, 9 + dy, 13 + dy, arm)
        t.p(4, 14 + dy, SKIN)
    else:
        t.vline(4, 8 + dy, 12 + dy, arm)
        t.vline(11, 8 + dy, 12 + dy, arm)
        t.p(4, 13 + dy, SKIN)
        t.p(11, 13 + dy, SKIN)

    # --- head ---
    t.rect(5, 2 + dy, 6, 6, SKIN)
    t.p(6, 5 + dy, EYE)
    t.p(9, 5 + dy, EYE)

    # --- per-citizen hair / headwear (grayscale values only) ---
    if style == "ada":       # high ponytail
        hair = rgb("f2f2f2")
        t.rect(5, 1 + dy, 6, 2, hair)
        t.p(4, 2 + dy, hair)
        t.vline(12, 2 + dy, 6 + dy, hair)      # ponytail
        t.p(12, 3 + dy, rgb("c2c2c2"))         # tie
        t.p(11, 2 + dy, hair)
    elif style == "boris":   # cautious: deep hood
        hood = rgb("9a9a9a")
        hood_sh = rgb("7c7c7c")
        t.rect(4, 1 + dy, 8, 3, hood)
        t.vline(4, 2 + dy, 8 + dy, hood)
        t.vline(11, 2 + dy, 8 + dy, hood_sh)
        t.hline(5, 10, 2 + dy, hood_sh)        # hood shadow over brow
        t.p(7, 0 + dy, hood)                   # hood point
        t.p(8, 0 + dy, hood_sh)
    elif style == "clio":    # round bob
        hair = rgb("dedede")
        t.rect(4, 1 + dy, 8, 2, hair)
        t.vline(4, 2 + dy, 5 + dy, hair)
        t.vline(11, 2 + dy, 5 + dy, hair)
        t.p(5, 3 + dy, hair)
    elif style == "dorian":  # slicked-back, widow's peak, long coat
        hair = rgb("6a6a6a")
        t.rect(5, 1 + dy, 6, 2, hair)
        t.p(11, 2 + dy, hair)
        t.p(8, 3 + dy, hair)                   # widow's peak
    elif style == "elena":   # long flowing hair over the shoulders
        hair = rgb("ececec")
        t.rect(4, 1 + dy, 8, 2, hair)
        t.vline(4, 2 + dy, 9 + dy, hair)
        t.vline(11, 2 + dy, 9 + dy, hair)
        t.p(5, 2 + dy, hair)
        t.p(3, 8 + dy, hair)
        t.p(12, 8 + dy, hair)

    t.outline(CITIZEN_OUTLINE)
    return t


def citizen_sheet(style: str) -> None:
    poses = ("idle_a", "idle_b", "walk_l", "pass_a", "walk_r", "pass_b")
    sheet([citizen_frame(style, p) for p in poses], f"citizen_{style}")


# ---------------------------------------------------------------------------
# Generation + validation
# ---------------------------------------------------------------------------

def generate_all() -> None:
    for v in ("a", "b", "c", "d"):
        save(grass_tile(v), f"grass_{v}")
    for v in ("a", "b"):
        save(path_tile(v), f"path_{v}")
        save(plaza_tile(v), f"plaza_{v}")
    save(plaza_emblem(), "plaza_emblem")
    save(tree("a"), "tree_a")
    save(tree("b"), "tree_b")
    save(lamp_post(), "lamp")
    save(antenna(), "antenna")
    save(solar_panel(), "solar")
    save(crates(), "crates")
    save(soft_shadow(), "shadow")
    sheet(server_rack_frames(), "server_rack")
    sheet(holo_obelisk_frames(), "obelisk")
    save(market(), "market")
    save(bank(), "bank")
    save(hall(), "hall")
    for style in STYLES:
        citizen_sheet(style)


def validate() -> bool:
    ok = True
    print(f"{'file':<22} {'size':<10} {'colors':>6} {'opaque%':>8}")
    for name, expected in sorted(GENERATED.items()):
        path = OUT_DIR / f"{name}.png"
        img = Image.open(path).convert("RGBA")
        colors = img.getcolors(maxcolors=4096) or []
        n_colors = len(colors)
        opaque = sum(n for n, (_, _, _, a) in colors if a > 0)
        pct = 100.0 * opaque / (img.width * img.height)
        line_ok = img.size == expected and n_colors >= 3 and pct > 8.0
        # ground tiles must be fully opaque
        if any(name.startswith(p) for p in ("grass", "path_", "plaza_a", "plaza_b")):
            line_ok = line_ok and pct == 100.0
        status = "" if line_ok else "  <-- FAIL"
        print(f"{name + '.png':<22} {f'{img.width}x{img.height}':<10} {n_colors:>6} {pct:>7.1f}%{status}")
        ok = ok and line_ok
    return ok


def write_previews(directory: str) -> None:
    dest = Path(directory)
    dest.mkdir(parents=True, exist_ok=True)
    for name in GENERATED:
        img = Image.open(OUT_DIR / f"{name}.png")
        big = img.resize((img.width * 8, img.height * 8), Image.NEAREST)
        big.save(dest / f"{name}.png")


def main() -> int:
    generate_all()
    print(f"wrote {len(GENERATED)} PNGs to {OUT_DIR}\n")
    ok = validate()
    if "--preview" in sys.argv:
        directory = sys.argv[sys.argv.index("--preview") + 1]
        write_previews(directory)
        print(f"\n8x previews written to {directory}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
