"""Schema validation helpers for the registry.

Implements validators wired into `gaia validate` for the v2 inheritance
contract (§ Section H.2, G7_HANDOVER_DELTA_2026-06-17.md, ratified 2026-06-18).
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Evidence-layer allowedLayers validator
# ---------------------------------------------------------------------------

def load_type_layer_policy(registry_path: str = ".") -> dict[str, dict]:
    """Return {type_id: {"allowedLayers": [...], "inheritMultiplier": float|None}}
    from meta.json evidence.types[].

    Used by check_evidence_layer_policy(). Returns an empty dict if meta.json
    is missing or malformed so callers degrade gracefully.
    """
    meta_path = os.path.join(registry_path, "registry", "schema", "meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        types = meta.get("evidence", {}).get("types", [])
        policy: dict[str, dict] = {}
        for entry in types:
            if not isinstance(entry, dict) or "id" not in entry:
                continue
            policy[entry["id"]] = {
                "allowedLayers": entry.get("allowedLayers", ["generic", "named"]),
                "inheritMultiplier": entry.get("inheritMultiplier"),
            }
        return policy
    except Exception:
        return {}


def check_evidence_layer_policy(
    skill: dict[str, Any],
    skill_layer: str,
    type_policy: dict[str, dict],
) -> list[dict]:
    """Check that every evidence row's effective layer is in its type's allowedLayers.

    Args:
        skill: A skill node dict (generic or named).
        skill_layer: "generic" or "named" -- the containing skill's layer. Used as
            the default when an evidence row has no explicit ``layer`` field.
        type_policy: Output of load_type_layer_policy().

    Returns:
        List of violation dicts. Each has keys:
            - error_code: "evidence-layer-not-allowed" (publish blocker)
            - skill_id: str
            - evidence_index: int
            - evidence_type: str
            - row_layer: str (effective layer of the row)
            - allowed_layers: list[str]
            - message: human-readable description

    # TODO (I3 partition-repair pass): pre-G7 rows lacking explicit `layer` are
    # assigned layer="named" conservatively (Section H.4). Post-I3, the migration
    # script emits explicit layer fields on every row so this fallback is only
    # needed during the transition window between I1 (schema) and I3 (migration).
    """
    violations: list[dict] = []
    evidence = skill.get("evidence") or []
    skill_id = skill.get("id", "<unknown>")

    for idx, row in enumerate(evidence):
        if not isinstance(row, dict):
            continue
        evidence_type = row.get("type")
        if not evidence_type or evidence_type not in type_policy:
            # Unknown type -- skip (separate validator handles unknown types).
            continue
        row_layer = row.get("layer", skill_layer)
        allowed = type_policy[evidence_type]["allowedLayers"]
        if row_layer not in allowed:
            violations.append({
                "error_code": "evidence-layer-not-allowed",
                "skill_id": skill_id,
                "evidence_index": idx,
                "evidence_type": evidence_type,
                "row_layer": row_layer,
                "allowed_layers": allowed,
                "message": (
                    f"Evidence row {idx} (type={evidence_type!r}) on skill {skill_id!r} "
                    f"has layer={row_layer!r} but type only allows {allowed}."
                ),
            })
    return violations


# ---------------------------------------------------------------------------
# Proxy-containment first-party rejection policy (#2473)
# ---------------------------------------------------------------------------

def normalize_github_repo(url: str | None) -> tuple[str, str] | None:
    """Return lowercase ``(owner, repo)`` for a GitHub URL, or ``None``."""
    if not url or not isinstance(url, str):
        return None
    raw = url.strip()
    if not raw:
        return None
    if raw.startswith("git+"):
        raw = raw[4:]
    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in {"github.com", "raw.githubusercontent.com"}:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None
    owner = parts[0].strip().lower()
    repo = parts[1].strip().lower()
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        return None
    return (owner, repo)


def _collect_first_party_repos(node: dict[str, Any]) -> set[tuple[str, str]]:
    repos: set[tuple[str, str]] = set()
    links = node.get("links")
    if isinstance(links, dict):
        for key in ("github", "repo", "canonicalRepo"):
            repo = normalize_github_repo(links.get(key))
            if repo is not None:
                repos.add(repo)
    top_canonical = normalize_github_repo(node.get("canonicalRepo"))
    if top_canonical is not None:
        repos.add(top_canonical)
    return repos


def check_proxy_containment_policy(
    skill: dict[str, Any],
    *,
    named_skills_by_id: dict[str, dict[str, Any]] | None = None,
    suite_skill: dict[str, Any] | None = None,
    require_external_stars: bool = False,
) -> list[dict[str, Any]]:
    """Reject demonstrably first-party or sub-floor ``proxy-containment`` rows.

    A ``proxy-containment`` row requires genuine containment in a qualifying
    external, non-first-party project with at least 10,000 external stars.
    It is rejected when:
      - the ``source`` GitHub repo owner/repo matches the skill's
        ``contributor``, its own ``links.github`` / ``links.repo`` /
        ``canonicalRepo``, or its referenced ``suiteRef`` capstone repo;
      - ``externalStars`` is supplied and is below ``10000``; or
      - ``require_external_stars=True`` and ``externalStars`` is missing.
    """
    violations: list[dict[str, Any]] = []
    evidence = skill.get("evidence") or []
    skill_id = skill.get("id", "<unknown>")

    first_party_owners: set[str] = set()
    contributor = skill.get("contributor")
    if isinstance(contributor, str) and contributor.strip():
        first_party_owners.add(contributor.strip().lower())

    first_party_repos = _collect_first_party_repos(skill)
    resolved_suite = suite_skill
    if resolved_suite is None and named_skills_by_id is not None:
        suite_ref = skill.get("suiteRef")
        if isinstance(suite_ref, str) and suite_ref in named_skills_by_id:
            resolved_suite = named_skills_by_id[suite_ref]
    if isinstance(resolved_suite, dict):
        first_party_repos |= _collect_first_party_repos(resolved_suite)

    for idx, row in enumerate(evidence):
        if not isinstance(row, dict) or row.get("type") != "proxy-containment":
            continue
        source = row.get("source")
        ext_stars = row.get("externalStars")
        if ext_stars is None:
            if require_external_stars:
                violations.append({
                    "error_code": "proxy-containment-missing-external-stars",
                    "skill_id": skill_id,
                    "evidence_index": idx,
                    "evidence_type": "proxy-containment",
                    "source": source,
                    "message": (
                        f"Evidence row {idx} (type='proxy-containment') on skill {skill_id!r} "
                        "is missing externalStars; proxy-containment requires externalStars >= 10000."
                    ),
                })
        elif (
            isinstance(ext_stars, bool)
            or not isinstance(ext_stars, (int, float))
            or ext_stars < 10_000
        ):
            violations.append({
                "error_code": "proxy-containment-below-star-floor",
                "skill_id": skill_id,
                "evidence_index": idx,
                "evidence_type": "proxy-containment",
                "source": source,
                "external_stars": ext_stars,
                "message": (
                    f"Evidence row {idx} (type='proxy-containment') on skill {skill_id!r} "
                    f"has externalStars={ext_stars!r}, below the 10,000 external-star floor."
                ),
            })

        source_repo = normalize_github_repo(source)
        if source_repo is None:
            continue

        matched_by: str | None = None
        if source_repo[0] in first_party_owners:
            matched_by = f"owner matches contributor {contributor!r}"
        elif source_repo in first_party_repos:
            matched_by = (
                f"repository {source_repo[0]}/{source_repo[1]} matches "
                "skill or suiteRef repository"
            )

        if matched_by is not None:
            violations.append({
                "error_code": "first-party-proxy-containment",
                "skill_id": skill_id,
                "evidence_index": idx,
                "evidence_type": "proxy-containment",
                "source": source,
                "source_repo": f"{source_repo[0]}/{source_repo[1]}",
                "matched_by": matched_by,
                "message": (
                    f"Evidence row {idx} (type='proxy-containment') on skill {skill_id!r} "
                    f"points to first-party repository {source_repo[0]}/{source_repo[1]} "
                    f"({matched_by}); proxy-containment requires an external, "
                    "non-first-party project."
                ),
            })

    return violations
