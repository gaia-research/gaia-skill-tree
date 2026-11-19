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
from scripts.upstream_watcher.weekly_reducer import (
    DECISION_ABSENT,
    DECISION_FLUSH,
    DECISION_HELD_SCOPE,
    DECISION_HOLD,
    DECISION_REJECTED,
    DECISION_REPLAYED,
    DECISION_UNAVAILABLE,
    DECISION_URGENT,
    FirstSeenPin,
    PollInput,
    ReducerConfig,
    empty_state,
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
            "suiteComponents": ["alice/old-leaf", "alice/kept-leaf"],
        },
        "alice/old-leaf": {"id": "alice/old-leaf"},
        "alice/kept-leaf": {"id": "alice/kept-leaf"},
        "bob/suite-b": {
            "id": "bob/suite-b",
            "links": {"github": "https://github.com/acme/shared-repo"},
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


def _plan_named_findings(
    raw_findings: list[dict[str, Any]],
    authority: dict[str, dict[str, Any]],
    gh: OfflineFakeGh | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], frozenset[str]]:
    """Run the REAL P1 canonical planner (plan_only=True, apply=False) and return validated named findings."""
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
    name_drift: list[dict[str, Any]] | None = None,
    component_root: str = "skills",
) -> dict[str, Any]:
    return {
        "finding_type": "update",
        "skillId": skill_id,
        "currentVersion": previous_version,
        "newVersion": version,
        "releasedAt": released_at,
        "sourceUrl": f"https://github.com/{repo}/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds or []),
        "componentRemoves": list(removes or []),
        "linkLiveness": list(liveness or []),
        "nameDrift": list(name_drift or []),
        "upstreamComponentRoot": component_root,
    }


# ---------------------------------------------------------------------------
# 1. Discriminating real P1 planner fixture: canonical removal + same-repo siblings
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

    _report, planned_findings, held_repos = _plan_named_findings(raw_findings, authority)
    assert held_repos == frozenset()
    assert len(planned_findings) == 2

    by_id = {f["skillId"]: f for f in planned_findings}
    assert by_id["alice/suite-a"]["componentRemoves"] == ["alice/old-leaf"]

    res = reduce_poll(
        empty_state(),
        PollInput(poll_id="poll-2026-11-10", observed_at=TUE_NOV_10, findings=planned_findings),
        authority,
    )

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
# 2. Vanished history vs absent sibling & immutable FirstSeenPin
# ---------------------------------------------------------------------------


def test_vanished_rows_preserved_only_for_verified_bucket_and_absent_sibling_stays_ineligible():
    authority = _base_authority()

    # Day 1 (Tue): both siblings observed on v1.0.0
    _, day1_findings, _ = _plan_named_findings(
        [
            _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha", "beta"], component_root="packages/a/skills"),
            _raw_update("bob/suite-b", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/b/skills"),
        ],
        authority,
    )
    r1 = reduce_poll(
        empty_state(),
        PollInput(poll_id="poll-day1", observed_at=TUE_NOV_10, findings=day1_findings),
        authority,
    )
    assert r1.status == "applied"

    # Day 2 (Thu): ONLY alice/suite-a advances to v1.1.0 (beta vanished, alpha still present); bob/suite-b is ABSENT.
    _, day2_findings, _ = _plan_named_findings(
        [
            _raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", previous_version="v1.0.0", adds=["alpha"], component_root="packages/a/skills"),
        ],
        authority,
    )
    r2 = reduce_poll(
        r1.state,
        PollInput(poll_id="poll-day2", observed_at=THU_NOV_12, findings=day2_findings),
        authority,
    )
    assert r2.status == "applied"
    assert r2.eligible == ()

    bucket_a = r2.state.get_bucket("acme/shared-repo", "alice/suite-a")
    bucket_b = r2.state.get_bucket("acme/shared-repo", "bob/suite-b")
    assert bucket_a is not None and bucket_b is not None

    # alice/suite-a: alpha keeps immutable v1.0.0 FirstSeenPin while updating last_seen_version to v1.1.0
    alpha_a = bucket_a.rows["acme/shared-repo:alpha"]
    assert alpha_a.first_seen_pin == FirstSeenPin(
        first_seen_version="v1.0.0",
        evidence_url="https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/alpha/SKILL.md",
        first_seen_at="2026-11-10T06:00:00Z",
        first_seen_poll_id="poll-day1",
    )
    assert alpha_a.last_seen_version == "v1.1.0"
    assert alpha_a.present_in_latest is True

    # alice/suite-a: beta is legitimately vanished and preserved with its v1.0.0 pin
    beta_a = bucket_a.rows["acme/shared-repo:beta"]
    assert beta_a.present_in_latest is False
    assert beta_a.vanished_at == "2026-11-12T06:00:00Z"
    assert beta_a.vanished_poll_id == "poll-day2"
    assert beta_a.first_seen_pin.first_seen_version == "v1.0.0"
    assert bucket_a.vanished_row_ids == ("acme/shared-repo:beta",)
    assert bucket_a.pending_since == "2026-11-10T06:00:00Z"  # Never slides forward!

    # bob/suite-b: absent on Thu -> untouched, NOT vanished, revision unchanged
    assert bucket_b == r1.state.get_bucket("acme/shared-repo", "bob/suite-b")
    assert bucket_b.vanished_row_ids == ()
    assert r2.decisions[("acme/shared-repo", "bob/suite-b")].decision == DECISION_ABSENT
    assert r2.decisions[("acme/shared-repo", "bob/suite-b")].eligible is False

    # Day 3 (Mon flush day): ONLY alice/suite-a is freshly observed; bob/suite-b is STILL absent.
    r3 = reduce_poll(
        r2.state,
        PollInput(poll_id="poll-monday", observed_at=MON_NOV_16, findings=day2_findings),
        authority,
    )
    assert r3.status == "applied"
    assert r3.write_authorized is False
    assert [(d.repository, d.named_id) for d in r3.eligible] == [("acme/shared-repo", "alice/suite-a")]
    dec_a = r3.decisions[("acme/shared-repo", "alice/suite-a")]
    dec_b = r3.decisions[("acme/shared-repo", "bob/suite-b")]

    assert dec_a.decision == DECISION_FLUSH
    assert dec_a.eligible is True
    assert dec_a.write_authorized is False
    assert dec_a.reasons == ("flush-day",)
    assert dec_a.vanished_row_ids == ("acme/shared-repo:beta",)
    assert dec_a.row_pins["acme/shared-repo:alpha"].first_seen_version == "v1.0.0"
    assert dec_a.row_pins["acme/shared-repo:beta"].first_seen_version == "v1.0.0"

    # Absent sibling (even with a 6-day-old snapshot on Monday flush day!) is NEVER eligible
    assert dec_b.decision == DECISION_ABSENT
    assert dec_b.eligible is False
    assert dec_b.finding is None


def test_one_week_old_unreobserved_snapshot_never_becomes_eligible_on_monday():
    """Directly guards against stale prior-poll snapshots authorizing a Monday flush."""
    authority = _base_authority()
    _, findings, _ = _plan_named_findings(
        [_raw_update("carol/other-suite", "other/repo", "v2.0.0", adds=["gamma"])],
        authority,
    )
    r1 = reduce_poll(
        empty_state(),
        PollInput(poll_id="poll-week-ago", observed_at=TUE_NOV_10, findings=findings),
        authority,
    )
    # Next Monday (Nov 16): poll runs with empty findings for other/repo (not re-observed)
    r2 = reduce_poll(
        r1.state,
        PollInput(poll_id="poll-next-monday", observed_at=MON_NOV_16, findings=[]),
        authority,
    )
    assert r2.status == "applied"
    assert r2.eligible == ()
    dec = r2.decisions[("other/repo", "carol/other-suite")]
    assert dec.decision == DECISION_ABSENT
    assert dec.eligible is False
    assert dec.finding is None
    # Bucket history remains intact and not marked vanished
    bucket = r2.state.get_bucket("other/repo", "carol/other-suite")
    assert bucket is not None
    assert bucket.vanished_row_ids == ()
    assert bucket.present_row_ids == ("other/repo:gamma",)


# ---------------------------------------------------------------------------
# 3. Replay vs later verified identical sighting vs conflicting poll_id / stale time
# ---------------------------------------------------------------------------


def test_replay_vs_later_identical_sighting_vs_conflicts_and_stale_time():
    authority = _base_authority()
    _, findings_v1, _ = _plan_named_findings(
        [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])],
        authority,
    )
    _, findings_v2, _ = _plan_named_findings(
        [_raw_update("carol/other-suite", "other/repo", "v1.1.0", adds=["gamma"])],
        authority,
    )

    # Initial poll on Tue
    r1 = reduce_poll(
        empty_state(),
        PollInput(poll_id="poll-1", observed_at=TUE_NOV_10, findings=findings_v1),
        authority,
    )
    assert r1.status == "applied"
    assert r1.state.revision == 1
    assert r1.state.get_bucket("other/repo", "carol/other-suite").sighting_count == 1

    # Exact replay of poll-1 -> idempotent no-op, revision/sighting_count unchanged, eligible=()
    r_replay = reduce_poll(
        r1.state,
        PollInput(poll_id="poll-1", observed_at=TUE_NOV_10, findings=findings_v1),
        authority,
    )
    assert r_replay.status == "replayed"
    assert r_replay.replayed is True
    assert r_replay.state == r1.state
    assert r_replay.eligible == ()
    assert r_replay.decisions[("other/repo", "carol/other-suite")].decision == DECISION_REPLAYED

    # Conflicting reuse of poll-1 (different findings) -> rejected fail-closed
    r_conflict_payload = reduce_poll(
        r1.state,
        PollInput(poll_id="poll-1", observed_at=TUE_NOV_10, findings=findings_v2),
        authority,
    )
    assert r_conflict_payload.status == "rejected"
    assert "conflicting poll_id" in (r_conflict_payload.rejection_reason or "")
    assert r_conflict_payload.state == r1.state
    assert r_conflict_payload.eligible == ()

    # Conflicting reuse of poll-1 (different observed_at) -> rejected fail-closed
    r_conflict_time = reduce_poll(
        r1.state,
        PollInput(poll_id="poll-1", observed_at=WED_NOV_11, findings=findings_v1),
        authority,
    )
    assert r_conflict_time.status == "rejected"
    assert r_conflict_time.state == r1.state

    # Stale timestamp with new poll_id -> rejected fail-closed
    r_stale = reduce_poll(
        r1.state,
        PollInput(poll_id="poll-stale", observed_at=TUE_NOV_10 - dt.timedelta(hours=1), findings=findings_v1),
        authority,
    )
    assert r_stale.status == "rejected"
    assert "stale observed_at" in (r_stale.rejection_reason or "")
    assert r_stale.state == r1.state

    # Later verified identical sighting on Monday (new poll_id, later observed_at, identical finding)
    r_later = reduce_poll(
        r1.state,
        PollInput(poll_id="poll-monday", observed_at=MON_NOV_16, findings=findings_v1),
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
# 4. Window-elapsed from pending_since (not releasedAt) & per-named urgency
# ---------------------------------------------------------------------------


def test_window_elapsed_uses_pending_since_never_released_at():
    authority = _base_authority()
    # Release is 30 days old, but first observed on Tue Nov 10
    _, findings, _ = _plan_named_findings(
        [_raw_update("carol/other-suite", "other/repo", "v1.0.0", released_at="2026-10-01T00:00:00Z", adds=["gamma"])],
        authority,
    )
    # Use flush_weekday=6 (Sunday) so Tuesday Nov 17 tests window-elapsed specifically
    cfg = ReducerConfig(flush_weekday=6, window_days=7)

    r1 = reduce_poll(empty_state(), PollInput("p1", TUE_NOV_10, findings), authority, cfg)
    assert r1.eligible == ()

    r2 = reduce_poll(r1.state, PollInput("p2", WED_NOV_11, findings), authority, cfg)
    assert r2.eligible == ()
    assert r2.decisions[("other/repo", "carol/other-suite")].decision == DECISION_HOLD

    # Exactly 7 days after pending_since (Tue Nov 17) -> window-elapsed!
    r3 = reduce_poll(r2.state, PollInput("p3", TUE_NOV_17, findings), authority, cfg)
    assert len(r3.eligible) == 1
    assert r3.eligible[0].decision == DECISION_FLUSH
    assert r3.eligible[0].reasons == ("window-elapsed",)
    assert r3.eligible[0].write_authorized is False


@pytest.mark.parametrize("status,expect_urgent", [
    (404, True),
    (410, True),
    (403, False),
    (429, False),
    (500, False),
    (503, False),
    ("network_error", False),
])
def test_per_named_urgency_isolation_between_same_repo_siblings(status: Any, expect_urgent: bool):
    authority = _base_authority()
    _, findings, _ = _plan_named_findings(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v1.0.0",
                adds=["alpha"],
                liveness=[
                    {
                        "skillId": "alice/kept-leaf",
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
        ],
        authority,
    )
    res = reduce_poll(empty_state(), PollInput("p-urg", TUE_NOV_10, findings), authority)
    assert res.status == "applied"
    dec_a = res.decisions[("acme/shared-repo", "alice/suite-a")]
    dec_b = res.decisions[("acme/shared-repo", "bob/suite-b")]

    # Sibling B NEVER inherits urgency from Sibling A
    assert dec_b.decision == DECISION_HOLD
    assert dec_b.eligible is False

    if expect_urgent:
        assert dec_a.decision == DECISION_URGENT
        assert dec_a.eligible is True
        assert dec_a.reasons == (f"dead-link:alice/kept-leaf:{status}",)
        assert [(d.repository, d.named_id) for d in res.eligible] == [("acme/shared-repo", "alice/suite-a")]
    else:
        assert dec_a.decision == DECISION_HOLD
        assert dec_a.eligible is False
        assert res.eligible == ()


# ---------------------------------------------------------------------------
# 5. Parameterized negative / adversarial probes (fail-closed, zero uncaught TypeError)
# ---------------------------------------------------------------------------


def _sealed_valid_finding(authority: dict[str, dict[str, Any]]) -> dict[str, Any]:
    _, findings, _ = _plan_named_findings(
        [_raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha"], component_root="packages/a/skills")],
        authority,
    )
    return findings[0]


@pytest.mark.parametrize("mutator", [
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
def test_malformed_or_mis_scoped_observations_reject_without_uncaught_exception(mutator):
    authority = _base_authority()
    bad = _sealed_valid_finding(authority)
    mutator(bad)
    # Re-seal so the test exercises semantic/structural validation, not just hash mismatch
    bad = envelope.seal(bad)

    _, healthy_other, _ = _plan_named_findings(
        [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])],
        authority,
    )

    res = reduce_poll(
        empty_state(),
        PollInput("p-neg", MON_NOV_16, [bad, *healthy_other]),
        authority,
    )
    assert res.status == "applied"
    assert len(res.rejected_observations) == 1
    assert res.rejected_observations[0].named_id == "alice/suite-a"
    assert res.state.get_bucket("acme/shared-repo", "alice/suite-a") is None
    # Unrelated repo still covered cleanly!
    assert [(d.repository, d.named_id) for d in res.eligible] == [("other/repo", "carol/other-suite")]


def test_tampered_digest_and_conflicting_duplicate_observations_fail_closed():
    authority = _base_authority()
    valid = _sealed_valid_finding(authority)
    tampered = copy.deepcopy(valid)
    tampered["componentRemoves"] = ["alice/old-leaf"]  # Digest no longer matches!

    res_tampered = reduce_poll(empty_state(), PollInput("p-tamp", MON_NOV_16, [tampered]), authority)
    assert res_tampered.status == "applied"
    assert len(res_tampered.rejected_observations) == 1
    assert "digest mismatch" in res_tampered.rejected_observations[0].reason
    assert res_tampered.eligible == ()

    # Existing bucket receiving a tampered observation on Monday stays untouched and DECISION_REJECTED
    r_seed = reduce_poll(empty_state(), PollInput("p-seed", TUE_NOV_10, [valid]), authority)
    r_bad_mon = reduce_poll(r_seed.state, PollInput("p-bad-mon", MON_NOV_16, [tampered]), authority)
    assert r_bad_mon.status == "applied"
    assert r_bad_mon.decisions[("acme/shared-repo", "alice/suite-a")].decision == DECISION_REJECTED
    assert r_bad_mon.decisions[("acme/shared-repo", "alice/suite-a")].eligible is False
    assert r_bad_mon.state.get_bucket("acme/shared-repo", "alice/suite-a") == r_seed.state.get_bucket(
        "acme/shared-repo", "alice/suite-a"
    )
    assert r_bad_mon.eligible == ()

    # Conflicting duplicate observations for same (repo, named_id) in one poll
    _, alt_findings, _ = _plan_named_findings(
        [_raw_update("alice/suite-a", "acme/shared-repo", "v1.1.0", adds=["alpha"], component_root="packages/a/skills")],
        authority,
    )
    res_dup = reduce_poll(empty_state(), PollInput("p-dup", MON_NOV_16, [valid, alt_findings[0]]), authority)
    assert res_dup.status == "applied"
    assert len(res_dup.rejected_observations) == 1
    assert "conflicting duplicate" in res_dup.rejected_observations[0].reason
    assert res_dup.state.get_bucket("acme/shared-repo", "alice/suite-a") is None
    assert res_dup.eligible == ()


def test_incomplete_poll_and_unavailable_suite_never_infer_vanishings_or_eligibility():
    authority = _base_authority()
    _, day1, _ = _plan_named_findings(
        [
            _raw_update("alice/suite-a", "acme/shared-repo", "v1.0.0", adds=["alpha", "beta"], component_root="packages/a/skills"),
            _raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"]),
        ],
        authority,
    )
    r1 = reduce_poll(empty_state(), PollInput("p1", TUE_NOV_10, day1), authority)

    # Incomplete poll on Monday -> fails closed completely
    r_inc = reduce_poll(r1.state, PollInput("p-inc", MON_NOV_16, day1, complete=False), authority)
    assert r_inc.status == "rejected"
    assert r_inc.state == r1.state
    assert r_inc.eligible == ()

    # Complete poll on Monday where alice/suite-a is unavailable -> untouched, unrelated repo eligible
    _, other_only, _ = _plan_named_findings(
        [_raw_update("carol/other-suite", "other/repo", "v1.0.0", adds=["gamma"])],
        authority,
    )
    r_unavail = reduce_poll(
        r1.state,
        PollInput(
            "p-unavail",
            MON_NOV_16,
            other_only,
            unavailable_named_ids=frozenset({"alice/suite-a"}),
        ),
        authority,
    )
    assert r_unavail.status == "applied"
    assert r_unavail.decisions[("acme/shared-repo", "alice/suite-a")].decision == DECISION_UNAVAILABLE
    assert r_unavail.decisions[("acme/shared-repo", "alice/suite-a")].eligible is False
    assert r_unavail.state.get_bucket("acme/shared-repo", "alice/suite-a").vanished_row_ids == ()
    assert [(d.repository, d.named_id) for d in r_unavail.eligible] == [("other/repo", "carol/other-suite")]


def test_naive_observed_at_rejected_fail_closed():
    authority = _base_authority()
    naive = dt.datetime(2026, 11, 16, 6, 0)
    res = reduce_poll(empty_state(), PollInput("p-naive", naive, []), authority)
    assert res.status == "rejected"
    assert "timezone-aware" in (res.rejection_reason or "")
    assert res.eligible == ()


# ---------------------------------------------------------------------------
# 6. Governance invariants: C1 Ruflo/AgentDB, #1833 legacy hold, frozen GBrain
# ---------------------------------------------------------------------------


def test_c1_ruflo_and_agentdb_distinct_sources_and_cross_source_rejection():
    authority = _base_authority()
    _, c1_findings, _ = _plan_named_findings(
        [
            _raw_update("ruvnet/ruflo", "ruvnet/ruflo", "v3.0.0", adds=["r-leaf"]),
            _raw_update("ruvnet/agentdb", "ruvnet/agentdb", "v2.0.0", adds=["a-leaf"]),
        ],
        authority,
    )
    res = reduce_poll(empty_state(), PollInput("p-c1", MON_NOV_16, c1_findings), authority)
    assert res.status == "applied"
    assert [(d.repository, d.named_id) for d in res.eligible] == [
        ("ruvnet/agentdb", "ruvnet/agentdb"),
        ("ruvnet/ruflo", "ruvnet/ruflo"),
    ]

    # Spoofed AgentDB claiming Ruflo release source must fail closed
    spoofed = copy.deepcopy(next(f for f in c1_findings if f["skillId"] == "ruvnet/agentdb"))
    spoofed["sourceUrl"] = "https://github.com/ruvnet/ruflo/releases/tag/v2.0.0"
    spoofed = envelope.seal(spoofed)

    res_spoof = reduce_poll(empty_state(), PollInput("p-c1-spoof", MON_NOV_16, [spoofed]), authority)
    assert len(res_spoof.rejected_observations) == 1
    assert res_spoof.rejected_observations[0].named_id == "ruvnet/agentdb"
    assert res_spoof.eligible == ()


def test_legacy_hold_1833_and_frozen_gbrain_stay_held_while_unrelated_repo_proceeds():
    authority = _base_authority()
    # Construct a valid legacy #1833-style open release issue so real P1 planner produces knownLegacyHolds
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

    _, findings, held_repos = _plan_named_findings(
        [
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
        ],
        authority,
        gh=gh,
    )
    assert "legacy/repo" in held_repos

    res = reduce_poll(
        empty_state(),
        PollInput(
            "p-gov",
            MON_NOV_16,
            findings,
            held_repos=held_repos,
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
