"""Lane B7 round-2 identity and proof rules: umbrella child listings (M2), the A1 status allowlist (M4), and
links.github against upstream.repo (L1). The fixtures are the lane-B reconcile fixtures, unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.identity import childLines
from tests.steward.issuehygiene.test_b_reconcile import BLOB, a1Fixture, item, run, skill


@pytest.mark.parametrize(("line", "expected"), [
    ("- #1236 candidate listed by a bullet", (1236,)),
    ("* #1237 candidate listed by a star bullet", (1237,)),
    ("- [ ] #1238 unchecked checklist item", (1238,)),
    ("- [x] #1239 checked checklist item", (1239,)),
    ("Child intake: #1240", (1240,)),
    ("- Child intake #1241 still open", (1241,)),
    ("Child intakes: #1242, #1243", (1242, 1243)),
    ("The child intake #1244 is pending founder review.", ()),
    ("Earlier we saw child intake #1245 mentioned mid-sentence.", ()),
    ("+ #1246 is prose, not a markdown list item", ()),
    ("Notes: see #1247 for context", ()),
])
def test_only_list_items_and_child_intake_prefixes_list_a_child(line: str, expected: tuple) -> None:
    assert childLines(line) == expected


def test_a_listing_inside_a_fenced_body_still_counts_as_a_list_line() -> None:
    body = "## Child intakes\n\n- [ ] #2001 first\n- [x] #2002 second\n\nProse: the child intake #2003 is elsewhere.\n"
    assert childLines(body) == (2001, 2002)


@pytest.mark.parametrize(("status", "authority"), [("awakened", "A"), ("named", "A")])
def test_the_schema_statuses_are_the_only_ones_that_can_close(tmp_path: Path, status: str, authority: str) -> None:
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=BLOB, status=status)), tmp_path)
    assert item(manifest, 10)["authority"] == authority


@pytest.mark.parametrize("status", ["archived", "draft", "deprecated", "retired-by-someone"])
def test_any_status_outside_the_schema_enum_is_not_proof(tmp_path: Path, status: str) -> None:
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=BLOB, status=status)), tmp_path)
    assert item(manifest, 10)["authority"] == "B"
    assert "registry-status-not-allowed" in item(manifest, 10)["notProven"]


def test_a_missing_status_is_not_proof(tmp_path: Path) -> None:
    body = "---\nid: obra/writing-skills\ncontributor: obra\nlinks:\n  github: " + BLOB + "\n---\n"
    manifest = run(a1Fixture(tmp_path, body), tmp_path)
    assert item(manifest, 10)["authority"] == "B"
    assert "registry-status-missing" in item(manifest, 10)["notProven"]


def test_an_unreadable_schema_fails_closed_for_every_status(tmp_path: Path) -> None:
    from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex

    census = a1Fixture(tmp_path, skill("obra/writing-skills", github=BLOB, status="named"))
    assert item(run(census, tmp_path), 10)["authority"] == "A"
    (tmp_path / "registry" / "schema" / "namedSkill.schema.json").unlink()
    assert buildRegistryIndex(tmp_path).statusAllowed is None
    manifest = run(census, tmp_path)
    assert item(manifest, 10)["authority"] == "B"
    assert "registry-status-not-allowed" in item(manifest, 10)["notProven"]
