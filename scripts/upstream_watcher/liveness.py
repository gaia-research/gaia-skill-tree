"""
scripts.upstream_watcher.liveness — link-liveness checker.

Responsible for:
- Converting GitHub blob/ URLs to raw.githubusercontent.com equivalents.
- HEAD-checking each component's ``links.github`` URL.
- Computing component-directory diffs between an upstream release tree
  and the current ``suiteComponents`` list.

Public API
----------
blob_to_raw(url)
    Convert a ``github.com/.../blob/…`` URL to ``raw.githubusercontent.com``.

check_component_liveness(components, registry_map)
    HEAD-check each component's ``links.github`` URL.  Return list of dicts
    with ``{skillId, url, status}``.

fetch_component_diff(owner, repo, tag, component_root, current_components)
    Compare the upstream release tree against the current component list.
    Return ``(adds, removes)`` tuples as skill-id slugs.
"""

from __future__ import annotations

import sys
from typing import Any

from scripts.lib.github_api import fetch_json, head_check, parse_owner_repo

# ---------------------------------------------------------------------------
# URL conversion
# ---------------------------------------------------------------------------


def blob_to_raw(url: str) -> str:
    """Convert a GitHub blob URL to a raw.githubusercontent.com URL.

    ``https://github.com/owner/repo/blob/branch/path``
    → ``https://raw.githubusercontent.com/owner/repo/branch/path``

    Returns the input unchanged if it doesn't match the blob pattern.
    """
    if "github.com" not in url or "/blob/" not in url:
        return url
    raw = url.replace("https://github.com/", "https://raw.githubusercontent.com/")
    raw = raw.replace("/blob/", "/")
    return raw


# ---------------------------------------------------------------------------
# Link liveness
# ---------------------------------------------------------------------------


def check_component_liveness(
    components: list[str],
    registry_map: dict[str, dict],
) -> list[dict[str, Any]]:
    """HEAD-check each component's ``links.github`` URL.

    Returns a list of dicts: ``{skillId, url, rawUrl, status}`` for any
    component whose check returns a non-2xx status or None (network error).

    2xx responses are omitted from the return value (they are healthy).
    """
    broken: list[dict[str, Any]] = []

    for comp_id in components:
        comp_fm = registry_map.get(comp_id)
        if not comp_fm:
            continue
        gh_url = (comp_fm.get("links") or {}).get("github", "")
        if not gh_url:
            continue

        raw_url = blob_to_raw(gh_url)
        status = head_check(raw_url)

        if status is None:
            broken.append(
                {
                    "skillId": comp_id,
                    "url": gh_url,
                    "rawUrl": raw_url,
                    "status": "network_error",
                }
            )
        elif status < 200 or status >= 300:
            broken.append(
                {
                    "skillId": comp_id,
                    "url": gh_url,
                    "rawUrl": raw_url,
                    "status": status,
                }
            )

    return broken


# ---------------------------------------------------------------------------
# Component diff
# ---------------------------------------------------------------------------


def fetch_component_diff(
    owner: str,
    repo: str,
    tag: str,
    component_root: str,
    current_components: list[str],
) -> tuple[list[str], list[str]]:
    """Compare upstream release tree against current component list.

    Fetches the full recursive GitHub tree for ``{owner}/{repo}`` at ``{tag}``
    and walks every path under ``{component_root}/`` (default ``"skills"``)
    to find ``SKILL.md`` leaves at any depth — flat layouts
    (``skills/<slug>/SKILL.md``) and layouts nested under grouping
    directories (``skills/<category>/<slug>/SKILL.md``, e.g.
    ``mattpocock/skills``'s ``skills/engineering/`` and
    ``skills/productivity/`` categories). The component slug is the name of
    the directory immediately containing ``SKILL.md`` — the same convention
    flat suites already use to key slugs, so flat and nested layouts stay
    consistent.

    Grouping directories that carry no ``SKILL.md`` anywhere beneath them
    (e.g. ``deprecated/``, ``in-progress/``, ``misc/``) are never walked
    into a slug, so they never surface as false additions, and real nested
    slugs are found regardless of depth, so they never surface as false
    removals.

    Each upstream slug is compared against the slugs of
    ``current_components`` (which are ``contributor/slug`` pairs — we
    extract the slug part, i.e. the last path component).

    Returns ``(adds, removes)`` where each is a list of slug strings.

    Notes
    -----
    - Returns ``([], [])`` if the tree API call fails or ``component_root``
      is not present in the upstream tree (version-only fallback).
    - Does NOT attempt to resolve ``contributor/`` for add proposals — that
      is the issuer's job (it knows the suite's contributor).
    """
    # Fetch the whole tree recursively in one call so nested component
    # directories at any depth are visible.
    tree_url = (
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tag}?recursive=1"
    )
    tree_data = fetch_json(tree_url)

    if not tree_data:
        print(
            f"  [warn] Could not fetch tree for {owner}/{repo}@{tag}",
            file=sys.stderr,
        )
        return ([], [])

    if tree_data.get("truncated"):
        print(
            f"  [warn] Tree for {owner}/{repo}@{tag} was truncated by the "
            "GitHub API; component diff may be incomplete.",
            file=sys.stderr,
        )

    component_root_norm = component_root.strip("/")
    prefix = f"{component_root_norm}/"

    root_present = any(
        item.get("path") == component_root_norm and item.get("type") == "tree"
        for item in tree_data.get("tree", [])
    )
    if not root_present:
        # component_root not found in tree — version-only fallback
        return ([], [])

    # Walk every SKILL.md blob under component_root and take its immediate
    # parent directory name as the component slug, regardless of nesting
    # depth.
    upstream_slugs: set[str] = set()
    for item in tree_data.get("tree", []):
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        if not path.startswith(prefix) or not path.endswith("/SKILL.md"):
            continue
        rel = path[len(prefix):]
        parts = rel.split("/")
        if len(parts) < 2:
            # SKILL.md directly under component_root with no component dir
            continue
        upstream_slugs.add(parts[-2])

    # Build current slug set from suiteComponents (extract last segment)
    current_slugs: set[str] = set()
    for comp_id in current_components:
        # comp_id is like "owner/slug" — take the last part
        slug = comp_id.split("/")[-1] if "/" in comp_id else comp_id
        current_slugs.add(slug)

    adds = sorted(upstream_slugs - current_slugs)
    removes = sorted(current_slugs - upstream_slugs)

    return (adds, removes)
