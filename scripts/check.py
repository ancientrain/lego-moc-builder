"""Structural checks: support, floating parts, connectivity to the ground.

Two graphs are combined:

* the classic stud-grid graph for upright parts (a part rests on the cells below);
* the real stud/socket graph for everything else, which is what makes sideways
  (SNOT) parts valid instead of "floating".
"""
from __future__ import annotations

from connections import connection_graph, incoming
from model import Model


def support_map(model: Model):
    """For each upright part: (supported_cells, total_cells)."""
    out = {}
    for p in model.parts:
        if p.snot or p.overlap:
            continue
        if p.level == 0:
            out[p] = (len(p.cells), len(p.cells))
            continue
        n = 0
        for (cx, cz) in p.cells:
            if (cx, cz, int(p.level) - 1) in model.occ:
                n += 1
        out[p] = (n, len(p.cells))
    return out


def graph(model: Model):
    """Adjacency for upright parts: A -> B when B sits directly under A."""
    below = {}
    for p in model.parts:
        if p.snot or p.overlap:
            continue
        for (cx, cz) in p.cells:
            q = model.occ.get((cx, cz, int(p.level) - 1))
            if q is not None and q is not p:
                below.setdefault(p, set()).add(q)
    return below


def _children(model: Model):
    children = {}
    for p, parents in graph(model).items():
        for q in parents:
            children.setdefault(q, set()).add(p)
    conn = connection_graph(model)
    for a, targets in conn.items():
        children.setdefault(a, set()).update(targets)
    return children, conn


def reachable(model: Model):
    children, _conn = _children(model)
    roots = [p for p in model.parts
             if not p.snot and not p.overlap and p.level == 0]
    seen = set(roots)
    stack = list(roots)
    while stack:
        cur = stack.pop()
        for nxt in children.get(cur, ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def report(model: Model):
    sup = support_map(model)
    floating_upright = [p for p, (n, _t) in sup.items() if n == 0]
    weak = [p for p, (n, t) in sup.items() if p.level > 0 and 0 < n < t * 0.25]

    conn = connection_graph(model)
    snot_parts = [p for p in model.parts if p.snot and not p.overlap]
    snot_unsupported = [p for p in snot_parts if not incoming(conn, p)]

    seen = reachable(model)
    orphans = [p for p in model.parts
               if not p.overlap and p not in seen]

    codes = {}
    for p in model.parts:
        codes[p.code] = codes.get(p.code, 0) + 1
    return {
        "parts": len(model.parts),
        "unique_codes": len(codes),
        "colours": len({p.colour for p in model.parts}),
        "top_level": model.top_surface(),
        "floating": floating_upright + snot_unsupported,
        "floating_upright": floating_upright,
        "snot_unsupported": snot_unsupported,
        "snot_parts": len(snot_parts),
        "connections": sum(len(v) for v in conn.values()),
        "weak_support": weak,
        "orphans": orphans,
        "bom": codes,
    }


def print_report(model: Model):
    r = report(model)
    print(f"parts={r['parts']} unique={r['unique_codes']} colours={r['colours']} "
          f"top_level={r['top_level']}")
    print(f"floating={len(r['floating'])} weak={len(r['weak_support'])} "
          f"orphans={len(r['orphans'])} snot={r['snot_parts']} "
          f"links={r['connections']}")
    for p in r["floating"][:8]:
        print(f"  FLOATING {p.code} at ({p.x:g},{p.z:g}) L{p.level:g}")
    for p in r["orphans"][:8]:
        print(f"  ORPHAN   {p.code} at ({p.x:g},{p.z:g}) L{p.level:g}")
    for code, n in sorted(r["bom"].items(), key=lambda kv: -kv[1]):
        print(f"  {code:<8} x{n}")
    return r
