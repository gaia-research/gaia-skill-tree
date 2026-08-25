"""Tests for gaia_cli.registryMaps.buildMergedSkillMap (Issue #1600).

Covers:
- Generic nodes and named skills merge into one {id: skillDict} map
- Named entries win over a generic entry on id collision
- Only status == "named" entries are included from the named half
- The RFC §C-2 `role` key (e.g. `role: variant`) survives from named
  entries' frontmatter into the merged map (Issue #1643 — it must NOT be
  stripped; TM grading reads it to exclude suite-variant origins)
- Missing registry/nodes or registry/named directories degrade gracefully
- End-to-end with trustMagnitude.py: a `role: variant` suite component is
  excluded from the graded-origin count (Issue #1643 regression), while a
  suite component with no RFC role at all (only a UI-facing non-champion
  distinction, which never reaches this map — see registryMaps.py's
  docstring) is NOT excluded (the original commit `59a87e45d` regression)
"""

import json
from pathlib import Path

import pytest

from gaia_cli.registryMaps import buildMergedSkillMap
from gaia_cli.trustMagnitude import computeTrustMagnitude


def _write_generic_node(tmp_path: Path, skill_id: str, **fields) -> None:
    nodes_dir = tmp_path / "registry" / "nodes" / "basic"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    node = {"id": skill_id, "name": skill_id, "evidence": [], **fields}
    (nodes_dir / f"{skill_id}.json").write_text(json.dumps(node), encoding="utf-8")


def _write_named_skill(tmp_path: Path, skill_id: str, *, status: str = "named", **fields) -> None:
    contributor, slug = skill_id.split("/", 1)
    named_dir = tmp_path / "registry" / "named" / contributor
    named_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = {
        "id": skill_id,
        "contributor": contributor,
        "status": status,
        "level": "2★",
        **fields,
    }
    body = "\n".join(f"{k}: {json.dumps(v)}" for k, v in frontmatter.items())
    (named_dir / f"{slug}.md").write_text(f"---\n{body}\n---\n## Installation\n", encoding="utf-8")


def test_merges_generic_and_named_skills(tmp_path):
    _write_generic_node(tmp_path, "research")
    _write_named_skill(tmp_path, "alice/research-deep")

    merged = buildMergedSkillMap(tmp_path)

    assert "research" in merged
    assert "alice/research-deep" in merged


def test_named_entry_wins_on_id_collision(tmp_path):
    _write_generic_node(tmp_path, "shared-id", name="generic-version")
    # Not a realistic id shape (named ids are normally contributor/slug), but
    # the merge semantics under test are id-keyed dict overlay regardless of
    # shape — write the file directly rather than through the slug-splitting
    # helper.
    named_dir = tmp_path / "registry" / "named"
    named_dir.mkdir(parents=True, exist_ok=True)
    (named_dir / "shared-id.md").write_text(
        '---\nid: "shared-id"\nstatus: "named"\nname: "named-version"\n---\n',
        encoding="utf-8",
    )

    merged = buildMergedSkillMap(tmp_path)
    assert merged["shared-id"]["name"] == "named-version"


def test_excludes_non_named_status(tmp_path):
    _write_named_skill(tmp_path, "bob/draft-skill", status="provisional")

    merged = buildMergedSkillMap(tmp_path)

    assert "bob/draft-skill" not in merged


def test_preserves_role_key_from_named_entries(tmp_path):
    """RFC §C-2's role: variant marker must survive into the merged map —
    trustMagnitude.py's _gradedOriginCount() reads it to exclude a suite
    component from the graded-origin count (Issue #1643 regression)."""
    _write_named_skill(tmp_path, "alice/variant-skill", role="variant")

    merged = buildMergedSkillMap(tmp_path)

    assert merged["alice/variant-skill"]["role"] == "variant"


def test_missing_registry_dirs_return_empty_map(tmp_path):
    merged = buildMergedSkillMap(tmp_path)
    assert merged == {}


def test_role_variant_component_excluded_from_graded_origin_count(tmp_path):
    """Issue #1643 end-to-end regression: a suite component carrying a
    genuine `role: variant` frontmatter marker must be excluded from the
    graded-origin count that drives fusion-recipe Trust Magnitude, when
    resolved through the shared buildMergedSkillMap() resolver — not just
    when the caller hand-builds a genericSkillMap directly (as
    test_trust_magnitude.py's unit-level coverage already does)."""
    _write_named_skill(tmp_path, "alice/comp-graded", overallGrade="B")
    _write_named_skill(tmp_path, "alice/comp-variant", role="variant", overallGrade="B")
    _write_named_skill(
        tmp_path,
        "alice/suite-skill",
        suiteComponents=["alice/comp-graded", "alice/comp-variant"],
    )

    merged = buildMergedSkillMap(tmp_path)
    suite = merged["alice/suite-skill"]

    tm = computeTrustMagnitude(suite, merged)
    # Auto-minted fusion-recipe row over 2 suiteComponents, but only
    # comp-graded counts (comp-variant is excluded by role='variant'):
    # m = 20*1 = 20; weight 1.5 => fusion-recipe artifact score 30.0, which
    # is also the skill's only evidence contribution.
    assert tm == pytest.approx(30.0)


def test_suite_component_without_role_still_counts_as_graded_origin(tmp_path):
    """Guards against reintroducing the original commit `59a87e45d` bug: a
    suite component with no genuine RFC `role` field at all (i.e. it is not
    the bucket champion, but that UI-only distinction never reaches
    buildMergedSkillMap()'s frontmatter-sourced map) must still count as a
    full graded origin — it must NOT lose fusion contribution."""
    _write_named_skill(tmp_path, "alice/comp-a", overallGrade="B")
    _write_named_skill(tmp_path, "alice/comp-b", overallGrade="B")
    _write_named_skill(
        tmp_path,
        "alice/suite-skill-2",
        suiteComponents=["alice/comp-a", "alice/comp-b"],
    )

    merged = buildMergedSkillMap(tmp_path)
    suite = merged["alice/suite-skill-2"]

    tm = computeTrustMagnitude(suite, merged)
    # Both components graded and neither is role='variant': m = 20*2 = 40;
    # weight 1.5 => 60.0.
    assert tm == pytest.approx(60.0)
