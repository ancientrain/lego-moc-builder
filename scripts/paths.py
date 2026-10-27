"""Locate a local LDraw parts library.

The library is a folder containing `parts/` (and usually `p/` and LDConfig.ldr).
Resolution order: $LDRAW_DIR, BrickLink Studio's bundled library, the Ubuntu
`ldraw-parts` package, then a few conventional paths. Windows paths are mapped
onto /mnt/<drive>/... when running inside WSL.
"""
from __future__ import annotations

import os
import re

STUDIO_WIN = r"C:\Program Files\Studio 2.0\ldraw"


def _as_local(path: str) -> str:
    """Translate C:\\... to /mnt/c/... when the process is not on Windows."""
    if os.name == "nt" or not re.match(r"^[A-Za-z]:[\\/]", path):
        return path
    drive = path[0].lower()
    rest = path[2:].replace("\\", "/").lstrip("/")
    return f"/mnt/{drive}/{rest}"


def _candidates():
    env = os.environ.get("LDRAW_DIR", "")
    if env:
        yield _as_local(env)
    yield _as_local(STUDIO_WIN)
    yield os.path.expanduser("~/lego/lib/usr/share/ldraw")
    yield "/usr/share/ldraw"
    yield "/usr/local/share/ldraw"
    yield os.path.expanduser("~/ldraw")


def find_ldraw() -> str:
    tried = []
    for cand in _candidates():
        tried.append(cand)
        if cand and os.path.isdir(os.path.join(cand, "parts")):
            return cand
    raise SystemExit(
        "No LDraw parts library found. Tried:\n  " + "\n  ".join(tried) + "\n\n"
        "Install one and point LDRAW_DIR at it:\n"
        "  BrickLink Studio : C:\\Program Files\\Studio 2.0\\ldraw\n"
        "  Ubuntu/Debian    : sudo apt install ldraw-parts  (/usr/share/ldraw)\n"
        "  official archive : https://library.ldraw.org  (complete.zip)"
    )


def cache_dir() -> str:
    """Where generated indexes live (parts.json / colors.json)."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
