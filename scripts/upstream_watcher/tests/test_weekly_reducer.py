"""Offline unit and P1-planner integration tests for scripts.upstream_watcher.weekly_reducer.

Run with:
    pytest scripts/upstream_watcher/tests/test_weekly_reducer.py -v
"""

from __future__ import annotations

import copy
import datetime as dt
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.upstream_watcher import batch, envelope, repository_batch
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.weekly_reducer import (
    DECISION_ABSENT,
    DECISION_FLUSH,
    DECISION_HELD_SCOPE,
    DECISION_HOLD,
    DECISION_REJECTED,
    DECISION_REPLAYED,
    DECISION_UNAVAILABLE,
    DECISION_URGENT,
    PRESENCE_PRESENT_CANDIDATE,
    PRESENCE_PRESENT_TRACKED,
    PRESENCE_UNKNOWN,
    PRESENCE_VANISHED,
    FirstSeenPin,
    PollInput,
    ReducerConfig,
    ScopedCompleteInventory,
    empty_state,
    parse_strict_utc,
    poll_input_from_batch_report,
    qualify_complete_inventory,
    reduce_poll,
)

# Verified UTC calendar anchors (Nov 1, 2026 is Sunday):
TUE_NOV_10 = dt.datetime(2026, 11, 10, 6, 0, tzinfo=dt.timezone.utc)
WED_NOV_11 = dt.datetime(2026, 11, 11, 6, 0, tzinfo=dt.timezone.utc)
THU_NOV_12 = dt.datetime(2026, 11, 12, 6, 0, tzinfo=dt.timezone.utc)
MON_NOV_16 = dt.datetime(2026, 11, 16, 6, 0, tzinfo=dt.timezone.utc)
TUE_NOV_17 = dt.datetime(2026, 11, 17, 6, 0, tzinfo=dt.timezone.utc)

POLICY = {
    "shared_source_model": "repo_envelope",
    "legacy_transition": "preserve_plan",
}


class OfflineFakeGh:
    """Offline read-only FakeGh for real P1 repository_batch planning; forbids all writes."""

    def __init__(self, issues: list[dict[str, Any]] | None = None, comments: dict[int, list[dict[str, Any]]] | None = None):
        self.issues = copy.deepcopy(issues or [])
        self.comments = copy.deepcopy(comments or {})

    def list_issues(self, state: str, since: str | None = None, labels: str | None = None) -> list[dict[str, Any]]:
        wanted = set(filter(None, (labels or "").split(",")))
        out = []
        for issue in self.issues:
            if issue.get("state") != state:
                continue
            if since and str(issue.get("updated_at") or "") < since:
                continue
            issue_labels = {
                lbl["name"] if isinstance(lbl, dict) else lbl
                for lbl in issue.get("labels", [])
            }
            if wanted and not wanted <= issue_labels:
                continue
            out.append(copy.deepcopy(issue))
        return out

    def list_comments(self, number: int) -> list[dict[str, Any]]:
        return copy.deepcopy(self.comments.get(number, []))

    def child_state(self, number: int) -> str:
        return "unknown"

    def create_issue(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("OfflineFakeGh forbids create_issue")

    def edit_issue(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("OfflineFakeGh forbids edit_issue")

    def edit_labels(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("OfflineFakeGh forbids edit_labels")

    def comment(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("OfflineFakeGh forbids comment")


def _base_authority() -> dict[str, dict[str, Any]]:
    """Authority map covering same-repo siblings, canonical removals, C1 Ruflo/AgentDB, #1833 hold, and GBrain."""
    return {
        # Same-repo sibling pair sharing acme/shared-repo with distinct roots
        "alice/suite-a": {
            "id": "alice/suite-a",
            "links": {"github": "https://github.com/acme/shared-repo"},
            "upstreamComponentRoot": "packages/a/skills",
            "suiteComponents": ["alice/old-leaf", "alice/kept-leaf"],
        },
        "alice/old-leaf": {"id": "alice/old-leaf"},
        "alice/kept-leaf": {"id": "alice/kept-leaf"},
        "bob/suite-b": {
            "id": "bob/suite-b",
            "links": {"github": "https://github.com/acme/shared-repo"},
            "upstreamComponentRoot": "packages/b/skills",
            "suiteComponents": ["bob/core-leaf"],
        },
        "bob/core-leaf": {"id": "bob/core-leaf"},
        # Unrelated healthy repo
        "carol/other-suite": {
            "id": "carol/other-suite",
            "links": {"github": "https://github.com/other/repo"},
            "suiteComponents": ["carol/leaf-one"],
        },
        "carol/leaf-one": {"id": "carol/leaf-one"},
        # C1 distinct release repositories: Ruflo capstone vs nested AgentDB
        "ruvnet/ruflo": {
            "id": "ruvnet/ruflo",
            "links": {"github": "https://github.com/ruvnet/ruflo"},
            "suiteComponents": ["ruvnet/ruflo-leaf"],
        },
        "ruvnet/ruflo-leaf": {"id": "ruvnet/ruflo-leaf"},
        "ruvnet/agentdb": {
            "id": "ruvnet/agentdb",
            "links": {"github": "https://github.com/ruvnet/agentdb"},
            "suiteComponents": ["ruvnet/agentdb-leaf"],
        },
        "ruvnet/agentdb-leaf": {"id": "ruvnet/agentdb-leaf"},
        # Frozen skill (GBrain)
        "garrytan/gbrain": {
            "id": "garrytan/gbrain",
            "links": {"github": "https://github.com/garrytan/gbrain"},
            "suiteComponents": ["garrytan/gbrain-leaf"],
        },
        "garrytan/gbrain-leaf": {"id": "garrytan/gbrain-leaf"},
        # Legacy hold repo (#1833-style)
        "legacy/suite": {
            "id": "legacy/suite",
            "links": {"github": "https://github.com/legacy/repo"},
            "suiteComponents": ["legacy/leaf"],
        },
        "legacy/leaf": {"id": "legacy/leaf"},
    }


def _plan_batch(
    raw_findings: list[dict[str, Any]],
    authority: dict[str, dict[str, Any]],
    gh: OfflineFakeGh | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], frozenset[str]]:
    """Run the REAL P1 canonical planner (plan_only=True, apply=False) and return report + planned findings."""
    fake_gh = gh or OfflineFakeGh()
    report, code = repository_batch.run_repository_batch(
        raw_findings,
        fake_gh,
        apply=False,
        authority=authority,
        index_loader=lambda: {"byId": {}, "bySlug": {}},
        policy=POLICY,
        historical_loader=lambda _ident: {},
        plan_only=True,
    )
    assert code == 0, f"P1 planner failed: {report.get('unknownEvidence')}"
    assert report["writeReadiness"] is False
    assert report["actualIssuesCreated"] == 0
    assert report["actualIssuesUpdated"] == 0

    named_findings: list[dict[str, Any]] = []
    held_repos: set[str] = set()
    for repo_plan in report["repositories"]:
        if repo_plan.get("knownLegacyHolds"):
            held_repos.add(repo_plan["repository"])
        payload = repo_plan.get("payload")
        if payload:
            named_findings.extend(copy.deepcopy(payload["findings"]))
    return report, named_findings, frozenset(held_repos)


def _open_envelope_issue(
    report: dict[str, Any],
    repo: str,
    *,
    number: int = 100,
    updated_at: str = "2026-11-10T06:00:00Z",
) -> dict[str, Any]:
    """Render a valid open repository-envelope issue from a real P1 planner report."""
    repo_plan = next(r for r in report["repositories"] if r["repository"] == repo)
    payload = copy.deepcopy(repo_plan["payload"])
    assert payload is not None
    return {
        "number": number,
        "state": "open",
        "title": envelope.title(payload),
        "labels": [{"name": "upstream:release"}],
        "body": envelope.render(payload),
        "updated_at": updated_at,
    }


def _raw_update(
    skill_id: str,
    repo: str,
    version: str,
    *,
    previous_version: str = "v0.9.0",
    released_at: str = "2026-11-10T01:00:00Z",
    adds: list[str] | None = None,
    removes: list[str] | None = None,
    liveness: list[dict[str, Any]] | None = None,
    liveness_unknown: list[str] | None = None,
    name_drift: list[dict[str, Any]] | None = None,
    component_root: str | None = "skills",
    mode: str = "components",
    finding_type: str = "update",
) -> dict[str, Any]:
    obs: dict[str, Any] = {
        "finding_type": finding_type,
        "skillId": skill_id,
        "currentVersion": previous_version,
        "newVersion": version,
        "releasedAt": released_at,
        "sourceUrl": f"https://github.com/{repo}/releases/tag/{version}",
        "mode": mode,
        "componentAdds": list(adds or []),
        "componentRemoves": list(removes or []),
        "linkLiveness": list(liveness or []),
        "nameDrift": list(name_drift or []),
    }
    if component_root is not None:
        obs["upstreamComponentRoot"] = component_root
    if liveness_unknown is not None:
        obs["linkLivenessUnknown"] = list(liveness_unknown)
    return obs


# ---------------------------------------------------------------------------
# 1. Real P1 planner report['observedFindings'] + canonical plan + sibling isolation
# ---------------------------------------------------------------------------


def test_real_p1_planner_preserves_canonical_removal_evidence_and_sibling_isolation():
    authority = _base_authority()
    raw_findings = [
        _raw_update(
            "alice/suite-a",
            "acme/shared-repo",
            "v1.0.0",
            adds=["alpha", "beta"],
            removes=["old-leaf"],  # P1 planner resolves slug -> canonical alice/old-leaf
            liveness=[
                {
                    "skillId": "alice/kept-leaf",
                    "url": "https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/kept-leaf/SKILL.md",
                    "rawUrl": "https://raw.githubusercontent.com/acme/shared-repo/v1.0.0/packages/a/skills/kept-leaf/SKILL.md",
                    "status": 503,
                }
            ],
            name_drift=[
                {
                    "skillId": "alice/kept-leaf",
                    "registrySlug": "kept-leaf",
                    "upstreamName": "Kept Leaf Renamed",
                    "sanitizedName": "kept-leaf-renamed",
                    "fixCommand": "gaia dev rename alice/kept-leaf alice/kept-leaf-renamed",
                }
            ],
            component_root="packages/a/skills",
        ),
        _raw_update(
            "bob/suite-b",
            "acme/shared-repo",
            "v1.0.0",
            adds=["alpha"],  # Same repo, same version, SAME slug, DIFFERENT root & suggestedId
            component_root="packages/b/skills",
        ),
    ]

    report, planned_findings, held_repos = _plan_batch(raw_findings, authority)
    assert held_repos == frozenset()
    assert len(planned_findings) == 2

    by_id = {f["skillId"]: f for f in planned_findings}
    assert by_id["alice/suite-a"]["componentRemoves"] == ["alice/old-leaf"]

    poll = poll_input_from_batch_report("poll-2026-11-10", TUE_NOV_10, report)
    assert poll.observed_findings == report["observedFindings"]
    res = reduce_poll(empty_state(), poll, authority)

    assert res.status == "applied"
    assert res.replayed is False
    assert res.write_authorized is False
    assert res.rejected_observations == ()
    assert res.eligible == ()  # Tuesday, non-urgent (503 is not urgent) -> hold

    bucket_a = res.state.get_bucket("acme/shared-repo", "alice/suite-a")
    bucket_b = res.state.get_bucket("acme/shared-repo", "bob/suite-b")
    assert bucket_a is not None and bucket_b is not None

    # Exact canonical finding snapshot preserved unchanged (no dropped removes/liveness/drift)
    assert bucket_a.latest_finding == by_id["alice/suite-a"]
    assert bucket_a.latest_finding_sha256 == by_id["alice/suite-a"]["payloadSha256"]
    assert bucket_a.latest_finding["componentRemoves"] == ["alice/old-leaf"]
    assert len(bucket_a.latest_finding["linkLiveness"]) == 1
    assert len(bucket_a.latest_finding["nameDrift"]) == 1

    # Sibling isolation on identical repo + version + slug ("acme/shared-repo:alpha")
    row_a = bucket_a.rows["acme/shared-repo:alpha"]
    row_b = bucket_b.rows["acme/shared-repo:alpha"]
    assert row_a.suggested_id == "alice/alpha"
    assert row_b.suggested_id == "bob/alpha"
    assert row_a.first_seen_pin.evidence_url.endswith("/blob/v1.0.0/packages/a/skills/alpha/SKILL.md")
    assert row_b.first_seen_pin.evidence_url.endswith("/blob/v1.0.0/packages/b/skills/alpha/SKILL.md")
    assert row_a.first_seen_pin != row_b.first_seen_pin


# ---------------------------------------------------------------------------
# 2. Preexisting valid envelope: A current, B retained-only, omitted candidate
# ---------------------------------------------------------------------------


def test_preexisting_envelope_retained_sibling_never_advances_or_flushes_and_omitted_candidate_is_unknown_without_inventory():
    """Production-like real planner test with preexisting open envelope:
    * Day 1 (Tue): both A and B observed; A has alpha & beta.
    * Day 2 (Thu): ONLY A observed on v1.1.0 with alpha only (beta leaves raw componentAdds
      but is retained in canonical candidates by batch.merge_rows); B is retained-only in
      the canonical envelope (absent from report['observedFindings']). Because an ordinary
      run_repository_batch report provides NO scoped complete inventory, beta's presence
      drops to PRESENCE_UNKNOWN with NO vanished mark.
    * Day 3 (Mon flush day): ONLY A observed again; B is STILL retained-only in canonical.
    """
    authority = _base_authority()

    day1_raw = [
        _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha", "beta"], component_root="packages/a/skills"),
        _raw_update("bob/suite-b", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/b/skills"),
    ]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    r1 = reduce_poll(
        empty_state(),
        poll_input_from_batch_report("poll-day1", TUE_NOV_10, day1_report),
        authority,
    )
    assert r1.status == "applied"
    assert r1.accepted_scopes == (("acme/shared-repo", "alice/suite-a"), ("acme/shared-repo", "bob/suite-b"))

    # Seed preexisting open envelope from Day 1 into OfflineFakeGh.
    open_issue_day1 = _open_envelope_issue(day1_report, "acme/shared-repo", number=101, updated_at="2026-11-10T06:00:00Z")
    gh_day2 = OfflineFakeGh(issues=[open_issue_day1])

    # Day 2 (Thu): ONLY alice/suite-a is observed on v1.1.0 with adds=["alpha"] (beta omitted).
    day2_raw = [
        _raw_update(
            "alice/suite-a",
            "acme/shared-repo",
            "v1.1.0",
            previous_version="v1.0.0",
            adds=["alpha"],
            component_root="packages/a/skills",
        ),
    ]
    day2_report, day2_planned, _ = _plan_batch(day2_raw, authority, gh=gh_day2)

    # Confirm the real planner retained BOTH bob/suite-b in the envelope AND beta in alice/suite-a's candidates.
    assert sorted(f["skillId"] for f in day2_planned) == ["alice/suite-a", "bob/suite-b"]
    planned_a = next(f for f in day2_planned if f["skillId"] == "alice/suite-a")
    assert sorted(row["id"] for row in planned_a["candidates"]) == [
        "acme/shared-repo:alpha",
        "acme/shared-repo:beta",
    ]
    assert [f["skillId"] for f in day2_report["observedFindings"]] == ["alice/suite-a"]

    r2 = reduce_poll(
        r1.state,
        poll_input_from_batch_report("poll-day2", THU_NOV_12, day2_report),
        authority,
    )
    assert r2.status == "applied"
    assert r2.rejected_observations == ()
    assert r2.accepted_scopes == (("acme/shared-repo", "alice/suite-a"),)
    assert r2.eligible == ()

    bucket_a = r2.state.get_bucket("acme/shared-repo", "alice/suite-a")
    bucket_b = r2.state.get_bucket("acme/shared-repo", "bob/suite-b")
    assert bucket_a is not None and bucket_b is not None

    # alice/suite-a: alpha keeps immutable v1.0.0 pin and advances last_seen to v1.1.0 / Day 2.
    alpha_a = bucket_a.rows["acme/shared-repo:alpha"]
    assert alpha_a.first_seen_pin == FirstSeenPin(
        first_seen_version="v1.0.0",
        evidence_url="https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/alpha/SKILL.md",
        first_seen_at="2026-11-10T06:00:00Z",
        first_seen_poll_id="poll-day1",
    )
    assert alpha_a.last_seen_version == "v1.1.0"
    assert alpha_a.last_seen_at == "2026-11-12T06:00:00Z"
    assert alpha_a.present_in_latest is True
    assert alpha_a.presence == PRESENCE_PRESENT_CANDIDATE

    # alice/suite-a: beta left raw componentAdds without a complete inventory -> UNKNOWN, NOT vanished!
    beta_a = bucket_a.rows["acme/shared-repo:beta"]
    assert beta_a.present_in_latest is False
    assert beta_a.presence == PRESENCE_UNKNOWN
    assert beta_a.historical_only is False
    assert beta_a.last_seen_version == "v1.0.0"
    assert beta_a.last_seen_at == "2026-11-10T06:00:00Z"  # NOT advanced!
    assert beta_a.last_seen_poll_id == "poll-day1"
    assert beta_a.vanished_at is None
    assert beta_a.vanished_poll_id is None
    assert bucket_a.present_row_ids == ("acme/shared-repo:alpha",)
    assert bucket_a.unknown_presence_row_ids == ("acme/shared-repo:beta",)
    assert bucket_a.vanished_row_ids == ()
    assert bucket_a.tracked_present_row_ids == ()
    assert bucket_a.historical_row_ids == ()
    assert bucket_a.latest_finding == planned_a  # Untouched canonical finding still holds beta

    # bob/suite-b: retained in canonical envelope ONLY -> NOT observed, NOT advanced, NOT eligible!
    assert bucket_b == r1.state.get_bucket("acme/shared-repo", "bob/suite-b")
    assert bucket_b.sighting_count == 1
    assert bucket_b.revision == 1
    assert r2.decisions[("acme/shared-repo", "bob/suite-b")].decision == DECISION_ABSENT
    assert r2.decisions[("acme/shared-repo", "bob/suite-b")].eligible is False

    # Day 3 (Mon flush day): ONLY A observed again; B still retained-only in canonical payload.
    r3 = reduce_poll(
        r2.state,
        poll_input_from_batch_report("poll-monday", MON_NOV_16, day2_report),
        authority,
    )
    assert r3.status == "applied"
    assert r3.write_authorized is False
    assert [(d.repository, d.named_id) for d in r3.eligible] == [("acme/shared-repo", "alice/suite-a")]

    dec_a = r3.decisions[("acme/shared-repo", "alice/suite-a")]
    dec_b = r3.decisions[("acme/shared-repo", "bob/suite-b")]
    assert dec_a.decision == DECISION_FLUSH
    assert dec_a.eligible is True
    assert dec_a.reasons == ("flush-day",)
    assert dec_a.present_row_ids == ("acme/shared-repo:alpha",)
    assert dec_a.unknown_presence_row_ids == ("acme/shared-repo:beta",)
    assert dec_a.vanished_row_ids == ()

    # Retained-only sibling B on Monday flush day is STILL DECISION_ABSENT and NEVER eligible!
    assert dec_b.decision == DECISION_ABSENT
    assert dec_b.eligible is False
    assert dec_b.finding is None
    assert r3.state.get_bucket("acme/shared-repo", "bob/suite-b") == r1.state.get_bucket("acme/shared-repo", "bob/suite-b")


def test_new_historical_only_row_and_unseen_retained_sibling_do_not_fabricate_sightings():
    """Starting from empty_state() against a preexisting open envelope:
    * Unseen retained sibling B creates NO bucket at all.
    * Retained candidate row beta (omitted from raw componentAdds) stays in canonical view
      as historical_only without counting as present, vanished, or fabricating a prior timestamp.
    """
    authority = _base_authority()
    day1_raw = [
        _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha", "beta"], component_root="packages/a/skills"),
        _raw_update("bob/suite-b", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/b/skills"),
    ]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    open_issue = _open_envelope_issue(day1_report, "acme/shared-repo", number=102)

    day2_raw = [
        _raw_update(
            "alice/suite-a",
            "acme/shared-repo",
            "v1.1.0",
            previous_version="v1.0.0",
            adds=["alpha"],
            component_root="packages/a/skills",
        ),
    ]
    day2_report, _, _ = _plan_batch(day2_raw, authority, gh=OfflineFakeGh(issues=[open_issue]))

    # Fresh reducer state sees Day 2 directly.
    res = reduce_poll(
        empty_state(),
        poll_input_from_batch_report("poll-fresh-day2", THU_NOV_12, day2_report),
        authority,
    )
    assert res.status == "applied"
    assert res.accepted_scopes == (("acme/shared-repo", "alice/suite-a"),)
    # Retained-only sibling B never created a bucket!
    assert res.state.get_bucket("acme/shared-repo", "bob/suite-b") is None

    bucket_a = res.state.get_bucket("acme/shared-repo", "alice/suite-a")
    assert bucket_a is not None
    assert bucket_a.present_row_ids == ("acme/shared-repo:alpha",)
    assert bucket_a.vanished_row_ids == ()  # Never journaled as present -> not marked vanished
    assert bucket_a.historical_row_ids == ("acme/shared-repo:beta",)

    beta = bucket_a.rows["acme/shared-repo:beta"]
    assert beta.historical_only is True
    assert beta.present_in_latest is False
    assert beta.first_seen_pin == FirstSeenPin(
        first_seen_version="v1.0.0",
        evidence_url="https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/beta/SKILL.md",
        first_seen_at=None,
        first_seen_poll_id=None,
    )
    assert beta.last_seen_at is None
    assert beta.last_seen_poll_id is None
    assert beta.vanished_at is None
    assert beta.vanished_poll_id is None
    # Canonical view still preserves beta untouched.
    assert any(r["id"] == "acme/shared-repo:beta" for r in bucket_a.latest_finding["candidates"])


def test_one_week_old_unreobserved_snapshot_never_becomes_eligible_on_monday():
    """Directly guards against stale prior-poll snapshots authorizing a Monday flush."""
    authority = _base_authority()
    raw = [_raw_update("carol/other-suite", "other/repo", "v2.0.0", adds=["gamma"])]
    report, _, _ = _plan_batch(raw, authority)
    r1 = reduce_poll(
        empty_state(),
        poll_input_from_batch_report("poll-week-ago", TUE_NOV_10, report),
        authority,
    )
    # Next Monday: empty current observation (even if canonical plan is empty) -> ABSENT
    r2 = reduce_poll(
        r1.state,
        PollInput("poll-next-monday", MON_NOV_16, observed_findings=[], planned_findings=[]),
        authority,
    )
    assert r2.status == "applied"
    assert r2.eligible == ()
    dec = r2.decisions[("other/repo", "carol/other-suite")]
    assert dec.decision == DECISION_ABSENT
    assert dec.eligible is False
    assert dec.finding is None
    bucket = r2.state.get_bucket("other/repo", "carol/other-suite")
    assert bucket is not None
    assert bucket.vanished_row_ids == ()
    assert bucket.present_row_ids == ("other/repo:gamma",)


# ---------------------------------------------------------------------------
# 3. Pin continuity: independently planned later finding fails closed
# ---------------------------------------------------------------------------


def test_pin_conflict_on_independently_planned_later_finding_fails_closed_preserving_prior_state():
    """An otherwise valid, independently planned v1.1.0 finding (without a preexisting
    open envelope) re-pins alpha to v1.1.0. The reducer MUST reject alice/suite-a fail-closed,
    preserving Day 1 state byte-for-byte, while unrelated carol/other-suite proceeds cleanly.
    """
    authority = _base_authority()

    day1_raw = [_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills")]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    r1 = reduce_poll(
        empty_state(),
        poll_input_from_batch_report("poll-pin-day1", TUE_NOV_10, day1_report),
        authority,
    )
    assert r1.status == "applied"
    day1_bucket = r1.state.get_bucket("acme/shared-repo", "alice/suite-a")
    assert day1_bucket is not None

    # Independently planned Day 2 (no preexisting envelope in OfflineFakeGh):
    # planner emits a valid sealed finding whose alpha row has firstSeenVersion="v1.1.0".
    day2_raw = [
        _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", previous_version="v1.0.0", adds=["alpha"], component_root="packages/a/skills"),
        _raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"]),
    ]
    day2_report, _, _ = _plan_batch(day2_raw, authority)

    r2 = reduce_poll(
        r1.state,
        poll_input_from_batch_report("poll-pin-conflict", MON_NOV_16, day2_report),
        authority,
    )
    assert r2.status == "applied"
    assert len(r2.rejected_observations) == 1
    assert r2.rejected_observations[0].named_id == "alice/suite-a"
    assert "pin conflict" in r2.rejected_observations[0].reason

    # Affected scope is rejected and preserved byte-for-byte!
    assert r2.decisions[("acme/shared-repo", "alice/suite-a")].decision == DECISION_REJECTED
    assert r2.decisions[("acme/shared-repo", "alice/suite-a")].eligible is False
    assert r2.state.get_bucket("acme/shared-repo", "alice/suite-a") == day1_bucket

    # Unrelated healthy repo still gets full coverage!
    assert [(d.repository, d.named_id) for d in r2.eligible] == [("other/repo", "carol/other-suite")]


# ---------------------------------------------------------------------------
# 4. Scoped fresh urgency: carried 404 on unknown liveness vs fresh tracked 404/410
# ---------------------------------------------------------------------------


def test_raw_unknown_liveness_with_carried_404_is_nonurgent_while_canonical_is_unchanged():
    """Real planner settle_liveness carries a prior 404 forward when linkLivenessUnknown
    includes that component. The reducer must keep the canonical 404 untouched AND NOT
    grant urgency because there is no fresh current raw check.
    """
    authority = _base_authority()
    day1_raw = [
        _raw_update(
            "alice/suite-a",
            "acme/shared-repo",
            "v1.0.0",
            adds=["alpha"],
            liveness=[
                {
                    "skillId": "alice/kept-leaf",
                    "url": "https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/kept-leaf/SKILL.md",
                    "status": 404,
                }
            ],
            component_root="packages/a/skills",
        )
    ]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    open_issue = _open_envelope_issue(day1_report, "acme/shared-repo", number=103)

    # Day 2 (Thu): raw liveness check for alice/kept-leaf is UNKNOWN (not fresh 404).
    day2_raw = [
        _raw_update(
            "alice/suite-a",
            "acme/shared-repo",
            "v1.0.0",
            adds=["alpha"],
            liveness=[],
            liveness_unknown=["alice/kept-leaf"],
            component_root="packages/a/skills",
        )
    ]
    day2_report, day2_planned, _ = _plan_batch(day2_raw, authority, gh=OfflineFakeGh(issues=[open_issue]))

    # Confirm real planner carried the 404 forward into canonical linkLiveness!
    assert len(day2_planned) == 1
    assert day2_planned[0]["linkLiveness"][0]["status"] == 404

    res = reduce_poll(
        empty_state(),
        poll_input_from_batch_report("poll-carried-404", THU_NOV_12, day2_report),
        authority,
    )
    assert res.status == "applied"
    assert res.eligible == ()
    dec = res.decisions[("acme/shared-repo", "alice/suite-a")]
    assert dec.decision == DECISION_HOLD
    assert dec.eligible is False
    assert dec.reasons == ("within-review-window",)
    # Full untouched canonical finding still preserves the carried 404.
    bucket = res.state.get_bucket("acme/shared-repo", "alice/suite-a")
    assert bucket is not None
    assert bucket.latest_finding == day2_planned[0]
    assert bucket.latest_finding["linkLiveness"][0]["status"] == 404


@pytest.mark.parametrize("status,skill_id,expect_urgent", [
    (404, "alice/kept-leaf", True),
    (410, "alice/kept-leaf", True),
    (404, "bob/core-leaf", False),        # Foreign sibling component -> not tracked in alice/suite-a
    (404, "alice/untracked-leaf", False), # Untracked component -> not in suiteComponents
    (403, "alice/kept-leaf", False),
    (429, "alice/kept-leaf", False),
    (500, "alice/kept-leaf", False),
    (503, "alice/kept-leaf", False),
    ("network_error", "alice/kept-leaf", False),
])
def test_per_named_urgency_requires_tracked_fresh_404_or_410_and_isolates_siblings(
    status: Any,
    skill_id: str,
    expect_urgent: bool,
):
    authority = _base_authority()
    raw = [
        _raw_update(
            "alice/suite-a",
            "acme/shared-repo",
            "v1.0.0",
            adds=["alpha"],
            liveness=[
                {
                    "skillId": skill_id,
                    "url": "https://github.com/acme/shared-repo/blob/v1.0.0/skills/kept-leaf/SKILL.md",
                    "status": status,
                }
            ],
            component_root="packages/a/skills",
        ),
        _raw_update(
            "bob/suite-b",
            "acme/shared-repo",
            "v1.0.0",
            adds=["alpha"],
            component_root="packages/b/skills",
        ),
    ]
    report, _, _ = _plan_batch(raw, authority)
    res = reduce_poll(
        empty_state(),
        poll_input_from_batch_report("p-urg", TUE_NOV_10, report),
        authority,
    )
    assert res.status == "applied"
    dec_a = res.decisions[("acme/shared-repo", "alice/suite-a")]
    dec_b = res.decisions[("acme/shared-repo", "bob/suite-b")]

    # Sibling B NEVER inherits urgency from Sibling A
    assert dec_b.decision == DECISION_HOLD
    assert dec_b.eligible is False

    if expect_urgent:
        assert dec_a.decision == DECISION_URGENT
        assert dec_a.eligible is True
        assert dec_a.reasons == (f"dead-link:{skill_id}:{status}",)
        assert [(d.repository, d.named_id) for d in res.eligible] == [("acme/shared-repo", "alice/suite-a")]
    else:
        assert dec_a.decision == DECISION_HOLD
        assert dec_a.eligible is False
        assert res.eligible == ()


def test_raw_404_not_confirmed_in_sealed_canonical_finding_does_not_manufacture_urgency():
    authority = _base_authority()
    raw_clean = [_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills")]
    _, planned_clean, _ = _plan_batch(raw_clean, authority)

    # Raw claims a 404 that is absent from the sealed canonical finding.
    raw_with_unconfirmed_404 = copy.deepcopy(raw_clean)
    raw_with_unconfirmed_404[0]["linkLiveness"] = [
        {
            "skillId": "alice/kept-leaf",
            "url": "https://github.com/acme/shared-repo/blob/v1.0.0/skills/kept-leaf/SKILL.md",
            "status": 404,
        }
    ]
    res = reduce_poll(
        empty_state(),
        PollInput("p-unconfirmed-404", TUE_NOV_10, raw_with_unconfirmed_404, planned_clean),
        authority,
    )
    assert res.status == "applied"
    assert res.decisions[("acme/shared-repo", "alice/suite-a")].decision == DECISION_HOLD
    assert res.eligible == ()


# ---------------------------------------------------------------------------
# 5. Replay vs later verified identical poll vs conflicts (both tracks + holds)
# ---------------------------------------------------------------------------


def test_replay_vs_later_identical_sighting_vs_conflicts_and_stale_time():
    authority = _base_authority()
    raw_v1 = [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])]
    raw_v2 = [_raw_update("carol/other-suite", "other/repo", "v1.1.0", adds=["gamma"])]
    report_v1, planned_v1, _ = _plan_batch(raw_v1, authority)
    report_v2, planned_v2, _ = _plan_batch(raw_v2, authority)

    poll_1 = poll_input_from_batch_report("poll-1", TUE_NOV_10, report_v1)
    r1 = reduce_poll(empty_state(), poll_1, authority)
    assert r1.status == "applied"
    assert r1.state.revision == 1
    assert r1.state.get_bucket("other/repo", "carol/other-suite").sighting_count == 1

    # Exact replay of poll-1 -> idempotent no-op
    r_replay = reduce_poll(r1.state, poll_1, authority)
    assert r_replay.status == "replayed"
    assert r_replay.replayed is True
    assert r_replay.state == r1.state
    assert r_replay.eligible == ()
    assert r_replay.decisions[("other/repo", "carol/other-suite")].decision == DECISION_REPLAYED

    # Conflicting reuse of poll-1 across planned_findings, observed_findings, held_repos, or observed_at
    for bad_poll in (
        PollInput("poll-1", TUE_NOV_10, raw_v1, planned_v2),
        PollInput("poll-1", TUE_NOV_10, raw_v2, planned_v1),
        PollInput("poll-1", TUE_NOV_10, raw_v1, planned_v1, held_repos=frozenset({"other/repo"})),
        PollInput("poll-1", WED_NOV_11, raw_v1, planned_v1),
    ):
        r_conflict = reduce_poll(r1.state, bad_poll, authority)
        assert r_conflict.status == "rejected"
        assert "conflicting poll_id" in (r_conflict.rejection_reason or "")
        assert r_conflict.state == r1.state
        assert r_conflict.eligible == ()

    # Stale timestamp with new poll_id -> rejected fail-closed
    r_stale = reduce_poll(
        r1.state,
        PollInput("poll-stale", TUE_NOV_10 - dt.timedelta(hours=1), raw_v1, planned_v1),
        authority,
    )
    assert r_stale.status == "rejected"
    assert "stale observed_at" in (r_stale.rejection_reason or "")
    assert r_stale.state == r1.state

    # Later verified identical poll on Monday -> applied, advances sighting_count & revision
    r_later = reduce_poll(
        r1.state,
        poll_input_from_batch_report("poll-monday", MON_NOV_16, report_v1),
        authority,
    )
    assert r_later.status == "applied"
    assert r_later.replayed is False
    assert r_later.state.revision == 2
    bucket = r_later.state.get_bucket("other/repo", "carol/other-suite")
    assert bucket.sighting_count == 2
    assert bucket.revision == 2
    assert bucket.pending_since == "2026-11-10T06:00:00Z"
    assert bucket.last_observed_at == "2026-11-16T06:00:00Z"
    assert bucket.last_poll_id == "poll-monday"
    assert len(r_later.eligible) == 1
    assert r_later.eligible[0].decision == DECISION_FLUSH
    assert r_later.eligible[0].write_authorized is False


# ---------------------------------------------------------------------------
# 6. Window-elapsed from pending_since (not releasedAt)
# ---------------------------------------------------------------------------


def test_window_elapsed_uses_pending_since_never_released_at():
    authority = _base_authority()
    raw = [_raw_update("carol/other-suite", "other/repo", "v1.0.0", released_at="2026-10-01T00:00:00Z", adds=["gamma"])]
    report, _, _ = _plan_batch(raw, authority)
    cfg = ReducerConfig(flush_weekday=6, window_days=7)

    r1 = reduce_poll(empty_state(), poll_input_from_batch_report("p1", TUE_NOV_10, report), authority, cfg)
    assert r1.eligible == ()

    r2 = reduce_poll(r1.state, poll_input_from_batch_report("p2", WED_NOV_11, report), authority, cfg)
    assert r2.eligible == ()
    assert r2.decisions[("other/repo", "carol/other-suite")].decision == DECISION_HOLD

    r3 = reduce_poll(r2.state, poll_input_from_batch_report("p3", TUE_NOV_17, report), authority, cfg)
    assert len(r3.eligible) == 1
    assert r3.eligible[0].decision == DECISION_FLUSH
    assert r3.eligible[0].reasons == ("window-elapsed",)
    assert r3.eligible[0].write_authorized is False


# ---------------------------------------------------------------------------
# 7. Checked join failures & duplicate conflicts
# ---------------------------------------------------------------------------


def test_checked_join_rejects_missing_canonical_mismatches_and_duplicate_conflicts():
    authority = _base_authority()
    raw_a = _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills")
    raw_a_v2 = _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", adds=["alpha"], component_root="packages/a/skills")
    raw_a_boot = _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills", finding_type="bootstrap")
    raw_other = _raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])

    _, planned_a, _ = _plan_batch([raw_a], authority)
    _, planned_a_v2, _ = _plan_batch([raw_a_v2], authority)
    _, planned_other, _ = _plan_batch([raw_other], authority)

    cases = [
        # Missing canonical match for raw observation
        ([raw_a, raw_other], planned_other, "missing canonical"),
        # Version/sourceUrl join mismatch
        ([raw_a, raw_other], planned_a_v2 + planned_other, "join mismatch"),
        # Finding kind join mismatch (bootstrap vs update)
        ([raw_a_boot, raw_other], planned_a + planned_other, "join mismatch"),
        # Raw componentAdds disagrees with canonical
        (
            [_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha", "beta"], component_root="packages/a/skills"), raw_other],
            planned_a + planned_other,
            "componentAdds disagrees",
        ),
        # Conflicting duplicate raw observations
        ([raw_a, raw_a_v2, raw_other], planned_a + planned_other, "conflicting duplicate raw"),
        # Conflicting duplicate canonical findings
        ([raw_a, raw_other], planned_a + planned_a_v2 + planned_other, "conflicting duplicate canonical"),
    ]
    for idx, (obs_list, plan_list, expected_substr) in enumerate(cases):
        res = reduce_poll(empty_state(), PollInput(f"p-join-{idx}", MON_NOV_16, obs_list, plan_list), authority)
        assert res.status == "applied"
        assert any(expected_substr in rej.reason for rej in res.rejected_observations), (idx, res.rejected_observations)
        assert res.state.get_bucket("acme/shared-repo", "alice/suite-a") is None
        assert [(d.repository, d.named_id) for d in res.eligible] == [("other/repo", "carol/other-suite")]


# ---------------------------------------------------------------------------
# 8. Defense-in-depth: missing candidates, malformed inputs & malformed scope sets
# ---------------------------------------------------------------------------


def _sealed_valid_pair(authority: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills")
    _, findings, _ = _plan_batch([raw], authority)
    return raw, findings[0]


@pytest.mark.parametrize("mutator", [
    lambda f: f.pop("candidates"),  # Passes envelope.validate_named, must NOT raise KeyError!
    lambda f: f.update({"componentAdds": [["nested-bad"]]}),
    lambda f: f.update({"componentAdds": [{"slug": "bad"}]}),
    lambda f: f.update({"componentAdds": [123]}),
    lambda f: f.update({"componentAdds": ["dup", "dup"]}),
    lambda f: f.update({"componentAdds": ["has space"]}),
    lambda f: f.update({"linkLiveness": ["not-a-dict"]}),
    lambda f: f.update({"linkLiveness": [{"skillId": "alice/kept-leaf", "url": "https://x", "status": True}]}),
    lambda f: f.update({"nameDrift": ["not-a-dict"]}),
    lambda f: f.update({"componentRemoves": ["bob/core-leaf"]}),  # out-of-scope removal
    lambda f: f.update({"componentRemoves": ["bob/suite-b"]}),    # suite root removal
    lambda f: f["candidates"][0].update({"evidenceUrl": "https://github.com/acme/shared-repo/blob/main/packages/a/skills/alpha/SKILL.md"}),
])
def test_malformed_canonical_observations_including_missing_candidates_reject_without_crashing(mutator):
    authority = _base_authority()
    raw_a, bad = _sealed_valid_pair(authority)
    mutator(bad)
    bad = envelope.seal(bad)

    raw_other = [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])]
    _, healthy_other, _ = _plan_batch(raw_other, authority)

    res = reduce_poll(
        empty_state(),
        PollInput("p-neg", MON_NOV_16, [raw_a, *raw_other], [bad, *healthy_other]),
        authority,
    )
    assert res.status == "applied"
    assert len(res.rejected_observations) == 1
    assert res.rejected_observations[0].named_id == "alice/suite-a"
    assert res.state.get_bucket("acme/shared-repo", "alice/suite-a") is None
    assert [(d.repository, d.named_id) for d in res.eligible] == [("other/repo", "carol/other-suite")]


@pytest.mark.parametrize("bad_poll", [
    PollInput("p-bad-1", MON_NOV_16, [], [], held_repos=None),                # type: ignore[arg-type]
    PollInput("p-bad-2", MON_NOV_16, [], [], held_repos="acme/shared-repo"),  # type: ignore[arg-type]
    PollInput("p-bad-3", MON_NOV_16, [], [], held_named_ids=None),            # type: ignore[arg-type]
    PollInput("p-bad-4", MON_NOV_16, [], [], unavailable_named_ids=123),      # type: ignore[arg-type]
    PollInput("p-bad-5", MON_NOV_16, None, []),                               # type: ignore[arg-type]
    PollInput("p-bad-6", MON_NOV_16, [], "not-a-list"),                       # type: ignore[arg-type]
    PollInput("p-bad-7", MON_NOV_16, [], [], complete="yes"),                 # type: ignore[arg-type]
    PollInput("p-bad-8", dt.datetime(2026, 11, 16, 6, 0), [], []),            # naive datetime
])
def test_malformed_scope_sets_and_poll_containers_fail_closed_without_crashing(bad_poll: PollInput):
    authority = _base_authority()
    res = reduce_poll(empty_state(), bad_poll, authority)
    assert res.status == "rejected"
    assert res.rejection_reason
    assert res.eligible == ()
    assert res.write_authorized is False


# ---------------------------------------------------------------------------
# 9. Deep state & decision isolation (no nested mutable aliasing)
# ---------------------------------------------------------------------------


def test_state_and_decision_views_have_no_nested_mutable_aliasing_across_apply_replay_rejection():
    authority = _base_authority()
    raw_1 = [
        _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], removes=["old-leaf"], component_root="packages/a/skills"),
        _raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"]),
    ]
    report_1, _, _ = _plan_batch(raw_1, authority)
    poll_1 = poll_input_from_batch_report("p-iso-1", MON_NOV_16, report_1)
    r1 = reduce_poll(empty_state(), poll_1, authority)
    assert r1.status == "applied"

    scope_a = ("acme/shared-repo", "alice/suite-a")
    scope_c = ("other/repo", "carol/other-suite")

    # Top-level state/decision mappings are read-only MappingProxyType.
    with pytest.raises(TypeError):
        r1.state.buckets[scope_a] = None  # type: ignore[index]
    with pytest.raises(TypeError):
        r1.decisions[scope_a] = None  # type: ignore[index]
    with pytest.raises(TypeError):
        r1.state.buckets[scope_a].rows["x"] = None  # type: ignore[index]

    # Mutating decision view must NOT mutate eligible view or r1.state.
    dec_a = r1.decisions[scope_a]
    elig_a = next(d for d in r1.eligible if (d.repository, d.named_id) == scope_a)
    assert dec_a is not elig_a
    assert dec_a.finding is not None and elig_a.finding is not None
    assert dec_a.finding is not elig_a.finding
    dec_a.finding["componentRemoves"].append("mutated-in-decision")
    dec_a.finding["candidates"][0]["status"] = "rejected"
    assert elig_a.finding["componentRemoves"] == ["alice/old-leaf"]
    assert elig_a.finding["candidates"][0]["status"] == "new"
    assert r1.state.buckets[scope_a].latest_finding["componentRemoves"] == ["alice/old-leaf"]
    assert r1.state.buckets[scope_a].latest_finding["candidates"][0]["status"] == "new"

    # Reverse direction: mutating eligible view must NOT mutate decisions view or r1.state.
    elig_c = next(d for d in r1.eligible if (d.repository, d.named_id) == scope_c)
    dec_c = r1.decisions[scope_c]
    assert elig_c is not dec_c
    assert elig_c.finding is not None and dec_c.finding is not None
    assert elig_c.finding is not dec_c.finding
    elig_c.finding["candidates"][0]["status"] = "mutated-in-eligible"
    assert dec_c.finding["candidates"][0]["status"] == "new"
    assert r1.state.buckets[scope_c].latest_finding["candidates"][0]["status"] == "new"

    # Mutating untouched bucket in r2.state must NOT mutate r1.state.
    raw_2 = [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])]
    report_2, _, _ = _plan_batch(raw_2, authority)
    r2 = reduce_poll(r1.state, poll_input_from_batch_report("p-iso-2", TUE_NOV_17, report_2), authority)
    assert r2.status == "applied"
    r2.state.buckets[scope_a].latest_finding["componentRemoves"].append("mutated-in-r2")
    r2.state.buckets[scope_a].rows["acme/shared-repo:alpha"].latest_row["status"] = "rejected"
    assert r1.state.buckets[scope_a].latest_finding["componentRemoves"] == ["alice/old-leaf"]
    assert r1.state.buckets[scope_a].rows["acme/shared-repo:alpha"].latest_row["status"] == "new"

    # Mutating replayed state must NOT mutate r1.state.
    r_replay = reduce_poll(r1.state, poll_1, authority)
    assert r_replay.status == "replayed"
    r_replay.state.buckets[scope_c].latest_finding["candidates"][0]["status"] = "rejected"
    assert r1.state.buckets[scope_c].latest_finding["candidates"][0]["status"] == "new"

    # Mutating rejected state must NOT mutate r1.state.
    r_rejected = reduce_poll(r1.state, PollInput("p-iso-inc", TUE_NOV_17, [], [], complete=False), authority)
    assert r_rejected.status == "rejected"
    r_rejected.state.buckets[scope_c].latest_finding["candidates"][0]["status"] = "rejected"
    assert r1.state.buckets[scope_c].latest_finding["candidates"][0]["status"] == "new"


# ---------------------------------------------------------------------------
# 10. Tampered digest, incomplete poll, unavailable suite
# ---------------------------------------------------------------------------


def test_tampered_digest_incomplete_poll_and_unavailable_suite_fail_closed():
    authority = _base_authority()
    raw_a, valid_a = _sealed_valid_pair(authority)
    tampered = copy.deepcopy(valid_a)
    tampered["componentRemoves"] = ["alice/old-leaf"]  # Digest no longer matches!

    res_tampered = reduce_poll(empty_state(), PollInput("p-tamp", MON_NOV_16, [raw_a], [tampered]), authority)
    assert res_tampered.status == "applied"
    assert len(res_tampered.rejected_observations) == 1
    assert "digest mismatch" in res_tampered.rejected_observations[0].reason
    assert res_tampered.eligible == ()

    # Seed valid bucket, then send tampered observation on Monday -> preserved & DECISION_REJECTED
    r_seed = reduce_poll(empty_state(), PollInput("p-seed", TUE_NOV_10, [raw_a], [valid_a]), authority)
    r_bad_mon = reduce_poll(r_seed.state, PollInput("p-bad-mon", MON_NOV_16, [raw_a], [tampered]), authority)
    assert r_bad_mon.status == "applied"
    assert r_bad_mon.decisions[("acme/shared-repo", "alice/suite-a")].decision == DECISION_REJECTED
    assert r_bad_mon.decisions[("acme/shared-repo", "alice/suite-a")].eligible is False
    assert r_bad_mon.state.get_bucket("acme/shared-repo", "alice/suite-a") == r_seed.state.get_bucket(
        "acme/shared-repo", "alice/suite-a"
    )
    assert r_bad_mon.eligible == ()

    # Incomplete poll fails closed completely
    r_inc = reduce_poll(r_seed.state, PollInput("p-inc", MON_NOV_16, [raw_a], [valid_a], complete=False), authority)
    assert r_inc.status == "rejected"
    assert r_inc.state == r_seed.state
    assert r_inc.eligible == ()

    # Unavailable suite stays untouched while unrelated repo is eligible
    raw_other = [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])]
    report_other, _, _ = _plan_batch(raw_other, authority)
    r_unavail = reduce_poll(
        r_seed.state,
        poll_input_from_batch_report(
            "p-unavail",
            MON_NOV_16,
            report_other,
            unavailable_named_ids=frozenset({"alice/suite-a"}),
        ),
        authority,
    )
    assert r_unavail.status == "applied"
    assert r_unavail.decisions[("acme/shared-repo", "alice/suite-a")].decision == DECISION_UNAVAILABLE
    assert r_unavail.decisions[("acme/shared-repo", "alice/suite-a")].eligible is False
    assert r_unavail.state.get_bucket("acme/shared-repo", "alice/suite-a").vanished_row_ids == ()
    assert [(d.repository, d.named_id) for d in r_unavail.eligible] == [("other/repo", "carol/other-suite")]


# ---------------------------------------------------------------------------
# 11. Governance invariants: C1 Ruflo/AgentDB, #1833 legacy hold, frozen GBrain
# ---------------------------------------------------------------------------


def test_c1_ruflo_and_agentdb_distinct_sources_and_cross_source_rejection():
    authority = _base_authority()
    raw_c1 = [
        _raw_update("ruvnet/ruflo", "ruvnet/ruflo", "v3.0.0", adds=["r-leaf"]),
        _raw_update("ruvnet/agentdb", "ruvnet/agentdb", "v2.0.0", adds=["a-leaf"]),
    ]
    report_c1, planned_c1, _ = _plan_batch(raw_c1, authority)
    res = reduce_poll(empty_state(), poll_input_from_batch_report("p-c1", MON_NOV_16, report_c1), authority)
    assert res.status == "applied"
    assert [(d.repository, d.named_id) for d in res.eligible] == [
        ("ruvnet/agentdb", "ruvnet/agentdb"),
        ("ruvnet/ruflo", "ruvnet/ruflo"),
    ]

    # Spoofed AgentDB claiming Ruflo release source must fail closed
    spoofed_raw = copy.deepcopy(raw_c1[1])
    spoofed_raw["sourceUrl"] = "https://github.com/ruvnet/ruflo/releases/tag/v2.0.0"
    spoofed_planned = copy.deepcopy(next(f for f in planned_c1 if f["skillId"] == "ruvnet/agentdb"))
    spoofed_planned["sourceUrl"] = "https://github.com/ruvnet/ruflo/releases/tag/v2.0.0"
    spoofed_planned = envelope.seal(spoofed_planned)

    res_spoof = reduce_poll(
        empty_state(),
        PollInput("p-c1-spoof", MON_NOV_16, [spoofed_raw], [spoofed_planned]),
        authority,
    )
    assert len(res_spoof.rejected_observations) == 2  # Both raw and canonical fail closed
    assert all(r.named_id == "ruvnet/agentdb" for r in res_spoof.rejected_observations)
    assert res_spoof.eligible == ()


def test_legacy_hold_1833_and_frozen_gbrain_stay_held_while_unrelated_repo_proceeds():
    authority = _base_authority()
    legacy_payload = envelope.seal(
        {
            "payloadVersion": 2,
            "skillId": "legacy/suite",
            "previousVersion": "v0.8.0",
            "newVersion": "v0.9.0",
            "releasedAt": "2026-10-01T00:00:00Z",
            "sourceUrl": "https://github.com/legacy/repo/releases/tag/v0.9.0",
            "mode": "components",
            "componentAdds": [],
            "componentRemoves": [],
            "linkLiveness": [],
            "nameDrift": [],
            "candidates": [],
        }
    )
    legacy_issue = {
        "number": 1833,
        "state": "open",
        "title": "[upstream] legacy/repo → v0.9.0",
        "labels": [{"name": "upstream:release"}],
        "body": batch.payload_block(legacy_payload),
        "updated_at": "2026-10-01T00:00:00Z",
    }
    gh = OfflineFakeGh(issues=[legacy_issue])

    raw_gov = [
        _raw_update(
            "legacy/suite",
            "legacy/repo",
            "v1.0.0",
            adds=["new-legacy"],
            liveness=[{"skillId": "legacy/leaf", "url": "https://github.com/legacy/repo/blob/v1.0.0/skills/leaf/SKILL.md", "status": 404}],
        ),
        _raw_update(
            "garrytan/gbrain",
            "garrytan/gbrain",
            "v1.0.0",
            adds=["gb-new"],
            liveness=[{"skillId": "garrytan/gbrain-leaf", "url": "https://github.com/garrytan/gbrain/blob/v1.0.0/skills/gbrain-leaf/SKILL.md", "status": 404}],
        ),
        _raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"]),
    ]
    report, _, held_repos = _plan_batch(raw_gov, authority, gh=gh)
    assert "legacy/repo" in held_repos

    res = reduce_poll(
        empty_state(),
        poll_input_from_batch_report(
            "p-gov",
            MON_NOV_16,
            report,
            held_named_ids=frozenset({"garrytan/gbrain"}),
        ),
        authority,
    )
    assert res.status == "applied"
    assert res.write_authorized is False
    # Neither #1833 legacy repo nor frozen GBrain becomes eligible (even on Monday with 404!)
    assert res.decisions[("legacy/repo", "legacy/suite")].decision == DECISION_HELD_SCOPE
    assert res.decisions[("legacy/repo", "legacy/suite")].eligible is False
    assert res.decisions[("garrytan/gbrain", "garrytan/gbrain")].decision == DECISION_HELD_SCOPE
    assert res.decisions[("garrytan/gbrain", "garrytan/gbrain")].eligible is False
    # Unrelated repo still gets full coverage
    assert [(d.repository, d.named_id) for d in res.eligible] == [("other/repo", "carol/other-suite")]


# ---------------------------------------------------------------------------
# 12. Scoped complete-inventory seam: tracked adoption, verified absence, unknown fallback
# ---------------------------------------------------------------------------


def test_complete_inventory_seam_tracked_adoption_vs_verified_absence_and_subsequent_unknown():
    """Tests the isolated offline ScopedCompleteInventory seam (NOT qualified production
    producer integration):
    * Day 1: alice/suite-a observes alpha & beta; bob/suite-b observes alpha.
    * Day 2: alice/suite-a raw componentAdds is empty (alpha adopted into suiteComponents,
      beta removed upstream) + unit-injected verified complete inventory containing
      {'alpha', 'kept-leaf'} -> alpha is PRESENCE_PRESENT_TRACKED (distinct from raw
      new-candidate eligibility), beta is PRESENCE_VANISHED for alice/suite-a ONLY,
      while sibling bob/suite-b is untouched.
    * Day 3: ordinary P1 report (no complete inventory) -> both alpha and beta drop to
      PRESENCE_UNKNOWN with beta's earlier vanished_at/vanished_poll_id preserved intact
      and NO new vanished mark on alpha.
    """
    authority = _base_authority()

    day1_raw = [
        _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha", "beta"], component_root="packages/a/skills"),
        _raw_update("bob/suite-b", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/b/skills"),
    ]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    r1 = reduce_poll(empty_state(), poll_input_from_batch_report("p-inv-1", TUE_NOV_10, day1_report), authority)
    assert r1.status == "applied"
    open_day1 = _open_envelope_issue(day1_report, "acme/shared-repo", number=201, updated_at="2026-11-10T06:00:00Z")

    # Day 2: alpha adopted into suiteComponents (empty raw delta), beta truly removed upstream.
    authority_day2 = copy.deepcopy(authority)
    authority_day2["alice/suite-a"]["suiteComponents"].append("alice/alpha")
    authority_day2["alice/alpha"] = {"id": "alice/alpha"}

    day2_raw = [
        _raw_update(
            "alice/suite-a",
            "acme/shared-repo",
            "v1.1.0",
            previous_version="v1.0.0",
            adds=[],
            component_root="packages/a/skills",
        ),
    ]
    day2_report, day2_planned, _ = _plan_batch(day2_raw, authority_day2, gh=OfflineFakeGh(issues=[open_day1]))
    # Offline unit-injected ScopedCompleteInventory seam (NOT qualified production producer integration).
    inv_day2 = ScopedCompleteInventory(
        poll_id="p-inv-2",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        version="v1.1.0",
        source_url="https://github.com/acme/shared-repo/releases/tag/v1.1.0",
        component_root="packages/a/skills",
        present_slugs=frozenset({"alpha", "kept-leaf", "old-leaf"}),
        complete=True,
        truncated=False,
        root_verified=True,
    )
    poll_day2 = PollInput(
        poll_id="p-inv-2",
        observed_at=THU_NOV_12,
        observed_findings=day2_report["observedFindings"],
        planned_findings=day2_planned,
        complete=True,
        complete_inventories=(inv_day2,),
    )
    r2 = reduce_poll(r1.state, poll_day2, authority_day2)
    assert r2.status == "applied"
    bucket_a2 = r2.state.get_bucket("acme/shared-repo", "alice/suite-a")
    bucket_b2 = r2.state.get_bucket("acme/shared-repo", "bob/suite-b")
    assert bucket_a2 is not None and bucket_b2 is not None

    # alpha is proven present upstream as tracked, NOT a raw new-candidate!
    alpha2 = bucket_a2.rows["acme/shared-repo:alpha"]
    assert alpha2.presence == PRESENCE_PRESENT_TRACKED
    assert alpha2.present_in_latest is False
    assert alpha2.vanished_at is None
    assert alpha2.vanished_poll_id is None
    assert alpha2.first_seen_pin == FirstSeenPin(
        first_seen_version="v1.0.0",
        evidence_url="https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/alpha/SKILL.md",
        first_seen_at="2026-11-10T06:00:00Z",
        first_seen_poll_id="p-inv-1",
    )

    # beta is proven absent by verified full root inventory -> vanished for alice/suite-a ONLY.
    beta2 = bucket_a2.rows["acme/shared-repo:beta"]
    assert beta2.presence == PRESENCE_VANISHED
    assert beta2.present_in_latest is False
    assert beta2.vanished_at == "2026-11-12T06:00:00Z"
    assert beta2.vanished_poll_id == "p-inv-2"

    assert bucket_a2.present_row_ids == ()
    assert bucket_a2.tracked_present_row_ids == ("acme/shared-repo:alpha",)
    assert bucket_a2.upstream_present_row_ids == ("acme/shared-repo:alpha",)
    assert bucket_a2.vanished_row_ids == ("acme/shared-repo:beta",)
    assert bucket_a2.unknown_presence_row_ids == ()
    # Sibling bob/suite-b untouched.
    assert bucket_b2 == r1.state.get_bucket("acme/shared-repo", "bob/suite-b")

    # Day 3: ordinary P1 report adapter (no complete inventory) -> presence UNKNOWN,
    # earlier vanished timestamp on beta preserved intact, NO new vanished mark on alpha.
    r3 = reduce_poll(
        r2.state,
        poll_input_from_batch_report("p-inv-3", MON_NOV_16, day2_report),
        authority_day2,
    )
    assert r3.status == "applied"
    bucket_a3 = r3.state.get_bucket("acme/shared-repo", "alice/suite-a")
    assert bucket_a3 is not None
    assert bucket_a3.rows["acme/shared-repo:alpha"].presence == PRESENCE_UNKNOWN
    assert bucket_a3.rows["acme/shared-repo:alpha"].vanished_at is None
    assert bucket_a3.rows["acme/shared-repo:alpha"].vanished_poll_id is None
    assert bucket_a3.rows["acme/shared-repo:beta"].presence == PRESENCE_UNKNOWN
    assert bucket_a3.rows["acme/shared-repo:beta"].vanished_at == "2026-11-12T06:00:00Z"
    assert bucket_a3.rows["acme/shared-repo:beta"].vanished_poll_id == "p-inv-2"
    assert bucket_a3.present_row_ids == ()
    assert bucket_a3.vanished_row_ids == ()
    assert bucket_a3.unknown_presence_row_ids == ("acme/shared-repo:alpha", "acme/shared-repo:beta")


def test_complete_inventory_seam_rejected_for_non_component_bootstrap_missing_root_and_mismatched_metadata():
    """Nominal empty adds, version-only, bootstrap, missing-root fallback, incomplete/truncated
    metadata, and cross-scope/mismatched inventories must NEVER prove disappearance.
    """
    authority = _base_authority()
    day1_raw = [_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills")]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    r1 = reduce_poll(empty_state(), poll_input_from_batch_report("p-q-1", TUE_NOV_10, day1_report), authority)
    open_day1 = _open_envelope_issue(day1_report, "acme/shared-repo", number=202, updated_at="2026-11-10T06:00:00Z")

    # Helper to construct a valid baseline inventory for Day 2
    def _base_inv(**overrides: Any) -> ScopedCompleteInventory:
        params: dict[str, Any] = {
            "poll_id": "p-q-2",
            "repository": "acme/shared-repo",
            "named_id": "alice/suite-a",
            "version": "v1.1.0",
            "source_url": "https://github.com/acme/shared-repo/releases/tag/v1.1.0",
            "component_root": "packages/a/skills",
            "present_slugs": frozenset({"old-leaf", "kept-leaf"}),
            "complete": True,
            "truncated": False,
            "root_verified": True,
        }
        params.update(overrides)
        return ScopedCompleteInventory(**params)

    # 1. Non-component (version-only), bootstrap, and missing-root fallback observations
    non_qualifying_obs = [
        _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", adds=[], mode="version-only", component_root="packages/a/skills"),
        _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", adds=[], finding_type="bootstrap", component_root="packages/a/skills"),
        _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", adds=[], component_root=None),
    ]
    for idx, obs in enumerate(non_qualifying_obs):
        slugs, reason = qualify_complete_inventory(
            _base_inv(),
            poll_id="p-q-2",
            repository="acme/shared-repo",
            named_id="alice/suite-a",
            raw_obs=obs,
            authority=authority,
        )
        assert slugs is None and reason, (idx, slugs, reason)
        rep, planned, _ = _plan_batch([obs], authority, gh=OfflineFakeGh(issues=[open_day1]))
        res = reduce_poll(
            r1.state,
            PollInput(f"p-q-2", THU_NOV_12, rep["observedFindings"], planned, complete_inventories=(_base_inv(),)),
            authority,
        )
        assert res.status == "applied"
        bucket = res.state.get_bucket("acme/shared-repo", "alice/suite-a")
        assert bucket is not None
        assert bucket.rows["acme/shared-repo:alpha"].presence == PRESENCE_UNKNOWN
        assert bucket.rows["acme/shared-repo:alpha"].vanished_at is None
        assert bucket.vanished_row_ids == ()

    # 2. Component update with mismatched/incomplete/truncated/unverified/cross-scope inventory
    valid_comp_obs = _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", adds=[], component_root="packages/a/skills")
    baseline_slugs, baseline_reason = qualify_complete_inventory(
        _base_inv(),
        poll_id="p-q-2",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        raw_obs=valid_comp_obs,
        authority=authority,
    )
    assert baseline_slugs == frozenset({"old-leaf", "kept-leaf"}) and baseline_reason is None
    rep_comp, planned_comp, _ = _plan_batch([valid_comp_obs], authority, gh=OfflineFakeGh(issues=[open_day1]))
    bad_inventories = [
        _base_inv(poll_id="wrong-poll"),
        _base_inv(repository="other/repo"),
        _base_inv(named_id="bob/suite-b"),
        _base_inv(version="v1.0.0"),
        _base_inv(source_url="https://github.com/acme/shared-repo/releases/tag/v1.0.0"),
        _base_inv(component_root="packages/b/skills"),
        _base_inv(component_root="../escape"),
        _base_inv(complete=False),
        _base_inv(truncated=True),
        _base_inv(root_verified=False),
    ]
    for idx, bad_inv in enumerate(bad_inventories):
        slugs, reason = qualify_complete_inventory(
            bad_inv,
            poll_id="p-q-2",
            repository="acme/shared-repo",
            named_id="alice/suite-a",
            raw_obs=valid_comp_obs,
            authority=authority,
        )
        assert slugs is None and reason, (idx, bad_inv, reason)
        res = reduce_poll(
            r1.state,
            PollInput("p-q-2", THU_NOV_12, rep_comp["observedFindings"], planned_comp, complete_inventories=(bad_inv,)),
            authority,
        )
        assert res.status == "applied"
        bucket = res.state.get_bucket("acme/shared-repo", "alice/suite-a")
        assert bucket is not None
        assert bucket.rows["acme/shared-repo:alpha"].presence == PRESENCE_UNKNOWN
        assert bucket.rows["acme/shared-repo:alpha"].vanished_at is None
        assert bucket.vanished_row_ids == ()

    # 3. Inventory contradicting explicit raw diff or configured tracked-set evidence is unusable
    obs_with_add = _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", adds=["gamma"], component_root="packages/a/skills")
    slugs, reason = qualify_complete_inventory(
        _base_inv(present_slugs=frozenset({"old-leaf", "kept-leaf"})),
        poll_id="p-q-2",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        raw_obs=obs_with_add,
        authority=authority,
    )
    assert slugs is None and "omits slugs" in (reason or "")

    # Inventory includes a slug explicitly reported in raw componentRemoves
    obs_with_remove = _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", adds=[], removes=["old-leaf"], component_root="packages/a/skills")
    slugs, reason = qualify_complete_inventory(
        _base_inv(present_slugs=frozenset({"old-leaf", "kept-leaf"})),
        poll_id="p-q-2",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        raw_obs=obs_with_remove,
        authority=authority,
    )
    assert slugs is None and "componentRemoves" in (reason or "")

    # Inventory claims an untracked slug absent from raw componentAdds
    slugs, reason = qualify_complete_inventory(
        _base_inv(present_slugs=frozenset({"old-leaf", "kept-leaf", "untracked-ghost"})),
        poll_id="p-q-2",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        raw_obs=valid_comp_obs,
        authority=authority,
    )
    assert slugs is None and "untracked slugs" in (reason or "")

    # Inventory omits a tracked suiteComponent absent from raw componentRemoves
    slugs, reason = qualify_complete_inventory(
        _base_inv(present_slugs=frozenset({"kept-leaf"})),
        poll_id="p-q-2",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        raw_obs=valid_comp_obs,
        authority=authority,
    )
    assert slugs is None and "tracked suiteComponents" in (reason or "")

    # Raw componentAdds overlaps configured suiteComponents
    obs_add_overlaps_tracked = _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", adds=["kept-leaf"], component_root="packages/a/skills")
    slugs, reason = qualify_complete_inventory(
        _base_inv(present_slugs=frozenset({"old-leaf", "kept-leaf"})),
        poll_id="p-q-2",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        raw_obs=obs_add_overlaps_tracked,
        authority=authority,
    )
    assert slugs is None and "overlaps configured suiteComponents" in (reason or "")


def test_complete_inventory_rejects_agreeing_raw_and_inventory_on_wrong_sibling_root_and_accepts_configured_and_default_roots():
    """Authoritative component root is derived strictly from authority[named_id]
    (configured upstreamComponentRoot, or documented 'skills' default only when unconfigured).
    * Discriminating test: raw_obs and inventory BOTH agree on sibling bob/suite-b's root
      ('packages/b/skills') for alice/suite-a (configured 'packages/a/skills') -> rejected,
      no applicable proof, no new vanished mark.
    * Configured root positive: both match 'packages/a/skills' -> accepted and proves absence.
    * Unconfigured default positive & mismatch: carol/other-suite has no upstreamComponentRoot
      in authority -> defaults to 'skills'; agreeing on 'packages/other/skills' is rejected,
      while agreeing on 'skills' is accepted.
    * Malformed configured upstreamComponentRoot or empty suiteComponents in authority -> rejected.
    """
    authority = _base_authority()

    # Seed alice/suite-a (configured root: packages/a/skills) and carol/other-suite (default root: skills)
    day1_raw = [
        _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills"),
        _raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"], component_root="skills"),
    ]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    r1 = reduce_poll(empty_state(), poll_input_from_batch_report("p-root-1", TUE_NOV_10, day1_report), authority)
    assert r1.status == "applied"
    open_acme = _open_envelope_issue(day1_report, "acme/shared-repo", number=204, updated_at="2026-11-10T06:00:00Z")
    open_other = _open_envelope_issue(day1_report, "other/repo", number=205, updated_at="2026-11-10T06:00:00Z")

    # 1. Discriminating sibling-root attack: raw AND inventory BOTH say sibling 'packages/b/skills' for alice/suite-a
    wrong_root_obs = _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", previous_version="v1.0.0", adds=[], component_root="packages/b/skills")
    wrong_root_inv = ScopedCompleteInventory(
        poll_id="p-root-wrong-sibling",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        version="v1.1.0",
        source_url="https://github.com/acme/shared-repo/releases/tag/v1.1.0",
        component_root="packages/b/skills",
        present_slugs=frozenset({"old-leaf", "kept-leaf"}),
        complete=True,
        truncated=False,
        root_verified=True,
    )
    slugs, reason = qualify_complete_inventory(
        wrong_root_inv,
        poll_id="p-root-wrong-sibling",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        raw_obs=wrong_root_obs,
        authority=authority,
    )
    assert slugs is None and "disagrees with registry authority" in (reason or "")

    rep_wrong, planned_wrong, _ = _plan_batch([wrong_root_obs], authority, gh=OfflineFakeGh(issues=[open_acme]))
    res_wrong = reduce_poll(
        r1.state,
        PollInput("p-root-wrong-sibling", THU_NOV_12, rep_wrong["observedFindings"], planned_wrong, complete_inventories=(wrong_root_inv,)),
        authority,
    )
    assert res_wrong.status == "applied"
    bucket_a_wrong = res_wrong.state.get_bucket("acme/shared-repo", "alice/suite-a")
    assert bucket_a_wrong is not None
    assert bucket_a_wrong.rows["acme/shared-repo:alpha"].presence == PRESENCE_UNKNOWN
    assert bucket_a_wrong.rows["acme/shared-repo:alpha"].vanished_at is None
    assert bucket_a_wrong.rows["acme/shared-repo:alpha"].vanished_poll_id is None
    assert bucket_a_wrong.vanished_row_ids == ()

    # 2. Configured root positive: raw AND inventory match authority['alice/suite-a']['upstreamComponentRoot']
    right_root_obs = _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", previous_version="v1.0.0", adds=[], component_root="packages/a/skills")
    right_root_inv = ScopedCompleteInventory(
        poll_id="p-root-right-configured",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        version="v1.1.0",
        source_url="https://github.com/acme/shared-repo/releases/tag/v1.1.0",
        component_root="packages/a/skills",
        present_slugs=frozenset({"old-leaf", "kept-leaf"}),
        complete=True,
        truncated=False,
        root_verified=True,
    )
    rep_right, planned_right, _ = _plan_batch([right_root_obs], authority, gh=OfflineFakeGh(issues=[open_acme]))
    res_right = reduce_poll(
        r1.state,
        PollInput("p-root-right-configured", THU_NOV_12, rep_right["observedFindings"], planned_right, complete_inventories=(right_root_inv,)),
        authority,
    )
    assert res_right.status == "applied"
    bucket_a_right = res_right.state.get_bucket("acme/shared-repo", "alice/suite-a")
    assert bucket_a_right is not None
    assert bucket_a_right.rows["acme/shared-repo:alpha"].presence == PRESENCE_VANISHED
    assert bucket_a_right.vanished_row_ids == ("acme/shared-repo:alpha",)

    # 3. Unconfigured documented 'skills' default: carol/other-suite has no upstreamComponentRoot in authority
    assert "upstreamComponentRoot" not in authority["carol/other-suite"]
    carol_wrong_obs = _raw_update("carol/other-suite", "other/repo", "v1.1.0", previous_version="v1.0.0", adds=[], component_root="packages/custom/skills")
    carol_wrong_inv = ScopedCompleteInventory(
        poll_id="p-root-carol-wrong",
        repository="other/repo",
        named_id="carol/other-suite",
        version="v1.1.0",
        source_url="https://github.com/other/repo/releases/tag/v1.1.0",
        component_root="packages/custom/skills",
        present_slugs=frozenset({"leaf-one"}),
        complete=True,
        truncated=False,
        root_verified=True,
    )
    rep_cw, planned_cw, _ = _plan_batch([carol_wrong_obs], authority, gh=OfflineFakeGh(issues=[open_other]))
    res_cw = reduce_poll(
        r1.state,
        PollInput("p-root-carol-wrong", THU_NOV_12, rep_cw["observedFindings"], planned_cw, complete_inventories=(carol_wrong_inv,)),
        authority,
    )
    assert res_cw.status == "applied"
    assert res_cw.state.get_bucket("other/repo", "carol/other-suite").rows["other/repo:gamma"].presence == PRESENCE_UNKNOWN
    assert res_cw.state.get_bucket("other/repo", "carol/other-suite").vanished_row_ids == ()

    carol_default_obs = _raw_update("carol/other-suite", "other/repo", "v1.1.0", previous_version="v1.0.0", adds=[], component_root="skills")
    carol_default_inv = ScopedCompleteInventory(
        poll_id="p-root-carol-default",
        repository="other/repo",
        named_id="carol/other-suite",
        version="v1.1.0",
        source_url="https://github.com/other/repo/releases/tag/v1.1.0",
        component_root="skills",
        present_slugs=frozenset({"leaf-one"}),
        complete=True,
        truncated=False,
        root_verified=True,
    )
    rep_cd, planned_cd, _ = _plan_batch([carol_default_obs], authority, gh=OfflineFakeGh(issues=[open_other]))
    res_cd = reduce_poll(
        r1.state,
        PollInput("p-root-carol-default", THU_NOV_12, rep_cd["observedFindings"], planned_cd, complete_inventories=(carol_default_inv,)),
        authority,
    )
    assert res_cd.status == "applied"
    assert res_cd.state.get_bucket("other/repo", "carol/other-suite").rows["other/repo:gamma"].presence == PRESENCE_VANISHED
    assert res_cd.state.get_bucket("other/repo", "carol/other-suite").vanished_row_ids == ("other/repo:gamma",)

    # 4. Malformed configured upstreamComponentRoot or empty suiteComponents in authority never defaults to 'skills'
    for bad_root in ("", " ", "/skills", "skills/", "../escape", "a//b", 123, True):
        bad_auth = copy.deepcopy(authority)
        bad_auth["carol/other-suite"]["upstreamComponentRoot"] = bad_root
        slugs, reason = qualify_complete_inventory(
            carol_default_inv,
            poll_id="p-root-carol-default",
            repository="other/repo",
            named_id="carol/other-suite",
            raw_obs=carol_default_obs,
            authority=bad_auth,
        )
        assert slugs is None and "malformed upstreamComponentRoot" in (reason or ""), (bad_root, slugs, reason)

    empty_comp_auth = copy.deepcopy(authority)
    empty_comp_auth["carol/other-suite"]["suiteComponents"] = []
    slugs, reason = qualify_complete_inventory(
        carol_default_inv,
        poll_id="p-root-carol-default",
        repository="other/repo",
        named_id="carol/other-suite",
        raw_obs=carol_default_obs,
        authority=empty_comp_auth,
    )
    assert slugs is None and "no configured suiteComponents" in (reason or "")


def test_complete_inventory_omitted_or_non_bool_availability_fields_cannot_prove_absence():
    """All three availability fields (complete, truncated, root_verified) default to
    conservative unusable values and accept strict bools only; omitting any one or all
    three, or passing truthy/falsy non-booleans, must never prove absence.
    """
    authority = _base_authority()
    day1_raw = [_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills")]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    r1 = reduce_poll(empty_state(), poll_input_from_batch_report("p-avail-1", TUE_NOV_10, day1_report), authority)
    open_day1 = _open_envelope_issue(day1_report, "acme/shared-repo", number=206, updated_at="2026-11-10T06:00:00Z")

    day2_obs = _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", previous_version="v1.0.0", adds=[], component_root="packages/a/skills")
    day2_report, day2_planned, _ = _plan_batch([day2_obs], authority, gh=OfflineFakeGh(issues=[open_day1]))

    common: dict[str, Any] = {
        "poll_id": "p-avail-2",
        "repository": "acme/shared-repo",
        "named_id": "alice/suite-a",
        "version": "v1.1.0",
        "source_url": "https://github.com/acme/shared-repo/releases/tag/v1.1.0",
        "component_root": "packages/a/skills",
        "present_slugs": frozenset({"old-leaf", "kept-leaf"}),
    }

    # Verify defaults themselves are conservative unusable values
    omitted_all = ScopedCompleteInventory(**common)
    assert omitted_all.complete is False
    assert omitted_all.truncated is True
    assert omitted_all.root_verified is False

    unusable_cases = [
        ("omit-all", omitted_all),
        ("omit-complete", ScopedCompleteInventory(**common, truncated=False, root_verified=True)),
        ("omit-truncated", ScopedCompleteInventory(**common, complete=True, root_verified=True)),
        ("omit-root-verified", ScopedCompleteInventory(**common, complete=True, truncated=False)),
        ("non-bool-complete-int", ScopedCompleteInventory(**common, complete=1, truncated=False, root_verified=True)),      # type: ignore[arg-type]
        ("non-bool-complete-str", ScopedCompleteInventory(**common, complete="true", truncated=False, root_verified=True)), # type: ignore[arg-type]
        ("non-bool-truncated-int", ScopedCompleteInventory(**common, complete=True, truncated=0, root_verified=True)),      # type: ignore[arg-type]
        ("non-bool-truncated-none", ScopedCompleteInventory(**common, complete=True, truncated=None, root_verified=True)),  # type: ignore[arg-type]
        ("non-bool-root-verified-int", ScopedCompleteInventory(**common, complete=True, truncated=False, root_verified=1)), # type: ignore[arg-type]
        ("non-bool-root-verified-str", ScopedCompleteInventory(**common, complete=True, truncated=False, root_verified="yes")), # type: ignore[arg-type]
    ]
    for label, inv in unusable_cases:
        slugs, reason = qualify_complete_inventory(
            inv,
            poll_id="p-avail-2",
            repository="acme/shared-repo",
            named_id="alice/suite-a",
            raw_obs=day2_obs,
            authority=authority,
        )
        assert slugs is None and reason, (label, slugs, reason)
        res = reduce_poll(
            r1.state,
            PollInput("p-avail-2", THU_NOV_12, day2_report["observedFindings"], day2_planned, complete_inventories=(inv,)),
            authority,
        )
        assert res.status == "applied", label
        bucket = res.state.get_bucket("acme/shared-repo", "alice/suite-a")
        assert bucket is not None
        assert bucket.rows["acme/shared-repo:alpha"].presence == PRESENCE_UNKNOWN, label
        assert bucket.rows["acme/shared-repo:alpha"].vanished_at is None, label
        assert bucket.vanished_row_ids == (), label


def test_historical_only_row_with_tracked_complete_inventory_preserves_pin_without_fabricating_first_observation():
    authority = _base_authority()
    day1_raw = [_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha", "beta"], component_root="packages/a/skills")]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    open_day1 = _open_envelope_issue(day1_report, "acme/shared-repo", number=203)

    # Day 2: beta is adopted into suiteComponents while alpha remains an active raw candidate add.
    authority_day2 = copy.deepcopy(authority)
    authority_day2["alice/suite-a"]["suiteComponents"].append("alice/beta")
    authority_day2["alice/beta"] = {"id": "alice/beta"}

    day2_raw = [_raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", previous_version="v1.0.0", adds=["alpha"], component_root="packages/a/skills")]
    day2_report, day2_planned, _ = _plan_batch(day2_raw, authority_day2, gh=OfflineFakeGh(issues=[open_day1]))
    inv = ScopedCompleteInventory(
        poll_id="p-hist-inv",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        version="v1.1.0",
        source_url="https://github.com/acme/shared-repo/releases/tag/v1.1.0",
        component_root="packages/a/skills",
        present_slugs=frozenset({"alpha", "beta", "kept-leaf", "old-leaf"}),
        complete=True,
        truncated=False,
        root_verified=True,
    )
    res = reduce_poll(
        empty_state(),
        PollInput("p-hist-inv", THU_NOV_12, day2_report["observedFindings"], day2_planned, complete_inventories=(inv,)),
        authority_day2,
    )
    assert res.status == "applied"
    bucket = res.state.get_bucket("acme/shared-repo", "alice/suite-a")
    assert bucket is not None
    beta = bucket.rows["acme/shared-repo:beta"]
    assert beta.historical_only is True
    assert beta.presence == PRESENCE_PRESENT_TRACKED
    assert beta.present_in_latest is False
    assert beta.first_seen_pin.first_seen_version == "v1.0.0"
    assert beta.first_seen_pin.first_seen_at is None
    assert beta.first_seen_pin.first_seen_poll_id is None
    assert beta.last_seen_at is None
    assert bucket.tracked_present_row_ids == ("acme/shared-repo:beta",)


# ---------------------------------------------------------------------------
# 13. Strict batch-report adapter validation (Finding 2)
# ---------------------------------------------------------------------------


def test_batch_report_adapter_standard_path_and_strict_malformed_rejections():
    authority = _base_authority()
    raw = [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])]
    report, _, _ = _plan_batch(raw, authority)

    # Exact accepted-report standard path succeeds
    poll = poll_input_from_batch_report("p-std", MON_NOV_16, report)
    assert poll.complete is True
    res = reduce_poll(empty_state(), poll, authority)
    assert res.status == "applied"
    assert len(res.eligible) == 1

    # Non-empty unknownEvidence -> complete=False -> reducer rejects fail-closed
    report_with_unknown = copy.deepcopy(report)
    report_with_unknown["unknownEvidence"] = [{"source": "repository-plan", "detail": "err", "stopped": True}]
    poll_inc = poll_input_from_batch_report("p-inc-rep", MON_NOV_16, report_with_unknown)
    assert poll_inc.complete is False
    res_inc = reduce_poll(empty_state(), poll_inc, authority)
    assert res_inc.status == "rejected"

    # Missing or wrong-shaped unknownEvidence -> PayloadError (never healthy!)
    report_no_unknown = copy.deepcopy(report)
    del report_no_unknown["unknownEvidence"]
    for bad_report in (
        report_no_unknown,
        {**report, "unknownEvidence": None},
        {**report, "unknownEvidence": ""},
        {**report, "unknownEvidence": {}},
        {**report, "knownLegacyHolds": "not-a-list"},
        {**report, "unavailable": "not-a-list"},
        {**report, "unavailableNamedIds": {}},
        {**report, "repositories": [{"repository": "other/repo", "knownLegacyHolds": "bad", "payload": None}]},
        {**report, "repositories": [{"repository": None, "knownLegacyHolds": [{"payloadSha256": "x"}], "payload": None}]},
    ):
        with pytest.raises(PayloadError):
            poll_input_from_batch_report("p-bad-rep", MON_NOV_16, bad_report)

    # Non-bool complete (e.g. complete="false") -> PayloadError
    for bad_complete in ("false", "true", 1, 0, None):
        with pytest.raises(PayloadError):
            poll_input_from_batch_report("p-bad-bool", MON_NOV_16, report, complete=bad_complete)  # type: ignore[arg-type]

    # Malformed hold / unavailable containers -> PayloadError (never TypeError!)
    with pytest.raises(PayloadError):
        poll_input_from_batch_report("p-bad-h1", MON_NOV_16, report, held_repos=None)  # type: ignore[arg-type]
    with pytest.raises(PayloadError):
        poll_input_from_batch_report("p-bad-h2", MON_NOV_16, report, held_repos=["not a repo"])
    with pytest.raises(PayloadError):
        poll_input_from_batch_report("p-bad-h3", MON_NOV_16, report, held_named_ids=None)  # type: ignore[arg-type]
    with pytest.raises(PayloadError):
        poll_input_from_batch_report("p-bad-h4", MON_NOV_16, report, held_named_ids="alice/suite-a")  # type: ignore[arg-type]
    with pytest.raises(PayloadError):
        poll_input_from_batch_report("p-bad-u1", MON_NOV_16, report, unavailable_named_ids=123)  # type: ignore[arg-type]
    with pytest.raises(PayloadError):
        poll_input_from_batch_report("p-bad-u2", MON_NOV_16, report, unavailable_named_ids=["bad id"])


# ---------------------------------------------------------------------------
# 14. Historical-only -> current transition records real first observation (Finding 3)
# ---------------------------------------------------------------------------


def test_historical_only_row_transitions_to_current_preserving_canonical_pin_and_recording_first_observation():
    authority = _base_authority()
    day1_raw = [_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha", "beta"], component_root="packages/a/skills")]
    day1_report, _, _ = _plan_batch(day1_raw, authority)
    open_day1 = _open_envelope_issue(day1_report, "acme/shared-repo", number=210, updated_at="2026-11-10T06:00:00Z")

    # Fresh reducer starts on Day 2 where beta is retained-only in canonical candidates
    day2_raw = [_raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", previous_version="v1.0.0", adds=["alpha"], component_root="packages/a/skills")]
    day2_report, _, _ = _plan_batch(day2_raw, authority, gh=OfflineFakeGh(issues=[open_day1]))
    r2 = reduce_poll(empty_state(), poll_input_from_batch_report("p-h2c-day2", THU_NOV_12, day2_report), authority)
    assert r2.status == "applied"
    beta2 = r2.state.get_bucket("acme/shared-repo", "alice/suite-a").rows["acme/shared-repo:beta"]
    assert beta2.historical_only is True
    assert beta2.first_seen_pin == FirstSeenPin(
        first_seen_version="v1.0.0",
        evidence_url="https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/beta/SKILL.md",
        first_seen_at=None,
        first_seen_poll_id=None,
    )

    # Day 3: beta is positively observed in raw componentAdds against Day 2 open envelope (no pin conflict!)
    open_day2 = _open_envelope_issue(day2_report, "acme/shared-repo", number=210, updated_at="2026-11-12T06:00:00Z")
    day3_raw = [_raw_update("alice/suite-a", "acme/shared-repo", "v1.2.0", previous_version="v1.1.0", adds=["alpha", "beta"], component_root="packages/a/skills")]
    day3_report, _, _ = _plan_batch(day3_raw, authority, gh=OfflineFakeGh(issues=[open_day2]))
    r3 = reduce_poll(r2.state, poll_input_from_batch_report("p-h2c-day3", MON_NOV_16, day3_report), authority)
    assert r3.status == "applied"
    assert r3.rejected_observations == ()
    beta3 = r3.state.get_bucket("acme/shared-repo", "alice/suite-a").rows["acme/shared-repo:beta"]
    assert beta3.historical_only is False
    assert beta3.present_in_latest is True
    assert beta3.presence == PRESENCE_PRESENT_CANDIDATE
    assert beta3.first_seen_pin == FirstSeenPin(
        first_seen_version="v1.0.0",
        evidence_url="https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/beta/SKILL.md",
        first_seen_at="2026-11-16T06:00:00Z",
        first_seen_poll_id="p-h2c-day3",
    )
    assert beta3.last_seen_at == "2026-11-16T06:00:00Z"
    assert beta3.last_seen_poll_id == "p-h2c-day3"

    # Day 4: subsequent sighting keeps Day 3 first_seen_at/first_seen_poll_id immutable
    r4 = reduce_poll(r3.state, poll_input_from_batch_report("p-h2c-day4", TUE_NOV_17, day3_report), authority)
    assert r4.status == "applied"
    beta4 = r4.state.get_bucket("acme/shared-repo", "alice/suite-a").rows["acme/shared-repo:beta"]
    assert beta4.first_seen_pin == beta3.first_seen_pin
    assert beta4.last_seen_at == "2026-11-17T06:00:00Z"
    assert beta4.last_seen_poll_id == "p-h2c-day4"


# ---------------------------------------------------------------------------
# 15. Fractional UTC precision through digest, storage, replay, and ordering (Finding 4)
# ---------------------------------------------------------------------------


def test_fractional_utc_precision_preserved_for_replay_conflict_and_subsecond_ordering():
    authority = _base_authority()
    raw = [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])]
    report, _, _ = _plan_batch(raw, authority)

    t_mid = "2026-11-10T06:00:00.500000Z"
    t_mid_equiv = "2026-11-10T06:00:00.5Z"
    t_earlier_same_sec = "2026-11-10T06:00:00.250000Z"
    t_conflict_same_sec = "2026-11-10T06:00:00.500001Z"
    t_later_same_sec = "2026-11-10T06:00:00.750000Z"

    r1 = reduce_poll(empty_state(), poll_input_from_batch_report("p-frac-1", t_mid, report), authority)
    assert r1.status == "applied"
    assert r1.observed_at == t_mid
    assert r1.state.last_observed_at == t_mid
    assert r1.state.get_bucket("other/repo", "carol/other-suite").last_observed_at == t_mid

    # Exact replay with equivalent fractional representation -> replayed, NOT a last-seen update
    r_rep = reduce_poll(r1.state, poll_input_from_batch_report("p-frac-1", t_mid_equiv, report), authority)
    assert r_rep.status == "replayed"
    assert r_rep.replayed is True
    assert r_rep.state == r1.state
    assert r_rep.state.get_bucket("other/repo", "carol/other-suite").sighting_count == 1
    assert r_rep.state.get_bucket("other/repo", "carol/other-suite").last_observed_at == t_mid

    # Same poll_id with different sub-second timestamp -> conflicting poll_id rejection
    r_conf = reduce_poll(r1.state, poll_input_from_batch_report("p-frac-1", t_conflict_same_sec, report), authority)
    assert r_conf.status == "rejected"
    assert "conflicting poll_id" in (r_conf.rejection_reason or "")
    assert r_conf.state == r1.state

    # New poll_id earlier within the same second -> stale observed_at rejection
    r_stale = reduce_poll(r1.state, poll_input_from_batch_report("p-frac-early", t_earlier_same_sec, report), authority)
    assert r_stale.status == "rejected"
    assert "stale observed_at" in (r_stale.rejection_reason or "")
    assert r_stale.state == r1.state

    # New poll_id later within the same second -> accepted and stored at full precision
    r_next = reduce_poll(r1.state, poll_input_from_batch_report("p-frac-2", t_later_same_sec, report), authority)
    assert r_next.status == "applied"
    assert r_next.observed_at == t_later_same_sec
    assert r_next.state.last_observed_at == t_later_same_sec
    assert r_next.state.get_bucket("other/repo", "carol/other-suite").last_observed_at == t_later_same_sec

    # Sub-microsecond (>6 fractional digits) rejected explicitly
    r_nano = reduce_poll(r_next.state, poll_input_from_batch_report("p-frac-nano", "2026-11-10T06:00:01.1234567Z", report), authority)
    assert r_nano.status == "rejected"
    assert "microsecond precision" in (r_nano.rejection_reason or "")


def test_strict_rfc3339_utc_grammar_rejects_comma_fractional_offsets_and_preserves_aware_datetime_ordering():
    """Explicit RFC3339 grammar rejects comma fractions, >6 fractional digits,
    fractional offsets, arbitrary separators, and naive/non-datetime inputs while
    keeping equivalent RFC3339 representations and aware datetimes with preserved
    microseconds working cleanly for replay, conflict, and ordering.
    """
    authority = _base_authority()
    raw = [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])]
    report, _, _ = _plan_batch(raw, authority)

    t_base = "2026-11-10T06:00:00.123456Z"
    r1 = reduce_poll(empty_state(), poll_input_from_batch_report("p-rfc-1", t_base, report), authority)
    assert r1.status == "applied"
    assert r1.observed_at == t_base

    # Equivalent RFC3339 representations (lowercase t/z, numeric offset, aware datetime) replay identically
    for equiv_ts in (
        "2026-11-10t06:00:00.123456z",
        "2026-11-10T06:00:00.123456+00:00",
        "2026-11-10T08:00:00.123456+02:00",
        "2026-11-10T01:30:00.123456-04:30",
        dt.datetime(2026, 11, 10, 8, 0, 0, 123456, tzinfo=dt.timezone(dt.timedelta(hours=2))),
    ):
        r_rep = reduce_poll(r1.state, poll_input_from_batch_report("p-rfc-1", equiv_ts, report), authority)
        assert r_rep.status == "replayed", equiv_ts
        assert r_rep.replayed is True
        assert r_rep.state == r1.state

    # Distinct legal microsecond via aware datetime under same poll_id -> conflict rejection
    r_dt_conf = reduce_poll(
        r1.state,
        poll_input_from_batch_report(
            "p-rfc-1",
            dt.datetime(2026, 11, 10, 8, 0, 0, 123457, tzinfo=dt.timezone(dt.timedelta(hours=2))),
            report,
        ),
        authority,
    )
    assert r_dt_conf.status == "rejected"
    assert "conflicting poll_id" in (r_dt_conf.rejection_reason or "")
    assert r_dt_conf.state == r1.state

    # Earlier distinct legal microsecond via offset string -> stale rejection (never collapsed)
    r_off_stale = reduce_poll(
        r1.state,
        poll_input_from_batch_report("p-rfc-early", "2026-11-10T08:00:00.123455+02:00", report),
        authority,
    )
    assert r_off_stale.status == "rejected"
    assert "stale observed_at" in (r_off_stale.rejection_reason or "")
    assert r_off_stale.state == r1.state

    # Later distinct legal microsecond via offset string -> applied at exact UTC microsecond
    r2 = reduce_poll(
        r1.state,
        poll_input_from_batch_report("p-rfc-2", "2026-11-10T08:00:00.123457+02:00", report),
        authority,
    )
    assert r2.status == "applied"
    assert r2.observed_at == "2026-11-10T06:00:00.123457Z"
    assert r2.state.last_observed_at == "2026-11-10T06:00:00.123457Z"

    # Unsupported / overprecise / comma / fractional-offset / arbitrary-separator / naive inputs
    invalid_timestamps: list[Any] = [
        "2026-11-10T06:00:00,5Z",
        "2026-11-10T06:00:00,123456Z",
        "2026-11-10T06:00:00,1234567Z",
        "2026-11-10T06:00:00,1234568Z",
        "2026-11-10T06:00:00.1234567Z",
        "2026-11-10T06:00:00+02:00:00",
        "2026-11-10T06:00:00+02:00:00.5",
        "2026-11-10T06:00:00+02:00:00,5",
        "2026-11-10 06:00:00Z",
        "2026-11-10_06:00:00Z",
        "20261110T060000Z",
        "2026-11-10T06:00Z",
        "2026-11-10T06:00:00",
        "2026-11-10T06:00:00+0200",
        "2026-11-10T06:00:00+02",
        "2026-11-10T06:00:00+24:00",
        "2026-11-10T06:00:00+00:60",
        "2026-11-10T06:00:00.Z",
        " 2026-11-10T06:00:00Z ",
        "2026-02-30T06:00:00Z",
        dt.datetime(2026, 11, 10, 6, 0, 0, 123456),  # naive datetime
        dt.date(2026, 11, 10),                       # date, not datetime
    ]
    for bad_ts in invalid_timestamps:
        with pytest.raises(ValueError):
            parse_strict_utc(bad_ts)
        r_bad = reduce_poll(r2.state, poll_input_from_batch_report("p-rfc-1", bad_ts, report), authority)
        assert r_bad.status == "rejected", bad_ts
        assert r_bad.replayed is False, bad_ts
        assert r_bad.state == r2.state, bad_ts


# ---------------------------------------------------------------------------
# 16. Explicit aggregate bounded resource contract (Finding 5)
# ---------------------------------------------------------------------------


def test_aggregate_resource_budgets_fail_closed_and_allow_exact_replay_at_capacity():
    authority = _base_authority()

    # 1. max_buckets=1 fails closed on a second bucket without mutating prior state
    cfg_buckets = ReducerConfig(max_buckets=1)
    rep_a, _, _ = _plan_batch([_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills")], authority)
    rep_c, _, _ = _plan_batch([_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])], authority)
    rb1 = reduce_poll(empty_state(), poll_input_from_batch_report("p-b1", TUE_NOV_10, rep_a), authority, cfg_buckets)
    assert rb1.status == "applied"
    rb2 = reduce_poll(rb1.state, poll_input_from_batch_report("p-b2", WED_NOV_11, rep_c), authority, cfg_buckets)
    assert rb2.status == "rejected"
    assert "buckets limit" in (rb2.rejection_reason or "")
    assert rb2.state == rb1.state

    # 2. max_rows_per_bucket=1 & max_total_rows=2 fail closed before committing oversized state
    cfg_rows = ReducerConfig(max_rows_per_bucket=1, max_total_rows=2)
    rep_two_rows, _, _ = _plan_batch([_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha", "beta"], component_root="packages/a/skills")], authority)
    rr = reduce_poll(empty_state(), poll_input_from_batch_report("p-r1", TUE_NOV_10, rep_two_rows), authority, cfg_rows)
    assert rr.status == "rejected"
    assert "rows_per_bucket limit" in (rr.rejection_reason or "")
    assert rr.state == empty_state()

    cfg_total_rows = ReducerConfig(max_rows_per_bucket=2, max_total_rows=2)
    rt1 = reduce_poll(empty_state(), poll_input_from_batch_report("p-tr1", TUE_NOV_10, rep_two_rows), authority, cfg_total_rows)
    assert rt1.status == "applied"
    rt2 = reduce_poll(rt1.state, poll_input_from_batch_report("p-tr2", WED_NOV_11, rep_c), authority, cfg_total_rows)
    assert rt2.status == "rejected"
    assert "total_rows limit" in (rt2.rejection_reason or "")
    assert rt2.state == rt1.state

    # 3. max_versions_per_bucket=1 fails closed when a second distinct version arrives
    cfg_versions = ReducerConfig(max_versions_per_bucket=1)
    rv1 = reduce_poll(empty_state(), poll_input_from_batch_report("p-v1", TUE_NOV_10, rep_a), authority, cfg_versions)
    assert rv1.status == "applied"
    open_a = _open_envelope_issue(rep_a, "acme/shared-repo", number=220)
    rep_a_v2, _, _ = _plan_batch(
        [_raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", previous_version="v1.0.0", adds=["alpha"], component_root="packages/a/skills")],
        authority,
        gh=OfflineFakeGh(issues=[open_a]),
    )
    rv2 = reduce_poll(rv1.state, poll_input_from_batch_report("p-v2", WED_NOV_11, rep_a_v2), authority, cfg_versions)
    assert rv2.status == "rejected"
    assert "versions_per_bucket limit" in (rv2.rejection_reason or "")
    assert rv2.state == rv1.state

    # 4. max_seen_polls=2 allows exact replay at capacity while rejecting a 3rd distinct poll_id
    cfg_polls = ReducerConfig(max_seen_polls=2)
    poll_1 = poll_input_from_batch_report("p-cap-1", TUE_NOV_10, rep_c)
    poll_2 = poll_input_from_batch_report("p-cap-2", WED_NOV_11, rep_c)
    poll_3 = poll_input_from_batch_report("p-cap-3", THU_NOV_12, rep_c)
    rp1 = reduce_poll(empty_state(), poll_1, authority, cfg_polls)
    rp2 = reduce_poll(rp1.state, poll_2, authority, cfg_polls)
    assert rp1.status == "applied" and rp2.status == "applied"
    assert len(rp2.state.seen_polls) == 2

    # Legitimate exact replay at capacity MUST succeed
    rp_replay = reduce_poll(rp2.state, poll_2, authority, cfg_polls)
    assert rp_replay.status == "replayed"
    assert rp_replay.replayed is True
    assert rp_replay.state == rp2.state

    # New distinct poll_id at capacity MUST fail closed without dropping receipts
    rp3 = reduce_poll(rp2.state, poll_3, authority, cfg_polls)
    assert rp3.status == "rejected"
    assert "seen_polls limit" in (rp3.rejection_reason or "")
    assert rp3.state == rp2.state
    assert len(rp3.state.seen_polls) == 2
