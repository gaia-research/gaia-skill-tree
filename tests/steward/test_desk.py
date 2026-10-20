"""The founder desk: decisions for a person, operations for the machinery."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from gaia_cli.steward.desk import (
    DECISION_RECORD_SCHEMA,
    QUIET_LINE,
    Desk,
    DeskDecision,
    DeskOperation,
    build_desk,
    load_decision_records,
    render_desk,
)
from gaia_cli.steward.lane import Lane, LanePolicy, LaneEntry, LaneTransition
from gaia_cli.steward.models import (
    AuthorityClass,
    Debt,
    FounderDecision,
    FounderQueue,
    Priority,
    Subject,
)
from gaia_cli.steward.routing import LANE_ESCALATION_OBJECTIVE, LANE_ESCALATION_RULE


NOW = "2026-10-20T12:00:00Z"
RECENT = "2026-10-20T06:00:00Z"
LANE_POLICY = LanePolicy(max_in_flight=1, max_attempts=2, cooldown_seconds=3600)
SECRET = "AKIAIOSFODNN7EXAMPLE"
SECRET_TOKEN = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"


def _debt(
    kind: str,
    subject: str,
    authority: AuthorityClass = AuthorityClass.C,
    observed: dict | None = None,
    status: str = "open",
) -> Debt:
    return Debt(
        id=f"debt:{kind}:{subject}",
        kind=kind,
        subject=Subject("repository-surface", subject),
        source="fixture",
        current_state={},
        observed_state=observed or {},
        confidence=1.0,
        priority=Priority(1.0, 1.0, 1.0, 1.0, 0.1, 1.0),
        authority=authority,
        status=status,
        first_observed_at="2026-10-01T00:00:00Z",
        last_observed_at=NOW,
        observation_count=3,
    )


def _entry(debt_id: str, rule: str = "doc-drift", state: str = "queued", attempts: int = 0) -> LaneEntry:
    return LaneEntry(
        debt_id=debt_id, rule=rule, state=state, attempts=attempts, priority=1.0,
        first_queued_at="2026-10-01T00:00:00Z", last_transition_at=NOW, last_verdict=None,
        history=(LaneTransition(NOW, "dispatched", state, f"rejected on attempt {attempts}"),),
    )


def _lane(*entries: LaneEntry) -> Lane:
    return Lane(entries=tuple(sorted(entries, key=lambda item: item.debt_id)), policy=LANE_POLICY)


def _queue_decision(rule: str, target: str, debts: list[Debt], objective: str = "Decide the mapping.") -> FounderDecision:
    return FounderDecision.create(
        rule=rule, decision_target=target, objective=objective,
        debt_ids=tuple(item.id for item in debts),
        evidence=tuple(
            {
                "debtId": item.id, "source": item.source, "subject": item.subject.to_dict(),
                "observedState": dict(item.observed_state), "confidence": 1.0,
            }
            for item in sorted(debts, key=lambda d: d.id)
        ),
    )


def _desk(**overrides) -> Desk:
    arguments = dict(
        open_debts=(), founder_queue=FounderQueue.create(()), lane=_lane(),
        coverage_unknown=(), not_evaluated=(), decision_records=(),
        ledger_shared=True, last_scheduled_run_at=RECENT, now=NOW,
    )
    arguments.update(overrides)
    return build_desk(**arguments)


def _record(identifier: str = "ship-gate", **overrides) -> dict:
    record = {
        "schemaVersion": DECISION_RECORD_SCHEMA, "id": identifier, "status": "open",
        "decision": "Should the ship gate block on a red advisory?",
        "whyItMatters": "A red advisory today ships silently.",
        "evidence": ["advisory run 41", "two incidents last month"],
        "recommended": "Block, with a label override.",
        "alternative": "Warn only.",
        "unblocks": "The release workflow rewrite.",
        "links": ["https://example.test/issues/9"],
        "_source": f"founder/steward/decisions/{identifier}.json",
    }
    record.update(overrides)
    return record


# --- quiet --------------------------------------------------------------------


def test_a_clean_run_is_exactly_one_line() -> None:
    desk = _desk()
    assert desk.quiet() is True
    assert render_desk(desk) == QUIET_LINE == "Gaia Steward: nothing needs you."
    payload = desk.to_dict()
    assert payload["quiet"] is True and payload["decisions"] == [] and payload["operations"] == []


def test_closed_and_non_class_c_debt_do_not_wake_the_desk() -> None:
    desk = _desk(open_debts=(
        _debt("registry_integrity_failed", "r", AuthorityClass.B),
        _debt("agent_skill_mirror_drift", "m", AuthorityClass.A),
        _debt("credential_leak", "resolved.py", status="resolved"),
    ))
    assert desk.quiet()


# --- decision sources -----------------------------------------------------------


def test_founder_queue_decisions_are_reused_one_to_one_without_regrouping() -> None:
    a1 = _debt("generic_mapping", "cand-a1", observed={"decisionTarget": "alpha"})
    a2 = _debt("generic_mapping", "cand-a2", observed={"decisionTarget": "alpha"})
    b1 = _debt("generic_mapping", "cand-b1", observed={"decisionTarget": "beta"})
    first = _queue_decision("generic-mapping-decision", "alpha", [a1, a2])
    second = _queue_decision("generic-mapping-decision", "beta", [b1])
    queue = FounderQueue.create((first, second))

    desk = _desk(open_debts=(a1, a2, b1), founder_queue=queue)

    assert {item.decision_id for item in desk.decisions} == {first.decision_id, second.decision_id}
    by_id = {item.decision_id: item for item in desk.decisions}
    assert by_id[first.decision_id].debt_ids == tuple(sorted((a1.id, a2.id)))
    assert by_id[first.decision_id].decision == "Decide the mapping."
    assert by_id[first.decision_id].source == "class-c-debt"
    assert len(by_id[first.decision_id].evidence) == 2
    assert by_id[second.decision_id].debt_ids == (b1.id,)
    # Queue debt is not duplicated by the by-kind pass.
    assert len(desk.decisions) == 2


def test_other_open_class_c_debt_is_grouped_by_kind() -> None:
    stamps = [_debt("trust_stamp_stale", name) for name in ("skill-a", "skill-b")]
    unknown = [_debt("novel_governance_kind", "thing")]
    desk = _desk(open_debts=(*stamps, *unknown))

    by_kind = {item.debt_ids[0].split(":")[1]: item for item in desk.decisions}
    assert set(by_kind) == {"trust_stamp_stale", "novel_governance_kind"}
    stamp = by_kind["trust_stamp_stale"]
    assert stamp.debt_ids == tuple(sorted(item.id for item in stamps))
    assert "https://github.com/gaia-research/gaia-skill-tree/issues/1642" in stamp.links
    assert "refresh" in stamp.decision.lower()
    generic = by_kind["novel_governance_kind"]
    assert "novel_governance_kind" in generic.decision
    assert generic.recommended.startswith("None")
    assert generic.source == "class-c-debt"


def test_credential_decision_shows_location_and_fingerprint_but_never_the_secret() -> None:
    debt = _debt(
        "credential_leak", "scripts/deploy.sh",
        observed={
            "findingCount": 1,
            "findings": [{
                "line": 12, "fingerprint": "0123456789abcdef0123", "rule": "aws-key",
                "match": SECRET, "snippet": f"export KEY={SECRET}", "value": SECRET_TOKEN,
            }],
            "rawMatch": SECRET, "token": SECRET_TOKEN, "findingsCapped": False,
        },
    )
    desk = _desk(open_debts=(debt,))
    (decision,) = desk.decisions
    assert decision.priority == 0
    assert any("scripts/deploy.sh" in row and "line 12" in row and "0123456789ab" in row for row in decision.evidence)
    assert "scripts/deploy.sh#L12" in decision.links
    assert "rotate" in decision.decision.lower() or "rotate" in decision.recommended.lower()

    rendered = render_desk(desk) + json.dumps(desk.to_dict())
    for secret in (SECRET, SECRET_TOKEN, "0123456789abcdef0123"):
        assert secret not in rendered


def test_credential_subject_ids_that_look_like_secrets_are_scrubbed() -> None:
    long_secret = "sk-" + "a1B2c3D4" * 6
    debt = _debt("credential_leak", f"config/{long_secret}.env", observed={"findingCount": 1})
    rendered = render_desk(_desk(open_debts=(debt,)))
    assert long_secret not in rendered
    assert "[redacted]" in rendered


def test_escalated_lane_entries_become_an_envelope_decision() -> None:
    debt = _debt("doc_drift", "docs/a.md", AuthorityClass.B)
    desk = _desk(
        open_debts=(debt,),
        lane=_lane(_entry(debt.id, state="escalated", attempts=2)),
    )
    (decision,) = desk.decisions
    assert decision.source == "escalated-lane"
    assert decision.debt_ids == (debt.id,)
    assert decision.decision == LANE_ESCALATION_OBJECTIVE
    assert "envelope" in decision.recommended
    assert "attempt" in decision.evidence[0] or "rejected" in decision.evidence[0]


def test_queue_escalation_and_lane_escalation_merge_into_one_group() -> None:
    queued = _debt("doc_drift", "docs/a.md", AuthorityClass.B)
    lane_only = _debt("doc_drift", "docs/b.md", AuthorityClass.B)
    queue = FounderQueue.create((
        _queue_decision(LANE_ESCALATION_RULE, "lane-escalation/doc-drift", [queued], LANE_ESCALATION_OBJECTIVE),
    ))
    desk = _desk(
        open_debts=(queued, lane_only),
        founder_queue=queue,
        lane=_lane(
            _entry(queued.id, "doc-drift", "escalated", 2),
            _entry(lane_only.id, "doc-drift", "escalated", 2),
        ),
    )
    (decision,) = desk.decisions
    assert decision.source == "escalated-lane"
    assert decision.debt_ids == tuple(sorted((queued.id, lane_only.id)))
    assert decision.decision_id == queue.decisions[0].decision_id


def test_an_escalated_entry_whose_debt_is_no_longer_open_is_not_a_decision() -> None:
    desk = _desk(lane=_lane(_entry("debt:gone", state="escalated", attempts=2)))
    assert desk.decisions == ()
    assert desk.quiet()


def test_open_decision_records_appear_and_decided_ones_do_not() -> None:
    desk = _desk(decision_records=(
        _record("ship-gate"),
        _record("old-ruling", status="decided"),
    ))
    (decision,) = desk.decisions
    assert decision.decision_id == "ship-gate"
    assert decision.source == "decision-record"
    assert decision.links == ("https://example.test/issues/9",)
    assert decision.evidence == ("advisory run 41", "two incidents last month")
    assert decision.debt_ids == ()
    assert desk.operations == ()


# --- malformed decision records -------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        {"_source": "founder/steward/decisions/x.json", "_error": "unreadable: boom"},
        _record("missing", **{}) | {"decision": ""},
        {k: v for k, v in _record("nokeys").items() if k != "recommended"},
        _record("extra") | {"surprise": 1},
        _record("wrongschema") | {"schemaVersion": "v0"},
        _record("badstatus") | {"status": "pending"},
        _record("mismatch") | {"_source": "founder/steward/decisions/other.json"},
        _record("badevidence") | {"evidence": "not-a-list"},
        _record("BAD_ID"),
    ],
)
def test_malformed_records_become_operations_and_never_decisions(bad: dict) -> None:
    desk = _desk(decision_records=(bad,))
    assert desk.decisions == ()
    (operation,) = desk.operations
    assert operation.kind == "invalid_decision_record"
    assert operation.subject.startswith("founder/steward/decisions/")
    assert not desk.quiet()


def test_a_duplicate_record_id_is_flagged_not_silently_dropped() -> None:
    first = _record("dup")
    second = _record("dup") | {"_source": "founder/steward/decisions/dup.json"}
    desk = _desk(decision_records=(first, second))
    assert [item.decision_id for item in desk.decisions] == ["dup"]
    assert [op.kind for op in desk.operations] == ["invalid_decision_record"]


def test_load_decision_records_reads_valid_and_reports_broken_files(tmp_path: Path) -> None:
    directory = tmp_path / "founder/steward/decisions"
    directory.mkdir(parents=True)
    good = {k: v for k, v in _record("ship-gate").items() if not k.startswith("_")}
    (directory / "ship-gate.json").write_text(json.dumps(good), encoding="utf-8")
    (directory / "broken.json").write_text("{not json", encoding="utf-8")
    (directory / "list.json").write_text("[1,2]", encoding="utf-8")
    (directory / "binary.json").write_bytes(b"\xff\xfe\x00")
    (directory / "README.md").write_text("ignored", encoding="utf-8")

    records = load_decision_records(tmp_path)

    assert [item["_source"] for item in records] == [
        "founder/steward/decisions/binary.json",
        "founder/steward/decisions/broken.json",
        "founder/steward/decisions/list.json",
        "founder/steward/decisions/ship-gate.json",
    ]
    desk = _desk(decision_records=records)
    assert [item.decision_id for item in desk.decisions] == ["ship-gate"]
    assert sorted(op.subject.rsplit("/", 1)[-1] for op in desk.operations) == [
        "binary.json", "broken.json", "list.json",
    ]


def test_load_decision_records_with_no_directory_is_empty(tmp_path: Path) -> None:
    assert load_decision_records(tmp_path) == ()


# --- operations -----------------------------------------------------------------------


def test_operations_cover_every_failure_the_machinery_can_have() -> None:
    live = _entry("debt:stuck", "doc-drift", "dispatched", 2)
    desk = _desk(
        lane=_lane(live),
        coverage_unknown=("ci-health", "dead-code"),
        not_evaluated=({"sensor": "dependency-advisory", "reason": "advisory feed not supplied"},),
        failed_dispatches=({"subject": "debt:x", "detail": "builder crashed"},),
        ledger_shared=False,
        last_scheduled_run_at=None,
    )
    kinds = [op.kind for op in desk.operations]
    assert kinds == [
        "coverage_unknown", "coverage_unknown", "not_evaluated", "exhausted_attempts",
        "failed_dispatch", "stale_schedule", "ledger_local_only",
    ]
    assert desk.decisions == ()
    text = " ".join(render_desk(desk).split())
    assert "advisory feed not supplied" in text
    assert "ci-health" in text and "dead-code" in text
    assert "no scheduled run has ever been recorded" in text
    assert "local file" in text
    assert "builder crashed" in text
    assert "2 of 2 attempts" in text


@pytest.mark.parametrize(
    ("last", "stale"),
    [
        (None, True),
        ("2026-10-20T06:00:00Z", False),
        ("2026-10-18T12:00:00Z", False),     # exactly 48h: not yet stale
        ("2026-10-18T11:59:00Z", True),
        ("2026-10-01T00:00:00+00:00", True),
        ("garbage", True),
    ],
)
def test_stale_schedule_threshold(last: str | None, stale: bool) -> None:
    desk = _desk(last_scheduled_run_at=last)
    assert any(op.kind == "stale_schedule" for op in desk.operations) is stale


def test_stale_after_hours_is_configurable() -> None:
    assert not _desk(last_scheduled_run_at="2026-10-18T00:00:00Z", stale_after_hours=72).operations
    assert _desk(last_scheduled_run_at="2026-10-18T00:00:00Z", stale_after_hours=24).operations


def test_operations_never_masquerade_as_decisions() -> None:
    desk = _desk(coverage_unknown=("dead-code",), ledger_shared=False)
    assert desk.decisions == ()
    text = render_desk(desk)
    assert "NEEDS YOUR DECISION (0)" in text
    assert "OPERATIONS (2)" in text


def test_unknown_kinds_and_sources_are_rejected() -> None:
    with pytest.raises(ValueError):
        DeskOperation("whatever", "s", "d")
    with pytest.raises(ValueError):
        DeskDecision("i", "d", "w", (), "r", "a", "u", (), (), "somewhere")


# --- determinism and ordering ---------------------------------------------------------------


def _busy_inputs() -> dict:
    debts = [
        _debt("trust_stamp_stale", "skill-a"),
        _debt("trust_stamp_stale", "skill-b"),
        _debt("credential_leak", "a.env", observed={"findingCount": 1}),
        _debt("novel_kind", "n1"),
        _debt("doc_drift", "docs/a.md", AuthorityClass.B),
    ]
    return dict(
        open_debts=debts,
        lane=_lane(_entry(debts[-1].id, "doc-drift", "escalated", 2)),
        coverage_unknown=["b-sensor", "a-sensor"],
        not_evaluated=[{"sensor": "z", "reason": "r1"}, {"sensor": "y", "reason": "r2"}],
        decision_records=[_record("rec-b"), _record("rec-a")],
        ledger_shared=False,
        last_scheduled_run_at=None,
    )


def test_identical_inputs_render_identically_regardless_of_input_order() -> None:
    inputs = _busy_inputs()
    baseline = render_desk(_desk(**inputs))
    assert render_desk(_desk(**inputs)) == baseline
    rng = random.Random(7)
    for _ in range(5):
        shuffled = {
            key: (rng.sample(list(value), len(value)) if isinstance(value, (list, tuple)) else value)
            for key, value in inputs.items()
        }
        assert render_desk(_desk(**shuffled)) == baseline
    assert json.dumps(_desk(**inputs).to_dict(), sort_keys=True) == json.dumps(
        _desk(**inputs).to_dict(), sort_keys=True
    )


def test_decisions_sort_by_priority_then_id() -> None:
    desk = _desk(**_busy_inputs())
    sources = [(item.priority, item.source) for item in desk.decisions]
    assert sources == sorted(sources, key=lambda pair: pair[0])
    assert desk.decisions[0].debt_ids[0].startswith("debt:credential_leak")
    assert desk.decisions[1].source == "escalated-lane"
    assert [item.decision_id for item in desk.decisions if item.source == "decision-record"] == ["rec-a", "rec-b"]
    last_priority = None
    ids: list[str] = []
    for item in desk.decisions:
        if item.priority != last_priority:
            assert ids == sorted(ids)
            ids, last_priority = [], item.priority
        ids.append(item.decision_id)
    assert ids == sorted(ids)


# --- render shape ---------------------------------------------------------------------------


def test_render_carries_every_field_and_separates_the_two_sections() -> None:
    text = render_desk(_desk(**_busy_inputs()))
    assert text.index("NEEDS YOUR DECISION") < text.index("OPERATIONS")
    for label in ("Decision:", "Why it matters:", "Evidence:", "Recommended:", "Alternative:", "Unblocks:", "Link:"):
        assert label in text
    decisions_part, operations_part = text.split("OPERATIONS", 1)
    assert "[coverage_unknown]" in operations_part and "[coverage_unknown]" not in decisions_part
    assert "Should the ship gate block" in decisions_part
    assert all(len(line) <= 90 for line in text.splitlines())
    assert text.isascii()
    assert text.endswith("\n")


def test_to_dict_is_json_serialisable_and_complete() -> None:
    payload = _desk(**_busy_inputs()).to_dict()
    json.dumps(payload)
    assert payload["schemaVersion"] == "steward-desk-v1"
    assert payload["quiet"] is False
    first = payload["decisions"][0]
    assert {"decisionId", "decision", "whyItMatters", "evidence", "recommended", "alternative",
            "unblocks", "links", "debtIds", "source"} <= set(first)
