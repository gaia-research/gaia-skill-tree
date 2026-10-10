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
DEFAULT_BADGES_INDEX = REPO_ROOT / "docs" / "badges" / "index.html"
BASE_URL = "https://gaiaskilltree.com"

# The three founder-approved low-risk pilot candidates
PILOT_CANDIDATE_REPOS = {
    "pbakaus/impeccable",
    "safishamsi/graphify",
    "trailhq/graft",
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
}

OUTBOUND_STATES = {
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


def plan_campaign(
    registry_data: dict[str, Any],
    existing_manifest: dict[str, Any],
    badges_index_path: Path = DEFAULT_BADGES_INDEX,
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
        elif norm_key == "safishamsi/graphify" and preflight["default_branch"] == "UNKNOWN":
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
                "badge_url": None,
                "deep_link": None,
                "markdown_preview": None,
                "preflight": preflight,
                "provisioning": provisioning,
            }
            manifest_repos[repo] = repo_record
            classification_counts[status] += 1
            continue

        # Derive canonical skill
        skill_obj, strategy, note = derive_canonical_skill(handle, repo, cinfo, named_dict)

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

            repo_record = {
                "repository": repo,
                "eligibility": computed_eligibility,
                "status": status,
                "decision_reason": decision_reason,
                "contributor_associations": [handle],
                "canonical_skill": None,
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

        badge_url = generate_badge_url(handle, skill_file, repo, honesty_mode)
        deep_link = f"{BASE_URL}/named/#explorer/{skill_id}"
        md_preview = f"[![Gaia Skill: {skill_name}]({badge_url})]({deep_link})"

        if strategy == "SUITE_CAPSTONE_PREFERENCE":
            computed_eligibility = "REVIEW"
        elif norm_key in PILOT_CANDIDATE_REPOS:
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

        repo_record = {
            "repository": repo,
            "eligibility": computed_eligibility,
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
) -> dict[str, Any]:
    """Records an approval, PR URL, or terminal outcome in the campaign manifest.

    Enforces legal state transitions, human approval gates, and duplicate dispatch prevention.
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

        # Check 2: Outbound PR creation gate
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

    now_iso = datetime.now(timezone.utc).isoformat()

    # Append to history ledger
    history_entry = {
        "timestamp": now_iso,
        "from_status": current_status,
        "to_status": target_status,
        "notes": notes,
        "actor": approved_by or prov.get("approved_by"),
        "pr_url": pr_url or prov.get("pr_url"),
    }
    prov.setdefault("history", []).append(history_entry)

    if approved_by:
        prov["approved"] = True
        prov["approved_by"] = approved_by
        prov["approved_at"] = prov.get("approved_at") or now_iso

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
    record_parser.add_argument("--force", action="store_true", help="Bypass transition validations (admin recovery only)")

    # Support default execution as 'plan' when no subcommand is specified
    args_list = sys.argv[1:]
    if not args_list or (args_list[0] not in ("plan", "record-outcome") and not args_list[0].startswith("-h")):
        args_list = ["plan"] + args_list

    args = parser.parse_args(args_list)

    if args.command == "record-outcome":
        manifest_data = load_existing_manifest(args.manifest)
        if not manifest_data or "repositories" not in manifest_data:
            raise ValueError(f"Cannot record outcome: valid manifest not found at {args.manifest}. Run 'plan' first.")

        updated = record_outcome(
            manifest_data=manifest_data,
            repo=args.repo,
            status=args.status,
            pr_url=args.pr_url,
            notes=args.notes,
            approved_by=args.approved_by,
            force=args.force,
        )
        args.manifest.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        print(f"Outcome successfully recorded for {args.repo} -> {args.status}")
        return

    # Subcommand: plan
    reg_data = load_registry(args.registry)
    existing_manifest = load_existing_manifest(args.manifest)

    manifest = plan_campaign(reg_data, existing_manifest, badges_index_path=args.badges_index)

    print("=== Gaia Badge Provisioning Plan Summary ===")
    print(f"Total Unique Repositories: {manifest['total_unique_repositories']}")
    print(f"Serving Mode: {manifest['serving_mode']} (authenticates_ownership={manifest['authenticates_ownership']})")
    print("Classifications:")
    for status, count in sorted(manifest["classification_counts"].items()):
        if count > 0:
            print(f"  {status:16}: {count}")

    if not args.dry_run:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"\nManifest successfully written to: {args.manifest}")


if __name__ == "__main__":
    main()
