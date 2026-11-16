"""Bounded, read-only runner visibility diagnosis. Never imports the watcher.

Only this module's fixed GETs and GraphQL query are issued. Response text, error
messages, cursors and untrusted headers are never serialized. Not a census or an
acceptance gate; agreement cannot establish causality or an atomic snapshot.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

API = "https://api.github.com"
MAX_PAGES = 10
MAX_BYTES = 4 * 1024 * 1024
QUERY = """query($owner:String!, $name:String!, $cursor:String, $size:Int!) {
  repository(owner:$owner, name:$name) {
    CONNECTION(states:OPEN, first:$size, after:$cursor) {
      totalCount pageInfo { hasNextPage endCursor }
      nodes { __typename number state }
    }
  }
}"""


class DiagnosticError(Exception):
    """Only fixed local error classes may leave the collection boundary."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def integer(value):
    return type(value) is int and value >= 0


def identity(row, kind=None):
    if not isinstance(row, dict):
        raise DiagnosticError("invalid-identity")
    kind = kind or ("PullRequest" if "pull_request" in row else "Issue")
    state = row.get("state")
    if (not integer(row.get("number")) or row["number"] == 0
            or state not in ("open", "OPEN")
            or ("__typename" in row and row["__typename"] != kind)):
        raise DiagnosticError("invalid-identity")
    return {"number": row["number"], "__typename": kind, "state": "OPEN"}


def nextPage(link, repo, repositoryId=None):
    """Bind EVERY link to this repository; return cursor only for in-memory use.

    Like the census's canonical projection, request the named repository path,
    not the numeric alias. Unlike its link-learned alias, require an id from the
    fixed repository GET. Do not import its raw-error/production collection path.
    """
    if not link:
        return None, None, None
    if len(link) > 16384:
        raise DiagnosticError("unsafe-link-size")
    pages, relations = [], set()
    nextNumber, nextCursor = None, None
    for part in link.split(","):
        match = re.fullmatch(r'\s*<([^<>]+)>;\s*rel="(next|prev|first|last)"\s*', part)
        if not match:
            raise DiagnosticError("invalid-link")
        url, rel = match.groups()
        if re.search(r"[\x00-\x20\x7f]", url):
            raise DiagnosticError("unsafe-link-encoding")
        try:
            parsed = urlsplit(url)
        except ValueError:
            raise DiagnosticError("unsafe-link-origin") from None
        if parsed.scheme != "https" or parsed.netloc != "api.github.com" or "#" in url:
            raise DiagnosticError("unsafe-link-origin")
        allowed = {f"/repos/{repo}/issues"}
        if integer(repositoryId) and repositoryId > 0:
            allowed.add(f"/repositories/{repositoryId}/issues")
        if parsed.path not in allowed:
            raise DiagnosticError("unsafe-link-repository-path")
        # Strict keys, singleton values and percent syntax; never discard an
        # unexpected filter. Only the observed optional after cursor is allowed.
        if (re.search(r"%(?![0-9A-Fa-f]{2})", parsed.query)
                or any(p.split("=", 1)[0] not in ("state", "per_page", "page", "after")
                       for p in parsed.query.split("&"))):
            raise DiagnosticError("unsafe-link-query")
        try:
            query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True,
                             max_num_fields=4, errors="strict")
        except (ValueError, UnicodeError):
            raise DiagnosticError("unsafe-link-query") from None
        if (set(query) not in ({"state", "per_page", "page"}, {"state", "per_page", "page", "after"})
                or query["state"] != ["open"] or query["per_page"] != ["100"]
                or len(query["page"]) != 1 or not re.fullmatch(r"[1-9][0-9]{0,5}", query["page"][0])):
            raise DiagnosticError("unsafe-link-query")
        cursor = query.get("after", [None])
        if len(cursor) != 1 or (cursor[0] is not None and not re.fullmatch(r"[A-Za-z0-9+/=_-]{1,2048}", cursor[0])):
            raise DiagnosticError("unsafe-link-cursor")
        if rel in relations:
            raise DiagnosticError("duplicate-link-relation")
        relations.add(rel)
        page = int(query["page"][0])
        # Artifact projection deliberately omits the opaque cursor.
        pages.append(f'<{API}/repos/{repo}/issues?state=open&per_page=100&page={page}>; rel="{rel}"')
        if rel == "next":
            nextNumber, nextCursor = page, cursor[0]
    return nextNumber, ", ".join(pages), nextCursor


class Probe:
    def __init__(self, repo, token, opener=None):
        if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", repo):
            raise DiagnosticError("invalid-repository")
        self.repo = repo
        self.token = token
        self.repositoryId = None
        self.opener = opener or build_opener(NoRedirect())
        self.deadline = time.monotonic() + 240
        self.requests = []

    def read(self, connection=None, cursor=None, size=100, page=None, after=None):
        record = {"surface": connection or ("rest-items" if page else "rest-count"),
                  "httpStatus": None, "errorClass": None}
        self.requests.append(record)
        try:
            remaining = self.deadline - time.monotonic()
            if len(self.requests) > 40 or remaining <= 0:
                raise DiagnosticError("budget-exhausted")
            if not self.token:
                raise DiagnosticError("missing-workflow-token")
            if connection:
                if connection not in ("issues", "pullRequests"):
                    raise DiagnosticError("invalid-connection")
                owner, name = self.repo.split("/")
                body = json.dumps({"query": QUERY.replace("CONNECTION", connection),
                                   "variables": {"owner": owner, "name": name,
                                                 "cursor": cursor, "size": size}}).encode()
                url, method = API + "/graphql", "POST"
            else:
                body, method = None, "GET"
                url = f"{API}/repos/{self.repo}"
                if page:
                    query = {"state": "open", "per_page": 100, "page": page}
                    if after is not None:
                        query["after"] = after
                    url += "/issues?" + urlencode(query)
            req = Request(url, data=body, method=method, headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json", "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Gaia-metadata-diagnostic"})
            with self.opener.open(req, timeout=min(30, remaining)) as response:
                record["httpStatus"] = response.status
                if response.status != 200:
                    raise DiagnosticError("http-non-200")
                if page:
                    requestId = response.headers.get("X-GitHub-Request-Id", "")
                    record["requestId"] = requestId if re.fullmatch(r"[A-Fa-f0-9:.-]{1,128}", requestId) else None
                    following, safeLink, nextCursor = nextPage(response.headers.get("Link"), self.repo, self.repositoryId)
                    record["link"] = safeLink
                    record["nextPage"] = following
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise DiagnosticError("response-too-large")
                data = json.loads(raw)
                if connection and (not isinstance(data, dict) or "errors" in data):
                    raise DiagnosticError("graphql-errors-or-partial")
                # Private continuation state never enters requests/artifact.
                return data, dict(record, _after=nextCursor) if page else record
        except HTTPError as exc:
            record["httpStatus"] = exc.code
            record["errorClass"] = "permission-denied" if exc.code in (401, 403) else "http-error"
            exc.close()
        except DiagnosticError as exc:
            record["errorClass"] = str(exc)  # fixed local literals only
        except Exception:
            record["errorClass"] = "transport-or-json-error"
        raise DiagnosticError(record["errorClass"])

    def count(self):
        data, _ = self.read()
        value = data.get("open_issues_count") if isinstance(data, dict) else None
        if not integer(value):
            raise DiagnosticError("missing-repository-count")
        repositoryId = data.get("id")
        if (integer(repositoryId) and repositoryId > 0
                and isinstance(data.get("full_name"), str)
                and data["full_name"].casefold() == self.repo.casefold()):
            if self.repositoryId is not None and self.repositoryId != repositoryId:
                raise DiagnosticError("repository-identity-unstable")
            self.repositoryId = repositoryId
        # Missing/invalid identity never authorizes a numeric alias.
        return value

    def connection(self, field, walk):
        result = {"totalCount": None, "pages": [], "nodes": [], "complete": False,
                  "collectionMode": "walk" if walk else "count-sample", "errorClass": None}
        cursor, seen, cursors = None, set(), set()
        try:
            for _ in range(MAX_PAGES if walk else 1):
                data, _ = self.read(field, cursor, 100 if walk else 1)
                conn = data.get("data", {}).get("repository", {}).get(field)
                if not isinstance(conn, dict) or not integer(conn.get("totalCount")):
                    raise DiagnosticError("missing-connection-count")
                if result["totalCount"] is not None and result["totalCount"] != conn["totalCount"]:
                    raise DiagnosticError("unstable-connection-count")
                result["totalCount"] = conn["totalCount"]
                info, nodes = conn.get("pageInfo"), conn.get("nodes")
                if (not isinstance(info, dict) or type(info.get("hasNextPage")) is not bool
                        or "endCursor" not in info or not isinstance(nodes, list)):
                    raise DiagnosticError("missing-page-fields")
                if (info["endCursor"] is not None and not isinstance(info["endCursor"], str)) or (
                        info["hasNextPage"] and (not info["endCursor"] or len(info["endCursor"]) > 2048)):
                    raise DiagnosticError("invalid-page-info")
                if walk and info["hasNextPage"] and len(nodes) != 100:
                    raise DiagnosticError("short-linked-connection-page")
                result["pages"].append({"hasNextPage": info["hasNextPage"],
                                        "endCursorPresent": bool(info["endCursor"])})
                if len(nodes) > (100 if walk else 1):
                    raise DiagnosticError("invalid-node-page")
                for node in nodes:
                    if not isinstance(node, dict) or "__typename" not in node:
                        raise DiagnosticError("missing-typename")
                    projected = identity(node, "Issue" if field == "issues" else "PullRequest")
                    if projected["number"] in seen:
                        raise DiagnosticError("duplicate-identity")
                    seen.add(projected["number"])
                    result["nodes"].append(projected)
                if not walk:
                    if (len(nodes) != min(1, result["totalCount"])
                            or info["hasNextPage"] != (result["totalCount"] > 1)):
                        raise DiagnosticError("incomplete-count-sample")
                    return result
                if not info["hasNextPage"]:
                    if len(seen) != result["totalCount"]:
                        raise DiagnosticError("incomplete-connection")
                    result["complete"] = True
                    return result
                following = info["endCursor"]
                if not isinstance(following, str) or not following or len(following) > 2048 or following in cursors or not nodes:
                    raise DiagnosticError("cursor-loop-or-invalid")
                cursors.add(following)
                cursor = following
            raise DiagnosticError("page-budget-exhausted")
        except DiagnosticError as exc:
            result["errorClass"] = str(exc)
        except Exception:
            result["errorClass"] = "missing-or-invalid-fields"
        return result

    def rest(self):
        result = {"nodes": [], "complete": False, "errorClass": None}
        page, seen, cursors, after = 1, set(), set(), None
        try:
            for _ in range(MAX_PAGES):
                rows, record = self.read(page=page, after=after)
                if not isinstance(rows, list) or len(rows) > 100:
                    raise DiagnosticError("invalid-rest-page")
                for row in rows:
                    node = identity(row)
                    if node["number"] in seen:
                        raise DiagnosticError("duplicate-identity")
                    seen.add(node["number"])
                    result["nodes"].append(node)
                following = record["nextPage"]
                if following is None:
                    result["complete"] = True  # transport end, NOT completeness acceptance
                    return result
                if following != page + 1 or len(rows) != 100:
                    raise DiagnosticError("loop-or-incomplete-page")
                after = record["_after"]
                if after is not None:
                    if after in cursors:
                        raise DiagnosticError("cursor-loop-or-invalid")
                    cursors.add(after)
                page = following
            raise DiagnosticError("page-budget-exhausted")
        except DiagnosticError as exc:
            result["errorClass"] = str(exc)
        return result

    def collect(self):
        report = {"diagnosticOnly": True, "acceptanceEligible": False, "p1Pass": False,
                  "status": "nonhealthy", "causality": "not-established", "failures": [],
                  "repositoryCounts": {}, "before": {}, "after": {}, "requests": self.requests}
        def count(phase):
            try:
                report["repositoryCounts"][phase] = {"value": self.count(), "errorClass": None}
            except DiagnosticError as exc:
                report["repositoryCounts"][phase] = {"value": None, "errorClass": str(exc)}
        count("before")
        report["before"] = {field: self.connection(field, True) for field in ("issues", "pullRequests")}
        report["rest"] = self.rest()
        report["after"] = {field: self.connection(field, False) for field in ("issues", "pullRequests")}
        count("after")
        failures = report["failures"]
        if any(r["errorClass"] for r in self.requests):
            failures.append("request-failure")
        counts = report["repositoryCounts"]
        if any(r["errorClass"] for r in counts.values()):
            failures.append("repository-count-unknown")
        elif counts["before"]["value"] != counts["after"]["value"]:
            failures.append("repository-count-unstable")
        rest = report["rest"]
        # Retained nodes are partial observations until the REST walk finishes.
        # Never present an incomplete/denied walk as an observed aggregate zero.
        report["restTypedCounts"] = {
            kind: sum(n["__typename"] == kind for n in rest["nodes"]) if rest["complete"] else None
            for kind in ("Issue", "PullRequest")
        }
        if not rest["complete"]:
            failures.append("rest-incomplete")
        comparisons = report["comparisons"] = {}
        for field in ("issues", "pullRequests"):
            before, after = report["before"][field], report["after"][field]
            if before["errorClass"] or after["errorClass"] or not before["complete"]:
                failures.append(field + "-unknown-or-incomplete")
            elif before["totalCount"] != after["totalCount"]:
                failures.append(field + "-count-unstable")
            comparison = comparisons[field + "Identities"] = {"status": "unknown", "reason": None}
            if not rest["complete"]:
                comparison["reason"] = "rest-incomplete"
            elif not before["complete"] or before["errorClass"]:
                comparison["reason"] = "before-connection-incomplete"
            else:
                same = {n["number"] for n in before["nodes"]} == {
                    n["number"] for n in rest["nodes"] if n["__typename"] == ("Issue" if field == "issues" else "PullRequest")}
                comparison["status"] = "agree" if same else "disagree"
                if not same:
                    failures.append(field + "-identity-disagreement")
            if comparison["status"] == "unknown":
                failures.append(field + "-identity-comparison-unknown")
        aggregate = comparisons["aggregateRest"] = {"status": "unknown", "reason": None}
        if not rest["complete"]:
            aggregate["reason"] = "rest-incomplete"
        elif counts["before"]["errorClass"] or counts["before"]["value"] is None:
            aggregate["reason"] = "repository-count-unknown"
        else:
            same = counts["before"]["value"] == len(rest["nodes"])
            aggregate["status"] = "agree" if same else "disagree"
            if not same:
                failures.append("aggregate-rest-disagreement")
        if aggregate["status"] == "unknown":
            failures.append("aggregate-rest-comparison-unknown")
        if not failures:
            report["status"] = "observations-agree-not-acceptance"
        return report


def main():
    # No argv/auth substitution surface. Workflow supplies its existing GITHUB_TOKEN.
    try:
        report = Probe(os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GH_TOKEN", "")).collect()
    except Exception:
        report = {"diagnosticOnly": True, "acceptanceEligible": False, "p1Pass": False,
                  "status": "nonhealthy", "failures": ["probe-initialization-or-internal-error"]}
    output = Path("generated-output/diagnostic-upstream-metadata.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "observations-agree-not-acceptance" else 3


if __name__ == "__main__":
    raise SystemExit(main())
