import os
import textwrap

from scripts import check_product_attribution as cpa


def _write_named_skill(named_dir, contributor, slug, skill_id, body, evidence_notes=""):
    contributor_dir = os.path.join(named_dir, contributor)
    os.makedirs(contributor_dir, exist_ok=True)
    header = textwrap.dedent(f"""\
        ---
        id: {skill_id}
        name: Test Skill
        contributor: {contributor}
        level: 1★
        evidence:
        - source: https://example.com/evidence
          notes: "{evidence_notes}"
        ---
        """)
    content = header + body + "\n"
    path = os.path.join(contributor_dir, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _patch_tool_map(monkeypatch, tool_map):
    monkeypatch.setattr(cpa, "TOOL_MAKER_MAP", tool_map)


def test_flags_unattributed_product_skill(tmp_path, monkeypatch):
    named_dir = tmp_path / "named"
    _write_named_skill(
        str(named_dir),
        "acme",
        "widgetool",
        "acme/widgetool",
        "## Overview\nRun `widgetool scan` to scan the repo.",
    )
    monkeypatch.setattr(cpa, "NAMED_DIR", str(named_dir))
    _patch_tool_map(monkeypatch, {
        "acme/widgetool": {"tool": "WidgeTool", "makers": ["Widgeco"]},
    })

    results = cpa.run_check()

    assert len(results) == 1
    assert results[0].skill_id == "acme/widgetool"
    assert results[0].attributed is False


def test_does_not_flag_skill_that_credits_maker_in_body(tmp_path, monkeypatch):
    named_dir = tmp_path / "named"
    _write_named_skill(
        str(named_dir),
        "acme",
        "widgetool",
        "acme/widgetool",
        "## Overview\nWidgeTool is made by Widgeco. Run `widgetool scan`.",
    )
    monkeypatch.setattr(cpa, "NAMED_DIR", str(named_dir))
    _patch_tool_map(monkeypatch, {
        "acme/widgetool": {"tool": "WidgeTool", "makers": ["Widgeco"]},
    })

    results = cpa.run_check()

    assert len(results) == 1
    assert results[0].attributed is True


def test_does_not_flag_skill_that_credits_maker_in_evidence_notes(tmp_path, monkeypatch):
    named_dir = tmp_path / "named"
    _write_named_skill(
        str(named_dir),
        "acme",
        "widgetool",
        "acme/widgetool",
        "## Overview\nRun `widgetool scan` to scan the repo.",
        evidence_notes="Official WidgeTool docs, maintained by Widgeco.",
    )
    monkeypatch.setattr(cpa, "NAMED_DIR", str(named_dir))
    _patch_tool_map(monkeypatch, {
        "acme/widgetool": {"tool": "WidgeTool", "makers": ["Widgeco"]},
    })

    results = cpa.run_check()

    assert len(results) == 1
    assert results[0].attributed is True


def test_skill_not_in_map_is_never_checked(tmp_path, monkeypatch):
    named_dir = tmp_path / "named"
    _write_named_skill(
        str(named_dir),
        "acme",
        "unrelated",
        "acme/unrelated",
        "## Overview\nA completely unrelated skill body with no tool references.",
    )
    monkeypatch.setattr(cpa, "NAMED_DIR", str(named_dir))
    _patch_tool_map(monkeypatch, {
        "acme/widgetool": {"tool": "WidgeTool", "makers": ["Widgeco"]},
    })

    results = cpa.run_check()

    assert results == []


def test_missing_skill_in_map_is_skipped_not_flagged(tmp_path, monkeypatch):
    named_dir = tmp_path / "named"
    os.makedirs(str(named_dir), exist_ok=True)
    monkeypatch.setattr(cpa, "NAMED_DIR", str(named_dir))
    _patch_tool_map(monkeypatch, {
        "acme/widgetool": {"tool": "WidgeTool", "makers": ["Widgeco"]},
    })

    results = cpa.run_check()

    assert results == []


def test_generate_report_strict_exit_code_reflects_unattributed_count(tmp_path, monkeypatch):
    named_dir = tmp_path / "named"
    _write_named_skill(
        str(named_dir),
        "acme",
        "widgetool",
        "acme/widgetool",
        "## Overview\nRun `widgetool scan` to scan the repo.",
    )
    monkeypatch.setattr(cpa, "NAMED_DIR", str(named_dir))
    _patch_tool_map(monkeypatch, {
        "acme/widgetool": {"tool": "WidgeTool", "makers": ["Widgeco"]},
    })

    results = cpa.run_check()
    report = cpa.generate_report(results, output_dir=None)

    assert report["checked"] == 1
    assert report["unattributedCount"] == 1


def test_run_check_is_idempotent(tmp_path, monkeypatch):
    named_dir = tmp_path / "named"
    _write_named_skill(
        str(named_dir),
        "acme",
        "widgetool",
        "acme/widgetool",
        "## Overview\nRun `widgetool scan` to scan the repo.",
    )
    monkeypatch.setattr(cpa, "NAMED_DIR", str(named_dir))
    _patch_tool_map(monkeypatch, {
        "acme/widgetool": {"tool": "WidgeTool", "makers": ["Widgeco"]},
    })

    first = [r.__dict__ for r in cpa.run_check()]
    second = [r.__dict__ for r in cpa.run_check()]

    assert len(first) == 1
    assert first == second
    # Read-only: the fixture file on disk must be untouched by either run.
    with open(os.path.join(str(named_dir), "acme", "widgetool.md"), encoding="utf-8") as f:
        content_after = f.read()
    assert "widgetool scan" in content_after
