"""Minimal LDraw library reader: resolve part files, flatten geometry, compute bounds.

Nothing here knows about colours beyond "16 means inherit"; rendering decides the RGB.
"""
from __future__ import annotations

import os

LDU_STUD = 20.0
LDU_BRICK = 24.0
LDU_PLATE = 8.0

IDENTITY = (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)

# Primitive files that represent a positive clutch stud.  stud3 / stud4 are
# underside tubes (negative sockets), so they are deliberately not listed.
STUD_NAMES = frozenset({"stud.dat", "stud2.dat", "stud2a.dat"})


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
        self._body_cache: dict[str, tuple] = {}
        self._stud_cache: dict[str, tuple] = {}

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

    # ---------- body / connections ----------
    def body_bbox(self, code: str):
        """Bounding box of the part *without* protruding studs.

        The body box is the right box for collision, placement and socket faces.
        Studs stick 4 LDU out of it, so using the plain geometry bbox would make
        two correctly connected parts look like they overlap.
        """
        key = os.path.basename(code).lower()
        if key in self._body_cache:
            return self._body_cache[key]
        path = self.path_of(code)
        if path is None:
            raise KeyError(f"part not found: {code}")
        polys: list = []
        self._walk(path, 16, polys, 0, (0.0, 0.0, 0.0),
                   [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
                   skip_studs=True)
        if not polys:
            bb = self.geometry(code)[1]
        else:
            xs = [v[0] for _c, vs in polys for v in vs]
            ys = [v[1] for _c, vs in polys for v in vs]
            zs = [v[2] for _c, vs in polys for v in vs]
            bb = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
        self._body_cache[key] = bb
        return bb

    def studs(self, code: str):
        """Connection studs of a part, in part-local LDraw coordinates.

        Returns ``((x, y, z), (nx, ny, nz))`` where the point is the base of the
        stud (the plane a mating part's underside sits on) and the normal points
        out of the part.  Both top studs and side studs are included; underside
        tubes are not.
        """
        key = os.path.basename(code).lower()
        if key in self._stud_cache:
            return self._stud_cache[key]
        path = self.path_of(code)
        if path is None:
            raise KeyError(f"part not found: {code}")
        out: list = []
        self._walk_studs(path, [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
                         (0.0, 0.0, 0.0), out, 0)
        seen = set()
        unique = []
        for pos, n in out:
            marker = (tuple(round(v, 1) for v in pos),
                      tuple(round(v, 3) for v in n))
            if marker in seen:
                continue
            seen.add(marker)
            unique.append((pos, n))
        unique.sort(key=lambda item: (-item[0][1], item[0][2], item[0][0]))
        result = tuple(unique)
        self._stud_cache[key] = result
        return result

    def _walk_studs(self, path, m, t, out, depth):
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
            if not line or line[0] != "1":
                continue
            p = line.split()
            if len(p) < 15:
                continue
            try:
                sx, sy, sz = float(p[2]), float(p[3]), float(p[4])
                sm = [float(x) for x in p[5:14]]
                name = " ".join(p[14:])
            except (IndexError, ValueError):
                continue
            base = os.path.basename(name.replace("\\", "/")).lower()
            nt = (a * sx + b * sy + c * sz + tx,
                  d * sx + e * sy + f * sz + ty,
                  g * sx + h * sy + i * sz + tz)
            if base in STUD_NAMES:
                nx = -(a * sm[1] + b * sm[4] + c * sm[7])
                ny = -(d * sm[1] + e * sm[4] + f * sm[7])
                nz = -(g * sm[1] + h * sm[4] + i * sm[7])
                out.append((nt, (nx, ny, nz)))
                continue
            sub = self.path_of(name)
            if sub is None:
                continue
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
            self._walk_studs(sub, nm, nt, out, depth + 1)

    def _walk(self, path, colour, out, depth, t, m, skip_studs=False):
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
                if skip_studs:
                    base = os.path.basename(name.replace("\\", "/")).lower()
                    if base.startswith(("stud", "stug")):
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
                self._walk(sub, subcol, out, depth + 1, nt, nm, skip_studs)
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
