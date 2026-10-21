"""Adversarial lane E, scenarios 3, 4, 5, 9, 11 and 14: the Class A proof under pressure.

Built on the reconciler helpers of test_b_reconcile. Each rule gets a positive control and a
table of missing-proof negatives. Authority may only be downgraded (A -> B -> C -> none), never
raised by added doubt. Three defects found while writing these are strict xfails with repro.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.closure import planClosures
from gaia_cli.steward.issuehygiene.hygienepolicy import KNOWN_RULE_IDS
from tests.steward.issuehygiene.test_b_reconcile import (
    BLOB,
    FETCHED,
    censusOf,
    childRow,
    item,
    mkRow,
    policyFor,
    run,
    skill,
    umbrellaRow,
    writeNamed,
)

BLOB_OTHER = "https://github.com/obra/superpowers/blob/main/skills/other-skill/SKILL.md"
BLOB_THIRD = "https://github.com/obra/superpowers/blob/main/skills/third/SKILL.md"
GOOD_RECORD = skill("obra/writing-skills", BLOB)
SUITE_V7 = skill(
    "obra/superpowers", "https://github.com/obra/superpowers/blob/main/SKILL.md",
    extra="upstream:\n  repo: obra/superpowers\n  version: v7.0.0\n",
)
SUITE_V6 = SUITE_V7.replace("v7.0.0", "v6.0.0")
RANK = {"A": 3, "B": 2, "C": 1, "none": 0}


def authorityOf(manifest: dict, number: int) -> str:
    return item(manifest, number)["authority"]


def plannedIssues(manifest: dict, policy=None) -> dict[int, str]:
    return {plan["issue"]: plan["ruleId"] for plan in planClosures(manifest, policy or policyFor())}


def closedCopy(row: dict) -> dict:
    return {**row, "state": "closed", "stateReason": "completed", "closedAt": FETCHED}


# ------------------------------------------------------------------ rule A1 (scenario 9)


def a1Census() -> object:
    return censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB)])


def test_a1_positive_control_is_authority_a(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/writing-skills", GOOD_RECORD)
    manifest = run(a1Census(), tmp_path)
    assert authorityOf(manifest, 10) == "A"
    assert item(manifest, 10)["ruleId"] == "A1-child-curated"


A1_NEGATIVES = {
    "no-registry-record": (None, BLOB),
    "draft-status": (skill("obra/writing-skills", BLOB, status="draft"), BLOB),
    "status-missing": ("---\nid: obra/writing-skills\ncontributor: obra\nlinks:\n  github: " + BLOB + "\n---\n", BLOB),
    "registry-repo-differs": (skill("obra/writing-skills", BLOB.replace("obra/superpowers", "fork/superpowers")), BLOB),
    "registry-path-differs": (skill("obra/writing-skills", BLOB.replace("writing-skills", "docs")), BLOB),
    "intake-path-differs": (GOOD_RECORD, BLOB_OTHER.replace("other-skill", "writing-skills").replace("skills/", "docs/")),
    "evidence-not-a-github-file": (GOOD_RECORD, "https://example.com/skills/writing-skills"),
    "evidence-url-unknown": (GOOD_RECORD, "_unknown"),
    "registry-link-missing": (skill("obra/writing-skills", ""), BLOB),
    "registry-ref-not-simple": (
        skill("obra/writing-skills", BLOB.replace("/blob/main/", "/blob/release-2/")), BLOB,
    ),
    "unreadable-record": ("---\nid: obra/writing-skills\n: : bad yaml [\n---\n", BLOB),
}


@pytest.mark.parametrize("case", sorted(A1_NEGATIVES))
def test_a1_every_missing_proof_is_never_authority_a(tmp_path: Path, case: str) -> None:
    registryText, url = A1_NEGATIVES[case]
    if registryText is not None:
        writeNamed(tmp_path, "obra/writing-skills", registryText)
    rows = [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", url)]
    manifest = run(censusOf(rows), tmp_path)
    assert authorityOf(manifest, 10) != "A"
    assert item(manifest, 10)["ruleId"] is None


def test_a1_orphan_child_whose_umbrella_is_absent_is_never_a(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/writing-skills", GOOD_RECORD)
    manifest = run(censusOf([childRow(10, "obra/writing-skills", BLOB, parent=99)]), tmp_path)
    assert authorityOf(manifest, 10) != "A"


def test_a1_disabled_rule_downgrades_to_b_and_plans_nothing(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/writing-skills", GOOD_RECORD)
    policy = policyFor(enabledRules=[rule for rule in KNOWN_RULE_IDS if rule != "A1-child-curated"])
    manifest = run(a1Census(), tmp_path, policy=policy)
    assert authorityOf(manifest, 10) == "B"
    assert 10 not in plannedIssues(manifest, policy)


# ------------------------------------------------------------------ rule A2 (scenario 4: merged vs open)


def a2Census(version: str = "v7.0.0", extra=(), closed=()) -> object:
    return censusOf([umbrellaRow(20, "obra/superpowers", version), *extra], closed=closed)


def test_a2_positive_control_registry_at_the_payload_version(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V7)
    assert authorityOf(run(a2Census(), tmp_path), 20) == "A"


def test_a2_open_sync_pull_request_is_not_evidence_of_a_merged_sync(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V6)
    openSync = mkRow(40, "[upstream sync] obra/superpowers v7.0.0", "", isPullRequest=True, mergedAt=None, state="open")
    manifest = run(a2Census(extra=[openSync]), tmp_path)
    assert authorityOf(manifest, 20) != "A"
    assert item(manifest, 20)["ruleId"] is None


def test_a2_merged_sync_pull_request_for_the_version_proves_when_registry_lags(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V6)
    merged = mkRow(40, "[upstream sync] obra/superpowers v7.0.0", "", isPullRequest=True,
                   mergedAt="2026-10-21T12:00:00Z", state="closed")
    assert authorityOf(run(a2Census(closed=[merged]), tmp_path), 20) == "A"


def test_a2_merged_sync_for_another_version_does_not_prove(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V6)
    merged = mkRow(40, "[upstream sync] obra/superpowers v6.0.0", "", isPullRequest=True,
                   mergedAt="2026-10-21T12:00:00Z", state="closed")
    assert authorityOf(run(a2Census(closed=[merged]), tmp_path), 20) != "A"


def test_a2_merged_sync_for_another_suite_does_not_prove(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V6)
    merged = mkRow(41, "[upstream sync] other/suite v7.0.0", "", isPullRequest=True,
                   mergedAt="2026-10-21T12:00:00Z", state="closed")
    assert authorityOf(run(a2Census(closed=[merged]), tmp_path), 20) != "A"


def test_a2_frozen_suite_record_is_never_a(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V7.replace("upstream:", "installable: false\nupstream:"))
    assert authorityOf(run(a2Census(), tmp_path), 20) != "A"


def test_a2_missing_suite_record_is_never_a(tmp_path: Path) -> None:
    assert authorityOf(run(a2Census(), tmp_path), 20) != "A"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "DEFECT (A2 proof gap): child #30 is listed in newer umbrella #21's body but its Umbrella is #20. "
        "buildGraph records a child-ref-parent-mismatch conflict and drops it, so #21 has zero dependencies "
        "and is A2-closed as completed while #30 is still open. A parent conflict must make the item unknown (B)."
    ),
)
def test_a2_umbrella_listing_an_open_child_owned_elsewhere_is_not_a(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V7)
    older = umbrellaRow(20, "obra/superpowers", "v6.0.0")
    newer = umbrellaRow(21, "obra/superpowers", "v7.0.0", extraBody="Child intakes:\n- [ ] #30 writing-skills\n")
    child = childRow(30, "obra/writing-skills", BLOB, parent=20)
    manifest = run(censusOf([older, newer, child]), tmp_path)
    assert authorityOf(manifest, 21) != "A"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "DEFECT (A2 proof gap): umbrella #20 lists child #10 in its Child intakes, but the census holds no row "
        "for #10 (absent from open and recentlyClosed). It is A2-closed as completed with dependencies []. "
        "Openness of #10 is unknown, so zero open children is not proven and the umbrella must be B."
    ),
)
def test_a2_umbrella_listing_a_child_the_census_does_not_hold_is_not_a(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V7)
    listed = umbrellaRow(20, "obra/superpowers", "v7.0.0", extraBody="Child intakes:\n- [ ] #10 writing-skills\n")
    assert authorityOf(run(censusOf([listed]), tmp_path), 20) != "A"


# ------------------------------------------------------------------ rule A3 (superseded umbrellas)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "DEFECT (A3 superseder): older umbrella #20 is A3-closed as superseded by #21, while #21 is A2-closed "
        "as completed in the same pass (its registry is at v7 and it has no dependencies). The superseder is "
        "not open afterwards, so #20's unresolved child #30 loses its parent. Contract 3.4 A3 requires an OPEN "
        "superseder; a superseder planned for closure in the same pass must not justify the older closure."
    ),
)
def test_a3_superseder_is_not_closed_in_the_same_pass_as_the_umbrella_it_supersedes(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V7)
    older = umbrellaRow(20, "obra/superpowers", "v6.0.0", adds=["writing-skills"])
    newer = umbrellaRow(21, "obra/superpowers", "v7.0.0", adds=["writing-skills"],
                        extraBody="Child intakes:\n- [ ] #30 writing-skills\n")
    child = childRow(30, "obra/writing-skills", BLOB, parent=20)
    planned = plannedIssues(run(censusOf([older, newer, child]), tmp_path))
    assert not (20 in planned and 21 in planned)


def test_a3_positive_superseded_umbrella_closes_while_the_open_superseder_stays_open(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V6)  # registry lags: the newer umbrella is not synced yet
    older = umbrellaRow(20, "obra/superpowers", "v6.0.0", adds=["writing-skills"])
    newer = umbrellaRow(21, "obra/superpowers", "v7.0.0", adds=["writing-skills"],
                        extraBody="Child intakes:\n- [ ] #30 writing-skills\n")
    child = childRow(30, "obra/writing-skills", BLOB, parent=20)
    manifest = run(censusOf([older, newer, child]), tmp_path)
    assert plannedIssues(manifest) == {20: "A3-umbrella-superseded"}
    assert item(manifest, 20)["canonical"] == 21
    assert authorityOf(manifest, 21) != "A"


@pytest.mark.parametrize("breakage", ["component-add-not-carried", "child-not-listed", "superseder-same-version"])
def test_a3_every_missing_proof_is_never_authority_a(tmp_path: Path, breakage: str) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V6)
    sameVersion = breakage == "superseder-same-version"
    olderVersion = "v6.0.0" if sameVersion else "v5.0.0"
    newerVersion = "v6.0.0" if sameVersion else "v7.0.0"
    newerAdds = [] if breakage == "component-add-not-carried" else ["writing-skills"]
    newerBody = "" if breakage == "child-not-listed" else "Child intakes:\n- [ ] #30 writing-skills\n"
    older = umbrellaRow(20, "obra/superpowers", olderVersion, adds=["writing-skills"])
    newer = umbrellaRow(21, "obra/superpowers", newerVersion, adds=newerAdds, extraBody=newerBody)
    child = childRow(30, "obra/writing-skills", BLOB, parent=20)
    manifest = run(censusOf([older, newer, child]), tmp_path)
    assert item(manifest, 20)["ruleId"] != "A3-umbrella-superseded"


# ------------------------------------------------------------------ rule A4 (scenario 3: same component, several releases)


def test_same_component_in_two_releases_closes_only_the_later_duplicate(tmp_path: Path) -> None:
    older = umbrellaRow(20, "obra/superpowers", "v6.0.0", adds=["writing-skills"])
    newer = umbrellaRow(21, "obra/superpowers", "v7.0.0", adds=["writing-skills"])
    first = childRow(30, "obra/writing-skills", BLOB, parent=20)
    second = childRow(31, "obra/writing-skills", BLOB, parent=21)
    manifest = run(censusOf([older, newer, first, second]), tmp_path)
    assert item(manifest, 31)["ruleId"] == "A4-duplicate-child"
    assert item(manifest, 31)["proposedTransition"]["duplicateOf"] == 30
    assert authorityOf(manifest, 30) != "A"
    assert plannedIssues(manifest) == {31: "A4-duplicate-child"}


def test_same_component_with_different_evidence_refs_is_never_a_duplicate(tmp_path: Path) -> None:
    older = umbrellaRow(20, "obra/superpowers", "v6.0.0", adds=["writing-skills"])
    newer = umbrellaRow(21, "obra/superpowers", "v7.0.0", adds=["writing-skills"])
    first = childRow(30, "obra/writing-skills", BLOB, parent=20)
    second = childRow(31, "obra/writing-skills", BLOB.replace("/main/", "/v7.0.0/"), parent=21)
    manifest = run(censusOf([older, newer, first, second]), tmp_path)
    assert item(manifest, 31)["ruleId"] != "A4-duplicate-child"
    assert plannedIssues(manifest) == {}


def test_same_component_curated_in_the_registry_is_closed_as_a1_by_each_child_not_as_a_duplicate(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/writing-skills", GOOD_RECORD)
    older = umbrellaRow(20, "obra/superpowers", "v6.0.0", adds=["writing-skills"])
    newer = umbrellaRow(21, "obra/superpowers", "v7.0.0", adds=["writing-skills"])
    first = childRow(30, "obra/writing-skills", BLOB, parent=20)
    second = childRow(31, "obra/writing-skills", BLOB, parent=21)
    manifest = run(censusOf([older, newer, first, second]), tmp_path)
    # The older umbrella is A3-superseded because its only child is resolved and #21 stays open.
    assert plannedIssues(manifest) == {20: "A3-umbrella-superseded", 30: "A1-child-curated", 31: "A1-child-curated"}
    assert item(manifest, 21)["authority"] != "A"


def test_an_orphaned_duplicate_is_never_closed_as_a_duplicate(tmp_path: Path) -> None:
    """Same key and same evidence as #30, but its umbrella #99 is absent: an orphan is never A."""

    older = umbrellaRow(20, "obra/superpowers", "v6.0.0", adds=["writing-skills"])
    first = childRow(30, "obra/writing-skills", BLOB, parent=20)
    orphan = childRow(31, "obra/writing-skills", BLOB, parent=99)
    manifest = run(censusOf([older, first, orphan]), tmp_path)
    assert item(manifest, 31)["ruleId"] != "A4-duplicate-child"
    assert authorityOf(manifest, 31) != "A"
    assert 31 not in plannedIssues(manifest)


# ------------------------------------------------------------------ partially approved batches (scenario 5)


def batchRows(third: bool) -> list[dict]:
    rows = [
        umbrellaRow(20, "obra/superpowers", "v7.0.0", adds=["writing-skills", "other-skill", "third"]),
        childRow(30, "obra/writing-skills", BLOB, parent=20),
        childRow(31, "obra/other-skill", BLOB_OTHER, parent=20),
    ]
    if third:
        rows.append(childRow(32, "obra/third", BLOB_THIRD, parent=20))
    return rows


def curateBatchRegistry(tmp_path: Path, third: bool) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V7)
    writeNamed(tmp_path, "obra/writing-skills", GOOD_RECORD)
    writeNamed(tmp_path, "obra/other-skill", skill("obra/other-skill", BLOB_OTHER))
    if third:
        writeNamed(tmp_path, "obra/third", skill("obra/third", BLOB_THIRD))


def test_partially_approved_batch_closes_only_the_approved_children_and_holds_the_umbrella(tmp_path: Path) -> None:
    curateBatchRegistry(tmp_path, third=False)
    manifest = run(censusOf(batchRows(third=True)), tmp_path)
    assert plannedIssues(manifest) == {30: "A1-child-curated", 31: "A1-child-curated"}
    assert authorityOf(manifest, 20) != "A"
    (batch,) = manifest["batches"]
    # The batch key takes the owner from the evidence URL (obra/superpowers), not from the contributor handle.
    assert batch["classB"] == ["upstream-candidate:obra/superpowers:third"]
    assert batch["size"] == 1


def test_once_every_batch_child_is_closed_the_umbrella_converges_to_a2_in_the_next_pass(tmp_path: Path) -> None:
    curateBatchRegistry(tmp_path, third=True)
    first = run(censusOf(batchRows(third=True)), tmp_path)
    assert plannedIssues(first) == {30: "A1-child-curated", 31: "A1-child-curated", 32: "A1-child-curated"}
    assert authorityOf(first, 20) != "A"  # open children still listed: the umbrella waits for them
    umbrella = umbrellaRow(20, "obra/superpowers", "v7.0.0", adds=["writing-skills", "other-skill", "third"])
    closedChildren = [closedCopy(row) for row in batchRows(third=True)[1:]]
    second = run(censusOf([umbrella], closed=closedChildren), tmp_path)
    assert plannedIssues(second) == {20: "A2-umbrella-synced"}


def test_an_approval_label_alone_never_proves_or_closes_a_child(tmp_path: Path) -> None:
    approved = childRow(10, "obra/writing-skills", BLOB, labels=("upstream:child", "upstream:approved"))
    manifest = run(censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0"), approved]), tmp_path)
    assert authorityOf(manifest, 10) != "A"


# ------------------------------------------------------------------ class C compression and no authority (scenario 11)


def test_many_alias_children_under_one_handle_pair_compress_to_one_founder_question(tmp_path: Path) -> None:
    rows = []
    for index in range(20):
        slug = f"skill-{index:02d}"
        url = f"https://github.com/garrytan/gbrain/blob/main/skills/{slug}/SKILL.md"
        writeNamed(tmp_path, f"garrytan/{slug}", skill(f"garrytan/{slug}", url))
        rows.append(childRow(100 + index, f"garry-tan/{slug}", url, parent=20))
    manifest = run(censusOf([umbrellaRow(20, "garrytan/gbrain", "v1.0.0"), *rows]), tmp_path)
    questions = manifest["founderQuestions"]
    assert len(questions) == 1
    assert questions[0]["affected"] == [100 + index for index in range(20)]
    assert all(entry["authority"] == "C" for entry in manifest["items"] if entry["kind"] == "child")
    assert plannedIssues(manifest) == {}


# ------------------------------------------------------------------ downgrade-only authority (scenario 14)


@pytest.mark.parametrize("perturbation", [
    "registry-record-removed",
    "registry-record-drafted",
    "rule-disabled",
    "registry-unreadable",
])
def test_added_doubt_only_downgrades_a_child(tmp_path: Path, perturbation: str) -> None:
    writeNamed(tmp_path, "obra/writing-skills", GOOD_RECORD)
    base = authorityOf(run(a1Census(), tmp_path), 10)
    assert base == "A"
    policy = policyFor()
    if perturbation == "registry-record-removed":
        (tmp_path / "registry/named/obra/writing-skills.md").unlink()
    elif perturbation == "registry-record-drafted":
        writeNamed(tmp_path, "obra/writing-skills", skill("obra/writing-skills", BLOB, status="draft"))
    elif perturbation == "rule-disabled":
        policy = policyFor(enabledRules=[rule for rule in KNOWN_RULE_IDS if rule != "A1-child-curated"])
    else:
        writeNamed(tmp_path, "obra/writing-skills", "---\nid: obra/writing-skills\n: : bad [\n---\n")
    after = authorityOf(run(a1Census(), tmp_path, policy=policy), 10)
    assert RANK[after] < RANK[base]


def test_adding_an_open_child_to_a_proven_umbrella_only_downgrades_it(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/superpowers", SUITE_V7)
    base = run(censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0")]), tmp_path)
    assert authorityOf(base, 20) == "A"
    grown = run(censusOf([
        umbrellaRow(20, "obra/superpowers", "v7.0.0"),
        childRow(33, "obra/unresolved", "https://github.com/obra/superpowers/blob/main/skills/unresolved/SKILL.md", parent=20),
    ]), tmp_path)
    assert RANK[authorityOf(grown, 20)] < RANK[authorityOf(base, 20)]


def test_unrelated_rows_never_raise_an_unproven_child_to_a(tmp_path: Path) -> None:
    rows = [childRow(10, "obra/writing-skills", BLOB)]
    assert authorityOf(run(censusOf(rows), tmp_path), 10) == "B"
    noisy = rows + [mkRow(500, "Human discussion", "no intake here", labels=())]
    assert authorityOf(run(censusOf(noisy), tmp_path), 10) != "A"
