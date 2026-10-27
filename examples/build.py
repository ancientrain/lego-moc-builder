#!/usr/bin/env python3
"""Build an example MOC end to end: model -> checks -> .ldr + BOM + previews.

Usage:
    python3 examples/build.py cottage
    python3 examples/build.py house --out out/house
    python3 examples/build.py villa --no-render
"""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PKG, "scripts"))
sys.path.insert(0, HERE)

import check  # noqa: E402
import render  # noqa: E402
from model import Collision  # noqa: E402

DESIGNS = ("cottage", "house", "villa")


def bom_rows(model):
    counts = {}
    for p in model.parts:
        counts[(p.code, p.colour)] = counts.get((p.code, p.colour), 0) + 1
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design", choices=DESIGNS)
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    out = os.path.abspath(args.out or os.path.join(PKG, "out", args.design))
    os.makedirs(out, exist_ok=True)

    t0 = time.time()
    try:
        model = importlib.import_module(args.design).build()
    except Collision as exc:
        print("COLLISION:", exc)
        return 1
    print(f"built {len(model.parts)} parts in {time.time() - t0:.1f}s")
    check.print_report(model)

    ldr = os.path.join(out, f"{args.design}.ldr")
    with open(ldr, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(model.to_ldr(f"{args.design} (DeepSeek MOC skill)"))
    print("wrote", ldr)

    colours = json.load(open(os.path.join(PKG, "cache", "colors.json"), encoding="utf-8"))
    try:
        parts_index = json.load(open(os.path.join(PKG, "cache", "parts.json"), encoding="utf-8"))
        names = {p["code"]: p["title"] for p in parts_index}
    except OSError:
        names = {}
    with open(os.path.join(out, "bom.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["part", "name", "ldraw_colour", "colour_name", "qty"])
        for (code, col), n in sorted(bom_rows(model).items(), key=lambda kv: -kv[1]):
            w.writerow([code, names.get(code, ""), col,
                        colours.get(str(col), {}).get("name", "?"), n])

    if not args.no_render:
        for name, kw in (("iso", dict(az=30, el=28)), ("front", dict(az=0, el=8))):
            path = os.path.join(out, f"preview-{name}.png")
            _, polys = render.render(model, path, size=(1100, 850), **kw)
            print(f"render {name}: {polys} polys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
