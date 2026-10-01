"""Unit tests for Trust Freshness & Materiality Doctrine."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from gaia_cli.trustFreshness import (
    DEFAULT_MAX_ROUTINE_TM_DRIFT,
    compareEvidenceRows,
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


def test_compare_evidence_rows_added_or_removed_blocks():
    c = [{"type": "github-stars-own", "stars": 100, "grade": "B", "source": "https://example.com"}]
    f = [
        {"type": "github-stars-own", "stars": 100, "grade": "B", "source": "https://example.com"},
        {"type": "repo-own", "commits": 10, "grade": "C", "source": "https://example.com"},
    ]
    is_material, blocking, _ = compareEvidenceRows(c, f)
    assert is_material
    assert any("evidence row count changed" in b for b in blocking)

    is_material2, blocking2, _ = compareEvidenceRows(f, c)
    assert is_material2
    assert any("evidence row count changed" in b for b in blocking2)


def test_compare_evidence_rows_retyped_blocks():
    c = [{"type": "github-stars-own", "stars": 100, "grade": "B", "source": "https://example.com"}]
    f = [{"type": "repo-own", "commits": 10, "grade": "B", "source": "https://example.com"}]
    is_material, blocking, _ = compareEvidenceRows(c, f)
    assert is_material
    assert any("evidence type changed" in b for b in blocking)


def test_compare_evidence_rows_regraded_blocks():
    c = [{"type": "github-stars-own", "stars": 100, "grade": "B", "source": "https://example.com"}]
    f = [{"type": "github-stars-own", "stars": 100, "grade": "A", "source": "https://example.com"}]
    is_material, blocking, _ = compareEvidenceRows(c, f)
    assert is_material
    assert any("evidence grade changed" in b for b in blocking)


def test_compare_evidence_rows_non_volatile_modified_blocks():
    c = [{"type": "repo-own", "commits": 100, "contributors": 5, "grade": "B", "source": "https://example.com"}]
    f = [{"type": "repo-own", "commits": 150, "contributors": 5, "grade": "B", "source": "https://example.com"}]
    is_material, blocking, _ = compareEvidenceRows(c, f)
    assert is_material
    assert any("non-volatile evidence row of type 'repo-own' was modified" in b for b in blocking)


def test_compare_evidence_rows_volatile_counter_only_is_routine():
    c = [{"type": "github-stars-own", "stars": 79067, "grade": "A", "source": "https://example.com", "notes": "79k"}]
    f = [
        {
            "type": "github-stars-own",
            "stars": 91660,
            "grade": "A",
            "source": "https://example.com",
            "notes": "91k",
            "updatedAt": "2026-10-01",
        }
    ]
    is_material, blocking, routine = compareEvidenceRows(c, f)
    assert not is_material
    assert len(blocking) == 0
    assert len(routine) == 1


def test_named_index_regraded_evidence_blocks():
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
                    "evidence": [{"type": "github-stars-own", "stars": 100, "grade": "B", "source": "https://example.com"}],
                }
            ]
        }
    }
    fresh = json.loads(json.dumps(comm))
    fresh["buckets"]["generic-a"][0]["evidence"][0]["grade"] = "A"
    is_material, blocking, _ = evaluateNamedIndexFreshness(comm, fresh)
    assert is_material
    assert any("evidence grade changed" in b for b in blocking)


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
                    "evidence": [{"type": "github-stars-own", "stars": 100, "grade": "B", "source": "https://example.com"}],
                }
            ]
        }
    }
    fresh = json.loads(json.dumps(comm))
    fresh["buckets"]["generic-a"][0]["evidence"][0]["stars"] = 150
    fresh["buckets"]["generic-a"][0]["evidence"][0]["updatedAt"] = "2026-10-01"
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
                    "evidence": [{"type": "github-stars-own", "stars": 100, "grade": "B", "source": "https://example.com"}],
                }
            ]
        }
    }
    fresh = json.loads(json.dumps(comm))
    fresh["buckets"]["generic-a"][0]["title"] = "Changed Title"
    is_material, blocking, _ = evaluateNamedIndexFreshness(comm, fresh)
    assert is_material
    assert any("structural field 'title' changed" in b for b in blocking)


def test_installability_content_digest_body_change_blocks(tmp_path: Path):
    # Initialize a mock git repo to test proof of volatile-only delta
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)

    skill_path = tmp_path / "registry" / "named" / "example" / "skill.md"
    skill_path.parent.mkdir(parents=True)
    initial_content = (
        "---\n"
        "id: example/skill\n"
        "evidence:\n"
        "  - type: github-stars-own\n"
        "    stars: 100\n"
        "    grade: B\n"
        "    source: https://example.com\n"
        "---\n\n"
        "# Initial Body\n"
    )
    skill_path.write_text(initial_content, encoding="utf-8")
    initial_sha = hashlib.sha256(initial_content.encode("utf-8")).hexdigest()

    idx_path = tmp_path / "docs" / "graph" / "installability" / "index.json"
    idx_path.parent.mkdir(parents=True)
    idx_content = json.dumps({"skills": {"example/skill": {"currentSkillContentSha256": initial_sha}}})
    idx_path.write_text(idx_content, encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True)

    # Edit the markdown body (meaningful content edit!)
    edited_content = initial_content.replace("# Initial Body", "# Edited Body Description")
    skill_path.write_text(edited_content, encoding="utf-8")
    edited_sha = hashlib.sha256(edited_content.encode("utf-8")).hexdigest()

    comm_doc = {
        "observations": [],
        "skills": {
            "example/skill": {
                "state": "unknown",
                "reason": "not-observed",
                "currentSkillContentSha256": initial_sha,
            }
        },
    }
    fresh_doc = {
        "observations": [],
        "skills": {
            "example/skill": {
                "state": "unknown",
                "reason": "not-observed",
                "currentSkillContentSha256": edited_sha,
            }
        },
    }

    is_material, blocking, _ = evaluateInstallabilityFreshness(comm_doc, fresh_doc, repo_root=tmp_path)
    assert is_material
    assert any("markdown body/description content was edited" in b for b in blocking)


def test_installability_content_digest_volatile_delta_proven(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)

    skill_path = tmp_path / "registry" / "named" / "example" / "skill.md"
    skill_path.parent.mkdir(parents=True)
    initial_content = (
        "---\n"
        "id: example/skill\n"
        "evidence:\n"
        "  - type: github-stars-own\n"
        "    stars: 100\n"
        "    grade: B\n"
        "    source: https://example.com\n"
        "---\n\n"
        "# Preserved Body\n"
    )
    skill_path.write_text(initial_content, encoding="utf-8")
    initial_sha = hashlib.sha256(initial_content.encode("utf-8")).hexdigest()

    idx_path = tmp_path / "docs" / "graph" / "installability" / "index.json"
    idx_path.parent.mkdir(parents=True)
    idx_content = json.dumps({"skills": {"example/skill": {"currentSkillContentSha256": initial_sha}}})
    idx_path.write_text(idx_content, encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True)

    # Update only the stars counter
    updated_content = initial_content.replace("stars: 100", "stars: 150")
    skill_path.write_text(updated_content, encoding="utf-8")
    updated_sha = hashlib.sha256(updated_content.encode("utf-8")).hexdigest()

    comm_doc = {
        "observations": [],
        "skills": {
            "example/skill": {
                "state": "unknown",
                "reason": "not-observed",
                "currentSkillContentSha256": initial_sha,
            }
        },
    }
    fresh_doc = {
        "observations": [],
        "skills": {
            "example/skill": {
                "state": "unknown",
                "reason": "not-observed",
                "currentSkillContentSha256": updated_sha,
            }
        },
    }

    is_material, blocking, routine = evaluateInstallabilityFreshness(comm_doc, fresh_doc, repo_root=tmp_path)
    assert not is_material
    assert len(blocking) == 0
    assert len(routine) == 1
    assert "proven limited to volatile Trust fields" in routine[0]


def test_api_freshness_requires_proven_ledger_routine(tmp_path: Path):
    c_dir = tmp_path / "committed"
    o_dir = tmp_path / "out"
    c_dir.mkdir()
    o_dir.mkdir()

    (c_dir / "health.json").write_text('{"status": "ok"}', encoding="utf-8")
    (o_dir / "health.json").write_text('{"status": "ok", "version": "8.17.1"}', encoding="utf-8")

    # Defaults to ledger_is_routine=False -> MUST BLOCK
    is_material, blocking, _ = evaluateApiFreshness(c_dir, o_dir, ["health.json"], ledger_is_routine=False)
    assert is_material
    assert any("trust ledger drift is not proven routine" in b for b in blocking)


def test_api_freshness_structural_field_in_skill_blocks(tmp_path: Path):
    c_dir = tmp_path / "committed" / "skills" / "example"
    o_dir = tmp_path / "out" / "skills" / "example"
    c_dir.mkdir(parents=True)
    o_dir.mkdir(parents=True)

    c_file = c_dir / "skill.json"
    o_file = o_dir / "skill.json"
    c_file.write_text(
        json.dumps({"id": "example/skill", "name": "original-name", "trustMagnitude": 100.0}),
        encoding="utf-8",
    )
    o_file.write_text(
        json.dumps({"id": "example/skill", "name": "mutated-name", "trustMagnitude": 102.0}),
        encoding="utf-8",
    )

    is_material, blocking, _ = evaluateApiFreshness(
        tmp_path / "committed",
        tmp_path / "out",
        ["skills/example/skill.json"],
        ledger_is_routine=True,
    )
    assert is_material
    assert any("structural field 'name' changed" in b for b in blocking)

def test_explicit_review_blocks_even_when_tm_does_not_move(tmp_path: Path):
    skill_file = tmp_path / "registry" / "named" / "example" / "skill.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "---\n"
        "id: example/skill\n"
        "timeline:\n"
        "  - timestamp: '2026-10-02T10:00:00Z'\n"
        "    action: recalibrate_trust_magnitude\n"
        "    contributor: reviewer1\n"
        "---\n",
        encoding="utf-8",
    )
    comm = {
        "generatedAt": "2026-10-01T00:00:00Z",
        "rows": [_base_row("example/skill", tm=172.43)],
    }
    fresh = {
        "generatedAt": "2026-10-02T12:00:00Z",
        "rows": [_base_row("example/skill", tm=172.43)],
    }
    is_material, blocking, routine = evaluateTrustLedgerFreshness(
        comm, fresh, repo_root=tmp_path
    )
    assert is_material
    assert routine == []
    assert any("explicit review event" in b for b in blocking)


def test_installability_digest_change_without_proof_blocks():
    comm = {
        "observations": [],
        "skills": {
            "example/skill": {
                "state": "unknown",
                "reason": "not-observed",
                "observationDigest": None,
                "observedAt": None,
                "currentSourceRoute": None,
                "currentSkillContentSha256": "a" * 64,
                "observedSourceRoute": None,
                "observedSkillContentSha256": None,
                "resolvedRevision": None,
                "deliveredContentSha256": None,
            }
        },
    }
    fresh = json.loads(json.dumps(comm))
    fresh["skills"]["example/skill"]["currentSkillContentSha256"] = "b" * 64

    is_material, blocking, routine = evaluateInstallabilityFreshness(
        comm, fresh, repo_root=None
    )
    assert is_material
    assert routine == []
    assert any("could not be verified" in b for b in blocking)

