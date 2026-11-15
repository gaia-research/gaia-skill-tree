"""Consume the four scoped founder locks from #2283, not closure authority.

The existing decision schema has no structured family fields. Exact question and
source-debt mappings therefore live in its allowed links/evidence fields. These
bindings interpret only the four explicit resolutions; arbitrary decided records
never authorize work. The #2283 implementation document or any expected record
enables the complete lock set; the document and all four finalized records are
then required. Missing, open or malformed locks fail closed.
Unrelated checkouts with neither retain ordinary reconciliation rules.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from gaia_cli.steward.desk import _check_record, load_decision_records

AUTHORITY = "https://github.com/gaia-research/gaia-skill-tree/issues/2283#issuecomment-6640916880"
CAMPAIGN_AUTHORITY = "founder/reports/upstream-backlog-2026-11/CAMPAIGN.md"
# qid: (current/default resolution, source debt suffix, affected issues, exact suite identities)
BINDINGS = {
    "q-08ecd62d": ("technical-reconciliation-only", "b46650ebeefbdb87", (1833,), ("ruvnet/ruflo", "ruvnet/agentdb")),
    "q-2568173e": ("records-and-version-sync-migration-deferred", "749fb275800fe372", (2002,), ("addyosmani/agent-skills", "addy-osmani/agent-skills")),
    "q-bfd37238": ("records-and-version-sync-only", "ac2f25b1b6af9db6", (1835,), ("garrytan/gbrain",)),
    "q-6720aecf": ("manual-disabled-fail-closed", "e5f9c70bc8f1e0c9", (2126, 2127), ()),
}
ALLOWED_RESOLUTIONS: dict[str, tuple[str, ...]] = {
    "q-08ecd62d": ("technical-reconciliation-only",),
    "q-2568173e": ("migration-deferred", "records-and-version-sync-migration-deferred"),
    "q-bfd37238": ("curation-deferred", "records-and-version-sync-only"),
    "q-6720aecf": ("manual-disabled-fail-closed",),
}
AMENDED_RESOLUTIONS: dict[str, str] = {
    "q-2568173e": "records-and-version-sync-migration-deferred",
    "q-bfd37238": "records-and-version-sync-only",
}
# Narrowly enumerated baseline children from founder/reports/upstream-backlog-2026-11/PLAN.md.
# Only these exact (issue, candidate_id) pairs may be evaluated for A1 proof-based closure under the
# 2026-11-15 rulings; new, absent, alias-suspect, or unrelated descendants remain held.
BASELINE_CHILDREN: dict[str, dict[int, str]] = {
    "q-bfd37238": {
        1925: "garrytan/article-enrichment", 1926: "garrytan/ask-user", 1929: "garrytan/brain-ingest-gate",
        1930: "garrytan/brain-link-discipline", 1931: "garrytan/brain-pdf", 1932: "garrytan/brain-taxonomist",
        1933: "garrytan/briefing", 1935: "garrytan/chat-connectors", 1936: "garrytan/citation-fixer",
        1938: "garrytan/cold-start", 1939: "garrytan/company-brainify", 1942: "garrytan/correction-pipeline",
        1943: "garrytan/cron-scheduler", 1944: "garrytan/cross-modal-review", 1945: "garrytan/daily-task-manager",
        1946: "garrytan/daily-task-prep", 1947: "garrytan/data-loss-gate", 1949: "garrytan/db-repair",
        1951: "garrytan/eiirp", 1952: "garrytan/enrich", 1954: "garrytan/frontmatter-guard",
        1957: "garrytan/gbrain-upgrade", 1958: "garrytan/google-loops", 1959: "garrytan/idea-ingest",
        1961: "garrytan/ingest", 1964: "garrytan/media-ingest", 1968: "garrytan/perplexity-research",
        1969: "garrytan/postgres-adopt", 1970: "garrytan/publish", 1971: "garrytan/query",
        1973: "garrytan/repo-architecture", 1974: "garrytan/reports", 1976: "garrytan/resolve-before-asking",
        1977: "garrytan/schema-author", 1978: "garrytan/schema-unify", 1982: "garrytan/skill-creator",
        1984: "garrytan/skillify", 1986: "garrytan/skillpack-harvest", 1987: "garrytan/smoke-test",
        1988: "garrytan/soul-audit", 1990: "garrytan/testing", 1992: "garrytan/voice-note-ingest",
        1993: "garrytan/webhook-transforms", 1997: "garrytan/mcp-access", 2135: "garrytan/skill-autobench",
        2204: "garrytan/academic-verify", 2205: "garrytan/archive-crawler", 2206: "garrytan/blog-ingest",
        2207: "garrytan/book-mirror", 2208: "garrytan/bulk-ingestion", 2209: "garrytan/citation-graph-ingest",
        2210: "garrytan/context-audit", 2211: "garrytan/conversation-archive", 2212: "garrytan/data-research",
        2213: "garrytan/draft-in-voice", 2214: "garrytan/fact-check", 2215: "garrytan/functional-area-resolver",
        2216: "garrytan/idea-lineage", 2217: "garrytan/measure-before-you-fix", 2218: "garrytan/meeting-ingestion",
        2219: "garrytan/minion-orchestrator", 2220: "garrytan/remote-mcp", 2221: "garrytan/research-compendium",
        2222: "garrytan/signal-detector", 2223: "garrytan/skill-optimizer", 2224: "garrytan/strategic-reading",
        2225: "garrytan/two-tier-extraction",
    },
    "q-2568173e": {
        2008: "addy-osmani/debugging-and-error-recovery",
        2013: "addy-osmani/git-workflow-and-versioning",
        2014: "addy-osmani/idea-refine",
        2015: "addy-osmani/interview-me",
    },
}


def loadIssueDecisions(root: Path) -> tuple[dict, ...]:
    names = {f"issue-question-{qid}.json" for qid in BINDINGS}
    records = load_decision_records(root)
    if any(record.get("_source") == "founder/steward/decisions" and "_error" in record for record in records):
        raise ValueError("issue decision directory unreadable")
    selected = tuple(record for record in records if Path(record.get("_source", "")).name in names)
    bindings = decidedBindings(selected)  # validate on every read, including closure re-derivation
    marker = root / "founder/steward/FOUNDER_LOCK_2283.md"
    enabled = marker.exists() or bool(selected)
    if enabled and not marker.is_file():
        raise ValueError("founder lock #2283 requires the FOUNDER_LOCK_2283.md document")
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
        _, suffix, issues, _ = BINDINGS[qid]
        target = f"issue-question/{qid}"
        debt = f"debt:issue_founder_decision:{qid}:{suffix}"
        required = {target, AUTHORITY, *(f"https://github.com/gaia-research/gaia-skill-tree/issues/{n}" for n in issues)}
        resolution = record.get("resolution")
        if resolution == AMENDED_RESOLUTIONS.get(qid):
            required.add(CAMPAIGN_AUTHORITY)
        if resolution not in ALLOWED_RESOLUTIONS[qid] or not required <= set(record["links"]) \
                or target not in record["evidence"] or debt not in record["evidence"]:
            raise ValueError(f"issue decision mapping or authority missing: {qid}")
        found[qid] = record
    return found
