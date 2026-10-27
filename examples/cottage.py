"""Design #3: a narrow townhouse with a flat roof.

Plot 12 x 16 studs, house 10 x 14, seven brick courses.
The ceiling is carried by 2x10 bricks (3006) that engage both side walls, so the
roof deck has real support even though the interior is hollow.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from paths import find_ldraw  # noqa: E402

from ldrawlib import Library  # noqa: E402
from model import Collision, Model  # noqa: E402

LDRAW_ROOT = find_ldraw()

# --- palette -------------------------------------------------------------
WALL = 15        # white
PLINTH = 72      # dark bluish grey
ROOF = 320       # dark red
DOOR = 70        # reddish brown
GLASS = 43       # trans light blue
TRIM = 71        # light bluish grey

# --- layout --------------------------------------------------------------
GRID_W, GRID_D = 12, 16
HX, HZ = 1, 1
HW, HD = 10, 14
COURSES = 7
WALL_TOP = 1 + 3 * COURSES          # 22

OPENINGS: dict[tuple[int, int], set[int]] = {}


def block(x, z, a, b):
    OPENINGS.setdefault((x, z), set()).update(range(a, b))


# ground floor
for x in (HX + 2, HX + 3):
    block(x, HZ, 1, 13)                     # door
for x in (HX + 6, HX + 7):
    block(x, HZ, 7, 13)                     # front window
for x in (HX + 3, HX + 4):
    block(x, HZ + HD - 1, 7, 13)            # back window 1
for x in (HX + 6, HX + 7):
    block(x, HZ + HD - 1, 7, 13)            # back window 2
for z in (HZ + 4, HZ + 5):
    block(HX, z, 7, 13)                     # left
for z in (HZ + 8, HZ + 9):
    block(HX + HW - 1, z, 7, 13)            # right
# first floor
for x in (HX + 2, HX + 3):
    block(x, HZ, 16, 22)
for x in (HX + 6, HX + 7):
    block(x, HZ, 16, 22)
for x in (HX + 3, HX + 4):
    block(x, HZ + HD - 1, 16, 22)
for x in (HX + 6, HX + 7):
    block(x, HZ + HD - 1, 16, 22)
for z in (HZ + 4, HZ + 5):
    block(HX, z, 16, 22)
for z in (HZ + 8, HZ + 9):
    block(HX + HW - 1, z, 16, 22)


# --- helpers -------------------------------------------------------------
def fill_rect(m, x0, z0, w, d, level, colour):
    for z in range(z0, z0 + d, 2):
        x = x0
        while x < x0 + w:
            left = x0 + w - x
            if left >= 4:
                m.place("3020", colour, x, z, level)
                x += 4
            else:
                m.place("3022", colour, x, z, level)
                x += 2


def pack_run(m, cells, level, colour, horizontal, offset, brick_colour=None):
    i, n = 0, len(cells)
    if offset and n >= 6:
        _wall_part(m, cells[0], level, brick_colour or colour, 2, horizontal)
        i = 2
    while i < n:
        left = n - i
        for size in (4, 2, 1):
            if left >= size:
                _wall_part(m, cells[i], level, brick_colour or colour, size, horizontal)
                i += size
                break


def _wall_part(m, cell, level, colour, size, horizontal):
    code = {4: "3010", 2: "3004", 1: "3005"}[size]
    m.place(code, colour, cell[0], cell[1], level, 0 if horizontal else 90)


def wall_runs():
    front = [((HX + i), HZ) for i in range(HW)]
    back = [((HX + i), HZ + HD - 1) for i in range(HW)]
    left = [(HX, HZ + j) for j in range(1, HD - 1)]
    right = [(HX + HW - 1, HZ + j) for j in range(1, HD - 1)]
    return [(front, True), (back, True), (left, False), (right, False)]


def build():
    lib = Library(LDRAW_ROOT)
    m = Model(lib, GRID_W, GRID_D)

    # plot
    fill_rect(m, 0, 0, GRID_W, GRID_D, 0, PLINTH)

    # walls
    for course, level in enumerate(range(1, WALL_TOP, 3)):
        colour = PLINTH if course == 0 else WALL
        for cells, horizontal in wall_runs():
            seg = [None if level in OPENINGS.get(c, set()) else c for c in cells]
            k = 0
            while k < len(seg):
                if seg[k] is None:
                    k += 1
                    continue
                j = k
                while j < len(seg) and seg[j] is not None:
                    j += 1
                pack_run(m, seg[k:j], level, colour, horizontal, offset=(course % 2))
                k = j

    # door leaves and glazing
    m.place("3245a", DOOR, HX + 2, HZ + 1, 1)
    m.place("3245a", DOOR, HX + 2, HZ + 1, 7)
    lower = [(HX + 6, HZ, 0), (HX + 3, HZ + HD - 1, 0), (HX + 6, HZ + HD - 1, 0),
             (HX, HZ + 4, 90), (HX + HW - 1, HZ + 8, 90)]
    upper = [(HX + 2, HZ, 0), (HX + 6, HZ, 0),
             (HX + 3, HZ + HD - 1, 0), (HX + 6, HZ + HD - 1, 0),
             (HX, HZ + 4, 90), (HX + HW - 1, HZ + 8, 90)]
    for (x, z, rot) in lower:
        m.place("3245a", GLASS, x, z, 7, rot=rot)
    for (x, z, rot) in upper:
        m.place("3245a", GLASS, x, z, 16, rot=rot)

    # ceiling beams: 2x10 bricks spanning the interior and both side walls
    for z in range(HZ, HZ + HD, 2):
        m.place("3006", WALL, HX, z, WALL_TOP)

    # roof deck, one stud overhang
    fill_rect(m, 0, 0, GRID_W, GRID_D, WALL_TOP + 3, ROOF)
    fill_rect(m, 0, 0, GRID_W, GRID_D, WALL_TOP + 4, ROOF)

    # white fascia around the roof edge
    edge = WALL_TOP + 5
    for x in range(0, GRID_W, 2):
        m.place("3069b", WALL, x, 0, edge)
        m.place("3069b", WALL, x, GRID_D - 1, edge)
    for z in range(2, GRID_D - 2, 2):
        m.place("3069b", WALL, 0, z, edge, rot=90)
        m.place("3069b", WALL, GRID_W - 1, z, edge, rot=90)
    for (cx, cz) in [(0, 1), (0, GRID_D - 2), (GRID_W - 1, 1), (GRID_W - 1, GRID_D - 2)]:
        m.place("3070b", WALL, cx, cz, edge)

    # planters flanking the door
    for px in (HX, HX + 5):
        m.place("3062b", TRIM, px, HZ - 1, 1)
        m.place("6141", 2, px, HZ - 1, 4)
        m.place("6141", 4, px, HZ - 1, 5)

    # chimney
    m.place("3003", ROOF, HX + 7, HZ + 9, WALL_TOP + 5)
    m.place("3003", ROOF, HX + 7, HZ + 9, WALL_TOP + 8)
    m.place("3022", TRIM, HX + 7, HZ + 9, WALL_TOP + 11)

    # doorstep
    m.place("3069b", TRIM, HX + 2, HZ - 1, 1)

    return m


if __name__ == "__main__":
    try:
        model = build()
    except Collision as exc:
        print("COLLISION:", exc)
        raise SystemExit(1)
    print(f"built {len(model.parts)} parts")
