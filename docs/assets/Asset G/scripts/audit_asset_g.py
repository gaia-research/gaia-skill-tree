#!/usr/bin/env python3
"""Audit Asset G files for dimensions, alpha, and WebP budget."""
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image

def audit(path, max_kb):
    path = Path(path)
    with Image.open(path) as img:
        has_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info
        ok_budget = path.suffix.lower() != ".webp" or path.stat().st_size <= max_kb * 1024
        return {
            "file": str(path),
            "mode": img.mode,
            "size": f"{img.width}x{img.height}",
            "bytes": path.stat().st_size,
            "has_alpha": has_alpha,
            "webp_under_budget": ok_budget,
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--max-kb", type=int, default=120)
    args = parser.parse_args()
    for f in args.files:
        print(audit(f, args.max_kb))

if __name__ == "__main__":
    main()
