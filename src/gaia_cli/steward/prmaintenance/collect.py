"""Read-only GitHub collection for PR maintenance: the census and the executor's live snapshot.

Reads only (``GET``). Pagination is explicit ``page=N`` offset paging that ends on a short page and is
cross-checked against an independent total (the ``rel="last"`` page of a one-item listing), because a
``--paginate`` walk follows server-built next links that some proxies rewrite to unreachable paths.
A failed request, a short walk or a count that disagrees with the independent total leaves the census
incomplete: the sensor then reports coverage unknown, never an empty backlog.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from gaia_cli.steward.prmaintenance.census import SCHEMA_VERSION

PAGE = 100
MAX_PAGES = 30
CLOSED_WINDOW_ROWS = 60
HEADLINE = re.compile(r'page=(\d+)[^>]*>;\s*rel="last"')


class CollectError(RuntimeError):
    """A read failed. The caller records the census as incomplete; nothing is guessed."""


Api = Callable[[str, Mapping[str, Any] | None], tuple[Any, str]]


def ghApi(path: str, params: Mapping[str, Any] | None = None) -> tuple[Any, str]:
    """GET one REST path through the gh CLI. Returns (decoded JSON, raw header block)."""

    command = ["gh", "api", "-i", "-X", "GET", path]
    for key, value in (params or {}).items():
        command += ["-f", f"{key}={value}"]
    try:
        run = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CollectError(f"{path}: {type(exc).__name__}") from exc
    head, _, body = run.stdout.partition("\r\n\r\n") if "\r\n\r\n" in run.stdout else run.stdout.partition("\n\n")
    status = re.match(r"HTTP/\S+ (\d+)", head)
    if run.returncode != 0 or not status or not status.group(1).startswith("2"):
        raise CollectError(f"{path}: HTTP {status.group(1) if status else 'error'}")
    try:
        return (json.loads(body) if body.strip() else None), head
    except ValueError as exc:
        raise CollectError(f"{path}: unparsable body") from exc


def listAll(api: Api, path: str, params: Mapping[str, Any] | None = None, key: str | None = None) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        body, _ = api(path, {**(params or {}), "per_page": PAGE, "page": page})
        batch = body.get(key) if key and isinstance(body, dict) else body
        if not isinstance(batch, list):
            raise CollectError(f"{path}: unexpected page shape")
        rows.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < PAGE:
            return rows
    raise CollectError(f"{path}: page cap exceeded")


def independentTotal(api: Api, path: str, params: Mapping[str, Any] | None = None) -> int:
    """The listing's size by an independent route: a one-item listing's ``rel="last"`` page number."""

    body, head = api(path, {**(params or {}), "per_page": 1, "page": 1})
    found = HEADLINE.search(head or "")
    if found:
        return int(found.group(1))
    return len(body) if isinstance(body, list) else 0


def sha256(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def isoNow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def commitRow(item: Mapping[str, Any]) -> dict:
    commit = item.get("commit") or {}
    return {
        "sha": item.get("sha"), "authorLogin": (item.get("author") or {}).get("login"),
        "authorId": (item.get("author") or {}).get("id"), "authorType": (item.get("author") or {}).get("type"),
        "committerLogin": (item.get("committer") or {}).get("login"),
        "committerName": (commit.get("committer") or {}).get("name"), "parents": len(item.get("parents") or []),
        "verified": bool((commit.get("verification") or {}).get("verified")),
        "message": str(commit.get("message") or "")[:200],
    }


def threadsUnresolved(api: Api, repo: str, number: int) -> int | None:
    """Unresolved review threads, or None when the route cannot say (unknown, never zero)."""

    try:
        body, _ = api(f"repos/{repo}/pulls/{number}/ccr/review_threads", None)
    except CollectError:
        return None
    if not isinstance(body, list):
        return None
    return sum(1 for thread in body if isinstance(thread, dict) and thread.get("isResolved") is False)


def pullRow(api: Api, repo: str, number: int) -> dict:
    pull, _ = api(f"repos/{repo}/pulls/{number}", None)
    head, base = pull["head"], pull["base"]
    headSha = head["sha"]
    return {
        "number": number, "prId": str(pull.get("id") or ""), "repositoryId": str((base.get("repo") or {}).get("id") or ""),
        "title": pull.get("title") or "", "state": pull.get("state"), "draft": bool(pull.get("draft")),
        "merged": bool(pull.get("merged")),
        "author": {"login": (pull.get("user") or {}).get("login"), "id": (pull.get("user") or {}).get("id"),
                   "type": (pull.get("user") or {}).get("type")},
        "headRef": head.get("ref"), "headSha": headSha, "headRepo": (head.get("repo") or {}).get("full_name"),
        "baseRef": base.get("ref"), "baseSha": base.get("sha"), "labels": sorted(x["name"] for x in pull.get("labels") or []),
        "requestedReviewers": sorted(x["login"] for x in pull.get("requested_reviewers") or []),
        "mergeable": pull.get("mergeable"), "mergeableState": pull.get("mergeable_state"),
        "body": pull.get("body") or "", "bodySha256": sha256(pull.get("body")),
        "commits": [commitRow(c) for c in listAll(api, f"repos/{repo}/pulls/{number}/commits")],
        "files": [{"path": f.get("filename"), "status": f.get("status"), "additions": f.get("additions"),
                   "deletions": f.get("deletions"), "blobSha": f.get("sha")}
                  for f in listAll(api, f"repos/{repo}/pulls/{number}/files")],
        "reviews": [{"user": (r.get("user") or {}).get("login"), "state": r.get("state"), "commitId": r.get("commit_id"),
                     "authorAssociation": r.get("author_association"), "submittedAt": r.get("submitted_at"),
                     "body": str(r.get("body") or "")[:2000]}
                    for r in listAll(api, f"repos/{repo}/pulls/{number}/reviews")],
        "checkRuns": [{"name": c.get("name"), "status": c.get("status"), "conclusion": c.get("conclusion"),
                       "app": (c.get("app") or {}).get("slug")}
                      for c in listAll(api, f"repos/{repo}/commits/{headSha}/check-runs", key="check_runs")],
        "comments": [{"id": c.get("id"), "user": (c.get("user") or {}).get("login"), "body": c.get("body") or "",
                      "createdAt": c.get("created_at"), "authorAssociation": c.get("author_association")}
                     for c in listAll(api, f"repos/{repo}/issues/{number}/comments")],
        "reviewThreadsUnresolved": threadsUnresolved(api, repo, number),
        "updatedAt": pull.get("updated_at"), "mergedAt": pull.get("merged_at"),
        "mergeCommitSha": pull.get("merge_commit_sha") if pull.get("merged") else None,
    }


def protectionOf(api: Api, repo: str) -> dict:
    """Required checks and approvals from active rulesets (over-approximated: every active ruleset applies)."""

    required: set[str] = set()
    strict, approvals, complete = False, 0, True
    try:
        rulesets, _ = api(f"repos/{repo}/rulesets", None)
        for summary in rulesets or []:
            if summary.get("enforcement") != "active" or summary.get("target") != "branch":
                continue
            detail, _ = api(f"repos/{repo}/rulesets/{summary['id']}", None)
            for rule in detail.get("rules") or []:
                params = rule.get("parameters") or {}
                if rule.get("type") == "required_status_checks":
                    required |= {c.get("context") for c in params.get("required_status_checks") or [] if c.get("context")}
                    strict = strict or bool(params.get("strict_required_status_checks_policy"))
                if rule.get("type") == "pull_request":
                    approvals = max(approvals, int(params.get("required_approving_review_count") or 0))
    except (CollectError, KeyError, TypeError):
        complete = False
    classic = "unavailable"
    try:
        branch, _ = api(f"repos/{repo}/branches/main/protection", None)
        classic = "read"
        contexts = (branch.get("required_status_checks") or {}).get("contexts") or []
        required |= set(contexts)
    except CollectError:
        pass
    return {"complete": complete, "source": "rulesets", "classicProtection": classic,
            "requiredChecks": sorted(required), "strict": strict, "requiredApprovals": approvals}


def collectCensus(api: Api, repo: str, fetchHeads: Callable[[int], None] | None = None) -> dict:
    """The whole census for one repository. Raises ``CollectError`` only when nothing usable can be said."""

    total = independentTotal(api, f"repos/{repo}/pulls", {"state": "open"})
    listed = listAll(api, f"repos/{repo}/pulls", {"state": "open"})
    rows, failures = [], []
    for item in sorted(listed, key=lambda r: r["number"]):
        try:
            row = pullRow(api, repo, item["number"])
            rows.append(row)
        except (CollectError, KeyError) as exc:
            failures.append(f"#{item['number']}: {exc}")
            continue
        if fetchHeads is not None:
            fetchHeads(item["number"])
    repoInfo, _ = api(f"repos/{repo}", None)
    refs = sorted({row["baseRef"] for row in rows} | {repoInfo["default_branch"]})
    tips = {ref: api(f"repos/{repo}/branches/{ref}", None)[0]["commit"]["sha"] for ref in refs}
    closedPage, _ = api(f"repos/{repo}/pulls", {"state": "closed", "sort": "updated", "direction": "desc", "per_page": CLOSED_WINDOW_ROWS})
    closed = [{"number": item["number"], "state": "closed", "mergedAt": item.get("merged_at"),
               "mergeCommitSha": item.get("merge_commit_sha"), "headRef": (item.get("head") or {}).get("ref"),
               "title": item.get("title") or "", "body": item.get("body") or "", "closedAt": item.get("closed_at")}
              for item in (closedPage or []) if isinstance(item, dict)]
    expectedPages = max(1, math.ceil(total / PAGE))
    walkedPages = max(1, math.ceil(len(listed) / PAGE))
    return {
        "schemaVersion": SCHEMA_VERSION, "repo": repo, "fetchedAt": isoNow(), "defaultBranch": repoInfo["default_branch"],
        "baseTips": tips, "protection": protectionOf(api, repo),
        "completeness": {
            "pulls": {"complete": total == len(listed), "pagesFetched": walkedPages, "expectedPages": expectedPages,
                      "itemCount": len(rows), "independentTotal": total},
            "details": {"complete": not failures and len(rows) == len(listed), "expected": len(listed), "fetched": len(rows),
                        "failures": failures[:5]},
        },
        "pulls": rows, "recentlyClosed": closed,
    }


def closedRows(api: Api, repo: str) -> list[dict]:
    page, _ = api(f"repos/{repo}/pulls", {"state": "closed", "sort": "updated", "direction": "desc", "per_page": CLOSED_WINDOW_ROWS})
    return [{"number": item["number"], "state": "closed", "mergedAt": item.get("merged_at"),
             "mergeCommitSha": item.get("merge_commit_sha"), "headRef": (item.get("head") or {}).get("ref"),
             "title": item.get("title") or "", "body": item.get("body") or "", "closedAt": item.get("closed_at")}
            for item in (page or []) if isinstance(item, dict)]


def liveSnapshot(api: Api, repo: str, number: int, fetchHead: Callable[[int], None] | None = None):
    """A fresh, single-PR snapshot for the executor gate. Everything the gate decides on is read here, now."""

    from gaia_cli.steward.prmaintenance.gate import Snapshot

    row = pullRow(api, repo, number)
    if fetchHead is not None:
        fetchHead(number)
    tip = api(f"repos/{repo}/branches/{row['baseRef']}", None)[0]["commit"]["sha"]
    siblings = [{"number": item["number"], "state": item.get("state"), "headRef": (item.get("head") or {}).get("ref"),
                 "headSha": (item.get("head") or {}).get("sha"), "headRepo": ((item.get("head") or {}).get("repo") or {}).get("full_name"),
                 "baseRef": (item.get("base") or {}).get("ref"), "labels": sorted(x["name"] for x in item.get("labels") or []),
                 "author": {"login": (item.get("user") or {}).get("login"), "id": (item.get("user") or {}).get("id"),
                            "type": (item.get("user") or {}).get("type")}}
                for item in listAll(api, f"repos/{repo}/pulls", {"state": "open"})]
    # A replacement is only as trustworthy as its original: bring the original's FULL row (commits, files) when the body names it.
    named = re.search(r"gaia-steward:replaces repo=[A-Za-z0-9._/-]{1,100} pr=([0-9]{1,9}) head=[0-9a-f]{12}", str(row.get("body") or ""))
    if named is not None:
        try:
            full = pullRow(api, repo, int(named.group(1)))
            siblings = [full if sibling["number"] == full["number"] else sibling for sibling in siblings]
            if fetchHead is not None:
                fetchHead(full["number"])
        except (CollectError, KeyError):
            pass  # the original stays a thin row; the evaluator then reports the link as unproven
    return Snapshot(row=row, tips={row["baseRef"]: tip}, protection=protectionOf(api, repo), siblings=siblings,
                    closed=closedRows(api, repo), merged=bool(row.get("merged")), mergeCommitSha=row.get("mergeCommitSha"))


def mergeParents(api: Api, repo: str, sha: str) -> list[str]:
    body, _ = api(f"repos/{repo}/commits/{sha}", None)
    return [p["sha"] for p in (body or {}).get("parents") or []]


def checksAt(api: Api, repo: str, sha: str) -> str:
    """A truthful one-line summary of the checks on a commit. Pending is reported as pending, never as healthy."""

    try:
        runs = listAll(api, f"repos/{repo}/commits/{sha}/check-runs", key="check_runs")
    except CollectError as exc:
        return f"not observed ({exc})"
    if not runs:
        return "no check runs yet at this commit"
    tally: dict[str, int] = {}
    for run in runs:
        key = run.get("conclusion") if run.get("status") == "completed" else str(run.get("status"))
        tally[str(key)] = tally.get(str(key), 0) + 1
    return f"{len(runs)} check run(s) at {sha[:12]}: " + ", ".join(f"{n} {k}" for k, n in sorted(tally.items()))


def writeCensus(root: Path, document: Mapping[str, Any], relative: Path) -> Path:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(target)
    return target
