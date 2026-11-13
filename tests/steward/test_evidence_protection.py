"""The production trust-boundary checker: protected means a verified, active, bypass-free ruleset, never an assumption."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_steward_evidence_protection", ROOT / "scripts/check_steward_evidence_protection.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

GOOD = {
    "name": "steward-evidence-append-only", "target": "branch", "enforcement": "active", "bypass_actors": [],
    "conditions": {"ref_name": {"include": [
        "refs/heads/steward/evidence", "refs/heads/steward/evidence-*", "refs/heads/steward/ledger"], "exclude": []}},
    "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
}
MAIN_ONLY = {**GOOD, "name": "Main Ruleset", "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}}}


def variant(**changes):
    return {**GOOD, **changes}


def test_the_documented_ruleset_protects_every_required_ref() -> None:
    report = checker.evaluate([GOOD])
    assert report["protected"] is True
    assert all(item["covered"] for item in report["refs"].values())


def test_the_existing_main_only_ruleset_protects_nothing_here() -> None:
    report = checker.evaluate([MAIN_ONLY])
    assert report["protected"] is False
    assert report["refs"]["refs/heads/steward/evidence"]["covered"] is False


def test_no_rulesets_means_unprotected() -> None:
    report = checker.evaluate([])
    assert report["protected"] is False
    assert report["refs"]["refs/heads/steward/evidence"]["problems"] == ["no ruleset exists"]


@pytest.mark.parametrize("changes,expected", [
    ({"enforcement": "evaluate"}, "not 'active'"),
    ({"enforcement": "disabled"}, "not 'active'"),
    ({"rules": [{"type": "deletion"}]}, "non_fast_forward"),
    ({"rules": [{"type": "non_fast_forward"}]}, "deletion"),
    ({"bypass_actors": [{"actor_id": 1, "actor_type": "RepositoryRole", "bypass_mode": "always"}]}, "bypass actor"),
    ({"target": "tag"}, "not a branch ruleset"),
    ({"conditions": {"ref_name": {"include": ["refs/heads/steward/*"], "exclude": ["refs/heads/steward/evidence"]}}}, "not included"),
])
def test_a_weakened_ruleset_is_not_protection(changes, expected) -> None:
    report = checker.evaluate([variant(**changes)])
    assert report["protected"] is False
    problems = " ".join(report["refs"]["refs/heads/steward/evidence"]["problems"])
    assert expected in problems


def test_one_good_ruleset_among_weak_ones_is_enough() -> None:
    assert checker.evaluate([MAIN_ONLY, variant(enforcement="disabled"), GOOD])["protected"] is True


def test_a_ruleset_that_misses_the_ledger_is_reported_per_ref() -> None:
    partial = variant(conditions={"ref_name": {"include": ["refs/heads/steward/evidence", "refs/heads/steward/evidence-*"], "exclude": []}})
    report = checker.evaluate([partial])
    assert report["refs"]["refs/heads/steward/evidence"]["covered"] is True
    assert report["refs"]["refs/heads/steward/ledger"]["covered"] is False
    assert report["protected"] is False


def test_cli_exit_codes_and_unreadable_input_is_never_protected(tmp_path: Path, capsys) -> None:
    good = tmp_path / "good.json"
    good.write_text(json.dumps([GOOD]))
    assert checker.main(["--rulesets-file", str(good)]) == 0
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([MAIN_ONLY]))
    assert checker.main(["--rulesets-file", str(bad)]) == 1
    assert "NOT protected" in capsys.readouterr().out
    assert checker.main(["--rulesets-file", str(tmp_path / "missing.json")]) == 2
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    assert checker.main(["--rulesets-file", str(broken)]) == 2
    notList = tmp_path / "obj.json"
    notList.write_text("{}")
    assert checker.main(["--rulesets-file", str(notList)]) == 2
    assert "UNVERIFIED" in capsys.readouterr().err
