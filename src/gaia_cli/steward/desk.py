"""The founder desk: what needs a person, separated from what is merely broken.

The founder digest (``digest.py``) answers "which Class C questions are open".
The desk is the single screen the full runner ends on, and it carries a harder
promise: **a decision is something only the founder can make; everything else
is an operational fault the machinery should be fixing or reporting honestly.**
Mixing the two is how a queue stops being read.

Two sections, never blended:

``NEEDS YOUR DECISION``
    Each item states the decision, why it matters, the evidence, a recommended
    answer, the alternative, what it unblocks, and where to look.  Sources are
    the existing founder queue (reused as-is, never regrouped), other open
    Class C debt grouped by kind, escalated lane entries (the envelope is the
    likelier defect), and explicit decision records under
    ``founder/steward/decisions/``.

``OPERATIONS``
    Sensors that could not observe, sensors that were not evaluated, lane
    attempts that ran out, a ledger that is not shared, a scheduled run that
    went quiet, and decision records that could not be read.  These are never
    decisions; they are faults to repair.

When both are empty the desk is exactly one line, and identical inputs always
render identical output, so it can be diffed and never nags.

Credential findings are rendered from an allow-list of non-secret fields (path,
line, a short fingerprint).  No other part of a credential observation is ever
copied into the desk.
"""

from __future__ import annotations

import json
import os
import re
import textwrap
from dataclasses import dataclass, field, replace
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from gaia_cli.steward.digest import ISSUE_FOUNDER_RULE, _evidence_lines, _parse, _recommendation, issueQuestion
from gaia_cli.steward.lane import Lane
from gaia_cli.steward.models import (
    AuthorityClass,
    Debt,
    FounderDecision,
    FounderQueue,
    content_hash,
    normalize_decision_target,
)
from gaia_cli.steward.routing import LANE_ESCALATION_OBJECTIVE, LANE_ESCALATION_RULE


DESK_SCHEMA = "steward-desk-v1"
DECISION_RECORD_SCHEMA = "steward-decision-v1"
DECISIONS_RELATIVE_DIR = "founder/steward/decisions"
QUIET_LINE = "Gaia Steward: nothing needs you."
TRUST_STAMP_ISSUE = "https://github.com/gaia-research/gaia-skill-tree/issues/1642"

DECISION_SOURCES = ("class-c-debt", "escalated-lane", "decision-record")
OPERATION_KINDS = (
    "coverage_unknown",
    "not_evaluated",
    "exhausted_attempts",
    "failed_dispatch",
    "stale_schedule",
    "ledger_local_only",
    "invalid_decision_record",
    "issue_backlog",
)

_RECORD_KEYS = frozenset({
    "schemaVersion", "id", "status", "decision", "whyItMatters", "evidence",
    "recommended", "alternative", "unblocks", "links",
})
_RECORD_OPTIONAL_KEYS = frozenset({"resolution"})
_RECORD_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
_MAX_RECORD_BYTES = 64 * 1024
_MAX_EVIDENCE_ITEMS = 8
_WIDTH = 78

# Lower sorts first. Security exposure outranks governance, which outranks
# explicit records, which outrank routine Class C questions.
_PRIORITY_CREDENTIAL = 0
_PRIORITY_ESCALATED = 10
_PRIORITY_RECORD = 20
_PRIORITY_CLASS_C = 30


# --- data --------------------------------------------------------------------


@dataclass(frozen=True)
class DeskDecision:
    decision_id: str
    decision: str
    why_it_matters: str
    evidence: tuple[str, ...]
    recommended: str
    alternative: str
    unblocks: str
    links: tuple[str, ...]
    debt_ids: tuple[str, ...]
    source: str
    priority: int = _PRIORITY_CLASS_C

    def __post_init__(self) -> None:
        if self.source not in DECISION_SOURCES:
            raise ValueError(f"unknown desk decision source: {self.source}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisionId": self.decision_id,
            "decision": self.decision,
            "whyItMatters": self.why_it_matters,
            "evidence": list(self.evidence),
            "recommended": self.recommended,
            "alternative": self.alternative,
            "unblocks": self.unblocks,
            "links": list(self.links),
            "debtIds": list(self.debt_ids),
            "source": self.source,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class DeskOperation:
    kind: str
    subject: str
    detail: str

    def __post_init__(self) -> None:
        if self.kind not in OPERATION_KINDS:
            raise ValueError(f"unknown desk operation kind: {self.kind}")

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "subject": self.subject, "detail": self.detail}


@dataclass(frozen=True)
class Desk:
    decisions: tuple[DeskDecision, ...] = ()
    operations: tuple[DeskOperation, ...] = ()
    as_of: str = field(default="")

    def quiet(self) -> bool:
        return not self.decisions and not self.operations

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Desk":
        """Rebuild a desk from its ``to_dict`` form (as stored on a run record)."""

        return cls(
            decisions=tuple(
                DeskDecision(
                    decision_id=item["decisionId"], decision=item["decision"],
                    why_it_matters=item["whyItMatters"], evidence=tuple(item.get("evidence", ())),
                    recommended=item["recommended"], alternative=item["alternative"],
                    unblocks=item["unblocks"], links=tuple(item.get("links", ())),
                    debt_ids=tuple(item.get("debtIds", ())), source=item["source"],
                    priority=item.get("priority", _PRIORITY_CLASS_C),
                )
                for item in data.get("decisions", ())
            ),
            operations=tuple(
                DeskOperation(kind=item["kind"], subject=item["subject"], detail=item["detail"])
                for item in data.get("operations", ())
            ),
            as_of=str(data.get("asOf", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": DESK_SCHEMA,
            "asOf": self.as_of,
            "quiet": self.quiet(),
            "decisions": [item.to_dict() for item in self.decisions],
            "operations": [item.to_dict() for item in self.operations],
        }


# --- decision records ----------------------------------------------------------


def load_decision_records(repo_root: Path) -> tuple[dict, ...]:
    """Read ``founder/steward/decisions/*.json`` without ever raising.

    Every file yields exactly one mapping carrying a ``_source`` key (its
    repo-relative path).  A file that cannot be read or parsed yields
    ``{"_source": ..., "_error": ...}`` so ``build_desk`` can surface it as an
    operation instead of dropping it.  Validation lives in ``build_desk``.
    """

    directory = Path(repo_root) / DECISIONS_RELATIVE_DIR
    try:
        if not directory.exists() and not directory.is_symlink():
            return ()  # no records directory is the normal, quiet case
        if directory.is_symlink() or not directory.is_dir():
            raise OSError("not a regular directory")
        with os.scandir(directory) as entries:
            paths = sorted(
                directory / entry.name for entry in entries if entry.name.endswith(".json")
            )
    except OSError as exc:
        # Present but unusable: say so, rather than looking like "no decisions".
        return ({"_source": DECISIONS_RELATIVE_DIR, "_error": f"directory unreadable: {exc}"},)
    records: list[dict] = []
    for path in paths:
        source = f"{DECISIONS_RELATIVE_DIR}/{path.name}"
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("not a regular file")
            raw = path.read_bytes()
            if len(raw) > _MAX_RECORD_BYTES:
                raise ValueError(f"exceeds {_MAX_RECORD_BYTES} bytes")
            parsed = json.loads(raw.decode("utf-8"))
        # ValueError covers UnicodeDecodeError and JSONDecodeError; pathological
        # nesting raises RecursionError and a huge literal can raise MemoryError.
        except (OSError, ValueError, RecursionError, MemoryError) as exc:
            records.append({"_source": source, "_error": f"unreadable: {type(exc).__name__}: {exc}"[:240]})
            continue
        if not isinstance(parsed, dict):
            records.append({"_source": source, "_error": "top level must be a JSON object"})
            continue
        records.append({**parsed, "_source": source})
    return tuple(records)


def _check_record(record: Mapping[str, Any]) -> str | None:
    """Return why a record is malformed, or None when it is valid."""

    if "_error" in record:
        return str(record["_error"])
    body = {key: value for key, value in record.items() if not str(key).startswith("_")}
    if body.get("schemaVersion") != DECISION_RECORD_SCHEMA:
        return f"schemaVersion must be {DECISION_RECORD_SCHEMA!r}"
    missing = sorted(_RECORD_KEYS - set(body))
    extra = sorted(set(body) - _RECORD_KEYS - _RECORD_OPTIONAL_KEYS)
    if missing:
        return "missing keys: " + ", ".join(missing)
    if extra:
        return "unknown keys: " + ", ".join(extra)
    identifier = body["id"]
    if not isinstance(identifier, str) or not _RECORD_ID.fullmatch(identifier):
        return "id must be a lowercase identifier"
    source = record.get("_source")
    if isinstance(source, str) and Path(source).stem != identifier:
        return f"id {identifier!r} does not match the file name"
    if body["status"] not in ("open", "decided"):
        return "status must be 'open' or 'decided'"
    if "resolution" in body and (not isinstance(body["resolution"], str) or not body["resolution"].strip()):
        return "resolution must be a non-empty string when present"
    for key in ("decision", "whyItMatters", "recommended", "alternative", "unblocks"):
        if not isinstance(body[key], str) or not body[key].strip():
            return f"{key} must be a non-empty string"
    for key in ("evidence", "links"):
        value = body[key]
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            return f"{key} must be a list of non-empty strings"
    return None


def _records_to_desk(
    records: Iterable[Mapping[str, Any]],
) -> tuple[list[DeskDecision], list[DeskOperation]]:
    decisions: list[DeskDecision] = []
    operations: list[DeskOperation] = []
    seen: set[str] = set()
    for record in records:
        source = str(record.get("_source", "decision record"))
        problem = _check_record(record) if isinstance(record, Mapping) else "not a mapping"
        identifier = record.get("id") if isinstance(record, Mapping) else None
        if problem is None and identifier in seen:
            problem = f"duplicate id {identifier!r}"
        if problem is not None:
            operations.append(DeskOperation(
                "invalid_decision_record", source,
                f"cannot be read as a {DECISION_RECORD_SCHEMA} record ({problem}); fix or remove it",
            ))
            continue
        seen.add(str(identifier))
        if record["status"] != "open":
            continue
        decisions.append(DeskDecision(
            decision_id=str(identifier),
            decision=record["decision"].strip(),
            why_it_matters=record["whyItMatters"].strip(),
            evidence=tuple(item.strip() for item in record["evidence"]),
            recommended=record["recommended"].strip(),
            alternative=record["alternative"].strip(),
            unblocks=record["unblocks"].strip(),
            links=tuple(item.strip() for item in record["links"]),
            debt_ids=(),
            source="decision-record",
            priority=_PRIORITY_RECORD,
        ))
    return decisions, operations


# --- Class C debt ----------------------------------------------------------------


_SECRETISH = re.compile(r"(?=[A-Za-z0-9+_=-]*\d)(?=[A-Za-z0-9+_=-]*[A-Za-z])[A-Za-z0-9+_=-]{32,}|AKIA[0-9A-Z]{8,}|gh[pousr]_[A-Za-z0-9]{8,}|sk-[A-Za-z0-9]{8,}|xox[abprs]-[A-Za-z0-9-]{8,}")
_FINGERPRINT = re.compile(r"[0-9a-f]{6,64}")


def _absorb_duplicates(
    record: DeskDecision, decisions: dict[str, DeskDecision]
) -> DeskDecision:
    """Fold generated Class C groups that cite the same issue into the founder's record.

    A record and an auto-grouped decision about one issue are one question asked
    twice. The record wins, takes over the group's debt ids so no debt loses its
    desk entry, and the group is removed.
    """

    issues = {link for link in record.links if "/issues/" in link}
    absorbed = [
        other for other in decisions.values()
        if other.source == "class-c-debt" and issues.intersection(other.links)
    ]
    if not absorbed:
        return record
    debt_ids = tuple(sorted({*record.debt_ids, *(i for other in absorbed for i in other.debt_ids)}))
    for other in absorbed:
        del decisions[other.decision_id]
    note = f"Also covers {len(debt_ids)} open Class C debt(s) cited on the same issue."
    return replace(record, debt_ids=debt_ids, evidence=record.evidence + ((note,) if debt_ids else ()))


def _scrub(text: str) -> str:
    return _SECRETISH.sub("[redacted]", text)


def _credential_rows(debts: Sequence[Debt]) -> tuple[list[str], list[str]]:
    """Evidence and links for credential debt from non-secret fields only."""

    evidence: list[str] = []
    links: list[str] = []
    for debt in sorted(debts, key=lambda item: item.id):
        path = _scrub(str(debt.subject.id))
        findings = debt.observed_state.get("findings")
        rows: list[str] = []
        if isinstance(findings, list):
            for finding in findings:
                if not isinstance(finding, Mapping):
                    continue
                line = finding.get("line")
                line_text = str(line) if isinstance(line, int) and not isinstance(line, bool) else None
                fingerprint = next(
                    (
                        str(finding[key])[:12]
                        for key in ("fingerprint", "hash", "sha256")
                        if isinstance(finding.get(key), str) and _FINGERPRINT.fullmatch(finding[key])
                    ),
                    None,
                )
                if line_text is None and fingerprint is None:
                    continue
                rows.append(
                    f"{path}"
                    + (f" line {line_text}" if line_text else "")
                    + (f" fingerprint {fingerprint}" if fingerprint else "")
                )
                if line_text:
                    links.append(f"{path}#L{line_text}")
        if not rows:
            count = debt.observed_state.get("findingCount")
            rows.append(f"{path} ({count} finding(s))" if isinstance(count, int) else path)
            links.append(path)
        evidence.extend(rows)
    return evidence, sorted(dict.fromkeys(links))


def _generic_evidence(debts: Sequence[Debt]) -> list[str]:
    rows: list[str] = []
    for debt in sorted(debts, key=lambda item: item.id):
        lines = _evidence_lines({
            "debtId": debt.id,
            "subject": debt.subject.to_dict(),
            "observedState": dict(debt.observed_state),
        })
        head, rest = lines[0].strip(), [item.strip() for item in lines[1:]]
        rows.append(head + (" - " + "; ".join(rest) if rest else ""))
    return rows


def _class_c_group(kind: str, debts: Sequence[Debt]) -> DeskDecision:
    ordered = sorted(debts, key=lambda item: item.id)
    ids = tuple(item.id for item in ordered)
    count = len(ordered)
    identity = f"decision-{content_hash({'deskKind': kind})[:20]}"
    unblocks = f"{count} open Class C debt item(s) of kind {kind}; Steward takes no action until you rule."
    if kind == "credential_leak":
        evidence, links = _credential_rows(ordered)
        return DeskDecision(
            decision_id=identity,
            decision=f"Rotate the exposed credential(s) and decide whether to purge git history ({count} finding(s)).",
            why_it_matters=(
                "A credential committed to a repository must be treated as compromised from the "
                "moment it was pushed; removing the line does not revoke it."
            ),
            evidence=tuple(evidence),
            recommended=(
                "Rotate or revoke the credential at its issuer first, then purge history only "
                "if the repository is public or the secret grants production access."
            ),
            alternative=(
                "If the match is a documented test fixture or placeholder, record that ruling so "
                "the finding is classified as intentional instead of rotated."
            ),
            unblocks=unblocks,
            links=tuple(links),
            # A debt id embeds a slug of its subject (a file path). Credential
            # subjects can carry secret-shaped text, so only the opaque digest
            # suffix leaves this module.
            debt_ids=tuple(item.rsplit(":", 1)[-1] for item in ids),
            source="class-c-debt",
            priority=_PRIORITY_CREDENTIAL,
        )
    if kind == "trust_stamp_stale":
        return DeskDecision(
            decision_id=identity,
            decision="Decide the Trust Magnitude stamp refresh policy for stale stored stamps.",
            why_it_matters=(
                "Stored trustMagnitude stamps disagree with the computed effective value, so "
                "displayed trust and computed trust differ until a refresh policy exists. "
                "Steward measures this and never edits stamps."
            ),
            evidence=tuple(_generic_evidence(ordered)),
            recommended=(
                "Choose one refresh mechanism in #1642 (for example a gated `gaia dev` command "
                "that restamps inside a reviewed PR) and record it as a decision."
            ),
            alternative=(
                "Declare stored stamps historical snapshots and exclude them from drift detection."
            ),
            unblocks=unblocks,
            links=(TRUST_STAMP_ISSUE,),
            debt_ids=ids,
            source="class-c-debt",
        )
    return DeskDecision(
        decision_id=identity,
        decision=f"Rule on {count} open Class C {kind} finding(s).",
        why_it_matters=(
            f"Policy classifies {kind} as Class C: its correct resolution turns on a governance "
            "judgment that Steward has no basis to make."
        ),
        evidence=tuple(_generic_evidence(ordered)),
        recommended="None. Steward has grouped the evidence and stopped deliberately.",
        alternative="Defer; the findings stay open and nothing else depends on them unless listed under Unblocks.",
        unblocks=unblocks,
        links=(),
        debt_ids=ids,
        source="class-c-debt",
    )


# --- founder queue and lane ------------------------------------------------------------


_RULE_WHY = {
    LANE_ESCALATION_RULE: (
        "Bounded repair stopped: the attempt ceiling was reached or a verifier escalated. "
        "The envelope, not the attempt, is the likelier defect, and nothing retries until you rule."
    ),
    "generic-mapping-decision": (
        "An unmapped candidate has no canonical generic capability, so it stays invisible to the "
        "tree and cannot be curated until a target is ruled."
    ),
}
_RULE_ALTERNATIVE = {
    LANE_ESCALATION_RULE: (
        "Take the finding yourself as a direct Class C ruling, or retire the routine "
        "instead of widening its envelope."
    ),
    "generic-mapping-decision": "Reject the mapping and leave the candidate unmapped.",
}
_NO_OPINION = (
    "None. This turns on product, ontology, or prestige judgment, which Steward has "
    "no basis to hold an opinion about."
)
_RULE_WHY[ISSUE_FOUNDER_RULE] = (
    "Steward can prove which upstream candidates are curated, but whether a family of them is "
    "accepted, rejected or deferred is a product decision. Nothing is closed or accepted until you rule."
)
_RULE_ALTERNATIVE[ISSUE_FOUNDER_RULE] = (
    "Defer; the affected issues stay open exactly as they are, and Steward takes no action on them."
)


def _flatten_evidence(evidence: Mapping[str, Any]) -> str:
    lines = _evidence_lines(evidence)
    head, rest = lines[0].strip(), [item.strip() for item in lines[1:]]
    return head + (" - " + "; ".join(rest) if rest else "")


def _from_founder_decision(decision: FounderDecision, source: str) -> DeskDecision:
    count = len(decision.debt_ids)
    recommended = _recommendation(decision) or _NO_OPINION
    links: tuple[str, ...] = (
        ("founder/steward/POLICY.yaml",) if decision.rule == LANE_ESCALATION_RULE else ()
    )
    return DeskDecision(
        decision_id=decision.decision_id,
        decision=issueQuestion(decision) or decision.objective,
        why_it_matters=_RULE_WHY.get(
            decision.rule,
            f"{count} open Class C debt item(s) are blocked on this ruling; Steward will not act on them.",
        ),
        evidence=tuple(_flatten_evidence(item) for item in decision.evidence),
        recommended=" ".join(recommended.split()),
        alternative=_RULE_ALTERNATIVE.get(
            decision.rule, "Defer; the debt stays open and Steward continues to take no action on it."
        ),
        unblocks=f"{count} open Class C debt item(s) under {decision.decision_target}.",
        links=links,
        debt_ids=decision.debt_ids,
        source=source,
        priority=_PRIORITY_ESCALATED if source == "escalated-lane" else _PRIORITY_CLASS_C,
    )


def _escalation_decisions(
    queue_decisions: Sequence[FounderDecision], lane: Lane | None, open_ids: frozenset[str]
) -> list[FounderDecision]:
    """Fold lane escalations into the queue's own lane-escalation groups.

    The queue is the authority and is reused unchanged; the lane is consulted
    only for escalated debt the queue did not already carry that is still open.
    Group identity is the queue's own, so a group is never split in two.
    """

    groups: dict[str, dict[str, Mapping[str, Any]]] = {}
    for decision in queue_decisions:
        if decision.rule != LANE_ESCALATION_RULE:
            continue
        groups[decision.decision_target] = dict(zip(decision.debt_ids, _aligned(decision), strict=True))
    if lane is not None:
        for entry in lane.escalated:
            target = normalize_decision_target(f"{LANE_ESCALATION_RULE}/{entry.rule}")
            if entry.debt_id not in open_ids or entry.debt_id in groups.get(target, {}):
                continue
            bucket = groups.setdefault(target, {})
            reason = entry.history[-1].reason if entry.history else "escalated"
            bucket[entry.debt_id] = {
                "debtId": entry.debt_id,
                "subject": {"id": entry.debt_id},
                "observedState": {"attempts": entry.attempts, "reason": reason},
            }
    return [
        FounderDecision.create(
            rule=LANE_ESCALATION_RULE,
            decision_target=target,
            objective=LANE_ESCALATION_OBJECTIVE,
            debt_ids=tuple(bucket),
            evidence=tuple(bucket[key] for key in sorted(bucket)),
        )
        for target, bucket in sorted(groups.items())
    ]


def _aligned(decision: FounderDecision) -> list[Mapping[str, Any]]:
    """Pair each source debt id with its own evidence row."""

    by_id = {str(item.get("debtId")): item for item in decision.evidence}
    return [by_id.get(debt_id, {"debtId": debt_id, "subject": {"id": debt_id}}) for debt_id in decision.debt_ids]


# --- operations ------------------------------------------------------------------------


def _backlogLine(backlog: Mapping[str, Any]) -> str:
    """One line of issue backlog: counts, closures this run and total, and the change since the last run."""

    net = backlog.get("netChange")
    change = "no previous run recorded" if not isinstance(net, int) else f"net change {net:+d} since the previous run"
    total = backlog.get("closedTotal")
    closedTotal = str(total) if isinstance(total, int) else "unknown"
    ready = backlog.get("readyWritesDisabled")
    readyText = f"; ready (writes disabled): {ready} proven closures" if isinstance(ready, int) and ready > 0 else ""
    return (
        f"open issues {backlog.get('openIssues')} (bot {backlog.get('botOpen')}, upstream children "
        f"{backlog.get('upstreamChildOpen')}); closed this run {backlog.get('closedThisRun', 0)} of "
        f"{closedTotal} total; {change}{readyText}"
    )



def _operations(
    *,
    lane: Lane | None,
    coverage_unknown: Sequence[str],
    not_evaluated: Sequence[Mapping[str, Any]],
    failed_dispatches: Sequence[Mapping[str, Any]],
    ledger_shared: bool,
    coverage_unknown_reasons: Mapping[str, str] | None = None,
    last_scheduled_run_at: str | None,
    now: str,
    stale_after_hours: int,
) -> list[DeskOperation]:
    operations: list[DeskOperation] = []
    reasons = coverage_unknown_reasons or {}
    for sensor in sorted(set(coverage_unknown)):
        why = f" Cause: {reasons[sensor]}" if reasons.get(sensor) else ""
        operations.append(DeskOperation(
            "coverage_unknown", str(sensor),
            "Steward could not observe this surface, so it refuses Class A repair and dispatch until it can." + why,
        ))
    for item in sorted(not_evaluated, key=lambda row: str(row.get("sensor", ""))):
        if item.get("inputAbsent") is True:
            continue  # no driver supplied it: shown in the receipt and retro, nothing to act on
        operations.append(DeskOperation(
            "not_evaluated", str(item.get("sensor", "unknown")),
            f"not evaluated: {item.get('reason', 'no reason given')}",
        ))
    if lane is not None:
        for entry in lane.entries:
            if entry.live and entry.attempts >= lane.policy.max_attempts:
                operations.append(DeskOperation(
                    "exhausted_attempts", entry.debt_id,
                    f"{entry.attempts} of {lane.policy.max_attempts} attempts used under {entry.rule} "
                    f"while still {entry.state}; the next rejection escalates it to you.",
                ))
    for item in sorted(failed_dispatches, key=lambda row: str(row.get("subject", ""))):
        operations.append(DeskOperation(
            "failed_dispatch", str(item.get("subject", "unknown")),
            str(item.get("detail", "dispatch failed")),
        ))
    if not ledger_shared:
        operations.append(DeskOperation(
            "ledger_local_only", "steward ledger",
            "state is in a local file, so manual and scheduled runs cannot see each other's work.",
        ))
    stale = _stale_schedule(last_scheduled_run_at, now, stale_after_hours)
    if stale is not None:
        operations.append(DeskOperation("stale_schedule", "scheduled run", stale))
    return operations


def _stale_schedule(last: str | None, now: str, stale_after_hours: int) -> str | None:
    if not last:
        return "no scheduled run has ever been recorded."
    then, current = _parse(last), _parse(now)
    if then is None or current is None:
        return f"last scheduled run time is unreadable ({last!r})."
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age = current - then
    if age > timedelta(hours=stale_after_hours):
        return f"last scheduled run was {int(age.total_seconds() // 3600)}h ago (limit {stale_after_hours}h)."
    return None


# --- build ---------------------------------------------------------------------------


def build_desk(
    *,
    open_debts: Sequence[Debt],
    founder_queue: FounderQueue | None,
    lane: Lane | None,
    coverage_unknown: Sequence[str],
    not_evaluated: Sequence[Mapping[str, Any]],
    decision_records: Sequence[Mapping[str, Any]],
    ledger_shared: bool,
    last_scheduled_run_at: str | None,
    now: str,
    stale_after_hours: int = 48,
    failed_dispatches: Sequence[Mapping[str, Any]] = (),
    coverage_unknown_reasons: Mapping[str, str] | None = None,
    backlog: Mapping[str, Any] | None = None,
) -> Desk:
    """Assemble the desk from already-computed inputs. Pure: no I/O, no clock."""

    queue_decisions = tuple(founder_queue.decisions) if founder_queue is not None else ()
    decisions: dict[str, DeskDecision] = {}

    # (a) the existing founder queue, mapped one-to-one and never regrouped.
    for decision in queue_decisions:
        if decision.rule == LANE_ESCALATION_RULE:
            continue
        decisions[decision.decision_id] = _from_founder_decision(decision, "class-c-debt")

    # (c) escalated lane entries, folded into the queue's own escalation groups.
    open_ids = frozenset(debt.id for debt in open_debts if debt.status == "open")
    for decision in _escalation_decisions(queue_decisions, lane, open_ids):
        decisions[decision.decision_id] = _from_founder_decision(decision, "escalated-lane")

    # (b) every other open Class C debt, grouped by kind.
    covered = {debt_id for decision in queue_decisions for debt_id in decision.debt_ids}
    by_kind: dict[str, list[Debt]] = {}
    for debt in open_debts:
        if debt.status == "open" and debt.authority is AuthorityClass.C and debt.id not in covered:
            by_kind.setdefault(debt.kind, []).append(debt)
    for kind, debts in sorted(by_kind.items()):
        group = _class_c_group(kind, debts)
        decisions[group.decision_id] = group

    # (d) explicit decision records.
    record_decisions, record_operations = _records_to_desk(decision_records)
    for item in record_decisions:
        decisions.setdefault(item.decision_id, _absorb_duplicates(item, decisions))

    ordered = tuple(sorted(decisions.values(), key=lambda item: (item.priority, item.decision_id)))
    operations = _operations(
        lane=lane,
        coverage_unknown=coverage_unknown,
        coverage_unknown_reasons=coverage_unknown_reasons,
        not_evaluated=not_evaluated,
        failed_dispatches=failed_dispatches,
        ledger_shared=ledger_shared,
        last_scheduled_run_at=last_scheduled_run_at,
        now=now,
        stale_after_hours=stale_after_hours,
    ) + record_operations
    if backlog:
        operations.append(DeskOperation("issue_backlog", "issue backlog", _backlogLine(backlog)))
    operations.sort(key=lambda op: (OPERATION_KINDS.index(op.kind), op.subject, op.detail))
    return Desk(decisions=ordered, operations=tuple(operations), as_of=now)


# --- render --------------------------------------------------------------------------


_ASCII = str.maketrans({"\u2014": "-", "\u2013": "-", "\u2026": "...", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


_CONTROLS = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _plain(text: str) -> str:
    """Whitespace-normalised, terminal-safe text (digest prose uses typography)."""

    # Control characters (ESC, BEL, NUL, DEL, ...) never reach a terminal; they
    # become spaces, then whitespace collapses. Newlines are never needed inside
    # a wrapped field, so they go too.
    cleaned = _CONTROLS.sub(" ", text.translate(_ASCII))
    return " ".join(cleaned.split()).encode("ascii", "replace").decode("ascii")


def _field(label: str, text: str) -> list[str]:
    prefix = f"   {label}:".ljust(20)
    return textwrap.wrap(
        _plain(text), width=_WIDTH, initial_indent=prefix,
        subsequent_indent=" " * 20, break_long_words=False, break_on_hyphens=False,
    ) or [prefix.rstrip()]


def _list_field(label: str, items: Sequence[str]) -> list[str]:
    if not items:
        return _field(label, "none")
    lines = [f"   {label}:"]
    for item in items[:_MAX_EVIDENCE_ITEMS]:
        lines.extend(textwrap.wrap(
            _plain(item), width=_WIDTH, initial_indent="     - ",
            subsequent_indent="       ", break_long_words=False, break_on_hyphens=False,
        ))
    if len(items) > _MAX_EVIDENCE_ITEMS:
        lines.append(f"     - ... and {len(items) - _MAX_EVIDENCE_ITEMS} more")
    return lines


def render_desk(desk: Desk) -> str:
    """Render the desk as plain text. Deterministic; one newline-terminated line when quiet."""

    if desk.quiet():
        return QUIET_LINE + "\n"
    lines = [_plain("Gaia Steward: founder desk" + (f" (as of {desk.as_of})" if desk.as_of else "")), ""]
    lines.append(f"NEEDS YOUR DECISION ({len(desk.decisions)})")
    if not desk.decisions:
        lines.append("   None.")
    for index, item in enumerate(desk.decisions, start=1):
        lines.extend(["", _plain(f" {index}. {item.decision_id}  [{item.source}]")])
        lines.extend(_field("Decision", item.decision))
        lines.extend(_field("Why it matters", item.why_it_matters))
        lines.extend(_list_field("Evidence", item.evidence))
        lines.extend(_field("Recommended", item.recommended))
        lines.extend(_field("Alternative", item.alternative))
        lines.extend(_field("Unblocks", item.unblocks))
        lines.extend(_list_field("Link", item.links))
    lines.extend(["", f"OPERATIONS ({len(desk.operations)})"])
    if not desk.operations:
        lines.append("   None.")
    for op in desk.operations:
        lines.extend(textwrap.wrap(
            _plain(f"[{op.kind}] {op.subject}: {op.detail}"), width=_WIDTH,
            initial_indent="   - ", subsequent_indent="     ",
            break_long_words=False, break_on_hyphens=False,
        ))
    return "\n".join(lines) + "\n"
