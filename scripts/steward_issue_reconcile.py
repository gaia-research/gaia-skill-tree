#!/usr/bin/env python3
"""Reconcile the Steward issue census into a deterministic manifest (#2130).

Dry run by default and read-only: it reads the census, the registry and the workflow
files, then writes only the requested --out, --matrix and --summary outputs.

    PYTHONPATH=src python scripts/steward_issue_reconcile.py --out manifest.json --summary

Writes to GitHub need every one of: --apply-closures, --receipts PATH (inside the fixed receipts store
.gaia/steward/issue-hygiene/receipts), --i-understand-writes and --repo OWNER/NAME (the census repository).
--apply-closures performs every closure through the same gate as scripts/steward_issue_close.py
(executor.gateClosure): it refuses with exit 2 and makes no forge call unless the checkout's POLICY.yaml has
writesEnabled true and the rest of the gate holds. --now is refused on the apply path, since freshness uses
the real clock. --max-closures may only lower the policy cap. The pilot runs from a throwaway checkout with
writesEnabled set to true and maxClosuresPerRun set to 5, and that edit is never committed (contract section 6).

Writes go through GhForge, which is stdlib urllib with GH_TOKEN or GITHUB_TOKEN. It fails closed when no
token is set, never follows a redirect, and never prints the token. Each closure re-reads the live issue first
(closure.executeClosure), so a stale manifest writes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from gaia_cli.steward.clock import utcNow
from gaia_cli.steward.issuehygiene.census import loadCensus
from gaia_cli.steward.issuehygiene.closure import (
    ActionRefused,
    ForgeBlockedError,
    ForgeIdentityError,
    ForgeItemError,
    closureAction,
    executeClosure,
    planClosures,
)
from gaia_cli.steward.issuehygiene.executor import (
    AlreadyRecorded,
    gateClosure,
    receiptFor,
    sameRepo,
)
from gaia_cli.steward.issuehygiene.hygienepolicy import HygienePolicy, loadHygienePolicy
from gaia_cli.steward.issuehygiene.outcomes import OutcomeStoreError, donePairs
from gaia_cli.steward.issuehygiene.reconcile import reconcile, workflowProbesFor
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, observedDigest
from gaia_cli.steward.policy import PolicyError, StewardPolicy

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CENSUS = Path(".gaia/steward/inputs/github-issues.json")
DEFAULT_POLICY = Path("founder/steward/POLICY.yaml")
GITHUB_API = "https://api.github.com"
EXIT_OK = 0
PLAN_CEILING = 1_000_000
EXIT_USAGE = 2
EXIT_REFUSED = 2
EXIT_BLOCKED = 3
PAGE_SIZE = 100
MAX_COMMENT_PAGES = 50
FAMILIES = ("child", "umbrella", "bootstrap", "botreport", "untracked")

Transport = Callable[[str, str, dict, bytes | None], tuple[int, dict, str]]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse to follow any redirect. A 3xx then surfaces as an HTTP error, which the caller treats as a failure (L6)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401 - urllib hook
        return None


NO_REDIRECT_OPENER = urllib.request.build_opener(NoRedirect)


def urllibTransport(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, dict, str]:
    """One HTTP call. HTTP errors come back as a status; transport failures raise ForgeBlockedError."""
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with NO_REDIRECT_OPENER.open(request, timeout=30) as response:
            return response.status, {name.lower(): value for name, value in response.headers.items()}, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", errors="replace") if error.fp else ""
        return error.code, {name.lower(): value for name, value in (error.headers or {}).items()}, text
    except (urllib.error.URLError, OSError) as error:
        raise ForgeBlockedError(f"transport-{type(error).__name__}") from None


class GhForge:
    """Issue writes over the GitHub REST API. Stdlib only. Fails closed without a token."""

    def __init__(self, repo: str, token: str | None, transport: Transport | None = None):
        if not token:
            raise ForgeBlockedError("no-token: set GH_TOKEN or GITHUB_TOKEN")
        self.repo = repo
        self.token = token
        self.transport = transport or urllibTransport

    def call(self, method: str, path: str, payload: dict | None = None, scoped: bool = True) -> tuple[dict, Any]:
        """One REST call. Anything but a 2xx answer is an error; an unfollowed 3xx is never success (M1)."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gaia-steward-issue-reconcile",
            "Authorization": f"Bearer {self.token}",
        }
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        url = f"{GITHUB_API}/repos/{self.repo}{path}" if scoped else f"{GITHUB_API}{path}"
        status, responseHeaders, text = self.transport(method, url, headers, body)
        if status in (401, 403, 429):
            raise ForgeBlockedError(f"http-{status}")
        if not 200 <= status < 300:
            suffix = " unfollowed-redirect" if 300 <= status < 400 else ""
            raise ForgeItemError(f"http-{status}{suffix}")
        try:
            return responseHeaders, (json.loads(text) if text else None)
        except ValueError as exc:
            raise ForgeItemError("unparsable-response") from exc

    def whoami(self) -> str:
        """The login our comments are written as. Raises when it cannot be read."""
        _, data = self.call("GET", "/user", scoped=False)
        login = data.get("login") if isinstance(data, dict) else None
        if not isinstance(login, str) or not login.strip():
            raise ForgeItemError("whoami: no login")
        return login

    def getIssue(self, number: int) -> dict:
        """The live issue, with the identity fields the closure checks. Locked, renumbered, transferred or a
        pull request raise ForgeIdentityError: the plan names a different thing, so nothing may be written."""
        _, data = self.call("GET", f"/issues/{number}")
        if not isinstance(data, dict):
            raise ForgeItemError("not-an-issue")
        if "pull_request" in data:
            raise ForgeIdentityError("row is a pull request")
        if data.get("number") != number:
            raise ForgeIdentityError(f"live number {data.get('number')} is not {number}")
        htmlUrl = data.get("html_url") if isinstance(data.get("html_url"), str) else ""
        expected = f"https://github.com/{self.repo}/issues/{number}"
        if htmlUrl.split("#", 1)[0].rstrip("/").lower() != expected.lower():
            raise ForgeIdentityError("issue is no longer at the expected repository (transferred)")
        if data.get("locked") is True:
            raise ForgeIdentityError("issue is locked")
        return {
            "number": number,
            "nodeId": data.get("node_id"),
            "htmlUrl": htmlUrl,
            "locked": False,
            "title": data.get("title"),
            "state": data.get("state"),
            "stateReason": data.get("state_reason"),
            "updatedAt": data.get("updated_at"),
            "body": data.get("body") or "",
            "labels": sorted(label["name"] for label in data.get("labels", []) if isinstance(label, dict)),
        }

    def listComments(self, number: int) -> list[dict]:
        from steward_issue_census import Response, listAll

        # The issue's count cross-checks even a 200/empty/no-Link first page.
        _, issue = self.call("GET", f"/issues/{number}")
        count = issue.get("comments") if isinstance(issue, dict) else None
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ForgeBlockedError("comment-count-unavailable")
        start = f"{GITHUB_API}/repos/{self.repo}/issues/{number}/comments?per_page={PAGE_SIZE}&page=1"

        def fetch(url: str) -> Response:
            # listAll verifies continuation origin/path/query before calling us.
            path = url.removeprefix(f"{GITHUB_API}/repos/{self.repo}")
            headers, rows = self.call("GET", path)
            return Response(200, headers, json.dumps(rows))

        listing = listAll(start, fetch, expectedItems=count)
        if listing.reason or len(listing.rows) != count:
            raise ForgeBlockedError(f"comment-history-incomplete:{listing.reason or 'count-mismatch'}")
        found = []
        ids = set()
        for row in listing.rows:
            if not isinstance(row, dict) or not isinstance(row.get("body"), str) or isinstance(row.get("id"), bool) \
                    or not isinstance(row.get("id"), int) or row["id"] <= 0:
                raise ForgeBlockedError("malformed-comment-row")
            author = row.get("user")
            if not isinstance(author, dict) or not isinstance(author.get("login"), str) \
                    or not author["login"].strip() or row["id"] in ids:
                raise ForgeBlockedError("malformed-comment-identity")
            ids.add(row["id"])
            found.append({"body": row["body"], "url": row.get("html_url"), "author": author["login"],
                          "createdAt": row.get("created_at"), "updatedAt": row.get("updated_at")})
        return found

    def addComment(self, number: int, body: str) -> str | None:
        headers, data = self.call("POST", f"/issues/{number}/comments", {"body": body})
        return data.get("html_url") if isinstance(data, dict) else None

    def closeIssue(self, number: int, stateReason: str, duplicateOf: int | None = None) -> None:
        """Close, then confirm from the response that the issue is closed with the reason we asked for (M1)."""
        _, data = self.call("PATCH", f"/issues/{number}", {"state": "closed", "state_reason": stateReason})
        if not isinstance(data, dict) or data.get("state") != "closed" or data.get("state_reason") != stateReason:
            raise ForgeItemError("close-not-confirmed")


def loadPolicy(root: Path, policyPath: Path | None) -> HygienePolicy:
    """Default path goes through StewardPolicy (D1's loader). A custom path reads its issueHygiene block."""
    if policyPath is None:
        return StewardPolicy.load(root).issue_hygiene
    raw = yaml.safe_load(policyPath.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{policyPath} is not a YAML mapping")
    return loadHygienePolicy(raw.get("issueHygiene"))


def cell(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def transition(item: dict) -> str:
    transition = item["proposedTransition"]
    if transition["action"] != "close":
        return "keep"
    suffix = f" of #{transition['duplicateOf']}" if transition.get("duplicateOf") else ""
    return f"close as {transition['stateReason']}{suffix}"


def renderMatrix(manifest: dict) -> str:
    items = manifest["items"]
    pages = [items[index:index + PAGE_SIZE] for index in range(0, len(items), PAGE_SIZE)] or [[]]
    lines = [
        "# Steward issue reconciliation matrix",
        "",
        f"Manifest `{manifest['manifestSha256'][:12]}` · census `{manifest['censusStatus']}` · fetched `{manifest['censusFetchedAt']}` · {len(items)} items",
        "",
    ]
    for index, page in enumerate(pages, 1):
        if page:
            lines += [f"## Page {index} of {len(pages)} (issues {page[0]['issue']}-{page[-1]['issue']})", ""]
        else:
            lines += [f"## Page {index} of {len(pages)}", ""]
        lines += [
            "| # | key | kind | parent | state | authority | rule | evidence | expected transition | not proven / unknowns |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for item in page:
            evidence = "; ".join(f"{entry['type']}:{entry['ref']}" for entry in item["evidence"])
            notes = ", ".join(item["notProven"] + item["unknowns"])
            lines.append(
                f"| {item['issue']} | `{cell(item['key'])}` | {item['kind']} | {cell(item['parent'])} | {item['state']} | "
                f"{item['authority']} | {cell(item['ruleId'])} | {cell(evidence[:160])} | {cell(transition(item))} | {cell(notes[:200])} |"
            )
        lines.append("")
    lines += ["## Founder questions", ""]
    for question in manifest["founderQuestions"]:
        affected = ", ".join(f"#{number}" for number in question["affected"])
        lines.append(f"- **{question['id']}** ({affected}): {question['question']} Options: {', '.join(question['options'])}.")
    if not manifest["founderQuestions"]:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def renderSummary(manifest: dict, plannedClosures: int | None = None, writesEnabled: bool = True) -> str:
    byFamily: dict[str, dict[str, int]] = {family: {"total": 0, "A": 0, "B": 0, "C": 0, "none": 0, "not-evaluated": 0} for family in FAMILIES}
    rules: dict[str, int] = {}
    for item in manifest["items"]:
        row = byFamily.setdefault(item["kind"], {"total": 0, "A": 0, "B": 0, "C": 0, "none": 0, "not-evaluated": 0})
        row["total"] += 1
        row[item["authority"]] = row.get(item["authority"], 0) + 1
        if item["state"] == "not-evaluated":
            row["not-evaluated"] += 1
        if item["authority"] == "A":
            rules[item["ruleId"]] = rules.get(item["ruleId"], 0) + 1
    lines = [
        f"census {manifest['censusStatus']} (fetched {manifest['censusFetchedAt']}) · open issues {manifest['stats']['openIssues']} · "
        f"manifest {manifest['manifestSha256'][:12]}",
        "",
        f"{'family':<11}{'total':>6}{'A':>5}{'B':>5}{'C':>5}{'none':>6}{'not-eval':>10}",
    ]
    for family in FAMILIES:
        row = byFamily[family]
        lines.append(
            f"{family:<11}{row['total']:>6}{row['A']:>5}{row['B']:>5}{row['C']:>5}{row['none']:>6}{row['not-evaluated']:>10}"
        )
    children = [item for item in manifest["items"] if item["kind"] == "child"]
    lines += [
        "",
        f"children: A1-closable {sum(1 for item in children if item['ruleId'] == 'A1-child-curated')}, "
        f"A4-duplicate-closable {sum(1 for item in children if item['ruleId'] == 'A4-duplicate-child')}, "
        f"B {sum(1 for item in children if item['authority'] == 'B')}, C {sum(1 for item in children if item['authority'] == 'C')}",
        f"authority-A by rule: {json.dumps(rules, sort_keys=True) if rules else '{}'}",
    ]
    for item in manifest["items"]:
        if item["kind"] in ("umbrella", "botreport", "bootstrap"):
            label = item["suite"] or item["key"]
            lines.append(f"  #{item['issue']} {item['kind']} {label}: {item['authority']} {item['state']}" + (f" ({item['ruleId']})" if item["ruleId"] else ""))
    lines += ["", f"batches: {len(manifest['batches'])} (B children {sum(batch['size'] for batch in manifest['batches'])})"]
    lines.append(f"founder questions: {len(manifest['founderQuestions'])}")
    if plannedClosures is not None and writesEnabled:
        lines.append(f"closure plans: {plannedClosures}")
    elif plannedClosures is not None:
        lines.append(f"closure plans: 0 (issueHygiene.writesEnabled is false; {plannedClosures} proven closure(s) held as debt)")
    return "\n".join(lines)


def parseArgs(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile the Steward issue census (#2130). Dry run unless --apply-closures.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root (registry and workflows)")
    parser.add_argument("--census", type=Path, default=None, help=f"census file (default <root>/{DEFAULT_CENSUS})")
    parser.add_argument("--policy", type=Path, default=None, help=f"policy file (default <root>/{DEFAULT_POLICY} via StewardPolicy)")
    parser.add_argument("--now", default=None, help="RFC 3339 instant for census age checks (default: current UTC)")
    parser.add_argument("--out", type=Path, default=None, help="write the manifest JSON here")
    parser.add_argument("--matrix", type=Path, default=None, help="write the complete paginated matrix here")
    parser.add_argument("--summary", action="store_true", help="print per-family counts")
    parser.add_argument("--apply-closures", action="store_true", help="close Class A items on GitHub")
    parser.add_argument("--receipts", type=Path, default=None, help="append-only closure receipts JSONL")
    parser.add_argument("--i-understand-writes", action="store_true", help="required with --apply-closures")
    parser.add_argument("--repo", default=None, help="owner/repo (default: the census repo)")
    parser.add_argument("--run-id", default=None, help="receipt run id (default: receipts file stem)")
    parser.add_argument("--max-closures", type=int, default=None,
                        help="pilot cap for this run (1 to the policy maxClosuresPerRun; default: the policy value)")
    return parser.parse_args(argv)


def refuse(message: str) -> int:
    print(f"refusing: {message}", file=sys.stderr)
    return EXIT_REFUSED


def applyClosures(args: argparse.Namespace, root: Path, forgeFactory: Callable[[str, str | None], Any] | None) -> int:
    """--apply-closures: every closure goes through executor.gateClosure, the gate scripts/steward_issue_close.py uses.

    Every refusal here is checked before any forge is built, so a refused run makes no call to GitHub.
    """
    if args.now is not None:
        return refuse("--now is not accepted with --apply-closures; freshness uses the real clock")
    if not args.i_understand_writes or args.receipts is None:
        print("refusing: --apply-closures needs --receipts PATH and --i-understand-writes", file=sys.stderr)
        return EXIT_USAGE
    if args.census is not None:
        return refuse("--census is not accepted with --apply-closures; the checkout census is authoritative")
    if args.policy is not None:
        return refuse("--apply-closures reads the checkout's founder/steward/POLICY.yaml only; --policy is not accepted")
    if not args.repo:
        return refuse("--apply-closures needs --repo OWNER/NAME, the repository the closures are written to")
    relative = args.receipts
    if relative.is_absolute():
        try:
            relative = relative.relative_to(root)
        except ValueError:
            return refuse("the receipts path is outside this checkout and so outside the receipts store")
    try:
        receipt = receiptFor(root, relative.as_posix())
    except ActionRefused as exc:
        return refuse(str(exc))
    try:
        loaded = StewardPolicy.load(root)
    except PolicyError as exc:
        return refuse(f"steward policy unreadable: {exc}")
    if loaded.issue_hygiene_error:
        return refuse(loaded.issue_hygiene_error)
    policy = loaded.issue_hygiene
    if not policy.writesEnabled:
        return refuse("issueHygiene.writesEnabled is false; no closure is performed")
    now = utcNow()
    census = loadCensus(root / CENSUS_INPUT, now=now, maxAgeSeconds=policy.maxCensusAgeSeconds)
    if not census.status.complete:
        return refuse(f"census is {census.status.status}; nothing is proven")
    if not sameRepo((census.document or {}).get("repo"), args.repo):
        return refuse("--repo does not name the census repository")
    manifest = reconcile(census, buildRegistryIndex(root), policy, now, workflowDisabled=workflowProbesFor(census, policy))
    cap = policy.maxClosuresPerRun if args.max_closures is None else max(1, min(args.max_closures, policy.maxClosuresPerRun))
    try:
        recorded = donePairs(root)
    except OutcomeStoreError as exc:
        return refuse(f"closure outcomes unreadable: {exc}")
    plans = planClosures(manifest, replace(policy, maxClosuresPerRun=cap), done=recorded)
    digest = observedDigest(manifest)
    runId = args.run_id or receipt.stem
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    factory = forgeFactory or (lambda name, secret: GhForge(name, secret))
    try:
        forge = factory(args.repo, token)
    except ForgeBlockedError as exc:
        print(f"refusing writes: {exc}", file=sys.stderr)
        return EXIT_BLOCKED
    results: list[dict[str, Any]] = []
    for plan in plans:
        action = closureAction(plan, relative.as_posix(), digest, args.repo)
        try:
            gated = gateClosure(root, action, receipt, runId, now, args.repo)
        except AlreadyRecorded:
            results.append({"key": plan["key"], "issue": plan["issue"], "outcome": "resumed-done"})
            continue
        except ActionRefused as exc:
            print(f"refusing {plan['key']} (#{plan['issue']}): {exc}", file=sys.stderr)
            return EXIT_REFUSED
        try:
            result = executeClosure(
                gated, forge, receipt, now, runId, args.repo,
                root=root,
            )
        except ActionRefused as exc:
            print(f"refusing {plan['key']} (#{plan['issue']}): {exc}", file=sys.stderr)
            return EXIT_REFUSED
        results.append(result)
        if result["outcome"] == "blocked":
            break
    counts: dict[str, int] = {}
    for result in results:
        counts[result["outcome"]] = counts.get(result["outcome"], 0) + 1
    print(json.dumps({"runId": runId, "plans": len(plans), "outcomes": dict(sorted(counts.items()))}, sort_keys=True))
    return EXIT_OK


def main(argv: list[str] | None = None, forgeFactory: Callable[[str, str | None], Any] | None = None) -> int:
    args = parseArgs(argv)
    root = args.root.resolve()
    if args.apply_closures:
        return applyClosures(args, root, forgeFactory)
    censusPath = args.census if args.census is not None else root / DEFAULT_CENSUS
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else utcNow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    try:
        policy = loadPolicy(root, args.policy)
    except Exception as exc:  # policy problems fail loudly, never silently open writes
        print(f"policy error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    census = loadCensus(censusPath, now=now, maxAgeSeconds=policy.maxCensusAgeSeconds)
    registry = buildRegistryIndex(root)
    probes = workflowProbesFor(census, policy)
    manifest = reconcile(census, registry, policy, now, workflowDisabled=probes)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.matrix is not None:
        args.matrix.parent.mkdir(parents=True, exist_ok=True)
        args.matrix.write_text(renderMatrix(manifest), encoding="utf-8")
    if args.summary:
        proven = len(planClosures(manifest, replace(policy, writesEnabled=True, maxClosuresPerRun=PLAN_CEILING)))
        print(renderSummary(manifest, proven, writesEnabled=policy.writesEnabled))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
