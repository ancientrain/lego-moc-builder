"""Build a searchable index of the LDraw parts library and colour table.

Usage:
    python3 index_parts.py [--ldraw ROOT] [--out DIR]
"""
import json
import os

from paths import find_ldraw
import re
import sys

DEFAULT_ROOT = os.path.expanduser(find_ldraw())

ORG_RE = re.compile(r"^0\s+!LDRAW_ORG\s+(\S+)")
COLOR_RE = re.compile(
    r"^0\s+!COLOUR\s+(?P<name>.+?)\s+CODE\s+(?P<code>\d+)\s+VALUE\s+#(?P<rgb>[0-9A-Fa-f]{6})"
)


def read_header(path):
    title = None
    org = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for _ in range(25):
                line = fh.readline()
                if not line:
                    break
                line = line.rstrip("\r\n")
                if title is None and line.startswith("0 "):
                    title = line[2:].strip()
                m = ORG_RE.match(line)
                if m:
                    org = m.group(1)
                    break
    except OSError:
        return None, None
    return title, org


def index_parts(root):
    """Index both Studio's official (`parts`) and unofficial catalogues."""
    out = []
    seen = set()
    for sub in ("parts", "UnOfficial/parts"):
        parts_dir = os.path.join(root, sub)
        if not os.path.isdir(parts_dir):
            continue
        for name in sorted(os.listdir(parts_dir)):
            if not name.lower().endswith(".dat"):
                continue
            code = name[:-4]
            if code.lower() in seen:
                continue
            title, org = read_header(os.path.join(parts_dir, name))
            if not title or not org:
                continue
            if "Part" not in org and "Shortcut" not in org:
                continue
            if title.startswith("~"):
                continue
            seen.add(code.lower())
            out.append({"file": name, "code": code, "title": title, "org": org})
    return out


def index_colors(root):
    colors = {}
    path = os.path.join(root, "LDConfig.ldr")
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = COLOR_RE.match(line.strip())
            if m:
                colors[int(m.group("code"))] = {
                    "name": m.group("name").strip(),
                    "rgb": "#" + m.group("rgb").upper(),
                }
    return colors


def main():
    root = DEFAULT_ROOT
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--ldraw":
            root = args[i + 1]
        elif a == "--out":
            out_dir = args[i + 1]
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    parts = index_parts(root)
    colors = index_colors(root)
    with open(os.path.join(out_dir, "parts.json"), "w", encoding="utf-8") as fh:
        json.dump(parts, fh, ensure_ascii=False)
    with open(os.path.join(out_dir, "colors.json"), "w", encoding="utf-8") as fh:
        json.dump({str(k): v for k, v in colors.items()}, fh, ensure_ascii=False)

    print(f"root      : {root}")
    print(f"parts     : {len(parts)}")
    print(f"colours   : {len(colors)}")
    print(f"index dir : {out_dir}")
    for kw in ("window", "door", "slope 45", "roof"):
        hits = [p for p in parts if kw in p["title"].lower()]
        print(f"\n--- '{kw}' : {len(hits)} hits (first 12)")
        for p in hits[:12]:
            print(f"  {p['code']:<12} {p['title']}")


if __name__ == "__main__":
    main()
