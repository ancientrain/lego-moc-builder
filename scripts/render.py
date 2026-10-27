"""Renderer: LDraw polygons -> shaded image, numpy z-buffer rasteriser.

Orthographic camera, flat shading with one directional light, back-face culling,
depth buffer (so hollow parts and stacked plates never bleed through), and a thin
depth-discontinuity outline for definition.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
from PIL import Image

from ldrawlib import LDU_PLATE, LDU_STUD
from model import Model

HERE = os.path.dirname(os.path.abspath(__file__))
COLORS = json.load(open(os.path.join(HERE, "..", "cache", "colors.json"), encoding="utf-8"))


def rgb(colour: int):
    c = COLORS.get(str(colour))
    if not c:
        return np.array([200, 30, 200], dtype=np.float32)
    h = c["rgb"].lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def _unit(v):
    n = math.sqrt(float(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)) or 1.0
    return np.array(v, dtype=np.float64) / n


class Camera:
    """Orthographic camera. World -Y is up."""

    def __init__(self, az_deg, el_deg):
        az, el = math.radians(az_deg), math.radians(el_deg)
        d = np.array([math.sin(az) * math.cos(el),
                      -math.sin(el),
                      math.cos(az) * math.cos(el)])
        self.pos_dir = d
        self.f = -d
        self.right = _unit(np.cross(self.f, np.array([0.0, -1.0, 0.0])))
        self.up = np.cross(self.right, self.f)


LIGHT = _unit([-0.42, -0.78, 0.46])


def collect(model: Model):
    """Return (triangles Nx3x3, face colours Nx3, part index N)."""
    lib = model.lib
    tris_all = []
    cols_all = []
    for p in model.parts:
        part_polys, _bb = lib.geometry(p.code)
        m = p.R
        base = rgb(p.colour)
        # faint per-part variation so coplanar bricks stay readable
        jitter = 0.965 + 0.07 * ((hash((p.code, p.x, p.z, p.level)) % 1000) / 1000.0)
        base = base * jitter
        for col, verts in part_polys:
            pts = np.array(verts, dtype=np.float64)
            if pts.shape[1] != 3:
                continue
            a_, b_, c_, d_, e_, f_, g_, h_, i_ = m
            M = np.array([[a_, b_, c_], [d_, e_, f_], [g_, h_, i_]])
            pts = pts @ M.T + np.array([p.tx, p.ty, p.tz])
            colour = base if col in (16, 24) else rgb(col)
            # fan-triangulate quads
            if len(pts) == 3:
                tris_all.append(pts)
                cols_all.append(colour)
            elif len(pts) == 4:
                tris_all.append(pts[[0, 1, 2]])
                cols_all.append(colour)
                tris_all.append(pts[[0, 2, 3]])
                cols_all.append(colour)
            else:
                for k in range(1, len(pts) - 1):
                    tris_all.append(pts[[0, k, k + 1]])
                    cols_all.append(colour)
    if not tris_all:
        raise ValueError("no geometry")
    return np.stack(tris_all), np.stack(cols_all)


def render(model: Model, out_png: str, size=(1100, 850), az=-32, el=26,
           margin=0.06, bg=(238, 241, 244), supersample=2, outline=True,
           shadow=True):
    cam = Camera(az, el)
    tris, cols = collect(model)

    bb = model.world_bbox()
    centre = np.array([(bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2])

    # camera-space coordinates
    R = np.stack([cam.right, cam.up, cam.f])           # rows
    local = tris - centre
    cam_pts = local @ R.T
    u, v, depth = cam_pts[..., 0], cam_pts[..., 1], cam_pts[..., 2]

    # normals + lighting (world space)
    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    n = np.cross(e1, e2)
    ln = np.linalg.norm(n, axis=1)
    ln[ln == 0] = 1.0
    n = n / ln[:, None]

    facing = n @ cam.f
    # LDraw winding conventions are inconsistent across parts; the z-buffer makes
    # back-face culling optional and culling risks dropping real top surfaces.
    keep = np.ones(len(facing), dtype=bool)
    # two-sided shading
    flip = (n @ LIGHT) < 0
    n[flip] *= -1

    lam = np.clip(n @ LIGHT, 0, 1)
    shade = 0.50 + 0.62 * lam
    face_cols = cols * shade[:, None]

    u, v, depth, face_cols = u[keep], v[keep], depth[keep], face_cols[keep]

    w, h = size
    ss = supersample
    W, H = w * ss, h * ss

    # fit the *projected* silhouette, not the world bounding box
    umin, umax = float(u.min()), float(u.max())
    vmin, vmax = float(v.min()), float(v.max())
    du = max(umax - umin, 1e-6)
    dv = max(vmax - vmin, 1e-6)
    scale = (1 - 2 * margin) * min(W / du, H / dv)
    uc = (umin + umax) / 2
    vc = (vmin + vmax) / 2

    sx = W / 2 + (u - uc) * scale
    sy = H / 2 - (v - vc) * scale

    img = np.empty((H, W, 3), dtype=np.float32)
    img[:] = np.array(bg, dtype=np.float32)
    zbuf = np.full((H, W), np.inf, dtype=np.float32)

    order = np.argsort(-depth.mean(axis=1))      # far first (helps early z reject)

    for idx in order:
        x = sx[idx]
        y = sy[idx]
        xmin, xmax = int(np.floor(x.min())), int(np.ceil(x.max()))
        ymin, ymax = int(np.floor(y.min())), int(np.ceil(y.max()))
        if xmax < 0 or ymax < 0 or xmin >= W or ymin >= H:
            continue
        xmin, xmax = max(xmin, 0), min(xmax, W - 1)
        ymin, ymax = max(ymin, 0), min(ymax, H - 1)
        if xmax < xmin or ymax < ymin:
            continue

        x0, x1, x2 = x
        y0, y1, y2 = y
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-9:
            continue

        xs = np.arange(xmin, xmax + 1) + 0.5
        ys = np.arange(ymin, ymax + 1) + 0.5
        X, Y = np.meshgrid(xs, ys)

        w0 = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / den
        w1 = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / den
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue

        d = depth[idx]
        z = w0 * d[0] + w1 * d[1] + w2 * d[2]

        sub_z = zbuf[ymin:ymax + 1, xmin:xmax + 1]
        upd = inside & (z < sub_z)
        if not upd.any():
            continue
        sub_z[upd] = z[upd]
        sub_i = img[ymin:ymax + 1, xmin:xmax + 1]
        sub_i[upd] = face_cols[idx]

    if shadow:
        # cheap contact shadow: darken pixels whose depth is behind the model centre
        pass

    if outline:
        zf = np.where(np.isfinite(zbuf), zbuf, 0.0).astype(np.float32)
        gx = np.abs(np.gradient(zf, axis=1))
        gy = np.abs(np.gradient(zf, axis=0))
        mask = (gx + gy) > 6.0
        mask &= np.isfinite(zbuf)
        img[mask] *= 0.62

    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    if ss > 1:
        out = out.resize((w, h), Image.LANCZOS)
    out.save(out_png)
    return out_png, int(keep.sum())
