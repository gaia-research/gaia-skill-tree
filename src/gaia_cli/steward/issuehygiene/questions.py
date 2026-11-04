"""Consume the four scoped founder locks from #2283, not closure authority.

The existing decision schema has no structured family fields. Exact question and
source-debt mappings therefore live in its allowed links/evidence fields. These
bindings interpret only the four explicit resolutions; arbitrary decided records
never authorize work. The #2283 implementation document or any expected record
enables the complete lock set; missing, open or malformed locks then fail closed.
Unrelated checkouts with neither retain ordinary reconciliation rules.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from gaia_cli.steward.desk import _check_record, load_decision_records

AUTHORITY = "https://github.com/gaia-research/gaia-skill-tree/issues/2283#issuecomment-6640916880"
# qid: (resolution, source debt suffix, affected issues, exact suite identities)
BINDINGS = {
    "q-08ecd62d": ("technical-reconciliation-only", "b46650ebeefbdb87", (1833,), ("ruvnet/ruflo", "ruvnet/agentdb")),
    "q-2568173e": ("migration-deferred", "749fb275800fe372", (2002,), ("addyosmani/agent-skills", "addy-osmani/agent-skills")),
    "q-bfd37238": ("curation-deferred", "ac2f25b1b6af9db6", (1835,), ("garrytan/gbrain",)),
    "q-6720aecf": ("manual-disabled-fail-closed", "e5f9c70bc8f1e0c9", (2126, 2127), ()),
}


def loadIssueDecisions(root: Path) -> tuple[dict, ...]:
    names = {f"issue-question-{qid}.json" for qid in BINDINGS}
    records = load_decision_records(root)
    if any(record.get("_source") == "founder/steward/decisions" and "_error" in record for record in records):
        raise ValueError("issue decision directory unreadable")
    selected = tuple(record for record in records if Path(record.get("_source", "")).name in names)
    bindings = decidedBindings(selected)  # validate on every read, including closure re-derivation
    enabled = (root / "founder/steward/FOUNDER_LOCK_2283.md").exists() or bool(selected)
    if enabled and set(bindings) != set(BINDINGS):
        raise ValueError("founder lock #2283 requires all four finalized decision records")
    return selected


def decidedBindings(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    found = {}
    seen = set()
    for record in records:
        qid = str(record.get("id", "")).removeprefix("issue-question-")
        source = Path(str(record.get("_source", ""))).stem.removeprefix("issue-question-")
        if source in BINDINGS and qid != source:
            raise ValueError("issue decision identity mismatch")
        if qid not in BINDINGS:
            continue
        if _check_record(record) is not None or qid in seen:
            raise ValueError(f"invalid issue decision {qid}")
        seen.add(qid)
        if record["status"] != "decided":
            continue
        resolution, suffix, issues, _ = BINDINGS[qid]
        target = f"issue-question/{qid}"
        debt = f"debt:issue_founder_decision:{qid}:{suffix}"
        required = {target, AUTHORITY, *(f"https://github.com/gaia-research/gaia-skill-tree/issues/{n}" for n in issues)}
        if record.get("resolution") != resolution or not required <= set(record["links"]) \
                or target not in record["evidence"] or debt not in record["evidence"]:
            raise ValueError(f"issue decision mapping or authority missing: {qid}")
        found[qid] = record
    return found
