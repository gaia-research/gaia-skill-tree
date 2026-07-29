"""Tests for the Stage-1 minimum-effort evidence writer (RFC2 §3.2).

Verifies buildStageOneRows / writeStageOneEvidence emit exactly the three
Stage-1 evidence types (github-stars-own, repo-own, self-attestation) in the
canonical shape gaia dev evidence writes, set NO grade / class / star level /
Trust Magnitude, perform NO web fetch, and are deterministic.
"""

from gaia_cli.stageOneEvidence import (
    STAGE_ONE_TYPES,
    buildStageOneRows,
    writeStageOneEvidence,
)


SOURCE = "https://github.com/mattpocock/grill-me"
EVALUATOR = "mattpocock"

# Fields that would encode a grade / class / star level / final TM. The Stage-1
# writer must NEVER set any of these — they are derived at appraisal time.
FORBIDDEN_FIELDS = {"grade", "class", "trustNumber", "star", "stars_level", "rank"}


def _rowsByType(rows):
    return {r["type"]: r for r in rows}


def test_emits_all_three_types_when_signals_present():
    rows = buildStageOneRows(
        SOURCE, EVALUATOR, stars=1200, commits=800, contributors=15
    )
    types = [r["type"] for r in rows]
    assert types == ["github-stars-own", "repo-own", "self-attestation"]


def test_types_are_the_stage_one_set():
    rows = buildStageOneRows(SOURCE, EVALUATOR, stars=10, commits=5, contributors=2)
    assert {r["type"] for r in rows} == set(STAGE_ONE_TYPES)
    assert STAGE_ONE_TYPES == ("github-stars-own", "repo-own", "self-attestation")


def test_canonical_shape_matches_gaia_dev_evidence():
    # gaia dev evidence writes source / evaluator / date / type on every fresh row.
    rows = buildStageOneRows(SOURCE, EVALUATOR, stars=10, commits=5, contributors=2)
    for row in rows:
        assert row["source"] == SOURCE
        assert row["evaluator"] == EVALUATOR
        assert isinstance(row["date"], str) and row["date"]
        assert row["type"] in STAGE_ONE_TYPES


def test_numeric_payload_on_correct_rows():
    byType = _rowsByType(
        buildStageOneRows(SOURCE, EVALUATOR, stars=1200, commits=800, contributors=15)
    )
    assert byType["github-stars-own"]["stars"] == 1200
    assert byType["repo-own"]["commits"] == 800
    assert byType["repo-own"]["contributors"] == 15
    # self-attestation carries no numeric payload — flat baseline.
    assert "stars" not in byType["self-attestation"]
    assert "commits" not in byType["self-attestation"]
    assert "contributors" not in byType["self-attestation"]


def test_no_grade_star_or_tm_fields_set():
    rows = buildStageOneRows(SOURCE, EVALUATOR, stars=99999, commits=99999, contributors=999)
    for row in rows:
        assert FORBIDDEN_FIELDS.isdisjoint(row.keys()), (
            f"Stage-1 row leaked a graded/scored field: {row}"
        )


def test_self_attestation_always_emitted():
    # Even with no repo signals at all, the flat baseline row is written.
    rows = buildStageOneRows(SOURCE, EVALUATOR)
    assert [r["type"] for r in rows] == ["self-attestation"]
    assert "stars" not in rows[0]


def test_stars_row_only_when_stars_present():
    rows = buildStageOneRows(SOURCE, EVALUATOR, commits=10, contributors=3)
    types = [r["type"] for r in rows]
    assert "github-stars-own" not in types
    assert types == ["repo-own", "self-attestation"]


def test_repo_row_only_when_repo_signals_present():
    rows = buildStageOneRows(SOURCE, EVALUATOR, stars=50)
    types = [r["type"] for r in rows]
    assert "repo-own" not in types
    assert types == ["github-stars-own", "self-attestation"]


def test_repo_row_with_only_commits():
    byType = _rowsByType(buildStageOneRows(SOURCE, EVALUATOR, commits=42))
    assert "repo-own" in byType
    assert byType["repo-own"]["commits"] == 42
    assert "contributors" not in byType["repo-own"]


def test_explicit_date_honoured():
    rows = buildStageOneRows(SOURCE, EVALUATOR, stars=5, date="2026-01-15")
    for row in rows:
        assert row["date"] == "2026-01-15"


def test_deterministic():
    a = buildStageOneRows(SOURCE, EVALUATOR, stars=1200, commits=800, contributors=15, date="2026-07-29")
    b = buildStageOneRows(SOURCE, EVALUATOR, stars=1200, commits=800, contributors=15, date="2026-07-29")
    assert a == b


def test_zero_signals_are_recorded_not_dropped():
    # 0 is a real signal (a repo with 0 stars), distinct from "no data" (None).
    byType = _rowsByType(
        buildStageOneRows(SOURCE, EVALUATOR, stars=0, commits=0, contributors=0)
    )
    assert byType["github-stars-own"]["stars"] == 0
    assert byType["repo-own"]["commits"] == 0
    assert byType["repo-own"]["contributors"] == 0


def test_write_appends_to_existing_list():
    existing = [{"source": "prior", "type": "peer-review", "evaluator": "x", "date": "2026-01-01"}]
    result = writeStageOneEvidence(
        existing, SOURCE, EVALUATOR, stars=10, commits=5, contributors=2
    )
    assert result is existing
    assert result[0]["type"] == "peer-review"
    assert [r["type"] for r in result[1:]] == list(STAGE_ONE_TYPES)


def test_write_handles_none_list():
    result = writeStageOneEvidence(None, SOURCE, EVALUATOR, stars=10)
    assert [r["type"] for r in result] == ["github-stars-own", "self-attestation"]
