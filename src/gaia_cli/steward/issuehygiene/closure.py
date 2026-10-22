"""Closure authority for issue hygiene (contract sections 3.4 and 3.5, lane B).

Only items the reconciler marked authority A, under an enabled rule, in a complete census,
become plans. ``executeClosure`` re-reads the live issue and writes nothing unless the
live state still matches the manifest snapshot. Every outcome is one JSON line in an
append-only receipts file. Issues are never deleted.

Closing is serialized per (key, issue) by a lock file next to the receipts. Under the lock the
closer re-reads the receipts and the live issue, so two closers cannot both comment or both
close. Closing comments preserve the full original candidate information, and a long payload
is split across marker-linked comments. The receipt records the sha256 of what was preserved.

Forge calls go through the small ``IssueForge`` protocol so the executor can be tested
with a fake. The GitHub REST implementation lives in ``scripts/steward_issue_reconcile.py``.
Lock files need POSIX ``fcntl``; the Steward runs on Linux.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol

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
from gaia_cli.steward.primitives.redact import scrub

RECEIPT_SCHEMA = "steward-issue-closure-receipt-v1"
MARKER_PREFIX = "<!-- gaia-steward-closure:"
PART_PREFIX = "<!-- gaia-steward-closure-part:"
# GitHub accepts comments up to 65,536 characters. Keep headroom under that limit.
COMMENT_LIMIT = 60_000
INLINE_LIMIT = 30_000
PART_SIZE = 40_000
OUTCOMES = ("closed", "stale-skip", "already-closed", "failed", "blocked", "blocked-identity")
DONE_OUTCOMES = ("closed", "already-closed")
COMMENT_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/(\d+)#issuecomment-(\d+)$")
COMMENT_ID = re.compile(r"issuecomment-(\d+)")
EVIDENCE_DETAIL_LIMIT = 300

REASONS = {
    RULE_A1: "The exact suggested-id registry record links to the same repo and file as the evidence URL (git ref may differ), so the candidate is already curated.",
    RULE_A2: "The suite registry version (or a merged sync PR) matches the umbrella payload, every candidate row is resolved, and no child intake remains open.",
    RULE_A3: "A newer open umbrella of the same suite carries the unresolved component adds and lists every remaining child.",
    RULE_A4: "A lower-numbered open child with the same candidate id and evidence URL stays canonical.",
    RULE_A5: "The gh-aw workflows this report describes are listed in policy and reported disabled by the census workflow listing.",
}


class ForgeBlockedError(Exception):
    """Auth, rate or transport failure: nothing about the item is known, so the batch stops."""


class ForgeItemError(Exception):
    """A failure that concerns one item only; the batch may continue."""


class ForgeIdentityError(ForgeItemError):
    """The live issue is not the one the plan names: locked, a pull request, renumbered or transferred."""


class IssueForge(Protocol):
    def getIssue(self, number: int) -> dict:
        """Live issue: number, title, state, stateReason, updatedAt, body, labels, locked, htmlUrl."""

    def listComments(self, number: int) -> list[dict]:
        """Comments as dicts with ``body``, ``url`` and ``author`` (the login) keys."""

    def addComment(self, number: int, body: str) -> str | None:
        """Post a comment; return its URL when the forge reports one."""

    def closeIssue(self, number: int, stateReason: str, duplicateOf: int | None = None) -> None:
        """Close with a GitHub state reason. Never deletes."""

    def whoami(self) -> str:
        """The login the forge writes as. Raises when it cannot be determined."""


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


def closureSha8(item: Mapping[str, Any]) -> str:
    """Eight hex digits that identify one closure decision, the value our closing markers carry.

    It covers the key, rule, issue, transition, proof evidence and preserved payload, and nothing that moves
    when we comment: not the manifest digest (which includes the census fetch time), not ``updatedAt``. A crash
    between our comment and our close therefore resumes on the same marker even after a census refresh, while
    a marker for a different decision (other evidence, other payload, other rule) is never proof.
    """
    transition = item["proposedTransition"]
    material = {
        "key": item["key"], "issue": item.get("issue"), "ruleId": item["ruleId"],
        "stateReason": transition["stateReason"], "duplicateOf": transition.get("duplicateOf"),
        "canonical": item.get("canonical"), "parent": item.get("parent"),
        "evidence": [[entry["type"], entry["ref"], entry.get("sha256")] for entry in item["evidence"]],
        "original": item["original"],
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]


def markerLine(key: str, sha8: str) -> str:
    return f"{MARKER_PREFIX}{key}:{sha8} -->"


def partMarkerLine(key: str, sha8: str, index: int, total: int) -> str:
    return f"{PART_PREFIX}{key}:{sha8}:{index}/{total} -->"


def fencedText(text: str) -> str:
    """Fence text in a block that its own backticks cannot close."""
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}"


def preservedTextOf(original: Mapping[str, Any]) -> str:
    """The preserved candidate information: the original payload as pretty-printed, sorted JSON."""
    return json.dumps(original, indent=2, sort_keys=True, ensure_ascii=False)


def chunked(text: str, size: int) -> list[str]:
    return [text[index:index + size] for index in range(0, len(text), size)] or [""]


def buildClosureComments(item: dict, manifest: dict) -> list[str]:
    """The closing comments, in posting order. The first carries the marker; later parts are linked by marker.

    Small preserved information sits inline in the first comment. Larger information is split into
    ``PART_SIZE`` pieces, each in its own comment. Concatenating the pieces reproduces the preserved text
    exactly, and its sha256 is recorded in the receipt.
    """
    sha8 = manifest["manifestSha256"][:8]
    key = item["key"]
    ruleId = item["ruleId"]
    transition = item["proposedTransition"]
    preserved = preservedTextOf(item["original"])
    digest = hashlib.sha256(preserved.encode("utf-8")).hexdigest()
    parts = chunked(preserved, PART_SIZE) if len(preserved) > INLINE_LIMIT else []
    closure = closureSha8(item)
    lines = [
        markerLine(key, closure),
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
        digestNote = f", sha256 {entry['sha256'][:12]}" if entry.get("sha256") else ""
        detail = scrub(str(entry.get("detail", "")))[:EVIDENCE_DETAIL_LIMIT]
        lines.append(f"- `{entry['ref']}` ({entry['type']}{digestNote}): {detail}")
    lines += ["", f"**Preserved candidate information** (sha256 `{digest}`, {len(preserved)} characters)", ""]
    if not parts:
        lines += ["<details><summary>Original payload</summary>", "", fencedText(preserved), "", "</details>", ""]
    else:
        lines += [
            f"The preserved candidate information is larger than one comment. It is split across {len(parts) + 1} "
            f"comments: this one and the {len(parts)} part comment(s) that follow, each marked "
            "`gaia-steward-closure-part`. Concatenated in order, they reproduce the sha256 above.",
            "",
        ]
    comments = ["\n".join(lines)]
    for index, text in enumerate(parts, start=1):
        comments.append("\n".join([
            partMarkerLine(key, closure, index, len(parts)),
            "",
            f"Preserved candidate information, part {index} of {len(parts)} (sha256 `{digest}`).",
            "",
            fencedText(text),
            "",
        ]))
    return comments


def buildClosureComment(item: dict, manifest: dict) -> str:
    """The first closing comment. Kept for callers that only need the marker-carrying comment."""
    return buildClosureComments(item, manifest)[0]


def preservedSha256Of(original: Mapping[str, Any]) -> str:
    return hashlib.sha256(preservedTextOf(original).encode("utf-8")).hexdigest()


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
        if item["ruleId"] == RULE_A3:
            # A3 needs its superseder open after the pass; a superseder closed by this plan is a refusal.
            superseder = byIssue.get(item["canonical"])
            if superseder is None or superseder["authority"] == "A":
                continue
        comments = buildClosureComments(item, manifest)
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
            "closureSha8": closureSha8(item),
            "preservedSha256": preservedSha256Of(item["original"]),
            "comment": comments[0],
            "comments": comments,
        })
    return plans


def closureCommentsFor(plan: Mapping[str, Any]) -> list[str]:
    """Rebuild a plan's closing comments from its observed fields.

    The sensor keeps debt state small by dropping the comments and keeping the manifest's own digest as
    ``reconciliationSha256``. Rebuilt this way the comments are identical to the ones ``planClosures``
    writes from the full manifest, so the markers still match.
    """
    item = {
        "key": plan["key"],
        "issue": plan["issue"],
        "ruleId": plan["ruleId"],
        "proposedTransition": {"stateReason": plan["stateReason"], "duplicateOf": plan.get("duplicateOf")},
        "parent": plan.get("parent"),
        "canonical": plan.get("canonical"),
        "evidence": plan["evidence"],
        "original": plan["original"],
    }
    return buildClosureComments(item, {"manifestSha256": plan["reconciliationSha256"]})


def closureCommentFor(plan: Mapping[str, Any]) -> str:
    """The first comment of ``closureCommentsFor``: the one carrying the marker."""
    return closureCommentsFor(plan)[0]


def commentIdFromUrl(url: Any) -> int | None:
    """The numeric id in a GitHub comment URL (``...#issuecomment-123``), or None."""
    if not isinstance(url, str):
        return None
    match = COMMENT_ID.search(url)
    return int(match.group(1)) if match else None


def urlNamesThisIssue(url: str, issue: int | None, repo: str | None) -> bool:
    match = COMMENT_URL.match(url)
    if match is None:
        return False
    owner, name, number = match.group(1), match.group(2), int(match.group(3))
    if issue is not None and number != issue:
        return False
    return repo is None or f"{owner}/{name}".lower() == str(repo).lower()


def closureProven(outcome: Mapping[str, Any], issue: int | None = None, repo: str | None = None) -> bool:
    """A closed outcome must carry exactly ONE proof of its closing comment.

    The proofs are a ``commentUrl`` that is a GitHub comment URL on this issue (and repo, when given), a
    positive ``commentId``, or ``markerVerified: true``. Two or more proofs are refused, and so is a
    proof that is present but wrong.
    """
    url = outcome.get("commentUrl")
    commentId = outcome.get("commentId")
    hasUrl = url not in (None, "")
    hasId = commentId is not None
    hasMarker = outcome.get("markerVerified") is True
    if hasUrl and not (isinstance(url, str) and urlNamesThisIssue(url, issue, repo)):
        return False
    if hasId and not (isinstance(commentId, int) and not isinstance(commentId, bool) and commentId > 0):
        return False
    return int(hasUrl) + int(hasId) + int(hasMarker) == 1


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


@contextmanager
def closureLock(receiptsPath: Path | str, key: str, issue: int) -> Iterator[None]:
    """Exclusive lock for one (key, issue) pair, held across check, comment, close and receipt."""
    path = Path(receiptsPath)
    lockDir = path.parent / ".locks"
    lockDir.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(f"{key}\n{issue}".encode("utf-8")).hexdigest()[:40] + ".lock"
    handle = os.open(lockDir / name, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        os.close(handle)


def buildReceipt(
    plan: dict, runId: str, outcome: str, now: Any, commentUrl: str | None, failure: str | None,
    commentId: int | None = None, markerVerified: bool = False, closer: str | None = None,
    preservedParts: int | None = None,
) -> dict:
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
        "preservedSha256": plan.get("preservedSha256"),
        "preservedParts": preservedParts,
        "closer": closer,
        "commentUrl": commentUrl,
        "commentId": commentId,
        "markerVerified": markerVerified,
        "closedAt": isoTime(now) if outcome == "closed" else None,
        "recordedAt": isoTime(now),
        "outcome": outcome,
        "failure": failure,
    }


def diffFields(plan: dict, live: dict, ownMarker: bool = False) -> list[str]:
    """Fields of the live issue that moved since the manifest snapshot.

    ``updatedAt`` is ignored only when our own marker comment for this plan explains it. Every
    other drift, title, body, labels or state included, stops the closure.
    """
    snapshot = plan["expectedSnapshot"]
    found = []
    if live.get("updatedAt") != snapshot.get("updatedAt") and not ownMarker:
        found.append("updatedAt")
    if bodySha256(live.get("body")) != snapshot.get("bodySha256"):
        found.append("bodySha256")
    if sorted(live.get("labels") or []) != sorted(snapshot.get("labels") or []):
        found.append("labels")
    liveTitle = live.get("title") if isinstance(live.get("title"), str) else ""
    if "titleSha256" in snapshot:
        titleMoved = hashlib.sha256(liveTitle.encode("utf-8")).hexdigest() != snapshot["titleSha256"]
    else:
        titleMoved = live.get("title") != snapshot.get("title")
    if titleMoved:
        found.append("title")
    return found


def findOwnMarker(comments: list[dict], key: str, sha8: str, closer: str | None) -> dict | None:
    """Our closing comment: the full marker for this key and manifest, authored by the closer identity.

    A foreign comment, another manifest's marker, or any comment when the closer is unknown is not proof.
    """
    if not closer:
        return None
    needle = markerLine(key, sha8)
    for comment in comments:
        if not isinstance(comment, dict) or not isinstance(comment.get("body"), str):
            continue
        if needle in comment["body"] and comment.get("author") == closer:
            return comment
    return None


def findPart(comments: list[dict], key: str, sha8: str, index: int, total: int, closer: str | None) -> dict | None:
    if not closer:
        return None
    needle = partMarkerLine(key, sha8, index, total)
    for comment in comments:
        if isinstance(comment, dict) and isinstance(comment.get("body"), str) and needle in comment["body"] \
                and comment.get("author") == closer:
            return comment
    return None


def findMarker(comments: list[dict], key: str) -> dict | None:
    """Any closing-comment marker for ``key``. Not proof by itself; kept for diagnostics only."""
    prefix = f"{MARKER_PREFIX}{key}:"
    for comment in comments:
        if isinstance(comment, dict) and isinstance(comment.get("body"), str) and prefix in comment["body"]:
            return comment
    return None


def identityProblem(live: Mapping[str, Any], issue: int) -> str | None:
    """Why the live issue is not the one the plan names, or None."""
    if live.get("locked") is True:
        return "issue is locked"
    if live.get("pullRequest") or live.get("isPullRequest") or live.get("pull_request"):
        return "row is a pull request"
    number = live.get("number")
    if number is not None and number != issue:
        return f"live number {number} is not {issue}"
    return None


def closerIdentity(forge: Any) -> str | None:
    """The login our comments are written as. None when it cannot be determined (then no marker is proof)."""
    try:
        value = forge.whoami()
    except Exception:  # noqa: BLE001 - an unknown closer is a fact, not an error to propagate
        return None
    return value if isinstance(value, str) and value.strip() else None


def executeClosure(plan: dict, forge: IssueForge, receiptsPath: Path | str, now: Any, runId: str = "") -> dict:
    """Close one planned issue after a live re-read, under a per-pair lock. Returns the receipt it appended.

    A pair the receipts already record as done is returned as ``resumed-done`` with no forge call and no
    new receipt. Ownership of the closing comment is decided by its author, not by its text alone.
    """
    if plan.get("authority") != "A" or plan.get("ruleId") not in KNOWN_RULE_IDS:
        raise ValueError("closure plans must carry authority A and a registered rule")
    issue = plan["issue"]
    key = plan["key"]
    comments = list(plan.get("comments") or [plan["comment"]])
    sha8 = plan["closureSha8"]
    total = len(comments)
    preservedParts = total

    def finish(outcome: str, commentUrl: str | None = None, failure: str | None = None,
               commentId: int | None = None, markerVerified: bool = False, closer: str | None = None) -> dict:
        receipt = buildReceipt(plan, runId, outcome, now, commentUrl, failure, commentId=commentId,
                               markerVerified=markerVerified, closer=closer, preservedParts=preservedParts)
        appendReceipt(receiptsPath, receipt)
        return receipt

    with closureLock(receiptsPath, key, issue):
        if resumeState(receiptsPath).isDone(key, issue):
            return {"key": key, "issue": issue, "outcome": "resumed-done"}
        try:
            live = forge.getIssue(issue)
        except ForgeIdentityError as exc:
            return finish("blocked-identity", failure=f"get-issue: {exc}")
        except ForgeBlockedError as exc:
            return finish("blocked", failure=f"get-issue: {exc}")
        except Exception as exc:  # item-local: continue with the batch
            return finish("failed", failure=f"get-issue: {exc}")

        problem = identityProblem(live, issue)
        if problem is not None:
            return finish("blocked-identity", failure=problem)
        if live.get("state") == "closed":
            return finish("already-closed")

        try:
            closer = closerIdentity(forge)
            listed = forge.listComments(issue)
        except ForgeBlockedError as exc:
            return finish("blocked", failure=f"list-comments: {exc}")
        except Exception as exc:  # item-local
            return finish("failed", failure=f"list-comments: {exc}")

        ownMarker = findOwnMarker(listed, key, sha8, closer)
        differences = diffFields(plan, live, ownMarker=ownMarker is not None)
        if live.get("state") != "open":
            differences.insert(0, "state")
        if differences:
            return finish("stale-skip", failure=",".join(differences), closer=closer)

        # Proof before close: our comment is identified by its marker and author on re-read, or we post it.
        commentUrl = None
        commentId = None
        markerVerified = False
        try:
            if ownMarker is not None:
                commentUrl = ownMarker.get("url")
                commentId = commentIdFromUrl(commentUrl)
                markerVerified = True
            else:
                commentUrl = forge.addComment(issue, comments[0])
                commentId = commentIdFromUrl(commentUrl)
                if commentUrl is None:
                    markerVerified = findOwnMarker(forge.listComments(issue), key, sha8, closer) is not None
                    if not markerVerified:
                        return finish("failed", failure="write: closing comment posted but not verifiable; issue left open",
                                      closer=closer)
            for index in range(2, total + 1):
                if findPart(listed, key, sha8, index, total, closer) is None:
                    forge.addComment(issue, comments[index - 1])
            forge.closeIssue(issue, plan["stateReason"], plan["duplicateOf"])
        except ForgeIdentityError as exc:
            return finish("blocked-identity", commentUrl, f"write: {exc}", commentId, markerVerified, closer)
        except ForgeBlockedError as exc:
            return finish("blocked", commentUrl, f"write: {exc}", commentId, markerVerified, closer)
        except Exception as exc:  # item-local
            return finish("failed", commentUrl, f"write: {exc}", commentId, markerVerified, closer)
        return finish("closed", commentUrl, None, commentId, markerVerified, closer)


def executeClosures(plans: list[dict], forge: IssueForge, receiptsPath: Path | str, now: Any, runId: str = "") -> list[dict]:
    """Run plans in order. Done pairs in the receipts file are skipped without any forge call.

    Stops after the first ``blocked`` receipt: auth or rate failures stop the batch. A ``blocked-identity``
    receipt is item-local and the batch continues.
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
    "COMMENT_LIMIT",
    "DONE_OUTCOMES",
    "ForgeBlockedError",
    "ForgeIdentityError",
    "ForgeItemError",
    "IssueForge",
    "PART_SIZE",
    "RECEIPT_SCHEMA",
    "ResumeState",
    "appendReceipt",
    "buildClosureComment",
    "buildClosureComments",
    "closureCommentFor",
    "closureCommentsFor",
    "closureLock",
    "closureSha8",
    "closureProven",
    "commentIdFromUrl",
    "executeClosure",
    "executeClosures",
    "identityProblem",
    "planClosures",
    "preservedSha256Of",
    "resumeState",
]
