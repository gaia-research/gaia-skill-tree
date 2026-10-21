"""Tests for `gaia dev timeline-resort` (named-skill frontmatter timeline re-sort)."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from gaia_cli.commands.dev.timelineResortCmd import canonicalJson, timelineResortCommand
from gaia_cli.main import main

SKILL_ID = "gaiabot/repo-docs-before-pr"

OUT_OF_ORDER = """---
id: gaiabot/repo-docs-before-pr
name: Repo Docs Before PR
contributor: gaiabot
status: awakened
description: Builds docs as a pre-PR guardrail;
  wrapped continuation line kept verbatim.
tags:
- documentation
- ci
evidence:
- class: B
  source: https://github.com/gaia-research/gaia-skill-tree
trustMagnitude: 36.0
timeline:
- timestamp: '2026-09-05T00:00:00Z'
  action: demote
  author: mbtiongson1
  notes: "Demoted from 2★ to 1★ (#1699)"
- timestamp: '2026-06-10T05:38:16Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence
- timestamp: '2026-06-14T12:32:18Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded as B (trustNumber: 70.0)'
installable: false
---
# Body

Body text with a stray fence:
---
More body.
"""

CHRONOLOGICAL = """---
id: gaiabot/repo-docs-before-pr
name: Repo Docs Before PR
timeline:
- timestamp: '2026-06-10T05:38:16Z'
  action: evidence_added
- timestamp: '2026-09-05T00:00:00Z'
  action: demote
installable: false
---
Body.
"""


def _write_registry(tmp_path: Path, text: str, skill_id: str = SKILL_ID) -> tuple[str, Path]:
    root = tmp_path / "reg"
    contributor, slug = skill_id.split("/", 1)
    target = root / "registry" / "named" / contributor / f"{slug}.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(text.encode("utf-8"))
    return str(root), target


def _args(root: str, skill_id: str = SKILL_ID, dry_run: bool = False) -> SimpleNamespace:
    return SimpleNamespace(registry=root, skill_id=skill_id, dry_run=dry_run, no_build=True)


def _timeline(path: Path) -> list:
    text = path.read_bytes().decode("utf-8")
    fm = text.split("---\n", 2)[1]
    return yaml.safe_load(fm)["timeline"]


def _lines_outside_timeline(text: str) -> tuple[list, list]:
    lines = text.splitlines(keepends=True)
    head = lines.index("timeline:\n")
    tail = lines.index("installable: false\n")
    return lines[:head], lines[tail:]


def test_already_chronological_is_noop(tmp_path, capsys):
    root, path = _write_registry(tmp_path, CHRONOLOGICAL)
    before = path.read_bytes()
    timelineResortCommand(_args(root))
    assert path.read_bytes() == before
    assert "already chronological" in capsys.readouterr().out


def test_reorder_moves_only_out_of_order_event(tmp_path):
    root, path = _write_registry(tmp_path, OUT_OF_ORDER)
    timelineResortCommand(_args(root))
    stamps = [e["timestamp"] for e in _timeline(path)]
    assert stamps == [
        "2026-06-10T05:38:16Z",
        "2026-06-14T12:32:18Z",
        "2026-09-05T00:00:00Z",
    ]


def test_event_multiset_identical_before_and_after(tmp_path):
    root, path = _write_registry(tmp_path, OUT_OF_ORDER)
    before = sorted(canonicalJson(e) for e in _timeline(path))
    timelineResortCommand(_args(root))
    after = sorted(canonicalJson(e) for e in _timeline(path))
    assert len(after) == 3
    assert before == after


def test_non_timeline_bytes_unchanged(tmp_path):
    root, path = _write_registry(tmp_path, OUT_OF_ORDER)
    old_head, old_tail = _lines_outside_timeline(OUT_OF_ORDER)
    timelineResortCommand(_args(root))
    new_text = path.read_bytes().decode("utf-8")
    new_head, new_tail = _lines_outside_timeline(new_text)
    assert new_head == old_head
    assert new_tail == old_tail
    assert new_text.endswith("# Body\n\nBody text with a stray fence:\n---\nMore body.\n")


DEMOTE_ITEM = (
    "- timestamp: '2026-09-05T00:00:00Z'\n"
    "  action: demote\n"
    "  author: mbtiongson1\n"
    "  notes: \"Demoted from 2★ to 1★ (#1699)\"\n"
)


def test_pure_reorder_of_item_blocks(tmp_path):
    root, path = _write_registry(tmp_path, OUT_OF_ORDER)
    timelineResortCommand(_args(root))
    expected = OUT_OF_ORDER.replace(DEMOTE_ITEM, "", 1).replace(
        "  details: 'Re-graded as B (trustNumber: 70.0)'\n",
        "  details: 'Re-graded as B (trustNumber: 70.0)'\n" + DEMOTE_ITEM,
        1,
    )
    assert path.read_bytes().decode("utf-8") == expected


def test_ties_keep_existing_order(tmp_path):
    text = (
        "---\n"
        "id: gaiabot/repo-docs-before-pr\n"
        "timeline:\n"
        "- timestamp: '2026-09-05T00:00:00Z'\n"
        "  action: first_tie\n"
        "- timestamp: '2026-06-10T05:38:16Z'\n"
        "  action: evidence_added\n"
        "- timestamp: '2026-09-05T00:00:00Z'\n"
        "  action: second_tie\n"
        "---\n"
        "Body.\n"
    )
    root, path = _write_registry(tmp_path, text)
    timelineResortCommand(_args(root))
    actions = [e["action"] for e in _timeline(path)]
    assert actions == ["evidence_added", "first_tie", "second_tie"]


@pytest.mark.parametrize("bad_stamp", ["'not-a-date'", "'2026-06-10T05:38:16'", "'2026-06-10'"])
def test_unparseable_or_naive_timestamp_refused_without_write(tmp_path, capsys, bad_stamp):
    text = OUT_OF_ORDER.replace("'2026-06-10T05:38:16Z'", bad_stamp)
    root, path = _write_registry(tmp_path, text)
    before = path.read_bytes()
    with pytest.raises(SystemExit) as exc:
        timelineResortCommand(_args(root))
    assert exc.value.code == 1
    assert path.read_bytes() == before
    err = capsys.readouterr().err
    assert "timestamp" in err
    assert "Fix:" in err


def test_non_mapping_event_refused_without_write(tmp_path, capsys):
    text = (
        "---\n"
        "id: gaiabot/repo-docs-before-pr\n"
        "timeline:\n"
        "- timestamp: '2026-09-05T00:00:00Z'\n"
        "  action: demote\n"
        "- 'just a string event'\n"
        "---\n"
        "Body.\n"
    )
    root, path = _write_registry(tmp_path, text)
    before = path.read_bytes()
    with pytest.raises(SystemExit):
        timelineResortCommand(_args(root))
    assert path.read_bytes() == before
    assert "not a mapping" in capsys.readouterr().err


def test_dry_run_writes_nothing(tmp_path, capsys):
    root, path = _write_registry(tmp_path, OUT_OF_ORDER)
    before = path.read_bytes()
    timelineResortCommand(_args(root, dry_run=True))
    assert path.read_bytes() == before
    out = capsys.readouterr().out
    assert "Proposed order" in out
    assert "Dry run: nothing written." in out


def test_missing_target_refused(tmp_path, capsys):
    root, _ = _write_registry(tmp_path, OUT_OF_ORDER)
    with pytest.raises(SystemExit) as exc:
        timelineResortCommand(_args(root, skill_id="nobody/missing-skill"))
    assert exc.value.code == 1
    assert "was not found" in capsys.readouterr().err


def test_frontmatter_id_mismatch_refused(tmp_path):
    root, path = _write_registry(tmp_path, OUT_OF_ORDER.replace("id: gaiabot/repo-docs-before-pr", "id: gaiabot/other"))
    before = path.read_bytes()
    with pytest.raises(SystemExit):
        timelineResortCommand(_args(root))
    assert path.read_bytes() == before


def _write_named_index(root: Path, contributor: str, level: str) -> None:
    index = {
        "buckets": {"skill-a": [{"contributor": contributor, "level": level, "genericSkillRef": "skill-a"}]},
        "byContributor": {},
        "awaitingClassification": [],
    }
    (root / "registry" / "named-skills.json").write_text(json.dumps(index), encoding="utf-8")


def test_dispatch_gates_timeline_resort_for_non_verifier(monkeypatch, tmp_path, capsys):
    root, path = _write_registry(tmp_path, OUT_OF_ORDER)
    _write_named_index(Path(root), "alice", "4★")
    before = path.read_bytes()
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "bob")
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", root, "dev", "timeline-resort", SKILL_ID])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "Verifier" in capsys.readouterr().err
    assert path.read_bytes() == before


def test_dispatch_allows_timeline_resort_for_verifier(monkeypatch, tmp_path, capsys):
    root, path = _write_registry(tmp_path, OUT_OF_ORDER)
    _write_named_index(Path(root), "alice", "4★")
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "alice")
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", root, "dev", "timeline-resort", SKILL_ID])
    try:
        main()
    except SystemExit as e:
        assert e.code in (None, 0)
    stamps = [e["timestamp"] for e in _timeline(path)]
    assert stamps[-1] == "2026-09-05T00:00:00Z"
