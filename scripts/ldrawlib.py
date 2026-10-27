"""Minimal LDraw library reader: resolve part files, flatten geometry, compute bounds.

Nothing here knows about colours beyond "16 means inherit"; rendering decides the RGB.
"""
from __future__ import annotations

import os

LDU_STUD = 20.0
LDU_BRICK = 24.0
LDU_PLATE = 8.0

IDENTITY = (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


class Library:
    """Index of an LDraw-format library.

    Studio ships its catalogue as `ldraw/parts` (official) plus
    `ldraw/UnOfficial/parts` (BrickLink's own updated files), so scan both.
    """

    SEARCH_DIRS = ("parts", "p", "UnOfficial/parts", "UnOfficial/p")

    def __init__(self, root: str):
        self.root = root
        bases = [os.path.join(root, d) for d in self.SEARCH_DIRS]
        bases = [b for b in bases if os.path.isdir(b)]
        if not bases:
            raise SystemExit(f"not an LDraw library: {root}")
        self._index = {}
        for base in bases:
            for dirpath, _dirnames, filenames in os.walk(base):
                for fn in filenames:
                    if fn.lower().endswith((".dat", ".ldr")):
                        self._index.setdefault(fn.lower(), os.path.join(dirpath, fn))
        self._geom_cache: dict[str, tuple[list, tuple]] = {}

    # ---------- lookup ----------
    def path_of(self, name: str) -> str | None:
        # LDraw references use backslashes (s\3001s01.dat) even on Linux.
        key = os.path.basename(name.replace("\\", "/")).lower()
        if not key.endswith((".dat", ".ldr")):
            key += ".dat"
        return self._index.get(key)

    def exists(self, code: str) -> bool:
        return self.path_of(code) is not None

    # ---------- geometry ----------
    def geometry(self, code: str):
        """Return (polygons, bbox) for a part code.

        polygons: list of (colour, [(x, y, z), ...]) in part-local LDraw coords.
        bbox: (minx, miny, minz, maxx, maxy, maxz)
        """
        key = os.path.basename(code).lower()
        if key in self._geom_cache:
            return self._geom_cache[key]
        path = self.path_of(code)
        if path is None:
            raise KeyError(f"part not found: {code}")
        polys: list = []
        self._walk(path, 16, polys, 0, (0.0, 0.0, 0.0),
                   [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0])
        if not polys:
            raise ValueError(f"empty geometry: {code}")
        xs = [v[0] for _c, vs in polys for v in vs]
        ys = [v[1] for _c, vs in polys for v in vs]
        zs = [v[2] for _c, vs in polys for v in vs]
        bbox = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
        result = (polys, bbox)
        self._geom_cache[key] = result
        return result

    def _walk(self, path, colour, out, depth, t, m):
        """Read `path`, applying affine (m, t) to every vertex it contributes."""
        if depth > 24:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            return
        a, b, c, d, e, f, g, h, i = m
        tx, ty, tz = t
        for line in lines:
            line = line.strip()
            if not line or line[0] not in "1234":
                continue
            kind = line[0]
            if kind == "1":
                try:
                    p = line.split()
                    col = int(p[1])
                    sx, sy, sz = float(p[2]), float(p[3]), float(p[4])
                    sm = [float(x) for x in p[5:14]]
                    name = " ".join(p[14:])
                except (IndexError, ValueError):
                    continue
                sub = self.path_of(name)
                if sub is None:
                    continue
                subcol = colour if col == 16 else col
                if subcol == 24:
                    subcol = colour
                nt = (a * sx + b * sy + c * sz + tx,
                      d * sx + e * sy + f * sz + ty,
                      g * sx + h * sy + i * sz + tz)
                sa, sb, sc, sd, se, sf, sg, sh, si = sm
                nm = [a * sa + b * sd + c * sg,
                      a * sb + b * se + c * sh,
                      a * sc + b * sf + c * si,
                      d * sa + e * sd + f * sg,
                      d * sb + e * se + f * sh,
                      d * sc + e * sf + f * si,
                      g * sa + h * sd + i * sg,
                      g * sb + h * se + i * sh,
                      g * sc + h * sf + i * si]
                self._walk(sub, subcol, out, depth + 1, nt, nm)
            elif kind in "34":
                try:
                    p = line.split()
                    col = int(p[1])
                    vals = [float(x) for x in p[2:]]
                except (IndexError, ValueError):
                    continue
                if col == 16:
                    col = colour
                if col == 24:
                    continue
                verts = []
                for k in range(0, len(vals) - 2, 3):
                    lx, ly, lz = vals[k], vals[k + 1], vals[k + 2]
                    verts.append((a * lx + b * ly + c * lz + tx,
                                  d * lx + e * ly + f * lz + ty,
                                  g * lx + h * ly + i * lz + tz))
                if len(verts) >= 3:
                    out.append((col, verts))


def footprint(bbox):
    """(width_studs, depth_studs, height_plates) for an axis-aligned part."""
    minx, miny, minz, maxx, maxy, maxz = bbox
    return ((maxx - minx) / LDU_STUD, (maxz - minz) / LDU_STUD,
            (maxy - miny) / LDU_PLATE)
