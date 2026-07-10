#!/usr/bin/env python3
"""Ascension Overdrive asset compression pipeline.

Reads raw vendor asset drops from ``docs/assets/Asset [A-Z]/`` and writes
web-optimised versions to ``docs/assets/ascension-overdrive/`` (or another
``--output-dir``).

Raw drops are ``.gitignore``d — only the compressed outputs at
``docs/assets/ascension-overdrive/`` are committed.  See ``.gitignore``
L8–14 and Issue #975 for context.

Prerequisites
-------------
* **Pillow** — ``pip install "Pillow>=10.2.0"``
* **ffmpeg** — required for MP4/WebM output.
  - Windows : ``winget install ffmpeg``
  - macOS   : ``brew install ffmpeg``
  - Linux   : ``sudo apt install ffmpeg``  or ``sudo dnf install ffmpeg``
* **pngquant** (optional) — used for the PNG fallback lane.
  - Windows : ``winget install pngquant``
  - macOS   : ``brew install pngquant``
  - Linux   : ``sudo apt install pngquant``
  If pngquant is absent, the script falls back to copying the source PNG
  with a warning.

Usage
-----
  python scripts/compress-assets.py                    # compress all Asset [A-Z]/ folders
  python scripts/compress-assets.py --dry-run          # print what would happen, no writes
  python scripts/compress-assets.py --only "Asset C"   # compress one folder only
  python scripts/compress-assets.py --force            # overwrite existing outputs
  python scripts/compress-assets.py --output-dir PATH  # override default output dir
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional heavy imports — PIL is required; everything else is stdlib.
# ---------------------------------------------------------------------------
try:
    from PIL import Image  # type: ignore[import]
except ImportError:
    Image = None  # type: ignore[assignment]  — guarded below at runtime

# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_ROOT = REPO_ROOT / "docs" / "assets"
DEFAULT_OUTPUT_DIR = ASSETS_ROOT / "ascension-overdrive"

# ---------------------------------------------------------------------------
# Size targets (bytes) keyed by output stem pattern
# ---------------------------------------------------------------------------
# Stamps   : 1254×1254 square plates
# Wide     : 2560×1440+ hero / arch plates
# Ledger   : 1024×1536 texture
# Component: 1254×1254 or 1536×1024 individual arch parts (treat as stamp)
_WEBP_TARGET_BYTES: dict[str, int] = {
    "apex-arch":          400 * 1024,  # wide hero plate
    "ledger-texture":      80 * 1024,  # texture at 1024×1536
    "rank-":              200 * 1024,  # rank stamps 1254×1254
    "unique-":            200 * 1024,  # unique stamps 1254×1254
    "apex-component-":    200 * 1024,  # individual arch components
}

_MP4_TARGET_BYTES = 500 * 1024
_WEBM_TARGET_BYTES = 500 * 1024

# ---------------------------------------------------------------------------
# Naming convention: maps raw file paths -> served kebab-case output stems.
#
# Each entry is (pattern_fn, output_stem_fn) where:
#   pattern_fn(path) -> bool        — True if this rule matches the path
#   output_stem_fn(path) -> str     — the stem to use for the output file
#
# Rules are evaluated in order; the first match wins.
# ---------------------------------------------------------------------------

def _stem(p: Path) -> str:
    return p.stem.lower()


def _slugify(text: str) -> str:
    """Convert arbitrary filename text to kebab-case slug."""
    text = text.lower()
    # Remove version suffixes like -v1, -v2, etc.
    text = re.sub(r"-v\d+$", "", text)
    # Replace runs of non-alphanumeric characters with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _match_apex_arch(p: Path) -> bool:
    """Asset A root files that are the full arch plate (not inside Individual/)."""
    return (
        p.parent.name == "Asset A"
        and p.suffix.lower() in (".png", ".webp")
    )


def _match_apex_individual(p: Path) -> bool:
    """Asset A/Individual/ PNG components."""
    return (
        "Asset A" in str(p)
        and p.parent.name == "Individual"
        and p.suffix.lower() in (".png", ".webp")
    )


def _match_ledger(p: Path) -> bool:
    """Asset B ledger texture PNGs (root or Variations/)."""
    return (
        "Asset B" in str(p)
        and "ledger" in _stem(p)
        and p.suffix.lower() == ".png"
    )


def _match_rank_stamp(p: Path) -> bool:
    """Asset C rank stamp PNGs."""
    return "Asset C" in str(p) and p.suffix.lower() == ".png"


def _match_unique(p: Path) -> bool:
    """Asset D Unique class PNGs (root or Variations/)."""
    return "Asset D" in str(p) and p.suffix.lower() == ".png"


def _match_motion_loop(p: Path) -> bool:
    """Motion-loop MP4s from any asset folder (except E)."""
    return (
        p.suffix.lower() == ".mp4"
        and not _is_asset_e(p)
    )


def _is_asset_e(p: Path) -> bool:
    """True if the file lives under an 'Asset E' directory."""
    for part in p.parts:
        if re.fullmatch(r"Asset\s+E", part, re.IGNORECASE):
            return True
    return False


def _is_asset_letter(p: Path) -> str | None:
    """Return the asset letter (A-Z) if path is under an Asset X folder, else None."""
    for part in p.parts:
        m = re.fullmatch(r"Asset\s+([A-Z])", part, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None


def _rank_stem_from_name(name: str) -> str | None:
    """
    Map a rank-stamp filename to its canonical output stem.

    Handles:
      *awakened*   -> rank-1-awakened
      *named*      -> rank-2-named
      *evolved*    -> rank-3-evolved
      *hardened*   -> rank-4-hardened
      *transcendent* | *ultimate* -> rank-5-ultimate
      *variant*    -> None (skip variant sheets — they map to multiple ranks)
    """
    n = name.lower()
    if "variant" in n:
        return None  # multi-rank composite sheet; skip
    if "awakened" in n:
        return "rank-1-awakened"
    if "named" in n:
        return "rank-2-named"
    if "evolved" in n:
        return "rank-3-evolved"
    if "hardened" in n:
        return "rank-4-hardened"
    # 5★ is now "Ultimate" — also handle the old vendor "transcendent" spelling
    if "transcendent" in n or "ultimate" in n:
        return "rank-5-ultimate"
    # Apex is rank 6, but Asset C likely has no explicit apex stamp;
    # treat any unrecognised rank file as an apex placeholder
    if "apex" in n:
        return "rank-6-apex"
    return None


def _unique_stem_from_name(name: str) -> str | None:
    """
    Map a Unique-class filename to its canonical output stem.

    Handles the old names (structural, gravitational) and the new names
    (ultimate, impossible) plus numeric patterns like "4 star unique".
    """
    n = name.lower()

    # Explicit canonical names first
    if "4star" in n or "4-star" in n or "4 star" in n or "structural" in n:
        return "unique-4"
    if ("5star" in n or "5-star" in n or "5 star" in n or
            "gravitational" in n or "ultimate" in n):
        return "unique-5-ultimate"
    if ("6star" in n or "6-star" in n or "6 star" in n or
            "impossible" in n):
        return "unique-6-impossible"

    # Fallback: try to find a bare star digit in the name
    m = re.search(r"\b([456])\s*star", n)
    if m:
        star = m.group(1)
        if star == "4":
            return "unique-4"
        if star == "5":
            return "unique-5-ultimate"
        if star == "6":
            return "unique-6-impossible"
    return None


def _apex_component_stem_from_name(name: str) -> str:
    """
    Map an Asset A Individual component filename to its canonical output stem.

    Example:
      ascension-overdrive-apex-component-grand-arch-v1 -> apex-component-grand-arch
    """
    n = _slugify(name)
    # Strip common prefixes that are redundant
    for prefix in ("ascension-overdrive-", "ascension-", "ao-"):
        if n.startswith(prefix):
            n = n[len(prefix):]
    # Strip 'apex-arch' prefix if it crept in (that's the main arch, not a component)
    return n


def _apex_arch_stem_from_name(name: str) -> str:
    """Map an Asset A root arch plate to its canonical output stem."""
    n = _slugify(name)
    # Map common vendor spellings
    if "apex" in n and "arch" in n:
        return "apex-arch"
    if "apex_gate" in n or "apex-gate" in n:
        return "apex-arch"
    return "apex-arch"  # single source — there's only one


def _ledger_stem_from_name(name: str) -> str:
    """Map Asset B ledger texture to its canonical output stem."""
    n = name.lower()
    if "variant" in n:
        return "ledger-texture-variant"
    return "ledger-texture"


# ---------------------------------------------------------------------------
# Build a mapping: (source_path) -> output_stem
# Returns None to skip the file.
# ---------------------------------------------------------------------------

def resolve_output_stem(source: Path) -> str | None:  # noqa: C901
    """
    Return the kebab-case output stem for a given source asset file, or None
    to signal that this file should be skipped.
    """
    # Always skip Asset E
    if _is_asset_e(source):
        return None

    # Skip non-asset files that sneak in (Python helpers, etc.)
    if source.suffix.lower() not in (".png", ".mp4", ".webp"):
        return None

    name = source.stem

    # --- Asset A root (full arch plate) ---
    if _match_apex_arch(source):
        return _apex_arch_stem_from_name(name)

    # --- Asset A Individual components ---
    if _match_apex_individual(source):
        return _apex_component_stem_from_name(name)

    # --- Asset B ledger ---
    if _match_ledger(source):
        return _ledger_stem_from_name(name)

    # --- Asset C rank stamps ---
    if _match_rank_stamp(source):
        stem = _rank_stem_from_name(name)
        if stem is None:
            # Multi-rank composite sheet or unrecognised - skip
            return None
        return stem

    # --- Asset D Unique class ---
    if _match_unique(source):
        # Skip any non-PNG files that slipped through (e.g. helper .py scripts)
        if source.suffix.lower() != ".png":
            return None
        stem = _unique_stem_from_name(name)
        if stem is None:
            return None
        return stem

    # --- Motion loop MP4s ---
    if _match_motion_loop(source):
        # Derive from the Unique stem if the name carries a star number
        unique_stem = _unique_stem_from_name(name)
        if unique_stem:
            return f"{unique_stem}-loop"
        # Generic loop name
        letter = _is_asset_letter(source)
        slug = _slugify(name)
        return f"{slug}-loop" if not slug.endswith("-loop") else slug

    return None


# ---------------------------------------------------------------------------
# WebP size target lookup
# ---------------------------------------------------------------------------

def _webp_target(stem: str) -> int:
    """Return the WebP byte target for the given output stem."""
    for key, target in _WEBP_TARGET_BYTES.items():
        if stem.startswith(key):
            return target
    # Default: treat as stamp
    return 200 * 1024


# ---------------------------------------------------------------------------
# Tool availability checks
# ---------------------------------------------------------------------------

def _check_pillow() -> bool:
    return Image is not None


def _check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _check_pngquant() -> bool:
    return shutil.which("pngquant") is not None


# ---------------------------------------------------------------------------
# PNG -> WebP  (Pillow)
# ---------------------------------------------------------------------------

def _compress_png_to_webp(
    source: Path,
    dest: Path,
    dry_run: bool,
    stem: str,
) -> tuple[bool, str]:
    """
    Convert source PNG to WebP at dest.

    Tries quality 82 first, retries at 75 then 68 if over target.
    Returns (success, log_line).
    """
    target = _webp_target(stem)
    src_kb = source.stat().st_size // 1024

    if dry_run:
        return True, f"  [PNG->WEBP]  {source.name}  {src_kb}KB  (dry run)"

    with Image.open(source) as img:
        mode = img.mode
        if mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA" if "A" in mode else "RGB")

    tried_qualities: list[int] = []
    for quality in (82, 75, 68):
        tried_qualities.append(quality)
        with Image.open(source) as img:
            if img.mode not in ("RGBA", "RGB"):
                img = img.convert("RGBA" if "A" in img.mode else "RGB")
            img.save(dest, format="WEBP", quality=quality, method=6)

        out_size = dest.stat().st_size
        out_kb = out_size // 1024
        if out_size <= target:
            qs = f"q{quality}"
            mark = "OK"
            return True, (
                f"  [PNG->WEBP]  {source.name}  "
                f"{src_kb}KB -> {out_kb}KB (WebP {qs})  {mark}"
            )

    # Still over target — report and keep the last attempt
    out_kb = dest.stat().st_size // 1024
    qs_list = "/".join(str(q) for q in tried_qualities)
    warn = (
        f"  [PNG->WEBP]  {source.name}  "
        f"{src_kb}KB -> {out_kb}KB (WebP q{tried_qualities[-1]}, "
        f"OVER TARGET {target // 1024}KB after q{qs_list})  WARN"
    )
    return True, warn


# ---------------------------------------------------------------------------
# PNG -> PNG  (pngquant or copy fallback)
# ---------------------------------------------------------------------------

def _compress_png_to_png(
    source: Path,
    dest: Path,
    dry_run: bool,
    has_pngquant: bool,
) -> tuple[bool, str]:
    """
    Compress source PNG and write to dest.

    Uses pngquant if available, otherwise copies with a warning.
    Returns (success, log_line).
    """
    src_kb = source.stat().st_size // 1024

    if dry_run:
        tool = "pngquant" if has_pngquant else "copy (pngquant not found)"
        return True, f"  [PNG->PNG ]  {source.name}  {src_kb}KB  (dry run, tool={tool})"

    if has_pngquant:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_out = Path(tmpdir) / source.name
            result = subprocess.run(
                [
                    "pngquant",
                    "--quality=65-85",
                    "--speed=1",
                    "--strip",
                    "--output", str(tmp_out),
                    "--force",
                    str(source),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode not in (0, 98, 99):
                # 98 = quality too low; 99 = error — fall back to copy
                shutil.copy2(source, dest)
                out_kb = dest.stat().st_size // 1024
                return True, (
                    f"  [PNG->PNG ]  {source.name}  "
                    f"{src_kb}KB -> {out_kb}KB (pngquant failed rc={result.returncode}, copied)  WARN"
                )
            if tmp_out.exists():
                shutil.copy2(tmp_out, dest)
                out_kb = dest.stat().st_size // 1024
                return True, (
                    f"  [PNG->PNG ]  {source.name}  "
                    f"{src_kb}KB -> {out_kb}KB (pngquant)  OK"
                )
            # pngquant wrote back to source location under some flag combos
            shutil.copy2(source, dest)
            out_kb = dest.stat().st_size // 1024
            return True, (
                f"  [PNG->PNG ]  {source.name}  "
                f"{src_kb}KB -> {out_kb}KB (pngquant, no output found, copied)  WARN"
            )
    else:
        shutil.copy2(source, dest)
        out_kb = dest.stat().st_size // 1024
        return True, (
            f"  [PNG->PNG ]  {source.name}  "
            f"{src_kb}KB -> {out_kb}KB (copy; install pngquant for compression)  WARN"
        )


# ---------------------------------------------------------------------------
# MP4 -> MP4 + WebM  (ffmpeg)
# ---------------------------------------------------------------------------

def _compress_mp4(
    source: Path,
    dest_mp4: Path,
    dest_webm: Path,
    dry_run: bool,
) -> tuple[bool, list[str]]:
    """
    Recompress source MP4 to H.264 MP4 and VP9 WebM.

    Tries increasing CRF values if outputs exceed 500KB.
    Returns (success, list_of_log_lines).
    """
    src_kb = source.stat().st_size // 1024
    logs: list[str] = []

    if dry_run:
        logs.append(
            f"  [MP4->MP4 ]  {source.name}  {src_kb}KB  (dry run)"
        )
        logs.append(
            f"  [MP4->WEBM]  {source.name}  {src_kb}KB  (dry run)"
        )
        return True, logs

    # ---- H.264 MP4 --------------------------------------------------------
    mp4_ok = False
    for crf in (28, 30, 32):
        cmd = [
            "ffmpeg", "-y", "-i", str(source),
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", "veryslow",
            "-movflags", "+faststart",
            "-an",  # strip audio (motion-loop assets)
            str(dest_mp4),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logs.append(
                f"  [MP4->MP4 ]  {source.name}  "
                f"ffmpeg error (CRF {crf}): {result.stderr.strip()[-200:]}  FAIL"
            )
            return False, logs

        out_kb = dest_mp4.stat().st_size // 1024
        if dest_mp4.stat().st_size <= _MP4_TARGET_BYTES:
            logs.append(
                f"  [MP4->MP4 ]  {source.name}  "
                f"{src_kb}KB -> {out_kb}KB (H.264 CRF {crf})  OK"
            )
            mp4_ok = True
            break

        if crf < 32:
            logs.append(
                f"  [MP4->MP4 ]  {source.name}  "
                f"{out_kb}KB over target at CRF {crf}, retrying..."
            )
        else:
            logs.append(
                f"  [MP4->MP4 ]  {source.name}  "
                f"{src_kb}KB -> {out_kb}KB (H.264 CRF {crf}, "
                f"OVER TARGET {_MP4_TARGET_BYTES // 1024}KB)  WARN"
            )
            mp4_ok = True  # keep even if over target

    # ---- VP9 WebM ---------------------------------------------------------
    for crf in (32, 36, 40):
        cmd = [
            "ffmpeg", "-y", "-i", str(source),
            "-c:v", "libvpx-vp9",
            "-crf", str(crf),
            "-b:v", "0",
            "-deadline", "best",
            "-cpu-used", "0",
            "-an",
            str(dest_webm),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logs.append(
                f"  [MP4->WEBM]  {source.name}  "
                f"ffmpeg error (CRF {crf}): {result.stderr.strip()[-200:]}  FAIL"
            )
            return False, logs

        out_kb = dest_webm.stat().st_size // 1024
        if dest_webm.stat().st_size <= _WEBM_TARGET_BYTES:
            logs.append(
                f"  [MP4->WEBM]  {source.name}  "
                f"{src_kb}KB -> {out_kb}KB (VP9 CRF {crf})  OK"
            )
            break
        if crf < 40:
            logs.append(
                f"  [MP4->WEBM]  {source.name}  "
                f"{out_kb}KB over target at CRF {crf}, retrying..."
            )
        else:
            logs.append(
                f"  [MP4->WEBM]  {source.name}  "
                f"{src_kb}KB -> {out_kb}KB (VP9 CRF {crf}, "
                f"OVER TARGET {_WEBM_TARGET_BYTES // 1024}KB)  WARN"
            )

    return mp4_ok, logs


# ---------------------------------------------------------------------------
# Collect all source files under Assets root
# ---------------------------------------------------------------------------

def collect_sources(
    assets_root: Path,
    only: str | None,
) -> list[Path]:
    """
    Return sorted list of candidate source files from ``docs/assets/Asset */``.
    Respects ``--only`` filter.
    """
    if only:
        # Accept "Asset C" or "C" shorthand
        only_norm = only.strip()
        if not only_norm.upper().startswith("ASSET"):
            only_norm = f"Asset {only_norm.upper()}"
        folders = [assets_root / only_norm]
    else:
        # All Asset [A-Z] folders
        folders = sorted(
            p for p in assets_root.iterdir()
            if p.is_dir() and re.fullmatch(r"Asset\s+[A-Z]", p.name, re.IGNORECASE)
        )

    sources: list[Path] = []
    for folder in folders:
        if not folder.exists():
            print(f"WARNING: folder not found: {folder}")
            continue
        for p in sorted(folder.rglob("*")):
            if p.is_file() and p.suffix.lower() in (".png", ".mp4"):
                sources.append(p)
    return sources


# ---------------------------------------------------------------------------
# Process one source file
# ---------------------------------------------------------------------------

def process_file(  # noqa: C901
    source: Path,
    output_dir: Path,
    dry_run: bool,
    force: bool,
    has_pillow: bool,
    has_ffmpeg: bool,
    has_pngquant: bool,
) -> tuple[int, int, int, int]:
    """
    Process a single source file.

    Returns (processed, saved_bytes, skipped, failed) counts.
    """
    # ---- Asset E check (log and skip) --------------------------------------
    if _is_asset_e(source):
        asset_letter = _is_asset_letter(source)
        print(
            f"  [SKIP    ]  {source.relative_to(ASSETS_ROOT)}  "
            f"(Asset {asset_letter} dropped per Issue #975)"
        )
        return 0, 0, 1, 0

    # ---- Resolve output stem -----------------------------------------------
    stem = resolve_output_stem(source)
    if stem is None:
        print(f"  [SKIP    ]  {source.name}  (no naming rule matched)")
        return 0, 0, 1, 0

    suffix = source.suffix.lower()

    # ---- Dispatch by type --------------------------------------------------
    if suffix == ".png":
        if not has_pillow:
            print(
                f"  [ERROR   ]  {source.name}  "
                f"Pillow not installed — cannot compress PNG"
            )
            return 0, 0, 0, 1

        dest_webp = output_dir / f"{stem}.webp"
        dest_png = output_dir / f"{stem}.png"

        # ---- Skip-if-newer check -------------------------------------------
        if not force:
            webp_fresh = dest_webp.exists() and dest_webp.stat().st_mtime >= source.stat().st_mtime
            png_fresh = dest_png.exists() and dest_png.stat().st_mtime >= source.stat().st_mtime
            if webp_fresh and png_fresh:
                print(f"  [SKIP    ]  {source.name}  (output up-to-date)")
                return 0, 0, 1, 0

        src_size = source.stat().st_size
        total_saved = 0
        total_processed = 0

        # WebP lane
        if force or not dest_webp.exists() or dest_webp.stat().st_mtime < source.stat().st_mtime:
            ok, log = _compress_png_to_webp(source, dest_webp, dry_run, stem)
            print(log)
            if ok and not dry_run and dest_webp.exists():
                total_saved += max(0, src_size - dest_webp.stat().st_size)
                total_processed += 1
            elif ok:
                total_processed += 1
            else:
                return 0, 0, 0, 1

        # PNG lane
        if force or not dest_png.exists() or dest_png.stat().st_mtime < source.stat().st_mtime:
            ok, log = _compress_png_to_png(source, dest_png, dry_run, has_pngquant)
            print(log)
            if ok and not dry_run and dest_png.exists():
                total_saved += max(0, src_size - dest_png.stat().st_size)
                total_processed += 1
            elif ok:
                total_processed += 1
            else:
                return 0, 0, 0, 1

        return total_processed, total_saved, 0, 0

    elif suffix == ".mp4":
        if not has_ffmpeg:
            print(
                f"  [ERROR   ]  {source.name}  "
                f"ffmpeg not found on PATH — install it and retry"
            )
            return 0, 0, 0, 1

        dest_mp4 = output_dir / f"{stem}.mp4"
        dest_webm = output_dir / f"{stem}.webm"

        if not force:
            mp4_fresh = dest_mp4.exists() and dest_mp4.stat().st_mtime >= source.stat().st_mtime
            webm_fresh = dest_webm.exists() and dest_webm.stat().st_mtime >= source.stat().st_mtime
            if mp4_fresh and webm_fresh:
                print(f"  [SKIP    ]  {source.name}  (output up-to-date)")
                return 0, 0, 1, 0

        src_size = source.stat().st_size
        ok, logs = _compress_mp4(source, dest_mp4, dest_webm, dry_run)
        for log in logs:
            print(log)
        if ok and not dry_run:
            saved = src_size
            if dest_mp4.exists():
                saved -= dest_mp4.stat().st_size
            if dest_webm.exists():
                saved -= dest_webm.stat().st_size
            return 2, max(0, saved), 0, 0
        elif ok:
            return 2, 0, 0, 0
        return 0, 0, 0, 1

    else:
        print(f"  [SKIP    ]  {source.name}  (unsupported type {suffix})")
        return 0, 0, 1, 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:  # noqa: C901
    parser = argparse.ArgumentParser(
        prog="compress-assets.py",
        description=(
            "Ascension Overdrive asset compression pipeline. "
            "Reads raw vendor drops from docs/assets/Asset [A-Z]/ "
            "and writes web-optimised outputs to docs/assets/ascension-overdrive/."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing any files.",
    )
    parser.add_argument(
        "--only",
        metavar="ASSET_FOLDER",
        help='Compress only one asset folder, e.g. "Asset C" or "C".',
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing outputs even if they are newer than the source.",
    )
    parser.add_argument(
        "--output-dir",
        metavar="PATH",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR}).",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)

    # ---- Pre-flight checks -------------------------------------------------
    has_pillow = _check_pillow()
    has_ffmpeg = _check_ffmpeg()
    has_pngquant = _check_pngquant()

    if not has_pillow:
        print(
            "ERROR: Pillow is not installed.  "
            'Run:  pip install "Pillow>=10.2.0"',
            file=sys.stderr,
        )
        return 1

    if not has_ffmpeg:
        print(
            "WARNING: ffmpeg not found on PATH.  "
            "MP4/WebM outputs will be skipped.\n"
            "  Windows: winget install ffmpeg\n"
            "  macOS:   brew install ffmpeg\n"
            "  Linux:   sudo apt install ffmpeg",
        )

    if not has_pngquant:
        print(
            "WARNING: pngquant not found.  "
            "PNG fallback lane will copy source files instead of compressing.\n"
            "  Windows: winget install pngquant\n"
            "  macOS:   brew install pngquant\n"
            "  Linux:   sudo apt install pngquant",
        )

    # ---- Create output directory -------------------------------------------
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Collect source files ----------------------------------------------
    sources = collect_sources(ASSETS_ROOT, args.only)

    if not sources:
        print("No source files found.  Check that docs/assets/Asset [A-Z]/ exists.")
        return 0

    print(f"\nAsset compression pipeline  ->  {output_dir}")
    print(f"Dry run: {args.dry_run}   Force: {args.force}")
    print(f"Found {len(sources)} source file(s)\n")

    # ---- Process -----------------------------------------------------------
    total_processed = 0
    total_saved = 0
    total_skipped = 0
    total_failed = 0

    for source in sources:
        try:
            p, s, sk, f = process_file(
                source=source,
                output_dir=output_dir,
                dry_run=args.dry_run,
                force=args.force,
                has_pillow=has_pillow,
                has_ffmpeg=has_ffmpeg,
                has_pngquant=has_pngquant,
            )
            total_processed += p
            total_saved += s
            total_skipped += sk
            total_failed += f
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR   ]  {source.name}  {exc}")
            if args.dry_run:
                traceback.print_exc()
            total_failed += 1

    # ---- Summary -----------------------------------------------------------
    saved_mb = total_saved / (1024 * 1024)
    print()
    print("-" * 60)
    print(f"Processed: {total_processed} file(s)")
    print(f"Saved:     {saved_mb:.2f} MB total")
    print(f"Skipped:   {total_skipped} file(s) "
          f"(Asset E dropped, or output already up-to-date)")
    print(f"Failed:    {total_failed} file(s)")
    if total_failed:
        print("\nOne or more files failed — see output above for details.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
