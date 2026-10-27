"""Design #4: cottage with real door/window hardware, furniture, pitched roof, garden.

Plot 16 x 20 studs. House 10 x 14, nine brick courses, 33-degree gable roof.
The roof (with its gable infill) is a lift-off unit, so the interior and its
furniture stay visible. Everything sits on the plate grid and is validated.
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

# --- colours -------------------------------------------------------------
WHITE = 15
GREEN = 2
DARK_GREEN = 6
RED = 4
YELLOW = 14
TAN = 19
BROWN = 70
GLASS = 43
GREY = 71
DARK_GREY = 72
DARK_RED = 320
ORANGE = 25

# --- layout --------------------------------------------------------------
PLOT_W, PLOT_D = 16, 20
HX, HZ = 3, 1
HW, HD = 10, 14
COURSES = 9
WALL_TOP = 1 + 3 * COURSES       # 28
BACK = HZ
FRONT = HZ + HD - 1              # 14
DOOR_X = HX + 3                  # 4 studs wide

OPENINGS: dict[tuple[int, int], set[int]] = {}


def block(x, z, a, b):
    OPENINGS.setdefault((x, z), set()).update(range(a, b))


for x in range(DOOR_X, DOOR_X + 4):
    block(x, FRONT, 1, 19)

WINDOWS = []
for level in (7, 19):
    for x in (HX, HX + 7):
        for dx in (0, 1):
            block(x + dx, FRONT, level, level + 6)
        WINDOWS.append((x, FRONT, level, 0))
    for x in (HX + 2, HX + 6):
        for dx in (0, 1):
            block(x + dx, BACK, level, level + 6)
        WINDOWS.append((x, BACK, level, 0))
    for z in (HZ + 6,):
        for dz in (0, 1):
            block(HX, z + dz, level, level + 6)
        WINDOWS.append((HX, z, level, 90))
    for z in (HZ + 7,):
        for dz in (0, 1):
            block(HX + HW - 1, z + dz, level, level + 6)
        WINDOWS.append((HX + HW - 1, z, level, 90))


# --- helpers -------------------------------------------------------------
def fill_rect(m, x0, z0, w, d, level, colour, plate="3020"):
    for z in range(z0, z0 + d, 2):
        x = x0
        while x < x0 + w:
            left = x0 + w - x
            if left >= 4:
                m.place(plate, colour, x, z, level)
                x += 4
            else:
                m.place("3022", colour, x, z, level)
                x += 2


def pack_run(m, cells, level, colour, horizontal, offset):
    i, n = 0, len(cells)
    if offset and n >= 6:
        _wall_part(m, cells[0], level, colour, 2, horizontal)
        i = 2
    while i < n:
        left = n - i
        for size in (4, 2, 1):
            if left >= size:
                _wall_part(m, cells[i], level, colour, size, horizontal)
                i += size
                break


def _wall_part(m, cell, level, colour, size, horizontal):
    code = {4: "3010", 2: "3004", 1: "3005"}[size]
    m.place(code, colour, cell[0], cell[1], level, 0 if horizontal else 90)


def wall_runs():
    front = [((HX + i), FRONT) for i in range(HW)]
    back = [((HX + i), BACK) for i in range(HW)]
    left = [(HX, HZ + j) for j in range(1, HD - 1)]
    right = [(HX + HW - 1, HZ + j) for j in range(1, HD - 1)]
    return [(front, True), (back, True), (left, False), (right, False)]


# --- sections ------------------------------------------------------------
def build_ground(m):
    fill_rect(m, 0, 0, PLOT_W, PLOT_D, 0, GREEN)


def build_walls(m):
    for course, level in enumerate(range(1, WALL_TOP, 3)):
        colour = GREY if course == 0 else WHITE
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


def build_openings(m):
    m.place("30179", BROWN, DOOR_X, FRONT, 1)                 # door frame
    for k in range(6):                                        # six 1x4 brick leaves
        m.place("3010", BROWN, DOOR_X, FRONT, 1 + 3 * k, overlap=True)
    m.place("3070b", YELLOW, DOOR_X + 3, FRONT, 7, overlap=True)   # handle
    for (x, z, level, rot) in WINDOWS:
        m.place("2377", WHITE, x, z, level, rot=rot)
        m.place("4862", GLASS, x, z, level, rot=rot, overlap=True)


def build_roof(m):
    for k in range(3):                                        # back slope
        level = WALL_TOP + 3 * k
        z = HZ + 2 * k
        for x in (HX, HX + 4):
            m.place("3297", DARK_RED, x, z, level)
        m.place("3298", DARK_RED, HX + 8, z, level)
    for k in range(3):                                        # front slope
        level = WALL_TOP + 3 * k
        z = FRONT - 2 - 2 * k
        for x in (HX, HX + 4):
            m.place("3297", DARK_RED, x, z, level, rot=180)
        m.place("3298", DARK_RED, HX + 8, z, level, rot=180)
    ridge = WALL_TOP + 9
    for x in (HX, HX + 4):
        m.place("3020", DARK_RED, x, HZ + 6, ridge)
    m.place("3022", DARK_RED, HX + 8, HZ + 6, ridge)

    # gable infill (part of the lift-off roof unit)
    for gx in (HX, HX + HW - 1):
        for z in range(HZ + 3, FRONT - 1, 2):
            if m.is_free(gx, z, WALL_TOP, w=1, d=2, h=3):
                m.place("3004", WHITE, gx, z, WALL_TOP, rot=90)
        for z in range(HZ + 5, FRONT - 3, 2):
            if m.is_free(gx, z, WALL_TOP + 3, w=1, d=2, h=3):
                m.place("3004", WHITE, gx, z, WALL_TOP + 3, rot=90)


def build_furniture(m):
    # wooden floor
    fill_rect(m, HX + 1, HZ + 1, HW - 2, HD - 2, 1, TAN)
    x0, z0 = HX + 1, HZ + 2          # interior origin (4, 3)
    b = 2                             # first free plate above the floor
    # rug 4 x 3
    for z in range(z0 + 4, z0 + 7):
        for x in (x0, x0 + 2):
            m.place("3023b", ORANGE, x, z, b)
    # bed 2 x 4 against the back-left corner
    m.place("3001", BROWN, x0, z0, b)
    m.place("3001", BROWN, x0, z0 + 2, b)
    m.place("3020", WHITE, x0, z0, b + 3)
    m.place("3020", WHITE, x0, z0 + 2, b + 3)
    m.place("3069b", WHITE, x0, z0, b + 4)        # pillow
    m.place("3069b", RED, x0 + 2, z0, b + 4)
    m.place("3020", RED, x0, z0 + 2, b + 4)       # blanket
    # table 2x2 + two chairs
    tx, tz = x0 + 4, z0 + 5
    for dx in (0, 1):
        for dz in (0, 1):
            m.place("3005", BROWN, tx + dx, tz + dz, b)
    m.place("3022", BROWN, tx, tz, b + 3)
    m.place("3022", TAN, tx, tz, b + 4)
    for (cx, cz) in ((tx, tz + 2), (tx + 2, tz)):
        m.place("3024", DARK_GREY, cx, cz, b)
        m.place("3005", DARK_GREY, cx, cz, b + 1)
        m.place("3022", DARK_GREY, cx, cz, b + 4)
    # kitchen counter along the front wall
    for x in (x0, x0 + 4):
        m.place("3010", BROWN, x, z0 + 9, b)
        m.place("3710", TAN, x, z0 + 9, b + 3)
    # shelf on the right wall
    m.place("3004", BROWN, x0 + 7, z0, b, rot=90)
    m.place("3004", BROWN, x0 + 7, z0, b + 3, rot=90)
    m.place("3023b", BROWN, x0 + 7, z0, b + 6, rot=90)


def build_garden(m):
    for z in range(FRONT + 1, PLOT_D):
        for x in (DOOR_X, DOOR_X + 2):
            m.place("3069b", TAN, x, z, 1)
    # front fence
    for x in range(0, PLOT_W, 4):
        m.place("33303", WHITE, x, 0, 1)
    # side fences
    for z in (4, 8, 12, 16):
        m.place("33303", WHITE, 0, z, 1, rot=90)
        m.place("33303", WHITE, PLOT_W - 1, z, 1, rot=90)
    # trees
    m.place("3470", GREEN, 1, 15, 1)
    m.place("3470", GREEN, PLOT_W - 5, 15, 1)
    # flowers beside the path
    for (fx, fz, fc) in ((5, 17, RED), (10, 17, YELLOW)):
        m.place("3741a", GREEN, fx, fz, 1)
        m.place("3742", fc, fx, fz, 5, overlap=True)


def build(roof=True):
    lib = Library(LDRAW_ROOT)
    m = Model(lib, PLOT_W, PLOT_D)
    build_ground(m)
    build_walls(m)
    build_openings(m)
    build_furniture(m)
    build_garden(m)
    if roof:
        build_roof(m)
    return m


if __name__ == "__main__":
    try:
        model = build()
    except Collision as exc:
        print("COLLISION:", exc)
        raise SystemExit(1)
    print(f"built {len(model.parts)} parts")
