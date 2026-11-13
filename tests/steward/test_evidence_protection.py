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


NAMESPACE = "refs/heads/steward/evidence-*"
OLD_FUTURE = ("refs/heads/steward/evidence-future-probe", "refs/heads/steward/evidence-rehearsal-9999-v9")
CONCRETE_ONLY = variant(conditions={"ref_name": {"include": list(checker.REQUIRED_REFS), "exclude": []}})
EXACT_SEVEN = variant(conditions={"ref_name": {"include": list(checker.REQUIRED_REFS) + list(OLD_FUTURE), "exclude": []}})


def withIncludes(*include, exclude=()):
    return variant(conditions={"ref_name": {"include": list(include), "exclude": list(exclude)}})


def test_the_documented_ruleset_covers_the_whole_namespace_not_just_samples() -> None:
    assert checker.evaluate([GOOD])["refs"][NAMESPACE]["covered"] is True
    assert checker.coversLanguage(GOOD["conditions"]["ref_name"]["include"], NAMESPACE)


def test_a_ruleset_naming_only_todays_concrete_refs_is_not_protection() -> None:
    """Codex re-review finding 2: it covers every existing branch and none of the future ones."""

    report = checker.evaluate([CONCRETE_ONLY])
    assert report["protected"] is False
    for ref in checker.REQUIRED_REFS:
        assert report["refs"][ref]["covered"] is True, ref
    assert report["refs"][NAMESPACE]["covered"] is False
    assert "do not cover every ref" in " ".join(report["refs"][NAMESPACE]["problems"])


def test_exact_names_plus_the_checkers_own_sample_names_still_fail() -> None:
    """Codex follow-up: seven exact refs (the old checked set) used to pass; sampled names cannot prove a namespace."""

    report = checker.evaluate([EXACT_SEVEN])
    assert report["protected"] is False
    assert report["refs"][NAMESPACE]["covered"] is False
    assert not checker.coversLanguage(EXACT_SEVEN["conditions"]["ref_name"]["include"], NAMESPACE)


def test_a_previously_unseen_name_is_protected_by_the_accepted_pattern() -> None:
    arbitrary = "refs/heads/steward/evidence-arbitrary-new-branch"
    assert checker.globMatch("refs/heads/steward/evidence-*", arbitrary)
    assert checker.evaluate([GOOD], refs=[arbitrary])["refs"][arbitrary]["covered"] is True
    assert checker.evaluate([EXACT_SEVEN], refs=[arbitrary])["refs"][arbitrary]["covered"] is False


@pytest.mark.parametrize("include", [
    ["refs/heads/steward/evidence-rehearsal-*"],
    ["refs/heads/steward/evidence-a*"],
    ["refs/heads/steward/evidence-?*"],          # needs one more character: "evidence-" itself is uncovered
    ["refs/heads/steward/evidence-*-v2"],
    ["refs/heads/steward/evidence"],
    ["refs/heads/main"],
    [],
])
def test_a_pattern_that_misses_part_of_the_namespace_fails(include) -> None:
    assert not checker.coversLanguage(include, NAMESPACE)
    assert checker.evaluate([withIncludes(*include, "refs/heads/steward/evidence", "refs/heads/steward/ledger")])["protected"] is False


@pytest.mark.parametrize("include", [
    ["refs/heads/steward/evidence-*"],
    ["refs/heads/steward/evidence*"],
    ["refs/heads/steward/*"],
    ["refs/heads/steward/**"],
    ["refs/heads/**"],
    ["~ALL"],
])
def test_exact_pattern_or_a_verified_superset_covers_the_namespace(include) -> None:
    assert checker.coversLanguage(include, NAMESPACE)
    assert checker.evaluate([withIncludes(*include, "refs/heads/steward/evidence", "refs/heads/steward/ledger")])["protected"] is True


def test_the_namespace_is_proved_over_the_union_of_includes() -> None:
    assert checker.coversLanguage(["refs/heads/steward/evidence-*", "refs/heads/main"], NAMESPACE)
    # two halves that together would need a character class the checker does not credit
    assert not checker.coversLanguage(["refs/heads/steward/evidence-a*", "refs/heads/steward/evidence-b*"], NAMESPACE)


def test_a_partial_wildcard_does_not_cover_the_whole_evidence_namespace() -> None:
    narrow = withIncludes("refs/heads/steward/evidence", "refs/heads/steward/evidence-rehearsal-*", "refs/heads/steward/ledger")
    report = checker.evaluate([narrow])
    assert report["protected"] is False
    assert report["refs"][NAMESPACE]["covered"] is False


@pytest.mark.parametrize("exclude", [
    ["refs/heads/steward/evidence-probe-*"],
    ["refs/heads/steward/evidence-rehearsal-*"],
    ["refs/heads/steward/*"],
    ["refs/heads/steward/ledger"],
    ["~ALL"],
])
def test_an_exclusion_inside_the_namespace_voids_the_ruleset(exclude) -> None:
    report = checker.evaluate([withIncludes(
        "refs/heads/steward/evidence", "refs/heads/steward/evidence-*", "refs/heads/steward/ledger", exclude=exclude)])
    assert report["protected"] is False


def test_an_unrelated_exclusion_does_not_void_it() -> None:
    assert checker.evaluate([withIncludes(
        "refs/heads/steward/evidence", "refs/heads/steward/evidence-*", "refs/heads/steward/ledger",
        exclude=["refs/heads/dev/*"])])["protected"] is True


def test_single_star_does_not_cross_path_segments() -> None:
    assert checker.globMatch("refs/heads/steward/evidence-*", "refs/heads/steward/evidence-x")
    assert not checker.globMatch("refs/heads/steward/evidence-*", "refs/heads/steward/evidence-x/y")
    assert checker.globMatch("refs/heads/steward/**", "refs/heads/steward/evidence-x/y")


def test_cli_rejects_the_exact_names_ruleset_and_names_the_namespace(tmp_path: Path, capsys) -> None:
    path = tmp_path / "exact.json"
    path.write_text(json.dumps([EXACT_SEVEN]))
    assert checker.main(["--rulesets-file", str(path)]) == 1
    out = capsys.readouterr().out
    assert f"UNPROTECTED {NAMESPACE}" in out
    assert "NOT protected" in out
