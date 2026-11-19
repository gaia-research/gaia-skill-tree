"""Offline unit and P1-planner integration tests for scripts.upstream_watcher.weekly_journal.

Run with:
    pytest scripts/upstream_watcher/tests/test_weekly_journal.py -v
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.upstream_watcher import envelope, repository_batch, staging
from scripts.upstream_watcher.weekly_journal import (
    JOURNAL_FORMAT,
    JOURNAL_NAMESPACE,
    STATUS_BOOTSTRAP,
    STATUS_CORRUPT,
    STATUS_FOREIGN,
    STATUS_LEGACY_V2,
    STATUS_LOST,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_STALE,
    JournalBlockedError,
    JournalConflictError,
    JournalPin,
    JournalSizeError,
    _journal_digest,
    commit_poll,
    decode_state,
    encode_state,
    load_journal,
    save_journal,
    serialize_state,
)
from scripts.upstream_watcher.weekly_reducer import (
    DECISION_FLUSH,
    DECISION_HOLD,
    PRESENCE_UNKNOWN,
    PRESENCE_VANISHED,
    PollInput,
    ReducerConfig,
    ScopedCompleteInventory,
    empty_state,
    poll_input_from_batch_report,
    reduce_poll,
)

# Verified UTC calendar anchors (Nov 1, 2026 is Sunday):
TUE_NOV_10 = dt.datetime(2026, 11, 10, 6, 0, tzinfo=dt.timezone.utc)
WED_NOV_11 = dt.datetime(2026, 11, 11, 6, 0, tzinfo=dt.timezone.utc)
THU_NOV_12 = dt.datetime(2026, 11, 12, 6, 0, tzinfo=dt.timezone.utc)
FRI_NOV_13 = dt.datetime(2026, 11, 13, 6, 0, tzinfo=dt.timezone.utc)
MON_NOV_16 = dt.datetime(2026, 11, 16, 6, 0, tzinfo=dt.timezone.utc)

POLICY = {
    "shared_source_model": "repo_envelope",
    "legacy_transition": "preserve_plan",
}


class OfflineFakeGh:
    """Offline read-only FakeGh for real P1 repository_batch planning; forbids all writes."""

    def __init__(
        self,
        issues: list[dict[str, Any]] | None = None,
        comments: dict[int, list[dict[str, Any]]] | None = None,
    ):
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
    return {
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
        "carol/other-suite": {
            "id": "carol/other-suite",
            "links": {"github": "https://github.com/other/repo"},
            "suiteComponents": ["carol/leaf-one"],
        },
        "carol/leaf-one": {"id": "carol/leaf-one"},
    }


def _plan_batch(
    raw_findings: list[dict[str, Any]],
    authority: dict[str, dict[str, Any]],
    gh: OfflineFakeGh | None = None,
) -> dict[str, Any]:
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
    return report


def _open_envelope_issue(
    report: dict[str, Any],
    repo: str,
    *,
    number: int = 100,
    updated_at: str = "2026-11-10T06:00:00Z",
) -> dict[str, Any]:
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
        "upstreamComponentRoot": component_root,
        "componentAdds": list(adds or []),
        "componentRemoves": list(removes or []),
        "linkLiveness": list(liveness or []),
        "nameDrift": list(name_drift or []),
    }


def _resign(payload: dict[str, Any]) -> str:
    signed = copy.deepcopy(payload)
    signed["digest"] = _journal_digest(signed)
    return json.dumps(signed, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _seed_single_poll_journal(tmp_path: Path) -> tuple[Path, dict[str, dict[str, Any]], Any, JournalPin]:
    authority = _base_authority()
    raw = [
        _raw_update(
            "alice/suite-a",
            "acme/shared-repo",
            "v1.0.0",
            adds=["alpha", "beta"],
            removes=["alice/old-leaf"],
            liveness=[
                {
                    "skillId": "alice/kept-leaf",
                    "url": "https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/kept-leaf/SKILL.md",
                    "status": 200,
                }
            ],
            name_drift=[{"skillId": "alice/kept-leaf", "upstreamName": "kept-leaf-renamed"}],
            component_root="packages/a/skills",
        )
    ]
    report = _plan_batch(raw, authority)
    poll = poll_input_from_batch_report("poll-1", TUE_NOV_10, report)
    res = reduce_poll(empty_state(), poll, authority)
    assert res.status == "applied"
    assert res.write_authorized is False

    journal_path = tmp_path / "named-v3.journal.json"
    saved = save_journal(journal_path, res.state, authority, poll=poll, allow_bootstrap=True)
    assert saved.status == STATUS_OK
    assert saved.pin is not None
    return journal_path, authority, res.state, saved.pin


# ---------------------------------------------------------------------------
# 1. P1 planner -> reducer -> journal round-trip & sibling independence
# ---------------------------------------------------------------------------


def test_p1_planner_week_long_carry_and_lossless_roundtrip(tmp_path: Path) -> None:
    authority = _base_authority()
    journal_path = tmp_path / "weekly-named-v3.json"

    # Fresh explicit offline bootstrap
    boot = load_journal(journal_path, authority, allow_bootstrap=True)
    assert boot.status == STATUS_BOOTSTRAP
    assert boot.usable is True
    assert boot.blocked is False
    assert boot.pin is None
    assert boot.state == empty_state()

    # Poll 1 (Tuesday): hold window starts, two candidates observed
    r1 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v1.0.0",
                adds=["alpha", "beta"],
                removes=["alice/old-leaf"],
                component_root="packages/a/skills",
            )
        ],
        authority,
    )
    p1 = poll_input_from_batch_report("poll-tue", TUE_NOV_10, r1)
    res1 = reduce_poll(boot.state, p1, authority)
    assert res1.status == "applied"
    assert res1.decisions[("acme/shared-repo", "alice/suite-a")].decision == DECISION_HOLD
    assert res1.write_authorized is False

    h1 = save_journal(journal_path, res1.state, authority, poll=p1, allow_bootstrap=True)
    assert h1.status == STATUS_OK
    assert h1.pin == JournalPin(revision=1, digest=h1.pin.digest)
    raw_bytes_1 = journal_path.read_bytes()

    # Deterministic serialization: re-serializing produces byte-for-byte identical output
    raw_bytes_1_again, pin_1_again = serialize_state(res1.state, authority)
    assert raw_bytes_1_again == raw_bytes_1
    assert pin_1_again == h1.pin

    # Reload from disk and verify complete lossless equality
    loaded1 = load_journal(journal_path, authority, trusted_latest_pin=h1.pin)
    assert loaded1.status == STATUS_OK
    assert loaded1.pin == h1.pin
    assert loaded1.state == res1.state

    # Poll 2 (Wednesday): new release v1.1.0 with gamma added, alpha retained via open issue
    issue_v1 = _open_envelope_issue(r1, "acme/shared-repo", number=101)
    r2 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v1.1.0",
                released_at="2026-11-11T01:00:00Z",
                adds=["alpha", "gamma"],
                component_root="packages/a/skills",
            )
        ],
        authority,
        gh=OfflineFakeGh(issues=[issue_v1]),
    )
    p2 = poll_input_from_batch_report("poll-wed", WED_NOV_11, r2)
    res2 = reduce_poll(loaded1.state, p2, authority)
    assert res2.status == "applied"

    h2 = save_journal(journal_path, res2.state, authority, expected_pin=loaded1.pin, poll=p2, initialized=True)
    assert h2.status == STATUS_OK
    assert h2.pin is not None and h2.pin.revision == 2

    # Poll 3 (Monday): flush day eligible, reloaded across process boundary
    loaded2 = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=h2.pin)
    assert loaded2.status == STATUS_OK
    assert loaded2.state == res2.state

    issue_v2 = _open_envelope_issue(r2, "acme/shared-repo", number=101, updated_at="2026-11-11T06:00:00Z")
    r3 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v1.1.0",
                released_at="2026-11-11T01:00:00Z",
                adds=["alpha", "gamma"],
                component_root="packages/a/skills",
            )
        ],
        authority,
        gh=OfflineFakeGh(issues=[issue_v2]),
    )
    p3 = poll_input_from_batch_report("poll-mon", MON_NOV_16, r3)
    res3 = reduce_poll(loaded2.state, p3, authority)
    assert res3.status == "applied"
    assert res3.decisions[("acme/shared-repo", "alice/suite-a")].decision == DECISION_FLUSH
    assert res3.write_authorized is False

    h3 = save_journal(journal_path, res3.state, authority, expected_pin=loaded2.pin, poll=p3, initialized=True)
    loaded3 = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=h3.pin)
    assert loaded3.status == STATUS_OK
    assert loaded3.state == res3.state

    bucket = loaded3.state.get_bucket("acme/shared-repo", "alice/suite-a")
    assert bucket is not None
    assert bucket.pending_since == "2026-11-10T06:00:00Z"
    assert bucket.first_poll_id == "poll-tue"
    assert bucket.last_poll_id == "poll-mon"
    assert bucket.sighting_count == 3
    assert len(bucket.versions_seen) == 2
    assert bucket.rows["acme/shared-repo:alpha"].first_seen_pin.first_seen_version == "v1.0.0"
    assert bucket.rows["acme/shared-repo:gamma"].first_seen_pin.first_seen_version == "v1.1.0"
    assert bucket.rows["acme/shared-repo:beta"].first_seen_pin.first_seen_version == "v1.0.0"
    assert bucket.rows["acme/shared-repo:beta"].presence == PRESENCE_UNKNOWN


def test_same_repo_same_version_same_slug_siblings_independent(tmp_path: Path) -> None:
    authority = _base_authority()
    journal_path = tmp_path / "siblings.json"

    r1 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v2.0.0",
                adds=["shared-tool"],
                component_root="packages/a/skills",
            ),
            _raw_update(
                "bob/suite-b",
                "acme/shared-repo",
                "v2.0.0",
                adds=["shared-tool"],
                component_root="packages/b/skills",
            ),
        ],
        authority,
    )
    p1 = poll_input_from_batch_report("poll-siblings-1", TUE_NOV_10, r1)
    res1 = reduce_poll(empty_state(), p1, authority)
    assert res1.status == "applied"

    h1 = save_journal(journal_path, res1.state, authority, poll=p1, allow_bootstrap=True)
    loaded1 = load_journal(journal_path, authority, trusted_latest_pin=h1.pin)
    assert loaded1.status == STATUS_OK
    assert loaded1.state == res1.state

    a_bucket = loaded1.state.get_bucket("acme/shared-repo", "alice/suite-a")
    b_bucket = loaded1.state.get_bucket("acme/shared-repo", "bob/suite-b")
    assert a_bucket is not None and b_bucket is not None
    assert a_bucket.latest_finding["skillId"] == "alice/suite-a"
    assert b_bucket.latest_finding["skillId"] == "bob/suite-b"
    assert "acme/shared-repo:shared-tool" in a_bucket.rows
    assert "acme/shared-repo:shared-tool" in b_bucket.rows

    # Update only alice/suite-a in poll 2 using the real open-envelope carry-forward
    # so shared-tool preserves its authoritative v2.0.0 first-seen pin; bob/suite-b stays untouched.
    open_siblings = _open_envelope_issue(r1, "acme/shared-repo", number=150)
    r2 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v2.1.0",
                released_at="2026-11-11T01:00:00Z",
                adds=["shared-tool", "alice-only"],
                component_root="packages/a/skills",
            )
        ],
        authority,
        gh=OfflineFakeGh(issues=[open_siblings]),
    )
    p2 = poll_input_from_batch_report("poll-siblings-2", WED_NOV_11, r2)
    res2 = reduce_poll(loaded1.state, p2, authority)
    assert res2.status == "applied"
    assert ("acme/shared-repo", "alice/suite-a") in res2.accepted_scopes
    assert ("acme/shared-repo", "bob/suite-b") not in res2.accepted_scopes

    h2 = save_journal(journal_path, res2.state, authority, expected_pin=loaded1.pin, poll=p2, initialized=True)
    loaded2 = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=h2.pin)
    assert loaded2.state is not None
    assert loaded2.state.get_bucket("acme/shared-repo", "bob/suite-b") == b_bucket
    a_bucket_2 = loaded2.state.get_bucket("acme/shared-repo", "alice/suite-a")
    assert a_bucket_2 is not None
    assert a_bucket_2.revision == 2
    assert a_bucket_2.rows["acme/shared-repo:shared-tool"].first_seen_pin.first_seen_version == "v2.0.0"
    assert a_bucket_2.rows["acme/shared-repo:alice-only"].first_seen_pin.first_seen_version == "v2.1.0"


# ---------------------------------------------------------------------------
# 2. Replay idempotency, conflicting poll_id, vanished vs unknown, historical-only
# ---------------------------------------------------------------------------


def test_replay_idempotency_conflicting_poll_and_incomplete_across_load(tmp_path: Path) -> None:
    journal_path, authority, state1, pin1 = _seed_single_poll_journal(tmp_path)
    bytes_before = journal_path.read_bytes()

    raw = [
        _raw_update(
            "alice/suite-a",
            "acme/shared-repo",
            "v1.0.0",
            adds=["alpha", "beta"],
            removes=["alice/old-leaf"],
            liveness=[
                {
                    "skillId": "alice/kept-leaf",
                    "url": "https://github.com/acme/shared-repo/blob/v1.0.0/packages/a/skills/kept-leaf/SKILL.md",
                    "status": 200,
                }
            ],
            name_drift=[{"skillId": "alice/kept-leaf", "upstreamName": "kept-leaf-renamed"}],
            component_root="packages/a/skills",
        )
    ]
    report = _plan_batch(raw, authority)
    loaded = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=pin1)
    assert loaded.state == state1

    replay_poll = poll_input_from_batch_report("poll-1", TUE_NOV_10, report)
    replayed = reduce_poll(loaded.state, replay_poll, authority)
    assert replayed.status == "replayed"
    assert replayed.replayed is True
    assert replayed.eligible == ()
    assert replayed.state == state1

    # Saving the unchanged replayed state with expected_pin is an idempotent no-op
    noop_handle = save_journal(journal_path, replayed.state, authority, expected_pin=pin1, initialized=True)
    assert noop_handle.pin == pin1
    assert journal_path.read_bytes() == bytes_before

    # Conflicting poll_id with altered timestamp fails closed
    conflict_poll = poll_input_from_batch_report("poll-1", WED_NOV_11, report)
    rejected_conflict = reduce_poll(loaded.state, conflict_poll, authority)
    assert rejected_conflict.status == "rejected"
    assert rejected_conflict.state == state1

    # Incomplete poll fails closed
    incomplete_poll = poll_input_from_batch_report("poll-incomplete", WED_NOV_11, report, complete=False)
    rejected_incomplete = reduce_poll(loaded.state, incomplete_poll, authority)
    assert rejected_incomplete.status == "rejected"
    assert rejected_incomplete.state == state1


def test_vanished_vs_unknown_and_historical_only_roundtrip(tmp_path: Path) -> None:
    authority = _base_authority()
    journal_path = tmp_path / "presence.json"

    # Poll 1: alpha + beta observed
    r1 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v1.0.0",
                adds=["alpha", "beta"],
                component_root="packages/a/skills",
            )
        ],
        authority,
    )
    p1 = poll_input_from_batch_report("p1", TUE_NOV_10, r1)
    res1 = reduce_poll(empty_state(), p1, authority)
    h1 = save_journal(journal_path, res1.state, authority, poll=p1, allow_bootstrap=True)

    # Poll 2: alpha omitted WITHOUT complete inventory -> PRESENCE_UNKNOWN, pin unchanged
    issue1 = _open_envelope_issue(r1, "acme/shared-repo", number=200)
    r2 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v1.1.0",
                released_at="2026-11-11T01:00:00Z",
                adds=["beta"],
                component_root="packages/a/skills",
            )
        ],
        authority,
        gh=OfflineFakeGh(issues=[issue1]),
    )
    loaded1 = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=h1.pin)
    p2 = poll_input_from_batch_report("p2", WED_NOV_11, r2)
    res2 = reduce_poll(loaded1.state, p2, authority)
    h2 = save_journal(journal_path, res2.state, authority, expected_pin=loaded1.pin, poll=p2, initialized=True)
    loaded2 = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=h2.pin)
    alpha2 = loaded2.state.get_bucket("acme/shared-repo", "alice/suite-a").rows["acme/shared-repo:alpha"]
    assert alpha2.presence == PRESENCE_UNKNOWN
    assert alpha2.first_seen_pin.first_seen_version == "v1.0.0"

    # Poll 3: qualified ScopedCompleteInventory proves alpha vanished
    r3 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v1.2.0",
                released_at="2026-11-12T01:00:00Z",
                adds=["beta"],
                component_root="packages/a/skills",
            )
        ],
        authority,
        gh=OfflineFakeGh(issues=[_open_envelope_issue(r2, "acme/shared-repo", number=200)]),
    )
    base_p3 = poll_input_from_batch_report("p3", THU_NOV_12, r3)
    inv3 = ScopedCompleteInventory(
        poll_id="p3",
        repository="acme/shared-repo",
        named_id="alice/suite-a",
        version="v1.2.0",
        source_url="https://github.com/acme/shared-repo/releases/tag/v1.2.0",
        component_root="packages/a/skills",
        present_slugs=frozenset({"old-leaf", "kept-leaf", "beta"}),
        complete=True,
        truncated=False,
        root_verified=True,
    )
    p3 = PollInput(
        poll_id=base_p3.poll_id,
        observed_at=base_p3.observed_at,
        observed_findings=base_p3.observed_findings,
        planned_findings=base_p3.planned_findings,
        complete=True,
        complete_inventories=(inv3,),
    )
    res3 = reduce_poll(loaded2.state, p3, authority)
    assert res3.status == "applied"
    h3 = save_journal(journal_path, res3.state, authority, expected_pin=loaded2.pin, poll=p3, initialized=True)
    loaded3 = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=h3.pin)
    alpha3 = loaded3.state.get_bucket("acme/shared-repo", "alice/suite-a").rows["acme/shared-repo:alpha"]
    assert alpha3.presence == PRESENCE_VANISHED
    assert alpha3.vanished_at == "2026-11-12T06:00:00Z"
    assert alpha3.vanished_poll_id == "p3"
    assert alpha3.first_seen_pin.first_seen_version == "v1.0.0"

    # Poll 4: no complete inventory -> transitions back to PRESENCE_UNKNOWN while retaining vanished_at/poll_id
    r4 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v1.3.0",
                released_at="2026-11-13T01:00:00Z",
                adds=["beta"],
                component_root="packages/a/skills",
            )
        ],
        authority,
        gh=OfflineFakeGh(issues=[_open_envelope_issue(r3, "acme/shared-repo", number=200)]),
    )
    p4 = poll_input_from_batch_report("p4", FRI_NOV_13, r4)
    res4 = reduce_poll(loaded3.state, p4, authority)
    h4 = save_journal(journal_path, res4.state, authority, expected_pin=loaded3.pin, poll=p4, initialized=True)
    loaded4 = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=h4.pin)
    alpha4 = loaded4.state.get_bucket("acme/shared-repo", "alice/suite-a").rows["acme/shared-repo:alpha"]
    assert alpha4.presence == PRESENCE_UNKNOWN
    assert alpha4.vanished_at == "2026-11-12T06:00:00Z"
    assert alpha4.vanished_poll_id == "p3"
    assert loaded4.state == res4.state

    # Historical-only row carried from an open issue on first observation round-trips cleanly
    hist_path = tmp_path / "historical-only.json"
    p_hist = poll_input_from_batch_report("p-hist", WED_NOV_11, r2)
    res_hist = reduce_poll(empty_state(), p_hist, authority)
    assert res_hist.status == "applied"
    h_hist = save_journal(hist_path, res_hist.state, authority, poll=p_hist, allow_bootstrap=True)
    loaded_hist = load_journal(hist_path, authority, trusted_latest_pin=h_hist.pin)
    assert loaded_hist.state == res_hist.state
    hist_alpha = loaded_hist.state.get_bucket("acme/shared-repo", "alice/suite-a").rows["acme/shared-repo:alpha"]
    assert hist_alpha.historical_only is True
    assert hist_alpha.first_seen_pin.first_seen_at is None
    assert hist_alpha.first_seen_pin.first_seen_poll_id is None
    assert hist_alpha.presence == PRESENCE_UNKNOWN


# ---------------------------------------------------------------------------
# 3. Lifecycle: missing, bootstrap, initialized-lost, legacy-v2, foreign, stale pin
# ---------------------------------------------------------------------------


def test_missing_bootstrap_and_initialized_lost_never_resets(tmp_path: Path) -> None:
    authority = _base_authority()
    missing_path = tmp_path / "does-not-exist.json"

    h_missing = load_journal(missing_path, authority, allow_bootstrap=False, initialized=False)
    assert h_missing.status == STATUS_MISSING
    assert h_missing.blocked is True
    assert h_missing.state is None

    h_boot = load_journal(missing_path, authority, allow_bootstrap=True, initialized=False)
    assert h_boot.status == STATUS_BOOTSTRAP
    assert h_boot.usable is True
    assert h_boot.state == empty_state()

    # Initialized + missing is LOST even when allow_bootstrap=True
    for allow_boot in (False, True):
        h_lost = load_journal(missing_path, authority, allow_bootstrap=allow_boot, initialized=True)
        assert h_lost.status == STATUS_LOST
        assert h_lost.blocked is True
        assert h_lost.state is None

    # Expected trusted_latest_pin on missing file is also LOST
    fake_pin = JournalPin(revision=1, digest="0" * 64)
    h_pin_lost = load_journal(missing_path, authority, allow_bootstrap=True, trusted_latest_pin=fake_pin)
    assert h_pin_lost.status == STATUS_LOST
    assert h_pin_lost.blocked is True

    # save_journal refuses creating over missing-initialized or without allow_bootstrap
    with pytest.raises(JournalBlockedError):
        save_journal(missing_path, empty_state(), authority, allow_bootstrap=False)
    with pytest.raises(JournalBlockedError):
        save_journal(missing_path, empty_state(), authority, allow_bootstrap=True, initialized=True)
    assert not missing_path.exists()


def test_legacy_v2_and_foreign_journals_never_overwritten_or_reinterpreted(tmp_path: Path) -> None:
    authority = _base_authority()
    _, empty_pin = serialize_state(empty_state(), authority)
    empty_poll = PollInput(poll_id="poll-empty", observed_at=TUE_NOV_10, observed_findings=(), planned_findings=())

    # Real legacy v2 journal written by staging.Journal
    legacy_path = tmp_path / "legacy-v2.json"
    legacy = staging.Journal()
    legacy.save(legacy_path)
    legacy_before = legacy_path.read_bytes()

    for allow_boot in (False, True):
        loaded = load_journal(legacy_path, authority, allow_bootstrap=allow_boot)
        assert loaded.status == STATUS_LEGACY_V2
        assert loaded.blocked is True
        assert loaded.state is None
        assert loaded.namespace == "legacy-v2"

    with pytest.raises(JournalBlockedError, match="legacy-v2"):
        save_journal(legacy_path, empty_state(), authority, allow_bootstrap=True)
    with pytest.raises(JournalBlockedError, match="legacy-v2"):
        save_journal(legacy_path, empty_state(), authority, expected_pin=empty_pin)
    with pytest.raises(JournalBlockedError, match="legacy-v2"):
        commit_poll(legacy_path, empty_poll, authority, expected_pin=empty_pin)
    assert legacy_path.read_bytes() == legacy_before

    # Foreign JSON format
    foreign_path = tmp_path / "foreign.json"
    foreign_bytes = b'{"format": "some-other-tool", "namespace": "other-v1", "version": 1}\n'
    foreign_path.write_bytes(foreign_bytes)

    loaded_foreign = load_journal(foreign_path, authority, allow_bootstrap=True)
    assert loaded_foreign.status == STATUS_FOREIGN
    assert loaded_foreign.blocked is True
    assert loaded_foreign.state is None

    with pytest.raises(JournalBlockedError, match="foreign"):
        save_journal(foreign_path, empty_state(), authority, allow_bootstrap=True)
    with pytest.raises(JournalBlockedError, match="foreign"):
        save_journal(foreign_path, empty_state(), authority, expected_pin=empty_pin)
    with pytest.raises(JournalBlockedError, match="foreign"):
        commit_poll(foreign_path, empty_poll, authority, expected_pin=empty_pin)
    assert foreign_path.read_bytes() == foreign_bytes


def test_trusted_latest_pin_refuses_stale_cache_restore_and_divergent_digest(tmp_path: Path) -> None:
    journal_path, authority, state1, pin1 = _seed_single_poll_journal(tmp_path)
    bytes_v1 = journal_path.read_bytes()

    # Advance to rev 2
    r2 = _plan_batch(
        [
            _raw_update(
                "carol/other-suite",
                "other/repo",
                "v1.0.0",
                adds=["new-carol-skill"],
                component_root="skills",
            )
        ],
        authority,
    )
    p2 = poll_input_from_batch_report("poll-2", WED_NOV_11, r2)
    res2 = reduce_poll(state1, p2, authority)
    h2 = save_journal(journal_path, res2.state, authority, expected_pin=pin1, poll=p2, initialized=True)
    pin2 = h2.pin
    assert pin2 is not None and pin2.revision == 2

    # Simulate external cache restoring older valid rev-1 snapshot
    journal_path.write_bytes(bytes_v1)

    # Without trusted_latest_pin, embedded digest alone cannot prove freshness
    unpinned = load_journal(journal_path, authority)
    assert unpinned.status == STATUS_OK
    assert unpinned.pin == pin1

    # With caller's explicit trusted_latest_pin, older valid file is REFUSED as stale
    stale = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=pin2)
    assert stale.status == STATUS_STALE
    assert stale.blocked is True
    assert stale.state is None
    assert stale.pin == pin1

    # Divergent digest at same revision is also refused
    divergent_pin = JournalPin(revision=1, digest=("f" if pin1.digest[0] != "f" else "e") + pin1.digest[1:])
    div = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=divergent_pin)
    assert div.status == STATUS_STALE
    assert div.blocked is True
    assert div.state is None


# ---------------------------------------------------------------------------
# 4. CAS enforcement, lineage/history-loss prevention, commit_poll, interrupted save
# ---------------------------------------------------------------------------


def test_cas_lineage_refuses_unrelated_higher_revision_with_valid_pin(tmp_path: Path) -> None:
    """Reproduces the lineage probe: valid rev-1 pin + unrelated rev-2 state must NOT erase rev-1 history."""
    journal_path, authority, state1, pin1 = _seed_single_poll_journal(tmp_path)
    bytes_v1 = journal_path.read_bytes()

    # Independently start from empty_state() and process two newer empty polls -> unrelated rev-2 state
    empty_a = PollInput(poll_id="empty-a", observed_at=WED_NOV_11, observed_findings=(), planned_findings=())
    empty_b = PollInput(poll_id="empty-b", observed_at=THU_NOV_12, observed_findings=(), planned_findings=())
    u1 = reduce_poll(empty_state(), empty_a, authority)
    assert u1.status == "applied"
    u2 = reduce_poll(u1.state, empty_b, authority)
    assert u2.status == "applied"
    assert u2.state.revision == 2
    assert u2.state.buckets == {}

    # 1. Refused without poll (no arbitrary replacement)
    with pytest.raises(JournalConflictError, match="arbitrary state replacement"):
        save_journal(journal_path, u2.state, authority, expected_pin=pin1, initialized=True)
    assert journal_path.read_bytes() == bytes_v1

    # 2. Refused even WITH a valid PollInput because reduce_poll(rev1, empty_b) preserves rev-1 history
    with pytest.raises(JournalConflictError, match="exact one-step reducer transition"):
        save_journal(journal_path, u2.state, authority, expected_pin=pin1, poll=empty_b, initialized=True)
    assert journal_path.read_bytes() == bytes_v1

    # 3. Verify original bucket, row pins, and poll-1 receipt are completely intact
    reloaded = load_journal(journal_path, authority, initialized=True, trusted_latest_pin=pin1)
    assert reloaded.status == STATUS_OK
    assert reloaded.state == state1
    assert "poll-1" in reloaded.state.seen_polls
    assert reloaded.state.get_bucket("acme/shared-repo", "alice/suite-a") is not None


def test_cas_same_revision_digest_mutation_refused(tmp_path: Path) -> None:
    journal_path, authority, _state1, pin1 = _seed_single_poll_journal(tmp_path)
    bytes_v1 = journal_path.read_bytes()

    # Construct a different valid rev-1 state from empty_state()
    r_other = _plan_batch(
        [
            _raw_update(
                "carol/other-suite",
                "other/repo",
                "v1.0.0",
                adds=["carol-add"],
                component_root="skills",
            )
        ],
        authority,
    )
    p_other = poll_input_from_batch_report("poll-other", TUE_NOV_10, r_other)
    other_rev1 = reduce_poll(empty_state(), p_other, authority)
    assert other_rev1.status == "applied"
    assert other_rev1.state.revision == 1

    with pytest.raises(JournalConflictError, match="digest mutation without revision advance"):
        save_journal(journal_path, other_rev1.state, authority, expected_pin=pin1, poll=p_other, initialized=True)
    assert journal_path.read_bytes() == bytes_v1


def test_commit_poll_verified_transition_replay_rejection_and_guards(tmp_path: Path) -> None:
    authority = _base_authority()
    journal_path = tmp_path / "commit-poll.json"

    r1 = _plan_batch(
        [
            _raw_update(
                "alice/suite-a",
                "acme/shared-repo",
                "v1.0.0",
                adds=["alpha"],
                component_root="packages/a/skills",
            )
        ],
        authority,
    )
    p1 = poll_input_from_batch_report("cp-1", TUE_NOV_10, r1)

    # 1. Explicit offline bootstrap via commit_poll
    c1 = commit_poll(journal_path, p1, authority, allow_bootstrap=True)
    assert c1.persisted is True
    assert c1.reduction.status == "applied"
    assert c1.handle.status == STATUS_OK
    assert c1.handle.pin is not None and c1.handle.pin.revision == 1
    pin1 = c1.handle.pin
    bytes_v1 = journal_path.read_bytes()

    # 2. Exact replay leaves disk bytes untouched and persisted=False
    c_replay = commit_poll(journal_path, p1, authority, expected_pin=pin1, initialized=True, trusted_latest_pin=pin1)
    assert c_replay.persisted is False
    assert c_replay.reduction.status == "replayed"
    assert c_replay.handle.pin == pin1
    assert journal_path.read_bytes() == bytes_v1

    # 3. Incomplete poll rejected fail-closed; disk bytes untouched
    p_inc = poll_input_from_batch_report("cp-inc", WED_NOV_11, r1, complete=False)
    c_inc = commit_poll(journal_path, p_inc, authority, expected_pin=pin1, initialized=True, trusted_latest_pin=pin1)
    assert c_inc.persisted is False
    assert c_inc.reduction.status == "rejected"
    assert journal_path.read_bytes() == bytes_v1

    # 4. Genuine next poll advances rev 1 -> rev 2 preserving poll-1 and alice/suite-a
    r2 = _plan_batch(
        [
            _raw_update(
                "carol/other-suite",
                "other/repo",
                "v1.0.0",
                adds=["carol-add"],
                component_root="skills",
            )
        ],
        authority,
    )
    p2 = poll_input_from_batch_report("cp-2", WED_NOV_11, r2)
    c2 = commit_poll(journal_path, p2, authority, expected_pin=pin1, initialized=True, trusted_latest_pin=pin1)
    assert c2.persisted is True
    assert c2.reduction.status == "applied"
    assert c2.handle.pin is not None and c2.handle.pin.revision == 2
    assert "cp-1" in c2.handle.state.seen_polls
    assert "cp-2" in c2.handle.state.seen_polls
    assert c2.handle.state.get_bucket("acme/shared-repo", "alice/suite-a") is not None
    assert c2.handle.state.get_bucket("other/repo", "carol/other-suite") is not None
    bytes_v2 = journal_path.read_bytes()

    # 5. Stale expected_pin refused with JournalConflictError; bytes untouched
    p3 = PollInput(poll_id="cp-3", observed_at=THU_NOV_12, observed_findings=(), planned_findings=())
    with pytest.raises(JournalConflictError):
        commit_poll(journal_path, p3, authority, expected_pin=pin1, initialized=True)
    assert journal_path.read_bytes() == bytes_v2


def test_cas_stale_expected_pin_and_bootstrap_collision_preserve_bytes(tmp_path: Path) -> None:
    journal_path, authority, state1, pin1 = _seed_single_poll_journal(tmp_path)

    r2 = _plan_batch(
        [
            _raw_update(
                "carol/other-suite",
                "other/repo",
                "v1.0.0",
                adds=["carol-add"],
                component_root="skills",
            )
        ],
        authority,
    )
    p2 = poll_input_from_batch_report("poll-2", WED_NOV_11, r2)
    res2 = reduce_poll(state1, p2, authority)
    h2 = save_journal(journal_path, res2.state, authority, expected_pin=pin1, poll=p2, initialized=True)
    pin2 = h2.pin
    assert pin2 is not None
    bytes_v2 = journal_path.read_bytes()

    # Stale expected_pin (pin1) rejected
    r3 = _plan_batch(
        [
            _raw_update(
                "carol/other-suite",
                "other/repo",
                "v1.1.0",
                released_at="2026-11-12T01:00:00Z",
                adds=["carol-add-2"],
                component_root="skills",
            )
        ],
        authority,
    )
    p3 = poll_input_from_batch_report("poll-3", THU_NOV_12, r3)
    res3 = reduce_poll(res2.state, p3, authority)
    with pytest.raises(JournalConflictError):
        save_journal(journal_path, res3.state, authority, expected_pin=pin1, poll=p3, initialized=True)
    assert journal_path.read_bytes() == bytes_v2

    # Bootstrap against existing file rejected
    with pytest.raises(JournalConflictError):
        save_journal(journal_path, res3.state, authority, expected_pin=None, poll=p3, allow_bootstrap=True)
    assert journal_path.read_bytes() == bytes_v2

    # Revision rollback rejected
    with pytest.raises(JournalConflictError):
        save_journal(journal_path, state1, authority, expected_pin=pin2, initialized=True)
    assert journal_path.read_bytes() == bytes_v2


def test_interrupted_save_leaves_prior_bytes_intact_and_cleans_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal_path, authority, state1, pin1 = _seed_single_poll_journal(tmp_path)
    bytes_v1 = journal_path.read_bytes()

    r2 = _plan_batch(
        [
            _raw_update(
                "carol/other-suite",
                "other/repo",
                "v1.0.0",
                adds=["carol-add"],
                component_root="skills",
            )
        ],
        authority,
    )
    p2 = poll_input_from_batch_report("poll-2", WED_NOV_11, r2)
    res2 = reduce_poll(state1, p2, authority)

    def _boom(_src: Any, _dst: Any) -> None:
        raise OSError("simulated interrupted os.replace")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(OSError, match="simulated interrupted os.replace"):
        save_journal(journal_path, res2.state, authority, expected_pin=pin1, poll=p2, initialized=True)

    assert journal_path.read_bytes() == bytes_v1
    leftover_tmps = [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftover_tmps == []


# ---------------------------------------------------------------------------
# 5. Corrupt JSON, duplicate keys, AND checksum-valid semantic contradictions
# ---------------------------------------------------------------------------


def test_malformed_json_duplicate_keys_digest_mismatch_and_non_file(tmp_path: Path) -> None:
    journal_path, authority, state1, _pin1 = _seed_single_poll_journal(tmp_path)
    valid_payload = encode_state(state1, authority)

    cases: list[tuple[str, bytes]] = [
        ("truncated", b'{"format": "gaia-upstream-weekly-named-journal",'),
        ("non-utf8", b"\xff\xfe\xfd"),
        ("json-array", b"[1, 2, 3]"),
        (
            "non-finite",
            b'{"format": "gaia-upstream-weekly-named-journal", "namespace": "named-v3", "journalVersion": 3, "revision": NaN}',
        ),
        (
            "duplicate-top-key",
            (
                '{"format": "' + JOURNAL_FORMAT + '", "namespace": "' + JOURNAL_NAMESPACE + '", '
                '"journalVersion": 3, "revision": 0, "revision": 0}'
            ).encode("utf-8"),
        ),
        (
            "digest-mismatch",
            json.dumps({**valid_payload, "revision": 99}, sort_keys=True).encode("utf-8"),
        ),
    ]

    for name, raw in cases:
        p = tmp_path / f"bad-{name}.json"
        p.write_bytes(raw)
        loaded = load_journal(p, authority, allow_bootstrap=True)
        assert loaded.status == STATUS_CORRUPT, f"{name} should be corrupt, got {loaded.status}"
        assert loaded.blocked is True
        assert loaded.state is None
        with pytest.raises(JournalBlockedError):
            save_journal(p, empty_state(), authority, allow_bootstrap=True)
        assert p.read_bytes() == raw

    # Directory and symlink paths are rejected as corrupt and never overwritten
    dir_path = tmp_path / "a-dir"
    dir_path.mkdir()
    assert load_journal(dir_path, authority, allow_bootstrap=True).status == STATUS_CORRUPT
    with pytest.raises(JournalBlockedError):
        save_journal(dir_path, empty_state(), authority, allow_bootstrap=True)

    link_path = tmp_path / "a-link.json"
    link_path.symlink_to(journal_path)
    assert load_journal(link_path, authority, allow_bootstrap=True).status == STATUS_CORRUPT
    with pytest.raises(JournalBlockedError):
        save_journal(link_path, empty_state(), authority, allow_bootstrap=True)


def _mutate_bool_as_int_revision(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["revision"] = True


def _mutate_bool_as_int_sighting(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["buckets"][0]["sightingCount"] = True


def _mutate_revision_mismatch(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["revision"] = 2


def _mutate_wrong_sibling_named_id(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    # Same repository (acme/shared-repo), wrong sibling namedId!
    p["buckets"][0]["namedId"] = "bob/suite-b"


def _mutate_wrong_repository(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["buckets"][0]["repository"] = "other/repo"


def _mutate_duplicate_bucket_scope(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["buckets"].append(copy.deepcopy(p["buckets"][0]))


def _mutate_missing_poll_ref(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["buckets"][0]["firstPollId"] = "missing-poll-id"


def _mutate_non_canonical_timestamp(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["lastObservedAt"] = "2026-11-10T06:00:00+00:00"
    p["seenPolls"][0]["observedAt"] = "2026-11-10T06:00:00+00:00"


def _mutate_pin_mismatch(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["buckets"][0]["rows"][0]["firstSeenPin"]["firstSeenVersion"] = "v9.9.9"


def _mutate_presence_contradicts_present_flag(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["buckets"][0]["rows"][0]["presence"] = PRESENCE_UNKNOWN


def _mutate_historical_only_with_timestamp(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["buckets"][0]["rows"][0]["historicalOnly"] = True
    p["buckets"][0]["rows"][0]["presentInLatest"] = False
    p["buckets"][0]["rows"][0]["presence"] = PRESENCE_UNKNOWN


def _mutate_vanished_without_timestamp(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["buckets"][0]["rows"][0]["presentInLatest"] = False
    p["buckets"][0]["rows"][0]["presence"] = PRESENCE_VANISHED
    p["buckets"][0]["rows"][0]["vanishedAt"] = None
    p["buckets"][0]["rows"][0]["vanishedPollId"] = None


def _mutate_finding_sha_mismatch(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["buckets"][0]["latestFindingSha256"] = "0" * 64


def _mutate_incomplete_seen_poll(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["seenPolls"][0]["complete"] = False


def _mutate_extra_top_key(p: dict[str, Any], _auth: dict[str, dict[str, Any]]) -> None:
    p["unexpectedField"] = "injected"


@pytest.mark.parametrize(
    "case_name,mutator",
    [
        ("bool_as_int_revision", _mutate_bool_as_int_revision),
        ("bool_as_int_sighting", _mutate_bool_as_int_sighting),
        ("revision_mismatch", _mutate_revision_mismatch),
        ("wrong_sibling_named_id", _mutate_wrong_sibling_named_id),
        ("wrong_repository", _mutate_wrong_repository),
        ("duplicate_bucket_scope", _mutate_duplicate_bucket_scope),
        ("missing_poll_ref", _mutate_missing_poll_ref),
        ("non_canonical_timestamp", _mutate_non_canonical_timestamp),
        ("pin_mismatch", _mutate_pin_mismatch),
        ("presence_contradicts_present_flag", _mutate_presence_contradicts_present_flag),
        ("historical_only_with_timestamp", _mutate_historical_only_with_timestamp),
        ("vanished_without_timestamp", _mutate_vanished_without_timestamp),
        ("finding_sha_mismatch", _mutate_finding_sha_mismatch),
        ("incomplete_seen_poll", _mutate_incomplete_seen_poll),
        ("extra_top_key", _mutate_extra_top_key),
    ],
)
def test_checksum_valid_semantic_contradictions_rejected(
    tmp_path: Path,
    case_name: str,
    mutator: Any,
) -> None:
    _path, authority, state1, _pin1 = _seed_single_poll_journal(tmp_path)
    payload = encode_state(state1, authority)
    mutator(payload, authority)
    resigned_bytes = _resign(payload).encode("utf-8")

    bad_path = tmp_path / f"contradiction-{case_name}.json"
    bad_path.write_bytes(resigned_bytes)

    loaded = load_journal(bad_path, authority, allow_bootstrap=True)
    assert loaded.status == STATUS_CORRUPT, f"{case_name}: expected corrupt, got {loaded.status} ({loaded.detail})"
    assert loaded.blocked is True
    assert loaded.state is None

    with pytest.raises(JournalBlockedError):
        save_journal(bad_path, empty_state(), authority, allow_bootstrap=True)
    assert bad_path.read_bytes() == resigned_bytes


# ---------------------------------------------------------------------------
# 6. Bounded file size & reducer resource caps
# ---------------------------------------------------------------------------


def test_max_bytes_bounds_load_and_save_without_overwriting(tmp_path: Path) -> None:
    journal_path, authority, state1, pin1 = _seed_single_poll_journal(tmp_path)
    bytes_v1 = journal_path.read_bytes()

    oversized_load = load_journal(journal_path, authority, max_bytes=len(bytes_v1) - 1)
    assert oversized_load.status == STATUS_CORRUPT
    assert oversized_load.blocked is True
    assert oversized_load.state is None

    with pytest.raises(JournalSizeError):
        save_journal(journal_path, state1, authority, expected_pin=pin1, max_bytes=64)
    assert journal_path.read_bytes() == bytes_v1
    assert [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_reducer_resource_caps_enforced_on_load(tmp_path: Path) -> None:
    journal_path, authority, state1, _pin1 = _seed_single_poll_journal(tmp_path)

    # state1 has 2 rows in alice/suite-a
    tight_rows = ReducerConfig(max_rows_per_bucket=1)
    loaded_rows = load_journal(journal_path, authority, config=tight_rows)
    assert loaded_rows.status == STATUS_CORRUPT
    assert loaded_rows.blocked is True

    tight_total = ReducerConfig(max_total_rows=1)
    loaded_total = load_journal(journal_path, authority, config=tight_total)
    assert loaded_total.status == STATUS_CORRUPT
    assert loaded_total.blocked is True

    # Add a second bucket and verify max_buckets=1 and max_seen_polls=1 reject on load
    r2 = _plan_batch(
        [
            _raw_update(
                "carol/other-suite",
                "other/repo",
                "v1.0.0",
                adds=["carol-add"],
                component_root="skills",
            )
        ],
        authority,
    )
    p2 = poll_input_from_batch_report("poll-2", WED_NOV_11, r2)
    res2 = reduce_poll(state1, p2, authority)
    h2 = save_journal(journal_path, res2.state, authority, expected_pin=_pin1, poll=p2, initialized=True)
    assert h2.status == STATUS_OK

    assert load_journal(journal_path, authority, config=ReducerConfig(max_buckets=1)).status == STATUS_CORRUPT
    assert load_journal(journal_path, authority, config=ReducerConfig(max_seen_polls=1)).status == STATUS_CORRUPT

    # Decode directly also rejects tight caps
    payload2 = encode_state(res2.state, authority)
    with pytest.raises(Exception):
        decode_state(payload2, authority, config=ReducerConfig(max_buckets=1))
