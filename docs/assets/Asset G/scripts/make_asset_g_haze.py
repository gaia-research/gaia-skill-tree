#!/usr/bin/env python3
"""Generate Asset G, a transparent warm-sepia parallax haze layer.

Usage:
  python scripts/make_asset_g_haze.py --out outputs --width 2000 --height 1200 --seed 975
"""
from __future__ import annotations
import argparse, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

def upsample_noise(width, height, grid_w, grid_h, seed):
    rng = np.random.default_rng(seed)
    small = (rng.random((grid_h, grid_w)) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(small, "L").resize((width, height), Image.Resampling.BICUBIC)).astype(np.float32) / 255.0

def generate_asset_g(width=2000, height=1200, seed=975, opacity=0.38):
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, width, dtype=np.float32)[None, :]

    n1 = upsample_noise(width, height, 34, 20, seed)
    n2 = upsample_noise(width, height, 74, 42, seed + 1)
    n3 = upsample_noise(width, height, 14, 9, seed + 2)

    bands = (
        np.exp(-((y - 0.22) ** 2) / (2 * 0.07 ** 2)) * 0.24 +
        np.exp(-((y - 0.49) ** 2) / (2 * 0.09 ** 2)) * 0.35 +
        np.exp(-((y - 0.76) ** 2) / (2 * 0.07 ** 2)) * 0.26
    )
    swirls = 0.5 + 0.5 * np.sin((x * 4.0 + y * 7.5 + n3 * 3.2) * math.pi)
    haze = (n1 * 0.52 + n2 * 0.28 + swirls * 0.20) * (bands + 0.12)

    lo, hi = np.percentile(haze, 52), np.percentile(haze, 99.2)
    haze = np.clip((haze - lo) / max(hi - lo, 1e-6), 0, 1) ** 1.85

    edge = np.minimum.reduce([
        np.broadcast_to(x / 0.12, (height, width)),
        np.broadcast_to((1 - x) / 0.12, (height, width)),
        np.broadcast_to(y / 0.10, (height, width)),
        np.broadcast_to((1 - y) / 0.10, (height, width)),
    ])
    haze *= np.clip(edge, 0, 1) * opacity

    alpha = np.clip(haze * 255, 0, 255).astype(np.uint8)
    rgb = np.empty((height, width, 3), dtype=np.uint8)
    rgb[..., 0] = 212
    rgb[..., 1] = 175
    rgb[..., 2] = 92
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA").filter(ImageFilter.GaussianBlur(1.1))

def save_webp(img, path, max_kb=120):
    for q in [48, 38, 30, 24, 18]:
        img.save(path, format="WEBP", quality=q, alpha_quality=55, method=3, lossless=False)
        size = path.stat().st_size
        if size <= max_kb * 1024:
            return q, size, True
    return q, size, False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="outputs")
    parser.add_argument("--width", type=int, default=2000)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=975)
    parser.add_argument("--opacity", type=float, default=0.38)
    parser.add_argument("--name", default="asset-g-haze")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    img = generate_asset_g(args.width, args.height, args.seed, args.opacity)
    png = out / f"{args.name}.png"
    webp = out / f"{args.name}.webp"
    preview = out / f"{args.name}-preview-on-midnight.png"

    img.save(png, optimize=True)
    q, size, ok = save_webp(img, webp)

    bg = Image.new("RGBA", img.size, (3, 7, 18, 255))
    Image.alpha_composite(bg, img).save(preview, optimize=True)

    print(f"PNG:  {png} ({png.stat().st_size} bytes)")
    print(f"WebP: {webp} ({size} bytes), q={q}, under_120kb={ok}")
    print(f"Preview: {preview}")

if __name__ == "__main__":
    main()
