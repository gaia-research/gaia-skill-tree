"""Lane B5 pilot path: closures through steward_issue_reconcile with explicit flags, not the policy.

The shipped policy is dry-run (B5). The pilot (contract section 6) runs only with --apply-closures,
--receipts and --i-understand-writes, and at most --max-closures. These tests pin that path.
"""

from __future__ import annotations

from pathlib import Path

from gaia_cli.steward.issuehygiene.closure import closureProven
from scripts.steward_issue_reconcile import main as reconcileMain
from tests.steward.issuehygiene.e_fakes import makeCheckout
from tests.steward.issuehygiene.test_b5_closure_guard import Forge, receiptsOf
from tests.steward.issuehygiene.test_b_closure import liveOf, scenarioRow
from tests.steward.issuehygiene.test_b_reconcile import BLOB, censusOf, childRow, mkRow, skill, umbrellaRow

SECOND = "https://github.com/obra/superpowers/blob/main/skills/other-skill/SKILL.md"


def twoChildCheckout(tmp_path: Path, policy: dict | None = None) -> Path:
    rows = [
        umbrellaRow(20, "obra/superpowers", "v7.0.0"),
        childRow(10, "obra/writing-skills", BLOB),
        childRow(11, "obra/other-skill", SECOND),
    ]
    return makeCheckout(
        tmp_path, census=censusOf(rows).document,
        named={"obra/writing-skills": skill("obra/writing-skills", github=BLOB),
               "obra/other-skill": skill("obra/other-skill", github=SECOND)},
        policy=policy,
    )


def liveForges() -> Forge:
    return Forge({
        10: liveOf(scenarioRow(10)),
        11: liveOf(mkRow(11, "[intake] obra/other-skill", "", labels=("upstream:child",))),
    })


def test_explicit_pilot_flags_close_under_the_dry_run_policy_within_the_cap(tmp_path: Path, capsys) -> None:
    root = twoChildCheckout(tmp_path, policy={"writesEnabled": False})
    forge = liveForges()
    receipts = tmp_path / "pilot.jsonl"

    code = reconcileMain(
        ["--root", str(root), "--now", "2026-10-21T19:30:00Z", "--summary", "--apply-closures",
         "--receipts", str(receipts), "--i-understand-writes", "--max-closures", "1"],
        forgeFactory=lambda name, secret: forge,
    )
    out = capsys.readouterr().out

    assert code == 0
    assert len([call for call in forge.writes() if call[0] == "close"]) == 1
    closedReceipts = [receipt for receipt in receiptsOf(receipts) if receipt["outcome"] == "closed"]
    assert len(closedReceipts) == 1
    assert closureProven({"outcome": "closed", "commentUrl": closedReceipts[0]["commentUrl"]}, closedReceipts[0]["issue"])
    assert "writesEnabled is false" in out and "held as debt" in out


def test_the_pilot_cap_can_only_lower_the_policy_cap(tmp_path: Path, capsys) -> None:
    root = twoChildCheckout(tmp_path, policy={"writesEnabled": False, "maxClosuresPerRun": 1})
    forge = liveForges()

    code = reconcileMain(
        ["--root", str(root), "--now", "2026-10-21T19:30:00Z", "--apply-closures",
         "--receipts", str(tmp_path / "pilot.jsonl"), "--i-understand-writes", "--max-closures", "9"],
        forgeFactory=lambda name, secret: forge,
    )
    capsys.readouterr()

    assert code == 0
    assert len([call for call in forge.writes() if call[0] == "close"]) == 1


def test_the_pilot_refuses_without_the_explicit_flags(tmp_path: Path, capsys) -> None:
    root = twoChildCheckout(tmp_path, policy={"writesEnabled": False})
    forge = liveForges()

    code = reconcileMain(
        ["--root", str(root), "--now", "2026-10-21T19:30:00Z", "--apply-closures"],
        forgeFactory=lambda name, secret: forge,
    )
    capsys.readouterr()

    assert code == 2
    assert forge.writes() == []
