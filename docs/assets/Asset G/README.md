# Asset G Trial — Parallax Haze Layer

Generated Asset G as an alpha-native warm-sepia haze layer.

## Recommended files

- `outputs/asset-g-haze.png`: transparent PNG source
- `outputs/asset-g-haze.webp`: production WebP
- `outputs/asset-g-haze-preview-on-midnight.png`: preview composited on Gaia `#030712`

## Specs

- Dimensions: 2000×1200
- Alpha: yes
- WebP budget target: ≤120KB
- Actual WebP: 61538 bytes, quality 48, under budget: True

## Implementation

Place between ledger paper and risers:

```html
<img
  class="ao-plane ao-haze"
  src="assets/ascension-overdrive/asset-g-haze.webp"
  alt=""
  aria-hidden="true"
  loading="lazy"
  decoding="async"
/>
```

Use `scripts/asset_g_css_snippet.css` and `scripts/asset_g_parallax_snippet.js` as the integration starting point.

## Regenerate

```bash
python scripts/make_asset_g_haze.py --out outputs --width 2000 --height 1200 --seed 975 --opacity 0.38
```
