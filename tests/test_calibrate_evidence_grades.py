"""Tests for `gaia dev calibrate-evidence-grades` — end-to-end CLI behaviour.

Covers:
- Dry-run writes nothing but returns correct counts
- Live run correctly grades rows using per-type thresholds + gradeCeiling
- trustNumber fallback (rows without magnitude drivers)
- Auto-derived rows are skipped
- No-type rows are skipped
- Idempotence: second run produces zero diffs
- S-capable types (arxiv, peer-review) reach S grade
- gradeCeiling clamps correctly (repo-own never exceeds B)
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev import calibrate_evidence_grades_command


# ── Fixtures ─────────────────────────────────────────────────────────────────

MINIMAL_META = {
    "evidence": {
        "gradeThresholds": {"S": 250, "A": 100, "B": 50, "C": 20},
        "types": [
            {"id": "arxiv",                "gradeCeiling": "S"},
            {"id": "peer-review",          "gradeCeiling": "S"},
            {"id": "github-stars-own",     "gradeCeiling": "S"},
            {"id": "benchmark-result",     "gradeCeiling": "S"},
            {"id": "verifier-attestation", "gradeCeiling": "S"},
            {"id": "proxy-containment",    "gradeCeiling": "S"},
            {"id": "fusion-recipe",        "gradeCeiling": "S"},
            {"id": "repo-own",             "gradeCeiling": "B"},
            {"id": "self-attestation",     "gradeCeiling": "C"},
            {"id": "social-signal",        "gradeCeiling": "A"},
        ],
        "perRowGradeThresholds": {
            "fusion-recipe":        {"S": 200, "A": 120, "B": 60,  "C": 30},
            "github-stars-own":     {"S": 88,  "A": 60,  "B": 35,  "C": 20},
            "proxy-containment":    {"S": 112, "A": 64,  "B": 32,  "C": 16},
            "verifier-attestation": {"S": 90,  "A": 54,  "B": 27,  "C": 14},
            "benchmark-result":     {"S": 90,  "A": 70,  "B": 40,  "C": 20},
            "arxiv":                {"S": 95,  "A": 70,  "B": 40,  "C": 15},
            "peer-review":          {"S": 88,  "A": 60,  "B": 35,  "C": 14},
            "repo-own":             {                    "B": 22,  "C": 9},
            "self-attestation":     {                              "C": 4},
            "social-signal":        {          "A": 60,  "B": 28,  "C": 12},
        },
    }
}


def _build_registry(tmp_path, evidence_rows, skill_id="test-skill", skill_type="basic"):
    """Create a minimal registry with one generic node and proper meta.json."""
    nodes_dir = tmp_path / "registry" / "nodes" / skill_type
    nodes_dir.mkdir(parents=True)
    schema_dir = tmp_path / "registry" / "schema"
    schema_dir.mkdir(parents=True)

    (schema_dir / "meta.json").write_text(json.dumps(MINIMAL_META), encoding="utf-8")

    node = {
        "id": skill_id,
        "name": "Test Skill",
        "type": skill_type,
        "description": "A skill for calibrate-evidence-grades tests.",
        "evidence": evidence_rows,
        "timeline": [],
    }
    (nodes_dir / f"{skill_id}.json").write_text(json.dumps(node, indent=2), encoding="utf-8")
    return str(tmp_path)


def _load_node(registry_root, skill_id="test-skill", skill_type="basic"):
    path = os.path.join(registry_root, "registry", "nodes", skill_type, f"{skill_id}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _args(registry_root, **overrides):
    base = dict(
        registry=registry_root,
        dry_run=False,
        skill=None,
        scope="all",
        no_build=True,
        yes=True,  # skip _confirm_destructive prompt
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ── Dry-run ───────────────────────────────────────────────────────────────────

def test_dry_run_writes_nothing(tmp_path):
    """--dry-run must not mutate any file."""
    root = _build_registry(tmp_path, [
        {"type": "arxiv", "source": "https://arxiv.org/abs/2310.03714", "trustNumber": 100},
    ])
    node_before = _load_node(root)
    calibrate_evidence_grades_command(_args(root, dry_run=True))
    node_after = _load_node(root)
    assert node_before == node_after


def test_dry_run_detects_upgrades(tmp_path, capsys):
    """--dry-run reports pending upgrades without writing."""
    root = _build_registry(tmp_path, [
        {"type": "arxiv", "source": "https://arxiv.org/abs/2310.03714", "trustNumber": 100},
    ])
    calibrate_evidence_grades_command(_args(root, dry_run=True))
    out = capsys.readouterr().out
    assert "→" in out or "updated" in out or "DRY RUN" in out


# ── S-capable types (arxiv + peer-review ceiling lifted) ─────────────────────

def test_arxiv_at_100_gets_s_grade(tmp_path):
    """arxiv with 500 citations (artifact_score=100) must reach S (gradeCeiling now S)."""
    root = _build_registry(tmp_path, [
        {"type": "arxiv", "source": "https://arxiv.org/abs/2005.14165", "citations": 500},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert ev[0]["grade"] == "S"


def test_arxiv_at_a_gets_a_grade(tmp_path):
    """arxiv ceiling is A — even high citation counts should reach A, not S."""
    root = _build_registry(tmp_path, [
        # citations=400 → score = 400/5 = 80.0 (≥ A floor 80; ceiling A, cannot reach S)
        {"type": "arxiv", "source": "https://arxiv.org/abs/test", "citations": 400},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert ev[0]["grade"] == "A"


def test_arxiv_below_a_floor_gets_b(tmp_path):
    """arxiv score 40 (B floor, below A=80) must get B."""
    root = _build_registry(tmp_path, [
        # citations=200 → score = 200/5 = 40.0 (B floor 40, below A=80)
        {"type": "arxiv", "source": "https://arxiv.org/abs/test", "citations": 200},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert ev[0]["grade"] == "B"


def test_peer_review_at_88_gets_s_grade(tmp_path):
    """peer-review with 4 reviewers (score≈120, above S floor 88) must reach S."""
    root = _build_registry(tmp_path, [
        {"type": "peer-review", "source": "https://nature.com/paper", "reviewers": 4},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert ev[0]["grade"] == "S"


def test_peer_review_below_s_floor_gets_a(tmp_path):
    """peer-review with 2 reviewers (score=60, exactly A floor) must get A."""
    root = _build_registry(tmp_path, [
        # reviewers=2 → magnitude=50, weight=1.2, score=60 (= A floor exactly, below S=88)
        {"type": "peer-review", "source": "https://nature.com/paper", "reviewers": 2},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert ev[0]["grade"] == "A"


# ── Grade ceiling clamping ─────────────────────────────────────────────────────

def test_repo_own_never_exceeds_b(tmp_path):
    """repo-own gradeCeiling=B means even a very high score stays at B."""
    root = _build_registry(tmp_path, [
        {"type": "repo-own", "source": "https://github.com/owner/repo", "trustNumber": 99},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert ev[0]["grade"] == "B"


def test_self_attestation_never_exceeds_c(tmp_path):
    """self-attestation gradeCeiling=C means any score ≥4 stays at C."""
    root = _build_registry(tmp_path, [
        {"type": "self-attestation", "source": "https://github.com/owner/repo", "trustNumber": 50},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert ev[0]["grade"] == "C"


def test_social_signal_never_exceeds_a(tmp_path):
    """social-signal gradeCeiling=A means even trustNumber=99 stays at A."""
    root = _build_registry(tmp_path, [
        {"type": "social-signal", "source": "https://youtube.com/watch?v=x", "trustNumber": 99},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert ev[0]["grade"] == "A"


# ── trustNumber fallback ──────────────────────────────────────────────────────

def test_trust_number_fallback_used_when_no_magnitude_drivers(tmp_path):
    """Row with only trustNumber (no stars/citations) still gets graded via fallback."""
    root = _build_registry(tmp_path, [
        # No stars field → computeArtifactScoreOrNone returns 0 → trustNumber fallback
        {"type": "github-stars-own", "source": "https://github.com/owner/repo", "trustNumber": 88},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    # trustNumber=88 >= S floor 88 → S (via fallback)
    assert ev[0]["grade"] == "S"


def test_trust_number_below_any_floor_yields_no_grade(tmp_path):
    """trustNumber below lowest floor must result in grade absent (not 'C')."""
    root = _build_registry(tmp_path, [
        {"type": "arxiv", "source": "https://arxiv.org/abs/test", "trustNumber": 10},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert "grade" not in ev[0]


# ── Skipped rows ──────────────────────────────────────────────────────────────

def test_auto_derived_rows_are_skipped(tmp_path):
    """_autoDerived rows must never have grade written to them."""
    root = _build_registry(tmp_path, [
        {"type": "fusion-recipe", "source": "internal", "_autoDerived": True, "trustNumber": 300},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert "grade" not in ev[0]


def test_rows_without_type_are_skipped(tmp_path):
    """Rows with no `type` field must be left unchanged."""
    root = _build_registry(tmp_path, [
        {"source": "https://example.com", "trustNumber": 80},
    ])
    before = _load_node(root)["evidence"][0].copy()
    calibrate_evidence_grades_command(_args(root))
    after = _load_node(root)["evidence"][0]
    assert before == after


# ── Idempotence ────────────────────────────────────────────────────────────────

def test_second_run_is_idempotent(tmp_path):
    """Running calibrate twice must produce zero additional changes on run 2."""
    root = _build_registry(tmp_path, [
        {"type": "arxiv", "source": "https://arxiv.org/abs/2310.03714", "trustNumber": 100},
        {"type": "repo-own", "source": "https://github.com/owner/repo", "trustNumber": 30},
        {"type": "peer-review", "source": "https://nature.com/paper", "trustNumber": 88},
    ])
    calibrate_evidence_grades_command(_args(root))
    node_after_run1 = _load_node(root)
    calibrate_evidence_grades_command(_args(root))
    node_after_run2 = _load_node(root)
    assert node_after_run1["evidence"] == node_after_run2["evidence"]


# ── Multiple rows in one skill ────────────────────────────────────────────────

def test_multiple_rows_graded_independently(tmp_path):
    """Each row is graded by its own type — no cross-contamination."""
    root = _build_registry(tmp_path, [
        {"type": "arxiv",        "source": "https://arxiv.org/abs/s", "citations": 500},
        {"type": "repo-own",     "source": "https://github.com/a",    "trustNumber": 50},
        {"type": "self-attestation", "source": "https://github.com/b", "trustNumber": 10},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert ev[0]["grade"] == "S"   # arxiv citations=500 → score=100 ≥ S floor 95
    assert ev[1]["grade"] == "B"   # repo-own trustNumber=50 (fallback) ≥ B floor 22, ceiling B
    assert ev[2]["grade"] == "C"   # self-attestation trustNumber=10 ≥ C floor 4, ceiling C


# ── Grade removal (stale grade cleared when score drops) ──────────────────────

def test_stale_grade_cleared_when_score_below_floor(tmp_path):
    """If a row previously had grade='B' but now scores below C floor, grade is removed."""
    root = _build_registry(tmp_path, [
        {"type": "arxiv", "source": "https://arxiv.org/abs/test", "grade": "B", "trustNumber": 5},
    ])
    calibrate_evidence_grades_command(_args(root))
    ev = _load_node(root)["evidence"]
    assert "grade" not in ev[0]


def test_missing_skill_filter_exits_before_write(tmp_path, capsys):
    root = _build_registry(tmp_path, [
        {"type": "arxiv", "source": "https://arxiv.org/abs/test", "grade": "B", "trustNumber": 5},
    ])
    before = _load_node(root)

    with pytest.raises(SystemExit) as exc:
        calibrate_evidence_grades_command(_args(root, skill="missing-skill"))

    assert exc.value.code != 0
    assert _load_node(root) == before
    assert "--skill target 'missing-skill' was not found" in capsys.readouterr().err
