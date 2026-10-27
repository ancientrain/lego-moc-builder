"""Grid-based brick model: placement, occupancy, LDraw export, structural checks.

Coordinates
-----------
x, z : studs, right-handed, origin at the model's front-left corner
level: plates above ground (1 plate = 8 LDU); ground surface is level 0
"""
from __future__ import annotations

from dataclasses import dataclass

from ldrawlib import LDU_PLATE, LDU_STUD, Library

# Explicit palette: code -> (width_studs, depth_studs, height_plates, kind)
# Slopes are 2 studs deep in +z and descend towards -z (verified from geometry).
PALETTE = {
    # bricks
    "3005": (1, 1, 3, "brick"),
    "3004": (2, 1, 3, "brick"),
    "3010": (4, 1, 3, "brick"),
    "3009": (6, 1, 3, "brick"),
    "3001": (4, 2, 3, "brick"),
    "3002": (3, 2, 3, "brick"),
    "3003": (2, 2, 3, "brick"),
    "3007": (8, 2, 3, "brick"),
    "3006": (10, 2, 3, "brick"),
    "3245a": (2, 1, 6, "brick"),
    "2377": (2, 1, 6, "window"),
    # plates
    "3024": (1, 1, 1, "plate"),
    "3023b": (2, 1, 1, "plate"),
    "3710": (4, 1, 1, "plate"),
    "3666": (6, 1, 1, "plate"),
    "3022": (2, 2, 1, "plate"),
    "3021": (3, 2, 1, "plate"),
    "3020": (4, 2, 1, "plate"),
    "3034": (8, 2, 1, "plate"),
    # tiles
    "3070b": (1, 1, 1, "tile"),
    "3069b": (2, 1, 1, "tile"),
    # 45 degree slopes (high edge at +z)
    "3040b": (1, 2, 3, "slope"),
    "3039": (2, 2, 3, "slope"),
    "3038": (3, 2, 3, "slope"),
    "3037": (4, 2, 3, "slope"),
    # double slopes
    "3045": (2, 2, 3, "slope_double_convex"),
    "3046": (2, 2, 3, "slope_double_concave"),
    # round
    "3062b": (1, 1, 3, "round_brick"),
    "4073": (1, 1, 1, "round_plate"),
    "6141": (1, 1, 1, "round_plate"),
    # real door / window hardware (BrickLink catalogue)
    "30179": (4, 1, 18, "doorframe"),
    "2377": (2, 1, 6, "window"),
    "4862": (2, 1, 4, "glass"),
    # 33 degree slopes, 3 studs deep, high edge at +z
    "3297": (4, 3, 3, "slope33"),
    "3298": (2, 3, 3, "slope33"),
    # garden
    "33303": (4, 1, 6, "fence"),
    "3470": (4, 4, 18, "tree"),
    "2423": (3, 4, 2, "leaf"),
    "3742": (1, 1, 1, "flower"),
    "3741a": (1, 1, 5, "stem"),
    "3031": (4, 4, 1, "plate"),
    "3795": (2, 6, 1, "plate"),
    "4477": (10, 1, 1, "plate"),
    "3036": (6, 8, 1, "plate"),
    "3028": (12, 6, 1, "plate"),
    # minifig parts (irregular geometry: placed with overlap + y_off)
    "970": (2, 1, 4, "minifig_legs"),
    "973": (2, 1, 5, "minifig_torso"),
    "3626c": (1, 1, 3, "minifig_head"),
    "10048": (2, 2, 2, "hair"),
    "20877": (2, 2, 2, "hair"),
    "30608": (1, 1, 1, "hair"),
    "6141": (1, 1, 1, "round_plate"),
}

ROT_MATRICES = {
    0: (1, 0, 0, 0, 1, 0, 0, 0, 1),
    90: (0, 0, 1, 0, 1, 0, -1, 0, 0),
    180: (-1, 0, 0, 0, 1, 0, 0, 0, -1),
    270: (0, 0, -1, 0, 1, 0, 1, 0, 0),
}


@dataclass(eq=False)
class Part:
    code: str
    colour: int
    x: int
    z: int
    level: int
    rot: int
    w: int
    d: int
    h: int
    kind: str
    index: int = -1
    overlap: bool = False
    y_off: float = 0.0

    @property
    def cells(self):
        return [(self.x + i, self.z + j) for i in range(self.w) for j in range(self.d)]


class Collision(Exception):
    pass


def build_order(parts):
    """Bottom-up order, structural parts before glazing/door leaves at each level."""
    def key(p):
        surface = 1 if p.colour in (43, 47, 70) or p.kind in ("window",) else 0
        return (p.level, surface, p.z, p.x)
    return sorted(parts, key=key)


class Model:
    def __init__(self, lib: Library, width: int, depth: int):
        self.lib = lib
        self.width = width          # studs along x
        self.depth = depth          # studs along z
        self.parts: list[Part] = []
        self.occ: dict[tuple[int, int, int], Part] = {}

    # ---------- placement ----------
    def place(self, code: str, colour: int, x: int, z: int, level: int,
              rot: int = 0, strict: bool = True, overlap: bool = False,
              y_off: float = 0.0) -> Part | None:
        """Place a part on the stud grid.

        overlap=True is for inserts (glass inside a window frame): the part is
        added for rendering and BOM but does not claim occupancy cells.
        """
        if code not in PALETTE:
            raise KeyError(f"{code} not in PALETTE")
        w, d, h, kind = PALETTE[code]
        if rot in (90, 270):
            w, d = d, w
        if x < 0 or z < 0 or x + w > self.width or z + d > self.depth:
            if strict:
                raise Collision(f"{code} out of bounds at ({x},{z}) L{level}")
            return None
        if level < 0:
            if strict:
                raise Collision(f"{code} below ground at ({x},{z}) L{level}")
            return None
        cells = [(x + i, z + j) for i in range(w) for j in range(d)]
        if not overlap:
            for cx, cz in cells:
                for lv in range(level, level + h):
                    if (cx, cz, lv) in self.occ:
                        if strict:
                            raise Collision(
                                f"{code} overlaps {self.occ[(cx, cz, lv)].code} at ({cx},{cz}) L{lv}")
                        return None
        part = Part(code, colour, x, z, level, rot, w, d, h, kind, len(self.parts),
                    overlap, y_off)
        if not overlap:
            for cx, cz in cells:
                for lv in range(level, level + h):
                    self.occ[(cx, cz, lv)] = part
        self.parts.append(part)
        return part

    def try_place(self, code, colour, x, z, level, rot=0):
        try:
            return self.place(code, colour, x, z, level, rot)
        except Collision:
            return None

    def is_free(self, x, z, level, w=1, d=1, h=1):
        if x < 0 or z < 0 or x + w > self.width or z + d > self.depth:
            return False
        for i in range(w):
            for j in range(d):
                for lv in range(level, level + h):
                    if (x + i, z + j, lv) in self.occ:
                        return False
        return True

    # ---------- queries ----------
    def top_surface(self):
        """Highest occupied plate level + 1."""
        if not self.occ:
            return 0
        return max(k[2] for k in self.occ) + 1

    def footprint_ok(self):
        return all(0 <= p.x and 0 <= p.z and p.x + p.w <= self.width
                   and p.z + p.d <= self.depth for p in self.parts)

    # ---------- export ----------
    def world_bbox(self):
        xs, ys, zs = [], [], []
        for p in self.parts:
            rb = self._rotated_bbox(p)
            xs += [rb[0] + p.x * LDU_STUD, rb[3] + p.x * LDU_STUD]
            zs += [rb[2] + p.z * LDU_STUD, rb[5] + p.z * LDU_STUD]
            ys += [-p.level * LDU_PLATE - rb[4], -p.level * LDU_PLATE - rb[1]]
        return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)

    def _rotated_bbox(self, p: Part):
        _polys, bb = self.lib.geometry(p.code)
        m = ROT_MATRICES[p.rot]
        xs, ys, zs = [], [], []
        for i in (0, 1):
            for j in (0, 1):
                for k in (0, 1):
                    vx = bb[0] if i == 0 else bb[3]
                    vy = bb[1] if j == 0 else bb[4]
                    vz = bb[2] if k == 0 else bb[5]
                    xs.append(m[0] * vx + m[1] * vy + m[2] * vz)
                    ys.append(m[3] * vx + m[4] * vy + m[5] * vz)
                    zs.append(m[6] * vx + m[7] * vy + m[8] * vz)
        return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

    def placement_line(self, p: Part) -> str:
        m = ROT_MATRICES[p.rot]
        rb = self._rotated_bbox(p)
        tx = p.x * LDU_STUD - rb[0]
        tz = p.z * LDU_STUD - rb[2]
        ty = -p.level * LDU_PLATE - rb[4] + p.y_off
        mx = " ".join(f"{v:g}" for v in m)
        return (f"1 {p.colour} {tx:g} {ty:g} {tz:g} {mx} {p.code}.dat")

    def to_ldr(self, title: str, steps: int = 12) -> str:
        out = [f"0 {title}", "0 Name: house.ldr", "0 Author: DeepSeek + DSH",
               "0 !LDRAW_ORG Unofficial_Model", ""]
        ordered = build_order(self.parts)
        for i, p in enumerate(ordered):
            out.append(self.placement_line(p))
            if steps and (i + 1) % steps == 0:
                out.append("0 STEP")
        out.append("0")
        return "\n".join(out) + "\n"
