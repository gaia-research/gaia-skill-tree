"""Sealed read-only GitHub issue and upstream ports for hosted P2 weekly census.

Zero ``LiveGh`` import, zero ``subprocess`` import, zero mutating methods.
Rejects redirects, foreign endpoints, duplicate JSON keys, query/filter drift,
credentials in URLs, cursor loops, and incomplete/uncorroborated walks.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Mapping
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, OpenerDirector, Request, build_opener

from scripts.lib.github_api import GitHubFetchError, GitHubNotFound
from scripts.steward_issue_census import (
    FetchError,
    Response,
    linkRelations,
    listAll,
    lowerHeaders,
    parseLinks,
    splitLinkValues,
)
from scripts.upstream_watcher import weekly_reducer
from scripts.upstream_watcher.live import GhError, GhNotFound, UnknownEvidenceError
from scripts.upstream_watcher.weekly_release_proof import (
    ReleaseHttpObservation,
    RepoMetadataObservation,
)

API = "https://api.github.com"
RAW_HOST = "raw.githubusercontent.com"
PER_PAGE = 100
MAX_PAGES = 100
MAX_BYTES = 4 * 1024 * 1024
USER_AGENT = "gaia-hosted-readonly-census/1.0"

_REPO_RE = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+")

_GQL_OPEN_TOTALS = (
    "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){"
    "id nameWithOwner "
    "issues(states:OPEN){totalCount} pullRequests(states:OPEN){totalCount}}}"
)
_GQL_CLOSED_TOTALS = (
    "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){"
    "id nameWithOwner "
    "issues(states:CLOSED){totalCount} pullRequests(states:[CLOSED,MERGED]){totalCount}}}"
)

_TREE_URL_RE = re.compile(r"^/repos/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/git/trees/[^/?#]+$")
_RAW_PATH_RE = re.compile(r"^/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/.+$")


class _NoRedirect(HTTPRedirectHandler):
    """Refuse every 3xx redirect rather than following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _is_non_bool_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate-json-key")
        result[key] = value
    return result


def _loads_strict_json(raw_text: str) -> Any:
    return json.loads(raw_text, object_pairs_hook=_no_duplicate_keys)


def _check_safe_url_basics(url: str, *, expected_host: str) -> Any:
    if not isinstance(url, str) or not url or len(url) > 8192:
        raise GhError("unsafe-url-length")
    if re.search(r"[\x00-\x20\x7f]", url) or "#" in url:
        raise GhError("unsafe-url-encoding")
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise GhError("unsafe-url-parse") from None
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != expected_host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
    ):
        raise GhError("unsafe-url-origin")
    if re.search(r"%(?![0-9A-Fa-f]{2})", parsed.query):
        raise GhError("unsafe-url-encoding")
    return parsed


def _validate_rest_issues_url(
    url: str,
    repo: str,
    repository_id: int | None,
    *,
    expected_state: str,
) -> None:
    parsed = _check_safe_url_basics(url, expected_host="api.github.com")
    allowed_paths = {f"/repos/{repo}/issues"}
    if _is_non_bool_int(repository_id) and repository_id > 0:
        allowed_paths.add(f"/repositories/{repository_id}/issues")
    if parsed.path not in allowed_paths:
        raise GhError("unsafe-link-repository-path")
    allowed_keys = {"state", "per_page", "page", "after", "before"}
    if any(p.split("=", 1)[0] not in allowed_keys for p in parsed.query.split("&")):
        raise GhError("unsafe-link-query")
    try:
        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=5,
            errors="strict",
        )
    except (ValueError, UnicodeError):
        raise GhError("unsafe-link-query") from None
    if query.get("state") != [expected_state] or query.get("per_page") != [str(PER_PAGE)]:
        raise GhError("unsafe-link-query-filter")
    if any(len(v) != 1 for v in query.values()):
        raise GhError("unsafe-link-query-duplicate")
    if "page" in query and not re.fullmatch(r"[1-9][0-9]{0,5}", query["page"][0]):
        raise GhError("unsafe-link-page")
    if "after" in query and "before" in query:
        raise GhError("unsafe-link-cursor")
    for key in ("after", "before"):
        if key in query:
            val = query[key][0]
            if not val or len(val) > 2048 or re.search(r"[\x00-\x20\x7f]", val):
                raise GhError("unsafe-link-cursor")


def _validate_links(
    link: str,
    repo: str,
    repository_id: int | None,
    *,
    expected_state: str,
) -> None:
    if not link:
        return
    if len(link) > 16384:
        raise GhError("unsafe-link-size")
    values = splitLinkValues(link)
    if not values:
        raise GhError("invalid-link")
    relations: set[str] = set()
    for url, params in values:
        _validate_rest_issues_url(
            url,
            repo,
            repository_id,
            expected_state=expected_state,
        )
        rels = linkRelations(params)
        if not rels or any(rel not in ("next", "prev", "first", "last") for rel in rels):
            raise GhError("invalid-link")
        for rel in rels:
            if rel in relations:
                raise GhError("duplicate-link-relation")
            relations.add(rel)


def _validate_rest_comments_url(
    url: str,
    repo: str,
    repository_id: int | None,
    number: int,
) -> None:
    parsed = _check_safe_url_basics(url, expected_host="api.github.com")
    allowed_paths = {f"/repos/{repo}/issues/{number}/comments"}
    if _is_non_bool_int(repository_id) and repository_id > 0:
        allowed_paths.add(f"/repositories/{repository_id}/issues/{number}/comments")
    if parsed.path not in allowed_paths:
        raise GhError("unsafe-comment-link-repository-path")
    allowed_keys = {"per_page", "page", "after", "before"}
    if not parsed.query or any(p.split("=", 1)[0] not in allowed_keys for p in parsed.query.split("&")):
        raise GhError("unsafe-comment-link-query")
    try:
        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=4,
            errors="strict",
        )
    except (ValueError, UnicodeError):
        raise GhError("unsafe-comment-link-query") from None
    if query.get("per_page") != [str(PER_PAGE)]:
        raise GhError("unsafe-comment-link-query-filter")
    if any(len(v) != 1 for v in query.values()):
        raise GhError("unsafe-comment-link-query-duplicate")
    if "page" in query and not re.fullmatch(r"[1-9][0-9]{0,5}", query["page"][0]):
        raise GhError("unsafe-comment-link-page")
    if "after" in query and "before" in query:
        raise GhError("unsafe-comment-link-cursor")
    for key in ("after", "before"):
        if key in query:
            val = query[key][0]
            if not val or len(val) > 2048 or re.search(r"[\x00-\x20\x7f]", val):
                raise GhError("unsafe-comment-link-cursor")


def _validate_comment_links(
    link: str,
    repo: str,
    repository_id: int | None,
    number: int,
) -> None:
    if not link:
        return
    if len(link) > 16384:
        raise GhError("unsafe-comment-link-size")
    values = splitLinkValues(link)
    if not values:
        raise GhError("invalid-comment-link")
    relations: set[str] = set()
    for url, params in values:
        _validate_rest_comments_url(url, repo, repository_id, number)
        rels = linkRelations(params)
        if not rels or any(rel not in ("next", "prev", "first", "last") for rel in rels):
            raise GhError("invalid-comment-link")
        for rel in rels:
            if rel in relations:
                raise GhError("duplicate-comment-link-relation")
            relations.add(rel)


def _read_bounded_response(response: Any) -> bytes:
    raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise GhError("response-too-large")
    return raw


def _issue_label_names(issue: Mapping[str, Any]) -> set[str]:
    raw = issue.get("labels")
    if not isinstance(raw, list):
        raise GhError("malformed-issue-labels")
    names: set[str] = set()
    for entry in raw:
        if isinstance(entry, dict):
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                raise GhError("malformed-issue-labels")
            names.add(name)
        elif isinstance(entry, str) and entry.strip():
            names.add(entry)
        else:
            raise GhError("malformed-issue-labels")
    return names


class ReadOnlyIssuePort:
    """Sealed read-only GitHub issue/PR port for hosted P2 census.

    Exposes only ``{repo, list_issues, get_issue, list_comments, child_state}``.
    Forbids subclassing.
    """

    __slots__ = (
        "repo",
        "_token",
        "_opener",
        "_repository_id",
        "_repository_node_id",
        "_max_requests",
        "_requests_used",
        "_deadline",
        "_closed_cache",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("ReadOnlyIssuePort cannot be subclassed")

    def __init__(
        self,
        repo: str,
        token: str,
        *,
        opener: OpenerDirector | None = None,
        max_requests: int = 80,
        deadline_seconds: float = 240.0,
    ) -> None:
        if not isinstance(repo, str) or not _REPO_RE.fullmatch(repo):
            raise GhError("invalid-repository")
        if not isinstance(token, str) or not token.strip():
            raise GhError("missing-workflow-token")
        if not _is_non_bool_int(max_requests) or max_requests < 1:
            raise GhError("invalid-request-budget")
        self.repo = repo
        self._token = token
        self._opener = opener if opener is not None else build_opener(_NoRedirect())
        self._repository_id: int | None = None
        self._repository_node_id: str | None = None
        self._max_requests = max_requests
        self._requests_used = 0
        self._deadline = time.monotonic() + deadline_seconds
        self._closed_cache: list[dict[str, Any]] | None = None

    def _matches_repo_url(self, url: Any, suffix: str = "") -> bool:
        if not isinstance(url, str):
            return False
        low = url.casefold()
        if low == f"{API}/repos/{self.repo}{suffix}".casefold():
            return True
        if self._repository_id is not None and low == f"{API}/repositories/{self._repository_id}{suffix}".casefold():
            return True
        return False

    def _consume_budget(self) -> float:
        remaining = self._deadline - time.monotonic()
        if self._requests_used >= self._max_requests or remaining <= 0:
            raise GhError("budget-exhausted")
        self._requests_used += 1
        return min(30.0, remaining)

    def _http_request(
        self,
        url: str,
        *,
        method: str = "GET",
        body_bytes: bytes | None = None,
    ) -> Response:
        timeout = self._consume_budget()
        _check_safe_url_basics(url, expected_host="api.github.com")
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }
        if body_bytes is not None:
            headers["Content-Type"] = "application/json"
        req = Request(url, data=body_bytes, method=method, headers=headers)
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                status = resp.status
                if 300 <= status < 400:
                    raise GhError("redirected")
                if status != 200:
                    raise GhError(f"http-{status}")
                raw = _read_bounded_response(resp)
                resp_headers = lowerHeaders(resp.headers.items())
                return Response(status, resp_headers, raw.decode("utf-8"))
        except HTTPError as exc:
            code = exc.code
            exc.close()
            if 300 <= code < 400:
                raise GhError("redirected") from None
            if code in (301, 404, 410):
                raise GhNotFound(f"http-{code}", str(code)) from None
            if code == 429:
                raise GhError("rate-limited") from None
            if code in (401, 403):
                raise GhError(f"permission-or-forbidden-{code}") from None
            raise GhError(f"http-{code}") from None
        except UnicodeDecodeError:
            raise GhError("invalid-utf8-response") from None
        except GhError:
            raise
        except Exception:
            raise GhError("transport-error") from None

    def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        resp = self._http_request(f"{API}/graphql", method="POST", body_bytes=payload)
        try:
            data = _loads_strict_json(resp.body)
        except ValueError:
            raise GhError("graphql-invalid-json") from None
        if not isinstance(data, dict) or data.get("errors"):
            raise GhError("graphql-errors-or-partial")
        return data

    def _pin_repository_metadata(self) -> tuple[int, int]:
        try:
            resp = self._http_request(f"{API}/repos/{self.repo}")
            data = _loads_strict_json(resp.body)
        except GhNotFound:
            raise GhError("repository-not-found") from None
        except ValueError:
            raise GhError("repository-invalid-json") from None
        if not isinstance(data, dict):
            raise GhError("repository-invalid-shape")
        repo_id = data.get("id")
        node_id = data.get("node_id")
        full_name = data.get("full_name")
        open_count = data.get("open_issues_count")
        if (
            not _is_non_bool_int(repo_id)
            or repo_id < 1
            or not isinstance(node_id, str)
            or not node_id
            or len(node_id) > 128
            or re.search(r"[\x00-\x20\x7f]", node_id)
            or not isinstance(full_name, str)
            or full_name.casefold() != self.repo.casefold()
            or not _is_non_bool_int(open_count)
        ):
            raise GhError("invalid-repository-identity-or-count")
        if self._repository_id is not None and self._repository_id != repo_id:
            raise GhError("repository-identity-unstable")
        if self._repository_node_id is not None and self._repository_node_id != node_id:
            raise GhError("repository-identity-unstable")
        self._repository_id = repo_id
        self._repository_node_id = node_id
        return repo_id, open_count

    def _typed_totals(self, state: str) -> tuple[int, int]:
        if self._repository_node_id is None:
            raise GhError("repository-node-id-not-pinned")
        owner, name = self.repo.split("/", 1)
        query = _GQL_OPEN_TOTALS if state == "open" else _GQL_CLOSED_TOTALS
        data = self._graphql(query, {"owner": owner, "name": name})
        try:
            repo_node = data["data"]["repository"]
            if not isinstance(repo_node, dict):
                raise TypeError("repository-node-not-dict")
            gql_id = repo_node.get("id")
            gql_name = repo_node.get("nameWithOwner")
            issues_total = repo_node["issues"]["totalCount"]
            prs_total = repo_node["pullRequests"]["totalCount"]
        except (KeyError, TypeError):
            raise GhError(f"{state}-connection-counts-unavailable") from None
        if (
            not isinstance(gql_id, str)
            or gql_id != self._repository_node_id
            or not isinstance(gql_name, str)
            or gql_name.casefold() != self.repo.casefold()
        ):
            raise GhError(f"{state}-graphql-repository-identity-mismatch")
        if not _is_non_bool_int(issues_total) or not _is_non_bool_int(prs_total):
            raise GhError(f"{state}-connection-counts-invalid")
        return issues_total, prs_total

    def _walk_rest_issues(
        self,
        start_url: str,
        *,
        expected_state: str,
        expected_items: int | None = None,
    ) -> Any:
        cursors: set[tuple[str, str]] = set()
        pages_fetched = 0
        boundary_error: str | None = None

        def fetch(url: str) -> Response:
            nonlocal pages_fetched, boundary_error
            try:
                if pages_fetched >= MAX_PAGES:
                    raise GhError("page-budget-exhausted")
                pages_fetched += 1
                _validate_rest_issues_url(
                    url,
                    self.repo,
                    self._repository_id,
                    expected_state=expected_state,
                )
                query = parse_qs(urlsplit(url).query)
                for key in ("after", "before"):
                    if key in query:
                        marker = (key, query[key][0])
                        if marker in cursors:
                            raise GhError("cursor-loop")
                        cursors.add(marker)
                resp = self._http_request(url)
                _validate_links(
                    resp.headers.get("link", ""),
                    self.repo,
                    self._repository_id,
                    expected_state=expected_state,
                )
                try:
                    parsed = _loads_strict_json(resp.body)
                except ValueError:
                    raise GhError("invalid-rest-json") from None
                if not isinstance(parsed, list) or len(parsed) > PER_PAGE:
                    raise GhError("invalid-rest-page-shape")
                return resp
            except GhError as exc:
                boundary_error = str(exc)
                raise FetchError("readonly-port-refused") from None

        listing = listAll(start_url, fetch, expectedItems=expected_items)
        if listing.reason is not None:
            raise GhError(boundary_error or f"listing-incomplete:{listing.reason}")
        if any(size != PER_PAGE for size in listing.pageSizes[:-1]):
            raise GhError("short-nonfinal-page")
        seen_numbers: set[int] = set()
        for row in listing.rows:
            if not isinstance(row, dict):
                raise GhError("malformed-issue-row")
            num = row.get("number")
            if type(num) is not int or num <= 0 or num in seen_numbers:
                raise GhError("malformed-or-duplicate-issue-number")
            if row.get("state") != expected_state:
                raise GhError("issue-state-mismatch")
            _issue_label_names(row)
            if "repository_url" in row and not self._matches_repo_url(row.get("repository_url")):
                raise GhError("issue-repository-mismatch")
            if "url" in row and not self._matches_repo_url(row.get("url"), f"/issues/{num}"):
                raise GhError("issue-identity-mismatch")
            seen_numbers.add(num)
        return listing

    def _observed_type_counts(self, rows: list[dict[str, Any]]) -> tuple[int, int]:
        issues = sum("pull_request" not in row for row in rows)
        prs = sum("pull_request" in row for row in rows)
        return issues, prs

    def _verified_open(self) -> list[dict[str, Any]]:
        _, open_count = self._pin_repository_metadata()
        start_url = f"{API}/repos/{self.repo}/issues?state=open&per_page={PER_PAGE}&page=1"
        before_totals = self._typed_totals("open")
        listing = self._walk_rest_issues(
            start_url,
            expected_state="open",
            expected_items=sum(before_totals),
        )
        after_totals = self._typed_totals("open")
        observed = self._observed_type_counts(listing.rows)
        if not (before_totals == after_totals == observed):
            raise GhError("open-typed-count-mismatch")
        if open_count == sum(before_totals):
            self._pin_repository_metadata()
            return listing.rows
        before_2 = self._typed_totals("open")
        listing_2 = self._walk_rest_issues(
            start_url,
            expected_state="open",
            expected_items=sum(before_2),
        )
        after_2 = self._typed_totals("open")
        observed_2 = self._observed_type_counts(listing_2.rows)
        if not (
            before_totals == before_2 == after_2 == observed_2
            and [r["number"] for r in listing.rows] == [r["number"] for r in listing_2.rows]
        ):
            raise GhError("open-unconfirmed-count-drift")
        self._pin_repository_metadata()
        return listing_2.rows

    def _verified_closed_unfiltered(self) -> list[dict[str, Any]]:
        """Complete unfiltered closed REST walk bracketed by typed GraphQL counts."""
        if self._closed_cache is not None:
            return self._closed_cache
        self._pin_repository_metadata()
        start_url = f"{API}/repos/{self.repo}/issues?state=closed&per_page={PER_PAGE}&page=1"
        before_totals = self._typed_totals("closed")
        listing = self._walk_rest_issues(
            start_url,
            expected_state="closed",
            expected_items=sum(before_totals),
        )
        if listing.pageSizes and listing.pageSizes[-1] == PER_PAGE:
            raise GhError("closed-listing-ends-on-full-page")
        after_totals = self._typed_totals("closed")
        observed = self._observed_type_counts(listing.rows)
        if not (before_totals == after_totals == observed):
            raise GhError("closed-typed-count-mismatch")
        # Re-pin repository ID after walk to confirm identity stability.
        self._pin_repository_metadata()
        self._closed_cache = listing.rows
        return listing.rows

    def _filter_rows_in_ram(
        self,
        rows: list[dict[str, Any]],
        *,
        since: str | None = None,
        labels: str | None = None,
    ) -> list[dict[str, Any]]:
        filtered = rows
        if since is not None:
            try:
                since_dt = weekly_reducer.parse_strict_utc(since)
            except (TypeError, ValueError) as exc:
                raise GhError("invalid-since-timestamp") from exc
            kept: list[dict[str, Any]] = []
            for row in filtered:
                raw_upd = row.get("updated_at")
                if not isinstance(raw_upd, str):
                    raise GhError("missing-updated-at")
                try:
                    upd_dt = weekly_reducer.parse_strict_utc(raw_upd)
                except (TypeError, ValueError) as exc:
                    raise GhError("invalid-updated-at") from exc
                if upd_dt >= since_dt:
                    kept.append(row)
            filtered = kept
        if labels:
            wanted = {lbl for lbl in labels.split(",") if lbl}
            filtered = [row for row in filtered if wanted <= _issue_label_names(row)]
        return list(filtered)

    def list_issues(
        self,
        state: str,
        since: str | None = None,
        labels: str | None = None,
    ) -> list[dict[str, Any]]:
        if state == "open":
            rows = self._verified_open()
            return self._filter_rows_in_ram(rows, since=since, labels=labels)
        if state == "closed":
            rows = self._verified_closed_unfiltered()
            return self._filter_rows_in_ram(rows, since=since, labels=labels)
        raise GhError("unsupported-issue-state")

    def get_issue(self, number: int) -> dict[str, Any]:
        if type(number) is not int or number < 1:
            raise GhError("invalid-issue-number")
        resp = self._http_request(f"{API}/repos/{self.repo}/issues/{number}")
        try:
            data = _loads_strict_json(resp.body)
        except ValueError:
            raise GhError("issue-invalid-json") from None
        if not isinstance(data, dict) or type(data.get("number")) is not int or data.get("number") != number:
            raise GhError("issue-identity-mismatch")
        if "pull_request" in data:
            raise GhError("issue-is-pull-request")
        if data.get("state") not in ("open", "closed"):
            raise GhError("issue-invalid-state")
        _issue_label_names(data)
        if not self._matches_repo_url(data.get("url"), f"/issues/{number}"):
            raise GhError("issue-identity-mismatch")
        if "repository_url" in data and not self._matches_repo_url(data.get("repository_url")):
            raise GhError("issue-repository-mismatch")
        return data

    def child_state(self, number: int) -> str:
        try:
            issue = self.get_issue(number)
        except GhNotFound:
            return "absent"
        if issue.get("state") != "closed":
            return "open"
        labels = _issue_label_names(issue)
        return "closed-rejected" if "upstream:rejected" in labels else "closed"

    def list_comments(self, number: int) -> list[dict[str, Any]]:
        if type(number) is not int or number < 1:
            raise GhError("invalid-issue-number")
        items: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        visited_urls: set[str] = set()
        url = f"{API}/repos/{self.repo}/issues/{number}/comments?per_page={PER_PAGE}&page=1"
        pages_fetched = 0
        last_links: dict[str, str] = {}
        last_batch_len = 0

        for _ in range(MAX_PAGES):
            if url in visited_urls:
                raise GhError("comments-next-loop")
            visited_urls.add(url)
            _validate_rest_comments_url(url, self.repo, self._repository_id, number)
            try:
                resp = self._http_request(url)
                batch_rows = _loads_strict_json(resp.body)
            except GhNotFound:
                raise GhError("comments-not-found") from None
            except ValueError:
                raise GhError("comments-invalid-json") from None
            if not isinstance(batch_rows, list) or len(batch_rows) > PER_PAGE:
                raise GhError("comments-invalid-page-shape")
            link_header = resp.headers.get("link", "")
            _validate_comment_links(link_header, self.repo, self._repository_id, number)
            if pages_fetched > 0 and len(batch_rows) == 0:
                raise GhError("comments-empty-linked-page")
            for row in batch_rows:
                if not isinstance(row, dict):
                    raise GhError("comments-malformed-row")
                cid = row.get("id")
                if not _is_non_bool_int(cid) or cid < 1 or cid in seen_ids:
                    raise GhError("comments-duplicate-or-invalid-id")
                if not isinstance(row.get("body"), str):
                    raise GhError("comments-malformed-body")
                if not self._matches_repo_url(row.get("issue_url"), f"/issues/{number}"):
                    raise GhError("comments-issue-identity-mismatch")
                seen_ids.add(cid)
            items.extend(batch_rows)
            pages_fetched += 1
            last_batch_len = len(batch_rows)
            last_links = parseLinks(link_header)
            if "next" in last_links:
                if len(batch_rows) != PER_PAGE:
                    raise GhError("comments-short-nonfinal-page")
                url = last_links["next"]
                continue
            break
        else:
            raise GhError("comment-page-budget-exhausted")

        if "last" not in last_links and last_batch_len > 0:
            probe_url = f"{API}/repos/{self.repo}/issues/{number}/comments?per_page={PER_PAGE}&page={pages_fetched + 1}"
            try:
                probe_resp = self._http_request(probe_url)
                probe_rows = _loads_strict_json(probe_resp.body)
            except GhNotFound:
                raise GhError("comments-probe-not-found") from None
            except ValueError:
                raise GhError("comments-probe-invalid-json") from None
            if not isinstance(probe_rows, list):
                raise GhError("comments-probe-invalid-shape")
            if probe_rows:
                raise GhError("comments-unlinked-continuation")
        return items


class HostedUpstreamClient:
    """Sealed tokenless read-only upstream client for hosted census.

    Never accepts or sends campaign tokens on public upstream requests.
    Rejects redirects, foreign origins, duplicate JSON keys, and excessive bytes.
    """

    __slots__ = (
        "_opener",
        "_max_requests",
        "_requests_used",
        "_deadline",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("HostedUpstreamClient cannot be subclassed")

    def __init__(
        self,
        *,
        opener: OpenerDirector | None = None,
        max_requests: int = 400,
        deadline_seconds: float = 240.0,
    ) -> None:
        if not _is_non_bool_int(max_requests) or max_requests < 1:
            raise UnknownEvidenceError("invalid-request-budget")
        self._opener = opener if opener is not None else build_opener(_NoRedirect())
        self._max_requests = max_requests
        self._requests_used = 0
        self._deadline = time.monotonic() + deadline_seconds

    def _consume_budget(self) -> float:
        remaining = self._deadline - time.monotonic()
        if self._requests_used >= self._max_requests or remaining <= 0:
            raise UnknownEvidenceError("upstream-budget-exhausted")
        self._requests_used += 1
        return min(30.0, remaining)

    def _api_get_raw(self, url: str) -> tuple[int, dict[str, str], Any | None, bool]:
        timeout = self._consume_budget()
        _check_safe_url_basics(url, expected_host="api.github.com")
        req = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                status = resp.status
                resp_headers = lowerHeaders(resp.headers.items())
                if 300 <= status < 400:
                    return status, resp_headers, None, True
                raw = _read_bounded_response(resp)
                parsed = _loads_strict_json(raw.decode("utf-8"))
                if not isinstance(parsed, dict):
                    return status, resp_headers, None, False
                return status, resp_headers, parsed, False
        except HTTPError as exc:
            status = exc.code
            resp_headers = lowerHeaders(exc.headers.items() if exc.headers is not None else [])
            body_obj: Any = None
            try:
                raw = _read_bounded_response(exc)
                parsed = _loads_strict_json(raw.decode("utf-8"))
                if isinstance(parsed, dict):
                    body_obj = parsed
            except Exception:
                body_obj = None
            exc.close()
            return status, resp_headers, body_obj, (300 <= status < 400)
        except GhError as exc:
            raise UnknownEvidenceError(str(exc)) from None
        except Exception:
            raise UnknownEvidenceError("upstream-transport-or-json-error") from None

    def fetch_release_observations(
        self,
        owner: str,
        repo: str,
    ) -> tuple[ReleaseHttpObservation, RepoMetadataObservation | None]:
        """Read ``/releases/latest`` (and ``/repos/{owner}/{repo}`` on 404) as proof observations."""
        if not _REPO_RE.fullmatch(f"{owner}/{repo}"):
            raise UnknownEvidenceError("invalid-upstream-repository")
        canonical_repo = f"{owner}/{repo}".lower()
        rel_url = f"{API}/repos/{owner}/{repo}/releases/latest"
        rel_status, rel_headers, rel_body, rel_redir = self._api_get_raw(rel_url)
        latest_obs = ReleaseHttpObservation(
            requested_url=rel_url,
            requested_repository=canonical_repo,
            status_code=rel_status,
            redirected=rel_redir,
            body=rel_body,
            headers=rel_headers,
        )
        meta_obs: RepoMetadataObservation | None = None
        if rel_status == 404 and not rel_redir:
            repo_url = f"{API}/repos/{owner}/{repo}"
            m_status, _m_headers, m_body, m_redir = self._api_get_raw(repo_url)
            meta_obs = RepoMetadataObservation(
                requested_url=repo_url,
                requested_repository=canonical_repo,
                status_code=m_status,
                redirected=m_redir,
                body=m_body,
            )
        return latest_obs, meta_obs

    def fetch_json(self, url: str, *, strict: bool = True) -> dict[str, Any]:
        """Strict tokenless tree JSON fetch for ``enumerate_component_tree`` / ``walk_truncated_tree``."""
        parsed = _check_safe_url_basics(url, expected_host="api.github.com")
        if not _TREE_URL_RE.fullmatch(parsed.path):
            raise GitHubFetchError("disallowed-upstream-tree-url")
        if parsed.query and parsed.query != "recursive=1":
            raise GitHubFetchError("disallowed-upstream-tree-query")
        try:
            status, headers, body, redir = self._api_get_raw(url)
        except UnknownEvidenceError as exc:
            raise GitHubFetchError(str(exc)) from None
        if redir:
            raise GitHubFetchError("redirected", status=status, headers=headers)
        if status == 404:
            raise GitHubNotFound("http-404", status=404, headers=headers)
        if status != 200 or not isinstance(body, dict):
            msg = str(body.get("message") or "") if isinstance(body, dict) else ""
            raise GitHubFetchError(f"http-{status}", status=status, headers=headers, body=msg)
        return body

    def head_check(self, url: str) -> int | None:
        """Tokenless HEAD check restricted to ``raw.githubusercontent.com``."""
        try:
            timeout = self._consume_budget()
            parsed = _check_safe_url_basics(url, expected_host=RAW_HOST)
            if parsed.query or not _RAW_PATH_RE.fullmatch(parsed.path):
                return None
            req = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
            with self._opener.open(req, timeout=timeout) as resp:
                if 300 <= resp.status < 400:
                    return None
                return resp.status
        except HTTPError as exc:
            code = exc.code
            exc.close()
            if 300 <= code < 400:
                return None
            return code
        except Exception:
            return None

    def fetch_text(self, url: str) -> str | None:
        """Tokenless GET restricted to ``raw.githubusercontent.com``."""
        try:
            timeout = self._consume_budget()
            parsed = _check_safe_url_basics(url, expected_host=RAW_HOST)
            if parsed.query or not _RAW_PATH_RE.fullmatch(parsed.path):
                return None
            req = Request(url, method="GET", headers={"User-Agent": USER_AGENT})
            with self._opener.open(req, timeout=timeout) as resp:
                if 300 <= resp.status < 400 or resp.status != 200:
                    return None
                raw = _read_bounded_response(resp)
                return raw.decode("utf-8", errors="replace")
        except HTTPError as exc:
            exc.close()
            return None
        except Exception:
            return None
