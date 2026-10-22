"""Lane B7 round-2 executor blockers: one gate for every closure (H1), the hourly cap across runs (L2),
the clock flags (L3), repo identity (L4, L5, D4), exit codes for repeat runs (D2), proof strictness (D6),
the no-redirect transport (L6) and compact actions (D5).

Nothing here reaches GitHub. Forges are the in-memory fakes from the closure tests.
"""

from __future__ import annotations

import json
import threading
from dataclasses import replace
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.closure import (
    ForgeItemError,
    closureProven,
    executeClosure,
    planClosures,
)
from gaia_cli.steward.issuehygiene.executor import (
    RECEIPTDIR,
    closuresWithinHour,
    compactPlan,
    hourlyBudget,
)
from gaia_cli.steward.issuehygiene.hygienepolicy import HygienePolicy
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, observedDigest
from scripts.steward_issue_close import EXIT_OK, EXIT_REFUSED, main as closeMain
from scripts.steward_issue_reconcile import main as reconcileMain, urllibTransport
from tests.steward.issuehygiene.test_b5_closure_guard import Forge, bigUmbrella, liveUmbrella
from tests.steward.issuehygiene.test_b_closure import liveOf
from tests.steward.issuehygiene.test_b_reconcile import policyFor
from tests.steward.issuehygiene.test_b5_closure_guard import REPO, checkout

RECEIPT = ".gaia/steward/issue-hygiene/receipts/R1.jsonl"
COMMENT = f"https://github.com/{REPO}/issues/10#issuecomment-901"


def childLive(document: dict, number: int = 10) -> dict:
    row = next(row for row in document["issues"] if row["number"] == number)
    return liveOf(row)


def planAction(root: Path, document: dict, **changes) -> Path:
    from gaia_cli.steward.issuehygiene.census import validateCensus  # noqa: F401
    from gaia_cli.steward.issuehygiene.reconcile import reconcile
    from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
    from tests.steward.issuehygiene.e_fakes import censusOf
    from tests.steward.issuehygiene.test_b_reconcile import NOW

    manifest = reconcile(censusOf(document), buildRegistryIndex(root), policyFor(), NOW)
    plan = planClosures(manifest, policyFor())[0]
    action = {**compactPlan(plan), "receiptPath": RECEIPT, "manifestSha256": observedDigest(manifest),
              "repo": REPO, **changes}
    target = root / "action.json"
    target.write_text(json.dumps(action, sort_keys=True), encoding="utf-8")
    return target


def closeRun(root: Path, action: Path, forge: Forge, capsys, now: str = "2026-10-21T19:30:00Z", repo: str | None = None):
    constructed: list[str] = []

    def factory(name, token):
        constructed.append(name)
        return forge

    argv = ["--root", str(root), "--action", str(action), "--run-id", "R1", "--now", now]
    if repo is not None:
        argv += ["--repo", repo]
    code = closeMain(argv, forgeFactory=factory)
    out = capsys.readouterr().out.strip()
    return code, (json.loads(out.splitlines()[-1]) if out else None), constructed


def store(root: Path) -> Path:
    return root / RECEIPTDIR


def applyArgs(root: Path, receipts: Path, *extra: str) -> list[str]:
    return ["--root", str(root), "--apply-closures", "--i-understand-writes", "--receipts", str(receipts), *extra]


# --- H1: one executor, one gate ---------------------------------------------------------------

def test_apply_closures_with_writes_off_refuses_with_zero_forge_calls(tmp_path: Path) -> None:
    root, _ = checkout(tmp_path, policy={"writesEnabled": False})
    calls: list[str] = []
    code = reconcileMain(applyArgs(root, store(root) / "R1.jsonl", "--repo", REPO),
                         forgeFactory=lambda name, token: calls.append(name) or Forge({}))
    assert code == EXIT_REFUSED
    assert calls == []
    assert not (store(root) / "R1.jsonl").exists()


def test_apply_closures_refuses_a_receipts_path_outside_the_store(tmp_path: Path) -> None:
    root, _ = checkout(tmp_path)
    calls: list[str] = []
    elsewhere = tmp_path / "elsewhere" / "R1.jsonl"
    code = reconcileMain(applyArgs(root, elsewhere, "--repo", REPO),
                         forgeFactory=lambda name, token: calls.append(name) or Forge({}))
    assert code == EXIT_REFUSED
    assert calls == [] and not elsewhere.exists()


def test_apply_closures_refuses_a_symlinked_store(tmp_path: Path) -> None:
    root, _ = checkout(tmp_path)
    real = tmp_path / "other-store"
    real.mkdir()
    (root / ".gaia" / "steward").mkdir(parents=True, exist_ok=True)
    (root / ".gaia" / "steward" / "issue-hygiene").symlink_to(real, target_is_directory=True)
    calls: list[str] = []
    code = reconcileMain(applyArgs(root, store(root) / "R1.jsonl", "--repo", REPO),
                         forgeFactory=lambda name, token: calls.append(name) or Forge({}))
    assert code == EXIT_REFUSED
    assert calls == [] and list(real.iterdir()) == []


def test_apply_closures_requires_repo(tmp_path: Path) -> None:
    root, _ = checkout(tmp_path)
    calls: list[str] = []
    code = reconcileMain(applyArgs(root, store(root) / "R1.jsonl"),
                         forgeFactory=lambda name, token: calls.append(name) or Forge({}))
    assert code == EXIT_REFUSED and calls == []


def test_apply_closures_repo_must_equal_the_census_repo(tmp_path: Path) -> None:
    root, _ = checkout(tmp_path)
    calls: list[str] = []
    code = reconcileMain(applyArgs(root, store(root) / "R1.jsonl", "--repo", "someone/else"),
                         forgeFactory=lambda name, token: calls.append(name) or Forge({}))
    assert code == EXIT_REFUSED and calls == []


def test_apply_closures_refuses_the_now_flag(tmp_path: Path) -> None:
    root, _ = checkout(tmp_path)
    calls: list[str] = []
    code = reconcileMain(applyArgs(root, store(root) / "R1.jsonl", "--repo", REPO, "--now", "2026-10-21T19:30:00Z"),
                         forgeFactory=lambda name, token: calls.append(name) or Forge({}))
    assert code == EXIT_REFUSED and calls == []


def test_the_dry_run_is_unchanged_and_still_accepts_now(tmp_path: Path) -> None:
    root, _ = checkout(tmp_path)
    out = tmp_path / "manifest.json"
    code = reconcileMain(["--root", str(root), "--out", str(out), "--now", "2026-10-21T19:30:00Z"])
    assert code == 0 and out.is_file()


# --- L3: the close script reads the real clock, so --now cannot make a stale census look fresh ------

def test_the_close_script_ignores_now(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path)
    action = planAction(root, document)
    forge = Forge({10: childLive(document)})
    code, outcome, constructed = closeRun(root, action, forge, capsys, now="2001-01-01T00:00:00Z")
    assert code == EXIT_OK, "a stale --now must not refuse: the close script reads the real (pinned) clock"
    assert outcome["outcome"] == "closed"


# --- D4: the census repo must be the repo the action and the forge name ----------------------------

def test_a_rewritten_census_repo_refuses_before_any_forge_is_built(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path)
    action = planAction(root, document)
    rewritten = json.loads((root / CENSUS_INPUT).read_text(encoding="utf-8"))
    rewritten["repo"] = "evil/other"
    (root / CENSUS_INPUT).write_text(json.dumps(rewritten), encoding="utf-8")
    code, _, constructed = closeRun(root, action, Forge({10: childLive(document)}), capsys)
    assert code == EXIT_REFUSED
    assert constructed == []


def test_an_action_repo_that_differs_from_the_census_refuses(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path)
    action = planAction(root, document, repo="someone/else")
    code, _, constructed = closeRun(root, action, Forge({10: childLive(document)}), capsys)
    assert code == EXIT_REFUSED and constructed == []


# --- D2: a repeat run on a closed pair is a terminal, exit-0 outcome --------------------------------

def test_a_second_run_on_a_closed_pair_exits_zero_with_its_recorded_outcome(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path)
    action = planAction(root, document)
    forge = Forge({10: childLive(document)})
    first_code, first, _ = closeRun(root, action, forge, capsys)
    assert first_code == EXIT_OK and first["outcome"] == "closed"
    second_code, second, constructed = closeRun(root, action, forge, capsys)
    assert second_code == EXIT_OK
    assert second["outcome"] == "closed"
    assert second["commentUrl"] == first["commentUrl"]
    assert len([call for call in forge.calls if call[0] == "close"]) == 1


# --- L2: the hourly budget counts closures from every run ------------------------------------------

def writeClosedReceipts(root: Path, runId: str, count: int, closedAt: str) -> None:
    store(root).mkdir(parents=True, exist_ok=True)
    lines = []
    for index in range(count):
        lines.append(json.dumps({
            "schemaVersion": "steward-issue-closure-receipt-v1", "runId": runId, "key": f"upstream-candidate:o/r:x{index}",
            "issue": 900 + index, "outcome": "closed", "closedAt": closedAt, "commentUrl": COMMENT,
        }, sort_keys=True))
    (store(root) / f"{runId}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_the_policy_hourly_cap_refuses_a_closure_after_other_runs_used_it(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path)
    action = planAction(root, document)
    cap = policyFor().maxClosuresPerRun
    writeClosedReceipts(root, "R0", cap, "2026-10-21T19:10:00Z")
    code, _, constructed = closeRun(root, action, Forge({10: childLive(document)}), capsys)
    assert code == EXIT_REFUSED and constructed == []


def test_closures_older_than_an_hour_do_not_use_this_hours_budget(tmp_path: Path, capsys) -> None:
    root, document = checkout(tmp_path)
    action = planAction(root, document)
    writeClosedReceipts(root, "R0", 50, "2026-10-21T10:00:00Z")
    code, outcome, _ = closeRun(root, action, Forge({10: childLive(document)}), capsys)
    assert code == EXIT_OK and outcome["outcome"] == "closed"


def test_the_hard_cap_of_25_closures_per_hour_holds_even_when_the_policy_allows_more(tmp_path: Path) -> None:
    root, _ = checkout(tmp_path)
    writeClosedReceipts(root, "R0", 25, "2026-10-21T19:20:00Z")
    now = datetime(2026, 10, 21, 19, 30, tzinfo=timezone.utc)
    generous = replace(policyFor(), maxClosuresPerRun=30)
    assert closuresWithinHour(root, now) == 25
    assert hourlyBudget(root, now, generous) == 0


# --- D6: proof strictness ------------------------------------------------------------------------------

@pytest.mark.parametrize("outcome", [
    {"commentUrl": COMMENT, "markerVerified": "yes"},      # non-bool marker beside a valid URL
    {"commentUrl": COMMENT + "\n"},                        # trailing newline is not a comment URL
    {"commentUrl": ""},                                    # present but empty is invalid, not absent
    {"commentUrl": COMMENT, "commentId": 0},               # present but invalid id beside a valid URL
    {"commentId": 0},                                      # zero is present and invalid
    {"commentId": 901, "markerVerified": 1},               # int is not a bool marker
])
def test_present_but_invalid_proof_fields_are_refused(outcome: dict) -> None:
    assert closureProven(outcome, 10, REPO) is False


def test_a_single_valid_proof_is_accepted() -> None:
    assert closureProven({"commentUrl": COMMENT}, 10, REPO) is True
    assert closureProven({"commentId": 901}, 10, REPO) is True
    assert closureProven({"markerVerified": True}, 10, REPO) is True


# --- L5: repo identity is required for proof ----------------------------------------------------------

def test_closure_proof_requires_the_repo() -> None:
    with pytest.raises(ValueError):
        closureProven({"commentUrl": COMMENT}, 10, None)


# --- L6: a 3xx is never followed by the forge transport ---------------------------------------------

class RedirectingHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        self.send_response(302)
        self.send_header("Location", "/landed")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args) -> None:  # silence test output
        return


def test_the_forge_transport_does_not_follow_a_post_redirect(tmp_path: Path) -> None:
    server = HTTPServer(("127.0.0.1", 0), RedirectingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/repos/x/y/issues/1/comments"
        status, _headers, _text = urllibTransport("POST", url, {"Accept": "application/json"}, b"{}")
        assert status == 302
    finally:
        server.shutdown()
        server.server_close()


# --- D5: compact actions and plans --------------------------------------------------------------------

def test_a_300_candidate_umbrella_gives_a_compact_action_and_the_executor_still_posts_the_full_payload(tmp_path: Path, capsys) -> None:
    from gaia_cli.steward.issuehygiene.sensor import _observedPlan

    manifest, candidates, row = bigUmbrella(tmp_path, count=300)
    plan = planClosures(manifest, policyFor())[0]
    compact = compactPlan(plan)
    assert len(json.dumps(compact, sort_keys=True)) < 8 * 1024
    debtPlan = _observedPlan(plan, manifest)  # the debt state carries the same compact plan (per item)
    assert len(json.dumps(debtPlan, sort_keys=True)) < 8 * 1024
    assert "original" not in compact and "comments" not in compact and "comment" not in compact
    assert compact["preservedSha256"] == plan["preservedSha256"] and compact["closureSha8"] == plan["closureSha8"]


def test_a_compact_action_is_re_derived_and_posts_the_full_preserved_payload(tmp_path: Path, capsys) -> None:
    from tests.steward.issuehygiene.e_fakes import censusOf
    from tests.steward.issuehygiene.test_b_reconcile import NOW
    from gaia_cli.steward.issuehygiene.reconcile import reconcile
    from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex

    manifest, candidates, row = bigUmbrella(tmp_path, count=300)
    root = tmp_path
    (root / CENSUS_INPUT).parent.mkdir(parents=True, exist_ok=True)
    document = {"schemaVersion": "steward-github-census-v1", "repo": REPO, "fetchedAt": "2026-10-21T19:00:00Z",
                "source": "rest", "completeness": {"issues": {"complete": True, "pagesFetched": 1, "expectedPages": 1,
                "itemCount": 1, "lastLink": None}, "pulls": {"complete": True, "pagesFetched": 0, "expectedPages": 0,
                "itemCount": 0, "lastLink": None}}, "issues": [row], "recentlyClosed": []}
    (root / CENSUS_INPUT).write_text(json.dumps(document), encoding="utf-8")
    (root / "founder" / "steward").mkdir(parents=True, exist_ok=True)
    from tests.steward.issuehygiene.e_fakes import editPolicy
    import shutil
    from tests.steward.issuehygiene.e_fakes import REPO_ROOT
    shutil.copy(REPO_ROOT / "founder" / "steward" / "POLICY.yaml", root / "founder" / "steward" / "POLICY.yaml")
    editPolicy(root, {"writesEnabled": True})
    action = {**compactPlan(planClosures(manifest, policyFor())[0]), "receiptPath": RECEIPT,
              "manifestSha256": observedDigest(manifest), "repo": REPO}
    path = root / "action.json"
    path.write_text(json.dumps(action, sort_keys=True), encoding="utf-8")
    forge = Forge({20: liveUmbrella(row)})
    code, outcome, _ = closeRun(root, path, forge, capsys)
    assert code == EXIT_OK and outcome["outcome"] == "closed"
    posted = "".join(entry["body"] for entry in forge.comments.get(20, []))
    for candidate in candidates:
        assert candidate["id"] in posted
    receipt = json.loads((root / RECEIPT).read_text(encoding="utf-8").splitlines()[-1])
    assert receipt["preservedParts"] > 1 and receipt["preservedSha256"] == compactPlan(planClosures(manifest, policyFor())[0])["preservedSha256"]
