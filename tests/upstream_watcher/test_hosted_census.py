"""Synthetic end-to-end and adversarial tests for P2 hosted read-only census."""
from __future__ import annotations

import ast
import datetime as dt
import io
import json
import socket
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import OpenerDirector

import pytest
import yaml

from scripts.lib.github_api import GitHubFetchError
from scripts.upstream_watcher import (
    batch,
    envelope,
    hosted_census,
    name_drift,
    readonly_issue_port as rip,
    weekly_census,
    weekly_collector,
)
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.live import GhError
from scripts.upstream_watcher.weekly_effect import FakeIssueService

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "upstream-watcher.yml"
SCOPE_PATH = REPO_ROOT / "scripts" / "upstream_watcher" / "census_scope.json"


@pytest.fixture(autouse=True)
def _forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("hosted census test attempted real network access")

    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", _forbidden)


class _FakeHttpResponse:
    def __init__(self, status: int, body: bytes | str, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self._body = body.encode("utf-8") if isinstance(body, str) else body
        self.headers = headers or {}

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            return self._body
        return self._body[:n]

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None


class _FakeOpener(OpenerDirector):
    def __init__(self, handler: Any) -> None:
        self._handler = handler
        self.requests: list[tuple[str, str, dict[str, str], bytes | None]] = []

    def open(self, req: Any, timeout: float | None = None) -> Any:  # noqa: ARG002
        url = req.full_url
        method = req.get_method()
        headers = {k.lower(): v for k, v in req.header_items()}
        data = req.data
        self.requests.append((method, url, headers, data))
        resp = self._handler(method, url, headers, data)
        if isinstance(resp, Exception):
            raise resp
        status, body, resp_headers = resp
        if status >= 400:
            raw_bytes = body.encode("utf-8") if isinstance(body, str) else body
            raise HTTPError(url, status, f"HTTP {status}", resp_headers or {}, io.BytesIO(raw_bytes))
        return _FakeHttpResponse(status, body, resp_headers)


class _RejectingDuckPort:
    """Explicit duck-typed issue port used to prove exact-type refusal without LiveGh."""

    def __init__(self, repo: str) -> None:
        self.repo = repo

    def list_issues(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("duck port should be refused before reading")

    def get_issue(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("duck port should be refused before reading")

    def list_comments(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("duck port should be refused before reading")

    def child_state(self, *_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("duck port should be refused before reading")


def _parse_url(url: str) -> tuple[str, dict[str, str]]:
    parsed = urlsplit(url)
    raw_q = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=False)
    query = {k: v[0] for k, v in raw_q.items() if len(v) == 1}
    return parsed.path, query


def _gql_repo_response(node_id: str, repo: str, issues: int, prs: int) -> str:
    return json.dumps({
        "data": {
            "repository": {
                "id": node_id,
                "nameWithOwner": repo,
                "issues": {"totalCount": issues},
                "pullRequests": {"totalCount": prs},
            }
        }
    })


def _scope_authority() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    scope_data = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    authority: dict[str, dict[str, Any]] = {}
    for entry in scope_data["scope"]:
        nid = entry["namedId"]
        repo = entry["releaseRepo"]
        owner_part = nid.split("/", 1)[0]
        comp_id = f"{owner_part}/base-comp"
        authority[nid] = {
            "id": nid,
            "links": {"github": f"https://github.com/{repo}"},
            "upstream": {"repo": repo, "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": [comp_id],
        }
        authority[comp_id] = {
            "id": comp_id,
            "links": {"github": f"https://github.com/{repo}/blob/main/skills/base-comp/SKILL.md"},
        }
    suites = [authority[entry["namedId"]] for entry in scope_data["scope"]]
    return authority, suites


def test_readonly_port_safety_and_boundary() -> None:
    source = (REPO_ROOT / "scripts" / "upstream_watcher" / "readonly_issue_port.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            imported_names.add(mod)
            for alias in node.names:
                imported_names.add(f"{mod}.{alias.name}")
    assert "subprocess" not in imported_names
    assert not any("LiveGh" in name for name in imported_names)

    with pytest.raises(TypeError):
        class _SubPort(rip.ReadOnlyIssuePort):  # noqa: B903
            pass

    with pytest.raises(TypeError):
        class _SubClient(rip.HostedUpstreamClient):  # noqa: B903
            pass

    port = rip.ReadOnlyIssuePort("gaia-research/gaia-skill-tree", "tok-123")
    for forbidden in ("create_issue", "edit_issue", "edit_labels", "comment", "edit_comment", "delete_comment"):
        assert not hasattr(port, forbidden)

    # Rejects 3xx redirect
    redir_opener = _FakeOpener(lambda *_a: (302, "{}", {"Location": "https://evil.example/"}))
    redir_port = rip.ReadOnlyIssuePort("gaia-research/gaia-skill-tree", "tok-123", opener=redir_opener)
    with pytest.raises(GhError, match="redirected"):
        redir_port.get_issue(1)

    # Rejects duplicate JSON keys
    dup_opener = _FakeOpener(lambda *_a: (200, '{"number": 1, "number": 2}', {}))
    dup_port = rip.ReadOnlyIssuePort("gaia-research/gaia-skill-tree", "tok-123", opener=dup_opener)
    with pytest.raises(GhError, match="issue-invalid-json"):
        dup_port.get_issue(1)

    # Rejects boolean where int expected
    bool_opener = _FakeOpener(lambda *_a: (200, json.dumps({
        "id": True,
        "node_id": "R_kgDO1",
        "full_name": "gaia-research/gaia-skill-tree",
        "open_issues_count": 0,
    }), {}))
    bool_port = rip.ReadOnlyIssuePort("gaia-research/gaia-skill-tree", "tok-123", opener=bool_opener)
    with pytest.raises(GhError, match="invalid-repository-identity-or-count"):
        bool_port.list_issues("open")

    # HostedUpstreamClient never sends Authorization on API or raw.githubusercontent.com
    up_opener = _FakeOpener(lambda _m, url, _h, _d: (
        (200, "---\nname: base-comp\n---\n", {})
        if "raw.githubusercontent.com" in url
        else (200, json.dumps({
            "tag_name": "v1.0.0",
            "published_at": "2026-11-10T00:00:00Z",
            "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
        }), {})
    ))
    client = rip.HostedUpstreamClient(opener=up_opener)
    client.fetch_release_observations("owner", "repo")
    assert client.head_check("https://raw.githubusercontent.com/owner/repo/main/skills/base-comp/SKILL.md") == 200
    assert client.fetch_text("https://raw.githubusercontent.com/owner/repo/main/skills/base-comp/SKILL.md") is not None
    assert client.head_check("https://evil.example/owner/repo/main/SKILL.md") is None
    for _method, _url, headers, _data in up_opener.requests:
        assert "authorization" not in headers


def test_open_and_closed_inventory_multipage_and_adversarial() -> None:
    repo = "gaia-research/gaia-skill-tree"
    node_id = "R_kgDO99"

    # 1. Open typed count mismatch with exact query parsing (empty offset probe page=2 -> [])
    def mismatch_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 42, "node_id": "R_kgDO42", "full_name": repo, "open_issues_count": 2}), {}
        if method == "POST" and path == "/graphql":
            return 200, _gql_repo_response("R_kgDO42", repo, 2, 0), {}
        if path == f"/repos/{repo}/issues" and q.get("state") == "open" and q.get("per_page") == "100":
            if q.get("page") == "1" and "after" not in q:
                rows = [
                    {"number": 1, "state": "open", "title": "i1", "labels": []},
                    {"number": 2, "state": "open", "title": "p2", "labels": [], "pull_request": {"url": f"https://api.github.com/repos/{repo}/pulls/2"}},
                ]
                return 200, json.dumps(rows), {}
            if q.get("page") == "2" and "after" not in q:
                return 200, "[]", {}
        raise AssertionError(f"unexpected url: {url}")

    port = rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(mismatch_handler))
    with pytest.raises(GhError, match="open-typed-count-mismatch"):
        port.list_issues("open")

    # 2. Multi-page (>100 rows) open + closed with MERGED PR, pinned numeric repo alias, cursor, and empty offset probe
    open_p1 = [{"number": i, "state": "open", "title": f"o{i}", "labels": []} for i in range(1, 101)]
    open_p2 = [{"number": 101, "state": "open", "title": "op101", "labels": [], "pull_request": {"url": f"https://api.github.com/repos/{repo}/pulls/101"}}]
    closed_p1 = [
        {"number": 200 + i, "state": "closed", "title": f"c{i}", "labels": [{"name": "upstream:release"}], "updated_at": "2026-11-18T00:00:00Z"}
        for i in range(1, 101)
    ]
    closed_p2 = [
        {
            "number": 301,
            "state": "closed",
            "title": "merged-pr",
            "labels": [{"name": "upstream:child"}],
            "updated_at": "2026-11-19T00:00:00Z",
            "pull_request": {"url": f"https://api.github.com/repos/{repo}/pulls/301", "merged_at": "2026-11-19T00:00:00Z"},
        },
        {"number": 302, "state": "closed", "title": "old-boot", "labels": [{"name": "upstream:bootstrap"}], "updated_at": "2026-09-01T00:00:00Z"},
    ]
    seen_closed_merged_gql = [False]

    def multipage_handler(method: str, url: str, _h: dict[str, str], data: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 99, "node_id": node_id, "full_name": repo, "open_issues_count": 101}), {}
        if method == "POST" and path == "/graphql":
            gql = json.loads(data.decode("utf-8"))
            assert "id nameWithOwner" in gql["query"]
            if "states:OPEN" in gql["query"]:
                return 200, _gql_repo_response(node_id, repo, 100, 1), {}
            if "states:[CLOSED,MERGED]" in gql["query"]:
                seen_closed_merged_gql[0] = True
                return 200, _gql_repo_response(node_id, repo, 101, 1), {}
            raise AssertionError(f"unexpected graphql query: {gql['query']}")
        if path in (f"/repos/{repo}/issues", "/repositories/99/issues") and q.get("per_page") == "100":
            if q.get("state") == "open":
                if q.get("page") == "1" and "after" not in q:
                    return 200, json.dumps(open_p1), {"Link": '<https://api.github.com/repositories/99/issues?state=open&per_page=100&after=curOpen>; rel="next"'}
                if q.get("after") == "curOpen" and "page" not in q:
                    return 200, json.dumps(open_p2), {"Link": '<https://api.github.com/repositories/99/issues?state=open&per_page=100&before=cur0>; rel="prev"'}
                if q.get("page") == "3" and "after" not in q:
                    return 200, "[]", {}
            if q.get("state") == "closed":
                if q.get("page") == "1" and "after" not in q:
                    return 200, json.dumps(closed_p1), {"Link": '<https://api.github.com/repositories/99/issues?state=closed&per_page=100&after=curClosed>; rel="next"'}
                if q.get("after") == "curClosed" and "page" not in q:
                    return 200, json.dumps(closed_p2), {"Link": '<https://api.github.com/repositories/99/issues?state=closed&per_page=100&before=cur0>; rel="prev"'}
                if q.get("page") == "3" and "after" not in q:
                    return 200, "[]", {}
        raise AssertionError(f"unexpected url: {url}")

    ok_port = rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(multipage_handler))
    assert len(ok_port.list_issues("open")) == 101
    recent_closed = ok_port.list_issues("closed", since="2026-11-01T00:00:00Z")
    assert {r["number"] for r in recent_closed} == {200 + i for i in range(1, 101)} | {301}
    assert {r["number"] for r in ok_port.list_issues("closed", labels="upstream:bootstrap")} == {302}
    assert seen_closed_merged_gql[0] is True

    # 3. Unlinked continuation (non-empty offset terminal probe)
    def unlinked_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 99, "node_id": node_id, "full_name": repo, "open_issues_count": 1}), {}
        if method == "POST" and path == "/graphql":
            return 200, _gql_repo_response(node_id, repo, 1, 0), {}
        if path == f"/repos/{repo}/issues" and q.get("state") == "open":
            if q.get("page") == "1":
                return 200, json.dumps([{"number": 1, "state": "open", "title": "x", "labels": []}]), {}
            if q.get("page") == "2":
                return 200, json.dumps([{"number": 2, "state": "open", "title": "y", "labels": []}]), {}
        raise AssertionError(url)

    with pytest.raises(GhError, match="unlinked-continuation"):
        rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(unlinked_handler)).list_issues("open")

    # 4. Count drift (before != after)
    calls = [0]

    def drift_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 99, "node_id": node_id, "full_name": repo, "open_issues_count": 1}), {}
        if method == "POST" and path == "/graphql":
            calls[0] += 1
            tot = 1 if calls[0] == 1 else 2
            return 200, _gql_repo_response(node_id, repo, tot, 0), {}
        if path == f"/repos/{repo}/issues" and q.get("page") == "1":
            return 200, json.dumps([{"number": 1, "state": "open", "title": "x", "labels": []}]), {}
        if path == f"/repos/{repo}/issues" and q.get("page") == "2":
            return 200, "[]", {}
        raise AssertionError(url)

    with pytest.raises(GhError, match="open-typed-count-mismatch"):
        rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(drift_handler)).list_issues("open")

    # 5. Foreign Link origin
    def foreign_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, _q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 99, "node_id": node_id, "full_name": repo, "open_issues_count": 1}), {}
        if method == "POST" and path == "/graphql":
            return 200, _gql_repo_response(node_id, repo, 1, 0), {}
        return 200, json.dumps([{"number": 1, "state": "open", "title": "x", "labels": []}]), {
            "Link": '<https://evil.example/repos/x/y/issues?state=open&per_page=100&page=2>; rel="next"'
        }

    with pytest.raises(GhError, match="unsafe-url-origin"):
        rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(foreign_handler)).list_issues("open")

    # 6. Wrong pinned numeric repository ID in Link header
    def wrong_num_link_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, _q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 99, "node_id": node_id, "full_name": repo, "open_issues_count": 1}), {}
        if method == "POST" and path == "/graphql":
            return 200, _gql_repo_response(node_id, repo, 1, 0), {}
        return 200, json.dumps([{"number": 1, "state": "open", "title": "x", "labels": []}]), {
            "Link": '<https://api.github.com/repositories/999/issues?state=open&per_page=100&page=2>; rel="next"'
        }

    with pytest.raises(GhError, match="unsafe-link-repository-path"):
        rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(wrong_num_link_handler)).list_issues("open")

    # 7. GraphQL repository identity mismatch (wrong node_id)
    def gql_id_mismatch_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, _q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 99, "node_id": node_id, "full_name": repo, "open_issues_count": 0}), {}
        if method == "POST" and path == "/graphql":
            return 200, _gql_repo_response("R_kgDOOTHER", repo, 0, 0), {}
        raise AssertionError(url)

    with pytest.raises(GhError, match="open-graphql-repository-identity-mismatch"):
        rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(gql_id_mismatch_handler)).list_issues("open")

    # 8. get_issue PR/identity checks and list_comments identity/unlinked-continuation checks
    pr_issue_port = rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(lambda *_a: (200, json.dumps({
        "number": 5,
        "state": "open",
        "labels": [],
        "url": f"https://api.github.com/repos/{repo}/issues/5",
        "pull_request": {"url": f"https://api.github.com/repos/{repo}/pulls/5"},
    }), {})))
    with pytest.raises(GhError, match="issue-is-pull-request"):
        pr_issue_port.get_issue(5)

    wrong_repo_issue_port = rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(lambda *_a: (200, json.dumps({
        "number": 5,
        "state": "open",
        "labels": [],
        "url": "https://api.github.com/repos/other/repo/issues/5",
    }), {})))
    with pytest.raises(GhError, match="issue-identity-mismatch"):
        wrong_repo_issue_port.get_issue(5)

    good_closed_port = rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(lambda *_a: (200, json.dumps({
        "number": 5,
        "state": "closed",
        "labels": [{"name": "upstream:rejected"}],
        "url": f"https://api.github.com/repos/{repo}/issues/5",
    }), {})))
    assert good_closed_port.child_state(5) == "closed-rejected"

    bad_comment_port = rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(lambda *_a: (200, json.dumps([
        {"id": 10, "body": "ok", "issue_url": f"https://api.github.com/repos/{repo}/issues/999"},
    ]), {})))
    with pytest.raises(GhError, match="comments-issue-identity-mismatch"):
        bad_comment_port.list_comments(5)

    def unlinked_comments_handler(_m: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, q = _parse_url(url)
        assert path == f"/repos/{repo}/issues/5/comments"
        if q.get("page") == "1":
            return 200, json.dumps([{"id": 10, "body": "c1", "issue_url": f"https://api.github.com/repos/{repo}/issues/5"}]), {}
        if q.get("page") == "2":
            return 200, json.dumps([{"id": 11, "body": "c2", "issue_url": f"https://api.github.com/repos/{repo}/issues/5"}]), {}
        raise AssertionError(url)

    with pytest.raises(GhError, match="comments-unlinked-continuation"):
        rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(unlinked_comments_handler)).list_comments(5)


def test_typed_release_collection_uses_release_proof() -> None:
    authority, _ = _scope_authority()
    fm = authority["hikari9/auto-office"]
    repo = "gaia-research/gaia-skill-tree"

    # 200 same-version
    res_same = weekly_collector.collect_suite_observation(
        fm,
        authority,
        poll_id="p-1",
        upstream_client=rip.HostedUpstreamClient(opener=_FakeOpener(lambda *_a: (200, json.dumps({
            "tag_name": "v1.0.0",
            "published_at": "2026-11-10T00:00:00Z",
            "html_url": "https://github.com/hikari9/auto-office/releases/tag/v1.0.0",
        }), {}))),
    )
    assert res_same.status == "up-to-date"
    assert res_same.release_status == "same-version"

    # Corroborated 404 -> no-visible-latest-release
    def corr_404(_m: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        if url.endswith("/releases/latest"):
            return 404, "{}", {}
        return 200, json.dumps({"id": 7, "full_name": "Hikari9/auto-office"}), {}

    res_404 = weekly_collector.collect_suite_observation(
        fm,
        authority,
        poll_id="p-1",
        upstream_client=rip.HostedUpstreamClient(opener=_FakeOpener(corr_404)),
    )
    assert res_404.status == "up-to-date"
    assert res_404.release_status == "no-visible-latest-release"

    # Renamed repo 404 -> unknown with bounded sanitized proof_reason and zero candidates
    def renamed_404(_m: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        if url.endswith("/releases/latest"):
            return 404, "{}", {}
        return 200, json.dumps({"id": 7, "full_name": "other/renamed"}), {}

    collected_unknown = weekly_collector.collect_suites(
        [fm],
        authority,
        poll_id="p-1",
        upstream_client=rip.HostedUpstreamClient(opener=_FakeOpener(renamed_404)),
    )
    res_unknown = collected_unknown.results[0]
    assert res_unknown.status == "unknown"
    assert res_unknown.proof_reason == "metadata-repo-mismatch"

    def empty_inventory_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, _q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 100, "node_id": "R_kgDO100", "full_name": repo, "open_issues_count": 0}), {}
        if method == "POST" and path == "/graphql":
            return 200, _gql_repo_response("R_kgDO100", repo, 0, 0), {}
        if path == f"/repos/{repo}/issues":
            return 200, "[]", {}
        raise AssertionError(url)

    unknown_census = weekly_census.run_hosted_weekly_census(
        [fm],
        authority,
        rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(empty_inventory_handler)),
        collected_unknown,
        poll_id="p-1",
        observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty",
        config_repo=repo,
        index_loader=lambda: {"byId": {}, "bySlug": {}},
        policy={},
    )
    assert unknown_census.status == "unknown-incomplete"
    assert unknown_census.logical_candidate_count == 0
    assert unknown_census.scopes[0].decision == "unknown"

    # Same-version + unknown inventory cannot promote to campaign success
    def broken_inventory_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, _q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 100, "node_id": "R_kgDO100", "full_name": repo, "open_issues_count": 1}), {}
        if method == "POST" and path == "/graphql":
            return 200, _gql_repo_response("R_kgDO100", repo, 1, 0), {}
        if path == f"/repos/{repo}/issues":
            return 200, "[]", {}
        raise AssertionError(url)

    same_poll = weekly_collector.CollectedPoll("p-1", (res_same,), (), (), frozenset(), (), frozenset({"hikari9/auto-office"}))
    same_bad_inv = weekly_census.run_hosted_weekly_census(
        [fm],
        authority,
        rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(broken_inventory_handler)),
        same_poll,
        poll_id="p-1",
        observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty",
        config_repo=repo,
        index_loader=lambda: {"byId": {}, "bySlug": {}},
        policy={},
    )
    assert same_bad_inv.status == "unknown-incomplete"
    assert same_bad_inv.binding_status == "refused"
    assert same_bad_inv.logical_candidate_count == 0
    assert same_bad_inv.scopes[0].decision == "unknown"

    # Fabricated release_status in fake run_weekly_census cannot project raw findings
    fake = FakeIssueService(repo=repo)
    fake_census = weekly_census.run_weekly_census(
        [fm],
        authority,
        fake,
        same_poll,
        poll_id="p-1",
        observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty",
        config_repo=repo,
        index_loader=lambda: {"byId": {}, "bySlug": {}},
        policy={},
    )
    assert fake_census.scopes[0].collection_status == "no-finding-unconfirmed"
    assert fake_census.scopes[0].decision == "unknown"


def test_hosted_census_e2e_planner_reducer_binder_holds_and_redaction(tmp_path: Path) -> None:
    authority, _ = _scope_authority()
    repo = "gaia-research/gaia-skill-tree"
    node_id = "R_kgDO100"
    sentinel = "SENTINEL_SECRET_BODY_9f8e7d"
    legacy_payload = envelope.seal({
        "payloadVersion": 2,
        "skillId": "hikari9/auto-office",
        "newVersion": "v0.9.0",
        "releasedAt": "2026-10-01T00:00:00Z",
        "sourceUrl": "https://github.com/hikari9/legacy-auto-office/releases/tag/v0.9.0",
        "mode": "components",
        "componentAdds": [],
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
        "candidates": [],
    })
    legacy_issue = {
        "number": 1833,
        "state": "open",
        "title": "[upstream] hikari9/legacy-auto-office → v0.9.0",
        "labels": [{"name": "upstream:release"}],
        "updated_at": "2026-11-01T00:00:00Z",
        "body": batch.payload_block(legacy_payload) + f"\n\n{sentinel}",
    }

    def _historical_loader(identifier: str) -> dict[str, Any]:
        if identifier == "hikari9/auto-office":
            return {
                "hikari9/auto-office": {
                    "id": "hikari9/auto-office",
                    "links": {"github": "https://github.com/hikari9/legacy-auto-office"},
                    "upstream": {"repo": "hikari9/legacy-auto-office", "version": "v0.8.0"},
                }
            }
        return {}

    def _make_e2e_handler(*, break_inventory: bool = False) -> Any:
        def handler(method: str, url: str, _h: dict[str, str], data: bytes | None) -> tuple[int, str, dict[str, str]]:
            path, q = _parse_url(url)
            if path == f"/repos/{repo}":
                return 200, json.dumps({"id": 100, "node_id": node_id, "full_name": repo, "open_issues_count": 1}), {}
            if method == "POST" and path == "/graphql":
                gql = json.loads(data.decode("utf-8"))
                if "states:OPEN" in gql["query"]:
                    return 200, _gql_repo_response("R_kgDOBROKEN" if break_inventory else node_id, repo, 1, 0), {}
                return 200, _gql_repo_response(node_id, repo, 0, 0), {}
            if path == f"/repos/{repo}/issues":
                if q.get("state") == "open" and q.get("page") == "1" and "after" not in q:
                    return 200, json.dumps([legacy_issue]), {}
                if q.get("state") == "open" and q.get("page") == "2" and "after" not in q:
                    return 200, "[]", {}
                if q.get("state") == "closed":
                    return 200, "[]", {}
            if path == "/repos/obra/superpowers/releases/latest":
                return 200, json.dumps({
                    "tag_name": "v1.1.0",
                    "target_commitish": "9" * 40,  # must never be used as commit proof
                    "published_at": "2026-11-23T08:00:00Z",
                    "html_url": "https://github.com/obra/superpowers/releases/tag/v1.1.0",
                }), {}
            if path == "/repos/obra/superpowers/git/ref/tags/v1.1.0":
                return 200, json.dumps({
                    "ref": "refs/tags/v1.1.0",
                    "url": "https://api.github.com/repos/obra/superpowers/git/refs/tags/v1.1.0",
                    "object": {
                        "type": "commit",
                        "sha": "1" * 40,
                        "url": f"https://api.github.com/repos/obra/superpowers/git/commits/{'1' * 40}",
                    },
                }), {}
            if path == f"/repos/obra/superpowers/git/commits/{'1' * 40}":
                return 200, json.dumps({
                    "sha": "1" * 40,
                    "url": f"https://api.github.com/repos/obra/superpowers/git/commits/{'1' * 40}",
                    "tree": {
                        "sha": "a" * 40,
                        "url": f"https://api.github.com/repos/obra/superpowers/git/trees/{'a' * 40}",
                    },
                }), {}
            if path == "/repos/hikari9/auto-office/releases/latest":
                return 200, json.dumps({
                    "tag_name": "v1.1.0",
                    "target_commitish": "8" * 40,  # must never be used as commit proof
                    "published_at": "2026-11-23T08:00:00Z",
                    "html_url": "https://github.com/hikari9/auto-office/releases/tag/v1.1.0",
                }), {}
            if path == "/repos/hikari9/auto-office/git/ref/tags/v1.1.0":
                return 200, json.dumps({
                    "ref": "refs/tags/v1.1.0",
                    "url": "https://api.github.com/repos/hikari9/auto-office/git/refs/tags/v1.1.0",
                    "object": {
                        "type": "tag",
                        "sha": "2" * 40,
                        "url": f"https://api.github.com/repos/hikari9/auto-office/git/tags/{'2' * 40}",
                    },
                }), {}
            if path == f"/repos/hikari9/auto-office/git/tags/{'2' * 40}":
                return 200, json.dumps({
                    "sha": "2" * 40,
                    "tag": "v1.1.0",
                    "url": f"https://api.github.com/repos/hikari9/auto-office/git/tags/{'2' * 40}",
                    "object": {
                        "type": "commit",
                        "sha": "3" * 40,
                        "url": f"https://api.github.com/repos/hikari9/auto-office/git/commits/{'3' * 40}",
                    },
                }), {}
            if path == f"/repos/hikari9/auto-office/git/commits/{'3' * 40}":
                return 200, json.dumps({
                    "sha": "3" * 40,
                    "url": f"https://api.github.com/repos/hikari9/auto-office/git/commits/{'3' * 40}",
                    "tree": {
                        "sha": "a" * 40,
                        "url": f"https://api.github.com/repos/hikari9/auto-office/git/trees/{'a' * 40}",
                    },
                }), {}
            if path in (
                f"/repos/obra/superpowers/git/trees/{'a' * 40}",
                f"/repos/hikari9/auto-office/git/trees/{'a' * 40}",
            ) and q.get("recursive") == "1":
                return 200, json.dumps({
                    "sha": "a" * 40,
                    "truncated": False,
                    "tree": [
                        {"path": "skills", "type": "tree", "sha": "b" * 40},
                        {"path": "skills/base-comp", "type": "tree", "sha": "c" * 40},
                        {"path": "skills/base-comp/SKILL.md", "type": "blob", "sha": "d" * 40},
                        {"path": "skills/alpha", "type": "tree", "sha": "e" * 40},
                        {"path": "skills/alpha/SKILL.md", "type": "blob", "sha": "f" * 40},
                    ],
                }), {}
            if path == "/repos/leonxlnx/taste-skill/releases/latest":
                return 404, "{}", {}
            if path == "/repos/leonxlnx/taste-skill":
                return 200, json.dumps({"id": 77, "full_name": "leonxlnx/taste-skill"}), {}
            if "raw.githubusercontent.com" in url:
                if url.endswith("/SKILL.md"):
                    return 200, "---\nname: base-comp\n---\n", {}
                return 200, "", {}
            if path.endswith("/releases/latest"):
                repo_part = path[len("/repos/"):-len("/releases/latest")]
                return 200, json.dumps({
                    "tag_name": "v1.0.0",
                    "published_at": "2026-11-10T00:00:00Z",
                    "html_url": f"https://github.com/{repo_part}/releases/tag/v1.0.0",
                }), {}
            raise AssertionError(f"unexpected url: {url}")
        return handler

    reg_dir = tmp_path / "registry_named"
    for nid, meta in authority.items():
        md = reg_dir / f"{nid}.md"
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(f"---\n{yaml.safe_dump(meta)}---\n", encoding="utf-8")

    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({
        "ref": "refs/heads/census/p2-hosted-readonly-2026-11",
        "repository": {"full_name": repo, "default_branch": "main"},
        "inputs": {"apply": "false", "child_mode": "batch", "staging": "off", "skill_id": ""},
    }), encoding="utf-8")

    prov_env = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_EVENT_PATH": str(event_file),
        "GITHUB_ACTOR": "octocat",
        "GITHUB_REPOSITORY": repo,
        "GITHUB_REF": "refs/heads/census/p2-hosted-readonly-2026-11",
        "GITHUB_WORKFLOW_REF": f"{repo}/.github/workflows/upstream-watcher.yml@refs/heads/census/p2-hosted-readonly-2026-11",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "a" * 40,
        "DISPATCH_INPUTS_JSON": json.dumps({"apply": False, "child_mode": "batch", "staging": "off", "skill_id": ""}),
    }

    # Monday flush window so good finding flows through planner -> reducer -> binder
    up_opener = _FakeOpener(_make_e2e_handler())
    receipt = hosted_census.run_hosted_census(
        scope_path=SCOPE_PATH,
        issue_port=rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(_make_e2e_handler())),
        upstream_client=rip.HostedUpstreamClient(opener=up_opener),
        registry_root=reg_dir,
        index_loader=lambda: {"byId": {}, "bySlug": {}},
        historical_loader=_historical_loader,
        verify_historical_commit=False,
        now=dt.datetime(2026, 11, 23, 9, 0, 0, tzinfo=dt.timezone.utc),
        provenance_env=prov_env,
    )
    assert not any("/git/trees/v1.1.0" in url for _, url, _, _ in up_opener.requests)
    assert "tag-ref-recheck-not-atomic-or-immutable" in receipt["constraints"]
    assert receipt["status"] == "scoped-holds-or-unavailable"
    assert receipt["actualCreates"] == 0
    assert receipt["actualUpdates"] == 0
    assert receipt["writeAuthorized"] is False
    assert receipt["writeReadiness"] is False
    assert receipt["persisted"] is False
    assert receipt["stateMode"] == "ephemeral-empty"
    assert receipt["logicalCandidateCount"] == 1
    assert receipt["bindingStatus"] == "bound"
    assert len(receipt["knownLegacyHolds"]) == 1
    assert receipt["knownLegacyHolds"][0]["issue"] == 1833
    assert receipt["knownLegacyHolds"][0]["legacyNamedId"] == "hikari9/auto-office"
    assert receipt["knownLegacyHolds"][0]["hold"] == "separate-migration-approval-required"
    assert sentinel not in json.dumps(receipt)

    by_id = {s["namedId"]: s for s in receipt["scopes"]}
    assert by_id["obra/superpowers"]["collectionStatus"] == "observed"
    assert by_id["obra/superpowers"]["inventoryStatus"] == "verified"
    assert by_id["obra/superpowers"]["decision"] == "eligible-for-read-only-binding"
    assert by_id["obra/superpowers"]["nameDriftStatus"] == "verified"
    assert by_id["obra/superpowers"]["nameDriftCount"] == 0
    assert by_id["obra/superpowers"]["nameDriftVerifiedUnchangedCount"] == 1
    assert by_id["obra/superpowers"]["nameDriftVerifiedDriftCount"] == 0
    assert by_id["obra/superpowers"]["nameDriftUnknownCount"] == 0
    assert by_id["hikari9/auto-office"]["collectionStatus"] == "observed"
    assert by_id["hikari9/auto-office"]["inventoryStatus"] == "verified"
    assert by_id["hikari9/auto-office"]["decision"] == "held-repository-scope"
    assert by_id["hikari9/auto-office"]["nameDriftStatus"] == "verified"
    assert by_id["leonxlnx/taste-skill"]["collectionStatus"] == "no-visible-latest-release"
    assert by_id["garrytan/gbrain"]["collectionStatus"] == "same-version"

    # Known hold does NOT conceal a true read/identity failure
    broken_receipt = hosted_census.run_hosted_census(
        scope_path=SCOPE_PATH,
        issue_port=rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(_make_e2e_handler(break_inventory=True))),
        upstream_client=rip.HostedUpstreamClient(opener=_FakeOpener(_make_e2e_handler(break_inventory=True))),
        registry_root=reg_dir,
        index_loader=lambda: {"byId": {}, "bySlug": {}},
        historical_loader=_historical_loader,
        verify_historical_commit=False,
        now=dt.datetime(2026, 11, 23, 9, 0, 0, tzinfo=dt.timezone.utc),
        provenance_env=prov_env,
    )
    assert broken_receipt["status"] == "unknown-incomplete"
    assert broken_receipt["bindingStatus"] == "refused"
    assert broken_receipt["logicalCandidateCount"] == 0
    assert sentinel not in json.dumps(broken_receipt)

    # Separate exact-type refusal on both entrypoints using an explicit rejecting duck type
    duck = _RejectingDuckPort(repo)
    with pytest.raises(PayloadError):
        weekly_census.run_weekly_census(
            [], authority, duck,  # type: ignore[arg-type]
            weekly_collector.CollectedPoll("p", (), (), (), frozenset(), (), frozenset()),
            poll_id="p", observed_at="2026-11-23T09:00:00Z", state_mode="ephemeral-empty",
            config_repo=repo, index_loader=lambda: {}, policy={},
        )
    with pytest.raises(PayloadError):
        weekly_census.run_hosted_weekly_census(
            [], authority, FakeIssueService(repo=repo),  # type: ignore[arg-type]
            weekly_collector.CollectedPoll("p", (), (), (), frozenset(), (), frozenset()),
            poll_id="p", observed_at="2026-11-23T09:00:00Z", state_mode="ephemeral-empty",
            config_repo=repo, index_loader=lambda: {}, policy={},
        )
    with pytest.raises(PayloadError):
        weekly_census.run_hosted_weekly_census(
            [], authority, duck,  # type: ignore[arg-type]
            weekly_collector.CollectedPoll("p", (), (), (), frozenset(), (), frozenset()),
            poll_id="p", observed_at="2026-11-23T09:00:00Z", state_mode="ephemeral-empty",
            config_repo=repo, index_loader=lambda: {}, policy={},
        )


def test_workflow_contract_proof(tmp_path: Path) -> None:
    wf = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    on_block = wf.get("on", wf.get(True))
    assert list(on_block.keys()) == ["workflow_dispatch"]
    expected_inputs = {
        "permission_ab", "metadata_probe", "skill_id", "apply",
        "challenge_watch", "challenge_input", "challenge_shadow",
        "child_mode", "staging", "staging_bootstrap", "escalate_candidate",
    }
    assert set(on_block["workflow_dispatch"]["inputs"].keys()) == expected_inputs
    expected_perms = {"contents": "read", "issues": "read", "pull-requests": "read"}
    assert wf["permissions"] == expected_perms
    assert list(wf["jobs"].keys()) == ["weekly-census-readonly"]
    job = wf["jobs"]["weekly-census-readonly"]
    assert job["permissions"] == expected_perms
    assert job["timeout-minutes"] == 10
    assert "refs/heads/census/p2-hosted-readonly-2026-11" in job["if"]
    assert "github.run_attempt == 1" in job["if"]
    steps = job["steps"]
    assert steps[0]["uses"] == "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    assert steps[0]["with"]["persist-credentials"] is False
    assert steps[-1]["uses"] == "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
    assert steps[-1]["with"]["retention-days"] == 7
    assert steps[-1]["with"]["if-no-files-found"] == "error"
    assert steps[-1]["with"]["path"] == "generated-output/weekly-census-readonly-receipt.json"
    raw_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "actions/cache" not in raw_text
    assert "GAIA_OPERATOR_OVERRIDE" not in raw_text
    assert "STEWARD_ISSUE_HYGIENE_V2" not in raw_text
    assert "pip install" not in raw_text
    assert "GITHUB_EVENT_NAME" in raw_text
    assert "gaia-research/gaia-skill-tree/.github/workflows/upstream-watcher.yml@refs/heads/census/p2-hosted-readonly-2026-11" in raw_text

    # Wire dispatch validator: 4 explicit wire inputs without metadata_probe / permission_ab succeed
    normalized = hosted_census.validate_workflow_dispatch_payload({
        "apply": False,
        "child_mode": "batch",
        "staging": "off",
        "skill_id": "",
    })
    assert normalized["metadata_probe"] is False
    assert normalized["permission_ab"] is False

    for bad_payload in (
        {"apply": True, "child_mode": "batch", "staging": "off", "skill_id": ""},
        {"apply": False, "child_mode": "fanout", "staging": "off", "skill_id": ""},
        {"apply": False, "child_mode": "batch", "staging": "weekly", "skill_id": ""},
        {"apply": False, "child_mode": "batch", "staging": "off", "metadata_probe": True},
        {"apply": False, "child_mode": "batch", "staging": "off", "permission_ab": "true"},
        {"apply": False, "child_mode": "batch", "staging": "off", "staging_bootstrap": True},
        {"apply": False, "child_mode": "batch", "staging": "off", "skill_id": "owner/suite"},
        {"apply": False, "child_mode": "batch", "staging": "off", "extra_unknown": False},
    ):
        with pytest.raises(hosted_census.HostedCensusRefusal):
            hosted_census.validate_workflow_dispatch_payload(bad_payload)

    # Pre-network raw GITHUB_EVENT_PATH validation: rejects bad raw inputs, wrong ref, and oversized payloads without leaking values
    event_sentinel = "RAW_EVENT_SENTINEL_XYZ"
    for bad_event in (
        {"ref": "refs/heads/main", "inputs": {"apply": "false", "child_mode": "batch", "staging": "off"}},
        {"ref": "refs/heads/census/p2-hosted-readonly-2026-11", "inputs": {"apply": "true", "child_mode": "batch", "staging": "off"}},
        {"ref": "refs/heads/census/p2-hosted-readonly-2026-11", "inputs": {"apply": "false", "child_mode": "batch", "staging": "off", "metadata_probe": "true"}},
        {"ref": "refs/heads/census/p2-hosted-readonly-2026-11", "inputs": {"apply": "false", "child_mode": "batch", "staging": "off", "skill_id": event_sentinel}},
        {"ref": "refs/heads/census/p2-hosted-readonly-2026-11", "inputs": {"apply": "false", "child_mode": "batch", "staging": "off", "extra": event_sentinel}},
    ):
        ev_file = tmp_path / "bad_event.json"
        ev_file.write_text(json.dumps(bad_event), encoding="utf-8")
        with pytest.raises(hosted_census.HostedCensusRefusal) as exc_info:
            hosted_census.validate_raw_event_payload(ev_file)
        assert event_sentinel not in str(exc_info.value)

    big_file = tmp_path / "big_event.json"
    big_file.write_bytes(b" " * (hosted_census.MAX_EVENT_BYTES + 10))
    with pytest.raises(hosted_census.HostedCensusRefusal, match="raw-event-too-large"):
        hosted_census.validate_raw_event_payload(big_file)


def test_preflight_baseline_scope_and_raw_event_strictness(tmp_path: Path) -> None:
    # Authentic committed baseline files under REPO_ROOT pass preflight
    scope_data, scope_sha = hosted_census.load_and_validate_scope(SCOPE_PATH, repo_root=REPO_ROOT)
    assert scope_data["baselineCount"] == 81
    assert len(scope_sha) == 64

    # Empty repo_root with both committed baseline files missing is refused
    empty_repo = tmp_path / "empty_repo"
    empty_repo.mkdir()
    with pytest.raises(hosted_census.HostedCensusRefusal, match="missing-baseline-file"):
        hosted_census.load_and_validate_scope(SCOPE_PATH, repo_root=empty_repo)

    # Partial baseline (records present, metadata missing) is refused
    partial_repo = tmp_path / "partial_repo"
    rec_dst = partial_repo / hosted_census.BASELINE_RECORDS_REL
    rec_dst.parent.mkdir(parents=True, exist_ok=True)
    rec_dst.write_bytes((REPO_ROOT / hosted_census.BASELINE_RECORDS_REL).read_bytes())
    with pytest.raises(hosted_census.HostedCensusRefusal, match="missing-baseline-file"):
        hosted_census.load_and_validate_scope(SCOPE_PATH, repo_root=partial_repo)

    # Tampered baseline records file is refused by raw SHA-256
    meta_dst = partial_repo / hosted_census.BASELINE_METADATA_REL
    meta_dst.write_bytes((REPO_ROOT / hosted_census.BASELINE_METADATA_REL).read_bytes())
    # Exact authentic copy of both passes
    hosted_census.load_and_validate_scope(SCOPE_PATH, repo_root=partial_repo)

    tampered_rec_bytes = rec_dst.read_bytes() + b"\n"
    rec_dst.write_bytes(tampered_rec_bytes)
    with pytest.raises(hosted_census.HostedCensusRefusal, match="baseline-file-sha256-mismatch"):
        hosted_census.load_and_validate_scope(SCOPE_PATH, repo_root=partial_repo)

    # Restore records, tamper metadata file -> refused by raw SHA-256
    rec_dst.write_bytes((REPO_ROOT / hosted_census.BASELINE_RECORDS_REL).read_bytes())
    meta_dst.write_bytes(meta_dst.read_bytes() + b"\n")
    with pytest.raises(hosted_census.HostedCensusRefusal, match="baseline-file-sha256-mismatch"):
        hosted_census.load_and_validate_scope(SCOPE_PATH, repo_root=partial_repo)

    # Scope schemaVersion=true (bool) is refused; duplicate keys and NaN are refused
    base_scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    bool_scope = tmp_path / "bool_scope.json"
    bool_scope.write_text(json.dumps({**base_scope, "schemaVersion": True}), encoding="utf-8")
    with pytest.raises(hosted_census.HostedCensusRefusal, match="invalid-scope-schema"):
        hosted_census.load_and_validate_scope(bool_scope, repo_root=REPO_ROOT)

    dup_scope = tmp_path / "dup_scope.json"
    dup_scope.write_text('{"schemaVersion": 1, "schemaVersion": 1}', encoding="utf-8")
    with pytest.raises(hosted_census.HostedCensusRefusal, match="invalid-scope-file"):
        hosted_census.load_and_validate_scope(dup_scope, repo_root=REPO_ROOT)

    nan_scope = tmp_path / "nan_scope.json"
    nan_scope.write_text('{"schemaVersion": 1, "baselineCount": NaN}', encoding="utf-8")
    with pytest.raises(hosted_census.HostedCensusRefusal, match="invalid-scope-file"):
        hosted_census.load_and_validate_scope(nan_scope, repo_root=REPO_ROOT)

    # Raw event: numeric 0 / 0.0 must NEVER be accepted as false; duplicate keys & NaN refused
    for bad_inputs, expected_code in (
        ({"apply": 0, "child_mode": "batch", "staging": "off"}, "raw-event-apply-must-be-false"),
        ({"apply": 0.0, "child_mode": "batch", "staging": "off"}, "raw-event-apply-must-be-false"),
        ({"apply": "false", "child_mode": "batch", "staging": "off", "staging_bootstrap": 0}, "raw-event-switch-not-false:staging_bootstrap"),
        ({"apply": False, "child_mode": "batch", "staging": "off", "metadata_probe": 0.0}, "raw-event-switch-not-false:metadata_probe"),
    ):
        ev = tmp_path / "bad_zero_event.json"
        ev.write_text(json.dumps({
            "ref": "refs/heads/census/p2-hosted-readonly-2026-11",
            "repository": {"full_name": "gaia-research/gaia-skill-tree", "default_branch": "main"},
            "inputs": bad_inputs,
        }), encoding="utf-8")
        with pytest.raises(hosted_census.HostedCensusRefusal, match=expected_code):
            hosted_census.validate_raw_event_payload(ev)

    for bad_raw_json in (
        '{"inputs": {"apply": "false", "apply": "false", "child_mode": "batch", "staging": "off"}}',
        '{"inputs": {"apply": "false", "child_mode": "batch", "staging": "off", "staging_bootstrap": NaN}}',
    ):
        ev = tmp_path / "bad_json_event.json"
        ev.write_text(bad_raw_json, encoding="utf-8")
        with pytest.raises(hosted_census.HostedCensusRefusal, match="invalid-raw-event-json"):
            hosted_census.validate_raw_event_payload(ev)

    # Authentic real-shaped wire event inputs remain accepted
    for good_inputs in (
        {"apply": "false", "child_mode": "batch", "staging": "off", "skill_id": ""},
        {"apply": False, "child_mode": "batch", "staging": "off", "staging_bootstrap": "false", "metadata_probe": ""},
    ):
        ev = tmp_path / "good_event.json"
        ev.write_text(json.dumps({
            "ref": "refs/heads/census/p2-hosted-readonly-2026-11",
            "repository": {"full_name": "gaia-research/gaia-skill-tree", "default_branch": "main"},
            "inputs": good_inputs,
        }), encoding="utf-8")
        hosted_census.validate_raw_event_payload(ev)


def test_hosted_name_drift_redaction_verification_and_mixed_scopes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    malformed_sentinel = "MALFORMED_YAML_SENTINEL_9a8b7c"
    upstream_name_sentinel = "SENTINEL_UPSTREAM_DRIFT_NAME_4d5e6f"
    comp_map = {
        "owner/base-comp": {
            "id": "owner/base-comp",
            "links": {"github": "https://github.com/owner/repo/blob/main/skills/base-comp/SKILL.md"},
        },
    }

    # 1. Verified unchanged (reusing sanitize_name) vs verified drift
    res_match = name_drift.check_name_drift_hosted(
        ["owner/base-comp"],
        comp_map,
        fetch_text_fn=lambda _u: "---\nname: Base Comp\n---\n",
    )
    assert res_match.complete is True
    assert res_match.status == "verified"
    assert res_match.verified_unchanged == ("owner/base-comp",)
    assert res_match.verified_drift == ()
    assert res_match.unknown == ()

    res_drift = name_drift.check_name_drift_hosted(
        ["owner/base-comp"],
        comp_map,
        fetch_text_fn=lambda _u: f"---\nname: {upstream_name_sentinel}\n---\n",
    )
    assert res_drift.complete is True
    assert res_drift.verified_unchanged == ()
    assert res_drift.verified_drift == ("owner/base-comp",)
    assert res_drift.unknown == ()
    assert upstream_name_sentinel not in repr(res_drift)

    # 2. Malformed frontmatter, missing/unreadable, non-string name, alias bomb, duplicate keys
    for payload, expected_code in (
        (None, "fetch-failed"),
        ("no frontmatter here", "missing-frontmatter"),
        (f"---\nname: [unterminated {malformed_sentinel}\n---\n", "malformed-frontmatter"),
        ("---\ndescription: only\n---\n", "missing-upstream-name"),
        ("---\nname: 12345\n---\n", "invalid-upstream-name"),
        ("---\nname: true\n---\n", "invalid-upstream-name"),
        ("---\na: &a [x]\nname: *a\n---\n", "malformed-frontmatter"),
        ("---\nname: base-comp\nname: other\n---\n", "malformed-frontmatter"),
    ):
        res_bad = name_drift.check_name_drift_hosted(
            ["owner/base-comp"],
            comp_map,
            fetch_text_fn=lambda _u, p=payload: p,
        )
        assert res_bad.complete is False
        assert res_bad.status == "unknown"
        assert res_bad.verified_unchanged == ()
        assert res_bad.verified_drift == ()
        assert res_bad.unknown == (("owner/base-comp", expected_code),)
    captured_unit = capsys.readouterr()
    assert captured_unit.out == ""
    assert captured_unit.err == ""
    assert malformed_sentinel not in captured_unit.out + captured_unit.err

    # 3. Ordinary offline check_name_drift contract preserved unchanged
    ordinary = name_drift.check_name_drift(
        ["owner/base-comp"],
        comp_map,
        fetch_text_fn=lambda _u: "---\nname: Other Name\n---\n",
    )
    assert ordinary == [{
        "skillId": "owner/base-comp",
        "registrySlug": "base-comp",
        "upstreamName": "Other Name",
        "sanitizedName": "other-name",
        "fixCommand": "gaia dev rename owner/base-comp owner/other-name",
    }]

    # 4. Combined good scope (verified drift) + incomplete scope (malformed frontmatter with sentinel)
    #    + qualifying knownLegacyHold preserved, zero sentinel/upstream-name/instruction leakage
    authority, _ = _scope_authority()
    repo = "gaia-research/gaia-skill-tree"
    node_id = "R_kgDO100"
    legacy_payload = envelope.seal({
        "payloadVersion": 2,
        "skillId": "hikari9/auto-office",
        "newVersion": "v0.9.0",
        "releasedAt": "2026-10-01T00:00:00Z",
        "sourceUrl": "https://github.com/hikari9/legacy-auto-office/releases/tag/v0.9.0",
        "mode": "components",
        "componentAdds": [],
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
        "candidates": [],
    })
    legacy_issue = {
        "number": 1833,
        "state": "open",
        "title": "[upstream] hikari9/legacy-auto-office → v0.9.0",
        "labels": [{"name": "upstream:release"}],
        "updated_at": "2026-11-01T00:00:00Z",
        "body": batch.payload_block(legacy_payload),
    }

    def _historical_loader(identifier: str) -> dict[str, Any]:
        if identifier == "hikari9/auto-office":
            return {
                "hikari9/auto-office": {
                    "id": "hikari9/auto-office",
                    "links": {"github": "https://github.com/hikari9/legacy-auto-office"},
                    "upstream": {"repo": "hikari9/legacy-auto-office", "version": "v0.8.0"},
                }
            }
        return {}

    def mixed_handler(method: str, url: str, _h: dict[str, str], data: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, q = _parse_url(url)
        if path == f"/repos/{repo}":
            return 200, json.dumps({"id": 100, "node_id": node_id, "full_name": repo, "open_issues_count": 1}), {}
        if method == "POST" and path == "/graphql":
            gql = json.loads(data.decode("utf-8"))
            if "states:OPEN" in gql["query"]:
                return 200, _gql_repo_response(node_id, repo, 1, 0), {}
            return 200, _gql_repo_response(node_id, repo, 0, 0), {}
        if path == f"/repos/{repo}/issues":
            if q.get("state") == "open" and q.get("page") == "1" and "after" not in q:
                return 200, json.dumps([legacy_issue]), {}
            return 200, "[]", {}
        if path in ("/repos/obra/superpowers/releases/latest", "/repos/hikari9/auto-office/releases/latest"):
            rp = path[len("/repos/"):-len("/releases/latest")]
            return 200, json.dumps({
                "tag_name": "v1.1.0",
                "published_at": "2026-11-23T08:00:00Z",
                "html_url": f"https://github.com/{rp}/releases/tag/v1.1.0",
            }), {}
        if path in ("/repos/obra/superpowers/git/ref/tags/v1.1.0", "/repos/hikari9/auto-office/git/ref/tags/v1.1.0"):
            return 200, json.dumps({
                "ref": "refs/tags/v1.1.0",
                "object": {"type": "commit", "sha": "1" * 40},
            }), {}
        if path in (
            f"/repos/obra/superpowers/git/commits/{'1' * 40}",
            f"/repos/hikari9/auto-office/git/commits/{'1' * 40}",
        ):
            return 200, json.dumps({"sha": "1" * 40, "tree": {"sha": "a" * 40}}), {}
        if path in (
            f"/repos/obra/superpowers/git/trees/{'a' * 40}",
            f"/repos/hikari9/auto-office/git/trees/{'a' * 40}",
        ) and q.get("recursive") == "1":
            return 200, json.dumps({
                "sha": "a" * 40,
                "truncated": False,
                "tree": [
                    {"path": "skills", "type": "tree", "sha": "b" * 40},
                    {"path": "skills/base-comp", "type": "tree", "sha": "c" * 40},
                    {"path": "skills/base-comp/SKILL.md", "type": "blob", "sha": "d" * 40},
                    {"path": "skills/alpha", "type": "tree", "sha": "e" * 40},
                    {"path": "skills/alpha/SKILL.md", "type": "blob", "sha": "f" * 40},
                ],
            }), {}
        if "raw.githubusercontent.com" in url:
            if "/obra/superpowers/" in url and method == "GET":
                return 200, f"---\nname: {upstream_name_sentinel}\n---\n", {}
            if "/hikari9/auto-office/" in url and method == "GET":
                return 200, f"---\nname: [unterminated {malformed_sentinel}\n---\n", {}
            return 200, "", {}
        if path.endswith("/releases/latest"):
            rp = path[len("/repos/"):-len("/releases/latest")]
            return 200, json.dumps({
                "tag_name": "v1.0.0",
                "published_at": "2026-11-10T00:00:00Z",
                "html_url": f"https://github.com/{rp}/releases/tag/v1.0.0",
            }), {}
        raise AssertionError(f"unexpected url: {url}")

    reg_dir = tmp_path / "registry_named_mixed"
    for nid, meta in authority.items():
        md = reg_dir / f"{nid}.md"
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(f"---\n{yaml.safe_dump(meta)}---\n", encoding="utf-8")

    receipt = hosted_census.run_hosted_census(
        scope_path=SCOPE_PATH,
        issue_port=rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(mixed_handler)),
        upstream_client=rip.HostedUpstreamClient(opener=_FakeOpener(mixed_handler)),
        registry_root=reg_dir,
        index_loader=lambda: {"byId": {}, "bySlug": {}},
        historical_loader=_historical_loader,
        verify_historical_commit=False,
        now=dt.datetime(2026, 11, 23, 9, 0, 0, tzinfo=dt.timezone.utc),
        provenance_env={},
    )
    captured_e2e = capsys.readouterr()
    receipt_json = json.dumps(receipt)
    for forbidden_text in (malformed_sentinel, upstream_name_sentinel, "gaia dev rename"):
        assert forbidden_text not in captured_e2e.out
        assert forbidden_text not in captured_e2e.err
        assert forbidden_text not in receipt_json

    assert receipt["status"] == "unknown-incomplete"
    assert receipt["logicalCandidateCount"] == 1
    assert len(receipt["knownLegacyHolds"]) == 1
    assert receipt["knownLegacyHolds"][0]["issue"] == 1833

    by_id = {s["namedId"]: s for s in receipt["scopes"]}
    assert by_id["obra/superpowers"]["decision"] == "eligible-for-read-only-binding"
    assert by_id["obra/superpowers"]["nameDriftStatus"] == "verified"
    assert by_id["obra/superpowers"]["nameDriftCount"] == 1
    assert by_id["obra/superpowers"]["nameDriftVerifiedDriftCount"] == 1
    assert by_id["obra/superpowers"]["nameDriftUnknownCount"] == 0

    assert by_id["hikari9/auto-office"]["decision"] == "unknown"
    assert by_id["hikari9/auto-office"]["nameDriftStatus"] == "unknown"
    assert by_id["hikari9/auto-office"]["nameDriftCount"] is None
    assert by_id["hikari9/auto-office"]["nameDriftUnknownCount"] == 1
    assert by_id["hikari9/auto-office"]["nameDriftUnknown"] == [
        {"namedId": "hikari9/base-comp", "reason": "malformed-frontmatter"}
    ]


def test_hosted_tag_tree_proof_positive_and_adversarial() -> None:
    authority, _ = _scope_authority()
    fm = authority["obra/superpowers"]
    repo = "gaia-research/gaia-skill-tree"
    tree_body = {
        "sha": "a" * 40,
        "truncated": False,
        "tree": [
            {"path": "skills", "type": "tree", "sha": "b" * 40},
            {"path": "skills/base-comp", "type": "tree", "sha": "c" * 40},
            {"path": "skills/base-comp/SKILL.md", "type": "blob", "sha": "d" * 40},
            {"path": "skills/added", "type": "tree", "sha": "e" * 40},
            {"path": "skills/added/SKILL.md", "type": "blob", "sha": "f" * 40},
        ],
    }

    # 1. HostedUpstreamClient.fetch_json refuses tag-string tree URLs
    tag_client = rip.HostedUpstreamClient(opener=_FakeOpener(lambda *_a: (200, "{}", {})))
    with pytest.raises(GitHubFetchError, match="disallowed-upstream-tree-url"):
        tag_client.fetch_json("https://api.github.com/repos/obra/superpowers/git/trees/v1.1.0?recursive=1")

    # 2. Positive lightweight tag fixture (target_commitish ignored)
    def lightweight_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, q = _parse_url(url)
        if path == "/repos/obra/superpowers/releases/latest":
            return 200, json.dumps({
                "tag_name": "v1.1.0",
                "target_commitish": "9" * 40,
                "published_at": "2026-11-23T08:00:00Z",
                "html_url": "https://github.com/obra/superpowers/releases/tag/v1.1.0",
            }), {}
        if path == "/repos/obra/superpowers/git/ref/tags/v1.1.0":
            return 200, json.dumps({
                "ref": "refs/tags/v1.1.0",
                "object": {"type": "commit", "sha": "1" * 40},
            }), {}
        if path == f"/repos/obra/superpowers/git/commits/{'1' * 40}":
            return 200, json.dumps({"sha": "1" * 40, "tree": {"sha": "a" * 40}}), {}
        if path == f"/repos/obra/superpowers/git/trees/{'a' * 40}" and q.get("recursive") == "1":
            return 200, json.dumps(tree_body), {}
        if "raw.githubusercontent.com" in url:
            return 200, "---\nname: base-comp\n---\n" if method == "GET" else "", {}
        raise AssertionError(f"unexpected url: {url}")

    lw_opener = _FakeOpener(lightweight_handler)
    res_lw = weekly_collector.collect_suite_observation(
        fm,
        authority,
        poll_id="p-lw",
        upstream_client=rip.HostedUpstreamClient(opener=lw_opener),
    )
    assert res_lw.status == "observed"
    assert res_lw.complete_inventory is not None
    assert res_lw.complete_inventory.present_slugs == frozenset({"base-comp", "added"})
    assert not any("/git/trees/v1.1.0" in u for _, u, _, _ in lw_opener.requests)
    assert sum(1 for _, u, _, _ in lw_opener.requests if u.endswith("/git/ref/tags/v1.1.0")) == 2

    # 3. Positive 2-hop annotated tag fixture
    def annotated_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
        path, q = _parse_url(url)
        if path == "/repos/obra/superpowers/releases/latest":
            return 200, json.dumps({
                "tag_name": "v1.1.0",
                "published_at": "2026-11-23T08:00:00Z",
                "html_url": "https://github.com/obra/superpowers/releases/tag/v1.1.0",
            }), {}
        if path == "/repos/obra/superpowers/git/ref/tags/v1.1.0":
            return 200, json.dumps({
                "ref": "refs/tags/v1.1.0",
                "object": {"type": "tag", "sha": "2" * 40},
            }), {}
        if path == f"/repos/obra/superpowers/git/tags/{'2' * 40}":
            return 200, json.dumps({
                "sha": "2" * 40,
                "tag": "v1.1.0",
                "object": {"type": "tag", "sha": "3" * 40},
            }), {}
        if path == f"/repos/obra/superpowers/git/tags/{'3' * 40}":
            return 200, json.dumps({
                "sha": "3" * 40,
                "tag": "v1.1.0-inner",
                "object": {"type": "commit", "sha": "4" * 40},
            }), {}
        if path == f"/repos/obra/superpowers/git/commits/{'4' * 40}":
            return 200, json.dumps({"sha": "4" * 40, "tree": {"sha": "a" * 40}}), {}
        if path == f"/repos/obra/superpowers/git/trees/{'a' * 40}" and q.get("recursive") == "1":
            return 200, json.dumps(tree_body), {}
        if "raw.githubusercontent.com" in url:
            return 200, "---\nname: base-comp\n---\n" if method == "GET" else "", {}
        raise AssertionError(f"unexpected url: {url}")

    ann_opener = _FakeOpener(annotated_handler)
    res_ann = weekly_collector.collect_suite_observation(
        fm,
        authority,
        poll_id="p-ann",
        upstream_client=rip.HostedUpstreamClient(opener=ann_opener),
    )
    assert res_ann.status == "observed"
    assert res_ann.complete_inventory is not None
    assert not any("/git/trees/v1.1.0" in u for _, u, _, _ in ann_opener.requests)

    # 4. Negative cases: mismatched tree, changing ref, malformed/contradictory annotated hops, wrong namespace
    def _run_negative(mode: str, expected_reason: str) -> None:
        ref_reads = [0]

        def neg_handler(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
            path, q = _parse_url(url)
            assert "/git/trees/v1.1.0" not in path
            assert "evil.example" not in url
            if path == "/repos/obra/superpowers/releases/latest":
                return 200, json.dumps({
                    "tag_name": "v1.1.0",
                    "published_at": "2026-11-23T08:00:00Z",
                    "html_url": "https://github.com/obra/superpowers/releases/tag/v1.1.0",
                }), {}
            if path == "/repos/obra/superpowers/git/ref/tags/v1.1.0":
                ref_reads[0] += 1
                if mode == "wrong-namespace":
                    return 200, json.dumps({
                        "ref": "refs/heads/v1.1.0",
                        "object": {"type": "commit", "sha": "1" * 40},
                    }), {}
                if mode == "foreign-obj-url":
                    return 200, json.dumps({
                        "ref": "refs/tags/v1.1.0",
                        "object": {
                            "type": "commit",
                            "sha": "1" * 40,
                            "url": f"https://evil.example/repos/obra/superpowers/git/commits/{'1' * 40}",
                        },
                    }), {}
                if mode == "changing-ref":
                    sha = "1" * 40 if ref_reads[0] == 1 else "9" * 40
                    return 200, json.dumps({
                        "ref": "refs/tags/v1.1.0",
                        "object": {"type": "commit", "sha": sha},
                    }), {}
                if mode.startswith("ann-"):
                    return 200, json.dumps({
                        "ref": "refs/tags/v1.1.0",
                        "object": {"type": "tag", "sha": "2" * 40},
                    }), {}
                return 200, json.dumps({
                    "ref": "refs/tags/v1.1.0",
                    "object": {"type": "commit", "sha": "1" * 40},
                }), {}
            if path.startswith("/repos/obra/superpowers/git/tags/"):
                req_sha = path.rsplit("/", 1)[-1]
                if mode == "ann-wrong-name":
                    return 200, json.dumps({
                        "sha": req_sha,
                        "tag": "v9.9.9",
                        "object": {"type": "commit", "sha": "1" * 40},
                    }), {}
                if mode == "ann-sha-mismatch":
                    return 200, json.dumps({
                        "sha": "7" * 40,
                        "tag": "v1.1.0",
                        "object": {"type": "commit", "sha": "1" * 40},
                    }), {}
                if mode == "ann-invalid-target-type":
                    return 200, json.dumps({
                        "sha": req_sha,
                        "tag": "v1.1.0",
                        "object": {"type": "tree", "sha": "a" * 40},
                    }), {}
                if mode == "ann-cycle":
                    return 200, json.dumps({
                        "sha": req_sha,
                        "tag": "v1.1.0",
                        "object": {"type": "tag", "sha": req_sha},
                    }), {}
                if mode == "ann-depth":
                    next_hex = format(int(req_sha[0], 16) + 1, "x") * 40
                    return 200, json.dumps({
                        "sha": req_sha,
                        "tag": "v1.1.0",
                        "object": {"type": "tag", "sha": next_hex},
                    }), {}
            if path == f"/repos/obra/superpowers/git/commits/{'1' * 40}":
                return 200, json.dumps({"sha": "1" * 40, "tree": {"sha": "a" * 40}}), {}
            if path == f"/repos/obra/superpowers/git/trees/{'a' * 40}" and q.get("recursive") == "1":
                if mode == "mismatched-tree":
                    return 200, json.dumps({**tree_body, "sha": "f" * 40}), {}
                # Even if base-comp is missing from tree, changing-ref must never produce removals
                return 200, json.dumps({
                    "sha": "a" * 40,
                    "truncated": False,
                    "tree": [{"path": "skills", "type": "tree", "sha": "b" * 40}],
                }), {}
            if "raw.githubusercontent.com" in url:
                # 404 link would be urgent if proof had succeeded
                return 404, "", {}
            raise AssertionError(f"unexpected url for {mode}: {url}")

        collected = weekly_collector.collect_suites(
            [fm],
            authority,
            poll_id=f"p-neg-{mode}",
            upstream_client=rip.HostedUpstreamClient(opener=_FakeOpener(neg_handler)),
        )
        res = collected.results[0]
        assert res.status == "unknown"
        assert res.proof_reason == expected_reason
        assert res.complete_inventory is None

        def empty_inv(method: str, url: str, _h: dict[str, str], _d: bytes | None) -> tuple[int, str, dict[str, str]]:
            p, _q = _parse_url(url)
            if p == f"/repos/{repo}":
                return 200, json.dumps({"id": 100, "node_id": "R_kgDO100", "full_name": repo, "open_issues_count": 0}), {}
            if method == "POST" and p == "/graphql":
                return 200, _gql_repo_response("R_kgDO100", repo, 0, 0), {}
            if p == f"/repos/{repo}/issues":
                return 200, "[]", {}
            raise AssertionError(url)

        census = weekly_census.run_hosted_weekly_census(
            [fm],
            authority,
            rip.ReadOnlyIssuePort(repo, "tok", opener=_FakeOpener(empty_inv)),
            collected,
            poll_id=f"p-neg-{mode}",
            observed_at="2026-11-24T09:00:00Z",  # Tuesday (only urgent could flush)
            state_mode="ephemeral-empty",
            config_repo=repo,
            index_loader=lambda: {"byId": {}, "bySlug": {}},
            policy={},
        )
        assert census.status == "unknown-incomplete"
        assert census.logical_candidate_count == 0
        assert census.scopes[0].decision == "unknown"
        assert census.scopes[0].canonical_removals == ()
        assert census.scopes[0].inventory_status == "unknown"

    for neg_mode, exp_reason in (
        ("mismatched-tree", "tree-sha-mismatch"),
        ("changing-ref", "tag-ref-changed"),
        ("wrong-namespace", "tag-ref-namespace-mismatch"),
        ("foreign-obj-url", "tag-ref-object-url-mismatch"),
        ("ann-wrong-name", "tag-object-name-mismatch"),
        ("ann-sha-mismatch", "tag-object-sha-mismatch"),
        ("ann-invalid-target-type", "tag-object-invalid-target-type"),
        ("ann-cycle", "tag-peel-cycle"),
        ("ann-depth", "tag-peel-depth-exceeded"),
    ):
        _run_negative(neg_mode, exp_reason)
