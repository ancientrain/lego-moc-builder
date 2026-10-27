#!/usr/bin/env python3
"""奶蛙 (Milk Frog) — a chubby brick-built meme frog on a lily pad.

The body is a solid, hollow-free egg so the sculpture is stable; the face is a
SNOT mosaic built on 1x2 bricks with two side studs (11211).  The reference is
the yellow, pear-shaped frog with a cream belly, green eyes, brown hands/feet and
a tiny tail.  Run it through ``examples/build.py milkfrog``.
"""
from __future__ import annotations

import math

from paths import find_ldraw
from ldrawlib import Library
from model import Model, PALETTE

# LDraw colours
YELLOW = 14
CREAM = 78
BROWN = 84
DARK = 86
FOOT = 308
GREEN = 10
BLACK = 0
WHITE = 15
MOUTH = 320
PINK = 13
PAD = 10
PAD_RIM = 2

CX, CZ = 14.0, 13.0
BODY_BOTTOM = 2
BODY_TOP = 66
FACE_X0 = 8
FACE_ROWS = 7
FACE_LEVEL0 = 42

# (cx, cz, radius, level_min, level_max): feet and a little tail.
LOBES = (
    (8.0, 5.0, 3.2, 2, 9),
    (20.0, 5.0, 3.2, 2, 9),
    (14.0, 22.2, 2.4, 2, 8),
)

# t, rx, rz for the main egg.  t=0 is the bottom, t=1 the crown.  The widest
# point is reached in the plate-built base, then every brick layer is a subset
# of the layer below, so the sculpture needs no impossible overhangs.
PROFILE = (
    (0.00, 10.8, 9.0),
    (0.25, 10.8, 9.0),
    (0.45, 10.4, 8.7),
    (0.65, 9.4, 7.9),
    (0.80, 8.0, 6.8),
    (0.90, 6.6, 5.6),
    (0.97, 4.8, 4.2),
    (1.00, 3.2, 3.0),
)


def _lerp(a, b, t):
    return a + (b - a) * t


def _radii(level):
    t = (level - BODY_BOTTOM) / (BODY_TOP - BODY_BOTTOM)
    t = min(max(t, 0.0), 1.0)
    for i in range(len(PROFILE) - 1):
        t0, x0, z0 = PROFILE[i]
        t1, x1, z1 = PROFILE[i + 1]
        if t <= t1:
            u = (t - t0) / max(t1 - t0, 1e-9)
            return _lerp(x0, x1, u), _lerp(z0, z1, u)
    return PROFILE[-1][1], PROFILE[-1][2]


def _inside_ellipse(x, z, level, p=2.2):
    rx, rz = _radii(level)
    dx = (x + 0.5 - CX) / rx
    dz = (z + 0.5 - CZ) / rz
    return abs(dx) ** p + abs(dz) ** p <= 1.0


def body_cells(level):
    """Cells occupied by the body at *level* (one 3-plate brick layer)."""
    cells = set()
    for x in range(0, 28):
        for z in range(0, 26):
            if _inside_ellipse(x, z, level + 1.5):
                cells.add((x, z))
    for lx, lz, r, lo, hi in LOBES:
        if not (lo <= level + 1.5 <= hi):
            continue
        for x in range(int(lx - r - 1), int(lx + r + 2)):
            for z in range(int(lz - r - 1), int(lz + r + 2)):
                if (x - lx) ** 2 + (z - lz) ** 2 <= r * r:
                    cells.add((x, z))
    # A niche in front of the face so the SNOT mosaic has room.
    if FACE_LEVEL0 <= level <= FACE_LEVEL0 + FACE_ROWS * 3:
        hz = face_host_z(level)
        for x in range(FACE_X0, FACE_X0 + 12):
            for z in range(0, hz):
                cells.discard((x, z))
    return cells


def _front_z(level):
    """Approximate front surface of the main egg at *level*."""
    _rx, rz = _radii(level + 1.5)
    return CZ - rz


def face_host_z(level):
    """Z of the flat SNOT face wall.

    The face is a vertical wall at one fixed z; its bottom row rests on a small
    chin ledge added to the body below, and the rows above stack on it.
    """
    return 5


def colour_at(x, z, level):
    # feet: dark brown pads at the very front bottom
    if level <= 8 and z <= 5 and (abs(x + 0.5 - 8) <= 2.6 or abs(x + 0.5 - 20) <= 2.6):
        return FOOT
    # hands: dark brown ends resting on the sides of the belly
    if 16 <= level <= 26 and z <= _front_z(level) + 2.0 and (x <= 8 or x >= 20):
        return DARK
    # cream belly: front two studs, oval in x / level
    if 5 <= level <= 39 and z <= _front_z(level) + 1.8:
        u = (x + 0.5 - CX) / 6.4
        v = (level + 1.5 - 22.0) / 17.0
        if u * u + v * v <= 1.0:
            return CREAM
    return YELLOW


BRICKS = (
    ("3001", 0), ("3001", 90),
    ("3002", 0), ("3002", 90),
    ("3010", 0), ("3010", 90),
    ("3622", 0), ("3622", 90),
    ("3003", 0),
    ("3004", 0), ("3004", 90),
    ("3005", 0),
)

PLATES = (
    ("3036", 0), ("3036", 90),
    ("3020", 0), ("3020", 90),
    ("3795", 0), ("3795", 90),
    ("3034", 0), ("3034", 90),
    ("3031", 0),
    ("3710", 0), ("3710", 90),
    ("3022", 0),
    ("3023b", 0), ("3023b", 90),
    ("3024", 0),
)


def _fill(m, cells, level, colour_fn, shapes, supported=None):
    """Greedy brick tiling that can corbel over a growing cross-section.

    Pass 1 places a brick for every cell that has no cell directly below it,
    choosing an anchor that also covers at least one supported cell.  Pass 2
    fills the rest.  A placed part must always touch a supported cell, so no
    island of "looks connected" bricks is created.
    """
    free = set(cells)
    supported = set(cells) if supported is None else (set(supported) & set(cells))

    def dims(code, rot):
        w, d, _h, _kind = PALETTE[code]
        if rot in (90, 270):
            w, d = d, w
        return w, d

    def put(ax, az, code, rot, colour, must_touch):
        w, d = dims(code, rot)
        block = {(ax + i, az + j) for i in range(w) for j in range(d)}
        if not block <= free:
            return False
        if must_touch and not (block & supported):
            return False
        if any(colour_fn(bx, bz, level) != colour for bx, bz in block):
            return False
        if not m.place(code, colour, ax, az, level, rot, strict=False):
            return False
        free.difference_update(block)
        return True

    # 1. overhangs first: bridge from a supported neighbour outwards
    overhang = set(cells) - supported
    guard = 0
    while overhang and guard < len(cells) * 4 + 16:
        guard += 1
        # pick the cell with the most overhang neighbours, so one brick can
        # cover a whole lip instead of fragmenting it
        x, z = max(
            overhang,
            key=lambda c: sum((c[0] + dx, c[1] + dz) in overhang
                              for dx in (-1, 0, 1) for dz in (-1, 0, 1)),
        )
        if (x, z) not in free:
            overhang.discard((x, z))
            continue
        colour = colour_fn(x, z, level)
        best = None
        for code, rot in shapes:
            w, d = dims(code, rot)
            for ax in range(x - w + 1, x + 1):
                for az in range(z - d + 1, z + 1):
                    block = {(ax + i, az + j) for i in range(w) for j in range(d)}
                    if not block <= free:
                        continue
                    if not (block & supported):
                        continue
                    if any(colour_fn(bx, bz, level) != colour for bx, bz in block):
                        continue
                    score = (len(block & overhang), len(block & supported), w * d)
                    if best is None or score > best[0]:
                        best = (score, code, rot, ax, az)
        if best is None:
            overhang.discard((x, z))
            continue
        _score, code, rot, ax, az = best
        if m.place(code, colour, ax, az, level, rot, strict=False):
            w, d = dims(code, rot)
            block = {(ax + i, az + j) for i in range(w) for j in range(d)}
            free.difference_update(block)
            overhang.difference_update(block)
        else:
            overhang.discard((x, z))

    # 2. normal fill, but never build an island
    for x, z in sorted(cells):
        if (x, z) not in free:
            continue
        colour = colour_fn(x, z, level)
        placed = False
        for code, rot in shapes:
            if put(x, z, code, rot, colour, True):
                placed = True
                break
        if not placed:
            # leave a hidden gap rather than create a floating part
            if (x, z, level - 1) in m.occ:
                m.place(shapes[-1][0], colour, x, z, level, 0, strict=False)


def pad_cells():
    cells = set()
    for x in range(0, 29):
        for z in range(0, 27):
            dx = (x + 0.5 - CX) / 13.4
            dz = (z + 0.5 - CZ) / 11.8
            if abs(dx) ** 2.4 + abs(dz) ** 2.4 <= 1.0:
                # lily-pad notch: a diagonal bite out of the front-left edge
                if x <= 4 and z <= 7 and (4 - x) + (7 - z) <= 5:
                    continue
                cells.add((x, z))
    return cells


def _pad_colour(x, z, level):
    dx = (x + 0.5 - CX) / 13.4
    dz = (z + 0.5 - CZ) / 11.8
    return PAD_RIM if abs(dx) ** 2.4 + abs(dz) ** 2.4 > 0.78 else PAD


def face_pattern():
    """12 x 7 colour grid, row 0 at the top."""
    rows, cols = FACE_ROWS, 12
    face = [[YELLOW] * cols for _ in range(rows)]
    eye = (
        (0, 1, 1, 0),
        (1, 2, 2, 1),
        (1, 2, 2, 1),
        (0, 1, 1, 0),
    )
    for x0, mirror in ((1, False), (7, True)):
        for r in range(4):
            for c in range(4):
                v = eye[r][3 - c if mirror else c]
                if v == 1:
                    face[r][x0 + c] = GREEN
                elif v == 2:
                    face[r][x0 + c] = BLACK
    # laughing mouth, 6 studs wide
    for r in (5, 6):
        for c in range(3, 9):
            face[r][c] = MOUTH
    for c in (5, 6):
        face[5][c] = WHITE
    # blush
    face[5][1] = PINK
    face[5][10] = PINK
    return face


def build():
    lib = Library(find_ldraw())
    m = Model(lib, 28, 26)

    # 1. lily pad
    pad = pad_cells()
    for level in (0, 1):
        supported = set(pad) if level == 0 else {
            (x, z) for (x, z) in pad if (x, z, 0) in m.occ
        }
        _fill(m, pad, level, _pad_colour, PLATES, supported)
    # a tiny flower on the pad rim
    for x, z in ((5, 18), (6, 18), (5, 19), (6, 19)):
        m.place("4073", PINK, x, z, 2)
    m.place("4073", YELLOW, 5, 18, 3)

    # 2a. plate-built base: this is where the body widens, one plate per level
    for level in range(BODY_BOTTOM, 9):
        cells = body_cells(level)
        supported = {(x, z) for (x, z) in cells if (x, z, level - 1) in m.occ}
        _fill(m, cells, level, colour_at, PLATES, supported)

    # 2b. brick body above the widest point; every layer is narrower than the one
    # below, so it is a normal bottom-up stack with no corbelling required.
    hosts = {}
    for level in range(9, BODY_TOP, 3):
        cells = body_cells(level)
        # one-stud chin ledge so the bottom face row has something to stand on
        if level == FACE_LEVEL0 - 3:
            for x in range(FACE_X0, FACE_X0 + 12):
                cells.add((x, 5))
        reserved = set()
        if FACE_LEVEL0 <= level <= FACE_LEVEL0 + (FACE_ROWS - 1) * 3:
            hz = face_host_z(level)
            for x in range(FACE_X0, FACE_X0 + 12):
                reserved.add((x, hz))
        cells -= reserved
        supported = {(x, z) for (x, z) in cells if (x, z, level - 1) in m.occ}
        _fill(m, cells, level, colour_at, BRICKS, supported)
        if reserved:
            hz = face_host_z(level)
            for i in range(6):
                x = FACE_X0 + 2 * i
                hosts[(level, i)] = m.place("11211", YELLOW, x, hz, level)

    # 3. SNOT face mosaic: every pixel is a 1x1 tile on a side stud
    face = face_pattern()
    for row in range(FACE_ROWS):
        level = FACE_LEVEL0 + (FACE_ROWS - 1 - row) * 3
        for col in range(12):
            host = hosts[(level, col // 2)]
            colour = face[row][col]
            round_tile = colour == PINK or (row <= 3 and colour in (GREEN, BLACK))
            tile = "98138" if round_tile else "3070b"
            m.place_on_stud(tile, colour, host, stud=col % 2)
    return m
