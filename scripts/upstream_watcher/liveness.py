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

from typing import Any
from urllib.parse import quote

from scripts.lib.github_api import GitHubFetchError, fetch_json, head_check, is_permanent_unavailable
from scripts.upstream_watcher.live import SuiteUnavailable, UnknownEvidenceError

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
    - Returns ``([], [])`` when ``component_root`` is not present in the upstream
      tree (version-only fallback). That is a real layout, not missing data.
    - Raises :class:`SuiteUnavailable` (H2) when GitHub refuses the tree for good (451, 410, or a 403 that is
      not rate limiting). The suite is skipped.
    - Raises :class:`UnknownEvidenceError` when the tree cannot be read (any other
      failure, including a 404 on a tag the release endpoint just returned) or
      is truncated. An unreadable or partial tree must never become an empty or
      partial diff, because that would derive false componentRemoves.
    - Does NOT attempt to resolve ``contributor/`` for add proposals — that
      is the issuer's job (it knows the suite's contributor).
    """
    # Fetch the whole tree recursively in one call so nested component
    # directories at any depth are visible.
    # D11: the tag is percent-encoded whole. An unencoded '#' (or '?') cut the URL before ?recursive=1, and a
    # non-recursive tree then looked like removed components.
    tree_url = (
        f"https://api.github.com/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"
        f"/git/trees/{quote(tag, safe='')}?recursive=1"
    )
    try:
        tree_data = fetch_json(tree_url, strict=True)
    except GitHubFetchError as exc:
        if is_permanent_unavailable(exc):
            # H2: a tree that is permanently unavailable skips the suite. It never becomes a removal.
            raise SuiteUnavailable(f"tree for {owner}/{repo}@{tag} is unavailable: {exc}") from exc
        raise UnknownEvidenceError(
            f"tree for {owner}/{repo}@{tag} could not be read: {exc}"
        ) from exc
    # M3: only a real tree object is evidence. {} or a response without a tree list is unknown, and so is
    # an entry that is not an object. An empty list is a legitimate tree only when the response
    # identifies a resolved tree (its sha): then the layout is version-only, not unknown.
    if not isinstance(tree_data, dict) or not tree_data:
        raise UnknownEvidenceError(f"tree for {owner}/{repo}@{tag} returned no usable data")
    tree_items = tree_data.get("tree")
    if not isinstance(tree_items, list) or any(not isinstance(item, dict) for item in tree_items):
        raise UnknownEvidenceError(f"tree for {owner}/{repo}@{tag} has no usable tree list")
    if not tree_items and not (isinstance(tree_data.get("sha"), str) and tree_data["sha"]):
        raise UnknownEvidenceError(
            f"tree for {owner}/{repo}@{tag} is empty and does not identify a resolved tree"
        )

    if tree_data.get("truncated"):
        raise UnknownEvidenceError(
            f"tree for {owner}/{repo}@{tag} was truncated by the GitHub API; "
            "the component diff would be partial"
        )

    component_root_norm = component_root.strip("/")
    prefix = f"{component_root_norm}/"

    root_present = any(
        item.get("path") == component_root_norm and item.get("type") == "tree"
        for item in tree_items
    )
    if not root_present:
        # component_root not found in tree — version-only fallback
        return ([], [])

    # Walk every SKILL.md blob under component_root and take its immediate
    # parent directory name as the component slug, regardless of nesting
    # depth.
    upstream_slugs: set[str] = set()
    for item in tree_items:
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
