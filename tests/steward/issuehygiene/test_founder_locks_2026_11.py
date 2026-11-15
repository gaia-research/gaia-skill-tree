"""Regression tests for the 2026-11-15 C2 (Addy) and C3 (GBrain) limited-release amendment."""
from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.desk import _check_record
from gaia_cli.steward.issuehygiene.questions import (
    AMENDED_RESOLUTIONS,
    BASELINE_CHILDREN,
    BINDINGS,
    decidedBindings,
    loadIssueDecisions,
)
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from tests.steward.issuehygiene.test_b_reconcile import (
    NOW,
    botRow,
    censusOf,
    childRow,
    item,
    policyFor,
    skill,
    umbrellaRow,
    writeNamed,
)

ROOT = Path(__file__).resolve().parents[3]


def _gbrain_url(slug: str) -> str:
    return f"https://github.com/garrytan/gbrain/blob/main/skills/{slug}/SKILL.md"


def _addy_url(slug: str) -> str:
    return f"https://github.com/addy-osmani/agent-skills/blob/main/skills/{slug}/SKILL.md"


def _run(root: Path, source: list[dict], records=None) -> dict:
    (root / "registry/named").mkdir(parents=True, exist_ok=True)
    return reconcile(
        censusOf(source),
        buildRegistryIndex(root),
        policyFor(),
        NOW,
        decisionRecords=loadIssueDecisions(ROOT) if records is None else records,
    )


def test_baseline_enumerations_match_plan_counts_and_records_preserve_history():
    plan_text = (ROOT / "founder/reports/upstream-backlog-2026-11/PLAN.md").read_text()
    rows = re.findall(r"\| #(\d+) \| `([^`]+)` \| (yes|no) \|", plan_text)
    plan_gbrain = {int(n): c for n, c, _ in rows if c.startswith("garrytan/")}
    plan_addy = {int(n): c for n, c, _ in rows if c.startswith("addy-osmani/")}
    assert len(plan_gbrain) == 67
    assert len(plan_addy) == 4
    assert BASELINE_CHILDREN["q-bfd37238"] == plan_gbrain
    assert BASELINE_CHILDREN["q-2568173e"] == plan_addy

    records = {r["id"]: r for r in loadIssueDecisions(ROOT)}
    assert all(_check_record(r) is None for r in records.values())
    c3 = records["issue-question-q-bfd37238"]
    c2 = records["issue-question-q-2568173e"]
    assert c3["resolution"] == "records-and-version-sync-only"
    assert c2["resolution"] == "records-and-version-sync-migration-deferred"
    assert any("Previous resolution (2026-11-04): curation-deferred" in ev for ev in c3["evidence"])
    assert any("Previous resolution (2026-11-04): migration-deferred" in ev for ev in c2["evidence"])
    assert any("New candidates and the breadth audit (#2276) remain held." in ev for ev in c3["evidence"])
    assert any("Close the four children with proof, sync the version under the existing identifiers." in ev for ev in c2["evidence"])


def test_scoped_baseline_children_release_only_with_exact_a1_proof(tmp_path):
    writeNamed(tmp_path, "garrytan/article-enrichment", skill("garrytan/article-enrichment", github=_gbrain_url("article-enrichment")))
    writeNamed(tmp_path, "garrytan/skillify", skill("garrytan/skillify", github="https://github.com/garrytan/gstack/blob/main/skillify/SKILL.md"))
    writeNamed(tmp_path, "addy-osmani/debugging-and-error-recovery", skill("addy-osmani/debugging-and-error-recovery", github=_addy_url("debugging-and-error-recovery")))
    writeNamed(tmp_path, "addy-osmani/interview-me", skill("addy-osmani/interview-me", github=_addy_url("interview-me")))

    source = [
        umbrellaRow(1835, "garrytan/gbrain", "v0.60.725.0", labels=("upstream:release", "upstream:needs-info")),
        umbrellaRow(2002, "addy-osmani/agent-skills", "0.6.16", title="[upstream] addyosmani/agent-skills → 0.6.16"),
        childRow(1925, "garrytan/article-enrichment", _gbrain_url("article-enrichment"), parent=1835),
        childRow(1984, "garrytan/skillify", "https://github.com/garrytan/gstack/blob/main/skillify/SKILL.md", parent=1835),
        childRow(2008, "addy-osmani/debugging-and-error-recovery", _addy_url("debugging-and-error-recovery"), parent=2002),
        childRow(2015, "addy-osmani/interview-me", _addy_url("interview-me"), parent=2002),
    ]
    manifest = _run(tmp_path, source)

    for number in (1925, 1984, 2008, 2015):
        child = item(manifest, number)
        assert (child["state"], child["authority"], child["ruleId"]) == ("resolved", "A", "A1-child-curated")
        assert child["proposedTransition"]["action"] == "close"

    # Umbrellas themselves remain held (version sync still requires fresh human approval).
    for umbrella_num in (1835, 2002):
        umb = item(manifest, umbrella_num)
        assert (umb["state"], umb["authority"]) == ("held", "none")
        assert umb["proposedTransition"]["action"] == "keep"


def test_source_mismatch_and_needs_info_on_baseline_children_stay_held(tmp_path):
    writeNamed(
        tmp_path,
        "garrytan/article-enrichment",
        skill("garrytan/article-enrichment", github="https://github.com/garrytan/gbrain/blob/main/skills/other/SKILL.md"),
    )
    writeNamed(
        tmp_path,
        "garrytan/ask-user",
        skill("garrytan/ask-user", github=_gbrain_url("ask-user")),
    )
    writeNamed(
        tmp_path,
        "addy-osmani/idea-refine",
        skill("addy-osmani/idea-refine", github="https://github.com/addy-osmani/agent-skills/blob/main/skills/different/SKILL.md"),
    )
    source = [
        umbrellaRow(1835, "garrytan/gbrain", "v0.60.725.0", labels=("upstream:release", "upstream:needs-info")),
        umbrellaRow(2002, "addy-osmani/agent-skills", "0.6.16"),
        childRow(1925, "garrytan/article-enrichment", _gbrain_url("article-enrichment"), parent=1835),
        childRow(1926, "garrytan/ask-user", _gbrain_url("ask-user"), parent=1835, labels=("upstream:child", "upstream:needs-info")),
        childRow(2014, "addy-osmani/idea-refine", _addy_url("idea-refine"), parent=2002),
    ]
    manifest = _run(tmp_path, source)

    for number in (1925, 1926, 2014):
        child = item(manifest, number)
        assert (child["state"], child["authority"]) == ("held", "none")
        assert child["proposedTransition"]["action"] == "keep"


def test_new_absent_unknown_breadth_audit_and_skip_child_gate_remain_held(tmp_path):
    # Even if a new GBrain candidate happens to have a matching registry file, it is not in the 67 baseline.
    writeNamed(tmp_path, "garrytan/brand-new", skill("garrytan/brand-new", github=_gbrain_url("brand-new")))
    source = [
        umbrellaRow(1835, "garrytan/gbrain", "v0.60.725.0", labels=("upstream:release", "upstream:approved", "skip-child-gate")),
        childRow(2500, "garrytan/brand-new", _gbrain_url("brand-new"), parent=1835),
        childRow(2501, "garrytan/absent-skill", _gbrain_url("absent-skill"), parent=1835),
        childRow(2276, "garrytan/breadth-audit", _gbrain_url("breadth-audit"), parent=1835),
        childRow(2502, "garrytan/bad-url", "not-a-github-url", parent=1835),
    ]
    manifest = _run(tmp_path, source)

    assert (item(manifest, 1835)["state"], item(manifest, 1835)["authority"]) == ("held", "none")
    assert not any(1835 in q["affected"] for q in manifest["founderQuestions"])
    for number in (2500, 2501, 2276, 2502):
        entry = item(manifest, number)
        assert (entry["state"], entry["authority"]) == ("held", "none")
        assert entry["proposedTransition"]["action"] == "keep"


def test_addy_handle_migration_and_unrelated_questions_remain_held_or_class_c(tmp_path):
    # Registry migrated to addyosmani/* while intake is addy-osmani/* -> alias-suspect Class C, not A1.
    writeNamed(tmp_path, "addyosmani/debugging-and-error-recovery", skill("addyosmani/debugging-and-error-recovery", github=_addy_url("debugging-and-error-recovery")))
    writeNamed(tmp_path, "addyosmani/new-skill", skill("addyosmani/new-skill", github="https://github.com/addyosmani/agent-skills/blob/main/skills/new-skill/SKILL.md"))
    source = [
        umbrellaRow(2002, "addy-osmani/agent-skills", "0.6.16", title="[upstream] addyosmani/agent-skills → 0.6.16"),
        childRow(2008, "addy-osmani/debugging-and-error-recovery", _addy_url("debugging-and-error-recovery"), parent=2002),
        childRow(2510, "addyosmani/new-skill", "https://github.com/addyosmani/agent-skills/blob/main/skills/new-skill/SKILL.md", parent=2002),
        umbrellaRow(9999, "other/new-identity", "v1", title="[upstream] other/canonical → v1"),
    ]
    manifest = _run(tmp_path, source)

    # Alias question on #2008 stays Class C (migration not approved).
    assert item(manifest, 2008)["authority"] == "C"
    assert item(manifest, 2008)["proposedTransition"]["action"] == "keep"
    assert any(2008 in q["affected"] for q in manifest["founderQuestions"])
    # Non-baseline addyosmani/* child stays held.
    assert (item(manifest, 2510)["state"], item(manifest, 2510)["authority"]) == ("held", "none")
    # Unrelated question on #9999 stays Class C.
    assert item(manifest, 9999)["authority"] == "C"
    assert any(9999 in q["affected"] for q in manifest["founderQuestions"])


def test_old_full_hold_resolutions_still_retain_full_hold_and_c1_c4_unchanged(tmp_path):
    writeNamed(tmp_path, "garrytan/article-enrichment", skill("garrytan/article-enrichment", github=_gbrain_url("article-enrichment")))
    writeNamed(tmp_path, "addy-osmani/debugging-and-error-recovery", skill("addy-osmani/debugging-and-error-recovery", github=_addy_url("debugging-and-error-recovery")))
    source = [
        umbrellaRow(1833, "ruvnet/agentdb", "v3.63.8", title="[upstream] ruvnet/ruflo → v3.63.8"),
        umbrellaRow(1835, "garrytan/gbrain", "v0.60.725.0"),
        umbrellaRow(2002, "addy-osmani/agent-skills", "0.6.16"),
        childRow(1925, "garrytan/article-enrichment", _gbrain_url("article-enrichment"), parent=1835),
        childRow(2008, "addy-osmani/debugging-and-error-recovery", _addy_url("debugging-and-error-recovery"), parent=2002),
        botRow(2126, "[aw] Detection Runs", "security threats"),
        botRow(2127, "[aw] Steward Build Copilot: billing", ".github/workflows/steward-build-copilot.md"),
    ]
    old_records = copy.deepcopy(list(loadIssueDecisions(ROOT)))
    for rec in old_records:
        if rec["id"] == "issue-question-q-bfd37238":
            rec["resolution"] = "curation-deferred"
        elif rec["id"] == "issue-question-q-2568173e":
            rec["resolution"] = "migration-deferred"

    manifest = _run(tmp_path, source, records=tuple(old_records))
    for number in (1925, 2008, 2126, 2127):
        entry = item(manifest, number)
        assert (entry["state"], entry["authority"]) == ("held", "none")
        assert entry["proposedTransition"]["action"] == "keep"
    assert item(manifest, 1833)["authority"] == "B"


def test_amended_resolution_requires_campaign_authority_link_and_writes_stay_disabled():
    records = copy.deepcopy(list(loadIssueDecisions(ROOT)))
    for rec in records:
        if rec["id"] == "issue-question-q-bfd37238":
            assert rec["resolution"] == AMENDED_RESOLUTIONS["q-bfd37238"]
            rec["links"] = [link for link in rec["links"] if "CAMPAIGN.md" not in link]
    with pytest.raises(ValueError, match="authority missing"):
        decidedBindings(records)

    policy = yaml.safe_load((ROOT / "founder/steward/POLICY.yaml").read_text())
    assert policy["issueHygiene"]["writesEnabled"] is False
    assert set(BINDINGS) == {"q-08ecd62d", "q-2568173e", "q-bfd37238", "q-6720aecf"}
