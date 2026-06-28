#!/usr/bin/env python3
"""Sync README marker-owned regions to the adjacent Gaia wiki repository.

Pages updated
-------------
Home.md
    - Version string inside the "Graph at a Glance" code block
CLI-Reference.md
    - Editable install extra (.[embeddings] → .[embeddings,dev])
    - ``gaia --help`` quick-reference block (<!-- gaia:cli-start/end --> markers,
      idempotent on repeat runs)
Initiates-Rite.md
    - Editable install extra

Usage
-----
    python scripts/sync_wiki.py [--wiki-dir PATH] [--check] [--push]

    --wiki-dir PATH   Path to the cloned wiki repo (default: ../gaia-wiki)
    --check           Report drift without writing files  (exit 1 if stale)
    --push            git commit + push to wiki master after writing
                      Requires git credentials pre-configured on the wiki remote
                      (e.g. via https://token:PAT@github.com/... clone URL).

Called by
---------
    gaia docs build          → build_wiki_sync() in scripts/build_docs.py
    sync-artifacts.yml CI    → python scripts/sync_wiki.py --push (after cloning
                               the wiki with WIKI_PAT)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WIKI_REMOTE = "https://github.com/gaia-research/gaia-skill-tree.wiki.git"

# ─── helpers ──────────────────────────────────────────────────────────────────


def _extract_region(text: str, start: str, end: str) -> str | None:
    """Return content between HTML comment markers, stripped (None if absent)."""
    pattern = re.escape(start) + r"\n(.*?)\n" + re.escape(end)
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else None


def _replace_region(text: str, start: str, end: str, body: str) -> tuple[str, bool]:
    """Insert or replace a marker-bounded region.

    If markers are absent the region is appended at EOF (initial seeding).
    Returns (new_text, changed_bool).
    """
    region = f"{start}\n{body.rstrip()}\n{end}"
    if start not in text or end not in text:
        return text.rstrip() + "\n\n" + region + "\n", True
    before, rest = text.split(start, 1)
    _old, after = rest.split(end, 1)
    updated = before + region + after
    return updated, updated != text


def _readme_version(readme: str) -> str:
    m = re.search(r"Current Gaia CLI version: `([^`]+)`", readme)
    return m.group(1) if m else "unknown"


def _readme_cli_help(readme: str) -> str:
    return _extract_region(readme, "<!-- gaia:cli-start -->", "<!-- gaia:cli-end -->") or ""


def _readme_editable_install(readme: str) -> str:
    """Return the editable install command as it appears in README."""
    m = re.search(r'pip install -e "\.\[([^\]]+)\]"', readme)
    return f'pip install -e ".[{m.group(1)}]"' if m else 'pip install -e ".[embeddings,dev]"'


# ─── per-page updaters ────────────────────────────────────────────────────────


def _update_home(text: str, version: str) -> tuple[str, bool]:
    """Update the version string in the Graph at a Glance code block."""
    new_text = re.sub(
        r"(GAIA SKILL REGISTRY\s+)v\d+\.\d+\.\d+",
        rf"\g<1>v{version}",
        text,
    )
    return new_text, new_text != text


def _update_cli_reference(text: str, cli_help: str, editable_install: str) -> tuple[str, bool]:
    """Fix editable install extra and add/refresh the gaia --help quick-reference block."""
    changed = False

    # 1. Editable install extra (matches any .[...] variant)
    new_text = re.sub(r'pip install -e "\.\[[^\]]+\]"', editable_install, text)
    changed = changed or (new_text != text)
    text = new_text

    # 2. CLI quick-reference block (marker-based, idempotent)
    if cli_help:
        quick_ref_body = f"## Quick Reference\n\nThe complete `gaia --help` output:\n\n{cli_help}"
        text, did = _replace_region(
            text,
            "<!-- gaia:cli-start -->",
            "<!-- gaia:cli-end -->",
            quick_ref_body,
        )
        changed = changed or did

    return text, changed


def _update_initiates_rite(text: str, editable_install: str) -> tuple[str, bool]:
    """Fix editable install extra."""
    new_text = re.sub(r'pip install -e "\.\[[^\]]+\]"', editable_install, text)
    return new_text, new_text != text


# ─── page registry ────────────────────────────────────────────────────────────

def _make_updaters(version: str, cli_help: str, editable_install: str) -> dict:
    return {
        "Home.md": lambda t: _update_home(t, version),
        "CLI-Reference.md": lambda t: _update_cli_reference(t, cli_help, editable_install),
        "Initiates-Rite.md": lambda t: _update_initiates_rite(t, editable_install),
    }


# ─── git helpers ──────────────────────────────────────────────────────────────


def _git(wiki_dir: Path, *cmd: str) -> int:
    return subprocess.run(["git", *cmd], cwd=wiki_dir).returncode


def _push_wiki(wiki_dir: Path, version: str, pages: list[str]) -> int:
    _git(wiki_dir, "config", "user.name", "github-actions[bot]")
    _git(wiki_dir, "config", "user.email", "github-actions[bot]@users.noreply.github.com")

    rc = _git(wiki_dir, "add", *pages)
    if rc != 0:
        print(f"[wiki-sync] git add failed (rc={rc})", file=sys.stderr)
        return rc

    # Check whether there are staged changes before committing
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=wiki_dir,
    )
    if result.returncode == 0:
        print("[wiki-sync] No wiki changes to commit — already in sync.")
        return 0

    rc = _git(
        wiki_dir,
        "commit",
        "-m",
        f"docs: sync wiki pages from gaia docs build (v{version})",
    )
    if rc != 0:
        print(f"[wiki-sync] git commit failed (rc={rc})", file=sys.stderr)
        return rc

    rc = _git(wiki_dir, "push", "origin", "master")
    if rc != 0:
        print(
            "[wiki-sync] git push failed — check WIKI_PAT / wiki remote credentials.",
            file=sys.stderr,
        )
        return rc

    print(f"[wiki-sync] Wiki pushed to master (v{version}).")
    return 0


# ─── main ─────────────────────────────────────────────────────────────────────


def sync(wiki_dir: Path, check: bool, push: bool) -> int:
    if not wiki_dir.exists():
        print(f"[wiki-sync] Wiki dir not found ({wiki_dir}). Skipping.")
        return 0

    readme = README.read_text(encoding="utf-8")
    version = _readme_version(readme)
    cli_help = _readme_cli_help(readme)
    editable_install = _readme_editable_install(readme)

    updaters = _make_updaters(version, cli_help, editable_install)
    changed_pages: list[str] = []

    for page_name, updater in updaters.items():
        page_path = wiki_dir / page_name
        if not page_path.exists():
            print(f"[wiki-sync] skip {page_name} (not found in wiki)")
            continue

        original = page_path.read_text(encoding="utf-8")
        updated, changed = updater(original)

        if not changed:
            print(f"[wiki-sync] ok   {page_name}")
            continue

        changed_pages.append(page_name)
        if check:
            print(f"[wiki-sync] diff {page_name}")
        else:
            page_path.write_text(updated, encoding="utf-8")
            print(f"[wiki-sync] wrote {page_name}")

    if not changed_pages:
        print("[wiki-sync] Wiki pages are up to date.")
        return 0

    if check:
        print(
            "[wiki-sync] Wiki pages are stale. Run `python scripts/sync_wiki.py` to fix."
        )
        return 1

    if push:
        return _push_wiki(wiki_dir, version, changed_pages)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--wiki-dir",
        type=Path,
        default=ROOT.parent / "gaia-wiki",
        metavar="PATH",
        help="Path to the cloned wiki repo (default: ../gaia-wiki)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift without writing (exit 1 if stale)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="git commit + push to wiki master after writing",
    )
    args = parser.parse_args(argv)
    return sync(args.wiki_dir, args.check, args.push)


if __name__ == "__main__":
    raise SystemExit(main())
