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
import os
import re
import sys
import time
import urllib.request
import urllib.error
import json
from datetime import date, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMED_DIR = REPO_ROOT / "registry" / "named"

# ---------------------------------------------------------------------------
# Frontmatter parser (regex-based — no ruamel/python-frontmatter dep needed)
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)


def _split_frontmatter(text: str) -> tuple[str, str, str]:
    """Return (pre_fence, fm_content, body).

    pre_fence is always '---\\n'.  Returns ('', '', text) if no frontmatter.
    """
    m = _FM_RE.match(text)
    if not m:
        return ("", "", text)
    fm_raw = m.group(1)
    body = text[m.end():]
    return ("---\n", fm_raw, body)


def _load_yaml_simple(text: str) -> dict:
    """Thin wrapper — project uses pyyaml (listed in pyproject.toml deps)."""
    import yaml  # pyyaml — always available in this project
    return yaml.safe_load(text) or {}


# ---------------------------------------------------------------------------
# GitHub URL parser
# ---------------------------------------------------------------------------

_GH_RE = re.compile(
    r"https?://github\.com/([^/]+)/([^/\s#?]+)"
    r"(?:/(?:blob|tree|stargazers|commits?|releases?)(/[^\s#?]*)?)?"
)


def parse_owner_repo(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL.  Returns None on failure."""
    if not url:
        return None
    m = _GH_RE.match(url.strip())
    if not m:
        return None
    owner = m.group(1)
    repo = m.group(2).rstrip("/")
    # Strip .git suffix if present
    if repo.endswith(".git"):
        repo = repo[:-4]
    return (owner, repo)


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

_GH_API = "https://api.github.com/repos/{owner}/{repo}"
_CACHE: dict[str, int | None] = {}  # (owner/repo) -> star count or None on error


def fetch_stars(owner: str, repo: str) -> int | None:
    """Fetch stargazers_count from GitHub API.  Returns None on any error."""
    key = f"{owner}/{repo}"
    if key in _CACHE:
        return _CACHE[key]

    url = _GH_API.format(owner=owner, repo=repo)
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})

    token = os.environ.get("GH_TOKEN", "")
    if token:
        req.add_header("Authorization", f"token {token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            count = data.get("stargazers_count")
            _CACHE[key] = count
            return count
    except urllib.error.HTTPError as exc:
        print(
            f"  [warn] GitHub API {exc.code} for {key}: {exc.reason}",
            file=sys.stderr,
        )
        _CACHE[key] = None
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] GitHub API error for {key}: {exc}", file=sys.stderr)
        _CACHE[key] = None
        return None
    finally:
        time.sleep(0.1)


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
# Frontmatter rewriter
# ---------------------------------------------------------------------------

def _update_evidence_row_in_text(text: str, row_index: int, new_stars: int) -> str:
    """Update the `stars:` field (and add/update `updatedAt:`) in the raw YAML
    frontmatter text for the evidence entry at *row_index*.

    We rewrite only the matching evidence block to avoid disturbing ordering or
    formatting of the rest of the document.

    Strategy: locate the N-th evidence list item inside the frontmatter and do
    targeted in-place substitution.
    """
    m = _FM_RE.match(text)
    if not m:
        return text  # safety: nothing to update

    fm_text = m.group(1)
    body_text = text[m.end():]

    # Find all top-level '- ' evidence list item start positions in the fm_text.
    # Evidence block is under the 'evidence:' key — we find the block and then
    # locate the N-th list item.
    # Simple approach: split fm into lines and walk the evidence block.

    lines = fm_text.split("\n")
    in_evidence = False
    item_idx = -1
    item_start_line = None  # line index where item_idx == row_index starts
    item_end_line = None
    today_str = date.today().isoformat()

    for i, line in enumerate(lines):
        if re.match(r"^evidence\s*:", line):
            in_evidence = True
            continue
        if in_evidence:
            # A top-level key (no leading spaces) ends the evidence block
            if line and not line[0].isspace() and line[0] != "-":
                in_evidence = False
                if item_start_line is not None and item_end_line is None:
                    item_end_line = i
                break
            if re.match(r"^- ", line):
                item_idx += 1
                if item_idx == row_index:
                    item_start_line = i
                elif item_idx == row_index + 1:
                    item_end_line = i
                    break

    if item_start_line is None:
        return text  # Couldn't locate the block — bail out

    if item_end_line is None:
        item_end_line = len(lines)

    block_lines = lines[item_start_line:item_end_line]

    # Update or insert stars:
    stars_updated = False
    updated_at_updated = False
    new_block = []
    for bl in block_lines:
        if re.match(r"\s+stars\s*:", bl):
            indent = re.match(r"(\s+)", bl)
            prefix = indent.group(1) if indent else "  "
            new_block.append(f"{prefix}stars: {new_stars}")
            stars_updated = True
        elif re.match(r"\s+updatedAt\s*:", bl):
            indent = re.match(r"(\s+)", bl)
            prefix = indent.group(1) if indent else "  "
            new_block.append(f"{prefix}updatedAt: '{today_str}'")
            updated_at_updated = True
        else:
            new_block.append(bl)

    if not stars_updated:
        # Insert after first line of block (the '- ...' line)
        new_block.insert(1, f"  stars: {new_stars}")
    if not updated_at_updated:
        new_block.insert(1 if not stars_updated else 2, f"  updatedAt: '{today_str}'")

    new_lines = lines[:item_start_line] + new_block + lines[item_end_line:]
    new_fm = "\n".join(new_lines)
    return f"---\n{new_fm}\n---\n{body_text}"


# ---------------------------------------------------------------------------
# Process a single file
# ---------------------------------------------------------------------------

def process_file(path: Path, apply: bool) -> list[dict]:
    """Process one skill markdown file.  Returns list of result rows."""
    text = path.read_text(encoding="utf-8")
    _, fm_raw, _ = _split_frontmatter(text)
    if not fm_raw:
        return []

    fm = _load_yaml_simple(fm_raw)
    skill_id = fm.get("id", str(path.relative_to(NAMED_DIR).with_suffix("")))

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
        new_stars = fetch_stars(owner, repo)

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
            text = _update_evidence_row_in_text(text, idx, new_stars)

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
