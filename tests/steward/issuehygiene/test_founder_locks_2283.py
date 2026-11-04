"""Founder rulings are consumed, not passive desk records or release approvals."""
import copy
from pathlib import Path

import pytest

from gaia_cli.steward.desk import _check_record
from gaia_cli.steward.issuehygiene.questions import BINDINGS, decidedBindings, loadIssueDecisions
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.issuehygiene.sensor import IssueHygieneSensor
from tests.steward.issuehygiene.test_b_reconcile import (
    NOW, botRow, censusOf, childRow, item, policyFor, skill, umbrellaRow, writeNamed,
)

ROOT = Path(__file__).resolve().parents[3]


def rows():
    return [
        umbrellaRow(1833, "ruvnet/agentdb", "v3.63.8", title="[upstream] ruvnet/ruflo → v3.63.8"),
        umbrellaRow(2002, "addy-osmani/agent-skills", "v1", title="[upstream] addyosmani/agent-skills → v1"),
        umbrellaRow(1835, "garrytan/gbrain", "v1", labels=("upstream:release", "upstream:needs-info")),
        childRow(1836, "garrytan/one", "https://github.com/garrytan/gbrain/blob/main/skills/one/SKILL.md", parent=1835),
        childRow(2003, "addy-osmani/one", "https://github.com/addyosmani/agent-skills/blob/main/skills/one/SKILL.md", parent=2002),
        botRow(2126, "[aw] Detection Runs", "security threats"),
        botRow(2127, "[aw] Steward Build Copilot: billing", ".github/workflows/steward-build-copilot.md"),
        umbrellaRow(9999, "other/suite", "v1"),
    ]


def run(root, source=None, records=None):
    (root / "registry/named").mkdir(parents=True, exist_ok=True)
    return reconcile(censusOf(source or rows()), buildRegistryIndex(root), policyFor(), NOW,
                     decisionRecords=loadIssueDecisions(ROOT) if records is None else records)


def test_all_four_records_use_existing_schema_and_exact_mappings():
    records = loadIssueDecisions(ROOT)
    assert len(records) == 4
    assert all(_check_record(record) is None for record in records)
    assert set(decidedBindings(records)) == set(BINDINGS)


def test_locked_questions_disappear_but_implementation_and_children_are_preserved(tmp_path):
    source = rows()
    before = copy.deepcopy(source)
    manifest = run(tmp_path, source)
    assert source == before
    assert manifest["founderQuestions"] == []
    assert item(manifest, 1833)["authority"] == "B"
    for n in (2002, 1835, 1836, 2003, 2126, 2127):
        held = item(manifest, n)
        assert (held["state"], held["authority"]) == ("held", "none")
        assert held["proposedTransition"]["action"] == "keep"
        assert held["original"]["bodySha256"] == next(row["bodySha256"] for row in source if row["number"] == n)
        assert any(ev["type"] == "founder-decision" for ev in held["evidence"])
    assert item(manifest, 9999)["authority"] == "B"
    assert {b["suite"] for b in manifest["batches"]} == {"ruvnet/agentdb", "other/suite"}  # payload identity is preserved, not silently rewritten
    # Real sensor consumption: neither a locked C question nor a held-family B dispatch survives.
    scan = IssueHygieneSensor()._observations(manifest, policyFor(), "2026-10-21T19:30:00Z")
    assert not any(ob.kind == "issue_founder_decision" for ob in scan.observations)
    assert not any("gbrain" in ob.subject.id or "addy" in ob.subject.id for ob in scan.observations)


def test_defer_overrides_proven_child_closure_and_stale_skip_approval(tmp_path):
    source = rows()
    source[2] = umbrellaRow(1835, "garrytan/gbrain", "v1", labels=("upstream:release", "upstream:approved", "skip-child-gate"))
    writeNamed(tmp_path, "garrytan/one", skill("garrytan/one", github="https://github.com/garrytan/gbrain/blob/main/skills/one/SKILL.md"))
    manifest = run(tmp_path, source)
    assert item(manifest, 1836)["authority"] == "none"
    assert item(manifest, 1836)["proposedTransition"]["action"] == "keep"
    assert item(manifest, 1835)["state"] == "held"
    assert not any(1835 in q["affected"] for q in manifest["founderQuestions"])
    # An unrelated cross-contributor alias question is still unresolved, not covered by C2.
    assert any(2003 in q["affected"] for q in manifest["founderQuestions"])


def test_unrelated_question_is_not_silently_answered(tmp_path):
    source = rows()
    source[0] = umbrellaRow(1833, "other/new-identity", "v1", title="[upstream] ruvnet/ruflo → v1")
    manifest = run(tmp_path, source)
    assert item(manifest, 1833)["authority"] == "C"
    assert manifest["founderQuestions"]


@pytest.mark.parametrize("change", ["resolution", "authority", "debt", "schema", "duplicate"])
def test_malformed_or_unbound_lock_cannot_silently_release_hold(change):
    records = copy.deepcopy(list(loadIssueDecisions(ROOT)))
    if change == "resolution":
        records[0]["resolution"] = "approved"
    elif change == "authority":
        records[0]["links"] = []
    elif change == "debt":
        records[0]["evidence"] = []
    elif change == "schema":
        records[0]["inventedFamilyField"] = [1833]
    else:
        records.append(records[0])
    with pytest.raises(ValueError):
        decidedBindings(records)


def test_unreadable_target_file_is_not_treated_as_absent(tmp_path):
    path = tmp_path / "founder/steward/decisions/issue-question-q-bfd37238.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken")
    with pytest.raises(ValueError):
        loadIssueDecisions(tmp_path)


def test_missing_records_do_not_claim_founder_resolution(tmp_path):
    manifest = run(tmp_path, records=())
    assert item(manifest, 1833)["authority"] == "C"
    assert item(manifest, 2002)["authority"] == "C"
    # A needs-info hold is still not an actionable B even without a decision file.
    assert item(manifest, 1835)["state"] == "held"
