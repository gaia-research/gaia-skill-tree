#!/usr/bin/env python3
"""
stargazerHeartbeat.py — monthly stargazer refresh for github-stars-own evidence rows.

Usage:
    python scripts/stargazerHeartbeat.py [--dry-run] [--apply]

Default mode is --dry-run.  Pass --apply to write changes back to frontmatter files.

Algorithm:
1. Find all registry/named/<contributor>/<skill>.md files.
2. Parse YAML frontmatter.
3. For each evidence row with type in {github-stars-own, github-stars}:
   - Resolve the GitHub owner/repo from the evidence `source` URL first,
     falling back to `links.github` from the frontmatter.
4. Query GET https://api.github.com/repos/{owner}/{repo}.
5. Compare stargazers_count vs stored `stars` field.
6. If abs delta > 5% OR abs delta > 100: update `stars` + set `updatedAt` on the row.
7. Write back only if changed (idempotent).

Auth: set GH_TOKEN env var to raise rate limit to 5000 req/hr.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure repo root is on sys.path so ``scripts.lib`` resolves when this file
# is executed directly (e.g. ``python scripts/stargazerHeartbeat.py --apply``)
# as well as when imported as a module (e.g. in tests via pytest).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Shared library imports (scripts.lib — extracted in PR 2/7)
# ---------------------------------------------------------------------------

from scripts.lib.frontmatter import (
    load_yaml_simple,
    split_frontmatter,
    update_list_item_in_frontmatter,
)
from scripts.lib.github_api import fetch_json, parse_owner_repo

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = _REPO_ROOT
NAMED_DIR = REPO_ROOT / "registry" / "named"

# ---------------------------------------------------------------------------
# GitHub star fetch — thin wrapper around the shared fetch_json primitive
# ---------------------------------------------------------------------------


def _fetch_stars(owner: str, repo: str) -> int | None:
    """Fetch stargazers_count for *owner*/*repo* via the GitHub API.

    Returns ``None`` on any error (HTTPError, timeout, missing field).
    Delegates caching, throttling, and auth to ``scripts.lib.github_api.fetch_json``.
    """
    data = fetch_json(f"https://api.github.com/repos/{owner}/{repo}")
    if data is None:
        return None
    return data.get("stargazers_count")


# ---------------------------------------------------------------------------
# Delta threshold
# ---------------------------------------------------------------------------


def _needs_update(old: int, new: int) -> bool:
    """Return True if the star count warrants a refresh."""
    delta = abs(new - old)
    if delta > 100:
        return True
    if old > 0 and (delta / old) > 0.05:
        return True
    return False


# ---------------------------------------------------------------------------
# Process a single file
# ---------------------------------------------------------------------------


def process_file(path: Path, apply: bool) -> list[dict]:
    """Process one skill markdown file.  Returns list of result rows."""
    text = path.read_text(encoding="utf-8")
    _, fm_raw, _ = split_frontmatter(text)
    if not fm_raw:
        return []

    fm = load_yaml_simple(fm_raw)
    if "id" in fm:
        skill_id = fm["id"]
    else:
        try:
            skill_id = str(path.relative_to(NAMED_DIR).with_suffix(""))
        except ValueError:
            skill_id = path.stem

    # links.github for fallback owner/repo resolution
    links_github = (fm.get("links") or {}).get("github", "")

    evidence = fm.get("evidence") or []
    results = []

    for idx, row in enumerate(evidence):
        row_type = row.get("type", "")
        if row_type not in ("github-stars-own", "github-stars"):
            continue

        old_stars = row.get("stars")
        if old_stars is None:
            # No existing star count — still fetch so we can populate it
            old_stars = 0

        # Resolve owner/repo: prefer evidence source URL, fallback to links.github
        source_url = row.get("source", "")
        parsed = parse_owner_repo(source_url) or parse_owner_repo(links_github)

        if parsed is None:
            results.append({
                "skill_id": skill_id,
                "evidence_idx": idx,
                "old_stars": old_stars,
                "new_stars": None,
                "delta": None,
                "updated": False,
                "skip_reason": "no_github_url",
            })
            continue

        owner, repo = parsed
        new_stars = _fetch_stars(owner, repo)

        if new_stars is None:
            results.append({
                "skill_id": skill_id,
                "evidence_idx": idx,
                "old_stars": old_stars,
                "new_stars": None,
                "delta": None,
                "updated": False,
                "skip_reason": "api_error",
            })
            continue

        delta = new_stars - old_stars
        should_update = _needs_update(old_stars, new_stars)

        results.append({
            "skill_id": skill_id,
            "evidence_idx": idx,
            "old_stars": old_stars,
            "new_stars": new_stars,
            "delta": delta,
            "updated": should_update and apply,
            "skip_reason": None,
        })

        if should_update and apply:
            today_str = date.today().isoformat()
            text = update_list_item_in_frontmatter(
                text, "evidence", idx, {"stars": new_stars, "updatedAt": today_str}
            )

    if apply and any(r["updated"] for r in results):
        path.write_text(text, encoding="utf-8")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Monthly stargazer refresh for github-stars-own evidence rows."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print what would change without writing (default when neither flag given)",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually update frontmatter files",
    )
    args = parser.parse_args()

    # If neither flag given, default to dry-run
    if not args.apply:
        args.dry_run = True

    mode_label = "APPLY" if args.apply else "DRY-RUN"
    print(f"stargazerHeartbeat — mode: {mode_label}")
    print(f"Scanning {NAMED_DIR} ...\n")

    all_results: list[dict] = []

    md_files = sorted(NAMED_DIR.rglob("*.md"))
    for path in md_files:
        rows = process_file(path, apply=args.apply)
        all_results.extend(rows)

    # ---------------------------------------------------------------------------
    # Summary table
    # ---------------------------------------------------------------------------
    star_rows = [r for r in all_results if r["skip_reason"] is None]
    skipped = [r for r in all_results if r["skip_reason"] is not None]

    col_id = max((len(r["skill_id"]) for r in all_results), default=20) + 2
    col_id = max(col_id, 20)

    header = (
        f"{'skill_id':<{col_id}} {'old_stars':>10} {'new_stars':>10} "
        f"{'delta':>8}  {'updated':<8}"
    )
    sep = "-" * len(header)

    print(header)
    print(sep)

    updated_count = 0
    for r in star_rows:
        delta_str = f"{r['delta']:+d}" if r["delta"] is not None else "n/a"
        new_str = str(r["new_stars"]) if r["new_stars"] is not None else "error"
        upd_str = "YES" if r["updated"] else ("would" if r["delta"] is not None and _needs_update(r["old_stars"], r["new_stars"]) and not args.apply else "no")
        print(
            f"{r['skill_id']:<{col_id}} {r['old_stars']:>10} {new_str:>10} "
            f"{delta_str:>8}  {upd_str:<8}"
        )
        if r["updated"]:
            updated_count += 1

    print(sep)
    print(
        f"\nTotal evidence rows scanned: {len(all_results)} "
        f"(with stars: {len(star_rows)}, skipped: {len(skipped)})"
    )
    print(
        f"Files updated: {updated_count} "
        f"{'(written)' if args.apply else '(dry-run — pass --apply to write)'}"
    )

    if skipped:
        print("\nSkipped rows:")
        for r in skipped:
            print(f"  {r['skill_id']}[{r['evidence_idx']}]: {r['skip_reason']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
