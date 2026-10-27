"""Structural checks: support, floating parts, connectivity to the ground."""
from __future__ import annotations

from model import Model


def support_map(model: Model):
    """For each part: (supported_cells, total_cells)."""
    out = {}
    for p in model.parts:
        if p.level == 0:
            out[p] = (len(p.cells), len(p.cells))
            continue
        n = 0
        for (cx, cz) in p.cells:
            if (cx, cz, p.level - 1) in model.occ:
                n += 1
        out[p] = (n, len(p.cells))
    return out


def graph(model: Model):
    """Adjacency: A -> B when B sits directly under A."""
    below = {}
    for p in model.parts:
        for (cx, cz) in p.cells:
            q = model.occ.get((cx, cz, p.level - 1))
            if q is not None and q is not p:
                below.setdefault(p, set()).add(q)
    return below


def reachable(model: Model):
    below = graph(model)
    roots = [p for p in model.parts if p.level == 0]
    seen = set(roots)
    stack = list(roots)
    while stack:
        cur = stack.pop()
        for nxt, parents in below.items():
            if cur in parents and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def report(model: Model):
    sup = support_map(model)
    floating = [p for p, (n, _t) in sup.items() if n == 0]
    weak = [p for p, (n, t) in sup.items() if p.level > 0 and 0 < n < t * 0.25]
    seen = reachable(model)
    orphans = [p for p in model.parts if p not in seen]
    codes = {}
    for p in model.parts:
        codes[p.code] = codes.get(p.code, 0) + 1
    return {
        "parts": len(model.parts),
        "unique_codes": len(codes),
        "colours": len({p.colour for p in model.parts}),
        "top_level": model.top_surface(),
        "floating": floating,
        "weak_support": weak,
        "orphans": orphans,
        "bom": codes,
    }


def print_report(model: Model):
    r = report(model)
    print(f"parts={r['parts']} unique={r['unique_codes']} colours={r['colours']} "
          f"top_level={r['top_level']}")
    print(f"floating={len(r['floating'])} weak={len(r['weak_support'])} "
          f"orphans={len(r['orphans'])}")
    for p in r["floating"][:8]:
        print(f"  FLOATING {p.code} at ({p.x},{p.z}) L{p.level}")
    for p in r["orphans"][:8]:
        print(f"  ORPHAN   {p.code} at ({p.x},{p.z}) L{p.level}")
    for code, n in sorted(r["bom"].items(), key=lambda kv: -kv[1]):
        print(f"  {code:<8} x{n}")
    return r
