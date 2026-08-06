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

import re
import sys
from typing import Any

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

    for comp_id in components:
        comp_fm = registry_map.get(comp_id)
        if not comp_fm:
            continue
        gh_url = (comp_fm.get("links") or {}).get("github", "")
        if not gh_url:
            continue

        raw_url = blob_to_raw(gh_url)
        content = fetch_text(raw_url)
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
