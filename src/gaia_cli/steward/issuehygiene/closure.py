"""Closure authority for issue hygiene (contract sections 3.4 and 3.5, lane B).

Only items the reconciler marked authority A, under an enabled rule, in a complete census,
become plans. ``executeClosure`` re-reads the live issue and writes nothing unless the
live state still matches the manifest snapshot. Every outcome is one JSON line in an
append-only receipts file. Issues are never deleted.

Forge calls go through the small ``IssueForge`` protocol so the executor can be tested
with a fake. The GitHub REST implementation lives in ``scripts/steward_issue_reconcile.py``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from gaia_cli.steward.issuehygiene.census import bodySha256
from gaia_cli.steward.issuehygiene.hygienepolicy import HygienePolicy, KNOWN_RULE_IDS
from gaia_cli.steward.issuehygiene.reconcile import (
    CLOSABLE_STATES,
    RULE_A1,
    RULE_A2,
    RULE_A3,
    RULE_A4,
    RULE_A5,
)

RECEIPT_SCHEMA = "steward-issue-closure-receipt-v1"
MARKER_PREFIX = "<!-- gaia-steward-closure:"
OUTCOMES = ("closed", "stale-skip", "already-closed", "failed", "blocked")
DONE_OUTCOMES = ("closed", "already-closed")

REASONS = {
    RULE_A1: "The exact suggested-id registry record links to the same evidence URL, so the candidate is already curated.",
    RULE_A2: "The suite registry version (or a merged sync PR) matches the umbrella payload and no child intake remains open.",
    RULE_A3: "A newer open umbrella of the same suite carries the unresolved component adds and lists every remaining child.",
    RULE_A4: "A lower-numbered open child with the same key and evidence URL stays canonical.",
    RULE_A5: "The gh-aw workflows this report describes are listed in policy and provably disabled in the checkout.",
}


class ForgeBlockedError(Exception):
    """Auth, rate or transport failure: nothing about the item is known, so the batch stops."""


class ForgeItemError(Exception):
    """A failure that concerns one item only; the batch may continue."""


class IssueForge(Protocol):
    def getIssue(self, number: int) -> dict:
        """Live issue: title, state, stateReason, updatedAt, body and labels (list of names)."""

    def listComments(self, number: int) -> list[dict]:
        """Comments as dicts with ``body`` and ``url`` keys."""

    def addComment(self, number: int, body: str) -> str | None:
        """Post a comment; return its URL when the forge reports one."""

    def closeIssue(self, number: int, stateReason: str, duplicateOf: int | None = None) -> None:
        """Close with a GitHub state reason. Never deletes."""


@dataclass(frozen=True)
class ResumeState:
    """Which (key, issue) pairs a receipts file already records as done."""

    done: frozenset
    corrupt: int = 0

    def isDone(self, key: str, issue: int) -> bool:
        return (key, issue) in self.done

    def keys(self) -> frozenset:
        return frozenset(key for key, issue in self.done)


def isoTime(now: Any) -> str:
    if isinstance(now, datetime):
        moment = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(now)


def buildClosureComment(item: dict, manifest: dict) -> str:
    """The receipt comment posted before closing. Carries the marker used for resume."""
    sha8 = manifest["manifestSha256"][:8]
    ruleId = item["ruleId"]
    transition = item["proposedTransition"]
    lines = [
        f"{MARKER_PREFIX}{item['key']}:{sha8} -->",
        "",
        "### Closed by the Gaia steward issue hygiene rule",
        "",
        f"Rule **{ruleId}** closed this issue because its proof held in reconciliation manifest `{sha8}`. "
        "**Nothing was deleted.** The preserved work is linked below. Reopen this issue to reverse the closure.",
        "",
        f"- **Reason:** {REASONS[ruleId]}",
        f"- **Closed as:** `{transition['stateReason']}`"
        + (f" (duplicate of #{transition['duplicateOf']})" if transition.get("duplicateOf") else ""),
    ]
    if item.get("parent") is not None:
        lines.append(f"- **Parent umbrella:** #{item['parent']}")
    if item.get("canonical") is not None:
        lines.append(f"- **Canonical:** #{item['canonical']}")
    lines += ["", "**Proof**", ""]
    for entry in item["evidence"]:
        digest = f", sha256 {entry['sha256'][:12]}" if entry.get("sha256") else ""
        lines.append(f"- `{entry['ref']}` ({entry['type']}{digest}): {entry['detail']}")
    payload = {
        "title": item["original"]["title"],
        "labels": item["original"]["labels"],
        "bodySha256": item["original"]["bodySha256"],
        "candidate": item["original"]["candidate"],
    }
    lines += [
        "",
        "<details><summary>Original payload</summary>",
        "",
        "```json",
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        "```",
        "</details>",
        "",
    ]
    return "\n".join(lines)


def planClosures(manifest: dict, policy: HygienePolicy) -> list[dict]:
    """Ordered closure plans for authority-A items, capped by ``maxClosuresPerRun``.

    Empty unless writes are enabled and the census is complete. Duplicate closures are
    planned only when their canonical item is itself not closed by this run.
    """
    if manifest.get("censusStatus") != "complete" or not policy.writesEnabled:
        return []
    byIssue = {item["issue"]: item for item in manifest["items"]}
    plans: list[dict] = []
    for item in sorted(manifest["items"], key=lambda entry: entry["issue"]):
        if len(plans) >= policy.maxClosuresPerRun:
            break
        if item["authority"] != "A" or item["ruleId"] is None or not policy.ruleEnabled(item["ruleId"]):
            continue
        transition = item["proposedTransition"]
        if transition["action"] != "close" or item["state"] not in CLOSABLE_STATES:
            continue
        if item["ruleId"] == RULE_A4:
            canonical = byIssue.get(item["canonical"])
            if canonical is None or canonical["authority"] == "A":
                continue
        plans.append({
            "key": item["key"],
            "issue": item["issue"],
            "ruleId": item["ruleId"],
            "authority": "A",
            "state": item["state"],
            "stateReason": transition["stateReason"],
            "duplicateOf": transition.get("duplicateOf"),
            "parent": item["parent"],
            "canonical": item["canonical"],
            "reason": REASONS[item["ruleId"]],
            "expectedSnapshot": item["snapshot"],
            "original": item["original"],
            "evidence": item["evidence"],
            "comment": buildClosureComment(item, manifest),
        })
    return plans


def resumeState(receiptsPath: Path | str) -> ResumeState:
    """Read a receipts file and report which (key, issue) pairs are already done. Never raises."""
    path = Path(receiptsPath)
    if not path.is_file():
        return ResumeState(frozenset(), 0)
    done = set()
    corrupt = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            receipt = json.loads(line)
        except json.JSONDecodeError:
            corrupt += 1
            continue
        if not isinstance(receipt, dict):
            corrupt += 1
            continue
        if receipt.get("outcome") in DONE_OUTCOMES and isinstance(receipt.get("key"), str) and isinstance(receipt.get("issue"), int):
            done.add((receipt["key"], receipt["issue"]))
    return ResumeState(frozenset(done), corrupt)


def appendReceipt(receiptsPath: Path | str, receipt: dict) -> None:
    """Append one JSON line and fsync. A torn last line from a crash is terminated first."""
    path = Path(receiptsPath)
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = ""
    if path.is_file() and path.stat().st_size > 0:
        with open(path, "rb") as handle:
            handle.seek(-1, os.SEEK_END)
            if handle.read(1) != b"\n":
                prefix = "\n"
    line = prefix + json.dumps(receipt, sort_keys=True, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def buildReceipt(plan: dict, runId: str, outcome: str, now: Any, commentUrl: str | None, failure: str | None) -> dict:
    assert outcome in OUTCOMES, outcome
    return {
        "schemaVersion": RECEIPT_SCHEMA,
        "runId": runId,
        "key": plan["key"],
        "issue": plan["issue"],
        "ruleId": plan["ruleId"],
        "evidence": plan["evidence"],
        "parent": plan["parent"],
        "canonical": plan["canonical"],
        "reason": plan["reason"],
        "stateReason": plan["stateReason"],
        "duplicateOf": plan["duplicateOf"],
        "before": {"snapshot": plan["expectedSnapshot"]},
        "originalPayload": plan["original"],
        "commentUrl": commentUrl,
        "closedAt": isoTime(now) if outcome == "closed" else None,
        "recordedAt": isoTime(now),
        "outcome": outcome,
        "failure": failure,
    }


def diffFields(plan: dict, live: dict) -> list[str]:
    snapshot = plan["expectedSnapshot"]
    found = []
    if live.get("updatedAt") != snapshot.get("updatedAt"):
        found.append("updatedAt")
    if bodySha256(live.get("body")) != snapshot.get("bodySha256"):
        found.append("bodySha256")
    if sorted(live.get("labels") or []) != sorted(snapshot.get("labels") or []):
        found.append("labels")
    if live.get("title") != snapshot.get("title"):
        found.append("title")
    return found


def findMarker(comments: list[dict], key: str) -> dict | None:
    prefix = f"{MARKER_PREFIX}{key}:"
    for comment in comments:
        if isinstance(comment, dict) and isinstance(comment.get("body"), str) and prefix in comment["body"]:
            return comment
    return None


def executeClosure(plan: dict, forge: IssueForge, receiptsPath: Path | str, now: Any, runId: str = "") -> dict:
    """Close one planned issue after a live re-read. Returns the receipt it appended."""
    if plan.get("authority") != "A" or plan.get("ruleId") not in KNOWN_RULE_IDS:
        raise ValueError("closure plans must carry authority A and a registered rule")
    issue = plan["issue"]

    def finish(outcome: str, commentUrl: str | None = None, failure: str | None = None) -> dict:
        receipt = buildReceipt(plan, runId, outcome, now, commentUrl, failure)
        appendReceipt(receiptsPath, receipt)
        return receipt

    try:
        live = forge.getIssue(issue)
    except ForgeBlockedError as exc:
        return finish("blocked", failure=f"get-issue: {exc}")
    except Exception as exc:  # item-local: continue with the batch
        return finish("failed", failure=f"get-issue: {exc}")

    if live.get("state") == "closed":
        return finish("already-closed")
    differences = diffFields(plan, live)
    if live.get("state") != "open":
        differences.insert(0, "state")
    if differences:
        return finish("stale-skip", failure=",".join(differences))

    commentUrl = None
    try:
        existing = findMarker(forge.listComments(issue), plan["key"])
        if existing is None:
            commentUrl = forge.addComment(issue, plan["comment"])
        else:
            commentUrl = existing.get("url")
        forge.closeIssue(issue, plan["stateReason"], plan["duplicateOf"])
    except ForgeBlockedError as exc:
        return finish("blocked", commentUrl, f"write: {exc}")
    except Exception as exc:  # item-local
        return finish("failed", commentUrl, f"write: {exc}")
    return finish("closed", commentUrl)


def executeClosures(plans: list[dict], forge: IssueForge, receiptsPath: Path | str, now: Any, runId: str = "") -> list[dict]:
    """Run plans in order. Done pairs in the receipts file are skipped without any forge call.

    Stops after the first ``blocked`` receipt: auth or rate failures stop the batch.
    """
    state = resumeState(receiptsPath)
    results: list[dict] = []
    for plan in plans:
        if state.isDone(plan["key"], plan["issue"]):
            results.append({"key": plan["key"], "issue": plan["issue"], "outcome": "resumed-done"})
            continue
        receipt = executeClosure(plan, forge, receiptsPath, now, runId)
        results.append(receipt)
        if receipt["outcome"] == "blocked":
            break
    return results


__all__ = [
    "DONE_OUTCOMES",
    "ForgeBlockedError",
    "ForgeItemError",
    "IssueForge",
    "RECEIPT_SCHEMA",
    "ResumeState",
    "appendReceipt",
    "buildClosureComment",
    "executeClosure",
    "executeClosures",
    "planClosures",
    "resumeState",
]
