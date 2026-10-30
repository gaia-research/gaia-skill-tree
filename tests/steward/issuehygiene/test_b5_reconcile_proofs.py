"""Lane B5 reconciliation blockers: B2, B3, D4, L2, L3, L4, M5, M6 (reconcile side).

Each positive case proves the rule still fires when its hard proof holds. Each negative case is
the exact repro the verifier used, so a regression re-opens the same hole.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.census import Census, validateCensus
from gaia_cli.steward.issuehygiene.reconcile import reconcile, syncTokens, workflowProbesFor
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from tests.steward.issuehygiene.test_b_reconcile import (
    BLOB,
    BOT,
    FETCHED,
    NOW,
    botRow,
    censusOf,
    childRow,
    item,
    mkRow,
    policyFor,
    skill,
    umbrellaRow,
    writeNamed,
)

SUITE = "obra/superpowers"


def suiteRecord(root: Path, version: str, repo: str = SUITE) -> None:
    writeNamed(root, SUITE, skill(SUITE, extra=f"upstream:\n  repo: {repo}\n  version: {version}\n"))


def emptyRegistry(root: Path) -> None:
    """A readable ``registry/named`` directory with no suite or child of interest (a missing one is unknown, L4)."""
    writeNamed(root, "placeholder/none", skill("placeholder/none"))


def syncPr(number: int, title: str) -> dict:
    return mkRow(number, title, "", author=BOT, isPullRequest=True, mergedAt=FETCHED, state="closed")


def v2Umbrella(number: int, version: str, candidates: list[dict], title: str | None = None) -> dict:
    payload = {
        "payloadVersion": 2, "skillId": SUITE, "newVersion": version, "componentAdds": [],
        "componentRemoves": [], "candidates": candidates,
    }
    body = "## Upstream release detected\n\n<!-- gaia-upstream-payload\n" + json.dumps(payload, indent=2) + "\n-->\n"
    return mkRow(number, title or f"[upstream] {SUITE} → {version}", body, labels=("upstream:release",))


def candidate(identifier: str, status: str, child=None) -> dict:
    return {
        "id": identifier, "slug": identifier.rsplit("/", 1)[-1], "evidenceUrl": BLOB,
        "firstSeenVersion": "v1", "lastSeenVersion": "v1",
        "precheck": {"registry": "absent", "tracked": "none", "priorDisposition": "none"},
        "status": status, "child": child,
    }


def run(census: Census, root: Path, policy=None, workflowDisabled=None):
    return reconcile(census, buildRegistryIndex(root), policy or policyFor(), NOW, workflowDisabled)


# ---------------------------------------------------------------- B2: exact sync-PR tokens


@pytest.mark.parametrize(("title", "expected"), [
    ("[upstream sync] obra/superpowers -> v1.2", ("obra/superpowers", "v1.2")),
    ("[upstream sync] obra/superpowers → v1.2", ("obra/superpowers", "v1.2")),
    ("[upstream sync] obra/superpowers v1.2", ("obra/superpowers", "v1.2")),
    ("[upstream sync] obra/superpowers -> v1.2.3", ("obra/superpowers", "v1.2.3")),
    ("Add upstream sync for obra/superpowers", None),
    ("[upstream sync] obra/superpowers-fork -> v1.2", ("obra/superpowers-fork", "v1.2")),
    ("[upstream sync] obra/superpowers -> v1.2 and more", None),
])
def test_sync_title_parses_to_exact_repo_and_version_tokens(title: str, expected) -> None:
    assert syncTokens(title) == expected


@pytest.mark.parametrize("sibling", [
    "[upstream sync] obra/superpowers -> v1.2.3",
    "[upstream sync] obra/superpowers -> v10.0",
    "[upstream sync] obra/superpowers -> v1.20",
    "[upstream sync] obra/superpowers-fork -> v1.2",
    "[upstream sync] obra/superpowers-extra v1.2",
    "[upstream sync] other/obra/superpowers -> v1.2",
])
def test_a_sync_pr_for_a_different_version_or_repo_does_not_prove_a2(tmp_path: Path, sibling: str) -> None:
    suiteRecord(tmp_path, version="v1.0")
    rows = [umbrellaRow(20, SUITE, "v1.2")]
    manifest = run(censusOf(rows, closed=[syncPr(60, sibling)]), tmp_path)

    assert item(manifest, 20)["authority"] != "A"


def test_the_exact_sync_pr_still_proves_a2(tmp_path: Path) -> None:
    suiteRecord(tmp_path, version="v1.0")
    rows = [umbrellaRow(20, SUITE, "v1.2")]
    manifest = run(censusOf(rows, closed=[syncPr(60, "[upstream sync] obra/superpowers -> v1.2")]), tmp_path)

    assert item(manifest, 20)["authority"] == "A"
    assert item(manifest, 20)["ruleId"] == "A2-umbrella-synced"


# ---------------------------------------------------------------- B3: contributor alias duplicates


def test_alias_handle_duplicate_is_never_closed_as_a4(tmp_path: Path) -> None:
    emptyRegistry(tmp_path)
    rows = [
        umbrellaRow(20, "acme/foo", "v1.0"),
        childRow(101, "addyosmani/foo", BLOB.replace("writing-skills", "foo")),
        childRow(102, "addy-osmani/foo", BLOB.replace("writing-skills", "foo")),
    ]
    manifest = run(censusOf(rows), tmp_path)

    alias = item(manifest, 102)
    assert alias["authority"] != "A"
    assert alias["ruleId"] is None
    assert alias["proposedTransition"]["action"] == "keep"


def test_alias_handle_with_a_registry_record_is_class_c_not_a(tmp_path: Path) -> None:
    link = BLOB.replace("writing-skills", "foo")
    writeNamed(tmp_path, "addyosmani/foo", skill("addyosmani/foo", github=link))
    rows = [
        umbrellaRow(20, "acme/foo", "v1.0"),
        childRow(101, "addyosmani/foo", link),
        childRow(102, "addy-osmani/foo", link),
    ]
    manifest = run(censusOf(rows), tmp_path)

    assert item(manifest, 102)["authority"] == "C"
    assert item(manifest, 102)["ruleId"] is None


def test_identical_handle_duplicate_with_same_evidence_still_closes_as_a4(tmp_path: Path) -> None:
    emptyRegistry(tmp_path)
    rows = [
        umbrellaRow(20, "acme/foo", "v1.0"),
        childRow(101, "addyosmani/foo", BLOB.replace("writing-skills", "foo")),
        childRow(102, "addyosmani/foo", BLOB.replace("writing-skills", "foo")),
    ]
    manifest = run(censusOf(rows), tmp_path)

    assert item(manifest, 102)["authority"] == "A"
    assert item(manifest, 102)["ruleId"] == "A4-duplicate-child"


# ---------------------------------------------------------------- D4: v2 candidate rows gate A2


def test_v2_umbrella_with_an_unresolved_new_row_is_not_a2(tmp_path: Path) -> None:
    suiteRecord(tmp_path, version="v1.2")
    rows = [v2Umbrella(20, "v1.2", [
        candidate("obra/alpha", "present"),
        candidate("obra/beta", "new"),
    ])]
    manifest = run(censusOf(rows), tmp_path)

    assert item(manifest, 20)["authority"] == "B"
    assert any(reason.startswith("candidate-unresolved:obra/beta") for reason in item(manifest, 20)["notProven"])


def test_v2_umbrella_whose_rows_are_all_resolved_is_a2(tmp_path: Path) -> None:
    suiteRecord(tmp_path, version="v1.2")
    rows = [v2Umbrella(20, "v1.2", [
        candidate("obra/alpha", "present"),
        candidate("obra/beta", "rejected"),
    ])]
    manifest = run(censusOf(rows), tmp_path)

    assert item(manifest, 20)["authority"] == "A"
    assert item(manifest, 20)["ruleId"] == "A2-umbrella-synced"


def test_v2_row_with_a_closed_child_counts_as_resolved(tmp_path: Path) -> None:
    suiteRecord(tmp_path, version="v1.2")
    closed = childRow(30, "obra/gamma", BLOB.replace("writing-skills", "gamma"), parent=20)
    closed = {**closed, "state": "closed", "stateReason": "completed", "closedAt": FETCHED}
    rows = [v2Umbrella(20, "v1.2", [candidate("obra/gamma", "tracked", child=30)])]
    manifest = run(censusOf(rows, closed=[closed]), tmp_path)

    assert item(manifest, 20)["authority"] == "A"


def test_v2_row_with_an_open_child_blocks_a2(tmp_path: Path) -> None:
    suiteRecord(tmp_path, version="v1.2")
    rows = [
        v2Umbrella(20, "v1.2", [candidate("obra/gamma", "tracked", child=30)]),
        childRow(30, "obra/gamma", BLOB.replace("writing-skills", "gamma"), parent=20),
    ]
    manifest = run(censusOf(rows), tmp_path)

    assert item(manifest, 20)["authority"] == "B"


def test_v2_row_with_a_child_the_census_does_not_hold_is_unresolved(tmp_path: Path) -> None:
    suiteRecord(tmp_path, version="v1.2")
    rows = [v2Umbrella(20, "v1.2", [candidate("obra/gamma", "tracked", child=99)])]
    manifest = run(censusOf(rows), tmp_path)

    assert item(manifest, 20)["authority"] == "B"


# ---------------------------------------------------------------- L2, L3: registry status and upstream repo type


def test_a_deprecated_registry_record_is_never_a1(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/writing-skills", skill("obra/writing-skills", github=BLOB, status="deprecated"))
    manifest = run(censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB)]), tmp_path)

    assert item(manifest, 10)["authority"] != "A"


def test_a_non_string_upstream_repo_is_never_a1(tmp_path: Path) -> None:
    writeNamed(tmp_path, "obra/writing-skills", skill(
        "obra/writing-skills", github=BLOB, extra="upstream:\n  repo:\n    - obra/writing-skills\n"))
    manifest = run(censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB)]), tmp_path)

    assert item(manifest, 10)["authority"] != "A"


# ---------------------------------------------------------------- L4: missing registry/named is unreadable


def test_missing_registry_named_directory_is_unknown_coverage_not_an_empty_registry(tmp_path: Path) -> None:
    rows = [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB)]
    manifest = run(censusOf(rows), tmp_path)

    assert item(manifest, 10)["state"] == "not-evaluated"
    assert item(manifest, 10)["authority"] != "A"
    assert any("dir-missing" in reason for reason in manifest["coverage"]["unknown"])


# ---------------------------------------------------------------- M5: A3 listing must be a list item


def supersedeWith(body_listing: str) -> list[dict]:
    older = umbrellaRow(30, SUITE, "v6.0.0", adds=("foo",))
    child = childRow(31, "obra/foo", BLOB.replace("writing-skills", "foo"), parent=30)
    newer = umbrellaRow(40, SUITE, "v7.0.0", adds=("foo",), extraBody=body_listing)
    return [older, child, newer]


def test_prose_containing_a_plus_slug_does_not_list_a_child_for_a3(tmp_path: Path) -> None:
    emptyRegistry(tmp_path)
    rows = supersedeWith("We considered adding + foo in a future release.\n")
    manifest = run(censusOf(rows), tmp_path)

    assert item(manifest, 30)["authority"] != "A"
    assert any(reason.startswith("not-listed-in-superseder") for reason in item(manifest, 30)["notProven"])


@pytest.mark.parametrize("listing", [
    "- `+ foo` (child intake: _pending_)\n",
    "- [ ] foo\n",
    "* [x] foo\n",
    "- foo\n",
])
def test_a_markdown_list_item_lists_a_child_for_a3(tmp_path: Path, listing: str) -> None:
    emptyRegistry(tmp_path)
    manifest = run(censusOf(supersedeWith(listing)), tmp_path)

    assert item(manifest, 30)["authority"] == "A"
    assert item(manifest, 30)["ruleId"] == "A3-umbrella-superseded"


# ---------------------------------------------------------------- M6: A5 workflow state comes from the census


A5_PATH = ".github/workflows/steward-build.lock.yml"
A5_BODY = "Gh-aw report. Workflow `.github/workflows/steward-build.lock.yml` failed on the last run.\n"


def a5Census(rows_extra: dict | None = None):
    census = censusOf([botRow(70, "[aw] Steward build failed", A5_BODY)])
    if rows_extra is not None:
        census.document["workflows"] = rows_extra
    return census


def a5Policy():
    return policyFor(a5Disabled=[A5_PATH])


def test_a5_is_proven_when_the_census_reports_the_workflow_disabled(tmp_path: Path) -> None:
    emptyRegistry(tmp_path)
    census = a5Census({"complete": True, "items": [{"path": A5_PATH, "state": "disabled_manually"}]})
    manifest = run(census, tmp_path, a5Policy(), workflowDisabled=workflowProbesFor(census, a5Policy()))

    assert item(manifest, 70)["authority"] == "A"
    assert item(manifest, 70)["ruleId"] == "A5-botreport-superseded"


def test_a5_is_not_proven_when_the_census_reports_the_workflow_active_even_if_the_checkout_disables_it(tmp_path: Path) -> None:
    emptyRegistry(tmp_path)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "steward-build.lock.yml").write_text(
        "on: push\njobs:\n  build:\n    if: ${{ false }}\n    runs-on: ubuntu-latest\n", encoding="utf-8")
    census = a5Census({"complete": True, "items": [{"path": A5_PATH, "state": "active"}]})
    manifest = run(census, tmp_path, a5Policy(), workflowDisabled=workflowProbesFor(census, a5Policy()))

    assert item(manifest, 70)["authority"] == "C"


def test_a5_is_not_proven_without_a_workflow_listing(tmp_path: Path) -> None:
    emptyRegistry(tmp_path)
    census = a5Census()
    manifest = run(census, tmp_path, a5Policy(), workflowDisabled=workflowProbesFor(census, a5Policy()))

    assert item(manifest, 70)["authority"] == "C"


def test_a5_is_not_proven_when_the_workflow_listing_is_incomplete(tmp_path: Path) -> None:
    emptyRegistry(tmp_path)
    census = a5Census({"complete": False, "reason": "http-403", "items": [{"path": A5_PATH, "state": "disabled_manually"}]})
    manifest = run(census, tmp_path, a5Policy(), workflowDisabled=workflowProbesFor(census, a5Policy()))

    assert item(manifest, 70)["authority"] == "C"


def test_a5_is_not_proven_for_a_workflow_policy_does_not_list(tmp_path: Path) -> None:
    emptyRegistry(tmp_path)
    census = a5Census({"complete": True, "items": [{"path": A5_PATH, "state": "disabled_manually"}]})
    manifest = run(census, tmp_path, policyFor(a5Disabled=[]), workflowDisabled=workflowProbesFor(census, policyFor()))

    assert item(manifest, 70)["authority"] == "C"


def test_validate_census_still_accepts_a_census_without_a_workflow_section(tmp_path: Path) -> None:
    census = a5Census()
    assert census.status.status == validateCensus(census.document, NOW, 21600).status
