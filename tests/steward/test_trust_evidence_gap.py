"""trust_evidence_gap: the dedicated Class C kind, debt migration and read-only discovery (#2201, 11A)."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.debt import KIND_SUPERSESSIONS, SUPERSEDED_RESOLUTION, reconcile_debt
from gaia_cli.steward.desk import build_desk, render_desk
from gaia_cli.steward.evidencediscovery import (
    DiscoveryError,
    buildDiscoveryReceipt,
    canonicalUrl,
    discoveryTargets,
    maxSearches,
    writeDiscoveryReceipt,
)
from gaia_cli.steward.lane import Lane
from gaia_cli.steward.models import (
    AuthorityClass,
    Debt,
    FounderQueue,
    Observation,
    Priority,
    Subject,
    debtIdFor,
)
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, StewardPolicy
from gaia_cli.steward.sensors import TrustCalibrationDriftSensor
from tests.steward.sensor_fixtures import commit_all, make_repo, tree_digest

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = "2026-11-07T00:00:00Z"
START = datetime(2026, 11, 7, tzinfo=timezone.utc)
PARENT = {
    "id": "parent-platform",
    "name": "Parent Platform",
    "type": "fusion",
    "description": "Generic parent with no evidence of its own.",
    "evidence": [],
}


def _named(skill_id: str = "owner/child", *, level: str = "2★", evidence: list | None = None) -> str:
    skill = {
        "id": skill_id,
        "name": skill_id.split("/")[-1],
        "status": "named",
        "contributor": skill_id.split("/")[0],
        "level": level,
        "genericSkillRef": "parent-platform",
        "evidence": evidence or [],
    }
    return "---\n" + yaml.safe_dump(skill, sort_keys=False, allow_unicode=True) + "---\n"


def _gapRepo(tmp_path: Path, *, evidence: list | None = None, level: str = "2★") -> Path:
    meta = {"evidence": {"gradeThresholds": {"S": 250, "A": 100, "B": 50, "C": 20},
                         "types": [{"id": t} for t in ("arxiv", "repo-own", "github-stars-own", "benchmark-result", "self-attestation")],
                         "perRowGradeThresholds": {}}}
    return make_repo(tmp_path, {
        "registry/nodes/fusion/parent-platform.json": json.dumps(PARENT),
        "registry/named/owner/child.md": _named(level=level, evidence=evidence),
        "registry/schema/meta.json": json.dumps(meta),
    })


def _debt(kind: str, subject: str = "owner/child", *, status: str = "open", **extra) -> Debt:
    subj = Subject(type="named-skill", id=subject)
    return Debt(
        id=debtIdFor(kind, subj), kind=kind, subject=subj, source="trust-calibration-drift",
        current_state={"level": "2★"},
        # The interim marker is what makes a drift debt the same condition as the gap.
        observed_state={"preservedLevel": "2★", "evidenceGap": True} if kind == "trust_calibration_drift" else {"preservedLevel": "2★"},
        confidence=1.0,
        priority=Priority(0.5, 0.5, 0.5, 0.5, 0.5, 0.5), authority=AuthorityClass.B if kind == "trust_calibration_drift" else AuthorityClass.C,
        status=status, first_observed_at="2026-10-28T00:00:00Z", last_observed_at="2026-10-28T00:00:00Z",
        observation_count=3, **extra,
    )


def _gapObservation(subject: str = "owner/child", at: str = NOW) -> Observation:
    return Observation(
        kind="trust_evidence_gap", subject=Subject(type="named-skill", id=subject), observed_at=at,
        source="trust-calibration-drift", status="drift", current_state={"level": "2★"},
        observed_state={"evidenceGap": True, "preservedLevel": "2★", "evidenceBasis": "no-effective-evidence-rows", "effectiveRowCount": 0},
    )


# --- the kind and its policy ------------------------------------------------------------


def test_policy_classifies_the_kind_as_class_c_with_priority() -> None:
    policy = StewardPolicy.load(REPO_ROOT)
    assert policy.authority_for("trust_evidence_gap") is AuthorityClass.C
    assert policy.priority_for("trust_evidence_gap", 1.0).score > 0
    # The interim marker's kind keeps its class; only the empty-pool finding moved.
    assert policy.authority_for("trust_calibration_drift") is AuthorityClass.B
    assert not any(rule.debt_kind == "trust_evidence_gap" for rule in policy.dispatch_rules.values())


def test_sensor_declares_and_emits_the_kind_with_the_rating_preserved(tmp_path: Path) -> None:
    assert "trust_evidence_gap" in TrustCalibrationDriftSensor.debt_kinds
    repo = _gapRepo(tmp_path)

    (observation,) = TrustCalibrationDriftSensor().scan(repo, NOW)

    assert observation.kind == "trust_evidence_gap"
    assert observation.observed_state["preservedLevel"] == "2★"
    assert observation.observed_state["evidenceGap"] is True
    assert not {"targetLevel", "calibrationCommand", "laneEligible"} & set(observation.observed_state)


def test_the_lane_never_receives_the_gap_even_without_the_marker(tmp_path: Path) -> None:
    repo = _gapRepo(tmp_path)
    (repo / POLICY_RELATIVE_PATH).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, repo / POLICY_RELATIVE_PATH)
    ticks = iter(START + timedelta(minutes=n) for n in range(100))
    result = StewardController(sensors=[TrustCalibrationDriftSensor()], clock=lambda: next(ticks)).scan(repo)

    (debt,) = result.open_debts
    assert debt.kind == "trust_evidence_gap" and debt.authority is AuthorityClass.C
    policy = StewardPolicy.load(REPO_ROOT)
    dispatchable = {rule.debt_kind: rule.id for rule in policy.dispatch_rules.values()}
    assert debt.kind not in dispatchable
    assert Lane(entries=(), policy=policy.lane).entries == ()


# --- debt id migration ----------------------------------------------------------------


def test_the_successor_kind_supersedes_the_interim_drift_debt_without_deleting_it() -> None:
    assert KIND_SUPERSESSIONS["trust_evidence_gap"] == ("trust_calibration_drift",)
    policy = StewardPolicy.load(REPO_ROOT)
    old = _debt("trust_calibration_drift")
    unrelated = _debt("trust_calibration_drift", "owner/other")

    result = reconcile_debt(
        [_gapObservation()], {old.id: old, unrelated.id: unrelated}, policy,
        exhaustive_sources=("trust-calibration-drift",), observed_at=NOW,
    )

    by_id = {debt.id: debt for debt in result.debts}
    new = by_id[debtIdFor("trust_evidence_gap", old.subject)]
    assert new.status == "open" and new.authority is AuthorityClass.C
    assert new.supersedes == (old.id,)
    kept = by_id[old.id]  # retained, never deleted
    assert kept.status == "resolved" and kept.resolution == SUPERSEDED_RESOLUTION
    assert kept.superseded_by == new.id
    assert kept.observation_count == old.observation_count and kept.first_observed_at == old.first_observed_at
    assert (old.id, new.id) in result.superseded and old.id in result.resolved and new.id in result.created
    # A different subject's debt is not touched by this subject's migration (the sweep owns it).
    assert by_id[unrelated.id].superseded_by is None


def test_genuine_prior_drift_is_not_linked_or_resolved_by_the_migration() -> None:
    policy = StewardPolicy.load(REPO_ROOT)
    genuine = replace(_debt("trust_calibration_drift"), observed_state={"targetLevel": "1★", "trustGrade": "ungraded"})

    result = reconcile_debt([_gapObservation()], {genuine.id: genuine}, policy, observed_at=NOW)

    by_id = {debt.id: debt for debt in result.debts}
    new = by_id[debtIdFor("trust_evidence_gap", genuine.subject)]
    assert new.supersedes == () and result.superseded == ()
    assert by_id[genuine.id].status == "open" and by_id[genuine.id].superseded_by is None
    assert genuine.id not in result.resolved


def test_a_drift_debt_with_the_marker_but_a_target_level_is_genuine_drift() -> None:
    policy = StewardPolicy.load(REPO_ROOT)
    odd = replace(_debt("trust_calibration_drift"), observed_state={"evidenceGap": True, "targetLevel": "1★"})
    result = reconcile_debt([_gapObservation()], {odd.id: odd}, policy, observed_at=NOW)
    assert result.superseded == ()


def test_migration_is_idempotent_and_survives_a_ledger_round_trip() -> None:
    policy = StewardPolicy.load(REPO_ROOT)
    old = _debt("trust_calibration_drift")
    first = reconcile_debt([_gapObservation()], {old.id: old}, policy, observed_at=NOW)
    loaded = {debt.id: Debt.from_dict(debt.to_dict()) for debt in first.debts}
    again = reconcile_debt([_gapObservation(at="2026-11-08T00:00:00Z")], loaded, policy, observed_at="2026-11-08T00:00:00Z")

    new = next(debt for debt in again.debts if debt.kind == "trust_evidence_gap")
    kept = next(debt for debt in again.debts if debt.id == old.id)
    assert new.supersedes == (old.id,) and new.observation_count == 2
    assert kept.superseded_by == new.id and kept.resolution == SUPERSEDED_RESOLUTION
    assert again.created == () and again.superseded == ()
    assert Debt.from_dict(new.to_dict()) == new


def test_a_debt_without_links_serializes_exactly_as_before() -> None:
    plain = _debt("trust_stamp_stale")
    assert "supersedes" not in plain.to_dict() and "supersededBy" not in plain.to_dict()


def test_real_drift_returning_reopens_the_old_debt_and_clears_its_forward_link() -> None:
    policy = StewardPolicy.load(REPO_ROOT)
    old = _debt("trust_calibration_drift")
    migrated = reconcile_debt([_gapObservation()], {old.id: old}, policy, observed_at=NOW)
    ledger = {debt.id: debt for debt in migrated.debts}
    drift = Observation(
        kind="trust_calibration_drift", subject=old.subject, observed_at="2026-11-09T00:00:00Z",
        source="trust-calibration-drift", status="drift", current_state={"level": "2★"},
        observed_state={"targetLevel": "1★"},
    )

    result = reconcile_debt([drift], ledger, policy, exhaustive_sources=("trust-calibration-drift",), observed_at="2026-11-09T00:00:00Z")

    by_id = {debt.id: debt for debt in result.debts}
    assert by_id[old.id].status == "open" and by_id[old.id].superseded_by is None
    gap = by_id[debtIdFor("trust_evidence_gap", old.subject)]
    assert gap.status == "resolved" and gap.supersedes == (old.id,)  # history stays on the successor


def test_the_controller_migrates_a_seeded_ledger_and_keeps_every_receipt(tmp_path: Path) -> None:
    from gaia_cli.steward.receipts import write_current_state

    repo = _gapRepo(tmp_path)
    policy_path = repo / POLICY_RELATIVE_PATH
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy_path)
    old = _debt("trust_calibration_drift")
    state = repo / ".gaia/steward"
    write_current_state(state / "debt.json", [old], repo_root=repo, state_root=state)
    ticks = iter(START + timedelta(minutes=n) for n in range(100))

    result = StewardController(sensors=[TrustCalibrationDriftSensor()], clock=lambda: next(ticks)).scan(repo)

    ledger = json.loads((state / "debt.json").read_text(encoding="utf-8"))["debts"]
    by_id = {item["id"]: item for item in ledger}
    new_id = debtIdFor("trust_evidence_gap", old.subject)
    assert by_id[old.id]["resolution"] == "superseded" and by_id[old.id]["supersededBy"] == new_id
    assert by_id[new_id]["supersedes"] == [old.id] and by_id[new_id]["status"] == "open"
    assert old.id in result.receipt.debt_resolved and new_id in result.receipt.debt_created


# --- the desk -----------------------------------------------------------------------------


def test_the_desk_shows_one_grouped_decision_for_every_gap() -> None:
    gaps = [replace(_debt("trust_evidence_gap", f"owner/skill-{n}"), observed_state={
        "preservedLevel": "2★", "evidenceBasis": "no-effective-evidence-rows", "effectiveRowCount": 0}) for n in range(3)]

    desk = build_desk(
        open_debts=gaps, founder_queue=FounderQueue.create(()), lane=Lane(entries=(), policy=StewardPolicy.load(REPO_ROOT).lane),
        coverage_unknown=(), not_evaluated=(), decision_records=(),
        ledger_shared=True, last_scheduled_run_at="2026-11-07T00:00:00Z", now=NOW,
    )

    (decision,) = desk.decisions
    assert decision.debt_ids == tuple(sorted(item.id for item in gaps))
    assert decision.source == "class-c-debt"
    assert len(decision.evidence) == 3 and all("rating 2★ preserved" in row for row in decision.evidence)
    text = render_desk(desk)
    assert "evidence gap" in decision.decision and "never" in decision.why_it_matters
    assert "steward_evidence_discovery.py" in decision.recommended
    assert "demotion" in decision.recommended
    assert "issues/2201" in " ".join(decision.links)
    assert "owner/skill-0" in text


# --- the read-only discovery routine ---------------------------------------------------


def _log(**overrides) -> dict:
    log = {
        "skillId": "owner/child",
        "searchedBy": "driver",
        "searches": [
            {"query": "owner/child benchmark", "channel": "benchmarks", "searchedAt": "2026-11-07T00:00:00Z", "results": []},
            {"query": "owner/child paper", "channel": "papers", "searchedAt": "2026-11-07T00:01:00Z", "results": [
                {"url": "https://arxiv.org/abs/2501.00001", "title": "A paper", "evidenceType": "arxiv",
                 "attribution": "Some Author", "publishedAt": "2026-08-01"},
            ]},
        ],
    }
    log.update(overrides)
    return log


def test_targets_come_from_the_gap_findings(tmp_path: Path) -> None:
    repo = _gapRepo(tmp_path)
    (target,) = discoveryTargets(repo, NOW)
    assert (target.skillId, target.preservedLevel, target.evidenceBasis) == ("owner/child", "2★", "no-effective-evidence-rows")
    assert target.toDict()["maxSearches"] == maxSearches


def test_the_receipt_records_positive_and_negative_searches_and_admits_nothing(tmp_path: Path) -> None:
    repo = _gapRepo(tmp_path)

    receipt = buildDiscoveryReceipt(_log(), repoRoot=repo, generatedAt=NOW)

    assert receipt["readOnly"] is True
    assert receipt["admittedEvidence"] == [] and receipt["ratingChange"] is None
    assert receipt["preservedLevel"] == "2★"
    negative, positive = receipt["searches"]
    assert negative["outcome"] == "negative" and negative["resultCount"] == 0 and negative["query"] == "owner/child benchmark"
    assert positive["outcome"] == "positive"
    (candidate,) = positive["candidates"]
    assert candidate["freshness"] == {"class": "fresh", "ageDays": 98}
    assert candidate["duplicate"]["isDuplicate"] is False
    assert candidate["admissibility"]["state"] == "admissible-candidate"
    assert candidate["attribution"] == "Some Author" and candidate["publishedAt"] == "2026-08-01"
    assert receipt["outcome"] == "candidates-found"
    coverage = receipt["coverage"]
    assert (coverage["positive"], coverage["negative"]) == (1, 1)
    assert coverage["channelsNotSearched"] == ["upstream-repo", "releases-usage"]
    assert "channel family not searched: upstream-repo" in coverage["limitations"]


def test_needs_review_candidates_do_not_confirm_the_gap(tmp_path: Path) -> None:
    repo = _gapRepo(tmp_path)
    log = _log()
    log["searches"] = [{"query": "q", "channel": "benchmarks", "searchedAt": NOW, "results": [
        {"url": "https://x.test/bench", "evidenceType": "benchmark-result", "attribution": "lab"},
    ]}]

    receipt = buildDiscoveryReceipt(log, repoRoot=repo, generatedAt=NOW)

    assert receipt["outcome"] == "candidates-need-review"
    assert receipt["coverage"]["needsReviewCandidates"] == 1 and receipt["coverage"]["admissibleCandidates"] == 0
    assert "NOT confirmed" in receipt["nextStep"]
    assert receipt["admittedEvidence"] == [] and receipt["ratingChange"] is None


def test_inadmissible_only_results_still_confirm_the_gap(tmp_path: Path) -> None:
    repo = _gapRepo(tmp_path)
    log = _log()
    log["searches"] = [{"query": "q", "channel": "papers", "searchedAt": NOW, "results": [
        {"url": "https://x.test/n", "evidenceType": "nonsense", "attribution": "o"},
    ]}]

    assert buildDiscoveryReceipt(log, repoRoot=repo, generatedAt=NOW)["outcome"] == "evidence-gap-confirmed"


def test_only_negative_searches_confirm_the_gap_and_never_recommend_a_demotion(tmp_path: Path) -> None:
    repo = _gapRepo(tmp_path)
    log = _log()
    log["searches"] = log["searches"][:1]

    receipt = buildDiscoveryReceipt(log, repoRoot=repo, generatedAt=NOW)

    assert receipt["outcome"] == "evidence-gap-confirmed"
    assert receipt["ratingChange"] is None and receipt["preservedLevel"] == "2★"
    assert "counter-evidence or supersession" in receipt["nextStep"]


def test_duplicates_are_marked_against_existing_effective_evidence_and_earlier_candidates(tmp_path: Path) -> None:
    existing = {"type": "repo-own", "source": "https://github.com/owner/child", "commits": 100, "contributors": 2}
    repo = _gapRepo(tmp_path, evidence=[existing], level="1★")
    log = _log()
    log["searches"] = [{"query": "q", "channel": "upstream-repo", "searchedAt": NOW, "results": [
        {"url": "https://GitHub.com/owner/child/", "evidenceType": "repo-own", "attribution": "owner"},
        {"url": "https://example.test/post", "evidenceType": "arxiv", "attribution": "x"},
        {"url": "https://example.test/post/", "evidenceType": "arxiv", "attribution": "x"},
    ]}]

    receipt = buildDiscoveryReceipt(log, repoRoot=repo, generatedAt=NOW)

    first, second, third = receipt["searches"][0]["candidates"]
    assert first["duplicate"] == {"isDuplicate": True, "of": "https://github.com/owner/child", "scope": "existing-effective-evidence"}
    assert first["admissibility"]["state"] == "inadmissible"
    assert second["duplicate"]["isDuplicate"] is False
    assert third["duplicate"]["scope"] == "earlier-candidate" and third["admissibility"]["state"] == "inadmissible"
    assert canonicalUrl("HTTPS://Example.test/a/#frag") == "https://example.test/a"


@pytest.mark.parametrize(("result", "state", "reason"), [
    ({"url": "https://github.com/o/r", "evidenceType": "github-stars-own", "attribution": "o"}, "needs-review", "stars are not proof"),
    ({"url": "https://x.test/b", "evidenceType": "benchmark-result", "attribution": "o"}, "needs-review", "catalog-gated"),
    ({"url": "https://x.test/s", "evidenceType": "self-attestation", "attribution": "o"}, "needs-review", "not independent"),
    ({"url": "https://x.test/n", "evidenceType": "nonsense", "attribution": "o"}, "inadmissible", "unknown evidence type"),
    ({"url": "ftp://x.test/f", "evidenceType": "arxiv", "attribution": "o"}, "inadmissible", "http(s)"),
    ({"url": "https://x.test/u", "evidenceType": "arxiv"}, "needs-review", "no attribution"),
    ({"url": "https://x.test/t", "attribution": "o"}, "needs-review", "no evidence type"),
])
def test_admissibility_is_an_annotation_with_a_reason(tmp_path: Path, result: dict, state: str, reason: str) -> None:
    repo = _gapRepo(tmp_path)
    log = _log()
    log["searches"] = [{"query": "q", "channel": "papers", "searchedAt": NOW, "results": [result]}]

    (candidate,) = buildDiscoveryReceipt(log, repoRoot=repo, generatedAt=NOW)["searches"][0]["candidates"]

    assert candidate["admissibility"]["state"] == state
    assert reason in " ".join(candidate["admissibility"]["reasons"])


@pytest.mark.parametrize("bad", [
    {"level": "3★"},
    {"admittedEvidence": [{"url": "https://x.test"}]},
    {"trustMagnitude": 100},
    {"searches": []},
    {"skillId": "not-a-named-id"},
    {"searches": [{"query": "q", "channel": "social", "searchedAt": NOW, "results": []}]},
    {"searches": [{"query": "q", "channel": "papers", "searchedAt": NOW, "results": [], "admit": True}]},
    {"searches": [{"query": "q", "channel": "papers", "searchedAt": NOW, "results": [{"url": "https://x.test", "newLevel": "4★"}]}]},
])
def test_a_log_that_carries_an_admission_a_rating_or_no_searches_is_rejected(tmp_path: Path, bad: dict) -> None:
    repo = _gapRepo(tmp_path)
    with pytest.raises(DiscoveryError):
        buildDiscoveryReceipt(_log(**bad), repoRoot=repo, generatedAt=NOW)


def test_the_pass_is_bounded(tmp_path: Path) -> None:
    repo = _gapRepo(tmp_path)
    many = [{"query": f"q{n}", "channel": "papers", "searchedAt": NOW, "results": []} for n in range(maxSearches + 1)]
    with pytest.raises(DiscoveryError, match="at most"):
        buildDiscoveryReceipt(_log(searches=many), repoRoot=repo, generatedAt=NOW)
    with pytest.raises(DiscoveryError, match="not found"):
        buildDiscoveryReceipt(_log(skillId="owner/missing"), repoRoot=repo, generatedAt=NOW)


def test_discovery_writes_only_ignored_local_state_and_leaves_the_registry_untouched(tmp_path: Path) -> None:
    repo = _gapRepo(tmp_path)
    before = tree_digest(repo / "registry")
    receipt = buildDiscoveryReceipt(_log(), repoRoot=repo, generatedAt=NOW)

    path, created = writeDiscoveryReceipt(repo, receipt)
    again, createdAgain = writeDiscoveryReceipt(repo, receipt)

    assert created and not createdAgain and again == path
    assert path.relative_to(repo).parts[:3] == (".gaia", "steward", "discovery")
    assert json.loads(path.read_text(encoding="utf-8"))["admittedEvidence"] == []
    assert tree_digest(repo / "registry") == before
    commit_all(repo)
    assert (repo / "registry/named/owner/child.md").read_text(encoding="utf-8") == _named()


def test_discovery_is_deterministic(tmp_path: Path) -> None:
    repo = _gapRepo(tmp_path)
    first = buildDiscoveryReceipt(_log(), repoRoot=repo, generatedAt=NOW)
    second = buildDiscoveryReceipt(_log(), repoRoot=repo, generatedAt=NOW)
    assert first == second and first["receiptId"].startswith("discovery-")


# --- stale-stamp desk commands: only safe cases get a write command (review of #2323) ----------


def _stampDebt(name: str, *, safe: bool, reasons: list[str] | None = None) -> Debt:
    state = {"recomputationOnly": safe, "holdReasons": reasons or []}
    return replace(_debt("trust_stamp_stale", name), observed_state=state)


def _stampDesk(*debts: Debt):
    return build_desk(
        open_debts=debts, founder_queue=FounderQueue.create(()), lane=Lane(entries=(), policy=StewardPolicy.load(REPO_ROOT).lane),
        coverage_unknown=(), not_evaluated=(), decision_records=(),
        ledger_shared=True, last_scheduled_run_at="2026-11-07T00:00:00Z", now=NOW,
    )


def test_the_desk_recommends_the_restricted_command_only_when_a_safe_stamp_exists() -> None:
    safe = _stampDebt("owner/a", safe=True)
    governed = _stampDebt("owner/b", safe=False, reasons=["level-disagrees-with-computed-grade"])

    (mixed,) = _stampDesk(safe, governed).decisions
    (only_safe,) = _stampDesk(safe).decisions
    (only_governed,) = _stampDesk(governed).decisions

    restricted = "gaia dev calibrate-trust-magnitude --all --recomputation-only"
    assert restricted in mixed.recommended and restricted in only_safe.recommended
    # A governed-only desk item carries no write command at all.
    assert "calibrate-trust-magnitude" not in only_governed.recommended
    assert "no write command is recommended" in only_governed.recommended
    # Whatever command is recommended is never the unrestricted form.
    for decision in (mixed, only_safe):
        assert decision.recommended.count("calibrate-trust-magnitude") == decision.recommended.count(restricted)


def test_the_desk_describes_every_kind_of_governed_hold() -> None:
    debts = [
        _stampDebt("owner/level", safe=False, reasons=["level-disagrees-with-computed-grade"]),
        _stampDebt("owner/rewrite", safe=False, reasons=["stored-grade-differs-from-computed-grade"]),
        _stampDebt("owner/missing", safe=False, reasons=["stored-grade-missing"]),
        _stampDebt("owner/both", safe=False, reasons=["level-disagrees-with-computed-grade", "stored-grade-differs-from-computed-grade"]),
        replace(_debt("trust_stamp_stale", "owner/unknown"), observed_state={}),
    ]

    (decision,) = _stampDesk(*debts).decisions

    text = decision.recommended
    assert "5 stamp(s) are governed" in text
    assert "2 with a computed grade that disagrees with the stored level" in text
    assert "2 whose refresh would rewrite the stored grade" in text
    assert "1 with no stored grade to preserve" in text
    assert "1 with no recorded hold reason" in text
    assert "#2148" in text
