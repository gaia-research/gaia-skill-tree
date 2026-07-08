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

    Fetches the GitHub tree for ``{owner}/{repo}`` at ``{tag}`` and lists
    directory names under ``{component_root}/`` (default ``"skills"``).

    Each upstream directory slug is compared against the slugs of
    ``current_components`` (which are ``contributor/slug`` pairs — we
    extract the slug part, i.e. the last path component).

    Returns ``(adds, removes)`` where each is a list of slug strings.

    Notes
    -----
    - Returns ``([], [])`` if the tree API call fails.
    - Does NOT attempt to resolve ``contributor/`` for add proposals — that
      is the issuer's job (it knows the suite's contributor).
    """
    # Fetch the tree at tag depth=1 to list top-level items
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tag}"
    tree_data = fetch_json(tree_url)

    if not tree_data:
        print(
            f"  [warn] Could not fetch tree for {owner}/{repo}@{tag}",
            file=sys.stderr,
        )
        return ([], [])

    # Collect subdirectory names under component_root
    component_root_norm = component_root.strip("/")
    upstream_slugs: set[str] = set()

    # First, try to find the component_root subtree in the top-level tree
    component_root_sha = None
    for item in tree_data.get("tree", []):
        if item.get("path") == component_root_norm and item.get("type") == "tree":
            component_root_sha = item.get("sha")
            break

    if component_root_sha:
        # Fetch the subtree for the component root
        subtree_url = (
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{component_root_sha}"
        )
        subtree_data = fetch_json(subtree_url)
        if subtree_data:
            for item in subtree_data.get("tree", []):
                if item.get("type") == "tree":
                    upstream_slugs.add(item["path"])
    else:
        # component_root not found in tree — version-only fallback
        return ([], [])

    # Build current slug set from suiteComponents (extract last segment)
    current_slugs: set[str] = set()
    for comp_id in current_components:
        # comp_id is like "owner/slug" — take the last part
        slug = comp_id.split("/")[-1] if "/" in comp_id else comp_id
        current_slugs.add(slug)

    adds = sorted(upstream_slugs - current_slugs)
    removes = sorted(current_slugs - upstream_slugs)

    return (adds, removes)
