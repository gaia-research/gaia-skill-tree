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
from gaia_cli.steward.prmaintenance import advice


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

    if decision.rule == ROUTINE_PR_FOUNDER_RULE:
        return _routinePrAdvice(decision)
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


def _routinePrAdvice(decision: FounderDecision) -> str:
    """A held routine pull request gets a derivable procedural recommendation and an explicit no-opinion on the content.

    The wording comes from ``prmaintenance.advice``, the same module the GitHub receipt uses, so the two surfaces cannot
    disagree. State recorded by an older sensor, or hand-edited, is never trusted for the text: the observed gate names
    are matched against a fixed set and everything else is fixed text.
    """

    observed = (decision.evidence[0].get("observedState") if decision.evidence else None) or {}
    gates = observed.get("gates") if isinstance(observed, Mapping) else None
    names = [g.get("name") for g in gates if isinstance(g, Mapping)] if isinstance(gates, list) else []
    return advice.combined(*advice.pair(names))


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


ISSUE_FOUNDER_RULE = "issue-founder-decision"
ROUTINE_PR_FOUNDER_RULE = "routine-pr-founder-decision"


def issueQuestion(decision: FounderDecision) -> str | None:
    """The exact issue-hygiene question and its affected issues, when this decision is one."""

    if decision.rule not in (ISSUE_FOUNDER_RULE, ROUTINE_PR_FOUNDER_RULE) or not decision.evidence:
        return None
    observed = decision.evidence[0].get("observedState") or {}
    question = observed.get("question")
    if not isinstance(question, str) or not question:
        return None
    if decision.rule == ROUTINE_PR_FOUNDER_RULE:
        return f"{question} Pull request: {observed.get('repo')}#{observed.get('number')} at head {str(observed.get('headSha'))[:12]}."
    affected = observed.get("affected") or []
    numbers = ", ".join(f"#{number}" for number in affected if isinstance(number, int)) or "none listed"
    return f"{question} Affected issues: {numbers}."


def backlogHealthLine(scan: ScanResult) -> str | None:
    """The issue backlog from the census reconciliation the scan observed, or None when no census was read."""

    stats = next((o.provenance.get("stats") for o in scan.observations
                  if o.source == "issue-hygiene" and isinstance(o.provenance.get("stats"), dict)), None)
    if not stats:
        return None
    return (f"  Issue backlog            open {stats.get('openIssues')} "
            f"(bot {stats.get('botOpen')}, upstream children {stats.get('upstreamChildOpen')})")


def _health(scan: ScanResult, lane: Lane, decisions: int, awaiting: int = 0) -> list[str]:
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
    if awaiting:
        lines.append(f"  Approved, not yet landed {awaiting}")
    backlog = backlogHealthLine(scan)
    if backlog is not None:
        lines.append(backlog)
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


def _record_sections(records: Any) -> list[str]:
    """Pending canonical records, approved records awaiting landing, and unreadable records."""

    sections: list[str] = []
    for item in records.pending:
        sections.extend([
            "─" * 68,
            f"{item.decision_id} — decision record",
            "",
            "Question",
            *_wrap(item.decision),
            "",
            "Why it matters",
            *_wrap(item.why_it_matters),
            "",
            "Steward recommendation",
            *_wrap(item.recommended),
            "",
            "Alternative",
            *_wrap(item.alternative),
            "",
            "Unblocks",
            *_wrap(item.unblocks),
            "",
            f"Identity  {item.decision_id}  (founder/steward/decisions/{item.decision_id}.json)",
            "",
        ])
    if records.awaiting:
        sections.extend([
            "─" * 68,
            f"APPROVED, AWAITING IMPLEMENTATION OR LANDING ({len(records.awaiting)})",
            "  The founder has ruled on each of these. No new decision is needed;",
            "  each still needs its change implemented or landed. Add a",
            "  `landedIn` field to a record once its change has landed.",
            "",
        ])
        for item in records.awaiting:
            sections.extend([f"  {item.record_id}", *_wrap(item.decision), ""])
    if records.invalid:
        sections.extend([
            "─" * 68,
            f"DECISION RECORDS THAT CANNOT BE READ ({len(records.invalid)})",
            "",
        ])
        for op in records.invalid:
            sections.extend([f"  {op.subject}", *_wrap(op.detail), ""])
    return sections


def render_founder_digest(scan: ScanResult, queue: FounderQueue, lane: Lane, records: Any = None) -> str:
    """Render the whole founder-facing digest for one fresh scan.

    ``records`` is a ``desk.RecordDesk`` over ``founder/steward/decisions/``. It
    is optional so a caller with no records directory keeps the old behaviour,
    but the digest never reports an empty desk while any record is actionable.
    """

    from gaia_cli.steward.desk import RecordDesk

    records = records if records is not None else RecordDesk()
    decisions = queue.decisions
    labels = decision_labels(decisions)
    pending = len(decisions) + len(records.pending)
    sections = [
        "Gaia Steward — founder digest",
        f"  as of {scan.receipt.finished_at}",
        "",
        "Health",
        *_health(scan, lane, pending, len(records.awaiting)),
        "",
    ]

    if not decisions and not records.pending:
        if not records.actionable():
            sections.extend([
                "Nothing requires a decision.",
                "",
                "That is the expected outcome. Steward is measured on how rarely it",
                "needs you as much as on what it closes — open debt below Class C is",
                "information, not a queue you are behind on.",
                "",
            ])
            return "\n".join(sections)
        sections.extend([
            "No decision is pending.",
            "",
            "Actionable decision records remain; they are listed below.",
            "",
        ])
        sections.extend(_record_sections(records))
        return "\n".join(sections)

    sections.append(
        f"{pending} decision(s) require founder judgment. Steward has taken"
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
            *_wrap(issueQuestion(decision) or decision.objective),
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
            sections.append("Steward recommendation")
            for index, paragraph in enumerate(recommendation.split("\n\n")):
                sections.extend(["", *_wrap(paragraph)] if index else _wrap(paragraph))
        sections.extend(["", f"Identity  {decision.decision_id}", ""])

    sections.extend(_record_sections(records))
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
