#!/usr/bin/env python3
"""Gaia Badge Provisioning Planner (Issue #1817).

Deterministically analyzes docs/badges/registry.json to produce a reviewable,
idempotent campaign manifest for outbound README badge provisioning.

Rules & Invariants:
1. One repository -> one canonical Named Skill badge -> one exact deep link.
2. Canonical skill selection:
   - Exactly 1 skill for repo -> canonical.
   - Multiple skills, contributor topSkill in repo -> topSkill is canonical.
   - Multiple skills, topSkill not in repo, exactly 1 suite capstone in repo -> capstone is canonical (flagged for review).
   - Otherwise -> AMBIGUOUS / REVIEW.
3. Collisions & Exclusions:
   - Multiple contributors mapped to the same repo -> COLLISION / SKIP.
   - Repositories under gaia-research/ -> GAIA_OWNED / SKIP (excluded from external pilot).
4. Campaign Lifecycle & State Preservation:
   - Separates computed eligibility (PILOT_CANDIDATE, READY, REVIEW, SKIP)
     from outbound execution state (APPROVED, PR_OPEN, ADOPTED, DECLINED, OPTED_OUT).
   - Once a repository has been contacted or transitioned into an outbound state,
     replanning NEVER automatically reverts it to dispatchable states (READY / PILOT_CANDIDATE).
   - Prevents duplicate external dispatch and enforces valid transition gates.
5. Serving Contract & Ownership Notice:
   - When Honesty Mode is active (HONESTY_MODE=true in docs/badges/index.html),
     badge URLs route directly to static _assets/ SVGs.
   - The '?repo=' query parameter is retained solely for cache isolation and GitHub
     Camo proxy separation.
   - Static SVG delivery does NOT authenticate repository ownership (OAuth hardening
     is deferred to #494).
6. Fail-closed State Loading:
   - Corrupt, invalid, or unreadable manifests abort execution immediately
     instead of silently resetting campaign progress.
7. Upstream Reconciliation (Issue #2069, scripts/badge_reconcile.py):
   - `reconcile` is strictly read-only: it observes GitHub and emits receipt.json /
     receipt.md without touching the manifest.
   - `predispatch` is the MANDATORY gate immediately before any external PR: it
     reserves the repo, refreshes upstream PR + README evidence, checks ledger and
     approval, and refuses duplicates / terminal restrictions / ambiguous state.
   - `record-outcome --status PR_OPEN` requires the reservation token issued by a
     successful `predispatch` (admin recovery: --force).
   - Manifest writes are serialized with an advisory file lock and are atomic.
8. Contribution-channel policy (Issue #2074, scripts/badge_policy.py):
   - `reconcile` classifies each scoped repo as PR_ALLOWED / ISSUE_FIRST / NO_OUTREACH / UNKNOWN (fail closed)
     and `predispatch` refuses everything except PR_ALLOWED or ISSUE_FIRST with a verified maintainer approval.
   - `policy ...` is an offline, append-only, hash-chained ledger of channel/approval/closure events. It never
     contacts GitHub; the only proposal artifact is a local draft that is never sent.
   - `POLICY_HOLD` is a non-terminal lifecycle status for a PR closed under a repo policy; history is kept.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:  # imported as scripts.plan_badge_provisioning (tests) or run as a script
    from scripts import badge_policy as bp
    from scripts import badge_reconcile as br
except ImportError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts import badge_policy as bp
    from scripts import badge_reconcile as br

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = REPO_ROOT / "docs" / "badges" / "registry.json"
DEFAULT_MANIFEST = REPO_ROOT / "campaigns" / "badge-provisioning" / "manifest.json"
DEFAULT_BADGES_INDEX = REPO_ROOT / "docs" / "badges" / "index.html"
DEFAULT_POLICY_LEDGER = br.DEFAULT_POLICY_LEDGER
DEFAULT_DRAFT_DIR = DEFAULT_MANIFEST.parent / "drafts"
BASE_URL = "https://gaiaskilltree.com"

# The three founder-approved low-risk pilot candidates
PILOT_CANDIDATE_REPOS = {
    "pbakaus/impeccable",
    "safishamsi/graphify",
    "graphify-labs/graphify",
    "trailhq/graft",
}

# Known upstream repository migrations (old_repo -> new_repo)
# Used to preserve campaign history and state when a repository moves or renames.
REPO_MIGRATIONS = {
    "safishamsi/graphify": "Graphify-Labs/graphify",
}

PRESENTATION_TIERS = {
    "SINGLE",
    "COMPACT_ROW",
    "LABELED_SECTION",
    "CURATED_COLLECTION",
    "NONE",
}

LEGAL_STATUSES = {
    "PILOT_CANDIDATE",
    "READY",
    "REVIEW",
    "SKIP",
    "APPROVED",
    "PR_OPEN",
    "ADOPTED",
    "ALREADY_ADOPTED",
    "DECLINED",
    "OPTED_OUT",
    "NO_RESPONSE",
    "POLICY_HOLD",
}

OUTBOUND_STATES = {
    "POLICY_HOLD",
    "APPROVED",
    "PR_OPEN",
    "ADOPTED",
    "ALREADY_ADOPTED",
    "DECLINED",
    "OPTED_OUT",
    "NO_RESPONSE",
}

TERMINAL_STATES = {
    "ADOPTED",
    "ALREADY_ADOPTED",
    "DECLINED",
    "OPTED_OUT",
    "NO_RESPONSE",
}


def detect_honesty_mode(index_path: Path = DEFAULT_BADGES_INDEX) -> bool:
    """Reads HONESTY_MODE from docs/badges/index.html.

    Fails closed if the file is missing, unreadable, or contains ambiguous settings.
    """
    if not index_path.exists():
        raise FileNotFoundError(f"Badges index not found: {index_path}")

    try:
        content = index_path.read_text(encoding="utf-8")
    except Exception as e:
        raise OSError(f"Failed to read badges index at {index_path}: {e}") from e

    matches = re.findall(r"const\s+HONESTY_MODE\s*=\s*(true|false)\s*;", content)
    if len(matches) != 1:
        raise ValueError(
            f"Ambiguous or missing HONESTY_MODE in {index_path}: found {len(matches)} matches, expected 1."
        )

    return matches[0] == "true"


def generate_badge_url(handle: str, skill_file: str, repo: str, honesty_mode: bool) -> str:
    """Generates the canonical public badge URL matching Badge Bench.

    In Honesty Mode (static _assets serving), the path includes /_assets/.
    The ?repo= query parameter is retained in both modes for cache isolation.
    """
    if honesty_mode:
        return f"{BASE_URL}/badges/_assets/{handle}/{skill_file}?repo={repo}"
    return f"{BASE_URL}/badges/{handle}/{skill_file}?repo={repo}"


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Registry not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_existing_manifest(path: Path) -> dict[str, Any]:
    """Loads existing manifest from path.

    Fails closed: If the file exists, it MUST be valid JSON and contain a dictionary.
    Any parsing error, unreadable file, or invalid structure raises an error
    to prevent silent campaign resets.
    """
    if not path.exists():
        return {}

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        raise OSError(f"Failed to read manifest file at {path}: {e}") from e

    try:
        data = json.loads(content)
    except Exception as e:
        raise ValueError(f"Corrupt manifest JSON at {path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Invalid manifest structure in {path}: expected dict, got {type(data).__name__}")

    if "repositories" in data and not isinstance(data["repositories"], dict):
        raise ValueError(f"Invalid manifest structure in {path}: 'repositories' must be a dict")

    return data


def normalize_repo(repo: str) -> str:
    return repo.strip()


def derive_canonical_skill(
    handle: str,
    repo: str,
    cinfo: dict[str, Any],
    named_dict: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, str, str]:
    """Derives the canonical skill object, resolution strategy, and notes.

    Returns: (skill_obj, strategy, note)
    """
    skills_in_repo = cinfo.get("skillsByRepo", {}).get(repo, [])
    top_skill_id = cinfo.get("topSkill")

    if not skills_in_repo:
        return None, "NO_SKILLS", "No skills mapped to this repository"

    # Deduplicate while preserving order
    unique_skills_in_repo = list(dict.fromkeys(skills_in_repo))

    if len(unique_skills_in_repo) == 1:
        sid = unique_skills_in_repo[0]
        skill_obj = named_dict.get(sid)
        if skill_obj:
            return skill_obj, "SINGLE_SKILL", "Sole skill mapped to repository"
        return None, "MISSING_SKILL_DATA", f"Skill {sid} metadata missing"

    # Multiple skills in repo
    if top_skill_id in unique_skills_in_repo:
        skill_obj = named_dict.get(top_skill_id)
        if skill_obj:
            return skill_obj, "TOP_SKILL_MATCH", f"Matches contributor topSkill ({len(unique_skills_in_repo)} skills in repo)"
        return None, "MISSING_SKILL_DATA", f"Top skill {top_skill_id} metadata missing"

    # topSkill is in another repository. Check if there is a suite capstone in this repo.
    suites = [sid for sid in unique_skills_in_repo if named_dict.get(sid, {}).get("branch") == "suite"]
    if len(suites) == 1:
        capstone_id = suites[0]
        skill_obj = named_dict.get(capstone_id)
        if skill_obj:
            return skill_obj, "SUITE_CAPSTONE_PREFERENCE", (
                f"Preferred suite capstone {capstone_id} over cross-repo topSkill {top_skill_id} "
                f"({len(unique_skills_in_repo)} skills in repo)"
            )

    return None, "AMBIGUOUS", (
        f"Multiple skills ({len(unique_skills_in_repo)}) and contributor topSkill {top_skill_id} "
        f"belongs to another repo (suites found: {suites})"
    )


def resolve_eligible_skills(
    handle: str,
    repo: str,
    cinfo: dict[str, Any],
    named_dict: dict[str, dict[str, Any]],
    honesty_mode: bool,
    assets_root: Path | None = None,
    check_assets: bool = True,
) -> list[dict[str, Any]]:
    """Resolves and validates all distinct eligible Named Skills for a repository.

    Deduplicates by Named Skill ID and verifies SVG asset existence.
    Distinguishes separate Named Skills from alternate badge styles (e.g. seals).
    """
    if assets_root is None:
        assets_root = REPO_ROOT / "docs" / "badges" / "_assets"

    raw_skill_ids = cinfo.get("skillsByRepo", {}).get(repo, [])
    # Deduplicate while preserving original order
    seen_ids: set[str] = set()
    unique_ids: list[str] = []
    for sid in raw_skill_ids:
        if sid not in seen_ids:
            seen_ids.add(sid)
            unique_ids.append(sid)

    eligible: list[dict[str, Any]] = []
    for sid in unique_ids:
        sobj = named_dict.get(sid)
        if not sobj:
            # Metadata missing for mapped skill
            continue

        skill_name = sobj.get("name", sid)
        skill_rank = sobj.get("rank", 0)
        skill_branch = sobj.get("branch", "standard")
        skill_file = sobj.get("file", f"{sid.split('/')[-1]}.svg")

        # Verify asset exists if assets_root is provided and check_assets is enabled
        if check_assets and assets_root:
            asset_path = assets_root / handle / skill_file
            if not asset_path.exists():
                raise FileNotFoundError(
                    f"Missing SVG badge asset for skill '{sid}': {asset_path}"
                )

        badge_url = generate_badge_url(handle, skill_file, repo, honesty_mode)
        deep_link = f"{BASE_URL}/named/#explorer/{sid}"
        markdown = f"[![Gaia Skill: {skill_name}]({badge_url})]({deep_link})"
        html = f'<a href="{deep_link}"><img src="{badge_url}" alt="Gaia Skill: {skill_name}" /></a>'

        eligible.append({
            "id": sid,
            "name": skill_name,
            "rank": skill_rank,
            "branch": skill_branch,
            "file": skill_file,
            "badge_url": badge_url,
            "deep_link": deep_link,
            "markdown": markdown,
            "html": html,
        })

    return eligible


def determine_badge_presentation(
    eligible_skills: list[dict[str, Any]],
    canonical_skill: dict[str, Any] | None,
    handle: str,
) -> dict[str, Any]:
    """Applies canonical README presentation rules:

    - 1: Single Named Skill badge
    - 2–4: Compact row of distinct skill badges
    - 5–8: Small labeled badge section
    - 9+: Concise curated display and link to full recognized collection
    """
    count = len(eligible_skills)
    if count == 0:
        return {
            "tier": "NONE",
            "eligible_count": 0,
            "displayed_count": 0,
            "displayed_skill_ids": [],
            "offered_skill_ids": [],
            "is_curated_selection": False,
            "collection_link": None,
            "markdown": "",
            "html": "",
        }

    offered_ids = [s["id"] for s in eligible_skills]

    if count == 1:
        item = eligible_skills[0]
        return {
            "tier": "SINGLE",
            "eligible_count": 1,
            "displayed_count": 1,
            "displayed_skill_ids": [item["id"]],
            "offered_skill_ids": offered_ids,
            "is_curated_selection": False,
            "collection_link": item["deep_link"],
            "markdown": item["markdown"],
            "html": item["html"],
        }

    if 2 <= count <= 4:
        return {
            "tier": "COMPACT_ROW",
            "eligible_count": count,
            "displayed_count": count,
            "displayed_skill_ids": offered_ids,
            "offered_skill_ids": offered_ids,
            "is_curated_selection": False,
            "collection_link": f"{BASE_URL}/u/{handle}/",
            "markdown": " ".join(s["markdown"] for s in eligible_skills),
            "html": "\n".join(s["html"] for s in eligible_skills),
        }

    if 5 <= count <= 8:
        md_text = "### Gaia Skill Tree Recognition\n\n" + " ".join(s["markdown"] for s in eligible_skills)
        html_text = (
            '<div class="gaia-badge-section">\n'
            "  <p><strong>Gaia Skill Tree Recognition:</strong></p>\n  "
            + "\n  ".join(s["html"] for s in eligible_skills)
            + "\n</div>"
        )
        return {
            "tier": "LABELED_SECTION",
            "eligible_count": count,
            "displayed_count": count,
            "displayed_skill_ids": offered_ids,
            "offered_skill_ids": offered_ids,
            "is_curated_selection": False,
            "collection_link": f"{BASE_URL}/u/{handle}/",
            "markdown": md_text,
            "html": html_text,
        }

    # count >= 9: Curated display and link to full collection
    canonical_id = canonical_skill["id"] if canonical_skill else eligible_skills[0]["id"]
    canonical_item = next((s for s in eligible_skills if s["id"] == canonical_id), eligible_skills[0])
    collection_link = f"{BASE_URL}/u/{handle}/"
    md_text = (
        f"{canonical_item['markdown']}\n\n"
        f"[Explore all {count} recognized skills in Gaia Skill Tree]({collection_link})"
    )
    html_text = (
        f"{canonical_item['html']}\n"
        f'<p><a href="{collection_link}">Explore all {count} recognized skills in Gaia Skill Tree</a></p>'
    )
    return {
        "tier": "CURATED_COLLECTION",
        "eligible_count": count,
        "displayed_count": 1,
        "displayed_skill_ids": [canonical_item["id"]],
        "offered_skill_ids": offered_ids,
        "is_curated_selection": True,
        "collection_link": collection_link,
        "markdown": md_text,
        "html": html_text,
    }

    return None, "AMBIGUOUS", (
        f"Multiple skills ({len(skills_in_repo)}) and contributor topSkill {top_skill_id} "
        f"belongs to another repo (suites found: {suites})"
    )


def plan_campaign(
    registry_data: dict[str, Any],
    existing_manifest: dict[str, Any],
    badges_index_path: Path = DEFAULT_BADGES_INDEX,
    assets_root: Path | None = None,
    check_assets: bool = True,
) -> dict[str, Any]:
    """Deterministically generates the campaign manifest, preserving existing outbound state."""
    honesty_mode = detect_honesty_mode(badges_index_path)
    contributors = registry_data.get("contributors", {})

    # 1. Group repository entries case-insensitively
    repo_groups: dict[str, list[dict[str, Any]]] = {}
    for handle, cinfo in contributors.items():
        named_dict = {s["id"]: s for s in cinfo.get("namedSkills", [])}
        for repo in cinfo.get("repos", []):
            norm_key = repo.strip().lower()
            repo_groups.setdefault(norm_key, []).append({
                "handle": handle,
                "repo": repo.strip(),
                "cinfo": cinfo,
                "named_dict": named_dict,
            })

    existing_repos_state = existing_manifest.get("repositories", {})
    existing_lookup: dict[str, dict[str, Any]] = {
        k.strip().lower(): v for k, v in existing_repos_state.items() if isinstance(v, dict)
    }

    manifest_repos: dict[str, Any] = {}
    classification_counts: dict[str, int] = {s: 0 for s in LEGAL_STATUSES}
    eligibility_counts: dict[str, int] = {
        "PILOT_CANDIDATE": 0,
        "READY": 0,
        "REVIEW": 0,
        "SKIP": 0,
    }

    for norm_key, entries in sorted(repo_groups.items()):
        canonical_repo_name = entries[0]["repo"]
        prev_state = existing_lookup.get(norm_key, {})
        if not prev_state:
            for old_repo, new_repo in REPO_MIGRATIONS.items():
                if new_repo.strip().lower() == norm_key and old_repo.strip().lower() in existing_lookup:
                    prev_state = existing_lookup[old_repo.strip().lower()]
                    break
        prev_status = prev_state.get("status")
        prev_prov = prev_state.get("provisioning", {})

        # Check whether repository has already entered outbound lifecycle or contact
        is_contacted_or_outbound = (
            prev_status in OUTBOUND_STATES
            or prev_prov.get("pr_url") is not None
            or prev_prov.get("attempts", 0) > 0
            or prev_prov.get("attempted_at") is not None
            or prev_prov.get("outcome") in OUTBOUND_STATES
        )

        # Baseline provisioning structure
        provisioning = {
            "approved": prev_prov.get("approved", False),
            "approved_by": prev_prov.get("approved_by"),
            "approved_at": prev_prov.get("approved_at"),
            "attempts": prev_prov.get("attempts", 0),
            "attempted_at": prev_prov.get("attempted_at"),
            "pr_url": prev_prov.get("pr_url"),
            "outcome": prev_prov.get("outcome"),
            "decision_notes": prev_prov.get("decision_notes"),
            "history": prev_prov.get("history", []),
        }

        # Baseline preflight structure
        preflight = {
            "existing_badge": prev_state.get("preflight", {}).get("existing_badge", False),
            "default_branch": prev_state.get("preflight", {}).get("default_branch", "UNKNOWN"),
            "readme_path": prev_state.get("preflight", {}).get("readme_path", "README.md"),
            "contribution_policy": prev_state.get("preflight", {}).get("contribution_policy", "UNKNOWN"),
        }

        # Preflight branch overrides for known pilots if not already set
        if norm_key == "pbakaus/impeccable" and preflight["default_branch"] == "UNKNOWN":
            preflight["default_branch"] = "main"
        elif norm_key in ("safishamsi/graphify", "graphify-labs/graphify") and preflight["default_branch"] == "UNKNOWN":
            preflight["default_branch"] = "v8"
        elif norm_key == "trailhq/graft" and preflight["default_branch"] == "UNKNOWN":
            preflight["default_branch"] = "main"

        # Case 1: Multi-contributor collision
        if len(entries) > 1:
            handles = sorted(list(set(e["handle"] for e in entries)))
            computed_eligibility = "SKIP"
            eligibility_counts[computed_eligibility] += 1

            if is_contacted_or_outbound:
                status = prev_status if prev_status in OUTBOUND_STATES else (prev_prov.get("outcome") or "PR_OPEN")
                decision_reason = f"Preserved outbound state {status} (Multi-contributor collision: mapped to handles {handles})"
            else:
                status = "SKIP"
                decision_reason = f"Multi-contributor collision: mapped to handles {handles}"

            repo_record = {
                "repository": canonical_repo_name,
                "eligibility": computed_eligibility,
                "status": status,
                "decision_reason": decision_reason,
                "contributor_associations": handles,
                "canonical_skill": None,
                "eligible_skills": [],
                "eligible_skill_count": 0,
                "offered_skills": [],
                "badge_presentation": None,
                "badge_url": None,
                "deep_link": None,
                "markdown_preview": None,
                "preflight": preflight,
                "provisioning": provisioning,
            }
            manifest_repos[canonical_repo_name] = repo_record
            classification_counts[status] += 1
            continue

        entry = entries[0]
        handle = entry["handle"]
        repo = entry["repo"]
        cinfo = entry["cinfo"]
        named_dict = entry["named_dict"]

        # Case 2: Gaia-owned internal repo
        if repo.lower().startswith("gaia-research/"):
            computed_eligibility = "SKIP"
            eligibility_counts[computed_eligibility] += 1

            if is_contacted_or_outbound:
                status = prev_status if prev_status in OUTBOUND_STATES else (prev_prov.get("outcome") or "PR_OPEN")
                decision_reason = f"Preserved outbound state {status} (Gaia-owned internal repository)"
            else:
                status = "SKIP"
                decision_reason = "Gaia-owned internal repository (excluded from external outreach)"

            preflight["contribution_policy"] = "INTERNAL"
            repo_record = {
                "repository": repo,
                "eligibility": computed_eligibility,
                "status": status,
                "decision_reason": decision_reason,
                "contributor_associations": [handle],
                "canonical_skill": None,
                "eligible_skills": [],
                "eligible_skill_count": 0,
                "offered_skills": [],
                "badge_presentation": None,
                "badge_url": None,
                "deep_link": None,
                "markdown_preview": None,
                "preflight": preflight,
                "provisioning": provisioning,
            }
            manifest_repos[repo] = repo_record
            classification_counts[status] += 1
            continue

        # Derive canonical skill and eligible skills
        skill_obj, strategy, note = derive_canonical_skill(handle, repo, cinfo, named_dict)
        eligible_skills = resolve_eligible_skills(
            handle,
            repo,
            cinfo,
            named_dict,
            honesty_mode,
            assets_root=assets_root,
            check_assets=check_assets,
        )

        # Case 3: No skill / Ambiguous skill
        if skill_obj is None:
            computed_eligibility = "REVIEW" if strategy == "AMBIGUOUS" else "SKIP"
            eligibility_counts[computed_eligibility] += 1

            if is_contacted_or_outbound:
                status = prev_status if prev_status in OUTBOUND_STATES else (prev_prov.get("outcome") or "PR_OPEN")
                decision_reason = f"Preserved outbound state {status} ({strategy}: {note})"
            else:
                status = computed_eligibility
                decision_reason = f"{strategy}: {note}"

            badge_presentation = determine_badge_presentation(eligible_skills, None, handle)

            repo_record = {
                "repository": repo,
                "eligibility": computed_eligibility,
                "status": status,
                "decision_reason": decision_reason,
                "contributor_associations": [handle],
                "canonical_skill": None,
                "eligible_skills": eligible_skills,
                "eligible_skill_count": len(eligible_skills),
                "offered_skills": badge_presentation["offered_skill_ids"],
                "badge_presentation": badge_presentation,
                "badge_url": None,
                "deep_link": None,
                "markdown_preview": None,
                "preflight": preflight,
                "provisioning": provisioning,
            }
            manifest_repos[repo] = repo_record
            classification_counts[status] += 1
            continue

        # Case 4: Valid canonical skill resolved
        skill_id = skill_obj["id"]
        skill_name = skill_obj.get("name", skill_id)
        skill_file = skill_obj.get("file", f"{skill_id.split('/')[-1]}.svg")
        skill_rank = skill_obj.get("rank", 0)

        canonical_skill = {
            "id": skill_id,
            "name": skill_name,
            "rank": skill_rank,
            "branch": skill_obj.get("branch", "standard"),
            "file": skill_file,
        }

        badge_presentation = determine_badge_presentation(eligible_skills, canonical_skill, handle)

        badge_url = generate_badge_url(handle, skill_file, repo, honesty_mode)
        deep_link = f"{BASE_URL}/named/#explorer/{skill_id}"
        md_preview = badge_presentation["markdown"]

        if strategy == "SUITE_CAPSTONE_PREFERENCE":
            computed_eligibility = "REVIEW"
        elif norm_key in {p.lower() for p in PILOT_CANDIDATE_REPOS}:
            computed_eligibility = "PILOT_CANDIDATE"
        else:
            computed_eligibility = "READY"

        eligibility_counts[computed_eligibility] += 1

        if is_contacted_or_outbound:
            status = prev_status if prev_status in OUTBOUND_STATES else (prev_prov.get("outcome") or "PR_OPEN")
            decision_reason = f"Preserved outbound state: {status} (computed eligibility: {computed_eligibility})"
        elif strategy == "SUITE_CAPSTONE_PREFERENCE":
            status = "REVIEW"
            decision_reason = f"Resolved via suite preference: {note}"
        elif computed_eligibility == "PILOT_CANDIDATE":
            status = "PILOT_CANDIDATE"
            decision_reason = f"Founder-selected pilot candidate ({strategy})"
        else:
            status = "READY"
            decision_reason = f"Deterministic resolution ({strategy})"

        provisioning["offered_skills"] = prev_prov.get("offered_skills") or badge_presentation["offered_skill_ids"]
        provisioning["chosen_presentation"] = prev_prov.get("chosen_presentation") or badge_presentation["tier"]

        repo_record = {
            "repository": repo,
            "eligibility": computed_eligibility,
            "status": status,
            "decision_reason": decision_reason,
            "contributor_associations": [handle],
            "canonical_skill": canonical_skill,
            "eligible_skills": eligible_skills,
            "eligible_skill_count": len(eligible_skills),
            "offered_skills": badge_presentation["offered_skill_ids"],
            "badge_presentation": badge_presentation,
            "badge_url": badge_url,
            "deep_link": deep_link,
            "markdown_preview": md_preview,
            "preflight": preflight,
            "provisioning": provisioning,
        }

        manifest_repos[repo] = repo_record
        classification_counts[status] += 1

    manifest = {
        "campaign": "Gaia Badge Provisioning Campaign #1817",
        "phase": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": existing_manifest.get("last_updated_at") or datetime.now(timezone.utc).isoformat(),
        "source_registry_generated_at": registry_data.get("generatedAt", "UNKNOWN"),
        "serving_mode": "honesty_mode_static" if honesty_mode else "worker_validated",
        "authenticates_ownership": False if honesty_mode else True,
        "serving_notice": (
            "Static _assets delivery. ?repo= is retained for cache isolation only "
            "and does not authenticate repository ownership (OAuth hardening deferred to #494)."
            if honesty_mode
            else "Worker validated delivery. Repo ownership verified via Cloudflare Worker."
        ),
        "total_unique_repositories": len(manifest_repos),
        "classification_counts": classification_counts,
        "eligibility_counts": eligibility_counts,
        "repositories": manifest_repos,
    }
    return manifest


def record_outcome(
    manifest_data: dict[str, Any],
    repo: str,
    status: str,
    pr_url: str | None = None,
    notes: str | None = None,
    approved_by: str | None = None,
    force: bool = False,
    actor: str | None = None,
) -> dict[str, Any]:
    """Records an approval, PR URL, or terminal outcome in the campaign manifest.

    Enforces legal state transitions, human approval gates, and duplicate dispatch prevention.

    ``POLICY_HOLD`` (Issue #2074) is a non-terminal internal hold recorded when the repo's contribution
    policy blocks outreach (for example a PR closed under an issue-first policy). It never erases the
    PR URL, attempts or history. Leaving it needs a FRESH ``APPROVED`` with ``approved_by``; the stale
    approval of the earlier attempt does not carry over. ``actor`` attributes the history entry
    without touching the approval fields.
    """
    repos_dict = manifest_data.get("repositories", {})

    target_repo = None
    target_key = None
    for k, v in repos_dict.items():
        if k.strip().lower() == repo.strip().lower():
            target_repo = v
            target_key = k
            break

    if target_repo is None:
        for old_repo, new_repo in REPO_MIGRATIONS.items():
            if old_repo.strip().lower() == repo.strip().lower():
                for k, v in repos_dict.items():
                    if k.strip().lower() == new_repo.strip().lower():
                        target_repo = v
                        target_key = k
                        break
                if target_repo is not None:
                    break

    if target_repo is None:
        raise KeyError(f"Repository '{repo}' not found in campaign manifest.")

    target_status = status.strip().upper()
    if target_status not in LEGAL_STATUSES:
        raise ValueError(
            f"Invalid target status '{target_status}'. Must be one of {sorted(LEGAL_STATUSES)}"
        )

    current_status = target_repo.get("status", "READY")
    prov = target_repo.setdefault("provisioning", {})

    if not force:
        # Check 1: Terminal state lock
        if current_status in TERMINAL_STATES and current_status != target_status:
            raise ValueError(
                f"Illegal transition: Repository '{repo}' is in terminal state '{current_status}' "
                f"and cannot transition to '{target_status}'."
            )

        if target_status == "POLICY_HOLD" and not notes:
            raise ValueError("Recording POLICY_HOLD requires --notes explaining the policy evidence.")

        # Check 2: Outbound PR creation gate
        if target_status == "PR_OPEN" and current_status == "POLICY_HOLD":
            raise ValueError(
                f"Illegal transition: Repository '{repo}' is on POLICY_HOLD; it cannot go straight to PR_OPEN. "
                "Record a fresh APPROVED (with --approved-by) after the policy gate is satisfied, then run predispatch."
            )
        if target_status == "PR_OPEN":
            if not pr_url:
                raise ValueError("Recording status PR_OPEN requires --pr-url.")
            if current_status == "PR_OPEN":
                raise ValueError(
                    f"Duplicate external dispatch prevented: Repository '{repo}' already has an "
                    f"open PR ({prov.get('pr_url')})."
                )

            is_approved = prov.get("approved", False) or bool(approved_by) or (current_status == "APPROVED")
            if not is_approved:
                raise ValueError(
                    f"Illegal transition: Repository '{repo}' cannot transition to PR_OPEN without "
                    f"explicit human approval. Status '{current_status}' alone does not authorize dispatch. "
                    "Provide --approved-by to record approval."
                )

        # Check 3: Approval transition gate
        if target_status == "APPROVED":
            if not approved_by and not prov.get("approved_by"):
                raise ValueError(
                    "Recording status APPROVED requires an approver (--approved-by)."
                )
            if current_status == "POLICY_HOLD" and not approved_by:
                raise ValueError(
                    "Leaving POLICY_HOLD requires a fresh human approval (--approved-by); "
                    "the earlier attempt's approval does not carry over."
                )

    now_iso = datetime.now(timezone.utc).isoformat()

    offered_skills = target_repo.get("offered_skills") or []
    presentation_tier = target_repo.get("badge_presentation", {}).get("tier", "SINGLE")

    if "offered_skills" not in prov:
        prov["offered_skills"] = offered_skills
    if "chosen_presentation" not in prov:
        prov["chosen_presentation"] = presentation_tier

    # Append to history ledger
    history_entry = {
        "timestamp": now_iso,
        "from_status": current_status,
        "to_status": target_status,
        "notes": notes,
        "actor": actor or approved_by or prov.get("approved_by"),
        "pr_url": pr_url or prov.get("pr_url"),
        "offered_skills": offered_skills,
        "presentation_tier": presentation_tier,
    }
    prov.setdefault("history", []).append(history_entry)

    if approved_by:
        prov["approved"] = True
        prov["approved_by"] = approved_by
        prov["approved_at"] = now_iso if current_status == "POLICY_HOLD" else (prov.get("approved_at") or now_iso)

    if target_status == "APPROVED":
        prov["approved"] = True
        if approved_by:
            prov["approved_by"] = approved_by
        if not prov.get("approved_at"):
            prov["approved_at"] = now_iso

    elif target_status == "PR_OPEN":
        prov["attempts"] = prov.get("attempts", 0) + 1
        prov["attempted_at"] = now_iso
        prov["pr_url"] = pr_url
        prov["outcome"] = "PR_OPEN"

    elif target_status in TERMINAL_STATES:
        prov["outcome"] = target_status
        if pr_url:
            prov["pr_url"] = pr_url

    elif target_status == "POLICY_HOLD":
        prov["outcome"] = "POLICY_HOLD"

    if notes:
        prov["decision_notes"] = notes

    target_repo["status"] = target_status

    # Recalculate classification counts
    counts: dict[str, int] = {s: 0 for s in LEGAL_STATUSES}
    for r in repos_dict.values():
        st = r.get("status", "READY")
        counts[st] = counts.get(st, 0) + 1
    manifest_data["classification_counts"] = counts
    manifest_data["last_updated_at"] = now_iso

    return manifest_data


def write_manifest_atomic(path: Path, data: dict[str, Any]) -> None:
    """Write manifest via temp file + os.replace so readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, indent=2) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


@contextlib.contextmanager
def manifest_lock(path: Path) -> Iterator[None]:
    """Exclusive advisory lock serializing manifest read-modify-write cycles."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / (path.name + ".lock")
    with open(lock_path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _load_for_reconcile(args: argparse.Namespace, client: "br.GitHubClient | None" = None
                        ) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...], "br.GitHubClient"]:
    """Load ledger inputs. The live GitHub client is only built when the caller injects none, so tests
    and offline callers never touch the network or the local ``gh`` credential store."""
    manifest = load_existing_manifest(args.manifest)
    if not manifest or "repositories" not in manifest:
        raise ValueError(f"Cannot reconcile: valid manifest not found at {args.manifest}.")
    registry = load_registry(args.registry)
    authors = tuple(args.campaign_author or br.DEFAULT_CAMPAIGN_AUTHORS)
    return manifest, registry, authors, client if client is not None else br.GitHubClient(br.UrllibTransport())


def _cmd_reconcile(args: argparse.Namespace, client: "br.GitHubClient | None" = None) -> int:
    if not args.all and not args.repo:
        print("error: specify --repo (repeatable) or --all", file=sys.stderr)
        return 64
    manifest, registry, authors, gh_client = _load_for_reconcile(args, client)
    n_repos = len(manifest.get("repositories", {})) if args.all else len(args.repo)
    mode = getattr(args, "policy", "auto")
    max_repos = getattr(args, "policy_max_repos", 10)
    scan_policy = mode == "on" or (mode == "auto" and not args.all and n_repos <= max_repos)
    if mode == "on" and n_repos > max_repos:
        print(f"error: policy scan covers at most {max_repos} repo(s) per run (cost guard) but {n_repos} are in "
              "scope. Scope with --repo, or raise --policy-max-repos explicitly.", file=sys.stderr)
        return 64
    # Recorded history (closures, refusals, approvals) is always overlaid: it is offline and free.
    policy_cfg = br.PolicyConfig(call_budget=getattr(args, "policy_budget", br.PolicyConfig.call_budget),
                                 events=br.load_policy_events(getattr(args, "policy_ledger", DEFAULT_POLICY_LEDGER)),
                                 scan=scan_policy)
    receipt = br.reconcile_campaign(
        gh_client, manifest, registry,
        repos=None if args.all else args.repo, authors=authors, max_workers=args.max_workers,
        open_scan_limit=args.open_scan_limit, policy=policy_cfg,
    )
    out_dir = args.out_dir or (DEFAULT_MANIFEST.parent / "receipts" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    jp, mp = br.write_receipt(receipt, out_dir)
    s = receipt["summary"]
    print("=== Gaia Upstream Badge Reconciliation (read-only) ===")
    print(f"Repositories: {s['repositories']}  incomplete: {s['incomplete_evidence']}  anomalies: {s['anomalies']}")
    for k, v in s["by_classification"].items():
        print(f"  {k:18}: {v}")
    print("Policy channels: " + (", ".join(f"{k}={v}" for k, v in s["by_policy_channel"].items()) or "none")
          + f" (policy API calls: {receipt['cost']['policy_api_calls']}, incomplete: {s['policy_incomplete']})")
    print(f"receipt.json: {jp}\nreceipt.md:   {mp}")
    return 0


def _cmd_predispatch(args: argparse.Namespace, client: "br.GitHubClient | None" = None) -> int:
    manifest, registry, authors, gh_client = _load_for_reconcile(args, client)
    verdict = br.predispatch_gate(
        gh_client, manifest, registry, args.repo, args.worker,
        ttl_minutes=args.ttl_minutes, authors=authors, directory=args.reservation_dir,
        open_scan_limit=args.open_scan_limit,
        policy=br.PolicyConfig(call_budget=getattr(args, "policy_budget", 36),
                               events=br.load_policy_events(getattr(args, "policy_ledger", DEFAULT_POLICY_LEDGER))),
    )
    if args.out_dir and verdict.get("entry"):
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "predispatch.json").write_text(
            json.dumps({k: v for k, v in verdict.items()}, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    if verdict["allowed"]:
        print(f"ALLOWED: {verdict['repository']} (reservation expires {verdict['reservation']['expires_at']})")
        print(f"RESERVATION_TOKEN={verdict['reservation']['token']}")
        print("Create the PR now, then: record-outcome --status PR_OPEN --pr-url <url> --reservation-token <token>")
        return 0
    print(f"REFUSED: {verdict['repository']}", file=sys.stderr)
    for r in verdict["refusals"]:
        print(f"  - {r}", file=sys.stderr)
    return 2


def _slug(repo: str) -> str:
    return bp.normalize_repo_name(repo).replace("/", "__")


def _policy_record_key(manifest: dict[str, Any], repo: str) -> str:
    try:
        return br.find_record(manifest, repo)[0]
    except KeyError:
        raise ValueError(f"Repository '{repo}' not found in campaign manifest.") from None


def _ledger_view(ledger: Path, manifest: dict[str, Any], repo: str) -> tuple[str, dict[str, Any]]:
    key = _policy_record_key(manifest, repo)
    events = list(br.load_policy_events(ledger))
    return key, bp.ledger_state(events, [key, repo], br.KNOWN_MIGRATIONS)


def _cmd_policy(args: argparse.Namespace) -> int:
    """Offline policy-ledger operations. Nothing here touches the network or posts to GitHub."""
    ledger: Path = args.ledger
    act = args.policy_action
    if act == "verify":
        problems = bp.verify_chain(bp.read_events(ledger))
        for pr in problems:
            print(f"BROKEN: {pr}", file=sys.stderr)
        print("policy ledger intact" if not problems else f"{len(problems)} problem(s)")
        return 0 if not problems else 2
    manifest = load_existing_manifest(args.manifest)
    if not manifest or "repositories" not in manifest:
        raise ValueError(f"Cannot use policy ledger: valid manifest not found at {args.manifest}.")
    if act == "apply":
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        digest = hashlib.sha256(args.receipt.read_bytes()).hexdigest()
        wanted = {bp.normalize_repo_name(r) for r in (args.repo or [])}
        wrote = 0
        for name, entry in sorted(receipt.get("repositories", {}).items()):
            if wanted and bp.normalize_repo_name(name) not in wanted:
                continue
            pol = entry.get("policy") or {}
            if not pol.get("scanned"):
                continue
            key, state = _ledger_view(ledger, manifest, name)
            if state["last_channel"] == pol["channel"]:
                continue
            bp.append_event(ledger, key, "CHANNEL_CLASSIFIED", args.recorded_by, {
                "channel": pol["channel"], "previous_channel": state["last_channel"],
                "partial_channel": pol.get("partial_channel"), "observed_at": pol["observed_at"],
                "complete": pol["completeness"]["complete"], "incomplete_reasons": pol["completeness"]["incomplete_reasons"],
                "source_urls": sorted({sg["source_url"] for sg in pol["sources"] if sg.get("decisive") and sg.get("source_url")}),
                "receipt_sha256": digest, "aliases": entry.get("aliases", []),
            })
            wrote += 1
        print(f"recorded {wrote} channel event(s)")
        return 0
    key, state = _ledger_view(ledger, manifest, args.repo)
    if act == "status":
        out = {
            "repository": key, "last_channel": state["last_channel"],
            "historical_closures": [e["data"] | {"event_hash": e["hash"]} for e in state["historical_closures"]],
            "refusals": [e["data"] | {"event_hash": e["hash"]} for e in state["refusals"]],
            "drafts": [e["data"] | {"event_hash": e["hash"]} for e in state["drafts"]],
            "proposals_sent": [e["data"] | {"event_hash": e["hash"]} for e in state["proposals_sent"]],
            "approvals": [{"active": a["active"], "hash": a["event"]["hash"], **a["event"]["data"]} for a in state["approvals"]],
            "events": len(state["events"]),
        }
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    blocked = bool(state["refusals"])
    if act == "record-closure":
        bp.append_event(ledger, key, "HISTORICAL_CLOSURE_RECORDED", args.recorded_by, {
            "pr_url": args.pr_url, "state": "CLOSED_UNMERGED", "closed_at": args.closed_at, "kind": args.kind,
            "comment_url": args.comment_url, "excerpt": args.excerpt, "authority": args.authority,
            "live_verified": args.live_verified,
            "source_note": args.source_note, "aliases": [args.repo] if args.repo != key else []})
    elif act == "classify":
        bp.append_event(ledger, key, "CHANNEL_CLASSIFIED", args.recorded_by, {
            "channel": args.channel, "previous_channel": state["last_channel"], "partial_channel": None,
            "observed_at": datetime.now(timezone.utc).isoformat(), "complete": False,
            "incomplete_reasons": ["recorded_from_history_no_live_scan"], "basis": args.basis,
            "source_urls": args.source_url or [], "receipt_sha256": None, "aliases": []})
    elif act == "record-refusal":
        bp.append_event(ledger, key, "PRIOR_REFUSAL_RECORDED", args.recorded_by, {
            "source_url": args.source_url, "excerpt": args.excerpt, "authority": args.authority})
    elif act == "draft":
        if blocked:
            print("REFUSED: a prior refusal is recorded; no proposal may be drafted for this repo.", file=sys.stderr)
            return 2
        if state["proposals_sent"]:
            print("REFUSED: a proposal issue is already recorded; one outreach attempt = one proposal.", file=sys.stderr)
            return 2
        rec = manifest["repositories"][key]
        skill = (rec.get("canonical_skill") or {}).get("name")
        if not skill or not rec.get("deep_link") or not rec.get("badge_url"):
            print("REFUSED: ledger has no canonical skill / deep link / badge URL for this repo.", file=sys.stderr)
            return 2
        text = bp.render_draft_proposal(key, skill, rec["deep_link"], rec["badge_url"])
        out_path = args.out or (DEFAULT_DRAFT_DIR / f"{_slug(key)}.issue-first-proposal.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        bp.append_event(ledger, key, "ISSUE_PROPOSAL_DRAFTED", args.recorded_by, {
            "draft_path": str(out_path.relative_to(REPO_ROOT)) if out_path.is_relative_to(REPO_ROOT) else str(out_path),
            "draft_sha256": hashlib.sha256(text.encode()).hexdigest(), "words": bp.draft_word_count(text), "sent": False})
        print(f"draft written (LOCAL ONLY, never sent): {out_path}")
    elif act == "record-sent":
        if blocked:
            print("REFUSED: a prior refusal is recorded; no proposal may be recorded for this repo.", file=sys.stderr)
            return 2
        if state["proposals_sent"]:
            print("REFUSED: exactly one proposal issue is allowed per outreach attempt.", file=sys.stderr)
            return 2
        bp.append_event(ledger, key, "ISSUE_PROPOSAL_SENT", args.recorded_by, {"issue_url": args.issue_url})
    elif act == "approve":
        if blocked:
            print("REFUSED: a prior refusal is recorded; an approval cannot lift it.", file=sys.stderr)
            return 2
        if not any(bp._norm_url(e["data"]["issue_url"]) == bp._norm_url(args.issue_url) for e in state["proposals_sent"]):
            print("REFUSED: approval must attach to the single proposal issue recorded with `policy record-sent`.", file=sys.stderr)
            return 2
        if state["active_approvals"]:
            print("REFUSED: an active approval already exists; revoke it first.", file=sys.stderr)
            return 2
        bp.append_event(ledger, key, "MAINTAINER_APPROVAL_RECORDED", args.recorded_by, {
            "issue_url": args.issue_url, "approver": args.approver, "authority": args.authority,
            "evidence_url": args.evidence_url, "evidence_excerpt": args.evidence_excerpt, "scope": "single_readme_pr"})
    elif act == "revoke":
        bp.append_event(ledger, key, "APPROVAL_REVOKED", args.recorded_by, {
            "target_hash": args.target_hash, "reason": args.reason})
    print(f"recorded {act} for {key}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Gaia Badge Provisioning Planner (Issue #1817).")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    plan_parser = subparsers.add_parser("plan", help="Generate or update campaign manifest")
    plan_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="Path to registry.json")
    plan_parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Output manifest path")
    plan_parser.add_argument("--badges-index", type=Path, default=DEFAULT_BADGES_INDEX, help="Path to docs/badges/index.html")
    plan_parser.add_argument("--dry-run", action="store_true", help="Print summary without writing manifest")

    record_parser = subparsers.add_parser("record-outcome", help="Record campaign outcome or transition for a repository")
    record_parser.add_argument("--repo", required=True, help="Repository name (e.g. owner/repo)")
    record_parser.add_argument("--status", required=True, help="Target status (APPROVED, PR_OPEN, ADOPTED, DECLINED, OPTED_OUT)")
    record_parser.add_argument("--pr-url", default=None, help="PR URL (required for PR_OPEN)")
    record_parser.add_argument("--notes", default=None, help="Decision notes or reason")
    record_parser.add_argument("--approved-by", default=None, help="Human reviewer granting approval")
    record_parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to manifest.json")
    record_parser.add_argument("--force", action="store_true", help="ADMIN OVERRIDE (founder-authorized recovery only; agents/routines must never use it): "
                                 "bypasses transition validation and the PR_OPEN reservation gate")

    record_parser.add_argument("--actor", default=None, help="Who recorded this entry (history attribution only; does not set approval)")
    record_parser.add_argument("--reservation-token", default=None, help="Token from a successful 'predispatch' (required for PR_OPEN)")
    record_parser.add_argument("--reservation-dir", type=Path, default=br.DEFAULT_RESERVATION_DIR, help=argparse.SUPPRESS)

    def add_gh_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="Path to registry.json")
        sp.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to manifest.json (read-only)")
        sp.add_argument("--campaign-author", action="append", default=None,
                        help="GitHub login(s) that author campaign PRs (default: mbtiongson1)")
        sp.add_argument("--open-scan-limit", type=int, default=br.MAX_OPEN_SCAN,
                        help="Max unmarked open PRs to diff-inspect per repo; more makes the repo UNKNOWN, "
                             f"never READY (default {br.MAX_OPEN_SCAN})")
        sp.add_argument("--policy-ledger", type=Path, default=DEFAULT_POLICY_LEDGER,
                        help="Append-only policy ledger (read-only here)")
        sp.add_argument("--policy-budget", type=int, default=br.PolicyConfig.call_budget,
                        help="Max GitHub API calls per repo for the contribution-channel scan (cost guard); "
                             f"exceeding it makes the repo UNKNOWN (default {br.PolicyConfig.call_budget})")

    rec_parser = subparsers.add_parser(
        "reconcile", help="Read-only upstream reconciliation; writes receipt.json + receipt.md only")
    add_gh_args(rec_parser)
    rec_parser.add_argument("--repo", action="append", default=None, help="Repository (repeatable). Omit with --all")
    rec_parser.add_argument("--all", action="store_true", help="Reconcile the entire campaign manifest")
    rec_parser.add_argument("--read-only", action="store_true", default=True, help="Always on; accepted for explicitness")
    rec_parser.add_argument("--out-dir", type=Path, default=None,
                            help="Receipt directory (default: campaigns/badge-provisioning/receipts/<UTC timestamp>)")
    rec_parser.add_argument("--max-workers", type=int, default=4, help="Bounded concurrency (default 4)")
    rec_parser.add_argument("--policy", choices=("auto", "on", "off"), default="auto",
                            help="Contribution-channel scan (#2074). auto = on for a scoped --repo run, off for --all "
                                 "(unscanned repos report policy_channel UNKNOWN). Never required for a full campaign scan.")
    rec_parser.add_argument("--policy-max-repos", type=int, default=10,
                            help="Cost guard: max repos policy-scanned per run (default 10)")

    pre_parser = subparsers.add_parser(
        "predispatch", help="MANDATORY gate immediately before creating an upstream PR")
    add_gh_args(pre_parser)
    pre_parser.add_argument("--repo", required=True)
    pre_parser.add_argument("--worker", required=True, help="Worker identity recorded in the reservation")
    pre_parser.add_argument("--ttl-minutes", type=int, default=30)
    pre_parser.add_argument("--out-dir", type=Path, default=None, help="Optionally write the gate receipt here")
    pre_parser.add_argument("--reservation-dir", type=Path, default=br.DEFAULT_RESERVATION_DIR, help=argparse.SUPPRESS)

    rel_parser = subparsers.add_parser("release-reservation", help="Release a dispatch reservation")
    rel_parser.add_argument("--repo", required=True)
    rel_parser.add_argument("--token", default=None)
    rel_parser.add_argument("--force", action="store_true",
                            help="ADMIN OVERRIDE: release without token (stale reservation recovery; not for routine agent use)")
    rel_parser.add_argument("--reservation-dir", type=Path, default=br.DEFAULT_RESERVATION_DIR, help=argparse.SUPPRESS)


    pol_parser = subparsers.add_parser(
        "policy", help="Offline contribution-channel policy ledger (#2074). Never contacts GitHub or upstream.")
    pol_parser.add_argument("--ledger", type=Path, default=DEFAULT_POLICY_LEDGER, help="Append-only policy ledger (JSONL)")
    pol_parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to manifest.json (read-only)")
    psub = pol_parser.add_subparsers(dest="policy_action", required=True)
    psub.add_parser("verify", help="Verify the ledger hash chain")
    p_status = psub.add_parser("status", help="Show recorded policy state for a repo (offline)")
    p_status.add_argument("--repo", required=True)
    p_apply = psub.add_parser("apply", help="Record channel CHANGES from a reconcile receipt as ledger events")
    p_apply.add_argument("--receipt", type=Path, required=True)
    p_apply.add_argument("--repo", action="append", default=None)
    p_apply.add_argument("--recorded-by", required=True)
    p_clo = psub.add_parser("record-closure", help="Record a historical PR closure (never erased)")
    p_clo.add_argument("--repo", required=True)
    p_clo.add_argument("--pr-url", required=True)
    p_clo.add_argument("--closed-at", required=True)
    p_clo.add_argument("--kind", required=True, choices=bp.CLOSURE_KINDS)
    p_clo.add_argument("--excerpt", required=True)
    p_clo.add_argument("--comment-url", default=None)
    p_clo.add_argument("--authority", default="policy_bot")
    p_clo.add_argument("--source-note", default=None, help="Provenance, e.g. where the excerpt was read")
    p_clo.add_argument("--live-verified", action="store_true", help="Set only if a human verified the upstream state live")
    p_clo.add_argument("--recorded-by", required=True)
    p_cls = psub.add_parser("classify", help="Record a channel decision from history (no live scan); audit trail only")
    p_cls.add_argument("--repo", required=True)
    p_cls.add_argument("--channel", required=True, choices=bp.CHANNELS)
    p_cls.add_argument("--basis", required=True, help="Why, e.g. 'recorded #1010 closure under issue-first policy'")
    p_cls.add_argument("--source-url", action="append", default=None)
    p_cls.add_argument("--recorded-by", required=True)
    p_ref = psub.add_parser("record-refusal", help="Record an upstream refusal (terminal for this repo)")
    p_ref.add_argument("--repo", required=True)
    p_ref.add_argument("--source-url", required=True)
    p_ref.add_argument("--excerpt", required=True)
    p_ref.add_argument("--authority", default="maintainer")
    p_ref.add_argument("--recorded-by", required=True)
    p_dr = psub.add_parser("draft", help="Write a LOCAL draft proposal issue. It is never sent.")
    p_dr.add_argument("--repo", required=True)
    p_dr.add_argument("--out", type=Path, default=None)
    p_dr.add_argument("--recorded-by", required=True)
    p_sent = psub.add_parser("record-sent", help="A human records that they filed the ONE proposal issue")
    p_sent.add_argument("--repo", required=True)
    p_sent.add_argument("--issue-url", required=True)
    p_sent.add_argument("--recorded-by", required=True)
    p_ap = psub.add_parser("approve", help="Record a maintainer approval with authority and evidence")
    p_ap.add_argument("--repo", required=True)
    p_ap.add_argument("--issue-url", required=True)
    p_ap.add_argument("--approver", required=True, help="Maintainer GitHub login")
    p_ap.add_argument("--authority", required=True, choices=bp.AUTHORITY_ASSOCIATIONS)
    p_ap.add_argument("--evidence-url", required=True, help="URL of the approving comment (…#issuecomment-<id>)")
    p_ap.add_argument("--evidence-excerpt", required=True, help="Verbatim approving text; verified against upstream at predispatch")
    p_ap.add_argument("--recorded-by", required=True)
    p_rv = psub.add_parser("revoke", help="Revoke an approval (history is kept)")
    p_rv.add_argument("--repo", required=True)
    p_rv.add_argument("--target-hash", required=True)
    p_rv.add_argument("--reason", required=True)
    p_rv.add_argument("--recorded-by", required=True)

    # Support default execution as 'plan' when no subcommand is specified
    args_list = sys.argv[1:]
    commands = ("plan", "record-outcome", "reconcile", "predispatch", "release-reservation", "policy")
    if not args_list or (args_list[0] not in commands and not args_list[0].startswith("-h")):
        args_list = ["plan"] + args_list

    args = parser.parse_args(args_list)

    if args.command == "reconcile":
        sys.exit(_cmd_reconcile(args))
    if args.command == "predispatch":
        sys.exit(_cmd_predispatch(args))
    if args.command == "policy":
        try:
            sys.exit(_cmd_policy(args))
        except (bp.LedgerError, ValueError, OSError) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            sys.exit(2)
    if args.command == "release-reservation":
        try:
            released = br.release_reservation(args.repo, args.token, args.force, args.reservation_dir)
        except br.ReservationError as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            sys.exit(2)
        print("released" if released else "no reservation held")
        return

    if args.command == "record-outcome":
        with manifest_lock(args.manifest):
            manifest_data = load_existing_manifest(args.manifest)
            if not manifest_data or "repositories" not in manifest_data:
                raise ValueError(f"Cannot record outcome: valid manifest not found at {args.manifest}. Run 'plan' first.")

            gated_pr_open = args.status.strip().upper() == "PR_OPEN" and not args.force
            if gated_pr_open:
                if not args.reservation_token:
                    raise ValueError(
                        "Recording PR_OPEN requires --reservation-token from a successful 'predispatch' "
                        "(#2069 mandatory pre-dispatch gate)."
                    )
                try:
                    _key, _rec = br.find_record(manifest_data, args.repo)
                    br.verify_reservation(args.repo, args.reservation_token, args.reservation_dir,
                                          current_snapshot=br.ledger_snapshot(_rec))
                except br.ReservationError as e:
                    raise ValueError(f"Pre-dispatch reservation invalid: {e}") from e

            updated = record_outcome(
                manifest_data=manifest_data,
                repo=args.repo,
                status=args.status,
                pr_url=args.pr_url,
                notes=args.notes,
                approved_by=args.approved_by,
                force=args.force,
                actor=args.actor,
            )
            write_manifest_atomic(args.manifest, updated)
            if gated_pr_open:
                br.release_reservation(args.repo, args.reservation_token, directory=args.reservation_dir)
            else:
                # Any other ledger change voids outstanding authorization for this repo.
                br.release_reservation(args.repo, force=True, directory=args.reservation_dir)
        print(f"Outcome successfully recorded for {args.repo} -> {args.status}")
        return

    # Subcommand: plan
    reg_data = load_registry(args.registry)
    with manifest_lock(args.manifest) if not args.dry_run else contextlib.nullcontext():
        existing_manifest = load_existing_manifest(args.manifest)
        manifest = plan_campaign(reg_data, existing_manifest, badges_index_path=args.badges_index)
        if not args.dry_run:
            write_manifest_atomic(args.manifest, manifest)

    print("=== Gaia Badge Provisioning Plan Summary ===")
    print(f"Total Unique Repositories: {manifest['total_unique_repositories']}")
    print(f"Serving Mode: {manifest['serving_mode']} (authenticates_ownership={manifest['authenticates_ownership']})")
    print("Classifications:")
    for status, count in sorted(manifest["classification_counts"].items()):
        if count > 0:
            print(f"  {status:16}: {count}")

    if not args.dry_run:
        print(f"\nManifest successfully written to: {args.manifest}")


if __name__ == "__main__":
    main()
