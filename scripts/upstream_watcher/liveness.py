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
from scripts.upstream_watcher.live import SuiteUnavailable, UnknownEvidenceError, retry_transient, unknown_read_detail

# C9 (H-B): the requests a truncated tree's directory walk may make for one suite. Exhausting the budget makes the
# suite unavailable (tree-truncated), so one large suite can never stop the other suites.
TREE_REQUEST_BUDGET = 200

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


def tree_base_url(owner: str, repo: str) -> str:
    return f"https://api.github.com/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/git/trees"


def diff_slugs(upstream_slugs: set[str], current_components: list[str]) -> tuple[list[str], list[str]]:
    """Adds and removes between the upstream slugs and the slugs of ``current_components`` (``owner/slug``)."""
    current_slugs: set[str] = set()
    for comp_id in current_components:
        # comp_id is like "owner/slug" — take the last part
        slug = comp_id.split("/")[-1] if "/" in comp_id else comp_id
        current_slugs.add(slug)

    adds = sorted(upstream_slugs - current_slugs)
    removes = sorted(current_slugs - upstream_slugs)
    return (adds, removes)


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
    - Raises :class:`SuiteUnavailable` (H2) when GitHub refuses the tree for good (451, 410, or a repo-refusal 403).
      The suite is skipped.
    - Raises :class:`UnknownEvidenceError` when the tree cannot be read after its retries (C9 H-B: transient
      failures get three attempts). An unreadable tree must never become an empty or partial diff, because that
      would derive false componentRemoves.
    - A truncated tree (C9 H-B) is read one directory at a time, within TREE_REQUEST_BUDGET requests. If the budget
      runs out, or a sub-call still fails, the suite is :class:`SuiteUnavailable` with ``reason="tree-truncated"``.
    - Does NOT attempt to resolve ``contributor/`` for add proposals — that
      is the issuer's job (it knows the suite's contributor).
    """
    # Fetch the whole tree recursively in one call so nested component
    # directories at any depth are visible.
    # D11: the tag is percent-encoded whole. An unencoded '#' (or '?') cut the URL before ?recursive=1, and a
    # non-recursive tree then looked like removed components.
    tree_url = f"{tree_base_url(owner, repo)}/{quote(tag, safe='')}?recursive=1"
    try:
        tree_data = retry_transient(lambda: fetch_json(tree_url, strict=True))
    except GitHubFetchError as exc:
        if is_permanent_unavailable(exc):
            # H2: a tree that is permanently unavailable skips the suite. It never becomes a removal.
            raise SuiteUnavailable(f"tree for {owner}/{repo}@{tag} is unavailable: {exc}") from exc
        raise UnknownEvidenceError(
            f"tree for {owner}/{repo}@{tag} could not be read: {exc}{unknown_read_detail(exc)}"
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
        # C9 (H-B): a truncated listing is a condition of this suite, not of the run. Read the root directly.
        return walk_truncated_tree(owner, repo, tag, component_root, current_components)

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

    return diff_slugs(upstream_slugs, current_components)


def truncated_unavailable(message: str) -> SuiteUnavailable:
    return SuiteUnavailable(f"tree is truncated and {message}", reason="tree-truncated")


def walk_truncated_tree(
    owner: str,
    repo: str,
    tag: str,
    component_root: str,
    current_components: list[str],
) -> tuple[list[str], list[str]]:
    """C9 (H-B): the component diff of a truncated tree, read one directory at a time.

    The recursive listing is cut short, so the component root is walked with non-recursive requests (GET
    git/trees/<sha>). The layout rules are those of the recursive read: a component is a directory at least one
    level under the root that holds a SKILL.md. The walk is bounded by TREE_REQUEST_BUDGET requests. Exhausting it,
    or a sub-call that still fails after its retries, makes the suite unavailable (tree-truncated).
    """
    where = f"{owner}/{repo}@{tag}"
    base = tree_base_url(owner, repo)
    spent = [0]

    def listing(ref: str, path: str) -> list[dict]:
        if spent[0] >= TREE_REQUEST_BUDGET:
            raise truncated_unavailable(f"the directory walk of {where} exceeded its budget of {TREE_REQUEST_BUDGET} requests")
        spent[0] += 1
        url = f"{base}/{quote(ref, safe='')}"
        try:
            data = retry_transient(lambda: fetch_json(url, strict=True))
        except GitHubFetchError as exc:
            raise truncated_unavailable(f"a directory read of {where} at '{path or '/'}' failed: {exc}") from exc
        items = data.get("tree") if isinstance(data, dict) else None
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise truncated_unavailable(f"a directory read of {where} at '{path or '/'}' returned no usable tree list")
        return items

    segments = [part for part in component_root.strip("/").split("/") if part]
    if not segments:
        return ([], [])
    items = listing(tag, "")
    walked = ""
    for segment in segments:
        walked = f"{walked}/{segment}" if walked else segment
        entry = next((item for item in items if item.get("path") == segment and item.get("type") == "tree"), None)
        if entry is None:
            # component_root is not in the upstream tree: a version-only layout, as in the recursive read.
            return ([], [])
        if not isinstance(entry.get("sha"), str) or not entry["sha"]:
            raise truncated_unavailable(f"the entry '{walked}' of {where} names no tree sha")
        items = listing(entry["sha"], walked)

    upstream_slugs: set[str] = set()
    # Each frame: (directory name, directory path, its listing, its depth under the component root).
    stack: list[tuple[str, str, list[dict], int]] = [(segments[-1], walked, items, 0)]
    while stack:
        name, path, entries, depth = stack.pop()
        if depth >= 1 and any(entry.get("type") == "blob" and entry.get("path") == "SKILL.md" for entry in entries):
            upstream_slugs.add(name)
        for entry in entries:
            if entry.get("type") != "tree":
                continue
            child = entry.get("path")
            if not isinstance(child, str) or not child or not isinstance(entry.get("sha"), str) or not entry["sha"]:
                raise truncated_unavailable(f"an entry under '{path}' of {where} is not a directory with a tree sha")
            child_path = f"{path}/{child}"
            stack.append((child, child_path, listing(entry["sha"], child_path), depth + 1))
    return diff_slugs(upstream_slugs, current_components)
