"""Villa: two storeys + attic, garage behind, six-room plan, garden, minifigs.

Plot 28 x 20 studs. House 18 x 12 (x 9..26, z 4..15), garage 8 x 10 attached on
the left (x 1..8, z 4..13). Each storey is a slab + walls + furniture unit that
rests on the storey below, so every floor can be lifted off on its own.
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
BLACK = 0
RED = 4
GREEN = 2
DARK_GREEN = 6
BLUE = 1
YELLOW = 14
TAN = 19
BROWN = 70
DARK_BROWN = 308
ORANGE = 25
GLASS = 43
GREY = 71
DARK_GREY = 72
DARK_RED = 320
TRANS_CLEAR = 47

# --- geometry ------------------------------------------------------------
PLOT_W, PLOT_D = 28, 20
HX, HZ = 8, 4
HW, HD = 18, 12
GX, GZ = 0, 4
GW, GD = 8, 10

COURSES = 6
FLOOR_H = 3 * COURSES          # 18
BASE0 = 1                      # ground storey walls
SLAB1 = BASE0 + FLOOR_H        # 19
BASE1 = SLAB1 + 1              # 20
SLAB2 = BASE1 + FLOOR_H        # 38
BASE2 = SLAB2 + 1              # 39
ATTIC_COURSES = 4
ATTIC_TOP = BASE2 + 3 * ATTIC_COURSES    # 51
ROOF_STEPS = 5

DOOR0_X = HX + 3               # entrance door (4 wide)

OPEN0: dict = {}
OPEN1: dict = {}
OPEN2: dict = {}


def block(table, x, z, a, b):
    table.setdefault((x, z), set()).update(range(a, b))


for x in range(DOOR0_X, DOOR0_X + 4):
    block(OPEN0, x, HZ + HD - 1, 1, 19)
for x in (HX + 8, HX + 9):
    block(OPEN0, x, HZ, 7, 13)
for x in (HX + 12, HX + 13):
    block(OPEN0, x, HZ + HD - 1, 7, 13)
for z in (HZ + 5, HZ + 6):
    block(OPEN0, HX, z, 7, 13)
for z in (HZ + 7, HZ + 8):
    block(OPEN0, HX + HW - 1, z, 7, 13)

for x in (HX + 1, HX + 2, HX + 9, HX + 10):
    block(OPEN1, x, HZ, BASE1 + 6, BASE1 + 12)
for x in (HX + 3, HX + 4, HX + 11, HX + 12):
    block(OPEN1, x, HZ + HD - 1, BASE1 + 6, BASE1 + 12)
for z in (HZ + 6, HZ + 7):
    block(OPEN1, HX, z, BASE1 + 6, BASE1 + 12)
for z in (HZ + 8, HZ + 9):
    block(OPEN1, HX + HW - 1, z, BASE1 + 6, BASE1 + 12)

for gx in (HX, HX + HW - 1):
    for z in (HZ + 4, HZ + 5):
        block(OPEN2, gx, z, BASE2 + 3, BASE2 + 9)
for x in (HX + 6, HX + 7):
    block(OPEN2, x, HZ, BASE2 + 3, BASE2 + 9)
    block(OPEN2, x, HZ + HD - 1, BASE2 + 3, BASE2 + 9)


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


def wall_part(m, cell, level, colour, size, horizontal):
    code = {4: "3010", 2: "3004", 1: "3005"}[size]
    m.place(code, colour, cell[0], cell[1], level, 0 if horizontal else 90)


def build_run(m, cells, level, colour, horizontal, offset, openings=None):
    seg = [None if (openings and level in openings.get(c, set())) else c for c in cells]
    i, n = 0, len(seg)
    if offset and n >= 6 and seg[0] is not None and seg[1] is not None:
        wall_part(m, seg[0], level, colour, 2, horizontal)
        i = 2
    while i < n:
        if seg[i] is None:
            i += 1
            continue
        j = i
        while j < n and seg[j] is not None:
            j += 1
        k = i
        while k < j:
            left = j - k
            for size in (4, 2, 1):
                if left >= size:
                    wall_part(m, seg[k], level, colour, size, horizontal)
                    k += size
                    break
        i = j


def wall_runs():
    front = [((HX + i), HZ) for i in range(HW)]
    back = [((HX + i), HZ + HD - 1) for i in range(HW)]
    left = [(HX, HZ + j) for j in range(1, HD - 1)]
    right = [(HX + HW - 1, HZ + j) for j in range(1, HD - 1)]
    return [(front, True), (back, True), (left, False), (right, False)]


def window(m, x, z, level, rot=0):
    m.place("2377", WHITE, x, z, level, rot=rot)
    m.place("4862", GLASS, x, z, level, rot=rot, overlap=True)


def storey_walls(m, base, openings, courses=COURSES):
    for c in range(courses):
        level = base + 3 * c
        for cells, horizontal in wall_runs():
            build_run(m, cells, level, WHITE, horizontal, offset=(c % 2), openings=openings)


def partition_x(m, x, z0, z1, base, courses, colour, gap=None):
    for c in range(courses):
        level = base + 3 * c
        z = z0
        while z < z1:
            if gap and level in gap.get(z, set()):
                z += 1
                continue
            run = 0
            while z + run < z1 and not (gap and level in gap.get(z + run, set())):
                run += 1
            size = 4 if run >= 4 else (2 if run >= 2 else 1)
            m.place({4: "3010", 2: "3004", 1: "3005"}[size], colour, x, z, level, rot=90)
            z += size


def partition_z(m, z, x0, x1, base, courses, colour, gap=None):
    for c in range(courses):
        level = base + 3 * c
        x = x0
        while x < x1:
            if gap and level in gap.get(x, set()):
                x += 1
                continue
            run = 0
            while x + run < x1 and not (gap and level in gap.get(x + run, set())):
                run += 1
            size = 4 if run >= 4 else (2 if run >= 2 else 1)
            m.place({4: "3010", 2: "3004", 1: "3005"}[size], colour, x, z, level)
            x += size


def doorway(x_from, x_to, base, height=FLOOR_H):
    d = {}
    for x in range(x_from, x_to):
        d[x] = set(range(base, base + height))
    return d


# --- furniture -----------------------------------------------------------
def bed(m, x, z, level):
    m.place("3001", BROWN, x, z, level)
    m.place("3001", BROWN, x, z + 2, level)
    m.place("3020", WHITE, x, z, level + 3)
    m.place("3020", WHITE, x, z + 2, level + 3)
    m.place("3069b", WHITE, x, z, level + 4)
    m.place("3022", RED, x, z + 2, level + 4)


def table(m, x, z, level, colour=BROWN):
    for dx in (0, 1):
        for dz in (0, 1):
            m.place("3005", colour, x + dx, z + dz, level)
    m.place("3020", colour, x, z, level + 3)


def chair(m, x, z, level, colour=DARK_GREY):
    m.place("3024", colour, x, z, level)
    m.place("3005", colour, x, z, level + 1)
    m.place("3022", colour, x, z, level + 4)


def sofa(m, x, z, level, colour=BLUE):
    m.place("3020", colour, x, z, level)
    m.place("3010", colour, x, z, level + 1)


def counter(m, x, z, level, colour=BROWN, length=4):
    code = {4: "3010", 2: "3004", 6: "3009"}[length]
    top = {4: "3710", 2: "3023b", 6: "3666"}[length]
    m.place(code, colour, x, z, level)
    m.place(top, TAN, x, z, level + 3)


def shelf(m, x, z, level, colour=BROWN):
    m.place("3004", colour, x, z, level, rot=90)
    m.place("3004", colour, x, z, level + 3, rot=90)
    m.place("3023b", colour, x, z, level + 6, rot=90)


def wardrobe(m, x, z, level, colour=DARK_BROWN):
    m.place("3003", colour, x, z, level)
    m.place("3003", colour, x, z, level + 3)
    m.place("3022", colour, x, z, level + 6)


def bathtub(m, x, z, level):
    m.place("3020", WHITE, x, z, level)
    m.place("3710", WHITE, x, z, level + 1)
    m.place("3023b", TRANS_CLEAR, x + 1, z, level + 1, overlap=True)


def toilet(m, x, z, level):
    m.place("3023b", WHITE, x, z, level)
    m.place("3024", WHITE, x, z, level + 1)


def sink(m, x, z, level):
    m.place("3024", GREY, x, z, level)
    m.place("3023b", WHITE, x, z, level + 1)


def desk(m, x, z, level, colour=BROWN):
    m.place("3005", colour, x, z, level)
    m.place("3005", colour, x + 3, z, level)
    m.place("3020", colour, x, z, level + 3)


def minifig(m, x, z, level, legs, torso, head, hair=None, hair_colour=BROWN):
    m.place("970", legs, x, z, level, overlap=True)
    m.place("973", torso, x, z, level, y_off=-32, overlap=True)
    m.place("3626c", head, x, z, level, y_off=-76, overlap=True)
    if hair:
        m.place(hair, hair_colour, x, z, level, y_off=-100, overlap=True)


# --- storeys -------------------------------------------------------------
def build_plot(m):
    fill_rect(m, 0, 0, PLOT_W, HZ, 0, GREEN)                       # front lawn
    fill_rect(m, 0, HZ + HD, PLOT_W, PLOT_D - HZ - HD, 0, GREEN)   # back lawn
    fill_rect(m, HX + HW, HZ, PLOT_W - HX - HW, HD, 0, GREEN)      # right margin
    fill_rect(m, GX, GZ, GW, GD, 0, DARK_GREY)                     # garage floor
    fill_rect(m, GX, GZ + GD, GW, HZ + HD - GZ - GD, 0, GREEN)     # strip in front of garage
    fill_rect(m, HX, HZ, HW, HD, 0, TAN)                           # house floor


def slab(m, level):
    for k in range(3):
        m.place("3028", GREY, HX + 6 * k, HZ, level, rot=90)


def build_ground(m):
    storey_walls(m, BASE0, OPEN0)
    f = 1
    # one spine wall at x=20 with two doorways, plus a kitchen/WC divider
    partition_x(m, HX + 11, HZ + 1, HZ + HD - 1, BASE0, COURSES, WHITE,
                gap={HZ + 3: set(range(BASE0, BASE0 + 18)),
                     HZ + 8: set(range(BASE0, BASE0 + 18))})
    partition_z(m, HZ + 5, HX + 12, HX + HW - 1, BASE0, COURSES, WHITE,
                gap=doorway(HX + 14, HX + 15, BASE0))
    # living zone
    m.place("3069b", TAN, DOOR0_X, HZ + 1, f)          # entrance mat
    sofa(m, HX + 1, HZ + 2, f, BLUE)
    table(m, HX + 2, HZ + 5, f)
    m.place("3010", BROWN, HX + 7, HZ + 2, f)
    m.place("3710", DARK_GREY, HX + 7, HZ + 2, f + 3)
    # dining zone
    table(m, HX + 5, HZ + 8, f)
    chair(m, HX + 3, HZ + 8, f)
    chair(m, HX + 9, HZ + 8, f)
    # kitchen (right front)
    counter(m, HX + 12, HZ + 1, f, BROWN, 4)
    m.place("3003", GREY, HX + 14, HZ + 3, f)
    m.place("3003", GREY, HX + 14, HZ + 3, f + 3)
    # WC (right back)
    toilet(m, HX + 12, HZ + 7, f)
    sink(m, HX + 15, HZ + 7, f)
    # openings
    window(m, HX + 8, HZ, 7)
    window(m, HX + 12, HZ + HD - 1, 7)
    window(m, HX, HZ + 5, 7, rot=90)
    window(m, HX + HW - 1, HZ + 7, 7, rot=90)
    m.place("30179", BROWN, DOOR0_X, HZ + HD - 1, 1)
    for k in range(6):
        m.place("3010", DARK_BROWN, DOOR0_X, HZ + HD - 1, 1 + 3 * k, overlap=True)
    m.place("3070b", YELLOW, DOOR0_X + 3, HZ + HD - 1, 7, overlap=True)


def build_floor1(m):
    slab(m, SLAB1)
    storey_walls(m, BASE1, OPEN1)
    f = SLAB1 + 1
    # left: bedroom / study split
    partition_z(m, HZ + 5, HX + 1, HX + 7, BASE1, COURSES, WHITE,
                gap=doorway(HX + 3, HX + 4, BASE1))
    # spine wall
    partition_x(m, HX + 7, HZ + 1, HZ + HD - 1, BASE1, COURSES, WHITE,
                gap={HZ + 3: set(range(BASE1, BASE1 + 18)),
                     HZ + 8: set(range(BASE1, BASE1 + 18))})
    # right: bedroom2 / landing+bath split
    partition_z(m, HZ + 5, HX + 8, HX + HW - 1, BASE1, COURSES, WHITE,
                gap=doorway(HX + 9, HX + 10, BASE1))
    # bath / landing
    partition_x(m, HX + 12, HZ + 6, HZ + HD - 1, BASE1, COURSES, WHITE,
                gap=doorway(HZ + 8, HZ + 9, BASE1))
    # master bedroom
    bed(m, HX + 1, HZ + 1, f)
    wardrobe(m, HX + 5, HZ + 1, f)
    # study
    desk(m, HX + 1, HZ + 7, f)
    chair(m, HX + 2, HZ + 9, f)
    shelf(m, HX + 6, HZ + 7, f)
    # bedroom 2
    bed(m, HX + 9, HZ + 1, f)
    wardrobe(m, HX + 15, HZ + 1, f)
    # bathroom with bath
    bathtub(m, HX + 13, HZ + 6, f)
    toilet(m, HX + 15, HZ + 9, f)
    sink(m, HX + 13, HZ + 9, f)
    # openings
    for x in (HX + 1, HX + 9):
        window(m, x, HZ, BASE1 + 6)
    for x in (HX + 3, HX + 11):
        window(m, x, HZ + HD - 1, BASE1 + 6)
    window(m, HX, HZ + 6, BASE1 + 6, rot=90)
    window(m, HX + HW - 1, HZ + 8, BASE1 + 6, rot=90)


def build_attic(m):
    slab(m, SLAB2)
    storey_walls(m, BASE2, OPEN2, courses=ATTIC_COURSES)
    f = BASE2
    sofa(m, HX + 6, HZ + 6, f, DARK_GREEN)
    desk(m, HX + 2, HZ + 2, f)
    shelf(m, HX + 12, HZ + 2, f)
    m.place("3022", BROWN, HX + 11, HZ + 6, f)
    window(m, HX, HZ + 4, BASE2 + 3, rot=90)
    window(m, HX + HW - 1, HZ + 4, BASE2 + 3, rot=90)
    for z in (HZ, HZ + HD - 1):
        window(m, HX + 6, z, BASE2 + 3)


def build_roof(m):
    for k in range(ROOF_STEPS):
        level = ATTIC_TOP + 3 * k
        for i in range(0, 16, 4):
            m.place("3037", DARK_RED, HX + i, HZ + k, level)
            m.place("3037", DARK_RED, HX + i, HZ + HD - 2 - k, level, rot=180)
        m.place("3039", DARK_RED, HX + 16, HZ + k, level)
        m.place("3039", DARK_RED, HX + 16, HZ + HD - 2 - k, level, rot=180)
    ridge = ATTIC_TOP + 15
    for i in range(0, 16, 4):
        m.place("3020", DARK_RED, HX + i, HZ + 5, ridge)
    m.place("3022", DARK_RED, HX + 16, HZ + 5, ridge)
    spans = [(0, 6, 14), (1, 7, 13), (2, 8, 12), (3, 9, 11)]
    for gx in (HX, HX + HW - 1):
        for k, z0, z1 in spans:
            for z in range(z0, z1, 2):
                m.place("3004", WHITE, gx, z, ATTIC_TOP + 3 * k, rot=90)


def build_garage(m):
    for c in range(5):
        level = BASE0 + 3 * c
        for x in range(GX, GX + GW, 4):
            m.place("3010", GREY, x, GZ, level)
        for z in range(GZ + 1, GZ + GD - 1, 4):
            m.place("3010", GREY, GX, z, level, rot=90)
            m.place("3010", GREY, GX + GW - 1, z, level, rot=90)
    m.place("3005", GREY, GX, GZ + GD - 1, BASE0)
    fill_rect(m, GX, GZ, GW, GD, BASE0 + 15, GREY)


def car(m, x, z, level):
    for (wx, wz) in ((x, z + 1), (x + 3, z + 1), (x, z + 3), (x + 3, z + 3)):
        m.place("6141", BLACK, wx, wz, level - 1)
    m.place("3020", RED, x, z + 1, level)
    m.place("3020", RED, x, z + 3, level)
    m.place("3020", WHITE, x, z + 1, level + 1)
    m.place("3022", GLASS, x, z + 2, level + 2)


def motorcycle(m, x, z, level):
    m.place("3024", BLACK, x, z, level - 1)
    m.place("3024", BLACK, x, z + 2, level - 1)
    m.place("3023b", BLACK, x, z, level)
    m.place("3023b", BLUE, x, z, level + 1)


def build_garden(m):
    for z in range(GZ + GD, PLOT_D):
        for x in range(GX + 1, GX + GW - 1, 2):
            m.place("3069b", DARK_GREY, x, z, 1)
    for z in range(HZ - 1, HZ - 4, -1):
        for x in range(DOOR0_X, DOOR0_X + 4, 2):
            m.place("3069b", TAN, x, z, 1)
    m.place("3470", GREEN, 8, 16, 1)
    m.place("3470", GREEN, 20, 16, 1)
    for (fx, fz, fc) in ((16, 18, RED), (17, 18, YELLOW), (18, 18, RED), (19, 18, YELLOW)):
        m.place("3741a", GREEN, fx, fz, 1)
        m.place("3742", fc, fx, fz, 5, overlap=True)
    for x in range(0, PLOT_W, 4):
        m.place("33303", WHITE, x, 0, 1)


def build_minifigs(m):
    minifig(m, HX + 10, HZ + 4, 1, BLACK, RED, YELLOW, "10048", BLACK)
    minifig(m, HX + 3, HZ + 8, 1, DARK_GREY, WHITE, YELLOW, "20877", BROWN)
    minifig(m, HX + 3, HZ + 4, SLAB1 + 1, BLUE, WHITE, YELLOW, "10048", BROWN)
    minifig(m, HX + 2, HZ + 9, SLAB1 + 1, DARK_GREY, BLUE, YELLOW)
    minifig(m, GX + 6, GZ + 8, 1, BLACK, YELLOW, YELLOW)


def build(floors=(0, 1, 2), garden=True, minifigs=True):
    lib = Library(LDRAW_ROOT)
    m = Model(lib, PLOT_W, PLOT_D)
    build_plot(m)
    if garden:
        build_garden(m)
    if 0 in floors:
        build_ground(m)
        build_garage(m)
        car(m, GX + 1, GZ + 2, BASE0 + 1)
        motorcycle(m, GX + 5, GZ + 5, BASE0 + 1)
    if 1 in floors:
        build_floor1(m)
    if 2 in floors:
        build_attic(m)
        build_roof(m)
    if minifigs:
        build_minifigs(m)
    return m


if __name__ == "__main__":
    try:
        model = build()
    except Collision as exc:
        print("COLLISION:", exc)
        raise SystemExit(1)
    print(f"built {len(model.parts)} parts")
