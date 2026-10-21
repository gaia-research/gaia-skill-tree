#!/usr/bin/env python3
"""Reconcile the Steward issue census into a deterministic manifest (#2130).

Dry run by default and read-only: it reads the census, the registry and the workflow
files, then writes only the requested --out, --matrix and --summary outputs.

    PYTHONPATH=src python scripts/steward_issue_reconcile.py --out manifest.json --summary

Writes to GitHub need every one of: --apply-closures, --receipts PATH and
--i-understand-writes. Without a complete census they are refused (exit 3). Writes go
through GhForge, which is stdlib urllib with GH_TOKEN or GITHUB_TOKEN. It fails closed
when no token is set, and the token is never printed. Each closure re-reads the live
issue first (closure.executeClosure), so a stale manifest writes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from gaia_cli.steward.issuehygiene.census import loadCensus
from gaia_cli.steward.issuehygiene.closure import (
    ForgeBlockedError,
    ForgeItemError,
    executeClosures,
    planClosures,
)
from gaia_cli.steward.issuehygiene.hygienepolicy import HygienePolicy, loadHygienePolicy
from gaia_cli.steward.issuehygiene.reconcile import reconcile, workflowProbesFor
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.policy import StewardPolicy

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CENSUS = Path(".gaia/steward/inputs/github-issues.json")
DEFAULT_POLICY = Path("founder/steward/POLICY.yaml")
GITHUB_API = "https://api.github.com"
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_REFUSED = 3
PAGE_SIZE = 100
MAX_COMMENT_PAGES = 50
FAMILIES = ("child", "umbrella", "bootstrap", "botreport", "untracked")

Transport = Callable[[str, str, dict, bytes | None], tuple[int, dict, str]]


def urllibTransport(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, dict, str]:
    """One HTTP call. HTTP errors come back as a status; transport failures raise ForgeBlockedError."""
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
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

    def call(self, method: str, path: str, payload: dict | None = None) -> tuple[dict, Any]:
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
        status, responseHeaders, text = self.transport(method, f"{GITHUB_API}/repos/{self.repo}{path}", headers, body)
        if status in (401, 403, 429):
            raise ForgeBlockedError(f"http-{status}")
        if status >= 400:
            raise ForgeItemError(f"http-{status}")
        return responseHeaders, (json.loads(text) if text else None)

    def getIssue(self, number: int) -> dict:
        headers, data = self.call("GET", f"/issues/{number}")
        if not isinstance(data, dict) or "pull_request" in data:
            raise ForgeItemError("not-an-issue")
        return {
            "number": number,
            "title": data.get("title"),
            "state": data.get("state"),
            "stateReason": data.get("state_reason"),
            "updatedAt": data.get("updated_at"),
            "body": data.get("body") or "",
            "labels": sorted(label["name"] for label in data.get("labels", []) if isinstance(label, dict)),
        }

    def listComments(self, number: int) -> list[dict]:
        found: list[dict] = []
        for page in range(1, MAX_COMMENT_PAGES + 1):
            headers, data = self.call("GET", f"/issues/{number}/comments?per_page={PAGE_SIZE}&page={page}")
            rows = data if isinstance(data, list) else []
            found += [{"body": row.get("body") or "", "url": row.get("html_url")} for row in rows if isinstance(row, dict)]
            if len(rows) < PAGE_SIZE:
                return found
        raise ForgeBlockedError("comment-pagination-cap")

    def addComment(self, number: int, body: str) -> str | None:
        headers, data = self.call("POST", f"/issues/{number}/comments", {"body": body})
        return data.get("html_url") if isinstance(data, dict) else None

    def closeIssue(self, number: int, stateReason: str, duplicateOf: int | None = None) -> None:
        self.call("PATCH", f"/issues/{number}", {"state": "closed", "state_reason": stateReason})


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


def renderSummary(manifest: dict, plannedClosures: int | None = None) -> str:
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
    if plannedClosures is not None:
        lines.append(f"closure plans: {plannedClosures}")
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, forgeFactory: Callable[[str, str | None], Any] | None = None) -> int:
    args = parseArgs(argv)
    root = args.root.resolve()
    censusPath = args.census if args.census is not None else root / DEFAULT_CENSUS
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    if args.apply_closures and (not args.i_understand_writes or args.receipts is None):
        print("refusing: --apply-closures needs --receipts PATH and --i-understand-writes", file=sys.stderr)
        return EXIT_USAGE
    try:
        policy = loadPolicy(root, args.policy)
    except Exception as exc:  # policy problems fail loudly, never silently open writes
        print(f"policy error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    census = loadCensus(censusPath, now=now, maxAgeSeconds=policy.maxCensusAgeSeconds)
    registry = buildRegistryIndex(root)
    probes = workflowProbesFor(root, census, policy)
    manifest = reconcile(census, registry, policy, now, workflowDisabled=probes)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.matrix is not None:
        args.matrix.parent.mkdir(parents=True, exist_ok=True)
        args.matrix.write_text(renderMatrix(manifest), encoding="utf-8")

    plans = planClosures(manifest, policy) if args.apply_closures else None
    if args.summary:
        print(renderSummary(manifest, len(planClosures(manifest, policy))))

    if args.apply_closures:
        if manifest["censusStatus"] != "complete":
            print(f"refusing writes: census is {manifest['censusStatus']}", file=sys.stderr)
            return EXIT_REFUSED
        repo = args.repo or (census.document or {}).get("repo")
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        factory = forgeFactory or (lambda name, secret: GhForge(name, secret))
        try:
            forge = factory(repo, token)
        except ForgeBlockedError as exc:
            print(f"refusing writes: {exc}", file=sys.stderr)
            return EXIT_REFUSED
        runId = args.run_id or args.receipts.stem
        results = executeClosures(plans or [], forge, args.receipts, now, runId)
        counts: dict[str, int] = {}
        for result in results:
            counts[result["outcome"]] = counts.get(result["outcome"], 0) + 1
        print(json.dumps({"runId": runId, "plans": len(plans or []), "outcomes": dict(sorted(counts.items()))}, sort_keys=True))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
