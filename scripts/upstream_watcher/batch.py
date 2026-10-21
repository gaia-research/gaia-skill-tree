"""
scripts.upstream_watcher.batch — umbrella-with-batch-record planner (#2131, F3 amendment).

Default emission (``--child-mode batch``): one umbrella per suite carries a
``payloadVersion: 2`` payload with a ``candidates[]`` row per component. No
per-candidate child is created. ``--escalate <candidate-id>`` creates one
intake child for one row.

Pipeline for one run (``run_batch``):

1. Load the registry index and a LIST snapshot of open + recently closed
   issues. Any failure => unknown evidence, ZERO writes, exit code 3.
2. For each update finding, merge candidate rows keyed by candidate id
   (never dropped), run prechecks, and compare the canonical payload hash
   with the live umbrella. Equal hash and title => no-op (no edit, no comment).
3. Writes re-read the live issue first. A changed updatedAt/body hash triggers
   one re-plan; a second mismatch gives up for this run (no duplicate create).

Payload fields are versioned by ``payloadVersion``; ``payloadSha256`` is the
SHA-256 of the canonical JSON of the payload without that field.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import Counter
from typing import Any

from scripts.lib.github_api import parse_owner_repo
from scripts.upstream_watcher import prechecks, records
from scripts.upstream_watcher.issuer import (
    _LABEL_VOCAB,
    _REVIEWER_ACTIONS,
    render_child_body,
)
from scripts.upstream_watcher.live import GhError, LiveGh, open_umbrellas, read_live
from scripts.upstream_watcher.records import RecordError

PAYLOAD_VERSION = 2
UNKNOWN_EXIT_CODE = 3
# H2: a label reset is retried this many times before the run gives up. Giving up leaves the
# body untouched, so the next run still sees a payload change (non-noop) and retries.
RESET_ATTEMPTS = 3
# M5: GitHub's body limit is 65,536 characters. A suite whose full inline payload renders above
# BODY_BUDGET is written in records mode (compact index in the body, full rows in record
# comments). BODY_LIMIT is the hard ceiling: a body that still exceeds it fails closed.
BODY_LIMIT = 65_536
BODY_BUDGET = 60_000
PLACEHOLDER_BODY = (
    "## Upstream release detected\n\n"
    "Writing the batch record. The full rows are attached as record comments on this issue, "
    "and this body is replaced once they are written."
)
PAYLOAD_RE = re.compile(r"<!-- gaia-upstream-payload\n(.*?)\n-->", re.DOTALL)
ESCALATE_LABELS = ["intake", "needs-triage", "upstream:child"]
# Row statuses (prechecks: new, tracked, present, rejected; escalate: escalated).
# present and rejected are resolved. Every other row stays unresolved until its
# child intake is closed. The approve workflow applies the same rule.
RESOLVED_STATUSES = frozenset({"present", "rejected"})
CHILD_UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


def parse_payload(body: str | None) -> dict | None:
    """Return the decoded payload block of an umbrella body, or None."""
    match = PAYLOAD_RE.search(body or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def canonical_hash(payload: dict) -> str:
    """SHA-256 over canonical JSON, excluding the hash field itself."""
    data = {key: value for key, value in payload.items() if key != "payloadSha256"}
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def body_hash(body: str) -> str:
    return hashlib.sha256((body or "").encode("utf-8")).hexdigest()


def payload_block(payload: dict) -> str:
    if "candidateRecords" in payload:
        # Records mode keeps the index on one line so the index itself stays well under the limit.
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    else:
        encoded = json.dumps(payload, indent=2, ensure_ascii=False)
    return "<!-- gaia-upstream-payload\n" + encoded + "\n-->"


def label_names(issue: dict) -> list[str]:
    return [label["name"] if isinstance(label, dict) else label for label in issue.get("labels", [])]


def owner_repo_of(finding: dict) -> str:
    parsed = parse_owner_repo(finding.get("sourceUrl", "")) if finding.get("sourceUrl") else None
    return f"{parsed[0]}/{parsed[1]}" if parsed else finding["skillId"]


def umbrella_title(owner_repo: str, version: str) -> str:
    return f"[upstream] {owner_repo} → {version}"


def umbrella_prefix(owner_repo: str) -> str:
    return f"[upstream] {owner_repo} → "


# ---------------------------------------------------------------------------
# Candidate rows
# ---------------------------------------------------------------------------


def candidate_rows(finding: dict, component_root: str = "skills") -> list[dict]:
    """Build un-prechecked candidate rows for a finding's componentAdds."""
    owner_repo = owner_repo_of(finding)
    owner, repo = owner_repo.split("/", 1) if "/" in owner_repo else (owner_repo, "")
    contributor = finding["skillId"].split("/")[0] if "/" in finding["skillId"] else finding["skillId"]
    version = finding["newVersion"]
    rows = []
    for slug in finding.get("componentAdds", []):
        rows.append(
            {
                "id": f"{owner_repo}:{slug}",
                "slug": slug,
                "suggestedId": f"{contributor}/{slug}",
                "evidenceUrl": f"https://github.com/{owner}/{repo}/blob/main/{component_root}/{slug}/SKILL.md",
                "firstSeenVersion": version,
                "lastSeenVersion": version,
                "child": None,
            }
        )
    return rows


def adopted_child(precheck: dict) -> int | None:
    tracked = precheck.get("tracked", "none")
    return int(tracked.split("#", 1)[1]) if tracked.startswith("child:#") else None


def child_state_lookup(live: dict, probe=None):
    """Return ``state_of(number)`` -> ``open`` | ``closed`` | ``absent`` | ``unknown``.

    The LIST snapshot answers first (open issues and those closed within the
    recent window). A number the snapshot does not hold is asked of *probe*, a
    single GET. Without a probe the answer is ``unknown``, which every caller
    treats as "keep the link and never drop the row" (fail closed).
    """
    known = {issue["number"]: issue.get("state") for issue in live["issues"]}
    cache: dict[int, str] = {}

    def state_of(number: int) -> str:
        if known.get(number) in ("open", "closed"):
            return known[number]
        if number not in cache:
            cache[number] = probe(number) if probe is not None else CHILD_UNKNOWN
        return cache[number]

    return state_of


def dead_children(rows: list[dict], state_of) -> frozenset[int]:
    """Child numbers a row links to that GitHub reports as definitively absent (301 transferred, 404 or 410)."""
    return frozenset(
        row["child"] for row in rows if row.get("child") is not None and state_of(row["child"]) == "absent"
    )


def row_is_unresolved(row: dict, state_of) -> bool:
    """A row still owes a decision unless it is registry-present, rejected, or its child intake is closed."""
    if row.get("status") in RESOLVED_STATUSES:
        return False
    child = row.get("child")
    return not (child is not None and state_of(child) == "closed")


def unresolved_row_ids(payload: dict, state_of) -> list[str]:
    """Ids of the candidate rows in a v2 payload that are still unresolved. v1 has none."""
    return [row["id"] for row in payload.get("candidates", []) if row_is_unresolved(row, state_of)]


def carry_forward(live: dict, prefix: str, state_of, gh=None) -> list[dict]:
    """Unresolved rows of the newest closed umbrella for a suite, to seed a new umbrella.

    The source is the full closed ``upstream:release`` history (``closedUmbrellas``),
    never the 30-day window: an umbrella closed months ago still carries its
    unresolved rows, so closing an umbrella can never drop candidates. A carried
    row keeps its status, child link and firstSeenVersion, and records
    ``carriedFrom`` as the umbrella it was last carried from. Records-mode umbrellas are
    read back through their record comments (M5).
    """
    closed = [
        issue
        for issue in live["closedUmbrellas"]
        if issue.get("state") == "closed"
        and "upstream:release" in label_names(issue)
        and str(issue.get("title", "")).startswith(prefix)
    ]
    if not closed:
        return []
    newest = max(closed, key=lambda issue: issue["number"])
    rows = load_rows(gh, newest["number"], parse_payload(newest.get("body")))
    return [
        {**row, "carriedFrom": f"#{newest['number']}"}
        for row in rows
        if row_is_unresolved(row, state_of)
    ]


def merge_rows(
    existing: list[dict],
    incoming: list[dict],
    version: str,
    dead: frozenset[int] | set[int] = frozenset(),
) -> tuple[list[dict], list[str]]:
    """Merge incoming candidate rows into existing ones, keyed by candidate id.

    Existing rows are never dropped. Escalated status and child links survive
    version churn. A child link in *dead* (definitively 301/404/410) is cleared and
    a row that was tracked or escalated goes back to ``new``, so it is visible
    as an unresolved candidate again. Returns (rows sorted by id, ids of newly
    added rows).
    """
    by_id = {row["id"]: dict(row) for row in existing}
    for row in by_id.values():
        if row.get("child") is not None and row["child"] in dead:
            row["child"] = None
            if row.get("status") in ("tracked", "escalated"):
                row["status"] = "new"
            if isinstance(row.get("precheck"), dict):
                row["precheck"] = {**row["precheck"], "tracked": "none"}
    added: list[str] = []
    for fresh in incoming:
        row = dict(fresh)
        if fresh["id"] in by_id:
            current = by_id[fresh["id"]]
            current["lastSeenVersion"] = version
            current["precheck"] = fresh["precheck"]
            current["status"] = "escalated" if current.get("status") == "escalated" else fresh["status"]
            child = adopted_child(fresh["precheck"])
            if child is not None:
                current["child"] = child
            elif current.get("child") is None:
                current["child"] = None
            continue
        by_id[fresh["id"]] = row
        row["child"] = adopted_child(fresh["precheck"])
        added.append(fresh["id"])
    return [by_id[key] for key in sorted(by_id)], added


def settle_liveness(finding: dict, previous_payload: dict | None) -> dict:
    """L2: a component whose head check hit a transient network error is not a broken link.

    Such a component is kept out of the hashed linkLiveness, and its previous recorded state
    (if the umbrella already holds one) is carried forward. A transient error never creates a
    new row, so it cannot churn the umbrella.
    """
    unknown = set(finding.get("linkLivenessUnknown") or [])
    if not unknown:
        return finding
    kept = list(finding.get("linkLiveness") or [])
    fresh_ids = {row["skillId"] for row in kept}
    prior = {row["skillId"]: row for row in (previous_payload or {}).get("linkLiveness", [])}
    carried = [prior[sid] for sid in sorted(unknown) if sid in prior and sid not in fresh_ids]
    return {**finding, "linkLiveness": kept + carried}


def load_rows(gh, number: int, payload: dict | None) -> list[dict]:
    """Full candidate rows of an umbrella.

    Inline payloads hold them in ``candidates``. Records-mode payloads hold an index there, and
    the full rows are read back from the umbrella's record comments and verified against the
    body digest. Any failure raises GhError (fail closed).
    """
    if payload is None:
        return []
    meta = payload.get("candidateRecords")
    if meta is None:
        return list(payload.get("candidates", []))
    if gh is None:
        raise RecordError(f"#{number} holds records and no GitHub client was given to read them")
    try:
        comments = gh.list_comments(number)
    except GhError as exc:
        raise RecordError(f"record comments of #{number} could not be listed: {exc}") from exc
    return records.read_rows(comments, meta)


def build_payload(finding: dict, rows: list[dict], previous_version: str | None, records_meta: dict | None = None) -> dict:
    payload = {
        "payloadVersion": PAYLOAD_VERSION,
        "skillId": finding["skillId"],
        "previousVersion": previous_version if previous_version is not None else finding.get("currentVersion", "none"),
        "newVersion": finding["newVersion"],
        "releasedAt": finding.get("releasedAt", ""),
        "sourceUrl": finding.get("sourceUrl", ""),
        "mode": finding.get("mode", "version-only"),
        "componentAdds": list(finding.get("componentAdds", [])),
        "componentRemoves": list(finding.get("componentRemoves", [])),
        "linkLiveness": list(finding.get("linkLiveness", [])),
        "nameDrift": list(finding.get("nameDrift", [])),
        "candidates": rows,
    }
    if records_meta is not None:
        payload["candidateRecords"] = records_meta
    payload["payloadSha256"] = canonical_hash(payload)
    return payload


def layout(finding: dict, rows: list[dict], previous_version: str | None) -> tuple[dict, str, list[dict] | None]:
    """Choose inline or records mode for *rows*. Returns (payload, body, record rows or None).

    Inline (the default, unchanged) when the full rendering fits BODY_BUDGET. Otherwise the body
    carries an index and the full rows go to record comments. A body that still exceeds
    BODY_LIMIT in records mode raises RecordError, so nothing over the limit is ever written.
    """
    inline = build_payload(finding, rows, previous_version)
    inline_body = render_batch_body(inline)
    if len(inline_body) <= BODY_BUDGET:
        return inline, inline_body, None
    index = [{"id": row["id"], "status": row["status"], "child": row.get("child")} for row in rows]
    meta = {"chunks": len(records.chunk_rows(rows)), "rows": len(rows), "sha256": records.rows_digest(rows)}
    payload = build_payload(finding, index, previous_version, records_meta=meta)
    body = render_batch_body(payload)
    if len(body) > BODY_LIMIT:
        raise RecordError(
            f"{len(rows)} candidate rows leave an umbrella index of {len(body)} characters, "
            f"over GitHub's {BODY_LIMIT}-character body limit; the suite needs a curation decision"
        )
    return payload, body, rows


def _records_summary(payload: dict) -> str:
    """Batch-review text for a records-mode umbrella: the rows live in its record comments."""
    meta = payload["candidateRecords"]
    counts = Counter(row["status"] for row in payload["candidates"])
    status_line = ", ".join(f"`{name}` {count}" for name, count in sorted(counts.items()))
    return (
        f"**{meta['rows']} candidate row(s)** are kept losslessly in {meta['chunks']} record comment(s) "
        "on this umbrella, because they do not fit in the body. The body holds an index only, "
        f"so it stays under GitHub's body limit. Status counts: {status_line}."
    )


def render_batch_body(payload: dict) -> str:
    """Human-readable umbrella body with an independently addressable batch table."""
    rows = payload["candidates"]
    records_summary = _records_summary(payload) if "candidateRecords" in payload else None
    table_rows = []
    for row in rows if records_summary is None else []:
        precheck = row.get("precheck", {})
        child = f"#{row['child']}" if row.get("child") else "—"
        table_rows.append(
            f"| `cand:{row['id']}` | `{row['suggestedId']}` | `{row['status']}` | "
            f"`{precheck.get('registry', 'unchecked')}` | `{precheck.get('tracked', 'none')}` | "
            f"`{precheck.get('priorDisposition', 'none')}` | {child} | "
            f"{row['firstSeenVersion']} → {row['lastSeenVersion']} |"
        )
    batch_table = records_summary if records_summary is not None else (
        "| Row | Suggested ID | Status | Registry | Tracked | Prior | Child | Seen |\n"
        "|---|---|---|---|---|---|---|---|\n" + "\n".join(table_rows)
        if table_rows
        else "_No new components detected._"
    )
    liveness = payload.get("linkLiveness") or []
    drift = payload.get("nameDrift") or []
    carried_rows = [] if records_summary is not None else [row for row in rows if row.get("carriedFrom")]
    carried_note = (
        f"\n\n_Carried forward from closed umbrella {', '.join(sorted({row['carriedFrom'] for row in carried_rows}))}: "
        f"{len(carried_rows)} unresolved row(s) kept open._"
        if carried_rows
        else ""
    )
    return f"""## Upstream release detected

> Auto-generated by the Gaia upstream watcher. See [upstream-watcher.md](https://github.com/gaia-research/gaia-skill-tree/blob/main/docs/agents/upstream-watcher.md) for the full design spec.

{payload_block(payload)}

---

### Version

**`{payload['skillId']}`** was at `{payload['previousVersion']}` → upstream is now **`{payload['newVersion']}`**
Released: `{payload['releasedAt']}`
Source: {payload['sourceUrl']}

**Mode:** `{payload['mode']}`. Components removed upstream: {len(payload['componentRemoves'])}. Broken links: {len(liveness)}. Name drift rows: {len(drift)}.

---

### Batch review

Each row is addressable as `cand:<id>`. Rows are retained for the life of the suite and never removed; a row that is `present`, `tracked` or `rejected` is suppressed from new work but kept here. To give one row its own intake child, run the **Upstream Watcher** workflow with `escalate_candidate=<id>`.

{batch_table}{carried_note}

---

### Label vocab

{_LABEL_VOCAB}

---

### Reviewer actions

{_REVIEWER_ACTIONS}
"""


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def baseline_ids(previous_payload: dict | None, owner_repo: str) -> set[str]:
    """Candidate ids a reviewer has already seen in the umbrella being replaced.

    A legacy (pre-v2) umbrella has no candidate rows; its ``componentAdds`` are
    what the reviewer approved. Converting it to v2 must not count those
    components as new.
    """
    if not previous_payload:
        return set()
    if "candidates" in previous_payload:
        return {row["id"] for row in previous_payload["candidates"]}
    return {f"{owner_repo}:{slug}" for slug in previous_payload.get("componentAdds", [])}


def _comments(gh, number: int) -> list[dict]:
    """Every comment on *number*, or RecordError. Used only when record comments are in play."""
    if gh is None:
        raise RecordError(f"#{number} needs its record comments and no GitHub client was given to read them")
    try:
        return gh.list_comments(number)
    except GhError as exc:
        raise RecordError(f"record comments of #{number} could not be listed: {exc}") from exc


def plan_suite(finding: dict, live: dict, index: dict, probe=None, gh=None) -> dict:
    """Compute the umbrella action for one update finding. Performs no writes.

    *probe* (``LiveGh.issue_state`` in a run) resolves child numbers the LIST snapshot does not
    hold. *gh* reads the record comments of a records-mode umbrella (M5). A GhError from either
    propagates: unknown evidence, no writes.
    """
    owner_repo = owner_repo_of(finding)
    new_version = finding["newVersion"]
    title = umbrella_title(owner_repo, new_version)
    prefix = umbrella_prefix(owner_repo)
    existing = open_umbrellas(live["issues"], prefix)
    umbrella = existing[-1] if existing else None
    state_of = child_state_lookup(live, probe)

    open_children, rejected = prechecks.index_children(live["issues"])
    incoming = []
    for row in candidate_rows(finding, finding.get("upstreamComponentRoot") or "skills"):
        checked = prechecks.precheck_row(row, index, open_children, rejected)
        incoming.append({**row, **checked})

    previous_payload = parse_payload(umbrella.get("body")) if umbrella else None
    finding = settle_liveness(finding, previous_payload)
    if umbrella is not None and previous_payload is not None:
        prior_rows = load_rows(gh, umbrella["number"], previous_payload)
        carried: list[dict] = []
    else:
        # A new umbrella, or one whose body was never written (a create that stopped part way),
        # starts from the closed umbrella's unresolved rows, so closing an umbrella never drops
        # candidates.
        carried = carry_forward(live, prefix, state_of, gh)
        prior_rows = carried
    rows, added = merge_rows(prior_rows, incoming, new_version, dead=dead_children(prior_rows, state_of))
    payload, body, record_rows = layout(finding, rows, previous_version=None)

    record_writes: list[tuple[str, int | None, str]] = []
    if record_rows is not None:
        comments = [] if umbrella is None else _comments(gh, umbrella["number"])
        record_writes = records.plan_writes(comments, record_rows)

    if umbrella is None:
        action = "create"
    elif (
        (previous_payload or {}).get("payloadSha256") == payload["payloadSha256"]
        and umbrella["title"] == title
        and not record_writes
    ):
        action = "noop"
    else:
        action = "update"

    approved = bool(umbrella) and "upstream:approved" in label_names(umbrella)
    seen_ids = baseline_ids(previous_payload, owner_repo)
    reset_rows = [rid for rid in added if rid not in seen_ids]
    reset = action == "update" and approved and (
        (previous_payload or {}).get("newVersion") != new_version or bool(reset_rows)
    )
    suppressed = [row["id"] for row in incoming if row["status"] in prechecks.SUPPRESSED_STATUSES]
    return {
        "suite": owner_repo,
        "title": title,
        "action": action,
        "umbrella": umbrella["number"] if umbrella else None,
        "umbrellaTitle": umbrella["title"] if umbrella else None,
        "payload": payload,
        "body": body,
        "records": record_rows,
        "recordWrites": record_writes,
        "newRows": added,
        "resetRows": reset_rows,
        "suppressed": suppressed,
        "carried": [row["id"] for row in carried],
        "totalRows": len(rows),
        "approvedVersion": (previous_payload or {}).get("newVersion") if approved else None,
        "reset": reset,
        "prevVersion": (previous_payload or {}).get("newVersion"),
        "snapshot": snapshot_of(umbrella) if umbrella else None,
    }


def snapshot_of(issue: dict) -> dict:
    return {"updatedAt": issue.get("updated_at"), "bodySha256": body_hash(issue.get("body") or "")}


def comment_for(plan: dict) -> str | None:
    """One comment per umbrella write, only when something a reviewer must see changed."""
    if plan["reset"]:
        return (
            f"Approval reset: `{plan['approvedVersion']}` was approved, but upstream is now "
            f"`{plan['payload']['newVersion']}` with added rows "
            f"{', '.join(f'`cand:{rid}`' for rid in plan['resetRows']) or 'none'}. "
            "`upstream:approved` was removed and `upstream:needs-info` applied. Re-apply `upstream:approved` after review."
        )
    if plan["umbrellaTitle"] != plan["title"]:
        prev = plan["prevVersion"] or "unknown"
        return (
            f"Updated umbrella for new upstream release: **`{plan['payload']['newVersion']}`** "
            f"(previously `{prev}`). Candidate rows refreshed; {len(plan['newRows'])} new row(s)."
        )
    return None


def new_report() -> dict:
    return {
        "generatedAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "childMode": "batch",
        "dryRun": True,
        "issuesCreated": 0,
        "issuesUpdated": 0,
        "suppressedDuplicates": 0,
        "retainedCandidates": 0,
        "unknownEvidence": [],
        "suites": [],
    }


def _retry(action):
    """Run *action*, retrying a GhError up to RESET_ATTEMPTS times. The last error is raised."""
    last: GhError | None = None
    for _attempt in range(RESET_ATTEMPTS):
        try:
            return action()
        except GhError as exc:
            last = exc
    raise last  # type: ignore[misc]


def _write_records(gh, number: int, writes: list[tuple[str, int | None, str]]) -> None:
    """Apply record comment writes. Retried: a repeated create only duplicates identical content, which readers accept."""
    for kind, comment_id, text in writes:
        if kind == "create":
            _retry(lambda text=text: gh.comment(number, text))
        else:
            _retry(lambda comment_id=comment_id, text=text: gh.edit_comment(comment_id, text))


def write_umbrella(plan: dict, gh: LiveGh) -> str:
    """Execute a create/update plan. Returns the outcome label.

    Order (H2, M5): the reviewer note, then the approval reset (labels), then the record
    comments, and the body last. A failure before the body write leaves the body unchanged, so
    the next run still sees a payload change and retries. Label, record and body writes are
    retried. The note is not, because a retry could duplicate it.
    """
    if plan["action"] == "create":
        if plan["records"] is None:
            number = gh.create_issue(plan["title"], ["upstream:release", "needs-triage"], plan["body"])
            plan["umbrella"] = number
            return "created"
        # Records mode: create with a placeholder, attach the record comments, then write the index body.
        number = gh.create_issue(plan["title"], ["upstream:release", "needs-triage"], PLACEHOLDER_BODY)
        plan["umbrella"] = number
        _write_records(gh, number, plan["recordWrites"])
        _retry(lambda: gh.edit_issue(number, plan["title"], plan["body"]))
        return "created"
    note = comment_for(plan)
    if note:
        gh.comment(plan["umbrella"], note)
    if plan["reset"]:
        _retry(lambda: gh.edit_labels(plan["umbrella"], add=["upstream:needs-info"], remove=["upstream:approved"]))
    _write_records(gh, plan["umbrella"], plan["recordWrites"])
    _retry(lambda: gh.edit_issue(plan["umbrella"], plan["title"], plan["body"]))
    return "updated"


def process_suite(finding: dict, gh: LiveGh, index: dict, live: dict, apply: bool) -> tuple[dict, dict]:
    """Plan and (when apply) write one suite. Returns (suite report row, live snapshot)."""
    plan = plan_suite(finding, live, index, probe=gh.issue_state, gh=gh)
    outcome = "planned"
    if plan["action"] == "noop":
        outcome = "noop"
    elif apply:
        outcome = "raced-skip"
        for _attempt in range(2):
            if plan["action"] == "noop":
                # L1: a racing run already wrote this exact umbrella. Nothing to write.
                outcome = "noop"
                break
            if plan["action"] == "create":
                fresh = read_live(gh)
                if open_umbrellas(fresh["issues"], umbrella_prefix(plan["suite"])):
                    live = fresh
                    plan = plan_suite(finding, live, index, probe=gh.issue_state, gh=gh)
                    continue
                outcome = write_umbrella(plan, gh)
                break
            current = gh.get_issue(plan["umbrella"])
            if snapshot_of(current) != plan["snapshot"]:
                live = read_live(gh)
                plan = plan_suite(finding, live, index, probe=gh.issue_state, gh=gh)
                if plan["action"] == "noop":
                    outcome = "noop"
                    break
                continue
            outcome = write_umbrella(plan, gh)
            break
    row = {
        "suite": plan["suite"],
        "umbrella": plan["umbrella"],
        "action": plan["action"],
        "outcome": outcome,
        "newRows": plan["newRows"],
        "totalRows": plan["totalRows"],
        "suppressed": plan["suppressed"],
        "carried": plan["carried"],
    }
    return row, live


def fill_report(report: dict, suite_row: dict) -> None:
    report["suites"].append(
        {
            "suite": suite_row["suite"],
            "umbrella": suite_row["umbrella"],
            "newRows": len(suite_row["newRows"]),
            "totalRows": suite_row["totalRows"],
            "carriedForward": len(suite_row["carried"]),
            "outcome": suite_row["outcome"],
        }
    )
    report["retainedCandidates"] += suite_row["totalRows"]
    report["suppressedDuplicates"] += len(suite_row["suppressed"])
    if suite_row["action"] == "create" and suite_row["outcome"] in ("created", "planned"):
        report["issuesCreated"] += 1
    elif suite_row["action"] == "update" and suite_row["outcome"] in ("updated", "planned"):
        report["issuesUpdated"] += 1


def run_batch(
    findings: list[dict],
    gh: LiveGh,
    apply: bool,
    index_loader=prechecks.load_registry_index,
) -> tuple[dict, int]:
    """Plan (and when *apply*, write) umbrella batch records for update findings.

    Returns ``(report, exit_code)``. Exit 3 means unknown evidence: no write was
    made and the report lists the failing source.
    """
    report = new_report()
    report["dryRun"] = not apply
    updates = [finding for finding in findings if finding.get("finding_type") == "update"]

    try:
        index = index_loader()
    except prechecks.RegistryUnreadable as exc:
        report["unknownEvidence"].append({"source": "registry", "detail": str(exc)})
        return report, UNKNOWN_EXIT_CODE

    try:
        live = read_live(gh)
    except GhError as exc:
        report["unknownEvidence"].append({"source": "github-list", "detail": str(exc)})
        return report, UNKNOWN_EXIT_CODE

    for finding in updates:
        try:
            suite_row, live = process_suite(finding, gh, index, live, apply)
        except GhError as exc:
            report["unknownEvidence"].append(
                {"source": "github-write", "suite": finding["skillId"], "detail": str(exc)}
            )
            return report, UNKNOWN_EXIT_CODE
        fill_report(report, suite_row)
    return report, 0


def escalate_candidate(candidate_id: str, gh: LiveGh, apply: bool) -> tuple[dict, int]:
    """Create (or adopt) one intake child for a batch row. Returns (result, exit code)."""
    result: dict[str, Any] = {"candidate": candidate_id, "dryRun": not apply, "outcome": None, "child": None}
    try:
        live = read_live(gh)
    except GhError as exc:
        return {**result, "outcome": "unknown", "detail": str(exc)}, UNKNOWN_EXIT_CODE

    umbrella = None
    payload_now = None
    for issue in live["issues"]:
        if issue.get("state") != "open" or "upstream:release" not in label_names(issue):
            continue
        payload = parse_payload(issue.get("body"))
        if not payload:
            continue
        if any(candidate.get("id") == candidate_id for candidate in payload.get("candidates", [])):
            umbrella, payload_now = issue, payload
    if umbrella is None:
        return {**result, "outcome": "not-found"}, 2
    try:
        rows = load_rows(gh, umbrella["number"], payload_now)
    except GhError as exc:
        return {**result, "outcome": "unknown", "detail": str(exc)}, UNKNOWN_EXIT_CODE
    row = next((candidate for candidate in rows if candidate["id"] == candidate_id), None)
    if row is None:
        return {**result, "outcome": "not-found"}, 2
    if row.get("child") is not None:
        # A child link GitHub reports as definitively absent (301/404/410) must not block escalation.
        try:
            linked_state = child_state_lookup(live, gh.issue_state)(row["child"])
        except GhError as exc:
            return {**result, "outcome": "unknown", "detail": str(exc)}, UNKNOWN_EXIT_CODE
        if linked_state != "absent":
            return {**result, "outcome": "already-child", "child": row["child"], "umbrella": umbrella["number"]}, 0

    open_children, _ = prechecks.index_children(live["issues"])
    child_number = open_children.get(row["suggestedId"])
    if child_number is not None:
        outcome = "adopted"
    else:
        outcome = "created"
        if apply:
            child_body = render_child_body(
                slug=row["slug"],
                contributor=row["suggestedId"].split("/")[0],
                umbrella_number=umbrella["number"],
                suite_gh_url=payload_now.get("sourceUrl", ""),
            )
            child_number = gh.create_issue(f"[intake] {row['suggestedId']}", ESCALATE_LABELS, child_body)
    result.update({"umbrella": umbrella["number"], "child": child_number, "outcome": outcome})

    if not apply:
        return result, 0

    current = gh.get_issue(umbrella["number"])
    if snapshot_of(current) != snapshot_of(umbrella):
        return {**result, "outcome": "raced-skip"}, 0
    updated_rows = []
    for candidate in rows:
        if candidate["id"] == candidate_id:
            # An adopted child is tracked at once; a child created here is escalated.
            status = "escalated" if outcome == "created" else "tracked"
            candidate = {**candidate, "child": child_number, "status": status}
            if isinstance(candidate.get("precheck"), dict):
                candidate["precheck"] = {**candidate["precheck"], "tracked": f"child:#{child_number}"}
        updated_rows.append(candidate)
    try:
        _payload, body, record_rows = layout(payload_now, updated_rows, previous_version=payload_now.get("previousVersion"))
        record_writes = (
            records.plan_writes(_comments(gh, umbrella["number"]), record_rows) if record_rows is not None else []
        )
    except GhError as exc:
        return {**result, "outcome": "unknown", "detail": str(exc)}, UNKNOWN_EXIT_CODE
    _write_records(gh, umbrella["number"], record_writes)
    gh.edit_issue(umbrella["number"], umbrella["title"], body)
    return result, 0


