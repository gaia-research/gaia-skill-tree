"""Offline probes only: never use credentials or the live network."""
import copy
import hashlib
import io
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml

from scripts.upstream_watcher import metadata_probe as probe

SECRET = "PRIVATE-title-body-author-token-raw-exception"


class Response:
    def __init__(self, data, headers=None, status=200):
        self.data = json.dumps(data).encode()
        self.headers = headers or {}
        self.status = status

    def read(self, limit):
        return self.data[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def nodes(kind, count, start=1):
    return [{"number": n, "__typename": kind, "state": "OPEN",
             "title": SECRET, "body": SECRET, "author": SECRET}
            for n in range(start, start + count)]


class Fixture:
    def __init__(self, issues=2, prs=1, omit=False, fault=None):
        self.issues = nodes("Issue", issues)
        self.prs = nodes("PullRequest", prs, issues + 1)
        self.omit, self.fault = omit, fault
        self.calls = []
        self.counts = 0
        self.connectionReads = {"issues": 0, "pullRequests": 0}

    def open(self, req, timeout):
        self.calls.append(req)
        assert 0 < timeout <= 30
        if req.full_url.endswith("/graphql"):
            assert req.method == "POST"
            body = json.loads(req.data)
            query = body["query"]
            assert query.lstrip().startswith("query(") and "mutation" not in query
            assert all(word not in query for word in ("title", "body", "author", "comments"))
            field = "pullRequests" if "pullRequests(" in query else "issues"
            self.connectionReads[field] += 1
            if field == "pullRequests" and self.fault == "denial":
                raise HTTPError(req.full_url, 403, SECRET, {}, io.BytesIO(SECRET.encode()))
            if field == "pullRequests" and self.fault == "partial":
                return Response({"data": {"repository": {field: {"totalCount": 0}}},
                                 "errors": [{"message": SECRET}]})
            source = self.prs if field == "pullRequests" else self.issues
            size = body["variables"]["size"]
            cursor = body["variables"]["cursor"]
            start = int(cursor or 0)
            page = copy.deepcopy(source[start:start + size])
            info = {"hasNextPage": start + size < len(source), "endCursor": str(start + size)}
            if self.fault == "cursor-loop":
                info = {"hasNextPage": True, "endCursor": "0"}
            if self.fault == "missing-typename" and page:
                page[0].pop("__typename")
            total = len(source)
            if self.fault == "unstable" and size == 1:
                total += 1
            conn = {"totalCount": total, "nodes": page, "pageInfo": info}
            if self.fault == "missing-count":
                conn.pop("totalCount")
            if self.fault == "missing-page-info":
                conn.pop("pageInfo")
            return Response({"data": {"repository": {field: conn}}})
        assert req.method == "GET" and req.data is None
        if "/issues?" not in req.full_url:
            self.counts += 1
            if self.fault == "exception":
                raise RuntimeError(SECRET)
            if self.fault == "missing-rest-count":
                return Response({"title": SECRET})
            return Response({"id": 12345, "full_name": "org/repo",
                             "open_issues_count": len(self.issues) + len(self.prs) +
                             (1 if self.fault == "rest-unstable" and self.counts > 1 else 0)})
        page = int(parse_qs(urlsplit(req.full_url).query)["page"][0])
        if ((self.fault == "rest-denial-first" and page == 1)
                or (self.fault == "rest-denial-mid" and page == 2)):
            raise HTTPError(req.full_url, 403, SECRET, {}, io.BytesIO(SECRET.encode()))
        source = self.issues + ([] if self.omit else self.prs)
        rows = []
        for node in source[(page - 1) * 100:page * 100]:
            row = dict(node, state="open")
            row.pop("__typename")
            if node["__typename"] == "PullRequest":
                row["pull_request"] = {"url": SECRET}
            rows.append(row)
        headers = {"X-GitHub-Request-Id": "ABCD:1234", "Authorization": SECRET}
        if page * 100 < len(source) or self.fault in ("rest-loop", "foreign", "short-linked"):
            following = page if self.fault == "rest-loop" else page + 1
            host = "evil.example" if self.fault == "foreign" else "api.github.com"
            headers["Link"] = f'<https://{host}/repos/org/repo/issues?state=open&per_page=100&page={following}>; rel="next"'
        if self.fault == "duplicate" and rows:
            rows.append(rows[0])
        if self.fault == "bad-status":
            return Response(rows, headers, 206)
        if self.fault == "invalid-json":
            response = Response(rows, headers)
            response.data = SECRET.encode()
            return response
        return Response(rows, headers)


def run(fixture):
    report = probe.Probe("org/repo", SECRET, fixture).collect()
    serialized = json.dumps(report)
    assert SECRET not in serialized
    assert all(word not in serialized for word in ('"title"', '"body"', '"author"', '"Authorization"'))
    assert report["diagnosticOnly"] and not report["acceptanceEligible"] and not report["p1Pass"]
    assert report["causality"] == "not-established"
    assert len(fixture.calls) <= 40
    assert all(c.method in ("GET", "POST") for c in fixture.calls)
    return report


def test_agreement_is_not_acceptance():
    report = run(Fixture())
    assert report["status"] == "observations-agree-not-acceptance"
    assert report["restTypedCounts"] == {"Issue": 2, "PullRequest": 1}


def test_complete_empty_rest_has_observed_zero_counts():
    report = run(Fixture(0, 0))
    assert report["rest"]["complete"] is True
    assert report["rest"]["nodes"] == []
    assert report["restTypedCounts"] == {"Issue": 0, "PullRequest": 0}
    assert report["status"] == "observations-agree-not-acceptance"


@pytest.mark.parametrize("fault, observed", [("rest-denial-first", 0), ("rest-denial-mid", 100)])
def test_incomplete_rest_counts_are_unknown_not_zero_or_partial(fault, observed):
    report = run(Fixture(99, 2, fault=fault))
    assert report["rest"]["complete"] is False
    assert report["rest"]["errorClass"] == "permission-denied"
    # Mid-walk retains both types as partial observations, not aggregate counts.
    assert len(report["rest"]["nodes"]) == observed
    if observed:
        assert {n["__typename"] for n in report["rest"]["nodes"]} == {"Issue", "PullRequest"}
    assert report["restTypedCounts"] == {"Issue": None, "PullRequest": None}
    assert report["status"] == "nonhealthy"
    assert "rest-incomplete" in report["failures"]
    assert any(r["httpStatus"] == 403 and r["errorClass"] == "permission-denied"
               for r in report["requests"])


def test_actual_tuple_is_observation_not_acceptance():
    report = run(Fixture(244, 6, omit=True))
    assert report["repositoryCounts"]["before"]["value"] == 250
    assert report["before"]["issues"]["totalCount"] == 244
    assert report["before"]["pullRequests"]["totalCount"] == 6
    assert report["restTypedCounts"] == {"Issue": 244, "PullRequest": 0}
    assert report["status"] == "nonhealthy"
    assert "pullRequests-identity-disagreement" in report["failures"]


@pytest.mark.parametrize("fault", ["denial", "partial", "missing-count", "missing-rest-count",
    "missing-page-info", "missing-typename", "unstable", "rest-unstable", "exception",
    "cursor-loop", "rest-loop", "foreign", "short-linked", "duplicate", "bad-status", "invalid-json"])
def test_failures_are_nonhealthy_and_redacted(fault):
    fixture = Fixture(fault=fault)
    report = run(fixture)
    assert report["status"] == "nonhealthy" and report["failures"]
    if not report["rest"]["complete"]:
        assert report["restTypedCounts"] == {"Issue": None, "PullRequest": None}
    if fault in ("denial", "partial"):
        assert report["before"]["pullRequests"]["totalCount"] is None
        assert report["before"]["pullRequests"]["errorClass"]
        assert report["before"]["issues"]["totalCount"] == 2
    if fault == "denial":
        assert any(r["httpStatus"] == 403 and r["errorClass"] == "permission-denied" for r in report["requests"])


def test_complete_pagination_and_page_budget():
    complete = run(Fixture(244, 6))
    assert complete["status"] == "observations-agree-not-acceptance"
    assert complete["rest"]["complete"] is True
    assert complete["restTypedCounts"] == {"Issue": 244, "PullRequest": 6}
    report = run(Fixture(1001, 0))
    assert report["restTypedCounts"] == {"Issue": None, "PullRequest": None}
    assert report["status"] == "nonhealthy"
    assert report["before"]["issues"]["errorClass"] == "page-budget-exhausted"


def test_deadline_and_no_token_never_send_request():
    for token, expired in (("", False), (SECRET, True)):
        fixture = Fixture()
        client = probe.Probe("org/repo", token, fixture)
        if expired:
            client.deadline = 0
        report = client.collect()
        assert report["status"] == "nonhealthy"
        assert report["restTypedCounts"] == {"Issue": None, "PullRequest": None}
        assert not fixture.calls


@pytest.mark.parametrize("link", [
    '<https://api.github.com/repos/org/other/issues?state=open&per_page=100&page=2>; rel="next"',
    '<https://api.github.com/repos/org/repo/issues?state=open&per_page=100&page=2&token=secret>; rel="next"',
    '<https://user:secret@api.github.com/repos/org/repo/issues?state=open&per_page=100&page=2>; rel="next"',
    SECRET])
def test_unsafe_links_are_not_serialized(link):
    with pytest.raises(probe.DiagnosticError):
        probe.nextPage(link, "org/repo")


class AliasFixture(Fixture):
    """Observed public Link shape, synthetic id/cursor; never use a live token."""
    def open(self, req, timeout):
        response = super().open(req, timeout)
        if "/issues?" not in req.full_url:
            return response
        assert urlsplit(req.full_url).path == "/repos/org/repo/issues"
        query = parse_qs(urlsplit(req.full_url).query)
        page = int(query["page"][0])
        if page > 1:
            assert query["after"] == [f"cursor-{page}"]
        if "Link" in response.headers:
            response.headers["Link"] = (
                f'<https://api.github.com/repositories/12345/issues?state=open&per_page=100'
                f'&page={page + 1}&after=cursor-{page + 1}>; rel="next"')
        return response


def test_bound_numeric_alias_and_cursor_continuation():
    fixture = AliasFixture(245, 7)
    report = run(fixture)
    assert report["rest"]["complete"] is True
    assert report["restTypedCounts"] == {"Issue": 245, "PullRequest": 7}
    assert report["status"] == "observations-agree-not-acceptance"
    assert all("cursor-" not in json.dumps(r) for r in report["requests"])
    assert report["after"]["issues"]["complete"] is False  # count sample only


@pytest.mark.parametrize("fault", ["rest-denial-first", "rest-denial-mid", "foreign"])
def test_incomplete_rest_comparisons_are_unknown(fault):
    report = run(Fixture(99, 2, fault=fault))
    assert not any("disagreement" in f for f in report["failures"])
    assert report["comparisons"]["aggregateRest"] == {
        "status": "unknown", "reason": "rest-incomplete"}
    for field in ("issues", "pullRequests"):
        assert report["comparisons"][field + "Identities"] == {
            "status": "unknown", "reason": "rest-incomplete"}
    assert report["status"] == "nonhealthy"


def test_incomplete_graphql_and_missing_count_cannot_confirm_disagreement():
    report = run(Fixture(fault="denial"))
    assert "pullRequests-identity-disagreement" not in report["failures"]
    assert report["comparisons"]["pullRequestsIdentities"] == {
        "status": "unknown", "reason": "before-connection-incomplete"}
    report = run(Fixture(fault="missing-rest-count"))
    assert "aggregate-rest-disagreement" not in report["failures"]
    assert report["comparisons"]["aggregateRest"] == {
        "status": "unknown", "reason": "repository-count-unknown"}


@pytest.mark.parametrize("url, reason", [
    ("https://api.github.com/repositories/54321/issues?state=open&per_page=100&page=2", "repository-path"),
    ("https://api.github.com/repositories/123450/issues?state=open&per_page=100&page=2", "repository-path"),
    ("https://evil.example/repositories/12345/issues?state=open&per_page=100&page=2", "origin"),
    ("http://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2", "origin"),
    ("https://api.github.com:443/repositories/12345/issues?state=open&per_page=100&page=2", "origin"),
    ("https://user:secret@api.github.com/repositories/12345/issues?state=open&per_page=100&page=2", "origin"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2#", "origin"),
    ("https://api.github.com/repositories/12345/%2e%2e/issues?state=open&per_page=100&page=2", "repository-path"),
    ("https://api.github.com/repos/org/repo/../other/issues?state=open&per_page=100&page=2", "repository-path"),
    ("https://api.github.com/repositories/12345/issues/extra?state=open&per_page=100&page=2", "repository-path"),
    ("https://api.github.com/repositories/12345/issues?state=closed&per_page=100&page=2", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=99&page=2", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=02", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=0", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&page=3", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&labels=x", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&before=x", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&after=%GG", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&%61fter=x", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&after", "query"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&after=", "cursor"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&after=%0Asecret", "cursor"),
    ("https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&after=https%3A%2F%2Fevil.example", "cursor"),
])
def test_alias_security_rejections_have_safe_reason_classes(url, reason):
    with pytest.raises(probe.DiagnosticError) as caught:
        probe.nextPage(f'<{url}>; rel="next"', "org/repo", 12345)
    assert str(caught.value) == "unsafe-link-" + reason
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("repositoryId", [None, 0, -1, True, "12345", 54321])
def test_numeric_alias_needs_trusted_positive_repository_id(repositoryId):
    with pytest.raises(probe.DiagnosticError, match="^unsafe-link-repository-path$"):
        probe.nextPage('<https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2>; rel="next"',
                       "org/repo", repositoryId)


def test_encoded_cursor_is_preserved_in_memory_only_and_all_relations_checked():
    url = "https://api.github.com/repositories/12345/issues?state=open&per_page=100&page=2&after=Y3Vyc29y%2B%2F%3D"
    page, projection, cursor = probe.nextPage(f'<{url}>; rel="next"', "org/repo", 12345)
    assert page == 2 and cursor == "Y3Vyc29y+/="
    assert "after" not in projection and cursor not in projection
    with pytest.raises(probe.DiagnosticError, match="^unsafe-link-repository-path$"):
        probe.nextPage(f'<{url}>; rel="next", <https://api.github.com/repositories/999/issues?state=open&per_page=100&page=3>; rel="last"',
                       "org/repo", 12345)
    with pytest.raises(probe.DiagnosticError, match="^duplicate-link-relation$"):
        probe.nextPage(f'<{url}>; rel="next", <{url}>; rel="next"', "org/repo", 12345)


@pytest.mark.parametrize("metadata", [{"id": 999, "full_name": "org/other"},
    {"id": "12345", "full_name": "org/repo"}, {"id": True, "full_name": "org/repo"},
    {"id": 12345}, {"full_name": "org/repo"}])
def test_repository_get_identity_not_link_supplied_identity_binds_alias(metadata):
    class Unbound(AliasFixture):
        def open(self, req, timeout):
            response = super().open(req, timeout)
            if not req.full_url.endswith("/graphql") and "/issues?" not in req.full_url:
                response = Response(dict(metadata, open_issues_count=101))
            return response
    report = run(Unbound(100, 1))
    assert report["rest"]["errorClass"] == "unsafe-link-repository-path"
    assert report["restTypedCounts"] == {"Issue": None, "PullRequest": None}
    assert not any("disagreement" in f for f in report["failures"])


@pytest.mark.parametrize("following, cursor", [(1, "cursor-2"), (3, "cursor-2"), (2, "repeated")])
def test_alias_nonmonotonic_pages_and_cursor_loops_refused(following, cursor):
    class Loop(AliasFixture):
        def open(self, req, timeout):
            response = super().open(req, timeout)
            if "/issues?" in req.full_url and "Link" in response.headers:
                page = int(parse_qs(urlsplit(req.full_url).query)["page"][0])
                nxt = page + 1 if cursor == "repeated" else following
                response.headers["Link"] = f'<https://api.github.com/repositories/12345/issues?state=open&per_page=100&page={nxt}&after={cursor}>; rel="next"'
            return response
    # AliasFixture's continuation assertion is for advancing cursors; this
    # adapter checks a deliberately repeated cursor without that assertion.
    if cursor == "repeated":
        class Loop(Fixture):
            def open(self, req, timeout):
                response = super().open(req, timeout)
                if "/issues?" in req.full_url and "Link" in response.headers:
                    page = int(parse_qs(urlsplit(req.full_url).query)["page"][0])
                    response.headers["Link"] = f'<https://api.github.com/repositories/12345/issues?state=open&per_page=100&page={page + 1}&after=repeated>; rel="next"'
                return response
    report = run(Loop(245, 7))
    assert report["rest"]["complete"] is False
    assert report["rest"]["errorClass"] in ("loop-or-incomplete-page", "cursor-loop-or-invalid")
    assert report["restTypedCounts"] == {"Issue": None, "PullRequest": None}
    assert report["status"] == "nonhealthy"


@pytest.mark.parametrize("field", ["issues", "pullRequests"])
@pytest.mark.parametrize("mismatch", [False, True])
def test_unstable_typed_counts_make_identity_comparison_unknown(field, mismatch):
    class Churn(Fixture):
        def open(self, req, timeout):
            response = super().open(req, timeout)
            if req.full_url.endswith("/graphql"):
                body = json.loads(req.data)
                if body["variables"]["size"] == 1 and field + "(" in body["query"]:
                    data = json.loads(response.data)
                    data["data"]["repository"][field]["totalCount"] += 1
                    # Totals remain valid one-node samples, never after censuses.
                    return Response(data)
            if mismatch and "/issues?" in req.full_url:
                rows = json.loads(response.data)
                kind = "Issue" if field == "issues" else "PullRequest"
                for row in rows:
                    if ("pull_request" in row) == (kind == "PullRequest"):
                        row["number"] += 1000
                return Response(rows, response.headers)
            return response
    report = run(Churn(2, 2))
    assert report["comparisons"][field + "Identities"] == {
        "status": "unknown", "reason": "connection-count-unstable"}
    other = "pullRequests" if field == "issues" else "issues"
    assert report["comparisons"][other + "Identities"]["status"] == "agree"
    assert field + "-count-unstable" in report["failures"]
    assert field + "-identity-disagreement" not in report["failures"]
    assert report["status"] == "nonhealthy"
    assert not report["after"][field]["complete"]


@pytest.mark.parametrize("beforeCount, afterCount", [(3, 4), (4, 3)])
def test_unstable_repository_counts_make_aggregate_comparison_unknown(beforeCount, afterCount):
    class AggregateChurn(Fixture):
        def open(self, req, timeout):
            response = super().open(req, timeout)
            if not req.full_url.endswith("/graphql") and "/issues?" not in req.full_url:
                data = json.loads(response.data)
                data["open_issues_count"] = beforeCount if self.counts == 1 else afterCount
                return Response(data)
            return response
    report = run(AggregateChurn())
    assert report["comparisons"]["aggregateRest"] == {
        "status": "unknown", "reason": "repository-count-unstable"}
    assert "repository-count-unstable" in report["failures"]
    assert "aggregate-rest-disagreement" not in report["failures"]
    assert report["status"] == "nonhealthy"


@pytest.mark.parametrize("base", [Fixture, AliasFixture], ids=["named", "numeric"])
@pytest.mark.parametrize("phase", ["before", "after"])
@pytest.mark.parametrize("metadata", [
    {}, {"full_name": "org/repo"}, {"id": 12345},
    *[{"id": value, "full_name": "org/repo"} for value in (None, True, False, 0, -1, 12345.0, "12345")],
    *[{"id": 12345, "full_name": value} for value in (None, True, 12345, "", "org/other", " org/repo", "org/repo/")],
])
def test_authoritative_identity_required_for_all_paths_and_count_reads(base, phase, metadata):
    class InvalidRepository(base):
        def open(self, req, timeout):
            response = super().open(req, timeout)
            if not req.full_url.endswith("/graphql") and "/issues?" not in req.full_url:
                if self.counts == (1 if phase == "before" else 2):
                    return Response(dict(metadata, open_issues_count=101))
            return response
    report = run(InvalidRepository(100, 1))
    assert report["repositoryCounts"][phase] == {
        "value": None, "errorClass": "invalid-repository-identity"}
    assert "repository-count-unknown" in report["failures"]
    assert report["status"] == "nonhealthy"
    assert all(c["status"] == "unknown" for c in report["comparisons"].values())
    assert not any("disagreement" in f for f in report["failures"])
    if base is AliasFixture and phase == "before":
        assert not report["rest"]["complete"]
        assert report["restTypedCounts"] == {"Issue": None, "PullRequest": None}
    else:
        assert report["rest"]["complete"]
        assert report["restTypedCounts"] == {"Issue": 100, "PullRequest": 1}


@pytest.mark.parametrize("field", ["issues", "pullRequests"])
@pytest.mark.parametrize("fault", ["denied", "partial", "missing", "invalid-sample"])
def test_unavailable_after_sample_makes_identity_comparison_unknown(field, fault):
    class UnavailableSample(Fixture):
        def open(self, req, timeout):
            if req.full_url.endswith("/graphql"):
                body = json.loads(req.data)
                if body["variables"]["size"] == 1 and field + "(" in body["query"]:
                    if fault == "denied":
                        self.calls.append(req)
                        raise HTTPError(req.full_url, 403, SECRET, {}, io.BytesIO(SECRET.encode()))
                    if fault == "partial":
                        self.calls.append(req)
                        return Response({"data": {}, "errors": [{"message": SECRET}]})
                    if fault == "missing":
                        self.calls.append(req)
                        return Response({"data": {"repository": {}}})
                    response = super().open(req, timeout)
                    data = json.loads(response.data)
                    data["data"]["repository"][field]["nodes"] = []
                    return Response(data)
            return super().open(req, timeout)
    report = run(UnavailableSample(2, 2))
    assert report["comparisons"][field + "Identities"] == {
        "status": "unknown", "reason": "after-connection-unknown"}
    assert report["after"][field]["errorClass"]
    assert field + "-unknown-or-incomplete" in report["failures"]
    assert field + "-identity-disagreement" not in report["failures"]
    assert report["status"] == "nonhealthy"


@pytest.mark.parametrize("base", [Fixture, AliasFixture], ids=["named", "numeric"])
@pytest.mark.parametrize("fault", ["denied-before", "denied-after", "missing-count-after", "changed-id-after"])
def test_unconfirmed_repository_observation_never_confirms_comparisons(base, fault):
    class UnconfirmedRepository(base):
        def open(self, req, timeout):
            response = super().open(req, timeout)
            if not req.full_url.endswith("/graphql") and "/issues?" not in req.full_url:
                if self.counts == (1 if fault == "denied-before" else 2):
                    if fault.startswith("denied"):
                        raise HTTPError(req.full_url, 403, SECRET, {}, io.BytesIO(SECRET.encode()))
                    data = json.loads(response.data)
                    if fault == "missing-count-after":
                        data.pop("open_issues_count")
                    else:
                        data["id"] += 1
                    return Response(data)
            return response
    report = run(UnconfirmedRepository(100, 1))
    assert report["status"] == "nonhealthy"
    assert "repository-count-unknown" in report["failures"]
    assert all(c["status"] == "unknown" for c in report["comparisons"].values())
    assert not any("disagreement" in f for f in report["failures"])
    if fault == "changed-id-after":
        assert report["repositoryCounts"]["after"]["errorClass"] == "repository-identity-unstable"


@pytest.mark.parametrize("base", [Fixture, AliasFixture], ids=["named", "numeric"])
def test_stable_authoritative_identity_and_complete_observations_are_comparable(base):
    class StableRepository(base):
        def open(self, req, timeout):
            response = super().open(req, timeout)
            if not req.full_url.endswith("/graphql") and "/issues?" not in req.full_url:
                data = json.loads(response.data)
                data["full_name"] = "ORG/REPO"
                return Response(data)
            return response
    report = run(StableRepository(100, 1))
    assert report["status"] == "observations-agree-not-acceptance"
    assert report["failures"] == []
    assert all(c["status"] == "agree" for c in report["comparisons"].values())
    assert all(not c["complete"] and c["collectionMode"] == "count-sample"
               for c in report["after"].values())


def test_no_redirects():
    assert probe.NoRedirect().redirect_request(None, None, 302, SECRET, {}, "https://evil.example") is None


def test_entrypoint_separate_artifact_and_safe_internal_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", SECRET)
    assert probe.main() == 3
    path = tmp_path / "generated-output/diagnostic-upstream-metadata.json"
    assert path.is_file() and SECRET not in path.read_text()
    assert not (path.parent / "upstream-watcher-report.json").exists()


def test_workflow_optin_inheritance_and_unchanged_normal_jobs():
    workflow = yaml.safe_load(Path(".github/workflows/upstream-watcher.yml").read_text())
    trigger = workflow.get("on", workflow.get(True))
    inputs = trigger["workflow_dispatch"]["inputs"]
    assert inputs["metadata_probe"]["type"] == "boolean"
    assert inputs["metadata_probe"]["default"] is False
    assert trigger["schedule"] == [{"cron": "0 6 * * *"}]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}
    jobs = copy.deepcopy(workflow["jobs"])
    assert jobs["watcher"].pop("if") == "${{ inputs.metadata_probe != true }}"
    # Exact entire normal job, including all step conditions, env and shell bodies.
    for name, expected in (("watcher", "b0fd80fef5e610dd12a337251d0d42708c6733ee77a0728dfa4f226a7ddfa56e"),
                           ("challenge-watch", "e05f40b376110af630fc9666d47a9a4e12dbecad2fe24f5fc96498422bb7d794")):
        assert hashlib.sha256(yaml.safe_dump(jobs[name], sort_keys=True).encode()).hexdigest() == expected
    assert jobs["challenge-watch"]["needs"] == "watcher"
    assert "always()" not in jobs["challenge-watch"]["if"]  # implicit success skips on skipped watcher
    diagnostic = jobs["metadata-probe"]
    assert diagnostic["if"] == "${{ github.event_name == 'workflow_dispatch' && inputs.metadata_probe == true }}"
    assert "permissions" not in diagnostic  # exact workflow-level inheritance, no grant
    assert diagnostic["timeout-minutes"] == 6
    steps = diagnostic["steps"]
    commands = [s["run"] for s in steps if "run" in s]
    assert commands == ["python -m scripts.upstream_watcher.metadata_probe"]
    assert next(s for s in steps if "env" in s)["env"] == {"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}
    upload = steps[-1]
    assert upload["if"] == "always()"
    assert upload["with"]["name"] == "DIAGNOSTIC-upstream-metadata-probe"
    assert upload["with"]["path"] == "generated-output/diagnostic-upstream-metadata.json"
