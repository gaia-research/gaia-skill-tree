"""Lane B8 M-2 and M-3, and H-3(c): the closure budget is honoured across runs, processes and planning.

- M-2: the planner filters pairs already recorded as done before it applies the per-run cap, so ten closures do
  not starve the next apply.
- M-3: the hourly budget check and its reservation happen under one repository-keyed lock. Two real processes
  racing for the last slot of an hour get exactly one reservation.
- H-3(c): closures pending in any run count against the hourly budget at emission time.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from gaia_cli.steward.issuehygiene.closure import appendReceipt, planClosures
from gaia_cli.steward.issuehygiene.executor import RECEIPTDIR, hourlyBudget
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from tests.steward.issuehygiene.e_fakes import REPO, censusOf as censusOfDocument, makeCheckout
from tests.steward.issuehygiene.test_b_reconcile import NOW, censusOf as rowsCensus, childRow, policyFor, skill, umbrellaRow
from tests.steward.issuehygiene.test_e_steward_full_e2e import closeActions, setUpSteward
from tests.steward.issuehygiene.test_e_steward_full_e2e import refuseNetwork  # noqa: F401 - autouse, offline

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "src"
HOUR_START = "2026-10-21T19:10:00Z"


def blobFor(number: int) -> str:
    return f"https://github.com/obra/superpowers/blob/main/skills/skill-{number}/SKILL.md"


def manyChildren(tmp_path: Path, count: int):
    rows = [umbrellaRow(20, "obra/superpowers", "v7.0.0")] + [childRow(n, f"obra/skill-{n}", blobFor(n)) for n in range(1, count + 1)]
    document = rowsCensus(rows).document
    named = {f"obra/skill-{n}": skill(f"obra/skill-{n}", github=blobFor(n)) for n in range(1, count + 1)}
    return makeCheckout(tmp_path, census=document, named=named), document


def closedReceipt(key: str, issue: int, runId: str = "OLD") -> dict:
    return {"schemaVersion": "steward-issue-closure-receipt-v1", "runId": runId, "key": key, "issue": issue,
            "outcome": "closed", "closedAt": HOUR_START, "commentUrl": None, "commentId": 1,
            "markerVerified": False, "failure": None, "recordedAt": HOUR_START}


# --- M-2: done pairs are filtered before the cap -------------------------------------------------

def test_the_planner_drops_done_pairs_before_it_applies_the_per_run_cap(tmp_path: Path) -> None:
    root, document = manyChildren(tmp_path, 12)
    policy = policyFor(maxClosuresPerRun=10)
    manifest = reconcile(censusOfDocument(document, NOW), buildRegistryIndex(root), policy, NOW)
    everything = planClosures(manifest, policy)
    assert len(everything) == 10, "the cap applies to the plan"
    done = frozenset((plan["key"], plan["issue"]) for plan in everything)
    remaining = planClosures(manifest, policy, done=done)
    assert [plan["issue"] for plan in remaining] == [11, 12], "after ten recorded closures the next apply still finds two"


# --- M-3: the budget check and the reservation are one step, under one lock ----------------------

def test_a_reservation_takes_one_slot_and_a_terminal_line_for_the_same_pair_releases_it(tmp_path: Path) -> None:
    from gaia_cli.steward.issuehygiene.executor import reserveClosure

    root = tmp_path / "checkout"
    store = root / RECEIPTDIR
    appendReceipt(store / "OLD.jsonl", {"outcome": "closed", "key": "k", "issue": 1, "closedAt": HOUR_START, "runId": "OLD"})
    policy = policyFor(maxClosuresPerRun=10)
    now = datetime(2026, 10, 21, 19, 30, tzinfo=timezone.utc)
    before = hourlyBudget(root, now, policy)
    reserveClosure(root, store / "R1.jsonl", policy, now, "pair-a", 2, "R1", REPO)
    assert hourlyBudget(root, now, policy) == before - 1
    appendReceipt(store / "R1.jsonl", {"outcome": "closed", "key": "pair-a", "issue": 2, "closedAt": HOUR_START, "runId": "R1"})
    assert hourlyBudget(root, now, policy) == before - 1, "the terminal line replaces the reservation, it is not counted twice"


CHILD = r'''
import sys, time
from datetime import datetime, timezone
from pathlib import Path
from gaia_cli.steward.issuehygiene import executor
from gaia_cli.steward.issuehygiene.hygienepolicy import loadHygienePolicy
root, runId, issue = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
real = executor.hourlyBudget
def slow(*args, **kwargs):
    time.sleep(0.6)
    return real(*args, **kwargs)
executor.hourlyBudget = slow
policy = loadHygienePolicy({"maxClosuresPerRun": 10, "maxCensusAgeSeconds": 21600, "closedWindowDays": 30,
                            "enabledRules": ["A1-child-curated"], "a5Disabled": [], "writesEnabled": True})
now = datetime(2026, 10, 21, 19, 30, tzinfo=timezone.utc)
try:
    executor.reserveClosure(root, root / ".gaia/steward/issue-hygiene/receipts" / (runId + ".jsonl"), policy, now,
                            "pair-" + str(issue), issue, runId, "gaia-research/gaia-skill-tree")
except executor.ActionRefused as exc:
    print("refused " + exc.code)
else:
    print("reserved")
'''


def test_two_real_processes_at_nine_of_ten_reserve_exactly_one_slot(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    store = root / RECEIPTDIR
    for issue in range(1, 10):
        appendReceipt(store / "OLD.jsonl", {"outcome": "closed", "key": f"old-{issue}", "issue": issue,
                                            "closedAt": HOUR_START, "runId": "OLD"})
    environment = {"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"}
    procs = [subprocess.Popen([sys.executable, "-c", CHILD, str(root), runId, str(100 + index)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
             for index, runId in enumerate(("R1", "R2"))]
    outputs = [proc.communicate(timeout=120)[0].strip() for proc in procs]
    assert sorted(output.split()[0] for output in outputs) == ["refused", "reserved"], outputs
    total = sum(1 for path in store.glob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()
                if '"outcome": "reserved"' in line)
    assert total == 1


# --- H-3(c): pending closures count toward the hourly budget at emission time --------------------

def test_a_same_hour_second_run_emits_only_what_the_hour_has_left(tmp_path, monkeypatch, capsys) -> None:
    steward, _gh, picks = setUpSteward(tmp_path, monkeypatch, capsys, 12)
    appendReceipt(steward.root / RECEIPTDIR / "OLD.jsonl",
                  {"outcome": "closed", "key": "old", "issue": 1, "closedAt": HOUR_START, "runId": "OLD"})
    appendReceipt(steward.root / RECEIPTDIR / "OLD.jsonl",
                  {"outcome": "closed", "key": "old2", "issue": 2, "closedAt": HOUR_START, "runId": "OLD"})
    appendReceipt(steward.root / RECEIPTDIR / "OLD.jsonl",
                  {"outcome": "closed", "key": "old3", "issue": 3, "closedAt": HOUR_START, "runId": "OLD"})
    appendReceipt(steward.root / RECEIPTDIR / "OLD.jsonl",
                  {"outcome": "closed", "key": "old4", "issue": 4, "closedAt": HOUR_START, "runId": "OLD"})
    code, first = steward.run()
    assert code == 0 and len(closeActions(first)) == 6, "the hour has six of ten left"
    code, second = steward.run()
    assert closeActions(second) == [], "pending closures of the first run hold the rest of the hour's budget"
