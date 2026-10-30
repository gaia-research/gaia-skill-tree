"""scripts/steward_issue_close.py: one forge.close_issue action, performed and printed (#2130, lane D2).

The forge is the FakeForge from the closure tests, injected through ``forgeFactory``. Nothing
reaches GitHub; the no-token case exercises the real GhForge constructor only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

from gaia_cli.steward.issuehygiene.closure import ForgeBlockedError, ForgeItemError, closureProven, itemDigest
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, observedDigest
from scripts.steward_issue_close import EXIT_BLOCKED, EXIT_FAILED, EXIT_OK, EXIT_REFUSED, main
from tests.steward.issuehygiene.test_b_closure import FakeForge, a1Scenario, liveOf, planFor, scenarioRow

RECEIPT = ".gaia/steward/issue-hygiene/receipts/R1.jsonl"
REPO_NAME = "gaia-research/gaia-skill-tree"
NOW_FLAG = "2026-10-21T19:30:00Z"


def scenario(tmp_path: Path):
    """The A1 scenario, plus the checkout the executor re-derives from: a writable policy and the census file."""
    manifest, census = a1Scenario(tmp_path)
    policy = tmp_path / "founder" / "steward" / "POLICY.yaml"
    policy.parent.mkdir(parents=True, exist_ok=True)
    text = (REPO_ROOT / "founder" / "steward" / "POLICY.yaml").read_text(encoding="utf-8")
    policy.write_text(text.replace("writesEnabled: false", "writesEnabled: true", 1), encoding="utf-8")
    from .e_fakes import approveClosureFixture
    approveClosureFixture(tmp_path)
    target = tmp_path / CENSUS_INPUT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(census.document), encoding="utf-8")
    return manifest, census


def writeAction(tmp_path: Path, manifest: dict, plan: dict, **changes) -> Path:
    action = {**plan, "receiptPath": RECEIPT, "manifestSha256": observedDigest(manifest),
              "itemSha256": itemDigest(plan), "repo": REPO_NAME, **changes}
    path = tmp_path / "action.json"
    path.write_text(json.dumps(action, sort_keys=True), encoding="utf-8")
    return path


def runScript(tmp_path: Path, action: Path, forge: FakeForge, capsys) -> tuple[int, dict | None]:
    code = main(["--root", str(tmp_path), "--action", str(action), "--run-id", "R1", "--now", NOW_FLAG],
                 forgeFactory=lambda repo, token: forge)
    out = capsys.readouterr().out.strip()
    return code, (json.loads(out) if out else None)


def test_closes_a_proven_issue_and_prints_its_outcome(tmp_path, capsys):
    manifest, _ = scenario(tmp_path)
    forge = FakeForge({10: liveOf(scenarioRow(10))})
    action = writeAction(tmp_path, manifest, planFor(manifest))

    code, outcome = runScript(tmp_path, action, forge, capsys)

    assert code == EXIT_OK
    assert outcome["outcome"] == "closed" and outcome["issue"] == 10
    assert outcome["commentUrl"] == "https://github.com/gaia-research/gaia-skill-tree/issues/10#issuecomment-1001"
    assert closureProven(outcome, 10, REPO_NAME)
    assert forge.issues[10]["state"] == "closed"
    receipts = (tmp_path / RECEIPT).read_text(encoding="utf-8").splitlines()
    # B8 M-3: the budget slot is reserved before the forge call; the terminal line resolves it.
    assert [json.loads(line)["outcome"] for line in receipts] == ["reserved", "closed"]


def test_an_already_closed_issue_is_reported_without_a_write(tmp_path, capsys):
    manifest, _ = scenario(tmp_path)
    live = liveOf(scenarioRow(10))
    live["state"] = "closed"
    forge = FakeForge({10: live})
    action = writeAction(tmp_path, manifest, planFor(manifest))

    code, outcome = runScript(tmp_path, action, forge, capsys)

    assert code == EXIT_OK and outcome["outcome"] == "already-closed"
    assert forge.writes() == []


def test_a_moved_issue_is_a_stale_skip_with_no_write(tmp_path, capsys):
    manifest, _ = scenario(tmp_path)
    live = liveOf(scenarioRow(10))
    live["updatedAt"] = "2026-10-21T21:00:00Z"
    forge = FakeForge({10: live})
    action = writeAction(tmp_path, manifest, planFor(manifest))

    code, outcome = runScript(tmp_path, action, forge, capsys)

    assert code == EXIT_OK and outcome["outcome"] == "stale-skip"
    assert forge.writes() == []


def test_a_blocked_forge_exits_three_and_says_so(tmp_path, capsys):
    manifest, _ = scenario(tmp_path)
    forge = FakeForge({10: liveOf(scenarioRow(10))}, failures={("get", 10): ForgeBlockedError("http-403")})
    action = writeAction(tmp_path, manifest, planFor(manifest))

    code, outcome = runScript(tmp_path, action, forge, capsys)

    assert code == EXIT_BLOCKED
    assert outcome["outcome"] == "blocked" and outcome["failure"] == "get-issue: http-403"
    assert forge.writes() == []


def test_an_item_failure_exits_one_and_leaves_the_issue_open(tmp_path, capsys):
    manifest, _ = scenario(tmp_path)
    forge = FakeForge({10: liveOf(scenarioRow(10))}, failures={("close", 10): ForgeItemError("http-422")})
    action = writeAction(tmp_path, manifest, planFor(manifest))

    code, outcome = runScript(tmp_path, action, forge, capsys)

    assert code == EXIT_FAILED and outcome["outcome"] == "failed"
    assert forge.issues[10]["state"] == "open"


@pytest.mark.parametrize("receipt", [
    "/tmp/elsewhere.jsonl",
    ".gaia/steward/issue-hygiene/receipts/../../../escape.jsonl",
    ".gaia/steward/issue-hygiene/receipts/R1.json",
    ".gaia/steward/elsewhere/R1.jsonl",
])
def test_a_receipt_outside_the_store_is_refused_before_any_forge_call(tmp_path, capsys, receipt):
    manifest, _ = scenario(tmp_path)
    forge = FakeForge({10: liveOf(scenarioRow(10))})
    action = writeAction(tmp_path, manifest, planFor(manifest), receiptPath=receipt)

    code, outcome = runScript(tmp_path, action, forge, capsys)

    assert code == EXIT_REFUSED and outcome["outcome"] == "refused"
    assert forge.calls == []


@pytest.mark.parametrize("missing", ["comment", "expectedSnapshot", "manifestSha256", "itemSha256"])
def test_an_action_missing_a_required_field_is_refused(tmp_path, capsys, missing):
    manifest, _ = scenario(tmp_path)
    action = {**planFor(manifest), "receiptPath": RECEIPT, "manifestSha256": manifest["manifestSha256"],
              "itemSha256": itemDigest(planFor(manifest))}
    del action[missing]
    path = tmp_path / "action.json"
    path.write_text(json.dumps(action, sort_keys=True), encoding="utf-8")

    code, outcome = runScript(tmp_path, path, FakeForge({10: liveOf(scenarioRow(10))}), capsys)

    assert code == EXIT_REFUSED and outcome is None  # an unreadable action has no outcome to report


def test_an_empty_closing_comment_is_refused(tmp_path, capsys):
    manifest, _ = scenario(tmp_path)
    action = writeAction(tmp_path, manifest, planFor(manifest), comment="   ")

    code, _ = runScript(tmp_path, action, FakeForge({10: liveOf(scenarioRow(10))}), capsys)

    assert code == EXIT_REFUSED


def test_a_non_authority_a_plan_is_refused_not_crashed(tmp_path, capsys):
    manifest, _ = scenario(tmp_path)
    action = writeAction(tmp_path, manifest, planFor(manifest), authority="B")

    code, outcome = runScript(tmp_path, action, FakeForge({10: liveOf(scenarioRow(10))}), capsys)

    assert code == EXIT_REFUSED and outcome["outcome"] == "refused"


def test_without_a_token_the_real_forge_refuses_and_nothing_is_written(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    manifest, _ = scenario(tmp_path)
    action = writeAction(tmp_path, manifest, planFor(manifest))

    code = main(["--root", str(tmp_path), "--action", str(action)])

    assert code == EXIT_BLOCKED
    assert capsys.readouterr().out == ""
    assert not (tmp_path / RECEIPT).exists()
