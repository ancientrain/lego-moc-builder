"""Grid-based brick model: placement, occupancy, LDraw export, structural checks.

Coordinates
-----------
x, z : studs, right-handed, origin at the model's front-left corner
level: plates above ground (1 plate = 8 LDU); ground surface is level 0

Orientation
-----------
``rot`` may be the legacy yaw (0 / 90 / 180 / 270), a named orientation such as
``"snot+z"``, or a tuple ``(rx, ry, rz)`` of 90-degree steps.  Parts whose
orientation is not a pure yaw are *SNOT* parts: they do not claim stud-grid cells
and are validated through their real stud / underside connections instead.
"""
from __future__ import annotations

from dataclasses import dataclass

from ldrawlib import LDU_PLATE, LDU_STUD, Library
from orientation import (
    IDENTITY, apply, det, normalize_rot, orientation_for_stud, RY,
)

# Explicit palette: code -> (width_studs, depth_studs, height_plates, kind)
# Slopes are 2 studs deep in +z and descend towards -z (verified from geometry).
PALETTE = {
    # bricks
    "3005": (1, 1, 3, "brick"),
    "3004": (2, 1, 3, "brick"),
    "3622": (3, 1, 3, "brick"),
    "3010": (4, 1, 3, "brick"),
    "3009": (6, 1, 3, "brick"),
    "3008": (8, 1, 3, "brick"),
    "3001": (4, 2, 3, "brick"),
    "3002": (3, 2, 3, "brick"),
    "3003": (2, 2, 3, "brick"),
    "2456": (6, 2, 3, "brick"),
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
    "2431": (4, 1, 1, "tile"),
    "6636": (6, 1, 1, "tile"),
    "98138": (1, 1, 1, "tile_round"),
    "14769": (2, 2, 1, "tile_round"),
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
    "3941": (2, 2, 3, "round_brick"),
    "2654": (2, 2, 1, "round_plate"),
    # SNOT
    "11211": (2, 1, 3, "brick_snot"),
    "87087": (1, 1, 3, "brick_snot"),
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
}

# Legacy yaw matrices, kept as a public name for render/check imports.
ROT_MATRICES = RY

YAW_ONLY = frozenset(RY.values())


@dataclass(eq=False)
class Part:
    code: str
    colour: int
    x: float
    z: float
    level: float
    rot: object
    w: int
    d: int
    h: int
    kind: str
    index: int = -1
    overlap: bool = False
    y_off: float = 0.0
    R: tuple = IDENTITY
    tx: float = 0.0
    ty: float = 0.0
    tz: float = 0.0
    snot: bool = False
    aabb: tuple = (0, 0, 0, 0, 0, 0)

    @property
    def cells(self):
        if self.snot:
            return []
        return [(int(self.x) + i, int(self.z) + j)
                for i in range(self.w) for j in range(self.d)]


class Collision(Exception):
    pass


def build_order(parts):
    """Bottom-up order, structural parts before SNOT tiles at each level."""
    def key(p):
        surface = 1 if p.colour in (43, 47, 70) or p.kind in ("window",) else 0
        return (p.level, 1 if p.snot else 0, surface, p.z, p.x)
    return sorted(parts, key=key)


def _aabb_overlap(a, b, eps=0.5):
    """True when two boxes intersect by more than *eps* LDU on every axis."""
    return all(min(a[3 + i], b[3 + i]) - max(a[i], b[i]) > eps for i in range(3))


def _rotated_bbox(bb, R):
    xs, ys, zs = [], [], []
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                vx = bb[0] if i == 0 else bb[3]
                vy = bb[1] if j == 0 else bb[4]
                vz = bb[2] if k == 0 else bb[5]
                rx, ry, rz = apply(R, (vx, vy, vz))
                xs.append(rx)
                ys.append(ry)
                zs.append(rz)
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


class Model:
    def __init__(self, lib: Library, width: int, depth: int):
        self.lib = lib
        self.width = width          # studs along x
        self.depth = depth          # studs along z
        self.parts: list[Part] = []
        self.occ: dict[tuple[int, int, int], Part] = {}

    # ---------- placement ----------
    def place(self, code: str, colour: int, x: float, z: float, level: float,
              rot=0, strict: bool = True, overlap: bool = False,
              y_off: float = 0.0) -> Part | None:
        """Place a part on the stud grid.

        overlap=True is for inserts (glass inside a window frame): the part is
        added for rendering and BOM but does not claim occupancy cells and does
        not participate in collision or support.
        """
        if code not in PALETTE:
            raise KeyError(f"{code} not in PALETTE")
        w, d, h, kind = PALETTE[code]
        R = normalize_rot(rot)
        snot = R not in YAW_ONLY
        if not snot and R in (RY[90], RY[270]):
            w, d = d, w
        if not snot:
            if not (float(x).is_integer() and float(z).is_integer()
                    and float(level).is_integer()):
                raise ValueError("upright parts need integer x/z/level")
            if x < 0 or z < 0 or x + w > self.width or z + d > self.depth:
                if strict:
                    raise Collision(f"{code} out of bounds at ({x},{z}) L{level}")
                return None
            if level < 0:
                if strict:
                    raise Collision(f"{code} below ground at ({x},{z}) L{level}")
                return None
        bb = self.lib.body_bbox(code)
        rb = _rotated_bbox(bb, R)
        tx = x * LDU_STUD - rb[0]
        ty = -level * LDU_PLATE - rb[4] + y_off
        tz = z * LDU_STUD - rb[2]
        return self._add(code, colour, R, tx, ty, tz, w, d, h, kind,
                         x, z, level, rot, strict, overlap, snot)

    def try_place(self, code, colour, x, z, level, rot=0):
        try:
            return self.place(code, colour, x, z, level, rot)
        except Collision:
            return None

    def place_on_stud(self, code: str, colour: int, host: Part, stud: int = 0,
                      spin: int = 0, strict: bool = True,
                      overlap: bool = False) -> Part | None:
        """Attach a part to one of *host*'s studs (including side studs).

        The new part's underside socket is centred on the stud base and its top
        surface points out along the stud normal.  This is the SNOT workhorse:
        a tile placed on a 11211 side stud ends up vertical, in one call.
        """
        if code not in PALETTE:
            raise KeyError(f"{code} not in PALETTE")
        studs = self.world_studs(host)
        if not studs:
            raise ValueError(f"{host.code} has no positive studs")
        s, n = studs[stud % len(studs)]
        R = orientation_for_stud(n, spin)
        bb = self.lib.body_bbox(code)
        bx = (bb[0] + bb[3]) / 2
        by = bb[4]
        bz = (bb[2] + bb[5]) / 2
        rx, ry, rz = apply(R, (bx, by, bz))
        tx, ty, tz = s[0] - rx, s[1] - ry, s[2] - rz
        rb = _rotated_bbox(bb, R)
        level = -(ty + rb[4]) / LDU_PLATE
        w, d, h, kind = PALETTE[code]
        return self._add(code, colour, R, tx, ty, tz, w, d, h, kind,
                         tx / LDU_STUD, tz / LDU_STUD, level,
                         (0, 0, 0), strict, overlap, True)

    def _add(self, code, colour, R, tx, ty, tz, w, d, h, kind,
             gx, gz, level, rot, strict, overlap, snot):
        bb = self.lib.body_bbox(code)
        aabb = _rotated_bbox(bb, R)
        aabb = (aabb[0] + tx, aabb[1] + ty, aabb[2] + tz,
                aabb[3] + tx, aabb[4] + ty, aabb[5] + tz)
        if not overlap:
            if not snot:
                if (aabb[0] / LDU_STUD < -0.6 or aabb[2] / LDU_STUD < -0.6
                        or aabb[3] / LDU_STUD > self.width + 0.6
                        or aabb[5] / LDU_STUD > self.depth + 0.6):
                    if strict:
                        raise Collision(f"{code} out of bounds at ({gx},{gz}) L{level}")
                    return None
                # Legacy grid collision keeps L-shaped parts (trees, fences,
                # flowers) that touch only at their bounding boxes legal.
                for cx in range(int(gx), int(gx) + w):
                    for cz in range(int(gz), int(gz) + d):
                        for lv in range(int(level), int(level) + h):
                            if (cx, cz, lv) in self.occ:
                                if strict:
                                    raise Collision(
                                        f"{code} overlaps {self.occ[(cx, cz, lv)].code} "
                                        f"at ({cx},{cz}) L{lv}")
                                return None
                # A SNOT part can still collide with this upright one.
                for other in self.parts:
                    if other.snot and _aabb_overlap(aabb, other.aabb):
                        if strict:
                            raise Collision(
                                f"{code} overlaps {other.code} at ({gx},{gz}) L{level}")
                        return None
            else:
                for other in self.parts:
                    if other.overlap:
                        continue
                    if _aabb_overlap(aabb, other.aabb):
                        if strict:
                            raise Collision(
                                f"{code} overlaps {other.code} at ({gx},{gz}) L{level}")
                        return None
        part = Part(code, colour, gx, gz, level, rot,
                    w, d, h, kind, len(self.parts), overlap, 0.0,
                    R, tx, ty, tz, snot, aabb)
        if not snot and not overlap:
            for cx, cz in part.cells:
                for lv in range(int(level), int(level) + h):
                    self.occ[(cx, cz, lv)] = part
        self.parts.append(part)
        return part

    def is_free(self, x, z, level, w=1, d=1, h=1):
        if x < 0 or z < 0 or x + w > self.width or z + d > self.depth:
            return False
        for i in range(w):
            for j in range(d):
                for lv in range(level, level + h):
                    if (x + i, z + j, lv) in self.occ:
                        return False
        return True

    # ---------- connections ----------
    def world_studs(self, part: Part):
        """Studs of *part* in world LDU: ((x, y, z), (nx, ny, nz))."""
        out = []
        for pos, n in self.lib.studs(part.code):
            p = apply(part.R, pos)
            nn = apply(part.R, n)
            out.append(((p[0] + part.tx, p[1] + part.ty, p[2] + part.tz), nn))
        return out

    def socket(self, part: Part):
        """Underside face: centre, outward normal, tangent axes and half sizes."""
        bb = self.lib.body_bbox(part.code)
        cx = (bb[0] + bb[3]) / 2
        cy = bb[4]
        cz = (bb[2] + bb[5]) / 2
        c = apply(part.R, (cx, cy, cz))
        c = (c[0] + part.tx, c[1] + part.ty, c[2] + part.tz)
        n = apply(part.R, (0, 1, 0))
        u = apply(part.R, (1, 0, 0))
        v = apply(part.R, (0, 0, 1))
        return {
            "centre": c,
            "normal": n,
            "u": u,
            "v": v,
            "hu": (bb[3] - bb[0]) / 2,
            "hv": (bb[5] - bb[2]) / 2,
        }

    # ---------- queries ----------
    def top_surface(self):
        """Highest occupied plate level + 1."""
        if not self.parts:
            return 0
        return max(p.level + p.h for p in self.parts)

    def footprint_ok(self):
        return all(-0.6 <= p.aabb[0] / LDU_STUD
                   and -0.6 <= p.aabb[2] / LDU_STUD
                   and p.aabb[3] / LDU_STUD <= self.width + 0.6
                   and p.aabb[5] / LDU_STUD <= self.depth + 0.6
                   for p in self.parts)

    # ---------- export ----------
    def world_bbox(self):
        xs, ys, zs = [], [], []
        for p in self.parts:
            _polys, bb = self.lib.geometry(p.code)
            rb = _rotated_bbox(bb, p.R)
            xs += [rb[0] + p.tx, rb[3] + p.tx]
            ys += [rb[1] + p.ty, rb[4] + p.ty]
            zs += [rb[2] + p.tz, rb[5] + p.tz]
        return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)

    def _rotated_bbox(self, p: Part):
        return _rotated_bbox(self.lib.body_bbox(p.code), p.R)

    def placement_line(self, p: Part) -> str:
        mx = " ".join(f"{v:g}" for v in p.R)
        return (f"1 {p.colour} {p.tx:g} {p.ty:g} {p.tz:g} {mx} {p.code}.dat")

    def to_ldr(self, title: str, steps: int = 12) -> str:
        name = "".join(ch if ch.isalnum() or ch in "-_." else "_"
                       for ch in title).strip("_") or "model"
        out = [f"0 {title}", f"0 Name: {name}.ldr", "0 Author: DeepSeek + DSH",
               "0 !LDRAW_ORG Unofficial_Model", ""]
        ordered = build_order(self.parts)
        for i, p in enumerate(ordered):
            out.append(self.placement_line(p))
            if steps and (i + 1) % steps == 0:
                out.append("0 STEP")
        out.append("0")
        return "\n".join(out) + "\n"
