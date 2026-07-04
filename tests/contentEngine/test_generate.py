"""Tests for scripts/contentEngine/generate_weekly_report.py."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# The content engine ships as a bare module (scripts/contentEngine is a package,
# but scripts/ is not). Add the package dir to sys.path so imports resolve.
ROOT = Path(__file__).resolve().parents[2]
PKG_DIR = ROOT / "scripts" / "contentEngine"
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

import generate_weekly_report as g  # noqa: E402
from synthesizer import synthesize, synthesizeL3Mechanical  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures — synthetic trending data that lives ONLY in the test's tempdir
# ---------------------------------------------------------------------------


def _seedTrendingApi(root: Path) -> Path:
    """Write minimal but valid trending/*.json fixtures for the loaders."""
    apiDir = root / "api" / "v1"
    trendingDir = apiDir / "trending"
    trendingDir.mkdir(parents=True, exist_ok=True)

    (trendingDir / "7d.json").write_text(json.dumps({
        "window": "7d",
        "generatedAt": "2026-07-04T10:00:00Z",
        "firstRun": False,
        "skills": [
            {
                "id": "alice/foo",
                "name": "Foo",
                "level": "3★",
                "contributor": "alice",
                "trustMagnitude": 42.5,
                "overallTrustGrade": "B",
                "trendingScore": 10.0,
                "tmDelta": 5.0,
                "new": False,
            },
            {
                "id": "bob/bar",
                "name": "Bar",
                "level": "4★",
                "contributor": "bob",
                "trustMagnitude": 88.1,
                "overallTrustGrade": "A",
                "trendingScore": 25.0,
                "tmDelta": 12.5,
                "new": True,
            },
        ],
    }))

    (trendingDir / "ascended.json").write_text(json.dumps({
        "generatedAt": "2026-07-04T10:00:00Z",
        "skills": [
            {
                "id": "alice/foo",
                "name": "Foo",
                "level": "3★",
                "contributor": "alice",
                "trustMagnitude": 42.5,
                "overallTrustGrade": "B",
                "ascendedAt": "2026-07-03T15:00:00Z",
                "previousLevel": "2★",
            },
        ],
    }))

    (trendingDir / "contested.json").write_text(json.dumps({
        "generatedAt": "2026-07-04T10:00:00Z",
        "buckets": [
            {
                "genericSkillRef": "ux-audit",
                "implementations": 3,
                "topTM": 100.0,
                "skills": [
                    {"id": "alice/foo", "trustMagnitude": 100.0, "level": "4★",
                     "overallTrustGrade": "A", "origin": True},
                    {"id": "bob/bar", "trustMagnitude": 55.0, "level": "3★",
                     "overallTrustGrade": "B", "origin": False},
                ],
            },
        ],
    }))

    return apiDir


def _emptyReport() -> dict:
    return g.assembleReport(
        year=2026, week=27,
        sections={
            "trending": {"title": "Trending this week", "entries": []},
            "ascended": {"title": "Recently ascended", "entries": []},
            "contested": {"title": "Most contested spaces", "entries": []},
        },
        salvageLayer="L3",
        generatedAt="2026-07-04T10:00:00Z",
        version="0.0.0-test",
    )


def _validReport() -> dict:
    return g.assembleReport(
        year=2026, week=27,
        sections={
            "trending": g.renderTrendingSection([{"id": "a/x", "name": "X"}]),
            "ascended": {"title": "Recently ascended", "entries": []},
            "contested": {"title": "Most contested spaces", "entries": []},
        },
        salvageLayer="L3",
        generatedAt="2026-07-04T10:00:00Z",
        version="0.0.0-test",
    )


# ---------------------------------------------------------------------------
# Tests — canonical from the plan
# ---------------------------------------------------------------------------


def test_L3_never_raises_on_valid_data():
    report = _validReport()
    out = synthesizeL3Mechanical(report)
    assert out["salvageLayer"] == "L3"
    # Must preserve the input shape (no field drops).
    assert out["sections"]["trending"]["entries"][0]["id"] == "a/x"


def test_L3_raises_on_empty_data():
    with pytest.raises(ValueError, match="empty sections"):
        synthesizeL3Mechanical(_emptyReport())


def test_publish_gate_off_writes_to_draft(tmp_path: Path):
    apiDir = _seedTrendingApi(tmp_path)
    docsRoot = tmp_path / "docs"
    g.run(apiDir, docsRoot, publishFlag=False,
          now=datetime(2026, 7, 4, 10, 0, 0))

    draftPath = docsRoot / "reports" / "DRAFT" / "2026-27.md"
    assert draftPath.exists(), f"DRAFT markdown missing at {draftPath}"
    body = draftPath.read_text(encoding="utf-8")
    assert "Weekly Report" in body
    assert "Foo" in body  # trending fixture bleeds through
    # Publish target artefacts must NOT exist in draft mode.
    assert not (docsRoot / "reports" / "2026-27").exists()
    assert not (docsRoot / "api" / "v1" / "reports" / "2026-27.json").exists()


def test_publish_gate_on_writes_canonical(tmp_path: Path):
    apiDir = _seedTrendingApi(tmp_path)
    docsRoot = tmp_path / "docs"
    g.run(apiDir, docsRoot, publishFlag=True,
          now=datetime(2026, 7, 4, 10, 0, 0))

    canonical = docsRoot / "api" / "v1" / "reports" / "2026-27.json"
    html = docsRoot / "reports" / "2026-27" / "index.html"
    archiveJson = docsRoot / "api" / "v1" / "reports" / "index.json"
    archiveHtml = docsRoot / "reports" / "index.html"

    for p in (canonical, html, archiveJson, archiveHtml):
        assert p.exists(), f"expected {p} to be published"

    data = json.loads(canonical.read_text(encoding="utf-8"))
    assert data["reportId"] == "2026-27"
    assert data["schemaVersion"] == "1.0.0"
    assert data["salvageLayer"] in ("L1", "L2", "L3")
    assert data["urls"]["canonical"].endswith("/reports/2026-27/")

    # Archive must contain the freshly-published entry.
    archive = json.loads(archiveJson.read_text(encoding="utf-8"))
    ids = [r["reportId"] for r in archive["reports"]]
    assert "2026-27" in ids


def test_isoYearWeek_year_boundary():
    """ISO year != calendar year at boundaries. 2027-01-01 is a Friday and
    belongs to ISO week 53 of 2026 (%G-%V), not week 1 of 2027 (%Y-%W)."""
    year, week = g.isoYearWeek(datetime(2027, 1, 1))
    assert (year, week) == (2026, 53)
    assert g.weekLabel(year, week) == "2026-53"

    # Sanity: 2021-01-01 (Friday) → ISO 2020-W53.
    year2, week2 = g.isoYearWeek(datetime(2021, 1, 1))
    assert (year2, week2) == (2020, 53)


def test_contested_shape_reads_buckets_not_skills(tmp_path: Path):
    apiDir = _seedTrendingApi(tmp_path)
    buckets = g.loadContested(apiDir, top=5)
    assert len(buckets) == 1
    assert buckets[0]["genericSkillRef"] == "ux-audit"

    # Wrong shape must raise loudly (red-team fix).
    contestedPath = apiDir / "trending" / "contested.json"
    contestedPath.write_text(json.dumps({"generatedAt": "x", "skills": []}))
    with pytest.raises(ValueError, match="buckets"):
        g.loadContested(apiDir)


def test_index_json_rebuilt_not_appended(tmp_path: Path):
    """Two consecutive publish runs against different weeks should both appear
    in the archive index — but a THIRD publish where one report's HTML has
    been deleted must prune the stale entry (rebuild semantics, not append)."""
    apiDir = _seedTrendingApi(tmp_path)
    docsRoot = tmp_path / "docs"

    g.run(apiDir, docsRoot, publishFlag=True,
          now=datetime(2026, 7, 4, 10, 0, 0))  # 2026-27
    g.run(apiDir, docsRoot, publishFlag=True,
          now=datetime(2026, 7, 11, 10, 0, 0))  # 2026-28

    archivePath = docsRoot / "api" / "v1" / "reports" / "index.json"
    archive = json.loads(archivePath.read_text(encoding="utf-8"))
    ids = {r["reportId"] for r in archive["reports"]}
    assert {"2026-27", "2026-28"}.issubset(ids)

    # Now delete week 27's HTML dir and re-publish week 28. The archive must
    # be REBUILT from disk — the pruned 27 disappears from index.json.
    import shutil
    shutil.rmtree(docsRoot / "reports" / "2026-27")

    g.run(apiDir, docsRoot, publishFlag=True,
          now=datetime(2026, 7, 11, 10, 0, 0))
    archive2 = json.loads(archivePath.read_text(encoding="utf-8"))
    ids2 = {r["reportId"] for r in archive2["reports"]}
    assert "2026-27" not in ids2
    assert "2026-28" in ids2


def test_no_snake_case_new_publics():
    """Public functions added in this workstream must be camelCase (workspace
    rule). We reflect the module and check every callable that isn't a
    private helper (leading underscore) or an imported dunder.

    Whitelisted grandfathered names: main, run — matching the CLI shape used
    across scripts/ (see build_docs.py, buildTrendingProjection.py)."""
    import inspect

    whitelist = {"main", "run"}
    banned = []
    for name, obj in inspect.getmembers(g):
        if name.startswith("_") or name in whitelist:
            continue
        if not inspect.isfunction(obj):
            continue
        # Only inspect functions defined in this module (not re-exports).
        if inspect.getmodule(obj) is not g:
            continue
        if "_" in name:
            banned.append(name)

    assert not banned, (
        f"Public functions must be camelCase per workspace rules; found "
        f"snake_case: {banned}"
    )
