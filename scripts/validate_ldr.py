"""Validate an exported .ldr: part files exist, colours exist, placements parse."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))
from paths import find_ldraw  # noqa: E402
from ldrawlib import Library  # noqa: E402

LDRAW_ROOT = os.path.expanduser(find_ldraw())
COLOURS = json.load(open(os.path.join(ROOT, "cache", "colors.json"), encoding="utf-8"))


def main(path):
    lib = Library(LDRAW_ROOT)
    n_parts = 0
    n_steps = 0
    missing_parts = set()
    bad_colours = set()
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith("0 STEP"):
                n_steps += 1
                continue
            if not line.startswith("1 "):
                continue
            tok = line.split()
            try:
                colour = int(tok[1])
                nums = [float(t) for t in tok[2:14]]
                name = " ".join(tok[14:])
            except (IndexError, ValueError):
                print(f"  line {lineno}: BAD SYNTAX -> {line[:60]}")
                continue
            if len(nums) != 12:
                print(f"  line {lineno}: expected 12 numbers, got {len(nums)}")
            if str(colour) not in COLOURS:
                bad_colours.add(colour)
            if not lib.exists(name):
                missing_parts.add(name)
            n_parts += 1

    print(f"file      : {path}")
    print(f"placements: {n_parts}")
    print(f"steps     : {n_steps}")
    print(f"missing   : {sorted(missing_parts) or 'none'}")
    print(f"bad colour: {sorted(bad_colours) or 'none'}")
    return 0 if not missing_parts and not bad_colours else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
