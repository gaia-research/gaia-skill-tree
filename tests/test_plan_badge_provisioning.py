"""Tests for scripts/plan_badge_provisioning.py (Gaia Badge Provisioning Campaign #1817)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.plan_badge_provisioning import (
    DEFAULT_MANIFEST,
    DEFAULT_REGISTRY,
    derive_canonical_skill,
    load_registry,
    plan_campaign,
)


def test_registry_load_and_deduplication():
    """Verify registry loading and case-insensitive repository grouping."""
    reg = load_registry(DEFAULT_REGISTRY)
    assert "contributors" in reg
    manifest = plan_campaign(reg, {})
    
    # Invariant: Exactly 43 distinct repositories after deduplication
    assert manifest["total_unique_repositories"] == 43
    
    # Invariant: Sum of classifications equals total repositories
    counts = manifest["classification_counts"]
    assert sum(counts.values()) == 43
    assert counts["PILOT_CANDIDATE"] == 3
    assert counts["REVIEW"] == 2
    assert counts["SKIP"] == 3
    assert counts["READY"] == 35


def test_unique_single_skill_mapping():
    """Verify single-skill repositories resolve cleanly."""
    cinfo = {
        "repos": ["pbakaus/impeccable"],
        "skillsByRepo": {"pbakaus/impeccable": ["pbakaus/impeccable"]},
        "topSkill": "pbakaus/impeccable",
        "topRank": 4,
        "namedSkills": [
            {
                "id": "pbakaus/impeccable",
                "name": "Impeccable",
                "rank": 4,
                "branch": "unique",
                "file": "impeccable.svg",
            }
        ],
    }
    named_dict = {s["id"]: s for s in cinfo["namedSkills"]}
    skill_obj, strategy, note = derive_canonical_skill(
        "pbakaus", "pbakaus/impeccable", cinfo, named_dict
    )
    assert skill_obj is not None
    assert skill_obj["id"] == "pbakaus/impeccable"
    assert strategy == "SINGLE_SKILL"


def test_canonical_top_skill_preference():
    """Verify repos with multiple skills select contributor's topSkill when contained."""
    cinfo = {
        "repos": ["addyosmani/agent-skills"],
        "skillsByRepo": {
            "addyosmani/agent-skills": [
                "addy-osmani/agent-skills",
                "addy-osmani/sub-skill-1",
            ]
        },
        "topSkill": "addy-osmani/agent-skills",
        "topRank": 4,
        "namedSkills": [
            {
                "id": "addy-osmani/agent-skills",
                "name": "Agent Skills",
                "rank": 4,
                "branch": "suite",
                "file": "agent-skills.svg",
            },
            {
                "id": "addy-osmani/sub-skill-1",
                "name": "Sub Skill",
                "rank": 2,
                "branch": "standard",
                "file": "sub-skill-1.svg",
            },
        ],
    }
    named_dict = {s["id"]: s for s in cinfo["namedSkills"]}
    skill_obj, strategy, note = derive_canonical_skill(
        "addy-osmani", "addyosmani/agent-skills", cinfo, named_dict
    )
    assert skill_obj is not None
    assert skill_obj["id"] == "addy-osmani/agent-skills"
    assert strategy == "TOP_SKILL_MATCH"


def test_suite_capstone_preference_when_top_skill_cross_repo():
    """Verify suite capstone in repo is preferred when topSkill is in another repo."""
    cinfo = {
        "repos": ["garrytan/gbrain", "garrytan/gstack"],
        "skillsByRepo": {
            "garrytan/gbrain": ["garrytan/brain-ops", "garrytan/gbrain"],
            "garrytan/gstack": ["garrytan/gstack"],
        },
        "topSkill": "garrytan/gstack",
        "topRank": 5,
        "namedSkills": [
            {
                "id": "garrytan/gstack",
                "name": "GStack",
                "rank": 5,
                "branch": "suite",
                "file": "gstack.svg",
            },
            {
                "id": "garrytan/gbrain",
                "name": "GBrain",
                "rank": 4,
                "branch": "suite",
                "file": "gbrain.svg",
            },
            {
                "id": "garrytan/brain-ops",
                "name": "Brain Ops",
                "rank": 3,
                "branch": "standard",
                "file": "brain-ops.svg",
            },
        ],
    }
    named_dict = {s["id"]: s for s in cinfo["namedSkills"]}
    skill_obj, strategy, note = derive_canonical_skill(
        "garrytan", "garrytan/gbrain", cinfo, named_dict
    )
    assert skill_obj is not None
    assert skill_obj["id"] == "garrytan/gbrain"
    assert strategy == "SUITE_CAPSTONE_PREFERENCE"


def test_ambiguous_repo_resolution():
    """Verify multi-skill repos with cross-repo topSkill and no suite capstone return AMBIGUOUS."""
    cinfo = {
        "repos": ["open-gsd/gsd-core"],
        "skillsByRepo": {
            "open-gsd/gsd-core": ["gsd-build/discuss-phase", "gsd-build/ship"]
        },
        "topSkill": "gsd-build/get-shit-done",
        "topRank": 4,
        "namedSkills": [
            {
                "id": "gsd-build/discuss-phase",
                "name": "Discuss",
                "rank": 3,
                "branch": "standard",
                "file": "discuss-phase.svg",
            },
            {
                "id": "gsd-build/ship",
                "name": "Ship",
                "rank": 3,
                "branch": "standard",
                "file": "ship.svg",
            },
        ],
    }
    named_dict = {s["id"]: s for s in cinfo["namedSkills"]}
    skill_obj, strategy, note = derive_canonical_skill(
        "gsd-build", "open-gsd/gsd-core", cinfo, named_dict
    )
    assert skill_obj is None
    assert strategy == "AMBIGUOUS"


def test_multi_contributor_collision_skipped():
    """Verify repos mapped under multiple contributor handles are marked SKIP."""
    dummy_reg = {
        "generatedAt": "2026-10-10",
        "contributors": {
            "handle1": {
                "repos": ["owner/shared-repo"],
                "skillsByRepo": {"owner/shared-repo": ["h1/skill1"]},
                "topSkill": "h1/skill1",
                "namedSkills": [{"id": "h1/skill1", "file": "skill1.svg"}],
            },
            "handle2": {
                "repos": ["owner/shared-repo"],
                "skillsByRepo": {"owner/shared-repo": ["h2/skill2"]},
                "topSkill": "h2/skill2",
                "namedSkills": [{"id": "h2/skill2", "file": "skill2.svg"}],
            },
        },
    }
    manifest = plan_campaign(dummy_reg, {})
    repo_data = manifest["repositories"]["owner/shared-repo"]
    assert repo_data["status"] == "SKIP"
    assert "Multi-contributor collision" in repo_data["decision_reason"]
    assert set(repo_data["contributor_associations"]) == {"handle1", "handle2"}


def test_gaia_owned_repo_skipped():
    """Verify gaia-research/* internal repos are skipped from external pilot."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})
    assert manifest["repositories"]["gaia-research/skill-fuse"]["status"] == "SKIP"
    assert "Gaia-owned internal repository" in manifest["repositories"]["gaia-research/skill-fuse"]["decision_reason"]


def test_pilot_candidates_resolved_with_valid_urls():
    """Verify the 3 approved pilot candidates have valid URLs and deep links."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})

    pilots = ["pbakaus/impeccable", "safishamsi/graphify", "trailhq/Graft"]
    for p in pilots:
        record = manifest["repositories"][p]
        assert record["status"] == "PILOT_CANDIDATE"
        assert record["badge_url"].startswith("https://gaiaskilltree.com/badges/")
        assert f"?repo={p}" in record["badge_url"]
        assert record["deep_link"].startswith("https://gaiaskilltree.com/named/#explorer/")
        assert record["markdown_preview"].startswith("[![Gaia Skill:")


def test_rerun_idempotence_and_preserves_persistent_state():
    """Verify that re-running planner does not overwrite previous PR outcomes or opt-outs."""
    reg = load_registry(DEFAULT_REGISTRY)
    existing_manifest = {
        "repositories": {
            "pbakaus/impeccable": {
                "status": "ALREADY_ADOPTED",
                "preflight": {"existing_badge": True, "default_branch": "main"},
                "provisioning": {
                    "pr_url": "https://github.com/pbakaus/impeccable/pull/1",
                    "attempted_at": "2026-10-10T12:00:00Z",
                    "outcome": "ADOPTED",
                },
            },
            "santifer/career-ops": {
                "status": "OPTED_OUT",
                "provisioning": {"outcome": "OPTED_OUT"},
            },
        }
    }
    manifest = plan_campaign(reg, existing_manifest)
    
    # Check preserved state
    imp = manifest["repositories"]["pbakaus/impeccable"]
    assert imp["status"] == "ALREADY_ADOPTED"
    assert imp["preflight"]["existing_badge"] is True
    assert imp["provisioning"]["outcome"] == "ADOPTED"
    assert imp["provisioning"]["pr_url"] == "https://github.com/pbakaus/impeccable/pull/1"

    sant = manifest["repositories"]["santifer/career-ops"]
    assert sant["status"] == "OPTED_OUT"
    assert sant["provisioning"]["outcome"] == "OPTED_OUT"
