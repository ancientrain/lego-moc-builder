"""Print bbox and polygon count for one or more part codes."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from paths import find_ldraw  # noqa: E402
from ldrawlib import Library, footprint  # noqa: E402

ROOT = os.path.expanduser(find_ldraw())


def main(codes):
    lib = Library(ROOT)
    for code in codes:
        if not lib.exists(code):
            print(f"{code}: MISSING")
            continue
        polys, bbox = lib.geometry(code)
        w, d, h = footprint(bbox)
        print(f"{code:<10} W{w:g} D{d:g} H{h:g} polys={len(polys):<5} "
              f"bbox=[{', '.join(f'{v:g}' for v in bbox)}]")


if __name__ == "__main__":
    main(sys.argv[1:])
