"""Tests for scripts/plan_badge_provisioning.py (Gaia Badge Provisioning Campaign #1817)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.plan_badge_provisioning import (
    DEFAULT_BADGES_INDEX,
    DEFAULT_MANIFEST,
    DEFAULT_REGISTRY,
    PRESENTATION_TIERS,
    derive_canonical_skill,
    determine_badge_presentation,
    detect_honesty_mode,
    generate_badge_url,
    load_existing_manifest,
    load_registry,
    plan_campaign,
    record_outcome,
    resolve_eligible_skills,
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
        assert record["eligibility"] == "PILOT_CANDIDATE"
        assert record["badge_url"].startswith("https://gaiaskilltree.com/badges/")
        assert "/_assets/" in record["badge_url"]
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


def test_detect_honesty_mode_active():
    """Verify honesty mode detection reads true from docs/badges/index.html."""
    mode = detect_honesty_mode(DEFAULT_BADGES_INDEX)
    assert mode is True


def test_detect_honesty_mode_inactive(tmp_path: Path):
    """Verify honesty mode detection reads false when configured off."""
    html = tmp_path / "index.html"
    html.write_text("const HONESTY_MODE = false;\n", encoding="utf-8")
    assert detect_honesty_mode(html) is False


def test_detect_honesty_mode_fails_closed(tmp_path: Path):
    """Verify honesty mode detection fails closed if missing, unreadable, or ambiguous."""
    missing = tmp_path / "nonexistent.html"
    with pytest.raises(FileNotFoundError):
        detect_honesty_mode(missing)

    ambiguous = tmp_path / "ambiguous.html"
    ambiguous.write_text("const HONESTY_MODE = true;\nconst HONESTY_MODE = false;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Ambiguous or missing"):
        detect_honesty_mode(ambiguous)

    no_constant = tmp_path / "none.html"
    no_constant.write_text("const OTHER = true;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Ambiguous or missing"):
        detect_honesty_mode(no_constant)


def test_badge_url_generation_modes():
    """Verify public badge URLs include _assets in honesty mode and retain ?repo= in both modes."""
    url_honesty = generate_badge_url("pbakaus", "impeccable.svg", "pbakaus/impeccable", honesty_mode=True)
    assert url_honesty == "https://gaiaskilltree.com/badges/_assets/pbakaus/impeccable.svg?repo=pbakaus/impeccable"

    url_worker = generate_badge_url("pbakaus", "impeccable.svg", "pbakaus/impeccable", honesty_mode=False)
    assert url_worker == "https://gaiaskilltree.com/badges/pbakaus/impeccable.svg?repo=pbakaus/impeccable"


def test_manifest_fails_closed_on_corrupt_data(tmp_path: Path):
    """Verify manifest loading fails closed on corrupt JSON or invalid structure with recovery."""
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text("{corrupt json ...", encoding="utf-8")

    with pytest.raises(ValueError, match="Corrupt manifest JSON"):
        load_existing_manifest(manifest_file)

    manifest_file.write_text("[\"not a dict\"]", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid manifest structure"):
        load_existing_manifest(manifest_file)

    # Recovery: write valid manifest
    valid_data = {"campaign": "test", "repositories": {}}
    manifest_file.write_text(json.dumps(valid_data), encoding="utf-8")
    recovered = load_existing_manifest(manifest_file)
    assert recovered["campaign"] == "test"


def test_lifecycle_preserves_contacted_and_outbound_states():
    """Verify replanning preserves PR_OPEN, ADOPTED, DECLINED, OPTED_OUT and never reverts to dispatchable."""
    reg = load_registry(DEFAULT_REGISTRY)
    existing_manifest = {
        "repositories": {
            "pbakaus/impeccable": {
                "status": "PR_OPEN",
                "provisioning": {
                    "approved": True,
                    "approved_by": "@mbtiongson1",
                    "attempts": 1,
                    "attempted_at": "2026-10-10T10:00:00Z",
                    "pr_url": "https://github.com/pbakaus/impeccable/pull/42",
                    "outcome": "PR_OPEN",
                },
            },
            "safishamsi/graphify": {
                "status": "DECLINED",
                "provisioning": {
                    "attempts": 1,
                    "outcome": "DECLINED",
                    "decision_notes": "Maintainer opted not to add badge",
                },
            },
            "trailhq/Graft": {
                "status": "ADOPTED",
                "provisioning": {
                    "attempts": 1,
                    "pr_url": "https://github.com/trailhq/graft/pull/1",
                    "outcome": "ADOPTED",
                },
            },
            "addyosmani/agent-skills": {
                "status": "OPTED_OUT",
                "provisioning": {
                    "outcome": "OPTED_OUT",
                },
            },
        }
    }

    manifest = plan_campaign(reg, existing_manifest)

    # pbakaus/impeccable must remain PR_OPEN, with eligibility=PILOT_CANDIDATE
    imp = manifest["repositories"]["pbakaus/impeccable"]
    assert imp["status"] == "PR_OPEN"
    assert imp["eligibility"] == "PILOT_CANDIDATE"
    assert imp["provisioning"]["attempts"] == 1
    assert imp["provisioning"]["pr_url"] == "https://github.com/pbakaus/impeccable/pull/42"

    # safishamsi/graphify must remain DECLINED, never reverting to PILOT_CANDIDATE
    graph = manifest["repositories"]["safishamsi/graphify"]
    assert graph["status"] == "DECLINED"
    assert graph["eligibility"] == "PILOT_CANDIDATE"
    assert graph["provisioning"]["outcome"] == "DECLINED"

    # trailhq/Graft must remain ADOPTED
    graft = manifest["repositories"]["trailhq/Graft"]
    assert graft["status"] == "ADOPTED"
    assert graft["eligibility"] == "PILOT_CANDIDATE"

    # addyosmani/agent-skills must remain OPTED_OUT
    addy = manifest["repositories"]["addyosmani/agent-skills"]
    assert addy["status"] == "OPTED_OUT"
    assert addy["eligibility"] == "READY"


def test_record_outcome_human_approval_gate_and_pr_submission():
    """Verify outcome recording enforces approval gate and tracks attempts/PR URLs."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})

    # Attempting to record PR_OPEN without approval must fail
    with pytest.raises(ValueError, match="cannot transition to PR_OPEN without explicit human approval"):
        record_outcome(
            manifest_data=manifest,
            repo="pbakaus/impeccable",
            status="PR_OPEN",
            pr_url="https://github.com/pbakaus/impeccable/pull/1",
        )

    # Record human approval
    record_outcome(
        manifest_data=manifest,
        repo="pbakaus/impeccable",
        status="APPROVED",
        approved_by="@founder",
        notes="Authorized Phase 1 pilot",
    )
    repo_state = manifest["repositories"]["pbakaus/impeccable"]
    assert repo_state["status"] == "APPROVED"
    assert repo_state["provisioning"]["approved"] is True
    assert repo_state["provisioning"]["approved_by"] == "@founder"

    # Now recording PR_OPEN succeeds
    record_outcome(
        manifest_data=manifest,
        repo="pbakaus/impeccable",
        status="PR_OPEN",
        pr_url="https://github.com/pbakaus/impeccable/pull/1",
        notes="PR dispatched",
    )
    repo_state = manifest["repositories"]["pbakaus/impeccable"]
    assert repo_state["status"] == "PR_OPEN"
    assert repo_state["provisioning"]["attempts"] == 1
    assert repo_state["provisioning"]["pr_url"] == "https://github.com/pbakaus/impeccable/pull/1"
    assert len(repo_state["provisioning"]["history"]) == 2


def test_record_outcome_duplicate_dispatch_prevented():
    """Verify recording PR_OPEN on a repo that already has an open PR is blocked."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})

    record_outcome(
        manifest_data=manifest,
        repo="safishamsi/graphify",
        status="APPROVED",
        approved_by="@founder",
    )
    record_outcome(
        manifest_data=manifest,
        repo="safishamsi/graphify",
        status="PR_OPEN",
        pr_url="https://github.com/safishamsi/graphify/pull/10",
    )

    # Second PR_OPEN attempt must raise ValueError
    with pytest.raises(ValueError, match="Duplicate external dispatch prevented"):
        record_outcome(
            manifest_data=manifest,
            repo="safishamsi/graphify",
            status="PR_OPEN",
            pr_url="https://github.com/safishamsi/graphify/pull/11",
        )


def test_record_outcome_terminal_states_locked():
    """Verify terminal states (ADOPTED, DECLINED, OPTED_OUT, NO_RESPONSE) cannot be transitioned."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})

    # Mark ADOPTED
    record_outcome(manifest_data=manifest, repo="trailhq/Graft", status="ADOPTED")
    with pytest.raises(ValueError, match="is in terminal state 'ADOPTED'"):
        record_outcome(manifest_data=manifest, repo="trailhq/Graft", status="PR_OPEN", pr_url="https://github.com/trailhq/graft/pull/1")

    # Mark DECLINED
    record_outcome(manifest_data=manifest, repo="pbakaus/impeccable", status="DECLINED")
    with pytest.raises(ValueError, match="is in terminal state 'DECLINED'"):
        record_outcome(manifest_data=manifest, repo="pbakaus/impeccable", status="READY")

    # Mark OPTED_OUT
    record_outcome(manifest_data=manifest, repo="addyosmani/agent-skills", status="OPTED_OUT")
    with pytest.raises(ValueError, match="is in terminal state 'OPTED_OUT'"):
        record_outcome(manifest_data=manifest, repo="addyosmani/agent-skills", status="APPROVED", approved_by="@founder")

    # Mark NO_RESPONSE
    record_outcome(manifest_data=manifest, repo="safishamsi/graphify", status="NO_RESPONSE", notes="Unmerged after timeout")
    with pytest.raises(ValueError, match="is in terminal state 'NO_RESPONSE'"):
        record_outcome(manifest_data=manifest, repo="safishamsi/graphify", status="PR_OPEN", pr_url="https://github.com/safishamsi/graphify/pull/12")


def test_multi_badge_single_skill_repo():
    """Verify single-skill repository resolves to tier SINGLE with exactly 1 badge."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})

    rec = manifest["repositories"]["pbakaus/impeccable"]
    assert rec["eligible_skill_count"] == 1
    assert len(rec["eligible_skills"]) == 1
    assert rec["offered_skills"] == ["pbakaus/impeccable"]

    pres = rec["badge_presentation"]
    assert pres["tier"] == "SINGLE"
    assert pres["eligible_count"] == 1
    assert pres["displayed_count"] == 1
    assert pres["is_curated_selection"] is False
    assert pres["displayed_skill_ids"] == ["pbakaus/impeccable"]
    assert pres["markdown"].startswith("[![Gaia Skill: Impeccable]")
    assert pres["markdown"] == rec["markdown_preview"]
    assert "<img" in pres["html"]


def test_multi_badge_two_to_four_skill_repo():
    """Verify 2-4 skill repository resolves to tier COMPACT_ROW with all badges."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})

    rec = manifest["repositories"]["disler/fusion-harness"]
    assert rec["eligible_skill_count"] == 4
    assert len(rec["eligible_skills"]) == 4
    assert len(rec["offered_skills"]) == 4

    pres = rec["badge_presentation"]
    assert pres["tier"] == "COMPACT_ROW"
    assert pres["eligible_count"] == 4
    assert pres["displayed_count"] == 4
    assert pres["is_curated_selection"] is False
    assert len(pres["displayed_skill_ids"]) == 4
    # Compact row is space-separated markdown badges on one row
    assert " " in pres["markdown"]
    assert pres["markdown"].count("[![Gaia Skill:") == 4
    assert pres["html"].count("<img") == 4


def test_multi_badge_five_to_eight_skill_repo():
    """Verify 5-8 skill repository resolves to tier LABELED_SECTION."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})

    rec = manifest["repositories"]["firecrawl/skills"]
    assert rec["eligible_skill_count"] == 5
    assert len(rec["eligible_skills"]) == 5

    pres = rec["badge_presentation"]
    assert pres["tier"] == "LABELED_SECTION"
    assert pres["eligible_count"] == 5
    assert pres["displayed_count"] == 5
    assert pres["is_curated_selection"] is False
    assert "### Gaia Skill Tree Recognition" in pres["markdown"]
    assert "gaia-badge-section" in pres["html"]


def test_multi_badge_nine_plus_skill_repo():
    """Verify 9+ skill repository resolves to tier CURATED_COLLECTION with collection link."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})

    rec = manifest["repositories"]["leonxlnx/taste-skill"]
    assert rec["eligible_skill_count"] == 12
    assert len(rec["eligible_skills"]) == 12
    # Full eligible skill set must be retained in offered_skills
    assert len(rec["offered_skills"]) == 12

    pres = rec["badge_presentation"]
    assert pres["tier"] == "CURATED_COLLECTION"
    assert pres["eligible_count"] == 12
    assert pres["displayed_count"] == 1
    assert pres["is_curated_selection"] is True
    assert pres["displayed_skill_ids"] == ["leonxlnx/taste-skill"]
    # Curated display displays top badge + collection link
    assert "Explore all 12 recognized skills" in pres["markdown"]
    assert "https://gaiaskilltree.com/u/leonxlnx/" in pres["markdown"]
    assert "<a href=\"https://gaiaskilltree.com/u/leonxlnx/\">" in pres["html"]


def test_multi_badge_duplicate_skills_deduplicated():
    """Verify duplicate skill entries in skillsByRepo are deduplicated."""
    cinfo = {
        "repos": ["owner/repo"],
        "skillsByRepo": {
            "owner/repo": ["owner/skill-a", "owner/skill-a", "owner/skill-b"]
        },
        "topSkill": "owner/skill-a",
        "namedSkills": [
            {"id": "owner/skill-a", "name": "Skill A", "rank": 3, "file": "skill-a.svg"},
            {"id": "owner/skill-b", "name": "Skill B", "rank": 2, "file": "skill-b.svg"},
        ],
    }
    named_dict = {s["id"]: s for s in cinfo["namedSkills"]}
    eligible = resolve_eligible_skills("owner", "owner/repo", cinfo, named_dict, honesty_mode=True, check_assets=False)
    assert len(eligible) == 2
    assert [s["id"] for s in eligible] == ["owner/skill-a", "owner/skill-b"]


def test_multi_badge_variants_vs_distinct_skills():
    """Verify that seal badge variants are not treated as separate earned skills."""
    cinfo = {
        "repos": ["owner/repo"],
        "skillsByRepo": {
            "owner/repo": ["owner/skill-1"]
        },
        "topSkill": "owner/skill-1",
        "namedSkills": [
            {
                "id": "owner/skill-1",
                "name": "Skill One",
                "rank": 4,
                "file": "skill-1.svg",
                "fileSeal": "skill-1-seal.svg",
            }
        ],
    }
    named_dict = {s["id"]: s for s in cinfo["namedSkills"]}
    eligible = resolve_eligible_skills("owner", "owner/repo", cinfo, named_dict, honesty_mode=True, check_assets=False)
    # Exactly one earned skill, not two
    assert len(eligible) == 1
    assert eligible[0]["id"] == "owner/skill-1"
    assert eligible[0]["file"] == "skill-1.svg"


def test_multi_badge_exact_offered_skill_ledger_recording():
    """Verify outcome recording records offered_skills and presentation tier in ledger history."""
    reg = load_registry(DEFAULT_REGISTRY)
    manifest = plan_campaign(reg, {})

    # Record approval on a multi-badge repo (disler/fusion-harness, 4 skills)
    record_outcome(
        manifest_data=manifest,
        repo="disler/fusion-harness",
        status="APPROVED",
        approved_by="@founder",
        notes="Approved multi-badge outreach",
    )
    rec = manifest["repositories"]["disler/fusion-harness"]
    prov = rec["provisioning"]
    assert prov["approved"] is True
    assert prov["chosen_presentation"] == "COMPACT_ROW"
    assert len(prov["offered_skills"]) == 4

    # Record PR_OPEN
    record_outcome(
        manifest_data=manifest,
        repo="disler/fusion-harness",
        status="PR_OPEN",
        pr_url="https://github.com/disler/fusion-harness/pull/1",
        notes="Dispatched multi-badge PR",
    )
    assert prov["outcome"] == "PR_OPEN"
    assert prov["attempts"] == 1
    assert len(prov["history"]) == 2

    # Check history entries
    h_appr = prov["history"][0]
    assert h_appr["presentation_tier"] == "COMPACT_ROW"
    assert len(h_appr["offered_skills"]) == 4

    h_pr = prov["history"][1]
    assert h_pr["presentation_tier"] == "COMPACT_ROW"
    assert len(h_pr["offered_skills"]) == 4
    assert h_pr["pr_url"] == "https://github.com/disler/fusion-harness/pull/1"


def test_multi_badge_fail_closed_on_missing_asset(tmp_path: Path):
    """Verify resolver fails closed when an SVG asset is missing on disk."""
    cinfo = {
        "repos": ["owner/repo"],
        "skillsByRepo": {"owner/repo": ["owner/missing-asset-skill"]},
        "topSkill": "owner/missing-asset-skill",
        "namedSkills": [
            {
                "id": "owner/missing-asset-skill",
                "name": "Missing",
                "rank": 3,
                "file": "nonexistent.svg",
            }
        ],
    }
    named_dict = {s["id"]: s for s in cinfo["namedSkills"]}
    with pytest.raises(FileNotFoundError, match="Missing SVG badge asset"):
        resolve_eligible_skills(
            "owner",
            "owner/repo",
            cinfo,
            named_dict,
            honesty_mode=True,
            assets_root=tmp_path,
            check_assets=True,
        )


def test_case_insensitive_lookup_preserves_state():
    """Verify that replanning preserves state even if casing differs between registry and manifest."""
    reg = load_registry(DEFAULT_REGISTRY)
    existing_manifest = {
        "repositories": {
            "TRAILHQ/GRAFT": {
                "status": "PR_OPEN",
                "provisioning": {
                    "approved": True,
                    "attempts": 1,
                    "pr_url": "https://github.com/trailhq/graft/pull/99",
                },
            }
        }
    }
    manifest = plan_campaign(reg, existing_manifest)
    graft_record = manifest["repositories"]["trailhq/Graft"]
    assert graft_record["status"] == "PR_OPEN"
    assert graft_record["provisioning"]["pr_url"] == "https://github.com/trailhq/graft/pull/99"

