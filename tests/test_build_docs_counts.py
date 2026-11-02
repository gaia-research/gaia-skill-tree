"""Regression tests for homepage and about-page registry counts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "build_docs.py"


def _load_build_docs():
    spec = importlib.util.spec_from_file_location("build_docs", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_homepage_ledger_counts_are_generated_from_registry_sources(tmp_path, monkeypatch):
    build_docs = _load_build_docs()
    monkeypatch.setattr(build_docs, "ROOT", tmp_path)
    _write_json(tmp_path / "registry/gaia.json", {
        "skills": [
            {"id": "one", "type": "basic", "evidence": []},
            {"id": "two", "type": "fusion", "evidence": []},
        ],
    })
    _write_json(tmp_path / "registry/named-skills.json", {
        "buckets": {
            "one": [
                {"id": "author/first", "level": "5★", "genericSkillRef": "one"},
                {"id": "other/implementation", "level": "5★", "genericSkillRef": "one"},
            ],
            "two": [{"id": "author/second", "level": "2★", "genericSkillRef": "two"}],
        },
    })
    homepage = tmp_path / "docs/index.html"
    homepage.parent.mkdir(parents=True)
    homepage.write_text(
        '<span id="ledgerNamed"><!-- gaia:homepage-named-start -->—'
        '<!-- gaia:homepage-named-end --></span>\n'
        '<span id="ledgerUlts"><!-- gaia:homepage-ultimates-start -->—'
        '<!-- gaia:homepage-ultimates-end --></span>\n'
        '<!-- gaia:stats-start --><!-- stale --><!-- gaia:stats-end -->',
        encoding="utf-8",
    )

    assert build_docs.build_docs_index(check=False) is True
    rendered = homepage.read_text(encoding="utf-8")
    assert 'id="ledgerNamed"><!-- gaia:homepage-named-start -->\n3\n' in rendered
    assert 'id="ledgerUlts"><!-- gaia:homepage-ultimates-start -->\n2\n' in rendered
    assert "skills=2; namedSkills=3; uniqueSkills=" in rendered


def test_public_directory_counts_all_records_without_calling_them_named_skills(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "generate_profile_pages", REPO_ROOT / "scripts" / "generateProfilePages.py"
    )
    assert spec is not None and spec.loader is not None
    profiles = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profiles)
    monkeypatch.setattr(profiles, "skill_branch", lambda _skill: "standard")
    monkeypatch.setattr(profiles, "rank_badge_html", lambda *args, **kwargs: "")

    grouped = profiles.collect_by_contributor({
        "buckets": {"one": [{"id": "classified/one", "contributor": "classified", "level": "2★"}]},
        "awaitingClassification": [{"id": "awakened/two", "contributor": "awakened", "level": "1★"}],
    })
    page = profiles.build_directory_page(grouped)

    assert set(grouped) == {"classified", "awakened"}
    assert "2 contributors · 2 skill records" in page
    assert "2 skill records" in page
    assert "2 named skills claimed" not in page


def test_about_contributor_total_matches_directory_population(tmp_path, monkeypatch):
    build_docs = _load_build_docs()
    monkeypatch.setattr(build_docs, "ROOT", tmp_path)
    monkeypatch.setattr(build_docs, "_read_version", lambda: "test")
    _write_json(tmp_path / "registry/gaia.json", {"skills": [{"id": "one", "evidence": []}]})
    _write_json(tmp_path / "registry/named-skills.json", {
        "buckets": {"one": [{"contributor": "classified"}]},
        "byContributor": {
            "classified": [{"id": "classified/one"}],
            "awakened-only": [{"id": "awakened-only/two"}],
            "another-builder": [{"id": "another-builder/three"}],
        },
    })
    about = tmp_path / "docs/about.html"
    about.parent.mkdir(parents=True)
    about.write_text(
        "<!-- gaia:about-tally-start --><!-- old --><!-- gaia:about-tally-end -->",
        encoding="utf-8",
    )

    assert build_docs.build_about_stats(check=False) is True
    rendered = about.read_text(encoding="utf-8")
    assert (
        '<dt class="ab-tally-label">Contributors</dt>\n'
        '            <dd class="ab-tally-num">3</dd>'
    ) in rendered
