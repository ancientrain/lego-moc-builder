"""Stud / underside connection graph, including side studs (SNOT).

A connection is a positive stud of one part whose base lies on the underside
socket face of another part, with opposing normals.  LDraw gives us the stud
positions and directions directly (``Library.studs``), so this works for top
studs and side studs alike without a hand-written table.
"""
from __future__ import annotations

from model import Model, Part


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def stud_fits(pos, normal, sock, tol=0.6):
    """True when a stud base at *pos* plugs into the socket face *sock*."""
    n = sock["normal"]
    if _dot(normal, n) > -0.999:
        return False
    cx, cy, cz = sock["centre"]
    d = (pos[0] - cx, pos[1] - cy, pos[2] - cz)
    if abs(_dot(d, n)) > tol:
        return False
    u, v = sock["u"], sock["v"]
    return (abs(_dot(d, u)) <= sock["hu"] + tol
            and abs(_dot(d, v)) <= sock["hv"] + tol)


def connection_graph(model: Model):
    """Map part -> set of parts it supports (its studs enter their sockets)."""
    graph: dict[Part, set[Part]] = {}
    sockets = {}
    for b in model.parts:
        if b.overlap:
            continue
        sockets[b] = model.socket(b)
    for a in model.parts:
        if a.overlap:
            continue
        studs = model.world_studs(a)
        if not studs:
            continue
        for pos, normal in studs:
            for b, sock in sockets.items():
                if b is a:
                    continue
                bb = b.aabb
                if not (bb[0] - 1 <= pos[0] <= bb[3] + 1
                        and bb[1] - 1 <= pos[1] <= bb[4] + 1
                        and bb[2] - 1 <= pos[2] <= bb[5] + 1):
                    continue
                if stud_fits(pos, normal, sock):
                    graph.setdefault(a, set()).add(b)
    return graph


def connection_count(graph):
    return sum(len(v) for v in graph.values())


def incoming(graph, part):
    """Parts that hold *part* by a stud entering its underside."""
    return [a for a, targets in graph.items() if part in targets and a is not part]


def connected_parts(graph):
    out = set()
    for a, targets in graph.items():
        out.add(a)
        out.update(targets)
    return out
