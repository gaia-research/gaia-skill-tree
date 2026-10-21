"""D1: the issue-hygiene sensor maps a reconciled census onto stable debt (contract 3.6).

Census and manifest are built by hand. The reconciliation modules belong to lane B,
so each test installs a stub for them in ``sys.modules``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.census import bodySha256
from gaia_cli.steward.issuehygiene.sensor import (
    CENSUS_INPUT,
    MANIFEST_SCHEMA,
    REGISTRY_MODULE,
    RECONCILE_MODULE,
    IssueHygieneSensor,
)
from gaia_cli.steward.primitives import SensorNotEvaluated, SensorUnavailable
from gaia_cli.steward.sensors import default_sensors, registered_debt_kinds

REPO_ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 10, 21, 20, 0, 0, tzinfo=timezone.utc)
NOW_TEXT = "2026-10-21T20:00:00Z"


def makeRow(number: int, title: str, body: str = "body", **extra) -> dict:
    row = {
        "number": number, "title": title, "state": "open", "stateReason": None,
        "labels": ["upstream:child"], "author": "github-actions[bot]",
        "createdAt": "2026-10-01T00:00:00Z", "updatedAt": "2026-10-20T00:00:00Z", "closedAt": None,
        "comments": 0, "body": body, "bodySha256": bodySha256(body), "isPullRequest": False,
        "mergedAt": None, "headRef": None, "baseRef": None,
    }
    row.update(extra)
    return row


def makeCensus(rows: list[dict], fetchedAt: str = "2026-10-21T19:00:00Z") -> dict:
    return {
        "schemaVersion": "steward-github-census-v1",
        "repo": "gaia-research/gaia-skill-tree",
        "fetchedAt": fetchedAt,
        "source": "rest",
        "completeness": {
            "issues": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": len(rows), "lastLink": None},
            "pulls": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": 0, "lastLink": None},
        },
        "issues": rows,
        "recentlyClosed": [],
    }


def makeItem(number: int, key: str, authority: str, **extra) -> dict:
    item = {
        "key": key, "issue": number, "kind": "child", "state": "resolved", "parent": None, "canonical": None,
        "authority": authority, "ruleId": None, "evidence": [], "proposedTransition": {
            "action": "close", "stateReason": "completed", "duplicateOf": None},
        "confidence": "proven", "unknowns": [], "dependencies": [],
        "snapshot": {"updatedAt": "2026-10-20T00:00:00Z", "bodySha256": "0" * 64, "labels": ["upstream:child"]},
    }
    item.update(extra)
    return item


def makeManifest(items: list[dict], **extra) -> dict:
    manifest = {
        "schemaVersion": MANIFEST_SCHEMA,
        "censusFetchedAt": "2026-10-21T19:00:00Z",
        "censusStatus": "complete",
        "coverage": {"known": ["upstream"], "unknown": [], "notEvaluated": []},
        "stats": {"openIssues": len(items), "botOpen": len(items), "upstreamChildOpen": len(items),
                  "umbrellaOpen": 0, "classA": 0, "classB": 0, "classC": 0, "untracked": 0, "notEvaluated": 0},
        "items": items,
        "batches": [],
        "founderQuestions": [],
        "manifestSha256": "f" * 64,
    }
    manifest.update(extra)
    return manifest


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "founder/steward").mkdir(parents=True)
    shutil.copy(REPO_ROOT / "founder/steward/POLICY.yaml", tmp_path / "founder/steward/POLICY.yaml")
    return tmp_path


def writeCensus(root: Path, document: dict) -> None:
    target = root / CENSUS_INPUT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document), encoding="utf-8")


def stubReconcile(monkeypatch, manifest: dict | None = None, error: Exception | None = None) -> list:
    calls: list = []
    registry = types.ModuleType(REGISTRY_MODULE)
    registry.buildRegistryIndex = lambda root: {"root": str(root)}
    reconcile = types.ModuleType(RECONCILE_MODULE)

    def fakeReconcile(census, index, policy, now):
        calls.append((census.status.status, index, policy, now))
        if error is not None:
            raise error
        return manifest

    reconcile.reconcile = fakeReconcile
    monkeypatch.setitem(sys.modules, REGISTRY_MODULE, registry)
    monkeypatch.setitem(sys.modules, RECONCILE_MODULE, reconcile)
    return calls


def scanOf(root: Path, observed: str = NOW_TEXT):
    return IssueHygieneSensor().scan_detailed(root, observed)


def byKind(observations, kind):
    return [o for o in observations if o.kind == kind]


def test_sensor_is_registered_with_routine_18_and_three_debt_kinds() -> None:
    sensor = next(s for s in default_sensors() if s.id == "issue-hygiene")
    assert sensor.routine_ids == (18,)
    assert sensor.resolution_scope == "exhaustive"
    assert sensor.driver_inputs == (CENSUS_INPUT.as_posix(),)
    assert {"issue_closure_ready", "issue_suite_review", "issue_founder_decision"} <= registered_debt_kinds()


def test_absent_census_is_not_evaluated_never_healthy(repo: Path, monkeypatch) -> None:
    stubReconcile(monkeypatch, makeManifest([]))
    with pytest.raises(SensorNotEvaluated) as caught:
        scanOf(repo)
    assert getattr(caught.value, "input_absent", False) is True


@pytest.mark.parametrize("mutate, expected", [
    (lambda doc: doc["completeness"]["issues"].update(complete=False), "incomplete"),
    (lambda doc: doc["issues"][0].update(body="tampered"), "incomplete"),
    (lambda doc: doc.update(fetchedAt="2026-10-01T00:00:00Z"), "stale"),
])
def test_incomplete_or_stale_census_is_coverage_unknown(repo: Path, monkeypatch, mutate, expected) -> None:
    calls = stubReconcile(monkeypatch, makeManifest([]))
    document = makeCensus([makeRow(1, "one")])
    mutate(document)
    writeCensus(repo, document)
    with pytest.raises(SensorUnavailable, match=expected):
        scanOf(repo)
    assert calls == []  # reconciliation never runs on a census that failed to prove itself


def test_missing_reconciliation_module_is_coverage_unknown_not_a_crash(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(1, "one")]))
    monkeypatch.setitem(sys.modules, REGISTRY_MODULE, None)
    monkeypatch.setitem(sys.modules, RECONCILE_MODULE, None)
    with pytest.raises(SensorUnavailable, match="not available"):
        scanOf(repo)


def test_reconciliation_exception_is_coverage_unknown_with_type_only(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(1, "one")]))
    stubReconcile(monkeypatch, error=ValueError("secret detail from a body"))
    with pytest.raises(SensorUnavailable) as caught:
        scanOf(repo)
    assert "ValueError" in str(caught.value)
    assert "secret detail" not in str(caught.value)


def test_manifest_with_unknown_coverage_is_coverage_unknown(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(1, "one")]))
    manifest = makeManifest([], coverage={"known": [], "unknown": ["upstream"], "notEvaluated": []})
    stubReconcile(monkeypatch, manifest)
    with pytest.raises(SensorUnavailable, match="coverage is unknown"):
        scanOf(repo)


def test_proven_closures_group_by_rule_and_batch_items_by_suite(repo: Path, monkeypatch) -> None:
    rows = [makeRow(10, "[intake] alpha"), makeRow(11, "[intake] beta"), makeRow(12, "[intake] gamma")]
    writeCensus(repo, makeCensus(rows))
    items = [
        makeItem(10, "upstream-candidate:o/r:alpha", "A", ruleId="A1-child-curated",
                 evidence=[{"type": "registry", "ref": "registry/named/o/alpha.md", "sha256": "a" * 64}]),
        makeItem(11, "upstream-candidate:o/r:beta", "B", kind="child", state="actionable"),
        makeItem(12, "upstream-candidate:x/y:gamma", "B", kind="child", state="actionable"),
        makeItem(99, "issue:99", "none"),
    ]
    batches = [{"suite": "o/r", "umbrella": 1835, "classB": ["upstream-candidate:o/r:beta"], "size": 2},
               {"suite": "x/y", "umbrella": 2002, "classB": ["upstream-candidate:x/y:gamma"], "size": 1}]
    stubReconcile(monkeypatch, makeManifest(items, batches=batches))
    scan = scanOf(repo)
    closures = byKind(scan.observations, "issue_closure_ready")
    suites = byKind(scan.observations, "issue_suite_review")
    rules = {o.subject.id: o for o in closures}
    assert rules["A1-child-curated"].status == "drift"
    assert rules["A1-child-curated"].observed_state["count"] == 1
    assert rules["A1-child-curated"].observed_state["items"][0]["title"] == "[intake] alpha"
    assert rules["A2-umbrella-synced"].status == "healthy"  # enabled, nothing ready: resolves, never invented
    assert sorted(o.subject.id for o in suites) == ["o/r", "x/y"]
    by_suite = {o.subject.id: o for o in suites}
    assert by_suite["o/r"].observed_state["umbrella"] == 1835
    assert by_suite["o/r"].observed_state["items"][0]["issue"] == 11
    assert all(o.kind != "sensor_coverage_unknown" for o in scan.observations)
    assert not any(o.observed_state.get("items") and "issue:99" in json.dumps(o.observed_state) for o in scan.observations)


def test_unproven_or_disabled_closure_is_downgraded_to_batch_review(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(20, "[intake] delta"), makeRow(21, "[intake] epsilon")]))
    items = [
        makeItem(20, "upstream-candidate:o/r:delta", "A", ruleId="A1-child-curated", confidence="high"),
        makeItem(21, "upstream-candidate:o/r:epsilon", "A", ruleId="A9-invented"),
    ]
    stubReconcile(monkeypatch, makeManifest(items, batches=[]))
    scan = scanOf(repo)
    assert all(o.observed_state.get("count") == 0 for o in byKind(scan.observations, "issue_closure_ready"))
    (suite,) = byKind(scan.observations, "issue_suite_review")
    assert suite.subject.id == "unbatched"
    assert sorted(row["issue"] for row in suite.observed_state["items"]) == [20, 21]


def test_founder_questions_form_one_debt_each_and_unquestioned_items_surface(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(30, "[intake] zeta"), makeRow(31, "[intake] eta")]))
    items = [makeItem(30, "upstream-candidate:o/r:zeta", "C", state="awaiting-founder"),
             makeItem(31, "upstream-candidate:o/r:eta", "C", state="awaiting-founder")]
    questions = [{"id": "Q-abc12345", "question": "Accept the o/r family?", "affected": [30],
                  "options": ["accept", "reject", "defer"], "recommendation": None, "basis": "two candidates"}]
    stubReconcile(monkeypatch, makeManifest(items, founderQuestions=questions))
    scan = scanOf(repo)
    founder = {o.subject.id: o for o in byKind(scan.observations, "issue_founder_decision")}
    assert set(founder) == {"Q-abc12345", "unquestioned"}
    assert founder["Q-abc12345"].observed_state["affected"] == [30]
    assert founder["unquestioned"].observed_state["affected"] == [31]
    assert not byKind(scan.observations, "issue_suite_review")  # Class C never becomes a batch debt


def test_debt_ids_are_stable_when_only_the_fetch_time_moves(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(40, "[intake] theta")]))
    items = [makeItem(40, "upstream-candidate:o/r:theta", "A", ruleId="A1-child-curated")]
    stubReconcile(monkeypatch, makeManifest(items))
    first = scanOf(repo, "2026-10-21T20:00:00Z")
    second_manifest = makeManifest(items, censusFetchedAt="2026-10-21T20:30:00Z")
    stubReconcile(monkeypatch, second_manifest)
    second = scanOf(repo, "2026-10-21T20:30:00Z")
    first_ids = [o.debt_id for o in first.observations]
    second_ids = [o.debt_id for o in second.observations]
    assert first_ids == second_ids
    assert [o.observed_state["manifestDigest"] for o in first.observations] == [
        o.observed_state["manifestDigest"] for o in second.observations
    ]
    assert all("censusFetchedAt" not in json.dumps(o.observed_state) for o in first.observations)


def test_manifest_stats_travel_in_provenance_for_before_after_receipts(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(50, "[intake] iota")]))
    stubReconcile(monkeypatch, makeManifest([makeItem(50, "upstream-candidate:o/r:iota", "A", ruleId="A1-child-curated")]))
    scan = scanOf(repo)
    provenance = scan.observations[0].provenance
    assert provenance["stats"]["openIssues"] == 1
    assert provenance["censusStatus"] == "complete"


def test_not_evaluated_scope_is_a_skipped_subject_so_nothing_sweeps(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(60, "[intake] kappa")]))
    manifest = makeManifest([], coverage={"known": ["upstream"], "unknown": [], "notEvaluated": ["bot-family:gh-aw"]})
    stubReconcile(monkeypatch, manifest)
    scan = scanOf(repo)
    assert [entry["subjectId"] for entry in scan.skipped] == ["bot-family:gh-aw"]


def test_policy_with_writes_disabled_still_reports_closure_debt_but_grants_nothing(repo: Path, monkeypatch) -> None:
    text = (repo / "founder/steward/POLICY.yaml").read_text(encoding="utf-8")
    (repo / "founder/steward/POLICY.yaml").write_text(
        text.replace("writesEnabled: true", "writesEnabled: false", 1), encoding="utf-8"
    )
    writeCensus(repo, makeCensus([makeRow(70, "[intake] lambda")]))
    stubReconcile(monkeypatch, makeManifest([makeItem(70, "upstream-candidate:o/r:lambda", "A", ruleId="A1-child-curated")]))
    scan = scanOf(repo)
    ready = byKind(scan.observations, "issue_closure_ready")
    assert {o.subject.id: o.observed_state["count"] for o in ready}["A1-child-curated"] == 1


def test_manifest_schema_mismatch_is_coverage_unknown(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(80, "[intake] mu")]))
    manifest = makeManifest([])
    manifest["schemaVersion"] = "steward-issue-reconciliation-v0"
    stubReconcile(monkeypatch, manifest)
    with pytest.raises(SensorUnavailable, match="does not declare"):
        scanOf(repo)
