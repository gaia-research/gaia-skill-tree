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
from typing import Any

from scripts.lib.github_api import parse_owner_repo
from scripts.upstream_watcher import prechecks
from scripts.upstream_watcher.issuer import (
    _LABEL_VOCAB,
    _REVIEWER_ACTIONS,
    render_child_body,
)
from scripts.upstream_watcher.live import GhError, LiveGh, open_umbrellas, read_live

PAYLOAD_VERSION = 2
UNKNOWN_EXIT_CODE = 3
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
    return "<!-- gaia-upstream-payload\n" + json.dumps(payload, indent=2, ensure_ascii=False) + "\n-->"


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


def carry_forward(live: dict, prefix: str, state_of) -> list[dict]:
    """Unresolved rows of the newest closed umbrella for a suite, to seed a new umbrella.

    The source is the full closed ``upstream:release`` history (``closedUmbrellas``),
    never the 30-day window: an umbrella closed months ago still carries its
    unresolved rows, so closing an umbrella can never drop candidates. A carried
    row keeps its status, child link and firstSeenVersion, and records
    ``carriedFrom`` as the umbrella it was last carried from.
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
    rows = (parse_payload(newest.get("body")) or {}).get("candidates", [])
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


def build_payload(finding: dict, rows: list[dict], previous_version: str | None) -> dict:
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
    payload["payloadSha256"] = canonical_hash(payload)
    return payload


def render_batch_body(payload: dict) -> str:
    """Human-readable umbrella body with an independently addressable batch table."""
    rows = payload["candidates"]
    table_rows = []
    for row in rows:
        precheck = row.get("precheck", {})
        child = f"#{row['child']}" if row.get("child") else "—"
        table_rows.append(
            f"| `cand:{row['id']}` | `{row['suggestedId']}` | `{row['status']}` | "
            f"`{precheck.get('registry', 'unchecked')}` | `{precheck.get('tracked', 'none')}` | "
            f"`{precheck.get('priorDisposition', 'none')}` | {child} | "
            f"{row['firstSeenVersion']} → {row['lastSeenVersion']} |"
        )
    batch_table = (
        "| Row | Suggested ID | Status | Registry | Tracked | Prior | Child | Seen |\n"
        "|---|---|---|---|---|---|---|---|\n" + "\n".join(table_rows)
        if table_rows
        else "_No new components detected._"
    )
    liveness = payload.get("linkLiveness") or []
    drift = payload.get("nameDrift") or []
    carried_rows = [row for row in rows if row.get("carriedFrom")]
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


def plan_suite(finding: dict, live: dict, index: dict, probe=None) -> dict:
    """Compute the umbrella action for one update finding. Performs no writes.

    *probe* (``LiveGh.issue_state`` in a run) resolves child numbers the LIST
    snapshot does not hold. Its GhError propagates: unknown evidence, no writes.
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
    prior_rows = (previous_payload or {}).get("candidates", [])
    carried: list[dict] = []
    if umbrella is None:
        # A new umbrella starts from the closed one's unresolved rows, so closing an
        # umbrella can never drop candidates.
        carried = carry_forward(live, prefix, state_of)
        prior_rows = carried
    rows, added = merge_rows(prior_rows, incoming, new_version, dead=dead_children(prior_rows, state_of))
    payload = build_payload(finding, rows, previous_version=None)
    if umbrella is None:
        action = "create"
    elif (previous_payload or {}).get("payloadSha256") == payload["payloadSha256"] and umbrella["title"] == title:
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
        "body": render_batch_body(payload),
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


def write_umbrella(plan: dict, gh: LiveGh) -> str:
    """Execute a create/update plan. Returns the outcome label."""
    if plan["action"] == "create":
        number = gh.create_issue(plan["title"], ["upstream:release", "needs-triage"], plan["body"])
        plan["umbrella"] = number
        return "created"
    gh.edit_issue(plan["umbrella"], plan["title"], plan["body"])
    if plan["reset"]:
        gh.edit_labels(plan["umbrella"], add=["upstream:needs-info"], remove=["upstream:approved"])
    note = comment_for(plan)
    if note:
        gh.comment(plan["umbrella"], note)
    return "updated"


def process_suite(finding: dict, gh: LiveGh, index: dict, live: dict, apply: bool) -> tuple[dict, dict]:
    """Plan and (when apply) write one suite. Returns (suite report row, live snapshot)."""
    plan = plan_suite(finding, live, index, probe=gh.issue_state)
    outcome = "planned"
    if plan["action"] == "noop":
        outcome = "noop"
    elif apply:
        outcome = "raced-skip"
        for _attempt in range(2):
            if plan["action"] == "create":
                fresh = read_live(gh)
                if open_umbrellas(fresh["issues"], umbrella_prefix(plan["suite"])):
                    live = fresh
                    plan = plan_suite(finding, live, index, probe=gh.issue_state)
                    continue
                outcome = write_umbrella(plan, gh)
                break
            current = gh.get_issue(plan["umbrella"])
            if snapshot_of(current) != plan["snapshot"]:
                live = read_live(gh)
                plan = plan_suite(finding, live, index, probe=gh.issue_state)
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
    row = None
    for issue in live["issues"]:
        if issue.get("state") != "open" or "upstream:release" not in label_names(issue):
            continue
        payload = parse_payload(issue.get("body"))
        if not payload:
            continue
        for candidate in payload.get("candidates", []):
            if candidate["id"] == candidate_id:
                umbrella, row, payload_now = issue, candidate, payload
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
    rows = []
    for candidate in payload_now["candidates"]:
        if candidate["id"] == candidate_id:
            # An adopted child is tracked at once; a child created here is escalated.
            status = "escalated" if outcome == "created" else "tracked"
            candidate = {**candidate, "child": child_number, "status": status}
            if isinstance(candidate.get("precheck"), dict):
                candidate["precheck"] = {**candidate["precheck"], "tracked": f"child:#{child_number}"}
        rows.append(candidate)
    rebuilt = build_payload(payload_now, rows, previous_version=payload_now.get("previousVersion"))
    body = render_batch_body(rebuilt)
    gh.edit_issue(umbrella["number"], umbrella["title"], body)
    return result, 0
