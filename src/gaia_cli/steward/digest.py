"""The founder digest (Steward V1.5).

`gaia steward founder` already knew *which* Class C matters were open. This
module decides how to spend the one resource the whole system exists to protect:

    the founder's attention.

The operating model (§ 12) is blunt about what bad looks like — seventeen issues,
eight workflow failures, four PR comments, three bot reports — and about what
good looks like: one decision, stated once, with what it unblocks and what each
answer costs. This renders the second.

Three rules shape everything below.

**Report by exception.** A digest that summarises a healthy repository at length
trains its reader to stop opening it. If nothing needs a decision, the digest
says one line and stops.

**Recommend only what is derivable.** Some Class C questions have a mechanically
obvious answer — bounded repair failed twice under one envelope, so the envelope
is the likelier defect. Most do not. Where Steward has no basis, it says so
rather than producing a confident-sounding sentence, because a recommendation
nobody can trace is worse than none.

**Blindness is louder than debt.** Open debt is information and is fine. A sensor
that could not run means Steward does not know what is true, and it fails closed
until someone fixes it. That goes at the top, above everything else.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from gaia_cli.steward.controller import ScanResult
from gaia_cli.steward.lane import Lane
from gaia_cli.steward.models import AuthorityClass, Debt, FounderDecision, FounderQueue


DIGEST_SCHEMA = "steward-founder-digest-v1"

# Rendered next to each decision so the founder can refer to one out loud.
# Derived from the decision's stable semantic hash rather than its position in
# the list: a positional C-001..C-00N would renumber every remaining decision
# the moment one was resolved, and a label that moves is not a label.
_LABEL_PREFIX = "C-"
_LABEL_LENGTH = 4

# Evidence keys that are never the decision — they are how the observation was
# made, not what is being asked.
_UNINTERESTING = frozenset({"input", "inputDigest", "digest", "decisionTarget"})
_MAX_EVIDENCE_ROWS = 5
_MAX_VALUE_CHARS = 96


def _parse(timestamp: str) -> datetime | None:
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age(first_seen: str, now: str) -> str:
    start, end = _parse(first_seen), _parse(now)
    if start is None or end is None:
        return "unknown"
    delta = end - start
    if delta.days >= 1:
        return f"{delta.days}d"
    hours = int(delta.total_seconds() // 3600)
    if hours >= 1:
        return f"{hours}h"
    return f"{max(0, int(delta.total_seconds() // 60))}m"


def decision_labels(decisions: Sequence[FounderDecision]) -> dict[str, str]:
    """Assign each decision a short, stable, collision-free display label.

    The label is a prefix of the decision's own identity hash, so it survives
    other decisions arriving and being resolved. Length grows only far enough
    to keep the set unambiguous, and grows for *every* label at once so two
    printings of the same queue never disagree about how long a label is.
    """

    ordered = sorted(decisions, key=lambda item: item.decision_id)
    digests = {item.decision_id: item.decision_id.rsplit("-", 1)[-1] for item in ordered}
    length = _LABEL_LENGTH
    while length < 40:
        labels = {key: value[:length] for key, value in digests.items()}
        if len(set(labels.values())) == len(labels):
            return {key: f"{_LABEL_PREFIX}{value}" for key, value in labels.items()}
        length += 1
    return {key: f"{_LABEL_PREFIX}{value}" for key, value in digests.items()}


def _recommendation(decision: FounderDecision) -> str | None:
    """Return a recommendation only where one is mechanically derivable.

    Returning ``None`` is the common and correct case. Steward classifies and
    routes; it does not hold opinions about ontology, prestige, or product. A
    recommendation it cannot trace to a fact would be exactly the sort of
    confident-sounding filler that makes a digest stop being worth reading.
    """

    if decision.rule != "lane-escalation":
        return None
    routine = decision.decision_target.split("/", 1)[-1]
    return (
        f"Bounded repair under `{routine}` reached its attempt ceiling. The "
        "envelope is the likelier defect, not the attempt — the ceiling has "
        "already ruled out trying again under the same terms. The three "
        "answers worth weighing are: widen the envelope in `POLICY.yaml`, "
        "accept that this finding is a Class C question in disguise and rule "
        "on it directly, or retire the routine."
    )


def _evidence_lines(evidence: Mapping[str, Any]) -> list[str]:
    """Render one debt's evidence as a few short, decision-relevant lines."""

    subject = evidence.get("subject", {})
    lines = [f"  {subject.get('id', evidence.get('debtId', 'unknown'))}"]
    observed = evidence.get("observedState", {})
    if not isinstance(observed, Mapping):
        return lines
    rows = 0
    for key in sorted(observed):
        if key in _UNINTERESTING or rows >= _MAX_EVIDENCE_ROWS:
            continue
        value = observed[key]
        if isinstance(value, (dict, list)):
            rendered = f"{len(value)} item(s)"
        else:
            rendered = str(value)
        if len(rendered) > _MAX_VALUE_CHARS:
            rendered = rendered[: _MAX_VALUE_CHARS - 1] + "…"
        lines.append(f"    {key}: {rendered}")
        rows += 1
    return lines


def _health(scan: ScanResult, lane: Lane, decisions: int) -> list[str]:
    """The compact health view from the operating model, § 14."""

    open_debts = scan.open_debts
    counts = {
        authority.value: sum(1 for debt in open_debts if debt.authority is authority)
        for authority in AuthorityClass
    }
    sensor_total = scan.receipt.observations_collected
    unknown = scan.receipt.coverage_unknown
    oldest = _oldest(open_debts, scan.receipt.finished_at)
    lane_counts = lane.summary()["counts"]

    lines = [
        "  Sensor coverage          "
        + ("healthy" if not unknown else f"UNKNOWN — {', '.join(unknown)}"),
        f"  Observations             {sensor_total}",
        f"  Open debt                {len(open_debts)}"
        f"   (A {counts['A']}  B {counts['B']}  C {counts['C']})",
        f"  Oldest open debt         {oldest}",
        f"  Class B lane             {lane_counts['queued']} queued, "
        f"{lane_counts['dispatched']} in flight, {lane_counts['escalated']} escalated",
        f"  Decisions for you        {decisions}",
    ]
    if unknown:
        lines.append(
            "\n  Steward is blind, not idle. It refuses to repair or dispatch\n"
            "  while a sensor cannot complete, so the Class A lane is paused\n"
            "  until this is fixed. Nothing below is a complete picture."
        )
    return lines


def _oldest(open_debts: Sequence[Debt], now: str) -> str:
    if not open_debts:
        return "—"
    oldest = min(open_debts, key=lambda item: item.first_observed_at)
    return f"{_age(oldest.first_observed_at, now)}  ({oldest.id})"


def render_founder_digest(scan: ScanResult, queue: FounderQueue, lane: Lane) -> str:
    """Render the whole founder-facing digest for one fresh scan."""

    decisions = queue.decisions
    labels = decision_labels(decisions)
    sections = [
        "Gaia Steward — founder digest",
        f"  as of {scan.receipt.finished_at}",
        "",
        "Health",
        *_health(scan, lane, len(decisions)),
        "",
    ]

    if not decisions:
        sections.extend([
            "Nothing requires a decision.",
            "",
            "That is the expected outcome. Steward is measured on how rarely it",
            "needs you as much as on what it closes — open debt below Class C is",
            "information, not a queue you are behind on.",
            "",
        ])
        return "\n".join(sections)

    sections.append(
        f"{len(decisions)} decision(s) require founder judgment. Steward has taken"
    )
    sections.append("no action on any of them.")
    sections.append("")

    for decision in decisions:
        label = labels[decision.decision_id]
        sections.extend([
            "─" * 68,
            f"{label} — {decision.decision_target}",
            "",
            "Question",
            *_wrap(decision.objective),
            "",
            f"Blocks  {len(decision.debt_ids)} debt item(s)",
        ])
        for evidence in decision.evidence:
            sections.extend(_evidence_lines(evidence))
        recommendation = _recommendation(decision)
        sections.append("")
        if recommendation is None:
            sections.extend([
                "Steward recommendation",
                "  None. This turns on product, ontology, or prestige judgment,",
                "  which Steward has no basis to hold an opinion about. It has",
                "  grouped the evidence and stopped there deliberately.",
            ])
        else:
            sections.extend(["Steward recommendation", *_wrap(recommendation)])
        sections.extend(["", f"Identity  {decision.decision_id}", ""])

    sections.extend([
        "─" * 68,
        "",
        "One ruling can close several items at once — decisions are grouped by",
        "the exact question, not by the debt that surfaced it. Machine-readable",
        "form: gaia steward founder --json",
        "",
    ])
    return "\n".join(sections)


def _wrap(text: str, width: int = 66) -> list[str]:
    words = " ".join(text.split()).split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(f"  {current}")
            current = word
        else:
            current = candidate
    if current:
        lines.append(f"  {current}")
    return lines


def digest_payload(scan: ScanResult, queue: FounderQueue, lane: Lane) -> dict[str, Any]:
    """The same digest as data, for a caller that wants to render it elsewhere."""

    labels = decision_labels(queue.decisions)
    return {
        "schemaVersion": DIGEST_SCHEMA,
        "asOf": scan.receipt.finished_at,
        "coverageUnknown": list(scan.receipt.coverage_unknown),
        "openDebt": len(scan.open_debts),
        "lane": lane.summary()["counts"],
        "decisions": [
            {
                "label": labels[decision.decision_id],
                "decisionId": decision.decision_id,
                "decisionTarget": decision.decision_target,
                "rule": decision.rule,
                "blocks": len(decision.debt_ids),
                "recommendation": _recommendation(decision),
            }
            for decision in queue.decisions
        ],
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
