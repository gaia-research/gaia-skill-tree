"""Sprint D W2b (#905) — `gaia push --benchmark` USER-verb regression tests.

The scout digest EPIC W2b mandate: push proposes (writes provenance:pending),
CI or a Verifier promotes. These tests lock:

* --from-result-file happy path → pending row lands with every fingerprint field
* Missing --skill-id (with no result file skillId) → clean error, no write
* Missing dataset/inputHash → clean error, no write
* --dry-run never writes
* --benchmark short-name → canonical --benchmark-id mapping (humaneval → humaneval@v1.0)
* --benchmark mismatch with result-file benchmarkId is caught
* Self-attested cannot leak in via this path (push always writes pending)
* Attestor fallback works from --attestor flag, and errors cleanly when unknown
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.pushBenchmark import push_benchmark_command


pytestmark = [pytest.mark.integration]


def _hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _make_registry(tmp_path: Path) -> str:
    """Minimal registry with a demo skill that can accept benchmark evidence."""
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
        "description": "Demo target for push --benchmark tests.",
        "evidence": [],
        "timeline": [],
    }
    (nodes / "demo-skill.json").write_text(json.dumps(node, indent=2))
    return str(tmp_path)


def _load_evidence(root: str) -> list[dict]:
    p = Path(root) / "registry" / "nodes" / "basic" / "demo-skill.json"
    return json.loads(p.read_text(encoding="utf-8")).get("evidence", [])


def _write_result_file(tmp_path: Path, **overrides) -> Path:
    payload = {
        "skillId": "demo-skill",
        "benchmarkId": "humaneval@v1.0",
        "score": 0.5,
        "unit": "pass@1",
        "pass": 3,
        "total": 6,
        "datasetHash": _hex("dataset-bytes"),
        "benchmarkInputHash": _hex("dataset-bytes+prompt+harness"),
        "runAt": "2026-07-05T12:00:00Z",
        "harnessCommit": "abc1234",
    }
    payload.update(overrides)
    path = tmp_path / ".benchmark-result.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _push_args(root: str, **overrides) -> SimpleNamespace:
    base = dict(
        registry=root,
        benchmark="humaneval",
        fromResultFile=None,
        skillId=None,
        score=None,
        unit=None,
        datasetHash=None,
        benchmarkInputHash=None,
        runAt=None,
        attestor="testbot",
        harnessUrl=None,
        percentile=None,
        dry_run=False,
        no_build=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patch_contributor(monkeypatch):
    """Bypass docs-build side effects and stub the timeline event writer."""
    monkeypatch.setattr("gaia_cli.commands.dev.evidence._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.evidence.append_skill_event", lambda *a, **kw: None)


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------


def test_push_benchmark_from_result_file_lands_pending_row(tmp_path):
    root = _make_registry(tmp_path)
    result = _write_result_file(tmp_path)
    args = _push_args(root, fromResultFile=str(result))

    rc = push_benchmark_command(args)
    assert rc == 0

    rows = _load_evidence(root)
    assert len(rows) == 1
    row = rows[0]
    assert row["type"] == "benchmark-result"
    assert row["benchmarkId"] == "humaneval@v1.0"
    assert row["score"] == 0.5
    assert row["unit"] == "pass@1"
    assert row["provenance"] == "pending", "push MUST always write pending; promotion is CI's job"
    assert row["attestor"] == "testbot"
    assert row["datasetHash"] == _hex("dataset-bytes")
    assert row["benchmarkInputHash"] == _hex("dataset-bytes+prompt+harness")
    assert row["runAt"] == "2026-07-05T12:00:00Z"
    # pending rows are excluded from Trust Magnitude → must carry no grade.
    assert "grade" not in row


def test_push_benchmark_dry_run_writes_nothing(tmp_path, capsys):
    root = _make_registry(tmp_path)
    result = _write_result_file(tmp_path)
    args = _push_args(root, fromResultFile=str(result), dry_run=True)

    rc = push_benchmark_command(args)
    assert rc == 0
    assert _load_evidence(root) == []
    out = capsys.readouterr().out
    assert "dry-run" in out


def test_push_benchmark_explicit_flags_only(tmp_path):
    """No --from-result-file — every field passed on the command line."""
    root = _make_registry(tmp_path)
    args = _push_args(
        root,
        skillId="demo-skill",
        score=0.42,
        unit="pass@1",
        datasetHash=_hex("d"),
        benchmarkInputHash=_hex("d+p+h"),
        runAt="2026-07-05T12:00:00Z",
    )

    rc = push_benchmark_command(args)
    assert rc == 0
    row = _load_evidence(root)[0]
    assert row["score"] == 0.42
    assert row["provenance"] == "pending"


def test_push_benchmark_source_defaults_to_synthetic_when_no_harness_url(tmp_path):
    root = _make_registry(tmp_path)
    result = _write_result_file(tmp_path)
    args = _push_args(root, fromResultFile=str(result))

    push_benchmark_command(args)
    row = _load_evidence(root)[0]
    # source must be absolute http(s) (preflight requires it) AND unique per
    # (benchmarkId, inputHash) so duplicate pushes of the same run are caught.
    assert row["source"].startswith("https://")
    assert "humaneval" in row["source"]
    assert _hex("dataset-bytes+prompt+harness") in row["source"]


def test_push_benchmark_source_uses_explicit_harness_url_when_provided(tmp_path):
    root = _make_registry(tmp_path)
    result = _write_result_file(tmp_path)
    args = _push_args(
        root,
        fromResultFile=str(result),
        harnessUrl="https://github.com/foo/bar/blob/pinned-sha/scripts/benchmarks/humaneval/run.py",
    )

    push_benchmark_command(args)
    row = _load_evidence(root)[0]
    assert row["source"].endswith("scripts/benchmarks/humaneval/run.py")
    assert row["harnessUrl"] == row["source"]


# --------------------------------------------------------------------------
# Rejection paths
# --------------------------------------------------------------------------


def test_push_benchmark_missing_skill_id_rejected(tmp_path, capsys):
    """No skillId in result file and no --skill-id flag → clean error."""
    root = _make_registry(tmp_path)
    result = _write_result_file(tmp_path, skillId=None)
    # strip skillId from the file so the flow has nothing to resolve to
    payload = json.loads(result.read_text())
    payload.pop("skillId", None)
    result.write_text(json.dumps(payload))

    args = _push_args(root, fromResultFile=str(result))
    with pytest.raises(SystemExit) as exc:
        push_benchmark_command(args)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--skill-id" in err
    assert _load_evidence(root) == []


def test_push_benchmark_no_dataset_hash_rejected(tmp_path, capsys):
    root = _make_registry(tmp_path)
    args = _push_args(
        root,
        skillId="demo-skill",
        score=0.42,
        unit="pass@1",
        # datasetHash intentionally omitted
        benchmarkInputHash=_hex("d+p+h"),
        runAt="2026-07-05T12:00:00Z",
    )
    with pytest.raises(SystemExit) as exc:
        push_benchmark_command(args)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "dataset-hash" in err or "datasetHash" in err
    assert _load_evidence(root) == []


def test_push_benchmark_short_name_mismatch_with_result_file(tmp_path, capsys):
    """--benchmark humaneval + result file carrying swe-bench@v1 → rejected."""
    root = _make_registry(tmp_path)
    result = _write_result_file(tmp_path, benchmarkId="swe-bench@v1.0")
    args = _push_args(root, fromResultFile=str(result))
    with pytest.raises(SystemExit) as exc:
        push_benchmark_command(args)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "disagrees" in err.lower() or "mismatch" in err.lower() or "swe-bench" in err
    assert _load_evidence(root) == []


def test_push_benchmark_unknown_short_name_rejected(tmp_path, capsys):
    root = _make_registry(tmp_path)
    result = _write_result_file(tmp_path)
    args = _push_args(root, benchmark="totally-fake-benchmark", fromResultFile=str(result))
    with pytest.raises(SystemExit) as exc:
        push_benchmark_command(args)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unknown --benchmark" in err.lower()
    assert _load_evidence(root) == []


def test_push_benchmark_missing_result_file_rejected(tmp_path, capsys):
    root = _make_registry(tmp_path)
    args = _push_args(root, fromResultFile=str(tmp_path / "nope.json"))
    with pytest.raises(SystemExit) as exc:
        push_benchmark_command(args)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "not found" in err
    assert _load_evidence(root) == []


def test_push_benchmark_missing_attestor_and_no_config_rejected(tmp_path, capsys, monkeypatch):
    """When --attestor is not given AND config has no user, the flow errors cleanly."""
    root = _make_registry(tmp_path)
    result = _write_result_file(tmp_path)
    # Force the contributor helper to return the sentinel 'unknown'.
    monkeypatch.setattr("gaia_cli.commands.pushBenchmark._get_contributor", lambda: "unknown", raising=False)
    # Patch the actual symbol used at call site.
    import gaia_cli.commands.dev.helpers as helpers
    monkeypatch.setattr(helpers, "_get_contributor", lambda: "unknown")

    args = _push_args(root, fromResultFile=str(result), attestor=None)
    with pytest.raises(SystemExit) as exc:
        push_benchmark_command(args)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "attestor" in err.lower()
    assert _load_evidence(root) == []


# --------------------------------------------------------------------------
# Self-attested cannot leak through this path
# --------------------------------------------------------------------------


def test_push_benchmark_always_writes_pending_never_self_attested(tmp_path):
    """The push path has no flag to set provenance — always pending. Belt & braces."""
    root = _make_registry(tmp_path)
    result = _write_result_file(tmp_path)
    args = _push_args(root, fromResultFile=str(result))

    push_benchmark_command(args)
    row = _load_evidence(root)[0]
    assert row["provenance"] == "pending"
