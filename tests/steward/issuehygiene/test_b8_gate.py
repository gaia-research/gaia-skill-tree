"""Lane B8 H-3(b): the closure gate compares the action's own evidence digest, not the whole-manifest digest.

Unrelated census churn after emission (another issue's updatedAt moves) must not refuse a closure whose own proof
is unchanged. A change to the closure's own proof (its title, body, labels, state or evidence) still refuses it,
and the refusal carries a machine-readable reason code the driver records.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from gaia_cli.steward.issuehygiene.closure import closureAction, itemDigest, planClosures
from gaia_cli.steward.issuehygiene.executor import ActionRefused, gateClosure
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT
from scripts.steward_issue_close import EXIT_OK, EXIT_REFUSED, main as closeMain
from tests.steward.issuehygiene.e_fakes import censusOf as censusOfDocument, makeCheckout
from tests.steward.issuehygiene.test_b5_closure_guard import Forge, REPO
from tests.steward.issuehygiene.test_b_closure import liveOf
from tests.steward.issuehygiene.test_b_reconcile import BLOB, NOW, censusOf, childRow, mkRow, policyFor, skill, umbrellaRow

RECEIPT = ".gaia/steward/issue-hygiene/receipts/R1.jsonl"


def scenario(tmp_path: Path):
    unrelated = mkRow(30, "[intake] an unrelated open intake", "unrelated body", labels=("upstream:child",))
    rows = [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB), unrelated]
    document = censusOf(rows).document
    root = makeCheckout(tmp_path, census=document, named={"obra/writing-skills": skill("obra/writing-skills", github=BLOB)})
    return root, document


def emit(root: Path, document: dict):
    """What the runner emits: the plan, its per-item digest and the manifest digest, from the census on disk."""
    policy = policyFor()
    manifest = reconcile(censusOfDocument(document, NOW), buildRegistryIndex(root), policy, NOW)
    plan = next(plan for plan in planClosures(manifest, policy) if plan["issue"] == 10)
    return closureAction(plan, RECEIPT, manifest["manifestSha256"], REPO), plan


def writeCensus(root: Path, document: dict) -> None:
    (root / CENSUS_INPUT).write_text(json.dumps(document), encoding="utf-8")


def runClose(root: Path, action: dict, capsys) -> tuple[int, list[str], str]:
    actionFile = root / "action.json"
    actionFile.write_text(json.dumps(action, sort_keys=True), encoding="utf-8")
    constructed: list[str] = []
    code = closeMain(["--root", str(root), "--action", str(actionFile), "--run-id", "R1", "--repo", REPO],
                     forgeFactory=lambda repo, token: constructed.append(repo) or Forge({10: liveOf(childRowOf(root))}))
    out = capsys.readouterr()
    return code, constructed, out.out + out.err


def childRowOf(root: Path) -> dict:
    return next(row for row in json.loads((root / CENSUS_INPUT).read_text(encoding="utf-8"))["issues"] if row["number"] == 10)


def test_an_unrelated_updated_at_bump_after_emission_still_passes_the_gate(tmp_path: Path, capsys) -> None:
    root, document = scenario(tmp_path)
    action, _ = emit(root, document)
    moved = copy.deepcopy(document)
    for row in moved["issues"]:
        if row["number"] == 30:
            row["updatedAt"] = "2026-10-21T19:20:00Z"
    writeCensus(root, moved)
    code, constructed, text = runClose(root, action, capsys)
    assert code == EXIT_OK, text
    assert constructed == [REPO]
    assert '"outcome": "closed"' in text or '"outcome":"closed"' in text


def test_a_change_to_the_closures_own_title_refuses_it_with_a_reason_code(tmp_path: Path, capsys) -> None:
    root, document = scenario(tmp_path)
    action, _ = emit(root, document)
    changed = copy.deepcopy(document)
    for row in changed["issues"]:
        if row["number"] == 10:
            row["title"] = "[intake] renamed after emission"
    writeCensus(root, changed)
    code, constructed, text = runClose(root, action, capsys)
    assert code == EXIT_REFUSED
    assert constructed == [], "no forge is built for a closure whose own proof moved"
    assert '"outcome": "refused"' in text or '"outcome":"refused"' in text
    assert '"reason": "item-changed"' in text or '"reason":"item-changed"' in text


def test_the_item_digest_ignores_updated_at_and_census_fetch_time(tmp_path: Path) -> None:
    root, document = scenario(tmp_path)
    action, plan = emit(root, document)
    assert action["itemSha256"] == itemDigest(plan)
    bumped = copy.deepcopy(plan)
    bumped["expectedSnapshot"] = {**bumped["expectedSnapshot"], "updatedAt": "2026-10-22T00:00:00Z"}
    assert itemDigest(bumped) == itemDigest(plan)
    retitled = copy.deepcopy(plan)
    retitled["expectedSnapshot"] = {**retitled["expectedSnapshot"], "titleSha256": "f" * 64}
    assert itemDigest(retitled) != itemDigest(plan)


def test_the_gate_needs_an_item_digest_and_refuses_an_action_without_one(tmp_path: Path) -> None:
    root, document = scenario(tmp_path)
    action, _ = emit(root, document)
    del action["itemSha256"]
    try:
        gateClosure(root, action, root / RECEIPT, "R1", NOW, REPO)
    except ActionRefused as exc:
        assert exc.code == "item-changed"
    else:
        raise AssertionError("an action without its item digest must be refused")
