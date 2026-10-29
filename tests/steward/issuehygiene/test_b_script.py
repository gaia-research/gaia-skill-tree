from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.closure import ForgeBlockedError, ForgeItemError
from scripts.steward_issue_reconcile import GhForge, main, renderMatrix, renderSummary

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "issuehygiene" / "census-four-families.json"
NOW = "2026-10-21T19:30:00Z"
TOKEN = "ghp_test_secret_token_value"


class FakeTransport:
    """Replays scripted responses and records each request."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests: list[tuple] = []

    def __call__(self, method, url, headers, body):
        self.requests.append((method, url, dict(headers), body))
        if not self.responses:
            raise AssertionError(f"unexpected request {method} {url}")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def jsonResponse(status, payload, headers=None):
    return status, headers or {}, json.dumps(payload)


def test_gh_forge_fails_closed_without_token():
    with pytest.raises(ForgeBlockedError):
        GhForge("owner/repo", None, FakeTransport([]))


def test_gh_forge_get_issue_normalizes_and_sends_bearer_token():
    transport = FakeTransport([jsonResponse(200, {
        "number": 10, "node_id": "I_kw1", "locked": False, "html_url": "https://github.com/owner/repo/issues/10",
        "title": "[intake] x", "state": "open", "state_reason": None, "updated_at": "2026-10-21T10:00:00Z",
        "body": "hello", "labels": [{"name": "upstream:child"}],
    })])
    live = GhForge("owner/repo", TOKEN, transport).getIssue(10)
    assert live == {"number": 10, "nodeId": "I_kw1", "htmlUrl": "https://github.com/owner/repo/issues/10",
                    "locked": False, "title": "[intake] x", "state": "open", "stateReason": None,
                    "updatedAt": "2026-10-21T10:00:00Z", "body": "hello", "labels": ["upstream:child"]}
    method, url, headers, _body = transport.requests[0]
    assert method == "GET" and url == "https://api.github.com/repos/owner/repo/issues/10"
    assert headers["Authorization"] == f"Bearer {TOKEN}"


def test_gh_forge_rejects_pull_requests_as_item_error():
    transport = FakeTransport([jsonResponse(200, {"title": "pr", "pull_request": {}})])
    with pytest.raises(ForgeItemError):
        GhForge("owner/repo", TOKEN, transport).getIssue(5)


def test_gh_forge_auth_and_rate_limits_are_blocked_other_errors_are_item_local():
    for status in (401, 403, 429):
        with pytest.raises(ForgeBlockedError):
            GhForge("o/r", TOKEN, FakeTransport([jsonResponse(status, {})])).getIssue(1)
    with pytest.raises(ForgeItemError):
        GhForge("o/r", TOKEN, FakeTransport([jsonResponse(422, {})])).closeIssue(1, "completed")


def test_gh_forge_transport_failure_is_blocked_and_never_leaks_the_token():
    transport = FakeTransport([OSError("proxy refused " + TOKEN)])
    with pytest.raises(OSError):
        GhForge("o/r", TOKEN, transport).getIssue(1)


def test_gh_forge_lists_all_comment_pages():
    first = [{"id": index + 1, "body": f"c{index}", "html_url": f"u{index}", "user": {"login": "bot"}} for index in range(100)]
    second = [{"id": 101, "body": "last", "html_url": "ulast", "user": {"login": "bot"}}]
    link = '<https://api.github.com/repos/o/r/issues/9/comments?per_page=100&page=2>; rel="next"'
    transport = FakeTransport([jsonResponse(200, {"comments": 101}), jsonResponse(200, first, {"link": link}),
                               jsonResponse(200, second), jsonResponse(200, [])])
    comments = GhForge("o/r", TOKEN, transport).listComments(9)
    assert len(comments) == 101
    assert comments[-1] == {"body": "last", "url": "ulast", "author": "bot", "createdAt": None, "updatedAt": None}
    assert "page=2" in transport.requests[2][1]


def test_gh_forge_close_sends_state_reason_and_comment_returns_url():
    transport = FakeTransport([jsonResponse(201, {"html_url": "https://github.com/o/r/issues/3#c1"}),
                               jsonResponse(200, {"state": "closed", "state_reason": "not_planned"})])
    forge = GhForge("o/r", TOKEN, transport)
    assert forge.addComment(3, "body") == "https://github.com/o/r/issues/3#c1"
    forge.closeIssue(3, "not_planned")
    method, url, _headers, body = transport.requests[1]
    assert method == "PATCH" and url.endswith("/issues/3")
    assert json.loads(body) == {"state": "closed", "state_reason": "not_planned"}


def writePolicy(path: Path, writes: bool = True) -> Path:
    path.write_text(
        "issueHygiene:\n"
        "  maxClosuresPerRun: 10\n"
        "  maxCensusAgeSeconds: 21600\n"
        "  closedWindowDays: 30\n"
        f"  writesEnabled: {'true' if writes else 'false'}\n"
        "  enabledRules:\n"
        "    - A1-child-curated\n"
        "    - A2-umbrella-synced\n"
        "    - A3-umbrella-superseded\n"
        "    - A4-duplicate-child\n"
        "    - A5-botreport-superseded\n"
        "  a5Disabled: []\n",
        encoding="utf-8",
    )
    return path


def fakeRoot(tmp_path: Path) -> Path:
    from tests.steward.issuehygiene.e_fakes import copySchema

    root = tmp_path / "repo"
    copySchema(root)
    (root / "registry" / "named" / "obra").mkdir(parents=True)
    (root / "registry" / "named" / "obra" / "writing-skills.md").write_text(
        "---\nid: obra/writing-skills\ncontributor: obra\nstatus: named\n"
        "links:\n  github: https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md\n---\n",
        encoding="utf-8",
    )
    return root


def test_dry_run_writes_only_requested_outputs_and_never_calls_forge(tmp_path: Path):
    root = fakeRoot(tmp_path)
    out = tmp_path / "out" / "manifest.json"
    matrix = tmp_path / "out" / "matrix.md"
    policy = writePolicy(tmp_path / "policy.yaml")
    forgeCalls = []

    def forbiddenFactory(name, secret):
        forgeCalls.append(name)
        raise AssertionError("dry run must not build a forge")

    code = main(
        ["--root", str(root), "--census", str(FIXTURE), "--policy", str(policy), "--now", NOW,
         "--out", str(out), "--matrix", str(matrix), "--summary"],
        forgeFactory=forbiddenFactory,
    )
    assert code == 0
    assert forgeCalls == []
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["censusStatus"] == "complete"
    assert manifest["stats"]["classA"] == 1
    assert not (tmp_path / "out" / "receipts").exists()
    assert matrix.read_text(encoding="utf-8").startswith("# Steward issue reconciliation matrix")


def test_apply_without_acknowledgement_is_refused_with_usage_error(tmp_path: Path):
    code = main(["--root", str(tmp_path), "--apply-closures", "--receipts", str(tmp_path / "r.jsonl")])
    assert code == 2
    code = main(["--root", str(tmp_path), "--apply-closures", "--i-understand-writes"])
    assert code == 2


def checkoutWith(tmp_path: Path, census: dict | str | None = None) -> tuple[Path, Path]:
    """A writable checkout with the fixture census and the obra/writing-skills registry record. B7 H1: apply reads the checkout."""
    from tests.steward.issuehygiene.e_fakes import makeCheckout

    document = json.loads(FIXTURE.read_text(encoding="utf-8")) if census is None else census
    root = makeCheckout(tmp_path, census=document, named={
        "obra/writing-skills": "---\nid: obra/writing-skills\ncontributor: obra\nstatus: named\n"
                               "links:\n  github: https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md\n---\n",
    })
    return root, store(root)


def store(root: Path) -> Path:
    return root / ".gaia" / "steward" / "issue-hygiene" / "receipts"


def test_apply_refused_when_census_incomplete_and_no_forge_built(tmp_path: Path):
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["completeness"]["issues"]["complete"] = False
    root, receipts = checkoutWith(tmp_path, census=document)
    code = main(
        ["--root", str(root), "--apply-closures", "--i-understand-writes",
         "--receipts", str(receipts / "r.jsonl"), "--repo", "gaia-research/gaia-skill-tree"],
        forgeFactory=lambda name, secret: pytest.fail("no forge for an incomplete census"),
    )
    assert code == 2
    assert not (receipts / "r.jsonl").exists()


def test_apply_refused_without_token_and_no_writes(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    root, receipts = checkoutWith(tmp_path)
    code = main(
        ["--root", str(root), "--apply-closures", "--i-understand-writes",
         "--receipts", str(receipts / "r.jsonl"), "--repo", "gaia-research/gaia-skill-tree"],
    )
    assert code == 3
    assert not (receipts / "r.jsonl").exists()


def test_apply_with_forge_writes_receipts_for_plans_and_is_replay_idempotent(tmp_path: Path):
    root, receipts_dir = checkoutWith(tmp_path)
    rows = {item["number"]: item for item in json.loads(FIXTURE.read_text(encoding="utf-8"))["issues"]}

    class LiveForge:
        def __init__(self):
            self.closed = []
            self.comments = []

        def getIssue(self, number):
            live = rows[number]
            return {"number": number, "title": live["title"], "state": live["state"], "stateReason": None,
                    "updatedAt": live["updatedAt"], "body": live["body"],
                    "labels": [label if isinstance(label, str) else label["name"] for label in live["labels"]]}

        def listComments(self, number):
            return [{"body": body, "author": "steward-bot"} for n, body in self.comments if n == number]

        def whoami(self):
            return "steward-bot"

        def addComment(self, number, body):
            self.comments.append((number, body))
            return f"https://github.com/gaia-research/gaia-skill-tree/issues/{number}#issuecomment-{9000 + number}"

        def closeIssue(self, number, stateReason, duplicateOf=None):
            self.closed.append((number, stateReason, duplicateOf))

    forge = LiveForge()
    receipts = receipts_dir / "run.jsonl"
    args = ["--root", str(root), "--apply-closures", "--i-understand-writes",
            "--receipts", str(receipts), "--repo", "gaia-research/gaia-skill-tree"]
    assert main(args, forgeFactory=lambda name, secret: forge) == 0
    # fakeRoot registers obra/writing-skills with the exact evidence URL of child #2024, the only A1 item there
    assert forge.closed == [(2024, "completed", None)]
    lines = receipts.read_text(encoding="utf-8").splitlines()
    # B8 M-3: the budget slot is reserved before the forge call, and the terminal line resolves it.
    assert [json.loads(line)["outcome"] for line in lines] == ["reserved", "closed"]
    before = receipts.read_bytes()
    replay = LiveForge()
    assert main(args, forgeFactory=lambda name, secret: replay) == 0
    assert replay.closed == [] and replay.comments == []
    assert receipts.read_bytes() == before


def test_same_census_twice_gives_byte_identical_manifest(tmp_path: Path):
    root = fakeRoot(tmp_path)
    policy = writePolicy(tmp_path / "policy.yaml")
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    for target in (first, second):
        assert main(["--root", str(root), "--census", str(FIXTURE), "--policy", str(policy), "--now", NOW, "--out", str(target)]) == 0
    assert first.read_bytes() == second.read_bytes()


def test_shuffled_census_gives_byte_identical_manifest(tmp_path: Path):
    root = fakeRoot(tmp_path)
    policy = writePolicy(tmp_path / "policy.yaml")
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    shuffled = dict(document)
    issues = list(document["issues"])
    random.Random(11).shuffle(issues)
    shuffled["issues"] = issues
    census = tmp_path / "shuffled.json"
    census.write_text(json.dumps(shuffled), encoding="utf-8")
    base = tmp_path / "base.json"
    again = tmp_path / "again.json"
    assert main(["--root", str(root), "--census", str(FIXTURE), "--policy", str(policy), "--now", NOW, "--out", str(base)]) == 0
    assert main(["--root", str(root), "--census", str(census), "--policy", str(policy), "--now", NOW, "--out", str(again)]) == 0
    assert base.read_bytes() == again.read_bytes()


def test_matrix_is_complete_and_paginated():
    manifest = json.loads(json.dumps({
        "manifestSha256": "a" * 64, "censusStatus": "complete", "censusFetchedAt": NOW, "stats": {"openIssues": 0},
        "items": [{"issue": n, "key": f"issue:{n}", "kind": "untracked", "state": "actionable", "parent": None,
                   "authority": "none", "ruleId": None, "evidence": [], "notProven": [], "unknowns": [],
                   "proposedTransition": {"action": "keep", "stateReason": None, "duplicateOf": None}}
                  for n in range(1, 231)],
        "batches": [], "founderQuestions": [],
    }))
    text = renderMatrix(manifest)
    assert "Page 1 of 3" in text and "Page 3 of 3" in text
    assert text.count("`issue:") == 230
    summary = renderSummary(manifest, plannedClosures=0)
    assert "family" in summary and "closure plans: 0" in summary
