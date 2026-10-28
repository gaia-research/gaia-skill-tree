"""Mission-phase regressions: production facades and transport, all forge I/O mocked.

Older closure unit tests exercise the private already-proven worker. These tests
exercise the PUBLIC policy/proof boundary as well, without weakening it for tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.authority import DECISION_PATH, closureAuthorityApproved
from gaia_cli.steward.issuehygiene.closure import (
    ActionRefused, ForgeBlockedError, executeClosure, executeClosures,
    _executeProvenClosure, planClosures,
)
from gaia_cli.steward.policy import StewardPolicy
from scripts.steward_issue_reconcile import GhForge
from tests.steward.issuehygiene.test_b5_closure_guard import (
    checkout, Forge, ownMarkerPlan, bigUmbrella, liveUmbrella,
)
from tests.steward.issuehygiene.test_b7_executor import planAction, childLive, REPO, RECEIPT
from tests.steward.issuehygiene.test_b_reconcile import NOW, policyFor
from tests.steward.issuehygiene.test_b_closure import liveOf, scenarioRow


def planFrom(root, document):
    from gaia_cli.steward.issuehygiene.executor import gateClosure
    from tests.steward.issuehygiene.test_b7_executor import RECEIPTDIR
    action = json.loads(planAction(root, document).read_text())
    return gateClosure(root, action, root / RECEIPT, "R1", NOW, REPO)


@pytest.mark.parametrize("entry", [executeClosure, executeClosures])
def test_public_direct_call_without_checkout_has_no_authority(tmp_path, entry):
    _, plan = ownMarkerPlan(tmp_path)
    forge = Forge({10: liveOf(scenarioRow(10))})
    with pytest.raises(ActionRefused):
        entry([plan] if entry is executeClosures else plan, forge, tmp_path / "r.jsonl", NOW)
    assert forge.calls == []
    assert not (tmp_path / "r.jsonl").exists()


@pytest.mark.parametrize("status", ["open", "missing", "malformed"])
def test_switch_alone_cannot_ratify_closure(tmp_path, status):
    root, document = checkout(tmp_path)
    plan = planFrom(root, document)
    path = root / DECISION_PATH
    if status == "missing":
        path.unlink()
    else:
        path.write_text("{}" if status == "malformed" else json.dumps({"schemaVersion": "steward-decision-v1",
            "id": "steward-issue-closure-authority", "status": status}))
    policy = StewardPolicy.load(root).issue_hygiene
    assert not policy.writesEnabled and policy.enabledRules == ()
    forge = Forge({10: childLive(document)})
    with pytest.raises(ActionRefused, match="unratified"):
        executeClosure(plan, forge, root / RECEIPT, NOW, "R1", REPO, root=root)
    assert forge.calls == []
    assert not (root / RECEIPT).exists()


@pytest.mark.parametrize("resolution", [None, "rejected", "reject proposal: retain human-reviewed closure"])
def test_decided_is_not_affirmative_authority(tmp_path, resolution):
    root, document = checkout(tmp_path)
    plan = planFrom(root, document)
    path = root / DECISION_PATH
    record = json.loads(path.read_text())
    record["status"] = "decided"
    if resolution is None:
        record.pop("resolution", None)
    else:
        record["resolution"] = resolution
    path.write_text(json.dumps(record))
    assert not closureAuthorityApproved(root)
    assert not StewardPolicy.load(root).issue_hygiene.writesEnabled
    forge = Forge({10: childLive(document)})
    with pytest.raises(ActionRefused, match="unratified"):
        executeClosure(plan, forge, root / RECEIPT, NOW, "R1", REPO, root=root)
    assert not forge.calls


@pytest.mark.parametrize("position", ["before-marker", "after-marker"])
def test_intervening_foreign_comment_anywhere_in_final_history_blocks_close(tmp_path, position):
    _, plan = ownMarkerPlan(tmp_path)
    class RacingForge(Forge):
        def addComment(self, number, body):
            objection = {"body": "maintainer: keep this issue open", "author": "maintainer",
                         "url": f"https://example.test/issues/{number}#issuecomment-9999"}
            if position == "before-marker":
                self.comments.setdefault(number, []).append(objection)
            url = super().addComment(number, body)
            if position == "after-marker":
                self.comments[number].append(objection)
            return url
    forge = RacingForge({10: liveOf(scenarioRow(10))})
    result = _executeProvenClosure(plan, forge, tmp_path / "r.jsonl", NOW)
    assert result["outcome"] == "stale-skip"
    assert not any(call[0] == "close" for call in forge.calls)


def test_public_executor_honors_disabled_switch_and_rejects_forged_proof(tmp_path):
    root, document = checkout(tmp_path)
    plan = planFrom(root, document)
    forge = Forge({10: childLive(document)})
    policy = root / "founder/steward/POLICY.yaml"
    original = policy.read_text()
    policy.write_text(original.replace("writesEnabled: true", "writesEnabled: false"))
    with pytest.raises(ActionRefused, match="writesEnabled"):
        executeClosure(plan, forge, root / RECEIPT, NOW, "R1", REPO, root=root)
    policy.write_text(original)
    plan["evidence"] = []
    with pytest.raises(ActionRefused):
        executeClosure(plan, forge, root / RECEIPT, NOW, "R1", REPO, root=root)
    assert forge.calls == []


def test_public_executor_runs_once_and_replays_without_calls_or_receipts(tmp_path):
    root, document = checkout(tmp_path)
    plan = planFrom(root, document)
    forge = Forge({10: childLive(document)})
    first = executeClosure(plan, forge, root / RECEIPT, NOW, "R1", REPO, root=root)
    assert first["outcome"] == "closed" and first["markerVerified"] is True
    before = (root / RECEIPT).read_bytes()
    calls = list(forge.calls)
    second = executeClosure(plan, forge, root / RECEIPT, NOW, "R1", REPO, root=root)
    assert second["outcome"] == "resumed-done"
    assert forge.calls == calls and (root / RECEIPT).read_bytes() == before


@pytest.mark.parametrize("change", ["body", "labels", "title", "comment"])
def test_maintainer_change_during_comment_post_never_closes(tmp_path, change):
    _, plan = ownMarkerPlan(tmp_path)
    class RacingForge(Forge):
        def addComment(self, number, body):
            url = super().addComment(number, body)
            if change == "comment":
                self.comments[number].append({"body": "please keep open", "author": "maintainer"})
            else:
                self.issues[number][change] = ["security"] if change == "labels" else "changed by maintainer"
            return url
    forge = RacingForge({10: liveOf(scenarioRow(10))})
    result = _executeProvenClosure(plan, forge, tmp_path / "r.jsonl", NOW)
    assert result["outcome"] == "stale-skip"
    assert not any(c[0] == "close" for c in forge.calls)


@pytest.mark.parametrize("damage", ["lost", "tampered"])
def test_multipart_payload_must_be_read_back_in_full_before_close(tmp_path, damage):
    manifest, _, row = bigUmbrella(tmp_path)
    plan = planClosures(manifest, policyFor())[0]
    assert len(plan["comments"]) > 1
    class DamagedForge(Forge):
        def addComment(self, number, body):
            url = super().addComment(number, body)
            if "gaia-steward-closure-part:" in body:
                if damage == "lost": self.comments[number].pop()
                else: self.comments[number][-1]["body"] += "tampered"
            return url
    forge = DamagedForge({20: liveUmbrella(row)})
    result = _executeProvenClosure(plan, forge, tmp_path / "r.jsonl", NOW)
    assert result["outcome"] == "failed"
    assert "not verified" in result["failure"]
    assert not any(c[0] == "close" for c in forge.calls)


def transportForge(pages, count, headers=None):
    def transport(method, url, requestHeaders, payload):
        from urllib.parse import urlsplit, parse_qs
        if "/comments?" not in url:
            return 200, {}, json.dumps({"comments": count})
        page = int(parse_qs(urlsplit(url).query)["page"][0])
        return 200, (headers or {}).get(page, {}), json.dumps(pages.get(page, []))
    return GhForge(REPO, "synthetic-token", transport=transport)


def comment(n):
    return {"id": n, "body": f"comment {n}", "user": {"login": "maintainer"}}


@pytest.mark.parametrize("rows", [{}, [None], ["bad"], [{"id": 1}], []])
def test_malformed_or_false_empty_comment_listing_fails_closed(rows):
    forge = transportForge({1: rows}, 1)
    with pytest.raises(ForgeBlockedError):
        forge.listComments(10)


def test_short_comment_page_with_next_link_is_not_terminal():
    link = f'<https://api.github.com/repos/{REPO}/issues/10/comments?per_page=100&page=2>; rel="next"'
    forge = transportForge({1: [comment(1)], 2: [comment(2)]}, 2, {1: {"link": link}})
    assert [r["body"] for r in forge.listComments(10)] == ["comment 1", "comment 2"]


def test_verified_empty_comment_listing_is_complete():
    assert transportForge({1: []}, 0).listComments(10) == []
