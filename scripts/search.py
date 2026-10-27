"""Search the LDraw parts index.

Usage:
    python3 search.py "^Slope" --limit 40
    python3 search.py "Window" --exclude with Pattern Sticker --limit 20
"""
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "..", "cache", "parts.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--exclude", nargs="*", default=["with", "Pattern", "Sticker", "Duplo", "Print"])
    ap.add_argument("--include", action="store_true", help="match pattern against code too")
    args = ap.parse_args()

    parts = json.load(open(PARTS, encoding="utf-8"))
    norm = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
    rx = re.compile(norm(args.pattern), re.I)
    hits = []
    for p in parts:
        hay = norm(p["title"] + (" " + p["code"] if args.include else ""))
        if not rx.search(hay):
            continue
        if any(e.lower() in p["title"].lower() for e in args.exclude):
            continue
        hits.append(p)

    print(f"{len(hits)} hits for {args.pattern!r}")
    for p in hits[: args.limit]:
        print(f"  {p['code']:<12} {p['title']}")


if __name__ == "__main__":
    main()
