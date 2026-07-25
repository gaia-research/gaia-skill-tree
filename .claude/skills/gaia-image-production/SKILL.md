---
name: gaia-image-production
description: Gaia Skill Tree image-generation and deterministic export harness for Ascension Overdrive v3. Use when generating, iterating, refining, cropping, color-grading, making transparent cutouts, compressing, upscaling, or validating production image assets. Always use image gen 2 / gpt-image-2 and never nano-banana.
---

# Gaia Image Production Harness

Use this skill for generated images, image iteration, asset production,
responsive crops, transparency, color grading, upscaling, motion posters, and
final exports for Gaia Skill Tree. For Ascension Overdrive v3, the commissions
document is the source of truth; do not invent assets outside it.

This skill is adapted from the Gaia Research image-production harness. Its
Sharp-based ledger helpers remain in the adjacent Gaia Research repository and
are not assumed to exist here. Gaia Skill Tree uses the deterministic local
toolchain documented below.

## Hard rules

- Always use image gen 2 / `gpt-image-2` for generative work.
- Never use `nano-banana`, `nano-banana-2`, or a cheap/fast image model for Gaia
  production assets.
- Preserve every supplied or generated master outside Git. Never overwrite an
  incoming master.
- Only production WebP raster derivatives enter this repository. Keep PNG,
  PSD, AI, Figma, and other raster masters in the local master archive.
- SVG and motion formats enter Git only where the commissions document
  explicitly requires them, notably Asset H's primary SVG and Asset E's loops.
- Do not regenerate an accepted composition when deterministic editing,
  compositing, color grading, or export can satisfy the brief.
- Do not modify or replace v2 assets marked `REUSED-V2`.
- Use the `aov3-` filename prefix for every new Ascension v3 asset.

## Canonical Ascension v3 paths

- Commission source of truth:
  `founder/handovers/design-v6.1.1-ascension-overdrive-commissions-v3.md`
- Section shape:
  `founder/handovers/design-v6.1.1-ascension-overdrive-shape-v3.md`
- Existing v2 implementation reference:
  `docs/css/ascension-overdrive-v2.css` and
  `docs/js/ascension-overdrive-v2.js`
- Served production assets: `docs/assets/ascension-overdrive/`
- Local master root, outside Git:
  `/Users/marcotiongson/Documents/gaia-asset-masters/ascension-overdrive-v3/`
- Immutable supplied originals:
  `/Users/marcotiongson/Documents/gaia-asset-masters/ascension-overdrive-v3/incoming/`
- Working masters and iterations:
  `/Users/marcotiongson/Documents/gaia-asset-masters/ascension-overdrive-v3/workbench/`
- Approved local masters:
  `/Users/marcotiongson/Documents/gaia-asset-masters/ascension-overdrive-v3/approved/`
- Local review sheets:
  `/Users/marcotiongson/Documents/gaia-asset-masters/ascension-overdrive-v3/review/`

## Ascension v3 visual register

The design is a deliberate dichotomy, not one visual system recolored twice:

- Suite is warm, ceremonial, ordered, engraved, architectural, and closed.
- Unique is cold, broken, void-filled, impossible, and open.
- Shared substrate is celestial copperplate cartography, never a modern nebula
  or fantasy map.
- Suite stamps ascend from natural-history specimen plates at 1–3 stars to
  Beaux-Arts ceremonial architecture at 4–6 stars.
- Unique geometry must break structurally. It must not be Suite ornament on a
  dark background.
- Asset H is one binary gold thread: one trunk, exactly two branches, with
  negative space reserved for card overlays.

Use the OKLCH targets in the commissions document as the authoritative palette:

- Suite cream: `oklch(0.92 0.025 85)`
- Suite gold: `oklch(0.78 0.14 82)`
- Suite brass: `oklch(0.65 0.10 72)`
- Suite ink: `oklch(0.25 0.02 75)`
- Unique void: `oklch(0.13 0.015 260)`
- Unique singularity: `oklch(0.96 0.01 240)`
- Unique fracture: `oklch(0.55 0.03 245)`
- Unique glitch: `oklch(0.72 0.16 12)`
- Substrate ground: `oklch(0.22 0.015 85)`
- Substrate ink: `oklch(0.55 0.03 75)`

## Standard workflow

### 1. Read the brief and references

Read the relevant asset section in the commissions document, its failure test,
the v3 shape, and the closest accepted v2 production references. Treat exact
dimensions, alpha requirements, mobile compositions, size ceilings, named SVG
paths, and reuse/deprecation status as acceptance criteria.

### 2. Intake originals without mutation

Copy supplied files into `incoming/` with a descriptive `-concept-original`
name. Record the original filename, dimensions, byte size, and SHA-256 in the
directory README. Verify source and copy hashes match. Never optimize, resize,
strip metadata, or color-grade an incoming original in place.

### 3. Plan the batch

Before generation or editing, record:

- asset ID and purpose;
- target scene and rail;
- desktop, mobile, card, and badge dimensions required by the spec;
- alpha or opaque-ground requirement;
- reference masters that must be preserved;
- target WebP size ceiling;
- visual acceptance criteria and the applicable numbered failure tests.

### 4. Generate only what the brief requires

Use image gen 2 for missing compositions or targeted visual refinement. Use the
selected image as the reference for chained iteration. Ask for only the desired
change, retain versioned masters, and keep quiet space or silhouettes required
by the scene. Do not ask the model to rasterize UI copy.

For concept exploration, vary one meaningful axis per branch, such as geometry,
silhouette, negative-space distribution, or material register. Select one
candidate before expensive upscale and export work.

### 5. Prefer deterministic edits after selection

Once a composition is accepted, use deterministic tools for crop, resize,
color-grade, alpha cleanup, metadata stripping, and WebP compression. Avoid
generative edits for operations that should be reproducible.

The verified local stack is:

- Pillow 12 with libwebp 1.6 for scripted pixel operations;
- `cwebp` 1.6 for final WebP encoding, alpha control, crop, resize, and metadata
  stripping;
- `ffmpeg` and `ffprobe` 8.1 for Asset E loops and poster extraction;
- `sips` for quick metadata inspection;
- SHA-256 via `shasum -a 256`.

ImageMagick and a project-local Sharp installation are not assumed available.
Do not add them merely to complete routine production work.

### 6. Export WebP deliberately

For an opaque plate or substrate:

```bash
cwebp -preset picture -m 6 -q 78 -sharp_yuv -metadata none \
  input.png -o output.webp
```

For an alpha-bearing stamp or overlay:

```bash
cwebp -preset picture -m 6 -q 82 -alpha_q 100 -exact -sharp_yuv \
  -metadata none input.png -o output.webp
```

For a deterministic crop and resize before encoding:

```bash
cwebp -preset picture -m 6 -q 82 -alpha_q 100 -exact -sharp_yuv \
  -metadata none -crop X Y WIDTH HEIGHT -resize OUT_WIDTH OUT_HEIGHT \
  input.png -o output.webp
```

Tune quality downward only as far as the asset's size ceiling requires. Inspect
engraved hairlines, alpha edges, dark gradients, and singularity highlights at
100% after every compression change. Do not force card and badge variants from
the hero master when the spec requires hand-composed small-scale artwork.

### 7. Prepare transparency and chroma-key cutouts

Perform keying on a versioned workbench copy. Preserve RGB under transparent
pixels when edge compositing benefits from it. Produce a diagnostic mask and a
checkerboard preview, then inspect the result over both the substrate ground and
the Unique void. Reject white halos, dark matte fringes, pinholes, and clipped
engraved edges.

The Gaia Research `prep-cutout.ts` helper is a useful implementation reference,
but it resolves paths against Gaia Research and must not be run against this
repository without a deliberate port. Pillow is the default local mechanism
until such a port is separately commissioned.

### 8. Color-grade Asset G before commissioning new haze

Create Suite-warm and Unique-cold grades from the preserved v2 haze source.
Keep the alpha field and luminance structure stable while changing hue and
temperature. Launch a fresh illustration only if one of the explicit Asset G
escalation triggers in the commissions document fails during compositing.

### 9. Handle Asset E motion deterministically

Keep master loops outside Git. Deliver 24 or 30 fps, silent, seamless 6–12
second loops. Use H.264 MP4 and VP9 WebM only if the spec-authorized motion
formats are being committed. Extract a first-frame-parity WebP poster for the
reduced-motion path.

Example poster extraction:

```bash
ffmpeg -i input.mp4 -vf 'select=eq(n\,0)' -frames:v 1 poster.png
cwebp -preset picture -m 6 -q 82 -sharp_yuv -metadata none \
  poster.png -o poster.webp
```

Inspect loop duration, frame rate, dimensions, audio absence, and codec with:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate \
  -show_entries format=duration,size -of json input.webm
```

### 10. Review in contact sheets and composites

Review each related set at equal display size on one sheet. For C and D, place
4–6 star Suite and Unique stamps side by side so the dichotomy can be judged
without labels. Also composite alpha assets over both rail grounds. Review hero,
card, badge, desktop, and 375px mobile presentations independently.

### 11. Validate before promotion

For every production derivative, verify:

- exact pixel dimensions;
- actual file format, not only extension;
- alpha presence where required;
- byte size within the per-asset ceiling;
- filename follows `aov3-<asset>-<rank>-<state>.webp`;
- no collision with v2 filenames;
- clean compositing on both required grounds;
- source and derivative hashes recorded in the local master archive;
- only the reviewed WebP derivative is staged as a raster asset.

Useful inspection commands:

```bash
sips -g pixelWidth -g pixelHeight -g format -g hasAlpha asset.webp
du -h asset.webp
shasum -a 256 asset.webp
file asset.webp
```

Run the repository's design/asset checks that apply to the changed files. Do
not use unrelated full-suite failures to change the visual brief.

## Ascension v3 delivery priorities

Follow the commission cadence unless Marcus changes it:

1. Asset H, Y-Fork gold-thread illustration.
2. Asset B v3, astrolabe substrate.
3. Assets C v3 and D v3 as one paired stamp calibration pass.
4. Asset I, Unique Impossible terminal.
5. Asset F v3 Suite plates and Asset G color grades.
6. Asset E v3 motion loops last.

## Final handoff checklist

Report:

- immutable source path and checksum;
- approved local master path;
- production WebP path and dimensions;
- derivative paths and file sizes;
- whether alpha/composite tests passed;
- which commission failure tests passed;
- which design checks ran;
- any remaining manual visual-review risk.
