"""Offline probes only: never use credentials or the live network."""
import copy
import hashlib
import io
import json
from pathlib import Path
from urllib.error import HTTPError

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
            return Response({"open_issues_count": len(self.issues) + len(self.prs) +
                             (1 if self.fault == "rest-unstable" and self.counts > 1 else 0)})
        page = int(req.full_url.rsplit("=", 1)[1])
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
    if fault in ("denial", "partial"):
        assert report["before"]["pullRequests"]["totalCount"] is None
        assert report["before"]["pullRequests"]["errorClass"]
        assert report["before"]["issues"]["totalCount"] == 2
    if fault == "denial":
        assert any(r["httpStatus"] == 403 and r["errorClass"] == "permission-denied" for r in report["requests"])


def test_complete_pagination_and_page_budget():
    assert run(Fixture(244, 6))["status"] == "observations-agree-not-acceptance"
    report = run(Fixture(1001, 0))
    assert report["status"] == "nonhealthy"
    assert report["before"]["issues"]["errorClass"] == "page-budget-exhausted"


def test_deadline_and_no_token_never_send_request():
    for token, expired in (("", False), (SECRET, True)):
        fixture = Fixture()
        client = probe.Probe("org/repo", token, fixture)
        if expired:
            client.deadline = 0
        assert client.collect()["status"] == "nonhealthy"
        assert not fixture.calls


@pytest.mark.parametrize("link", [
    '<https://api.github.com/repos/org/other/issues?state=open&per_page=100&page=2>; rel="next"',
    '<https://api.github.com/repos/org/repo/issues?state=open&per_page=100&page=2&token=secret>; rel="next"',
    '<https://user:secret@api.github.com/repos/org/repo/issues?state=open&per_page=100&page=2>; rel="next"',
    SECRET])
def test_unsafe_links_are_not_serialized(link):
    with pytest.raises(probe.DiagnosticError):
        probe.nextPage(link, "org/repo")


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
