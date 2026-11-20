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

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from scripts.lib.github_api import GitHubFetchError, fetch_json, head_check, is_permanent_unavailable
from scripts.upstream_watcher.envelope import MAX_ROWS
from scripts.upstream_watcher.live import SuiteUnavailable, UnknownEvidenceError, retry_transient, unknown_read_detail

# C9 (H-B): the requests a truncated tree's directory walk may make for one suite. Exhausting the budget makes the
# suite unavailable (tree-truncated), so one large suite can never stop the other suites.
TREE_REQUEST_BUDGET = 200

_SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_VALID_TREE_TYPES = frozenset({"blob", "tree", "commit"})


def _is_valid_component_root(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if value.startswith("/") or value.endswith("/") or "\\" in value:
        return False
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    segments = value.split("/")
    return not any(not seg or seg in (".", "..") for seg in segments)


def _has_control_char(value: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in value)


def _has_malformed_path_segment(path: str) -> bool:
    segments = path.split("/")
    return any(not seg or seg in (".", "..") for seg in segments)


def _could_alias_component_root(path: str, component_root: str) -> bool:
    """Return True if a suspicious path could alias or traverse ``component_root``.

    Never used to accept or normalize paths — used solely to refuse inventory
    proof when a backslash or control-character path could cross the root.
    """
    cleaned = "".join(c for c in path if ord(c) >= 32 and ord(c) != 127).replace("\\", "/")
    root_parts = tuple(component_root.split("/"))
    raw_tokens = [seg for seg in cleaned.split("/") if seg]
    if not raw_tokens:
        return False
    if tuple(raw_tokens[: len(root_parts)]) == root_parts:
        return True
    stack: list[str] = []
    for seg in raw_tokens:
        if seg == ".":
            continue
        if seg == "..":
            if stack:
                stack.pop()
            continue
        stack.append(seg)
        if tuple(stack[: len(root_parts)]) == root_parts:
            return True
    if tuple(stack[: len(root_parts)]) == root_parts:
        return True
    if stack and len(stack) < len(root_parts) and tuple(stack) == root_parts[: len(stack)]:
        return True
    return False


@dataclass(frozen=True)
class ComponentTreeEnumeration:
    """Single-read component diff plus explicit complete-inventory provenance.

    ``present_slugs`` is populated ONLY when ``complete=True``, ``truncated=False``,
    ``root_verified=True``, and ``proof_reason is None``. Any missing root,
    truncation, malformed entry, submodule under the root, or ambiguous slug path
    leaves ``present_slugs=None`` and ``complete=False`` so callers never infer
    absence from partial or fallback diffs.
    """

    adds: tuple[str, ...]
    removes: tuple[str, ...]
    present_slugs: frozenset[str] | None
    component_root: str
    tree_sha: str | None
    complete: bool = False
    truncated: bool = True
    root_verified: bool = False
    proof_reason: str | None = "unverified"

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
    *,
    head_check_fn: Any = None,
) -> list[dict[str, Any]]:
    """HEAD-check each component's ``links.github`` URL.

    Returns a list of dicts: ``{skillId, url, rawUrl, status}`` for any
    component whose check returns a non-2xx status or None (network error).

    2xx responses are omitted from the return value (they are healthy).
    """
    broken: list[dict[str, Any]] = []
    check = head_check_fn if head_check_fn is not None else head_check

    for comp_id in components:
        comp_fm = registry_map.get(comp_id)
        if not comp_fm:
            continue
        gh_url = (comp_fm.get("links") or {}).get("github", "")
        if not gh_url:
            continue

        raw_url = blob_to_raw(gh_url)
        status = check(raw_url)

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


def enumerate_component_tree(
    owner: str,
    repo: str,
    tag: str,
    component_root: str,
    current_components: list[str],
    *,
    _legacy_malformed_blob_exc: bool = False,
    fetch_json_fn: Any = None,
) -> ComponentTreeEnumeration:
    """Fetch the release tree once and return both raw slug diff and inventory provenance.

    Preserves the exact fetch, retry, error, truncated-walk, and missing-root fallback
    semantics of :func:`fetch_component_diff`, while also recording whether the single
    recursive tree response proves complete, non-truncated, unambiguous entry coverage
    for ``component_root``.

    Positive complete-inventory proof is NEVER claimed on truncated trees (even when
    :func:`walk_truncated_tree` succeeds for the raw diff), missing/invalid/ambiguous
    roots, missing tree SHAs, omitted/non-false truncation flags, malformed or duplicate
    entries, git submodules under ``component_root``, invalid slugs, or multiple
    ``SKILL.md`` paths collapsing to the same slug.
    """
    # Fetch the whole tree recursively in one call so nested component
    # directories at any depth are visible.
    # D11: the tag is percent-encoded whole. An unencoded '#' (or '?') cut the URL before ?recursive=1, and a
    # non-recursive tree then looked like removed components.
    fetcher = fetch_json_fn if fetch_json_fn is not None else fetch_json
    tree_url = f"{tree_base_url(owner, repo)}/{quote(tag, safe='')}?recursive=1"
    try:
        tree_data = retry_transient(lambda: fetcher(tree_url, strict=True))
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
    raw_sha = tree_data.get("sha")
    tree_sha = raw_sha if isinstance(raw_sha, str) and raw_sha else None
    if not tree_items and tree_sha is None:
        raise UnknownEvidenceError(
            f"tree for {owner}/{repo}@{tag} is empty and does not identify a resolved tree"
        )

    if tree_data.get("truncated"):
        # C9 (H-B): a truncated listing is a condition of this suite, not of the run. Read the root directly.
        # Conservative unknown for complete-inventory proof: truncated trees never claim complete proof here.
        adds, removes = walk_truncated_tree(
            owner,
            repo,
            tag,
            component_root,
            current_components,
            fetch_json_fn=fetch_json_fn,
        )
        return ComponentTreeEnumeration(
            adds=tuple(adds),
            removes=tuple(removes),
            present_slugs=None,
            component_root=component_root,
            tree_sha=tree_sha,
            complete=False,
            truncated=True,
            root_verified=False,
            proof_reason="tree-truncated",
        )

    truncated_is_false = tree_data.get("truncated") is False
    component_root_norm = component_root.strip("/")
    prefix = f"{component_root_norm}/"

    root_present = any(
        item.get("path") == component_root_norm and item.get("type") == "tree"
        for item in tree_items
    )
    if not root_present:
        # component_root not found in tree — version-only fallback (never proves absence)
        return ComponentTreeEnumeration(
            adds=(),
            removes=(),
            present_slugs=None,
            component_root=component_root,
            tree_sha=tree_sha,
            complete=False,
            truncated=not truncated_is_false,
            root_verified=False,
            proof_reason="missing-component-root",
        )

    proof_reason: str | None = None
    if not truncated_is_false:
        proof_reason = "truncation-flag-not-false"
    elif tree_sha is None:
        proof_reason = "missing-tree-sha"
    elif not _is_valid_component_root(component_root):
        proof_reason = "invalid-component-root"

    # Walk every SKILL.md blob under component_root and take its immediate
    # parent directory name as the component slug, regardless of nesting
    # depth. Simultaneously verify complete-inventory proof invariants over the
    # exact same listing without making a second request.
    upstream_slugs: set[str] = set()
    path_types: dict[str, str] = {}
    slug_paths: dict[str, str] = {}
    for item in tree_items:
        item_path = item.get("path")
        item_type = item.get("type")

        if item_type == "blob":
            raw_blob_path = item.get("path", "")
            if not isinstance(raw_blob_path, str):
                if _legacy_malformed_blob_exc:
                    # Preserve pinned-parent AttributeError on non-string blob path.
                    raw_blob_path.startswith(prefix)
                raise UnknownEvidenceError(
                    f"tree for {owner}/{repo}@{tag} has malformed non-string blob path"
                )
            if raw_blob_path.startswith(prefix) and raw_blob_path.endswith("/SKILL.md"):
                rel = raw_blob_path[len(prefix):]
                parts = rel.split("/")
                if len(parts) >= 2:
                    slug = parts[-2]
                    upstream_slugs.add(slug)
                    if proof_reason is None:
                        if not _SLUG_RE.fullmatch(slug):
                            proof_reason = "invalid-slug"
                        elif slug in slug_paths and slug_paths[slug] != raw_blob_path:
                            proof_reason = "ambiguous-slug-path"
                        else:
                            slug_paths[slug] = raw_blob_path

        if proof_reason is None:
            if (
                not isinstance(item_path, str)
                or not item_path
                or not isinstance(item_type, str)
                or item_type not in _VALID_TREE_TYPES
            ):
                proof_reason = "malformed-tree-entry"
            elif item_path in path_types:
                proof_reason = "duplicate-tree-path"
            else:
                path_types[item_path] = item_type
                if item_path.startswith(prefix) and item_type == "commit":
                    proof_reason = "submodule-under-root"

    # Order-independent canonical path and tree-topology validation over the
    # full listing map before claiming positive complete-inventory proof.
    if proof_reason is None:
        for entry_path in path_types:
            if _has_malformed_path_segment(entry_path):
                proof_reason = "malformed-tree-path"
                break
            if ("\\" in entry_path or _has_control_char(entry_path)) and (
                entry_path == component_root
                or entry_path.startswith(prefix)
                or _could_alias_component_root(entry_path, component_root)
            ):
                proof_reason = "malformed-tree-path"
                break

    if proof_reason is None:
        root_parts = component_root.split("/")
        for depth in range(1, len(root_parts) + 1):
            ancestor = "/".join(root_parts[:depth])
            ancestor_type = path_types.get(ancestor)
            if ancestor_type is None:
                proof_reason = "missing-ancestor-tree"
                break
            if ancestor_type != "tree":
                proof_reason = "non-tree-parent"
                break

    if proof_reason is None:
        root_depth = len(component_root.split("/"))
        for entry_path in path_types:
            if not entry_path.startswith(prefix):
                continue
            parts = entry_path.split("/")
            for depth in range(root_depth + 1, len(parts)):
                parent = "/".join(parts[:depth])
                parent_type = path_types.get(parent)
                if parent_type is None:
                    proof_reason = "missing-parent-tree"
                    break
                if parent_type != "tree":
                    proof_reason = "non-tree-parent"
                    break
            if proof_reason is not None:
                break

    if proof_reason is None and len(upstream_slugs) > MAX_ROWS:
        proof_reason = "too-many-slugs"

    adds, removes = diff_slugs(upstream_slugs, current_components)
    if proof_reason is not None:
        return ComponentTreeEnumeration(
            adds=tuple(adds),
            removes=tuple(removes),
            present_slugs=None,
            component_root=component_root,
            tree_sha=tree_sha,
            complete=False,
            truncated=not truncated_is_false,
            root_verified=False,
            proof_reason=proof_reason,
        )

    return ComponentTreeEnumeration(
        adds=tuple(adds),
        removes=tuple(removes),
        present_slugs=frozenset(upstream_slugs),
        component_root=component_root,
        tree_sha=tree_sha,
        complete=True,
        truncated=False,
        root_verified=True,
        proof_reason=None,
    )


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
    result = enumerate_component_tree(
        owner,
        repo,
        tag,
        component_root,
        current_components,
        _legacy_malformed_blob_exc=True,
    )
    return (list(result.adds), list(result.removes))


def truncated_unavailable(message: str) -> SuiteUnavailable:
    return SuiteUnavailable(f"tree is truncated and {message}", reason="tree-truncated")


def walk_truncated_tree(
    owner: str,
    repo: str,
    tag: str,
    component_root: str,
    current_components: list[str],
    *,
    fetch_json_fn: Any = None,
) -> tuple[list[str], list[str]]:
    """C9 (H-B): the component diff of a truncated tree, read one directory at a time.

    The recursive listing is cut short, so the component root is walked with non-recursive requests (GET
    git/trees/<sha>). The layout rules are those of the recursive read: a component is a directory at least one
    level under the root that holds a SKILL.md. The walk is bounded by TREE_REQUEST_BUDGET requests. Exhausting it,
    or a sub-call that still fails after its retries, makes the suite unavailable (tree-truncated).
    """
    fetcher = fetch_json_fn if fetch_json_fn is not None else fetch_json
    where = f"{owner}/{repo}@{tag}"
    base = tree_base_url(owner, repo)
    spent = [0]

    def listing(ref: str, path: str) -> list[dict]:
        if spent[0] >= TREE_REQUEST_BUDGET:
            raise truncated_unavailable(f"the directory walk of {where} exceeded its budget of {TREE_REQUEST_BUDGET} requests")
        spent[0] += 1
        url = f"{base}/{quote(ref, safe='')}"
        try:
            data = retry_transient(lambda: fetcher(url, strict=True))
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
