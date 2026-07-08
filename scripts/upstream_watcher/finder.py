"""
scripts.upstream_watcher.finder — enumerate in-scope suite skills and detect
release findings (updates / bootstrap).

Separated from watcher.py to stay within the 500-line budget per design spec.

Public API
----------
iter_suite_skills()
    Yield (path, frontmatter) pairs for all in-scope named suites.

detect_mode(fm, registry_map)
    Auto-detect "components" vs "version-only" mode.

compute_finding(fm, release_data)
    Compare stored upstream.version against the live release; return a finding
    dict or None if the suite is up-to-date.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterator

from scripts.lib.github_api import parse_owner_repo
from scripts.lib.named_iterator import iter_named_skills

# ---------------------------------------------------------------------------
# Level parsing
# ---------------------------------------------------------------------------

_STAR_RE = re.compile(r"(\d+)[★\*]")


def _parse_star_level(level_str: str | None) -> int:
    """Return numeric star level from strings like '2★', '3*', etc."""
    if not level_str:
        return 0
    m = _STAR_RE.search(str(level_str))
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# Suite skill iteration
# ---------------------------------------------------------------------------


def iter_suite_skills(
    root: Path | None = None,
) -> Iterator[tuple[Path, dict]]:
    """Yield (path, frontmatter) for every in-scope named suite.

    In-scope means:
    - Has a non-empty ``suiteComponents`` list in frontmatter.
    - ``level >= 2★``.
    - Does NOT have ``watchUpstream: false``.
    """
    for path, fm in iter_named_skills(root=root):
        components = fm.get("suiteComponents")
        if not components:
            continue
        if _parse_star_level(fm.get("level")) < 2:
            if fm.get("level"):
                print(
                    f"  [skip] {fm.get('id')} — below 2★ ({fm.get('level')})",
                    file=sys.stderr,
                )
            continue
        if fm.get("watchUpstream") is False:
            print(
                f"  [skip] {fm.get('id')} — watchUpstream: false",
                file=sys.stderr,
            )
            continue
        yield path, fm


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------


def detect_mode(fm: dict, registry_map: dict[str, dict]) -> str:
    """Auto-detect watcher mode.

    Returns ``"components"`` if *every* suite component has a ``links.github``
    URL that resolves to a subpath within the same owner/repo as the suite
    itself.  Returns ``"version-only"`` otherwise.

    Parameters
    ----------
    fm:
        Suite frontmatter dict (must have ``links.github`` and
        ``suiteComponents``).
    registry_map:
        Dict mapping skill-id → frontmatter for all known named skills.
        Used to look up component ``links.github`` URLs.
    """
    suite_gh = (fm.get("links") or {}).get("github", "")
    suite_parsed = parse_owner_repo(suite_gh)
    if not suite_parsed:
        return "version-only"

    suite_owner, suite_repo = suite_parsed
    components = fm.get("suiteComponents") or []

    for comp_id in components:
        comp_fm = registry_map.get(comp_id)
        if not comp_fm:
            # Unknown component — can't verify; fall back to version-only
            return "version-only"
        comp_gh = (comp_fm.get("links") or {}).get("github", "")
        comp_parsed = parse_owner_repo(comp_gh)
        if not comp_parsed:
            return "version-only"
        comp_owner, comp_repo = comp_parsed
        if comp_owner != suite_owner or comp_repo != suite_repo:
            return "version-only"

    return "components"


# ---------------------------------------------------------------------------
# Finding computation
# ---------------------------------------------------------------------------


def compute_finding(fm: dict, release_data: dict) -> dict | None:
    """Compare stored upstream.version against a GitHub release payload.

    Returns a *finding* dict with ``finding_type`` of either ``"bootstrap"``
    (no stored upstream block) or ``"update"`` (version differs).  Returns
    ``None`` when the stored version equals the live release tag (up-to-date).

    Parameters
    ----------
    fm:
        Suite frontmatter dict.
    release_data:
        Parsed GitHub ``/releases/latest`` response.
    """
    skill_id = fm.get("id", "unknown")
    tag = release_data.get("tag_name", "")
    released_at = release_data.get("published_at", "")
    source_url = release_data.get("html_url", "")

    upstream_block = fm.get("upstream") or {}
    stored_version = upstream_block.get("version")

    if not stored_version:
        return {
            "finding_type": "bootstrap",
            "skillId": skill_id,
            "currentVersion": None,
            "newVersion": tag,
            "releasedAt": released_at,
            "sourceUrl": source_url,
        }

    if stored_version == tag:
        return None  # Up-to-date

    return {
        "finding_type": "update",
        "skillId": skill_id,
        "currentVersion": stored_version,
        "newVersion": tag,
        "releasedAt": released_at,
        "sourceUrl": source_url,
    }
