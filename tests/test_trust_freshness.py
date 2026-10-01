"""Unit tests for Trust Freshness & Materiality Doctrine."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from gaia_cli.trustFreshness import (
    DEFAULT_MAX_ROUTINE_TM_DRIFT,
    evaluateApiFreshness,
    evaluateInstallabilityFreshness,
    evaluateNamedIndexFreshness,
    evaluateTrustLedgerFreshness,
)


def _base_row(skill_id: str = "example/skill", tm: float = 172.43, grade: str = "A") -> dict[str, Any]:
    return {
        "skillId": skill_id,
        "tm": tm,
        "grade": grade,
        "currentStars": "4★",
        "mayStars": "4★",
        "juneStars": "4★",
        "g7Stars": "4★",
        "flag": "",
        "apexResults": None,
        "typeBreakdown": {"github-stars-own": 136.43, "repo-own": 36.0},
        "origin": False,
        "branch": "suite",
    }


def test_trust_ledger_no_drift():
    data = {
        "version": "8.17.1",
        "generatedAt": "2026-10-01T00:00:00Z",
        "rows": [_base_row()],
    }
    is_material, blocking, routine = evaluateTrustLedgerFreshness(data, data)
    assert not is_material
    assert len(blocking) == 0
    assert len(routine) == 0


def test_trust_ledger_routine_adoption_drift_is_warn_only():
    comm = {
        "version": "8.17.1",
        "generatedAt": "2026-10-01T00:00:00Z",
        "rows": [_base_row(tm=172.43)],
    }
    fresh = {
        "version": "8.17.1",
        "generatedAt": "2026-10-01T06:00:00Z",
        "rows": [_base_row(tm=174.68)],
    }
    is_material, blocking, routine = evaluateTrustLedgerFreshness(comm, fresh)
    assert not is_material
    assert len(blocking) == 0
    assert len(routine) == 1
    assert "172.43 -> 174.68" in routine[0]


def test_trust_ledger_grade_change_blocks():
    comm = {
        "version": "8.17.1",
        "generatedAt": "2026-10-01T00:00:00Z",
        "rows": [_base_row(tm=172.43, grade="A")],
    }
    fresh = {
        "version": "8.17.1",
        "generatedAt": "2026-10-01T06:00:00Z",
        "rows": [_base_row(tm=252.00, grade="S")],
    }
    is_material, blocking, _ = evaluateTrustLedgerFreshness(comm, fresh)
    assert is_material
    assert any("overall Trust Grade changed" in b for b in blocking)


def test_trust_ledger_apex_change_blocks():
    r1 = _base_row()
    r2 = _base_row()
    r2["apexResults"] = {"passed": True}
    comm = {"rows": [r1]}
    fresh = {"rows": [r2]}
    is_material, blocking, _ = evaluateTrustLedgerFreshness(comm, fresh)
    assert is_material
    assert any("apexResults changed" in b for b in blocking)


def test_trust_ledger_star_badge_change_blocks():
    r1 = _base_row()
    r2 = _base_row()
    r2["currentStars"] = "5★"
    comm = {"rows": [r1]}
    fresh = {"rows": [r2]}
    is_material, blocking, _ = evaluateTrustLedgerFreshness(comm, fresh)
    assert is_material
    assert any("currentStars changed" in b for b in blocking)


def test_trust_ledger_material_staleness_blocks():
    comm = {
        "rows": [_base_row(tm=100.0)],
    }
    fresh = {
        "rows": [_base_row(tm=135.0)],  # 35 point drift >= 30 threshold
    }
    is_material, blocking, _ = evaluateTrustLedgerFreshness(comm, fresh, max_tm_drift=30.0)
    assert is_material
    assert any("material staleness threshold" in b for b in blocking)


def test_trust_ledger_skill_set_change_blocks():
    comm = {"rows": [_base_row("example/skill-a")]}
    fresh = {"rows": [_base_row("example/skill-b")]}
    is_material, blocking, _ = evaluateTrustLedgerFreshness(comm, fresh)
    assert is_material
    assert any("skills added" in b or "skills removed" in b for b in blocking)


def test_trust_ledger_explicit_review_event_blocks(tmp_path: Path):
    skill_file = tmp_path / "registry" / "named" / "example" / "taste-skill.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "---\n"
        "id: example/taste-skill\n"
        "timeline:\n"
        "  - timestamp: '2026-10-02T10:00:00Z'\n"
        "    action: recalibrate_trust_magnitude\n"
        "    contributor: reviewer1\n"
        "---\n",
        encoding="utf-8",
    )
    comm = {
        "generatedAt": "2026-10-01T00:00:00Z",
        "rows": [_base_row("example/taste-skill", tm=172.43)],
    }
    fresh = {
        "generatedAt": "2026-10-02T12:00:00Z",
        "rows": [_base_row("example/taste-skill", tm=174.68)],
    }
    is_material, blocking, _ = evaluateTrustLedgerFreshness(comm, fresh, repo_root=tmp_path)
    assert is_material
    assert any("explicit review event" in b for b in blocking)


def test_installability_content_digest_only_is_warn_only():
    comm = {
        "schema": "observation-v1",
        "indexPath": "docs/graph/named/index.json",
        "observations": [],
        "skills": {
            "example/skill": {
                "state": "unknown",
                "reason": "not-observed",
                "observationDigest": None,
                "observedAt": None,
                "currentSourceRoute": {"url": "https://github.com/example/repo"},
                "currentSkillContentSha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "observedSourceRoute": None,
                "observedSkillContentSha256": None,
                "resolvedRevision": None,
                "deliveredContentSha256": None,
            }
        },
    }
    fresh = json.loads(json.dumps(comm))
    fresh["skills"]["example/skill"]["currentSkillContentSha256"] = (
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    is_material, blocking, routine = evaluateInstallabilityFreshness(comm, fresh)
    assert not is_material
    assert len(blocking) == 0
    assert len(routine) == 1


def test_installability_state_change_blocks():
    comm = {
        "schema": "observation-v1",
        "indexPath": "docs/graph/named/index.json",
        "observations": [],
        "skills": {
            "example/skill": {
                "state": "unknown",
                "reason": "not-observed",
                "observationDigest": None,
                "observedAt": None,
                "currentSourceRoute": {"url": "https://github.com/example/repo"},
                "currentSkillContentSha256": "aaaa",
                "observedSourceRoute": None,
                "observedSkillContentSha256": None,
                "resolvedRevision": None,
                "deliveredContentSha256": None,
            }
        },
    }
    fresh = json.loads(json.dumps(comm))
    fresh["skills"]["example/skill"]["state"] = "pass"
    is_material, blocking, _ = evaluateInstallabilityFreshness(comm, fresh)
    assert is_material
    assert any("state changed" in b for b in blocking)


def test_named_index_evidence_only_is_warn_only():
    comm = {
        "buckets": {
            "generic-a": [
                {
                    "id": "contributor/skill",
                    "name": "skill",
                    "genericSkillRef": "generic-a",
                    "level": "3★",
                    "origin": True,
                    "status": "named",
                    "title": "Skill Title",
                    "evidence": [{"type": "github-stars-own", "stars": 100}],
                }
            ]
        }
    }
    fresh = json.loads(json.dumps(comm))
    fresh["buckets"]["generic-a"][0]["evidence"][0]["stars"] = 150
    is_material, blocking, routine = evaluateNamedIndexFreshness(comm, fresh)
    assert not is_material
    assert len(blocking) == 0
    assert len(routine) == 1


def test_named_index_structural_field_blocks():
    comm = {
        "buckets": {
            "generic-a": [
                {
                    "id": "contributor/skill",
                    "name": "skill",
                    "genericSkillRef": "generic-a",
                    "level": "3★",
                    "origin": True,
                    "status": "named",
                    "title": "Skill Title",
                    "evidence": [{"type": "github-stars-own", "stars": 100}],
                }
            ]
        }
    }
    fresh = json.loads(json.dumps(comm))
    fresh["buckets"]["generic-a"][0]["title"] = "Changed Title"
    is_material, blocking, _ = evaluateNamedIndexFreshness(comm, fresh)
    assert is_material
    assert any("structural field 'title' changed" in b for b in blocking)


def test_api_freshness_routine_drift(tmp_path: Path):
    c_dir = tmp_path / "committed"
    o_dir = tmp_path / "out"
    c_dir.mkdir()
    o_dir.mkdir()

    (c_dir / "skills.json").write_text('{"count": 1, "tm": 172.43}', encoding="utf-8")
    (o_dir / "skills.json").write_text('{"count": 1, "tm": 174.68}', encoding="utf-8")

    is_material, blocking, routine = evaluateApiFreshness(
        c_dir, o_dir, ["skills.json"], ledger_is_routine=True
    )
    assert not is_material
    assert len(blocking) == 0
    assert "skills.json" in routine


def test_api_freshness_missing_file_blocks(tmp_path: Path):
    c_dir = tmp_path / "committed"
    o_dir = tmp_path / "out"
    c_dir.mkdir()
    o_dir.mkdir()

    (o_dir / "new.json").write_text('{"foo": 1}', encoding="utf-8")

    is_material, blocking, _ = evaluateApiFreshness(
        c_dir, o_dir, ["new.json"], ledger_is_routine=True
    )
    assert is_material
    assert any("missing in committed" in b for b in blocking)
