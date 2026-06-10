import json
import sys
from pathlib import Path


from gaia_cli.commands.stats import collect_stats, render_stats
from gaia_cli.main import main


def write_fixture_registry(root: Path) -> None:
    registry = root / "registry"
    named = registry / "named" / "alice"
    named.mkdir(parents=True)
    (registry / "gaia.json").write_text(
        json.dumps(
            {
                "skills": [
                    {"id": "tokenize", "type": "basic", "level": "0★", "evidence": []},
                    {"id": "web-search", "type": "basic", "level": "1★", "evidence": [{"class": "C"}]},
                    {
                        "id": "automated-testing",
                        "type": "extra",
                        "level": "2★",
                        "demerits": ["niche-integration"],
                        "evidence": [{"class": "B"}],
                    },
                    {"id": "autonomous-swe", "type": "ultimate", "level": "5★", "evidence": [{"class": "B"}, {"class": "A"}]},
                ],
                "edges": [{"source": "web-search", "target": "automated-testing"}],
            }
        ),
        encoding="utf-8",
    )
    (named / "pytest-patterns.md").write_text(
        "---\n"
        "id: alice/pytest-patterns\n"
        "genericSkillRef: automated-testing\n"
        "status: named\n"
        "level: 2★\n"
        "---\n",
        encoding="utf-8",
    )


def test_collect_stats_matches_fixture_graph(tmp_path):
    write_fixture_registry(tmp_path)

    stats = collect_stats(tmp_path)

    assert stats["total_skills"] == 4
    assert stats["total_edges"] == 1
    assert stats["type_counts"] == {"basic": 2, "extra": 1, "ultimate": 1}
    assert stats["level_counts"] == {"0★": 3, "2★": 1}
    assert stats["effective_level_counts"] == {"0★": 3, "1★": 1}
    assert stats["skills_with_demerits"] == 1
    assert stats["skills_with_effective_drop"] == 1
    assert stats["demerit_penalty_total"] == 1
    assert stats["skills_with_evidence"] == 3
    assert stats["evidence_counts"] == {"A": 1, "B": 1, "C": 1}
    assert stats["named_implemented"] == 1
    assert stats["named_eligible"] == 4


def test_collect_stats_supports_legacy_graph_layout(tmp_path):
    graph = tmp_path / "graph"
    named = graph / "named" / "alice"
    named.mkdir(parents=True)
    (graph / "gaia.json").write_text(
        json.dumps(
            {
                "skills": [
                    {"id": "plan", "type": "basic", "level": "1★", "prerequisites": [], "evidence": [{"class": "C"}]},
                    {"id": "execute", "type": "extra", "level": "2★", "prerequisites": ["plan"], "evidence": []},
                ]
            }
        ),
        encoding="utf-8",
    )
    (named / "execute.md").write_text(
        "---\nid: alice/execute\ngenericSkillRef: execute\nstatus: named\n---\n",
        encoding="utf-8",
    )

    stats = collect_stats(tmp_path)

    assert stats["total_skills"] == 2
    assert stats["total_edges"] == 1
    assert stats["named_implemented"] == 1


def test_render_stats_includes_registry_health_sections(tmp_path):
    write_fixture_registry(tmp_path)

    output = render_stats(collect_stats(tmp_path))

    assert "Gaia Registry — 4 skills  1 edges" in output
    assert "Type breakdown" in output
    assert "Basic Skill" in output
    assert "Level breakdown" in output
    assert "Effective level breakdown" in output
    assert "Demerits" in output
    assert "Evidence coverage" in output
    assert "With evidence    3 / 4" in output
    assert "Named skills" in output
    assert "Implemented     1 / 4 eligible (25%)" in output


def test_stats_cli_prints_summary(tmp_path, monkeypatch, capsys):
    write_fixture_registry(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "stats"])

    main()

    output = capsys.readouterr().out
    assert "Gaia Registry — 4 skills  1 edges" in output
    assert "Class A" in output
    assert "Effective level breakdown" in output


def test_collect_stats_missing_level(tmp_path):
    registry = tmp_path / "registry"
    registry.mkdir(parents=True, exist_ok=True)
    (registry / "gaia.json").write_text(
        json.dumps(
            {
                "skills": [
                    {"id": "tokenize", "type": "basic", "evidence": []},  # No 'level' key
                ],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    stats = collect_stats(tmp_path)
    assert "?" not in stats["level_counts"]
    assert "level_counts" in stats

