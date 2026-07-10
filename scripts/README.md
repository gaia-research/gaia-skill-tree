# scripts/

Utility scripts for the Gaia Skill Registry.

---

## compress-assets.py — Ascension Overdrive asset compression pipeline

Reads raw vendor asset drops from `docs/assets/Asset [A-Z]/` and writes
web-optimised versions to `docs/assets/ascension-overdrive/`.

Raw drops are `.gitignore`d (`.gitignore` L8–14) — only the compressed
outputs under `docs/assets/ascension-overdrive/` are tracked in git.
This keeps the repo lean while preserving lossless source files for
future re-compression passes.

### Prerequisites

| Tool | Required | Install |
|------|----------|---------|
| **Python 3.10+** | Yes | already in the repo environment |
| **Pillow ≥ 10.2.0** | Yes | `pip install "Pillow>=10.2.0"` (or `pip install -r scripts/compress-assets.requirements.txt`) |
| **ffmpeg** | For MP4/WebM output | Windows: `winget install ffmpeg` · macOS: `brew install ffmpeg` · Linux: `sudo apt install ffmpeg` |
| **pngquant** | Optional (PNG fallback) | Windows: `winget install pngquant` · macOS: `brew install pngquant` · Linux: `sudo apt install pngquant` |

If `ffmpeg` is absent the script continues — it simply skips all MP4
sources with a warning.  If `pngquant` is absent the PNG fallback lane
copies the source PNG as-is (with a warning) instead of losslessly
compressing it.

### How to run

```bash
# Compress all vendor drops (skips outputs that are already newer than source)
python scripts/compress-assets.py

# Dry run — print what would happen without writing any files
python scripts/compress-assets.py --dry-run

# Compress only Asset C rank stamps
python scripts/compress-assets.py --only "Asset C"

# Force-overwrite existing outputs
python scripts/compress-assets.py --force

# Write to a custom output directory
python scripts/compress-assets.py --output-dir /path/to/output
```

### Naming convention

| Source glob | Output stem(s) |
|-------------|----------------|
| `Asset A/<arch plate>.png` | `apex-arch.{png,webp}` |
| `Asset A/Individual/*.png` | `apex-component-<slug>.{png,webp}` |
| `Asset B/*ledger*.png` | `ledger-texture.{png,webp}` |
| `Asset B/*ledger*variant*.png` | `ledger-texture-variant.{png,webp}` |
| `Asset C/*awakened*.png` | `rank-1-awakened.{png,webp}` |
| `Asset C/*named*.png` | `rank-2-named.{png,webp}` |
| `Asset C/*evolved*.png` | `rank-3-evolved.{png,webp}` |
| `Asset C/*hardened*.png` | `rank-4-hardened.{png,webp}` |
| `Asset C/*transcendent*.png` or `*ultimate*.png` | `rank-5-ultimate.{png,webp}` |
| `Asset C/*apex*.png` | `rank-6-apex.{png,webp}` |
| `Asset D/*4star*/4*structural*.png` | `unique-4.{png,webp}` |
| `Asset D/*5star*/5*ultimate*/5*gravitational*.png` | `unique-5-ultimate.{png,webp}` |
| `Asset D/*6star*/6*impossible*.png` | `unique-6-impossible.{png,webp}` |
| `*.mp4` (any Asset folder) | `<stem>.{mp4,webm}` (H.264 + VP9) |
| `Asset E/*` | **SKIP** (Asset E dropped per Issue #975) |

**Rank 5 naming note:** the v2 design uses `Ultimate` as the formal name
for 5★ (was `Transcendent` in v1).  The script accepts either vendor
spelling (`transcendent` or `ultimate`) and always outputs
`rank-5-ultimate.*`.

### WebP size targets

| Asset class | Target |
|-------------|--------|
| Rank stamps 1254×1254 | < 200 KB |
| Unique stamps 1254×1254 | < 200 KB |
| Apex components | < 200 KB |
| Apex arch plate 1536×1024+ | < 400 KB |
| Ledger texture 1024×1536 | < 80 KB |
| MP4 (H.264) | < 500 KB |
| WebM (VP9) | < 500 KB |

The script retries at lower quality (82 → 75 → 68 for WebP;
CRF 28/32 → 30 → 32 for video) and reports a warning if the output
still exceeds the target.

### `.gitignore` status

Raw vendor drops are gitignored by the following rules in `.gitignore`:

```
docs/assets/Asset*/
docs/assets/**/Variations/
docs/assets/**/Individual/
```

Only `docs/assets/ascension-overdrive/` (compressed outputs) is tracked.
Run `git status` to confirm no raw asset paths appear as untracked files.

### Slot in the design workflow

1. Vendor drops assets to `docs/assets/Asset [A-Z]/`
2. Operator runs `python scripts/compress-assets.py`
3. Compressed outputs land in `docs/assets/ascension-overdrive/`
4. Operator commits the outputs on the appropriate design/infra branch
5. The design JS/CSS at `docs/js/ascension-overdrive-v2.js` and
   `docs/css/ascension-overdrive-v2.css` reference the served-path names
   (e.g. `/assets/ascension-overdrive/rank-1-awakened.webp`)

See Issue #975 for the full Ascension Overdrive v2 context.
