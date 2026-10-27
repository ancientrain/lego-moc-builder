"""Integer 90-degree orientations for LDraw parts.

LDraw matrices are stored row-major as nine integers::

    x' = a*x + b*y + c*z + tx
    y' = d*x + e*y + f*z + ty
    z' = g*x + h*y + i*z + tz

Only proper rotations (det = +1) built from multiples of 90 degrees are used, so
every rotated part still has an axis-aligned bounding box in LDU.  That keeps the
collision and connection checks exact instead of approximate.
"""
from __future__ import annotations

IDENTITY = (1, 0, 0, 0, 1, 0, 0, 0, 1)

# Rotation about the world X axis: +Y -> +Z (a SNOT part facing +Z).
RX = {
    0: IDENTITY,
    90: (1, 0, 0, 0, 0, -1, 0, 1, 0),
    180: (1, 0, 0, 0, -1, 0, 0, 0, -1),
    270: (1, 0, 0, 0, 0, 1, 0, -1, 0),
}
# Rotation about the world Y axis: the legacy yaw used by the first version.
RY = {
    0: IDENTITY,
    90: (0, 0, 1, 0, 1, 0, -1, 0, 0),
    180: (-1, 0, 0, 0, 1, 0, 0, 0, -1),
    270: (0, 0, -1, 0, 1, 0, 1, 0, 0),
}
# Rotation about the world Z axis: +X -> +Y.
RZ = {
    0: IDENTITY,
    90: (0, -1, 0, 1, 0, 0, 0, 0, 1),
    180: (-1, 0, 0, 0, -1, 0, 0, 0, 1),
    270: (0, 1, 0, -1, 0, 0, 0, 0, 1),
}


def matmul(a, b):
    """Multiply two 3x3 row-major integer matrices."""
    return tuple(
        sum(a[3 * i + k] * b[3 * k + j] for k in range(3))
        for i in range(3)
        for j in range(3)
    )


def apply(m, v):
    """Apply a row-major 3x3 matrix to a 3-vector."""
    return (
        m[0] * v[0] + m[1] * v[1] + m[2] * v[2],
        m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
        m[6] * v[0] + m[7] * v[1] + m[8] * v[2],
    )


def det(m):
    return (
        m[0] * (m[4] * m[8] - m[5] * m[7])
        - m[1] * (m[3] * m[8] - m[5] * m[6])
        + m[2] * (m[3] * m[7] - m[4] * m[6])
    )


def transpose(m):
    return (m[0], m[3], m[6], m[1], m[4], m[7], m[2], m[5], m[8])


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _clean(v):
    """Round a float vector that should contain only 0 / +1 / -1."""
    return tuple(int(round(x, 6)) for x in v)


def normalize_rot(rot):
    """Accept the legacy yaw (int), a named orientation, or (rx, ry, rz).

    ``rot=(90, 0, 0)`` rotates the part about X, so its studs face +Z.
    ``rot=(0, 90, 0)`` is the legacy yaw.
    """
    if isinstance(rot, int):
        return RY[rot % 360]
    if isinstance(rot, str):
        return _named(rot)
    if isinstance(rot, (tuple, list)) and len(rot) == 3:
        rx, ry, rz = (int(v) % 360 for v in rot)
        if rx % 90 or ry % 90 or rz % 90:
            raise ValueError("orientation angles must be multiples of 90")
        return matmul(RX[rx], matmul(RY[ry], RZ[rz]))
    if isinstance(rot, (tuple, list)) and len(rot) == 9:
        m = tuple(int(v) for v in rot)
        if det(m) != 1:
            raise ValueError("orientation matrix must have det=+1")
        return m
    raise ValueError(f"unsupported rot: {rot!r}")


def orientation_for_stud(normal, spin=0):
    """Return a rotation whose local +Y socket faces *normal*.

    ``normal`` is the outward direction of the stud this part will sit on, so the
    part's top surface (local -Y) points along ``normal``.  ``spin`` is a number
    of 90-degree turns around that stud.
    """
    n = _clean(normal)
    if n not in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        raise ValueError(f"stud normal must be an axis: {normal!r}")
    u = (-n[0], -n[1], -n[2])          # local +Y in world space
    if abs(u[0]) < 0.9:
        t = (1, 0, 0)
    elif abs(u[2]) < 0.9:
        t = (0, 0, 1)
    else:
        t = (0, 0, 1)
    w = cross(t, u)
    turns = (int(spin) // 90) % 4
    for _ in range(turns):
        t, w = w, (-t[0], -t[1], -t[2])
    # Columns are (t, u, w); rows of the matrix are the transposed columns.
    m = (t[0], u[0], w[0],
         t[1], u[1], w[1],
         t[2], u[2], w[2])
    m = _clean(m)
    assert det(m) == 1, m
    return m


def _named(name):
    key = name.lower().replace("_", "").replace("-", "").replace(" ", "")
    if key in ("up", "identity", "yaw0"):
        return IDENTITY
    if key in ("yaw90", "rot90"):
        return RY[90]
    if key in ("yaw180", "rot180"):
        return RY[180]
    if key in ("yaw270", "rot270"):
        return RY[270]
    axes = {
        "x+": (1, 0, 0), "x-": (-1, 0, 0),
        "y+": (0, 1, 0), "y-": (0, -1, 0),
        "z+": (0, 0, 1), "z-": (0, 0, -1),
    }
    for prefix in ("snot", "face", "stud"):
        if key.startswith(prefix):
            rest = key[len(prefix):]
            if rest in axes:
                # "snot+z" means the part's studs face +Z.
                return orientation_for_stud(axes[rest])
    raise ValueError(f"unknown orientation name: {name!r}")


def all_orientations():
    """The 24 proper axis-aligned rotations, as a tuple of matrices."""
    seen = []
    for rx in (0, 90, 180, 270):
        for ry in (0, 90, 180, 270):
            for rz in (0, 90, 180, 270):
                m = matmul(RX[rx], matmul(RY[ry], RZ[rz]))
                if m not in seen:
                    seen.append(m)
    if len(seen) != 24:
        raise AssertionError(f"expected 24 orientations, got {len(seen)}")
    return tuple(seen)
