"""Sprint D W2a (#904) — benchmark-result CLI Pre-Flight regression tests.

Covers:
  * happy path — every field present, row lands, all 8 mandatory fields
    survive round-trip to the on-disk node file.
  * missing-field rejection for each of the 8 required benchmark fingerprint fields.
  * self-attested provenance is FOREVER rejected.
  * dataset/inputHash rejected when they are not 64-char lowercase hex.
  * benchmarkId regex sweep (widened pattern accepts subset ids and dashed variants).
  * unit outside the frozen enum is rejected.
  * runAt without a timezone offset is rejected.
  * a legacy row without a `type` field still passes evidenceEntry validation
    (Draft-07 `if.required: ['type']` guard regression).
  * the standalone benchmark-result.schema.json is Draft-07-valid.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.evidence import meta_evidence_command
from gaia_cli.commands.dev.helpers import DevPreflightError, _preflight_benchmark_row


pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Fixture helpers (thin copies of the ones in tests/test_dev_evidence.py so
# the two files stay independently runnable).
# ---------------------------------------------------------------------------


def _make_registry(tmp_path: Path) -> str:
    nodes = tmp_path / "registry" / "nodes" / "basic"
    nodes.mkdir(parents=True)
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(
        json.dumps(
            {
                "evidence": {
                    "gradeThresholds": {"S": 250, "A": 100, "B": 50, "C": 20},
                    "types": [
                        {"id": "repo-own", "gradeCeiling": "S"},
                        {"id": "benchmark-result", "gradeCeiling": "S"},
                    ],
                    "perRowGradeThresholds": {},
                }
            }
        )
    )
    node = {
        "id": "demo-skill",
        "name": "Demo Skill",
        "type": "basic",
        "description": "A demo skill for benchmark evidence tests.",
        "evidence": [],
        "timeline": [],
    }
    (nodes / "demo-skill.json").write_text(json.dumps(node, indent=2))
    return str(tmp_path)


def _load_node(root: str) -> dict:
    p = os.path.join(root, "registry", "nodes", "basic", "demo-skill.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _bench_args(root: str, **overrides) -> SimpleNamespace:
    base = dict(
        registry=root,
        skill_id="demo-skill",
        source="https://example.com/bench-report",
        index=None,
        evidence_type="benchmark-result",
        trust=None,
        evaluator="tester",
        date="2026-07-05",
        notes=None,
        stars=None,
        views=None,
        citations=None,
        reviewers=None,
        commits=None,
        contributors=None,
        skill_count_in_repo=None,
        percentile=None,
        source_started_at=None,
        benchmark_id="humaneval@v1.0",
        score=0.87,
        unit="pass@1",
        run_at="2026-07-05T12:00:00Z",
        provenance="ci-reproduced",
        attestor="https://github.com/gaia-research/gaia-skill-tree/actions/runs/1@abc1234",
        dataset_hash=_hex("humaneval-v1-dataset"),
        benchmark_input_hash=_hex("humaneval-v1-dataset+prompt+harness"),
        harness_url=None,
        no_build=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patch_contributor(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.evidence._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.evidence.append_skill_event", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_benchmark_happy_path_writes_all_fields(tmp_path):
    root = _make_registry(tmp_path)
    meta_evidence_command(_bench_args(root))
    ev = _load_node(root)["evidence"]
    assert len(ev) == 1
    row = ev[0]
    assert row["type"] == "benchmark-result"
    assert row["benchmarkId"] == "humaneval@v1.0"
    assert row["score"] == 0.87
    assert row["unit"] == "pass@1"
    assert row["runAt"] == "2026-07-05T12:00:00Z"
    assert row["provenance"] == "ci-reproduced"
    assert row["datasetHash"] == _hex("humaneval-v1-dataset")
    assert row["benchmarkInputHash"] == _hex("humaneval-v1-dataset+prompt+harness")


def test_benchmark_happy_path_with_optional_fields(tmp_path):
    root = _make_registry(tmp_path)
    meta_evidence_command(
        _bench_args(
            root,
            percentile=95,
            harness_url="https://github.com/foo/bar/blob/pinned/scripts/benchmarks/humaneval/run.py",
        )
    )
    row = _load_node(root)["evidence"][0]
    assert row["percentile"] == 95
    assert row["harnessUrl"].endswith("run.py")


# ---------------------------------------------------------------------------
# Missing-field rejection — each of the 8 mandatory fingerprint fields.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_flag,missing_field",
    [
        ("benchmark_id", "benchmarkId"),
        ("score", "score"),
        ("unit", "unit"),
        ("run_at", "runAt"),
        ("provenance", "provenance"),
        ("attestor", "attestor"),
        ("dataset_hash", "datasetHash"),
        ("benchmark_input_hash", "benchmarkInputHash"),
    ],
)
def test_benchmark_missing_field_rejected(tmp_path, capsys, missing_flag, missing_field):
    root = _make_registry(tmp_path)
    args = _bench_args(root, **{missing_flag: None})
    with pytest.raises(SystemExit) as exc:
        meta_evidence_command(args)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert missing_field in err
    assert not _load_node(root)["evidence"], "row must not be written when preflight fails"


# ---------------------------------------------------------------------------
# Provenance policy
# ---------------------------------------------------------------------------


def test_benchmark_self_attested_forever_rejected(tmp_path, capsys):
    root = _make_registry(tmp_path)
    # argparse would normally reject self-attested via choices=[]; but the
    # helper is called directly with a raw dict too (e.g. W2b's push flow),
    # so exercise both belt-and-braces layers here.
    row = {
        "type": "benchmark-result",
        "source": "https://example.com",
        "evaluator": "tester",
        "date": "2026-07-05",
        "benchmarkId": "humaneval@v1.0",
        "score": 0.87,
        "unit": "pass@1",
        "runAt": "2026-07-05T12:00:00Z",
        "provenance": "self-attested",
        "attestor": "tester",
        "datasetHash": _hex("a"),
        "benchmarkInputHash": _hex("b"),
    }
    with pytest.raises(DevPreflightError) as exc:
        _preflight_benchmark_row(row)
    assert "self-attested" in exc.value.message
    assert "FOREVER" in exc.value.message


@pytest.mark.parametrize("provenance", ["verifier-attested", "ci-reproduced", "mirrored", "pending"])
def test_benchmark_all_valid_provenance_values_pass(tmp_path, provenance):
    root = _make_registry(tmp_path)
    meta_evidence_command(_bench_args(root, provenance=provenance))
    assert _load_node(root)["evidence"][0]["provenance"] == provenance


# ---------------------------------------------------------------------------
# Hash validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_hash",
    ["abc", "A" * 64, "0" * 63, "z" * 64, "0" * 65],
)
def test_benchmark_bad_dataset_hash_rejected(tmp_path, capsys, bad_hash):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit):
        meta_evidence_command(_bench_args(root, dataset_hash=bad_hash))
    err = capsys.readouterr().err
    assert "--dataset-hash" in err


def test_benchmark_bad_input_hash_rejected(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit):
        meta_evidence_command(_bench_args(root, benchmark_input_hash="tooshort"))
    err = capsys.readouterr().err
    assert "--benchmark-input-hash" in err


# ---------------------------------------------------------------------------
# benchmarkId regex — widened pattern must accept these forms.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bid",
    [
        "humaneval@v1.0",
        "humaneval/python@v1.0",
        "swe-bench_verified@1.0",
        "mmlu-5shot@2024-03",
        "humaneval@1",
        "humaneval@v1.0.2",
        "arc-agi@v2.1-preview",
    ],
)
def test_benchmark_id_widened_pattern_accepts(tmp_path, bid):
    root = _make_registry(tmp_path)
    meta_evidence_command(_bench_args(root, benchmark_id=bid))
    assert _load_node(root)["evidence"][0]["benchmarkId"] == bid


@pytest.mark.parametrize(
    "bid",
    [
        "HumanEval@v1.0",  # uppercase
        "humaneval",  # missing @version
        "@v1.0",  # missing name
        "humaneval@",  # missing version
        "1humaneval@v1",  # leading digit disallowed
    ],
)
def test_benchmark_id_bad_pattern_rejected(tmp_path, capsys, bid):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit):
        meta_evidence_command(_bench_args(root, benchmark_id=bid))
    err = capsys.readouterr().err
    assert "--benchmark-id" in err


# ---------------------------------------------------------------------------
# unit enum + runAt timezone
# ---------------------------------------------------------------------------


def test_benchmark_unit_outside_enum_rejected(tmp_path):
    root = _make_registry(tmp_path)
    row = {
        "type": "benchmark-result",
        "source": "https://example.com",
        "evaluator": "tester",
        "date": "2026-07-05",
        "benchmarkId": "humaneval@v1.0",
        "score": 0.87,
        "unit": "chrf",  # not in the frozen enum
        "runAt": "2026-07-05T12:00:00Z",
        "provenance": "ci-reproduced",
        "attestor": "tester",
        "datasetHash": _hex("a"),
        "benchmarkInputHash": _hex("b"),
    }
    with pytest.raises(DevPreflightError) as exc:
        _preflight_benchmark_row(row)
    assert "--unit" in exc.value.message


def test_benchmark_run_at_missing_timezone_rejected(tmp_path, capsys):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit):
        meta_evidence_command(_bench_args(root, run_at="2026-07-05T12:00:00"))
    err = capsys.readouterr().err
    assert "timezone" in err or "--run-at" in err


# ---------------------------------------------------------------------------
# Draft-07 regression — legacy row without a `type` field must still validate
# against the base evidenceEntry schema (the if.required:['type'] guard).
# ---------------------------------------------------------------------------


def test_legacy_evidence_without_type_still_passes_schema():
    import jsonschema

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "registry"
        / "schema"
        / "skill.schema.json"
    )
    with open(schema_path, encoding="utf-8") as f:
        skill_schema = json.load(f)
    ev_entry = skill_schema["definitions"]["evidenceEntry"]
    validator = jsonschema.Draft7Validator(ev_entry)

    legacy = {
        "source": "https://example.com/legacy",
        "evaluator": "someone",
        "date": "2020-01-01",
    }
    assert list(validator.iter_errors(legacy)) == []


def test_legacy_benchmark_result_row_predating_epoch_still_passes():
    """The date-epoch gate exempts pre-2026-07 benchmark-result rows so the
    existing 5 corpus rows do not break under the new required-fields clause."""
    import jsonschema

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "registry"
        / "schema"
        / "skill.schema.json"
    )
    with open(schema_path, encoding="utf-8") as f:
        skill_schema = json.load(f)
    ev_entry = skill_schema["definitions"]["evidenceEntry"]
    validator = jsonschema.Draft7Validator(ev_entry)

    legacy_bench = {
        "source": "https://arxiv.org/abs/2403.02128",
        "evaluator": "mbtiongson1",
        "date": "2026-06-19",
        "type": "benchmark-result",
        "class": "A",
    }
    assert list(validator.iter_errors(legacy_bench)) == []


def test_standalone_benchmark_result_schema_is_draft07_valid():
    import jsonschema

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "registry"
        / "schema"
        / "evidence"
        / "benchmark-result.schema.json"
    )
    with open(schema_path, encoding="utf-8") as f:
        sub_schema = json.load(f)
    jsonschema.Draft7Validator.check_schema(sub_schema)
