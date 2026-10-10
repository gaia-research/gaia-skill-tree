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
4. Preserves persistent campaign state (PR URLs, outcomes, manual overrides)
   across regenerations.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = REPO_ROOT / "docs" / "badges" / "registry.json"
DEFAULT_MANIFEST = REPO_ROOT / "campaigns" / "badge-provisioning" / "manifest.json"
BASE_URL = "https://gaiaskilltree.com"

# The three founder-approved low-risk pilot candidates
PILOT_CANDIDATE_REPOS = {
    "pbakaus/impeccable",
    "safishamsi/graphify",
    "trailhq/graft",
}


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Registry not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_existing_manifest(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Failed to load existing manifest at {path}: {e}", file=sys.stderr)
    return {}


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

    if len(skills_in_repo) == 1:
        sid = skills_in_repo[0]
        skill_obj = named_dict.get(sid)
        if skill_obj:
            return skill_obj, "SINGLE_SKILL", "Sole skill mapped to repository"
        return None, "MISSING_SKILL_DATA", f"Skill {sid} metadata missing"

    # Multiple skills in repo
    if top_skill_id in skills_in_repo:
        skill_obj = named_dict.get(top_skill_id)
        if skill_obj:
            return skill_obj, "TOP_SKILL_MATCH", f"Matches contributor topSkill ({len(skills_in_repo)} skills in repo)"
        return None, "MISSING_SKILL_DATA", f"Top skill {top_skill_id} metadata missing"

    # topSkill is in another repository. Check if there is a suite capstone in this repo.
    suites = [sid for sid in skills_in_repo if named_dict.get(sid, {}).get("branch") == "suite"]
    if len(suites) == 1:
        capstone_id = suites[0]
        skill_obj = named_dict.get(capstone_id)
        if skill_obj:
            return skill_obj, "SUITE_CAPSTONE_PREFERENCE", (
                f"Preferred suite capstone {capstone_id} over cross-repo topSkill {top_skill_id} "
                f"({len(skills_in_repo)} skills in repo)"
            )

    return None, "AMBIGUOUS", (
        f"Multiple skills ({len(skills_in_repo)}) and contributor topSkill {top_skill_id} "
        f"belongs to another repo (suites found: {suites})"
    )


def plan_campaign(registry_data: dict[str, Any], existing_manifest: dict[str, Any]) -> dict[str, Any]:
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

    manifest_repos: dict[str, Any] = {}
    classification_counts: dict[str, int] = {
        "PILOT_CANDIDATE": 0,
        "READY": 0,
        "REVIEW": 0,
        "SKIP": 0,
        "ALREADY_ADOPTED": 0,
        "OPTED_OUT": 0,
    }

    for norm_key, entries in sorted(repo_groups.items()):
        canonical_repo_name = entries[0]["repo"]
        prev_state = existing_repos_state.get(canonical_repo_name) or existing_repos_state.get(norm_key, {})
        
        # Check previous manual overrides or terminal states
        prev_status = prev_state.get("status")
        
        # Collision check: multiple contributors mapped to same repo
        if len(entries) > 1:
            handles = sorted(list(set(e["handle"] for e in entries)))
            status = "SKIP"
            if prev_status in ("OPTED_OUT", "ALREADY_ADOPTED"):
                status = prev_status
            
            repo_record = {
                "repository": canonical_repo_name,
                "status": status,
                "decision_reason": f"Multi-contributor collision: mapped to handles {handles}",
                "contributor_associations": handles,
                "canonical_skill": None,
                "badge_url": None,
                "deep_link": None,
                "markdown_preview": None,
                "preflight": {
                    "existing_badge": prev_state.get("preflight", {}).get("existing_badge", False),
                    "default_branch": prev_state.get("preflight", {}).get("default_branch", "UNKNOWN"),
                    "readme_path": prev_state.get("preflight", {}).get("readme_path", "README.md"),
                    "contribution_policy": prev_state.get("preflight", {}).get("contribution_policy", "UNKNOWN"),
                },
                "provisioning": prev_state.get("provisioning", {
                    "pr_url": None,
                    "attempted_at": None,
                    "outcome": None,
                }),
            }
            manifest_repos[canonical_repo_name] = repo_record
            classification_counts[status] += 1
            continue

        entry = entries[0]
        handle = entry["handle"]
        repo = entry["repo"]
        cinfo = entry["cinfo"]
        named_dict = entry["named_dict"]

        # Check self-owned repos (Gaia org)
        if repo.lower().startswith("gaia-research/"):
            status = "SKIP"
            repo_record = {
                "repository": repo,
                "status": status,
                "decision_reason": "Gaia-owned internal repository (excluded from external outreach)",
                "contributor_associations": [handle],
                "canonical_skill": None,
                "badge_url": None,
                "deep_link": None,
                "markdown_preview": None,
                "preflight": {
                    "existing_badge": False,
                    "default_branch": "main",
                    "readme_path": "README.md",
                    "contribution_policy": "INTERNAL",
                },
                "provisioning": prev_state.get("provisioning", {
                    "pr_url": None,
                    "attempted_at": None,
                    "outcome": None,
                }),
            }
            manifest_repos[repo] = repo_record
            classification_counts[status] += 1
            continue

        # Derive canonical skill
        skill_obj, strategy, note = derive_canonical_skill(handle, repo, cinfo, named_dict)

        if skill_obj is None:
            status = "REVIEW" if strategy == "AMBIGUOUS" else "SKIP"
            if prev_status in ("OPTED_OUT", "ALREADY_ADOPTED"):
                status = prev_status

            repo_record = {
                "repository": repo,
                "status": status,
                "decision_reason": f"{strategy}: {note}",
                "contributor_associations": [handle],
                "canonical_skill": None,
                "badge_url": None,
                "deep_link": None,
                "markdown_preview": None,
                "preflight": {
                    "existing_badge": prev_state.get("preflight", {}).get("existing_badge", False),
                    "default_branch": prev_state.get("preflight", {}).get("default_branch", "UNKNOWN"),
                    "readme_path": prev_state.get("preflight", {}).get("readme_path", "README.md"),
                    "contribution_policy": prev_state.get("preflight", {}).get("contribution_policy", "UNKNOWN"),
                },
                "provisioning": prev_state.get("provisioning", {
                    "pr_url": None,
                    "attempted_at": None,
                    "outcome": None,
                }),
            }
            manifest_repos[repo] = repo_record
            classification_counts[status] += 1
            continue

        # Valid skill found
        skill_id = skill_obj["id"]
        skill_name = skill_obj.get("name", skill_id)
        skill_file = skill_obj.get("file", f"{skill_id.split('/')[-1]}.svg")
        skill_rank = skill_obj.get("rank", 0)

        badge_url = f"{BASE_URL}/badges/{handle}/{skill_file}?repo={repo}"
        deep_link = f"{BASE_URL}/named/#explorer/{skill_id}"
        md_preview = f"[![Gaia Skill: {skill_name}]({badge_url})]({deep_link})"

        # Determine status
        if prev_status in ("OPTED_OUT", "ALREADY_ADOPTED"):
            status = prev_status
            decision_reason = f"Preserved previous state: {prev_status}"
        elif strategy == "SUITE_CAPSTONE_PREFERENCE":
            status = "REVIEW"
            decision_reason = f"Resolved via suite preference: {note}"
        elif norm_key in PILOT_CANDIDATE_REPOS:
            status = "PILOT_CANDIDATE"
            decision_reason = f"Founder-selected pilot candidate ({strategy})"
        else:
            status = "READY"
            decision_reason = f"Deterministic resolution ({strategy})"

        repo_record = {
            "repository": repo,
            "status": status,
            "decision_reason": decision_reason,
            "contributor_associations": [handle],
            "canonical_skill": {
                "id": skill_id,
                "name": skill_name,
                "rank": skill_rank,
                "branch": skill_obj.get("branch", "standard"),
                "file": skill_file,
            },
            "badge_url": badge_url,
            "deep_link": deep_link,
            "markdown_preview": md_preview,
            "preflight": {
                "existing_badge": prev_state.get("preflight", {}).get("existing_badge", False),
                "default_branch": prev_state.get("preflight", {}).get("default_branch", "UNKNOWN"),
                "readme_path": prev_state.get("preflight", {}).get("readme_path", "README.md"),
                "contribution_policy": prev_state.get("preflight", {}).get("contribution_policy", "UNKNOWN"),
            },
            "provisioning": prev_state.get("provisioning", {
                "pr_url": None,
                "attempted_at": None,
                "outcome": None,
            }),
        }

        # Keep manual overrides for known pilots
        if norm_key == "pbakaus/impeccable":
            repo_record["preflight"]["default_branch"] = "main"
        elif norm_key == "safishamsi/graphify":
            repo_record["preflight"]["default_branch"] = "v8"
        elif norm_key == "trailhq/graft":
            repo_record["preflight"]["default_branch"] = "main"

        manifest_repos[repo] = repo_record
        classification_counts[status] += 1

    manifest = {
        "campaign": "Gaia Badge Provisioning Campaign #1817",
        "phase": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_registry_generated_at": registry_data.get("generatedAt", "UNKNOWN"),
        "total_unique_repositories": len(manifest_repos),
        "classification_counts": classification_counts,
        "repositories": manifest_repos,
    }
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Gaia badge provisioning plan.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="Path to registry.json")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Output manifest path")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing manifest")
    args = parser.parse_args()

    reg_data = load_registry(args.registry)
    existing_manifest = load_existing_manifest(args.manifest)

    manifest = plan_campaign(reg_data, existing_manifest)

    print("=== Gaia Badge Provisioning Plan Summary ===")
    print(f"Total Unique Repositories: {manifest['total_unique_repositories']}")
    print("Classifications:")
    for status, count in sorted(manifest["classification_counts"].items()):
        print(f"  {status:16}: {count}")

    if not args.dry_run:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"\nManifest successfully written to: {args.manifest}")


if __name__ == "__main__":
    main()
