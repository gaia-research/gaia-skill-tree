"""The bounded Class B rolling maintenance lane (Steward V1.4).

V1.2 could render one packet. V1.3 could judge one patch. Neither could answer
the question that actually decides whether maintenance keeps moving while the
founder is elsewhere:

    *What should be worked on next, how much may be outstanding at once, and
    what happens to work that keeps failing?*

That is this module. It is a small state machine over open Class B debt, and
almost all of its content is limits:

- **`maxInFlight`** — the lane never has more outstanding work than a human can
  actually review. Autonomy that outruns review is not autonomy, it is backlog.
- **`maxAttempts`** — a debt that fails bounded repair repeatedly is not asking
  for another attempt. It is telling you the envelope is wrong, which is a
  governance question, so the lane stops retrying and escalates.
- **`cooldownSeconds`** — a just-rejected debt is not immediately re-dispatchable,
  so a broken loop cannot spend an afternoon rediscovering the same rejection.

Escalation has somewhere to land: an escalated entry leaves the agent lane and
enters the founder queue. That is the permitted B → C downgrade, never the
reverse. Nothing here dispatches an agent, spends anything, or touches canonical
state; the lane records what happened and what may happen next.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence

from gaia_cli.steward.models import Debt, stable_json


LANE_SCHEMA = "steward-lane-v1"
LANE_ENTRY_SCHEMA = "steward-lane-entry-v1"

# `queued` and `dispatched` are live; `escalated` and `closed` are terminal for
# the agent lane. There is no `accepted` state: acceptance closes an entry, and
# a closed entry records why.
LANE_STATES = ("queued", "dispatched", "escalated", "closed")
LIVE_STATES = ("queued", "dispatched")

# What a verification verdict does to a lane entry. `accept` is absent on
# purpose: Steward never produces one (see verification.py), so it can only
# arrive through an explicit human record.
VERDICT_EFFECTS = {
    "pending": "awaiting independent judgment",
    "reject": "returned for another bounded attempt",
    "escalate": "left the agent lane for the founder queue",
}


class LaneError(RuntimeError):
    """A lane transition was refused; no state changed."""


def _parse(timestamp: str) -> datetime:
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LaneError(f"unparseable lane timestamp: {timestamp!r}") from exc


@dataclass(frozen=True)
class LaneTransition:
    at: str
    from_state: str
    to_state: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "at": self.at,
            "from": self.from_state,
            "to": self.to_state,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LaneTransition":
        return cls(
            at=str(data["at"]),
            from_state=str(data["from"]),
            to_state=str(data["to"]),
            reason=str(data["reason"]),
        )


@dataclass(frozen=True)
class LaneEntry:
    """One Class B debt's position in the rolling lane."""

    debt_id: str
    rule: str
    state: str
    attempts: int
    priority: float
    first_queued_at: str
    last_transition_at: str
    last_verdict: str | None
    history: tuple[LaneTransition, ...]

    def __post_init__(self) -> None:
        if self.state not in LANE_STATES:
            raise LaneError(f"unknown lane state: {self.state}")
        if self.attempts < 0:
            raise LaneError("lane attempts may not be negative")

    @property
    def live(self) -> bool:
        return self.state in LIVE_STATES

    def moved(self, *, to: str, at: str, reason: str, **changes: Any) -> "LaneEntry":
        """Return this entry in a new state, with the move recorded.

        Every transition appends to `history`. A lane that could change state
        without saying why would be a worse audit record than no lane at all.
        """

        return replace(
            self,
            state=to,
            last_transition_at=at,
            history=self.history
            + (LaneTransition(at=at, from_state=self.state, to_state=to, reason=reason),),
            **changes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": LANE_ENTRY_SCHEMA,
            "debtId": self.debt_id,
            "rule": self.rule,
            "state": self.state,
            "attempts": self.attempts,
            "priority": self.priority,
            "firstQueuedAt": self.first_queued_at,
            "lastTransitionAt": self.last_transition_at,
            "lastVerdict": self.last_verdict,
            "history": [item.to_dict() for item in self.history],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LaneEntry":
        if data.get("schemaVersion") != LANE_ENTRY_SCHEMA:
            raise LaneError("unsupported lane entry schemaVersion")
        return cls(
            debt_id=str(data["debtId"]),
            rule=str(data["rule"]),
            state=str(data["state"]),
            attempts=int(data["attempts"]),
            priority=float(data["priority"]),
            first_queued_at=str(data["firstQueuedAt"]),
            last_transition_at=str(data["lastTransitionAt"]),
            last_verdict=data["lastVerdict"] if data.get("lastVerdict") is None else str(data["lastVerdict"]),
            history=tuple(LaneTransition.from_dict(item) for item in data["history"]),
        )


@dataclass(frozen=True)
class LanePolicy:
    """The three numbers that make the lane bounded rather than a loop."""

    max_in_flight: int
    max_attempts: int
    cooldown_seconds: int

    def to_dict(self) -> dict[str, int]:
        return {
            "maxInFlight": self.max_in_flight,
            "maxAttempts": self.max_attempts,
            "cooldownSeconds": self.cooldown_seconds,
        }


@dataclass(frozen=True)
class Lane:
    """The whole lane: every tracked entry, plus the bounds it runs under."""

    entries: tuple[LaneEntry, ...]
    policy: LanePolicy

    def by_id(self, debt_id: str) -> LaneEntry | None:
        return next((entry for entry in self.entries if entry.debt_id == debt_id), None)

    @property
    def in_flight(self) -> tuple[LaneEntry, ...]:
        return tuple(entry for entry in self.entries if entry.state == "dispatched")

    @property
    def queued(self) -> tuple[LaneEntry, ...]:
        return tuple(entry for entry in self.entries if entry.state == "queued")

    @property
    def escalated(self) -> tuple[LaneEntry, ...]:
        return tuple(entry for entry in self.entries if entry.state == "escalated")

    def replaced(self, entry: LaneEntry) -> "Lane":
        others = tuple(item for item in self.entries if item.debt_id != entry.debt_id)
        return Lane(entries=_ordered(others + (entry,)), policy=self.policy)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": LANE_SCHEMA,
            "policy": self.policy.to_dict(),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def summary(self) -> dict[str, Any]:
        counts = {state: sum(1 for entry in self.entries if entry.state == state) for state in LANE_STATES}
        return {
            "policy": self.policy.to_dict(),
            "counts": counts,
            "inFlight": [entry.debt_id for entry in self.in_flight],
            "escalated": [entry.debt_id for entry in self.escalated],
            "capacity": max(0, self.policy.max_in_flight - len(self.in_flight)),
        }


def _ordered(entries: Iterable[LaneEntry]) -> tuple[LaneEntry, ...]:
    return tuple(sorted(entries, key=lambda item: item.debt_id))


def load_lane(data: Mapping[str, Any] | None, policy: LanePolicy) -> Lane:
    """Rebuild the lane from ignored local state, or start an empty one.

    The bounds always come from current policy, never from the stored file: a
    lane that carried its own limits could keep running under a ceiling the
    founder had already lowered.
    """

    if data is None:
        return Lane(entries=(), policy=policy)
    if not isinstance(data, dict) or data.get("schemaVersion") != LANE_SCHEMA:
        raise LaneError("unsupported Steward lane state")
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list):
        raise LaneError("Steward lane entries must be a list")
    entries = tuple(LaneEntry.from_dict(item) for item in raw_entries)
    if len({entry.debt_id for entry in entries}) != len(entries):
        raise LaneError("duplicate debt id in Steward lane state")
    return Lane(entries=_ordered(entries), policy=policy)


def reconcile(
    lane: Lane,
    *,
    open_debts: Sequence[Debt],
    dispatchable_kinds: Mapping[str, str],
    now: str,
) -> Lane:
    """Bring the lane into agreement with what a fresh scan actually observed.

    Two directions, both mechanical. Newly observed dispatchable debt enters as
    `queued`. Debt that is no longer observed leaves as `closed` — including
    debt that was in flight, because a finding that stopped reproducing while an
    agent worked on it is resolved whether or not the agent is what resolved it.
    An escalated entry is deliberately *not* reopened by a fresh observation:
    it is waiting on a founder, and re-queueing it would loop around the very
    decision it escalated for.
    """

    observed = {
        debt.id: debt
        for debt in open_debts
        if debt.kind in dispatchable_kinds
    }
    result = lane
    for debt_id, debt in sorted(observed.items()):
        existing = result.by_id(debt_id)
        if existing is None:
            result = result.replaced(
                LaneEntry(
                    debt_id=debt_id,
                    rule=dispatchable_kinds[debt.kind],
                    state="queued",
                    attempts=0,
                    priority=debt.priority.score,
                    first_queued_at=now,
                    last_transition_at=now,
                    last_verdict=None,
                    history=(
                        LaneTransition(at=now, from_state="none", to_state="queued", reason="observed by a sensor"),
                    ),
                )
            )
        elif existing.state == "closed":
            # The same condition came back. That is a fresh attempt, not a
            # continuation, so the attempt count starts over.
            result = result.replaced(
                existing.moved(
                    to="queued",
                    at=now,
                    reason="condition observed again after closing",
                    attempts=0,
                    last_verdict=None,
                    priority=debt.priority.score,
                )
            )
        elif existing.priority != debt.priority.score:
            result = result.replaced(replace(existing, priority=debt.priority.score))

    for entry in result.entries:
        if entry.debt_id not in observed and entry.live:
            result = result.replaced(
                entry.moved(
                    to="closed",
                    at=now,
                    reason="the condition is no longer observed",
                )
            )
    return result


def next_dispatchable(lane: Lane, *, now: str) -> tuple[LaneEntry | None, str]:
    """Select the next entry the lane may hand out, or say why it may not.

    Returns the reason alongside the choice, because "nothing to do" and "at
    capacity" and "still cooling down" are three different states of health and
    a lane that reported them identically would hide a stall.
    """

    capacity = lane.policy.max_in_flight - len(lane.in_flight)
    if capacity <= 0:
        return None, (
            f"{len(lane.in_flight)} dispatch(es) already in flight, at the "
            f"maxInFlight ceiling of {lane.policy.max_in_flight}"
        )
    queued = lane.queued
    if not queued:
        return None, "no queued Class B debt"

    moment = _parse(now)
    ready: list[LaneEntry] = []
    cooling: list[LaneEntry] = []
    for entry in queued:
        cooldown = timedelta(seconds=lane.policy.cooldown_seconds)
        if entry.attempts > 0 and _parse(entry.last_transition_at) + cooldown > moment:
            cooling.append(entry)
        else:
            ready.append(entry)
    if not ready:
        return None, (
            f"{len(cooling)} queued debt(s) are still inside the "
            f"{lane.policy.cooldown_seconds}s cooldown after a rejected attempt"
        )
    # Highest expected maintenance value first; debt id breaks ties so the
    # selection is reproducible from the same state.
    chosen = min(ready, key=lambda item: (-item.priority, item.debt_id))
    return chosen, "selected by priority"


def mark_dispatched(lane: Lane, entry: LaneEntry, *, dispatch_id: str, now: str) -> Lane:
    if entry.state != "queued":
        raise LaneError(f"only queued debt may be dispatched; {entry.debt_id} is {entry.state}")
    if len(lane.in_flight) >= lane.policy.max_in_flight:
        raise LaneError("the lane is at its maxInFlight ceiling")
    return lane.replaced(
        entry.moved(
            to="dispatched",
            at=now,
            reason=f"handed out as {dispatch_id}",
            attempts=entry.attempts + 1,
            last_verdict=None,
        )
    )


def record_verdict(lane: Lane, debt_id: str, verdict: str, *, now: str, note: str = "") -> Lane:
    """Advance one entry on the strength of a verification verdict.

    ``pending`` is not a state change. Machinery finding nothing wrong is not
    progress through the lane — the work is still outstanding until somebody
    judges it — so the entry stays dispatched and only its `lastVerdict` moves.
    """

    entry = lane.by_id(debt_id)
    if entry is None:
        return lane
    if entry.state != "dispatched":
        raise LaneError(
            f"only dispatched debt may take a verdict; {debt_id} is {entry.state}"
        )
    suffix = f" ({note})" if note else ""

    if verdict == "pending":
        return lane.replaced(
            replace(entry, last_verdict="pending", last_transition_at=now)
        )
    if verdict == "escalate":
        return lane.replaced(
            entry.moved(
                to="escalated",
                at=now,
                reason=f"verification escalated{suffix}",
                last_verdict="escalate",
            )
        )
    if verdict == "reject":
        # The anti-loop rule. A debt that keeps failing bounded repair is not
        # asking for a bigger reasoner; it is evidence that the envelope, not
        # the attempt, is wrong — and that is a founder question.
        if entry.attempts >= lane.policy.max_attempts:
            return lane.replaced(
                entry.moved(
                    to="escalated",
                    at=now,
                    reason=(
                        f"rejected on attempt {entry.attempts} of a "
                        f"{lane.policy.max_attempts}-attempt ceiling; the envelope "
                        f"is the likelier defect{suffix}"
                    ),
                    last_verdict="reject",
                )
            )
        return lane.replaced(
            entry.moved(
                to="queued",
                at=now,
                reason=f"rejected on attempt {entry.attempts}; returned to the queue{suffix}",
                last_verdict="reject",
            )
        )
    if verdict == "accept":
        return lane.replaced(
            entry.moved(
                to="closed",
                at=now,
                reason=f"accepted by independent verification{suffix}",
                last_verdict="accept",
            )
        )
    raise LaneError(f"unknown verification verdict: {verdict}")


def lane_document(lane: Lane) -> dict[str, Any]:
    document = lane.to_dict()
    stable_json(document)
    return document


def utc_now_string() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
