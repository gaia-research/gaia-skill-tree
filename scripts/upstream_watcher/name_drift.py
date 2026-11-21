"""
scripts.upstream_watcher.name_drift — SKILL.md frontmatter name-drift detection.

Issue #1457: catch registry-slug / upstream-name divergence at watcher time,
before it has to wait for a periodic ``scripts/install_parity.py`` sweep to
surface it as ``DIRNAME_MISMATCH``.

Per issue #1446 (Option A, settled): the registry slug is authoritative, and
the fix for a divergence is always ``gaia dev rename <old-id> <new-id>`` — the
watcher never proposes adopting the upstream name automatically.

Public API
----------
sanitize_name(name)
    Mirror the ``skills`` npm CLI's ``sanitizeName()`` (vendored algorithm,
    see module docstring below) so the comparison uses the exact same
    directory-name derivation ``npx skills add`` and ``install_parity.py``
    already use.

check_name_drift(components, registry_map)
    For each tracked component, fetch its upstream SKILL.md, sanitize the
    frontmatter ``name``, and compare it against the registry slug.  Returns
    a list of drift dicts — empty when every component's slug still matches.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import sys
from typing import Any, Mapping, Sequence

import yaml

from scripts.lib.frontmatter import load_yaml_simple, split_frontmatter
from scripts.lib.github_api import fetch_text
from scripts.upstream_watcher.liveness import blob_to_raw

# ---------------------------------------------------------------------------
# sanitizeName — vendored from the `skills` npm package (dist/cli.mjs, v1.5.22)
# ---------------------------------------------------------------------------
#
# function sanitizeName(name) {
#     return name.toLowerCase()
#         .replace(/[^a-z0-9._]+/g, "-")
#         .replace(/^[.\-]+|[.\-]+$/g, "")
#         .substring(0, 255) || "unnamed-skill";
# }
#
# This is the exact function `npx skills add` uses to derive an installed
# directory name from SKILL.md frontmatter `name`, and the one
# `scripts/install_parity.py`'s DIRNAME_MISMATCH check is judged against
# (see docs/agents/install-parity.md "dir name from" table). Ported here so
# the watcher can run the same comparison without shelling out to npx on
# every poll.

_SANITIZE_INVALID_RE = re.compile(r"[^a-z0-9._]+")
_SANITIZE_TRIM_RE = re.compile(r"^[.\-]+|[.\-]+$")


def sanitize_name(name: str) -> str:
    """Return the installed directory name the `skills` npm CLI would derive.

    Mirrors ``sanitizeName()`` from the ``skills`` package verbatim: lowercase,
    collapse runs of non-``[a-z0-9._]`` characters to a single hyphen, trim
    leading/trailing dots and hyphens, cap at 255 chars, and fall back to
    ``"unnamed-skill"`` if the result is empty.
    """
    s = name.lower()
    s = _SANITIZE_INVALID_RE.sub("-", s)
    s = _SANITIZE_TRIM_RE.sub("", s)
    s = s[:255]
    return s or "unnamed-skill"


# ---------------------------------------------------------------------------
# Name-drift detection
# ---------------------------------------------------------------------------


def check_name_drift(
    components: list[str],
    registry_map: dict[str, dict],
    *,
    fetch_text_fn: Any = None,
) -> list[dict[str, Any]]:
    """Compare each component's registry slug against its sanitized upstream name.

    For every ``comp_id`` in *components*, fetches the component's SKILL.md
    (via ``links.github``, converted to a raw URL), parses the frontmatter
    ``name`` field, and runs it through :func:`sanitize_name`.  If the result
    disagrees with the registry slug (the last path segment of ``comp_id``),
    a drift record is appended.

    A component is skipped — not counted as drift — when it is missing from
    *registry_map*, has no ``links.github``, the fetch fails, the file has no
    frontmatter, or the frontmatter has no ``name`` field.  This mirrors
    :func:`scripts.upstream_watcher.liveness.check_component_liveness`'s
    skip-on-missing-data behavior: absence of a signal is not evidence of a
    divergence.

    Returns
    -------
    list[dict]
        Each dict has keys ``skillId``, ``registrySlug``, ``upstreamName``,
        ``sanitizedName``, and ``fixCommand`` (the exact
        ``gaia dev rename <old-id> <new-id>`` text a reviewer should run).
        Empty list when no component has drifted.
    """
    drift: list[dict[str, Any]] = []
    fetcher = fetch_text_fn if fetch_text_fn is not None else fetch_text

    for comp_id in components:
        comp_fm = registry_map.get(comp_id)
        if not comp_fm:
            continue
        gh_url = (comp_fm.get("links") or {}).get("github", "")
        if not gh_url:
            continue

        raw_url = blob_to_raw(gh_url)
        content = fetcher(raw_url)
        if not content:
            continue

        _, fm_raw, _ = split_frontmatter(content)
        if not fm_raw:
            continue

        try:
            upstream_fm = load_yaml_simple(fm_raw)
        except Exception as exc:  # noqa: BLE001
            print(
                f"  [warn] {comp_id} — could not parse upstream SKILL.md frontmatter: {exc}",
                file=sys.stderr,
            )
            continue

        upstream_name = upstream_fm.get("name") if isinstance(upstream_fm, dict) else None
        if not upstream_name:
            continue

        sanitized = sanitize_name(str(upstream_name))
        registry_slug = comp_id.split("/")[-1] if "/" in comp_id else comp_id

        if sanitized == registry_slug:
            continue

        contributor = comp_id.split("/")[0] if "/" in comp_id else comp_id
        new_id = f"{contributor}/{sanitized}"

        drift.append(
            {
                "skillId": comp_id,
                "registrySlug": registry_slug,
                "upstreamName": str(upstream_name),
                "sanitizedName": sanitized,
                "fixCommand": f"gaia dev rename {comp_id} {new_id}",
            }
        )

    return drift


# ---------------------------------------------------------------------------
# Hosted-only bounded, silent name-drift verification
# ---------------------------------------------------------------------------

MAX_HOSTED_SKILL_MD_CHARS = 256 * 1024
MAX_HOSTED_FRONTMATTER_CHARS = 16 * 1024
MAX_HOSTED_FRONTMATTER_LINES = 256
MAX_HOSTED_YAML_EVENTS = 1024
MAX_HOSTED_NAME_LEN = 255

_COMPONENT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_HAS_ALNUM_RE = re.compile(r"[A-Za-z0-9]")

HOSTED_NAME_DRIFT_UNKNOWN_REASONS = frozenset({
    "invalid-component-id",
    "missing-registry-entry",
    "missing-github-link",
    "invalid-raw-url",
    "fetch-failed",
    "content-too-large",
    "invalid-utf8-replacement",
    "missing-frontmatter",
    "frontmatter-too-large",
    "malformed-frontmatter",
    "missing-upstream-name",
    "invalid-upstream-name",
})


@dataclass(frozen=True)
class HostedNameDriftResult:
    """Redacted hosted-only name-drift outcome: local named IDs and allowlisted codes only.

    Never carries upstream names, sanitized names, URLs, exception strings,
    parse excerpts, or reviewer fix instructions.
    """

    verified_unchanged: tuple[str, ...]
    verified_drift: tuple[str, ...]
    unknown: tuple[tuple[str, str], ...]

    @property
    def complete(self) -> bool:
        return len(self.unknown) == 0

    @property
    def status(self) -> str:
        return "verified" if self.complete else "unknown"


class _HostedUniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _HostedUniqueKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in mapping:
            raise yaml.constructor.ConstructorError("duplicate-or-nonstring-key")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_HostedUniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _parse_hosted_frontmatter(fm_raw: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse bounded YAML frontmatter silently without anchors, aliases, tags, or duplicate keys."""
    if len(fm_raw) > MAX_HOSTED_FRONTMATTER_CHARS:
        return None, "frontmatter-too-large"
    if fm_raw.count("\n") >= MAX_HOSTED_FRONTMATTER_LINES:
        return None, "frontmatter-too-large"
    if "\x00" in fm_raw:
        return None, "malformed-frontmatter"
    if "\ufffd" in fm_raw:
        return None, "invalid-utf8-replacement"

    try:
        doc_count = 0
        event_count = 0
        for ev in yaml.parse(fm_raw, Loader=yaml.SafeLoader):
            event_count += 1
            if event_count > MAX_HOSTED_YAML_EVENTS:
                return None, "frontmatter-too-large"
            if isinstance(ev, yaml.DocumentStartEvent):
                doc_count += 1
                if doc_count > 1:
                    return None, "malformed-frontmatter"
            if isinstance(ev, yaml.AliasEvent):
                return None, "malformed-frontmatter"
            if getattr(ev, "anchor", None) is not None:
                return None, "malformed-frontmatter"
            if getattr(ev, "tag", None) is not None:
                return None, "malformed-frontmatter"
        parsed = yaml.load(fm_raw, Loader=_HostedUniqueKeySafeLoader)
    except Exception:  # noqa: BLE001 — never log or propagate untrusted parse excerpts
        return None, "malformed-frontmatter"

    if not isinstance(parsed, dict):
        return None, "malformed-frontmatter"
    return parsed, None


def _is_valid_hosted_upstream_name(value: Any) -> bool:
    if type(value) is not str:
        return False
    if not value or len(value) > MAX_HOSTED_NAME_LEN:
        return False
    if any(ord(c) < 32 or ord(c) == 127 or c == "\ufffd" for c in value):
        return False
    if not value.strip() or not _HAS_ALNUM_RE.search(value):
        return False
    return True


def check_name_drift_hosted(
    components: Sequence[str],
    registry_map: Mapping[str, Mapping[str, Any]],
    *,
    fetch_text_fn: Any,
) -> HostedNameDriftResult:
    """Hosted-only bounded name-drift verification with explicit unknown classification.

    Reuses :func:`sanitize_name` without altering ordinary watcher semantics.
    Never logs to stdout/stderr and never retains upstream text, URLs,
    exception strings, parse excerpts, or fix instructions.
    """
    unchanged: set[str] = set()
    drifted: set[str] = set()
    unknown: dict[str, str] = {}

    for comp_id in components:
        if not isinstance(comp_id, str) or not _COMPONENT_ID_RE.fullmatch(comp_id):
            unknown["?"] = "invalid-component-id"
            continue

        comp_fm = registry_map.get(comp_id)
        if not isinstance(comp_fm, Mapping) or comp_fm.get("id") != comp_id:
            unknown[comp_id] = "missing-registry-entry"
            continue

        links = comp_fm.get("links")
        gh_url = links.get("github") if isinstance(links, Mapping) else None
        if not isinstance(gh_url, str) or not gh_url:
            unknown[comp_id] = "missing-github-link"
            continue

        raw_url = blob_to_raw(gh_url)
        if not isinstance(raw_url, str) or not raw_url.startswith("https://raw.githubusercontent.com/"):
            unknown[comp_id] = "invalid-raw-url"
            continue

        try:
            content = fetch_text_fn(raw_url)
        except Exception:  # noqa: BLE001 — never log untrusted fetch diagnostics
            unknown[comp_id] = "fetch-failed"
            continue

        if not isinstance(content, str) or not content:
            unknown[comp_id] = "fetch-failed"
            continue
        if len(content) > MAX_HOSTED_SKILL_MD_CHARS:
            unknown[comp_id] = "content-too-large"
            continue

        _, fm_raw, _ = split_frontmatter(content)
        if not fm_raw or not fm_raw.strip():
            unknown[comp_id] = "missing-frontmatter"
            continue

        upstream_fm, fm_err = _parse_hosted_frontmatter(fm_raw)
        if fm_err is not None or upstream_fm is None:
            unknown[comp_id] = fm_err or "malformed-frontmatter"
            continue

        if "name" not in upstream_fm or upstream_fm["name"] is None:
            unknown[comp_id] = "missing-upstream-name"
            continue

        upstream_name = upstream_fm["name"]
        if not _is_valid_hosted_upstream_name(upstream_name):
            unknown[comp_id] = "invalid-upstream-name"
            continue

        sanitized = sanitize_name(upstream_name)
        registry_slug = comp_id.split("/")[-1] if "/" in comp_id else comp_id
        if sanitized == registry_slug:
            unchanged.add(comp_id)
        else:
            drifted.add(comp_id)

    return HostedNameDriftResult(
        verified_unchanged=tuple(sorted(unchanged)),
        verified_drift=tuple(sorted(drifted)),
        unknown=tuple(sorted(unknown.items())),
    )
