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
import sys
from collections import Counter
from typing import Any

from scripts.lib.github_api import parse_owner_repo
from scripts.upstream_watcher import approval, prechecks, records
from scripts.upstream_watcher.approval import (  # noqa: F401  (re-exported for callers and tests)
    APPROVAL_RESET_MARKER,
    canonical_hash,
    changed_fields,
    payload_tampered,
    reset_marker,
    reset_note,
)
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


def body_hash(body: str) -> str:
    return hashlib.sha256((body or "").encode("utf-8")).hexdigest()


# The fields a legacy (pre-v2, no candidates) payload carries. A reviewer approved exactly these.
LEGACY_KEYS = frozenset({
    "skillId", "previousVersion", "newVersion", "releasedAt", "sourceUrl", "mode",
    "componentAdds", "componentRemoves", "linkLiveness", "nameDrift",
})
LEGACY_DEFAULTS = {"componentAdds": [], "componentRemoves": [], "linkLiveness": [], "nameDrift": []}


def representation_only(previous: dict | None, payload: dict) -> bool:
    """True when *payload* is the v2 form of a legacy *previous* payload and every approved field is unchanged.

    Converting a legacy umbrella adds payloadVersion, the candidate rows (components the reviewer already
    saw as componentAdds, the baseline_ids rule) and the digests. That is a change of representation, not
    of approved content, so an approval survives it. Any changed legacy field is a content change and resets
    the approval (H1).
    """
    if previous is None or "candidates" in previous or "payloadVersion" in previous:
        return False
    if not ((set(previous) - {"payloadSha256"}) <= LEGACY_KEYS):
        return False
    return all(
        previous.get(key, LEGACY_DEFAULTS.get(key)) == payload.get(key)
        for key in LEGACY_KEYS
    )


def payload_changed(previous: dict | None, payload: dict) -> bool:
    """H1: True when the hashed payload differs from the previous one in a way the reviewer must see again.

    Metadata outside the hash never reaches this function. A legacy-to-v2 representation change is exempt
    (see representation_only). Everything else, including an absent previous payload, counts as a change.
    """
    if previous is None:
        return True
    if previous.get("payloadSha256") == payload["payloadSha256"]:
        return False
    return not representation_only(previous, payload)


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


def detached(row: dict) -> dict:
    """A row read from a tampered payload keeps no child link (D1a). Fresh prechecks re-adopt open children.

    A forged link can then only make a row unresolved, never resolved. The status of a row whose link is
    dropped falls back to ``new``, so the reviewer sees it again.
    """
    if row.get("child") is None:
        return row
    status = "new" if row.get("status") in ("escalated", "tracked") else row.get("status")
    return {**row, "child": None, "status": status}


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
            f"suite {finding['skillId']} has {len(rows)} candidate rows; its umbrella index would be "
            f"{len(body)} characters, over GitHub's {BODY_LIMIT}-character body limit. Nothing was written. "
            "Rows are never dropped, so this needs a curation decision: reject or escalate some rows, "
            "or split the suite (see docs/agents/upstream-watcher.md, records ceiling)."
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
    # D1a: the stored digest is recomputed on every read. A mismatch means the body was edited, so the
    # approval resets and the body is repaired from the fresh plan (its child links are not trusted).
    tampered = payload_tampered(previous_payload)
    finding = settle_liveness(finding, previous_payload)
    if umbrella is not None and previous_payload is not None:
        prior_rows = load_rows(gh, umbrella["number"], previous_payload)
        if tampered:
            prior_rows = [detached(row) for row in prior_rows]
        carried: list[dict] = []
    else:
        # A new umbrella, or one whose body was never written (a create that stopped part way),
        # starts from the closed umbrella's unresolved rows, so closing an umbrella never drops
        # candidates.
        carried = carry_forward(live, prefix, state_of, gh)
        prior_rows = carried
    rows, added = merge_rows(prior_rows, incoming, new_version, dead=dead_children(prior_rows, state_of))
    payload, body, record_rows = layout(finding, rows, previous_version=None)

    # D4 / M7: a records-mode umbrella, or one leaving records mode, is moved to its target generation with
    # the two-phase plan. Nothing here writes; the plan is executed by write_umbrella.
    record_plan = None
    had_records = previous_payload is not None and "candidateRecords" in previous_payload
    if record_rows is not None or had_records:
        comments = [] if umbrella is None else _comments(gh, umbrella["number"])
        record_plan = records.plan_generation(comments, record_rows)
    record_pending = record_plan is not None and bool(record_plan.prewrites or record_plan.cleanup)

    if umbrella is None:
        action = "create"
    elif (
        (previous_payload or {}).get("payloadSha256") == payload["payloadSha256"]
        and umbrella["title"] == title
        and not tampered
        and not record_pending
    ):
        action = "noop"
    else:
        action = "update"

    approved = bool(umbrella) and "upstream:approved" in label_names(umbrella)
    seen_ids = baseline_ids(previous_payload, owner_repo)
    reset_rows = [rid for rid in added if rid not in seen_ids]
    # H1: approval never survives a change to the hashed payload. The hash covers every payload field
    # (versions, component adds and removes, liveness, name drift, every candidate row and its
    # precheck, and the records digest), so any such change resets it. Metadata outside the hash
    # (for example an updated_at timestamp) does not. D1a: a tampered stored digest always resets it.
    reset = action == "update" and approved and (tampered or payload_changed(previous_payload, payload))
    changed = changed_fields(previous_payload, payload)
    if tampered and not changed:
        changed = ["payloadSha256 (the stored digest does not match the payload)"]
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
        "recordPlan": record_plan,
        "newRows": added,
        "resetRows": reset_rows,
        "changedFields": changed,
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


def approval_reset_note(plan: dict) -> str:
    """The one reviewer note an approval reset posts (approval.reset_note, fed from a plan)."""
    return reset_note(
        plan.get("approvedVersion") or "unknown",
        plan["payload"]["newVersion"],
        plan.get("changedFields", []),
        plan.get("resetRows", []),
        plan["payload"]["payloadSha256"],
    )


def comment_for(plan: dict) -> str | None:
    """The plain update note, for an umbrella whose title moved without an approval to reset."""
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


def _run_prewrites(gh, number: int, writes: list[tuple[str, int | None, str]]) -> None:
    """Run the prewrites of a generation plan, before the body switch (D4).

    A create is not retried: a create that landed before its error is reused by the next run, because the
    planner finds the chunk by its generation and index, so no second copy is ever made. A delete is retried.
    """
    for kind, comment_id, text in writes:
        if kind == "create":
            gh.comment(number, text)
        else:
            _retry(lambda comment_id=comment_id: gh.delete_comment(comment_id))


def _run_cleanup(gh, number: int, writes: list[tuple[str, int, str]]) -> None:
    """Delete the superseded generations, after the body switch (D4). Best effort.

    The body already names a complete generation, so a failed delete changes no reader's result. It is
    reported as a warning and the next run deletes it again.
    """
    for _kind, comment_id, _text in writes:
        try:
            _retry(lambda comment_id=comment_id: gh.delete_comment(comment_id))
        except GhError as exc:
            print(f"::warning::could not delete superseded record comment {comment_id} on #{number}: {exc}",
                  file=sys.stderr)


def _switch_records(gh, number: int, title: str, body: str, record_plan) -> None:
    """Write an umbrella's records and body in the order that keeps a complete generation readable (D4).

    1. prewrites: the target generation's missing chunks (new comments; nothing existing is edited);
    2. the body, which now names the target generation (the switch);
    3. cleanup: the superseded generations (best effort).
    A failure before step 2 leaves the body naming the old, complete generation. A failure after it leaves
    the new one complete. Only the cleanup can leave garbage, and readers ignore garbage.
    """
    if record_plan is not None:
        _run_prewrites(gh, number, record_plan.prewrites)
    _retry(lambda: gh.edit_issue(number, title, body))
    if record_plan is not None:
        _run_cleanup(gh, number, record_plan.cleanup)


def _approval_reset(gh, number: int, plan: dict) -> None:
    """Reset an approved umbrella whose hashed payload changed (H1).

    The reviewer note is posted once per payload hash (L3). The marker counts only when the watcher wrote
    it (D9): a human quoting the marker must not suppress the note. The labels are then reset, retried.
    A reset that still fails raises GhError, so the body is never written and the next run still sees a change.
    """
    marker = reset_marker(plan["payload"]["payloadSha256"])
    watcher_bodies = [row.get("body") or "" for row in gh.list_comments(number) if records.is_watcher_comment(row)]
    if not any(marker in text for text in watcher_bodies):
        gh.comment(number, approval_reset_note(plan))
    _retry(lambda: gh.edit_labels(number, add=["upstream:needs-info"], remove=["upstream:approved"]))


def write_umbrella(plan: dict, gh: LiveGh) -> str:
    """Execute a create/update plan. Returns the outcome label.

    Order (H1, H2, D4): the approval reset (note, then labels) when an approved umbrella's payload
    changed, then the records and body (see _switch_records). A failure before the body write leaves the
    body unchanged, so the next run still sees a payload change and retries. A plain update note is not
    retried, because a retry could duplicate it.
    """
    if plan["action"] == "create":
        if plan["records"] is None:
            number = gh.create_issue(plan["title"], ["upstream:release", "needs-triage"], plan["body"])
            plan["umbrella"] = number
            return "created"
        # Records mode: create with a placeholder, attach the record comments, then write the index body.
        number = gh.create_issue(plan["title"], ["upstream:release", "needs-triage"], PLACEHOLDER_BODY)
        plan["umbrella"] = number
        _switch_records(gh, number, plan["title"], plan["body"], plan["recordPlan"])
        return "created"
    if plan["reset"]:
        _approval_reset(gh, plan["umbrella"], plan)
    else:
        note = comment_for(plan)
        if note:
            gh.comment(plan["umbrella"], note)
    _switch_records(gh, plan["umbrella"], plan["title"], plan["body"], plan["recordPlan"])
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
        report["unknownEvidence"].append({"source": "registry", "detail": str(exc), "stopped": True})
        return report, UNKNOWN_EXIT_CODE

    try:
        live = read_live(gh)
    except GhError as exc:
        report["unknownEvidence"].append({"source": "github-list", "detail": str(exc), "stopped": True})
        return report, UNKNOWN_EXIT_CODE

    for finding in updates:
        try:
            suite_row, live = process_suite(finding, gh, index, live, apply)
        except RecordError as exc:
            # One suite's record comments cannot be verified. That suite gets zero writes, and the
            # other suites are still processed. The run still exits 3 at the end (H2).
            report["unknownEvidence"].append(
                {"source": "github-write", "suite": finding["skillId"], "detail": str(exc), "stopped": False}
            )
            continue
        except GhError as exc:
            report["unknownEvidence"].append(
                {"source": "github-write", "suite": finding["skillId"], "detail": str(exc), "stopped": True}
            )
            return report, UNKNOWN_EXIT_CODE
        fill_report(report, suite_row)
    return report, (UNKNOWN_EXIT_CODE if report["unknownEvidence"] else 0)


def batch_stopped(report: dict) -> bool:
    """True when the batch stopped part way on a GitHub read or write, so later writes must not start."""
    return any(entry.get("stopped") for entry in report.get("unknownEvidence", []))


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
        new_payload, body, record_rows = layout(
            payload_now, updated_rows, previous_version=payload_now.get("previousVersion")
        )
        touches_records = record_rows is not None or "candidateRecords" in payload_now
        record_plan = records.plan_generation(_comments(gh, umbrella["number"]), record_rows) if touches_records else None
        # H1: an approved umbrella whose hashed payload changes is reset, exactly as the watcher's own
        # writes do. D1a: so is one whose stored digest does not match its payload. The reset lands before
        # the body write.
        if "upstream:approved" in label_names(umbrella) and (
            payload_tampered(payload_now) or payload_changed(payload_now, new_payload)
        ):
            _approval_reset(gh, umbrella["number"], {
                "payload": new_payload,
                "approvedVersion": payload_now.get("newVersion"),
                "changedFields": changed_fields(payload_now, new_payload),
                "resetRows": [],
            })
        _switch_records(gh, umbrella["number"], umbrella["title"], body, record_plan)
    except GhError as exc:
        return {**result, "outcome": "unknown", "detail": str(exc)}, UNKNOWN_EXIT_CODE
    return result, 0


