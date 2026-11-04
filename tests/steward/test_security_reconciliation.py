"""#2283 evidence freshness is not suppression, authorization, or closure."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.check_security_dispositions import MATRIX, checkDispositions
from gaia_cli.steward.desk import _check_record, load_decision_records
from gaia_cli.steward.sensors_security import SecretScanSensor, _SecretTally

ROOT = Path(__file__).resolve().parents[2]


def matrix():
    return json.loads((ROOT / MATRIX).read_text(encoding="utf-8"))


def test_all_original_ids_groups_and_reviewed_bytes_are_preserved():
    document = matrix()
    assert checkDispositions(ROOT, document) == []
    assert Counter(row["group"] for row in document["rows"]) == {"D1": 16, "D2": 14, "D3": 9}
    assert Counter(row["status"] for row in document["rows"]) == {"harmless": 28, "fixture": 11}
    for row in document["rows"]:
        assert row["ledgerDisposition"] == "unchanged; parent-owned"
        assert row["originalAuthority"] == "C"
        if row["group"] == "D1":
            assert (ROOT / row["sourcePath"]).read_bytes() == (ROOT / row["canonicalSource"]).read_bytes()


def test_original_fingerprints_still_trigger_the_detector_not_an_allowlist():
    for row in matrix()["rows"]:
        findings = SecretScanSensor._findings(
            row["sourcePath"], (ROOT / row["sourcePath"]).read_text(encoding="utf-8"), _SecretTally()
        )
        actual = Counter((f["pattern"], f["fingerprint"]) for f in findings)
        expected = Counter((f["pattern"], f["fingerprint"]) for f in row["findings"])
        assert not (expected - actual), row["sourcePath"]


@pytest.mark.parametrize("field", ["sourcePath", "canonicalSource"])
def test_changed_reviewed_bytes_require_re_review(monkeypatch, field):
    document = matrix()
    row = next(row for row in document["rows"] if row["sourcePath"].startswith(".claude/"))
    target = ROOT / row[field]
    read = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda path: read(path) + b"\n// changed\n" if path == target else read(path))
    assert any("classification requires re-review" in item for item in checkDispositions(ROOT, document))


def test_new_credential_in_a_reviewed_file_is_not_blessed_by_the_matrix(monkeypatch):
    document = matrix()
    row = document["rows"][0]
    target = ROOT / row["sourcePath"]
    # Locally generated positive-test value; never obtained from an issuer.
    planted = "ghp" + "_" + hashlib.sha256(b"disposition-regression").hexdigest()
    changed = target.read_bytes() + f"\nvalue = '{planted}'\n".encode()
    findings = SecretScanSensor._findings(row["sourcePath"], changed.decode(), _SecretTally())
    assert any(f["pattern"] == "github-token" for f in findings)
    read = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda path: changed if path == target else read(path))
    assert any("classification requires re-review" in item for item in checkDispositions(ROOT, document))
    assert planted not in json.dumps(findings)


def test_guard_rejects_incomplete_inventory_unsafe_paths_and_missing_evidence():
    document = matrix()
    document["rows"].pop()
    document["rows"][0]["sourcePath"] = "../not-reviewed"
    document["rows"][1]["findings"] = []
    problems = checkDispositions(ROOT, document)
    assert "expected 39 unique credential finding ID strings" in problems
    assert "unsafe sourcePath" in problems
    assert any("invalid finding evidence" in item for item in problems)


def test_guard_does_not_claim_authentic_identity_or_scanner_authority():
    document = matrix()
    document["rows"][0]["debtId"] = "debt:credential_leak:invented"
    assert checkDispositions(ROOT, document) == []  # No independent inventory is supplied.
    result = subprocess.run(
        ["python", "scripts/check_security_dispositions.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "count, shape and reviewed-source-byte checks" in result.stdout
    assert "identity and scanner authority are not authenticated here" in result.stdout
    assert "scanner authority unchanged" not in result.stdout


def test_guard_refuses_symlinked_sources_before_reading(monkeypatch):
    document = matrix()
    target = ROOT / document["rows"][0]["sourcePath"]
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == target or original(path))
    assert any("symlinked sourcePath" in item for item in checkDispositions(ROOT, document))


def test_group_rulings_are_existing_schema_history_not_finding_closure():
    records = load_decision_records(ROOT)
    group = [r for r in records if r.get("id", "").startswith("steward-security-")]
    assert len(group) == 3
    assert all(_check_record(record) is None and record["status"] == "decided" for record in group)
    for record in group:
        assert matrix()["authorityLink"] in record["links"]
        assert "not an adjudication" in record["whyItMatters"]
        assert "does not authorize ledger mutation" in record["unblocks"]
    evidence = {item for record in group for item in record["evidence"] if item.startswith("debt:")}
    assert evidence == {row["debtId"] for row in matrix()["rows"]}


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for bundled Impeccable compatibility")
def test_bundled_script_compatibility_and_refusals():
    result = subprocess.run(
        ["node", "--test", "tests/steward/impeccable_compatibility.test.mjs"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
