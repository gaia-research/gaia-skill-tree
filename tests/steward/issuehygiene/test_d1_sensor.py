"""D1: the issue-hygiene sensor maps a reconciled census onto stable debt (contract 3.6).

Most tests replace the reconciliation seam (``sensor.reconcileCensus``) with a hand-built
manifest, so the mapping is tested in isolation. The end-to-end test at the bottom runs the
real reconciliation over the four-family fixture with a fixed clock.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene import sensor as sensorModule
from gaia_cli.steward.issuehygiene.census import bodySha256
from gaia_cli.steward.issuehygiene.closure import closureCommentFor
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, MANIFEST_SCHEMA, IssueHygieneSensor
from gaia_cli.steward.primitives import SensorNotEvaluated, SensorUnavailable
from gaia_cli.steward.sensors import default_sensors, registered_debt_kinds

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "tests/fixtures/issuehygiene/census-four-families.json"
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
    """A manifest item with every field the closure planner and the sensor read."""

    item = {
        "key": key, "issue": number, "kind": "child", "state": "resolved", "parent": None, "canonical": None,
        "authority": authority, "ruleId": None, "evidence": [], "proposedTransition": {
            "action": "close", "stateReason": "completed", "duplicateOf": None},
        "confidence": "proven", "unknowns": [], "notProven": [], "dependencies": [], "suite": None, "questions": [],
        "snapshot": {"state": "open", "title": f"title {number}", "updatedAt": "2026-10-20T00:00:00Z",
                     "bodySha256": "0" * 64, "labels": ["upstream:child"]},
        "original": {"title": f"title {number}", "labels": ["upstream:child"], "bodySha256": "0" * 64,
                     "candidate": {"suggestedId": key.rsplit(":", 1)[-1]}},
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
        "policy": {"enabledRules": [], "writesEnabled": True, "maxClosuresPerRun": 10, "a5Disabled": []},
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
    """Replace the reconciliation seam with a fake that returns ``manifest`` or raises ``error``."""

    calls: list = []

    def fakeReconcile(census, root, hygiene, now):
        calls.append((census.status.status, hygiene, now))
        if error is not None:
            raise error
        return manifest

    monkeypatch.setattr(sensorModule, "reconcileCensus", fakeReconcile)
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


def test_reconciliation_exception_is_coverage_unknown_with_type_only(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(1, "one")]))

    def explode(*args, **kwargs):
        raise ValueError("secret detail from a body")

    monkeypatch.setattr(sensorModule, "reconcile", explode)  # the real wrapper must catch it
    with pytest.raises(SensorUnavailable) as caught:
        scanOf(repo)
    assert "ValueError" in str(caught.value)
    assert "secret detail" not in str(caught.value)


def test_manifest_with_unknown_coverage_is_coverage_unknown(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(1, "one")]))
    manifest = makeManifest([], coverage={"known": [], "unknown": ["registry-unreadable:x"], "notEvaluated": []})
    stubReconcile(monkeypatch, manifest)
    with pytest.raises(SensorUnavailable, match="coverage is unknown"):
        scanOf(repo)


def test_proven_closure_becomes_a_plan_and_batch_items_group_by_suite(repo: Path, monkeypatch) -> None:
    rows = [makeRow(10, "[intake] alpha"), makeRow(11, "[intake] beta"), makeRow(12, "[intake] gamma")]
    writeCensus(repo, makeCensus(rows))
    items = [
        makeItem(10, "upstream-candidate:o/r:alpha", "A", ruleId="A1-child-curated",
                 evidence=[{"type": "registry", "ref": "registry/named/o/alpha.md", "sha256": "a" * 64, "detail": "exact"}]),
        makeItem(11, "upstream-candidate:o/r:beta", "B", suite="o/r", state="actionable"),
        makeItem(12, "upstream-candidate:x/y:gamma", "B", suite="x/y", state="actionable"),
        makeItem(99, "issue:99", "none"),
    ]
    batches = [{"suite": "o/r", "umbrella": 1835, "classB": ["upstream-candidate:o/r:beta"], "size": 1},
               {"suite": "x/y", "umbrella": 2002, "classB": ["upstream-candidate:x/y:gamma"], "size": 1}]
    stubReconcile(monkeypatch, makeManifest(items, batches=batches))
    scan = scanOf(repo)
    rules = {o.subject.id: o for o in byKind(scan.observations, "issue_closure_ready")}
    assert rules["A1-child-curated"].status == "drift"
    assert rules["A1-child-curated"].observed_state["count"] == 1
    plan = rules["A1-child-curated"].observed_state["plans"][0]
    # Debt state carries no closing comment; the emitter rebuilds it from this plan.
    assert plan["issue"] == 10 and "comment" not in plan
    assert plan["reconciliationSha256"] == "f" * 64  # the manifest's own digest, for the rebuild
    assert "<!-- gaia-steward-closure:" in closureCommentFor(plan)
    assert rules["A2-umbrella-synced"].status == "healthy"  # enabled, nothing ready: resolves, never invented
    suites = {o.subject.id: o for o in byKind(scan.observations, "issue_suite_review")}
    assert set(suites) == {"o/r", "x/y"}
    assert suites["o/r"].observed_state["umbrella"] == 1835
    assert suites["o/r"].observed_state["items"][0]["issue"] == 11
    assert all(o.kind != "sensor_coverage_unknown" for o in scan.observations)


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
    items = [makeItem(30, "upstream-candidate:o/r:zeta", "C", state="awaiting-founder", questions=["Q-abc12345"]),
             makeItem(31, "upstream-candidate:o/r:eta", "C", state="awaiting-founder", questions=[])]
    questions = [{"id": "Q-abc12345", "question": "Accept the o/r family?", "affected": [30],
                  "options": ["accept", "reject", "defer"], "recommendation": None, "basis": "two candidates"}]
    stubReconcile(monkeypatch, makeManifest(items, founderQuestions=questions))
    scan = scanOf(repo)
    founder = {o.subject.id: o for o in byKind(scan.observations, "issue_founder_decision")}
    assert set(founder) == {"Q-abc12345", "unquestioned"}
    assert founder["Q-abc12345"].observed_state["affected"] == [30]
    assert founder["Q-abc12345"].observed_state["decisionTarget"] == "issue-question/q-abc12345"
    assert founder["unquestioned"].observed_state["affected"] == [31]
    assert not byKind(scan.observations, "issue_suite_review")  # Class C never becomes a batch debt


def test_debt_ids_are_stable_when_only_the_fetch_time_moves(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(40, "[intake] theta")]))
    items = [makeItem(40, "upstream-candidate:o/r:theta", "A", ruleId="A1-child-curated")]
    stubReconcile(monkeypatch, makeManifest(items))
    first = scanOf(repo, "2026-10-21T20:00:00Z")
    stubReconcile(monkeypatch, makeManifest(items, censusFetchedAt="2026-10-21T20:30:00Z"))
    second = scanOf(repo, "2026-10-21T20:30:00Z")
    assert [o.debt_id for o in first.observations] == [o.debt_id for o in second.observations]
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


def test_not_evaluated_issues_are_one_partial_subject_so_nothing_sweeps(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(60, "[intake] kappa")]))
    manifest = makeManifest([], coverage={"known": ["upstream"], "unknown": [], "notEvaluated": [60]})
    stubReconcile(monkeypatch, manifest)
    scan = scanOf(repo)
    assert [entry["subjectId"] for entry in scan.skipped] == ["unevaluated-issues"]
    assert "#60" in scan.skipped[0]["reason"]


def test_writes_disabled_still_reports_the_closure_debt_because_the_runner_gates_writes(repo: Path, monkeypatch) -> None:
    text = (repo / "founder/steward/POLICY.yaml").read_text(encoding="utf-8")
    (repo / "founder/steward/POLICY.yaml").write_text(
        text.replace("writesEnabled: true", "writesEnabled: false", 1), encoding="utf-8"
    )
    writeCensus(repo, makeCensus([makeRow(70, "[intake] lambda")]))
    stubReconcile(monkeypatch, makeManifest([makeItem(70, "upstream-candidate:o/r:lambda", "A", ruleId="A1-child-curated")]))
    scan = scanOf(repo)
    ready = {o.subject.id: o.observed_state["count"] for o in byKind(scan.observations, "issue_closure_ready")}
    assert ready["A1-child-curated"] == 1


def test_manifest_schema_mismatch_is_coverage_unknown(repo: Path, monkeypatch) -> None:
    writeCensus(repo, makeCensus([makeRow(80, "[intake] mu")]))
    manifest = makeManifest([])
    manifest["schemaVersion"] = "steward-issue-reconciliation-v0"
    stubReconcile(monkeypatch, manifest)
    with pytest.raises(SensorUnavailable, match="does not declare"):
        scanOf(repo)


def copyRegistry(repo: Path) -> None:
    for name in ("named", "nodes"):
        shutil.copytree(REPO_ROOT / "registry" / name, repo / "registry" / name)


def test_end_to_end_real_reconcile_on_the_four_family_fixture(repo: Path) -> None:
    """The real reconciliation, the real registry and the fixed clock, through the sensor."""

    writeCensus(repo, json.loads(FIXTURE.read_text(encoding="utf-8")))
    copyRegistry(repo)
    first = scanOf(repo, NOW_TEXT)
    second = scanOf(repo, NOW_TEXT)

    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    openIssues = [r for r in document["issues"] if r["state"] == "open" and not r.get("isPullRequest")]
    openNumbers = {r["number"] for r in openIssues}
    stats = first.observations[0].provenance["stats"]
    assert stats["openIssues"] == len(openIssues) == 115
    assert first.observations[0].provenance["censusStatus"] == "complete"
    assert first.observations[0].provenance["censusFetchedAt"] == "2026-10-21T19:00:00Z"

    assert {o.kind for o in first.observations} <= {"issue_closure_ready", "issue_suite_review", "issue_founder_decision"}
    assert [o.debt_id for o in first.observations] == [o.debt_id for o in second.observations]
    assert [o.observed_state for o in first.observations] == [o.observed_state for o in second.observations]
    for observation in byKind(first.observations, "issue_closure_ready"):
        for plan in observation.observed_state["plans"]:
            assert plan["issue"] in openNumbers
            row = next(r for r in openIssues if r["number"] == plan["issue"])
            assert plan["expectedSnapshot"]["bodySha256"] == row["bodySha256"]
            assert "comment" not in plan and len(plan["reconciliationSha256"]) == 64
            assert "<!-- gaia-steward-closure:" in closureCommentFor(plan)
    assert {entry["subjectId"] for entry in first.skipped} <= {"unevaluated-issues"}


def test_end_to_end_stale_clock_is_coverage_unknown_not_a_partial_result(repo: Path) -> None:
    writeCensus(repo, json.loads(FIXTURE.read_text(encoding="utf-8")))
    copyRegistry(repo)
    with pytest.raises(SensorUnavailable, match="stale"):
        scanOf(repo, "2026-10-29T20:00:00Z")
