"""D1: issueHygiene policy caps, rule registry and POLICY.yaml wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.hygienepolicy import (
    KNOWN_RULE_IDS,
    MAX_CLOSURES_HARD_CAP,
    HygienePolicyError,
    loadHygienePolicy,
)
from gaia_cli.steward.models import AuthorityClass
from gaia_cli.steward.policy import PolicyError, StewardPolicy

REPO_ROOT = Path(__file__).resolve().parents[3]


def validSection(**overrides):
    section = {
        "maxClosuresPerRun": 10,
        "maxCensusAgeSeconds": 21600,
        "closedWindowDays": 30,
        "enabledRules": list(KNOWN_RULE_IDS),
        "a5Disabled": [],
        "writesEnabled": True,
    }
    section.update(overrides)
    return section


def test_absent_section_grants_no_closure_authority() -> None:
    policy = loadHygienePolicy(None)
    assert policy.writesEnabled is False
    assert policy.enabledRules == ()


def test_valid_section_loads_with_defaults_and_rules_in_registry_order() -> None:
    policy = loadHygienePolicy(validSection(enabledRules=["A4-duplicate-child", "A1-child-curated"]))
    assert policy.maxClosuresPerRun == 10
    assert policy.enabledRules == ("A1-child-curated", "A4-duplicate-child")
    assert policy.ruleEnabled("A2-umbrella-synced") is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"maxClosuresPerRun": MAX_CLOSURES_HARD_CAP + 1},
        {"maxClosuresPerRun": -1},
        {"maxCensusAgeSeconds": 10},
        {"maxCensusAgeSeconds": 10**9},
        {"closedWindowDays": 0},
        {"closedWindowDays": 365},
        {"enabledRules": ["A6-invented"]},
        {"enabledRules": ["A1-child-curated", "A1-child-curated"]},
        {"a5Disabled": ["../escape.yml"]},
        {"a5Disabled": [".github/workflows/sub/nested.yml"]},
        {"writesEnabled": "yes"},
        {"maxClosuresPerRun": True},
    ],
)
def test_policy_cannot_exceed_caps_or_invent_rules(overrides) -> None:
    with pytest.raises(HygienePolicyError):
        loadHygienePolicy(validSection(**overrides))


def test_missing_or_unknown_keys_fail_loudly() -> None:
    section = validSection()
    section.pop("closedWindowDays")
    with pytest.raises(HygienePolicyError):
        loadHygienePolicy(section)
    with pytest.raises(HygienePolicyError):
        loadHygienePolicy(validSection(closure={"rules": []}))


def test_repository_policy_wires_issue_debt_authority_and_routes() -> None:
    policy = StewardPolicy.load(REPO_ROOT)
    assert policy.authority_for("issue_closure_ready") is AuthorityClass.A
    assert policy.authority_for("issue_suite_review") is AuthorityClass.B
    assert policy.authority_for("issue_founder_decision") is AuthorityClass.C
    assert policy.dispatch_rule_for("issue_suite_review").routine == "issue-hygiene"
    assert policy.founder_rule_for("issue_founder_decision") is not None
    # B5: the shipped policy is dry-run (contract section 6). The pilot runs through explicit flags, not this policy.
    assert policy.issue_hygiene.writesEnabled is False
    assert policy.issue_hygiene.maxClosuresPerRun == 10
    assert policy.issue_hygiene.enabledRules == ()  # pending Class C authority, not a decided allowlist


def test_founder_rule_must_name_its_own_debt_kind(tmp_path) -> None:
    text = (REPO_ROOT / "founder/steward/POLICY.yaml").read_text(encoding="utf-8")
    broken = text.replace("debtKind: issue_founder_decision", "debtKind: generic_mapping", 1)
    (tmp_path / "founder/steward").mkdir(parents=True)
    (tmp_path / "founder/steward/POLICY.yaml").write_text(broken, encoding="utf-8")
    with pytest.raises(PolicyError):
        StewardPolicy.load(tmp_path)
