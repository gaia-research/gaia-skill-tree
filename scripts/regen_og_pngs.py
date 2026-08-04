#!/usr/bin/env python3
"""Batch-convert all per-skill OG SVGs to PNG using cairosvg (sequential).

Run from the repo root:
    pip install cairosvg
    python scripts/regen_og_pngs.py

Skips social-preview.svg (different 1280x640 dimensions).
"""
import base64
import sys
from io import BytesIO
from pathlib import Path

OG_W = 1200
OG_H = 630
SKIP = {"social-preview.svg"}
DOCS_DIR = Path("docs")


def _asset_data_uri(path: Path) -> str:
    """Return a raster-safe data URI for an SVG image asset.

    The committed OG SVGs use root-relative `/assets/...webp` links.  When a
    batch converter runs against local files those links are not guaranteed to
    resolve, and some Cairo builds cannot decode WebP even after inlining.  A
    PNG data URI is the most portable raster input; fall back to typed WebP if
    Pillow is unavailable.
    """
    try:
        from PIL import Image

        with Image.open(path) as img:
            buf = BytesIO()
            img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        mime = "image/webp" if path.suffix.lower() == ".webp" else "application/octet-stream"
        return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def inline_raster_assets(svg_content: str, docs_dir: Path = DOCS_DIR) -> str:
    """Inline root-relative docs assets before rasterizing an OG SVG."""
    asset_dir = docs_dir / "assets" / "ascension-overdrive"
    for path in sorted(asset_dir.glob("aov4-*-hero.webp")):
        href = "/" + path.relative_to(docs_dir).as_posix()
        if href in svg_content:
            svg_content = svg_content.replace(href, _asset_data_uri(path))
    return svg_content


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
            raster_svg = inline_raster_assets(svg_path.read_text(encoding="utf-8"))
            cairosvg.svg2png(
                bytestring=raster_svg.encode("utf-8"),
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
