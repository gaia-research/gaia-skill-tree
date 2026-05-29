#!/usr/bin/env python3
"""Batch-convert all per-skill OG SVGs to PNG using cairosvg (sequential).

Run from the repo root:
    pip install cairosvg
    python scripts/regen_og_pngs.py

Skips social-preview.svg (different 1280x640 dimensions).
"""
import sys
from pathlib import Path

OG_W = 1200
OG_H = 630
SKIP = {"social-preview.svg"}


def main() -> None:
    try:
        import cairosvg
    except ImportError:
        print("ERROR: cairosvg not installed. Run: pip install cairosvg", file=sys.stderr)
        sys.exit(1)

    og_dir = Path("docs/og")
    if not og_dir.exists():
        print(f"ERROR: {og_dir} not found. Run from repo root.", file=sys.stderr)
        sys.exit(1)

    svgs = sorted(p for p in og_dir.rglob("*.svg") if p.name not in SKIP)
    if not svgs:
        print("No SVGs found in docs/og/")
        return

    png_count = 0
    errors = []
    for svg_path in svgs:
        png_path = svg_path.with_suffix(".png")
        try:
            cairosvg.svg2png(
                url=str(svg_path.resolve()),
                write_to=str(png_path),
                output_width=OG_W,
                output_height=OG_H,
            )
            print(f"  PNG: {png_path.relative_to(og_dir.parent)}")
            png_count += 1
        except Exception as e:
            errors.append((svg_path, e))
            print(f"  ERR: {svg_path} — {e}", file=sys.stderr)

    print(f"\nGenerated {png_count}/{len(svgs)} PNG(s).")
    if errors:
        print(f"{len(errors)} error(s) — see above.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
