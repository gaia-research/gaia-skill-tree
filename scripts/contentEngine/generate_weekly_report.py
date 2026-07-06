#!/usr/bin/env python3
"""Generate Gaia's weekly content-engine report.

Reads Sprint B's trending API surface (docs/api/v1/trending/{7d,ascended,contested}.json)
and produces a report keyed by ISO year+week (%G-%V).

Publish gate: `GAIA_CONTENT_ENGINE_PUBLISH` (or --publish flag). Unset/0 writes
docs/reports/DRAFT/YYYY-WW.md (gitignored). 1 writes both the canonical JSON
under docs/api/v1/reports/YYYY-WW.json and the public HTML at
docs/reports/YYYY-WW/index.html, and rebuilds the archive index.

Invariants (Sprint F frozen):
  - URL /reports/YYYY-WW/         — SEO permanent, tweetable
  - Canonical JSON shape          — SDK contract
  - ISO week format %G-%V         — disagrees with %Y-%W at year boundaries

Public functions are camelCase (workspace rule); module filename keeps the
underscore per repo precedent (build_docs.py, check_nav_mounts.py).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Repo root is three parents up: contentEngine/ → scripts/ → repo root
ROOT = Path(__file__).resolve().parents[2]

# Make the sibling scripts/contentEngine/ package importable when this file is
# invoked directly (`python scripts/contentEngine/generate_weekly_report.py`).
# `scripts/` is intentionally NOT a Python package, so we drop this file's
# parent onto sys.path and import bare ("synthesizer") rather than dotted.
_PKG_DIR = Path(__file__).resolve().parent
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

# ---------------------------------------------------------------------------
# ISO week helpers
# ---------------------------------------------------------------------------


def isoYearWeek(dt: datetime) -> tuple[int, int]:
    """Return (isoYear, isoWeek) using %G-%V semantics.

    Note: ISO year != calendar year at boundaries. 2026-01-01 is a Thursday, so
    ISO week 53 of 2025 ends on 2026-01-04.  %Y and %W would return (2026, 0),
    which is wrong for our permanent-URL semantics.
    """
    isoCal = dt.isocalendar()
    return isoCal.year, isoCal.week


def weekLabel(year: int, week: int) -> str:
    """YYYY-WW zero-padded — the URL-facing label."""
    return f"{year:04d}-{week:02d}"


def prevWeekLabel(year: int, week: int) -> str:
    """Return the label for the ISO week preceding (year, week)."""
    # Anchor to Monday of the given ISO week, subtract 7 days, re-derive ISO.
    monday = datetime.fromisocalendar(year, week, 1)
    prior = monday.replace(tzinfo=None)
    from datetime import timedelta
    priorMonday = prior - timedelta(days=7)
    priorYear, priorWeek = isoYearWeek(priorMonday)
    return weekLabel(priorYear, priorWeek)


# ---------------------------------------------------------------------------
# Data loaders — read the trending API surface
# ---------------------------------------------------------------------------


def _readJson(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def loadTrending(apiDir: Path, window: str = "7d", top: int = 5) -> list[dict]:
    """Load the top-N trending skills from docs/api/v1/trending/<window>.json.

    Returns entries in the API's own sort order (already ranked by trendingScore
    or trustMagnitude — see buildTrendingProjection.py:build_trending_window).
    """
    data = _readJson(apiDir / "trending" / f"{window}.json")
    skills = data.get("skills", []) or []
    return skills[:top]


def loadAscended(apiDir: Path, top: int = 5) -> list[dict]:
    """Load the most-recent rank_up/calibrate events from ascended.json."""
    data = _readJson(apiDir / "trending" / "ascended.json")
    skills = data.get("skills", []) or []
    return skills[:top]


def loadContested(apiDir: Path, top: int = 3) -> list[dict]:
    """Load the top contested genericSkillRef buckets.

    contested.json's top-level is {generatedAt, buckets: [...]} — there is
    NO 'skills' key at root. Each bucket carries genericSkillRef, implementations,
    topTM, skills. We fail loudly if the shape is wrong rather than emitting a
    silently-empty section (red-team fix).
    """
    data = _readJson(apiDir / "trending" / "contested.json")
    if not data:
        return []
    if "buckets" not in data:
        raise ValueError(
            "contested.json missing required 'buckets' key — "
            "loadContested() cannot proceed with an unknown shape."
        )
    buckets = data.get("buckets", []) or []
    return buckets[:top]


# ---------------------------------------------------------------------------
# Section renderers — pure Python, feed the report dict
# ---------------------------------------------------------------------------


def renderTrendingSection(entries: list[dict]) -> dict:
    """Shape the trending section for the report dict."""
    return {
        "title": "Trending this week",
        "entries": [
            {
                "id": e.get("id", ""),
                "name": e.get("name", "") or e.get("id", ""),
                "contributor": e.get("contributor", ""),
                "level": e.get("level", ""),
                "trustMagnitude": e.get("trustMagnitude", 0),
                "trustGrade": e.get("overallTrustGrade"),
                "trendingScore": e.get("trendingScore", 0),
                "tmDelta": e.get("tmDelta", 0),
                "isNew": bool(e.get("new", False)),
                "url": f"https://gaiaskilltree.com/named/#explorer/{e.get('id', '')}",
            }
            for e in entries
        ],
    }


def renderAscendedSection(entries: list[dict]) -> dict:
    """Shape the recently-ascended section."""
    return {
        "title": "Recently ascended",
        "entries": [
            {
                "id": e.get("id", ""),
                "name": e.get("name", "") or e.get("id", ""),
                "contributor": e.get("contributor", ""),
                "level": e.get("level", ""),
                "previousLevel": e.get("previousLevel"),
                "trustMagnitude": e.get("trustMagnitude", 0),
                "trustGrade": e.get("overallTrustGrade"),
                "ascendedAt": e.get("ascendedAt", ""),
                "url": f"https://gaiaskilltree.com/named/#explorer/{e.get('id', '')}",
            }
            for e in entries
        ],
    }


def renderContestedSection(buckets: list[dict]) -> dict:
    """Shape the contested-space section from the buckets array."""
    return {
        "title": "Most contested spaces",
        "entries": [
            {
                "genericSkillRef": b.get("genericSkillRef", ""),
                "implementations": b.get("implementations", 0),
                "topTM": b.get("topTM", 0),
                "skills": [
                    {
                        "id": s.get("id", ""),
                        "level": s.get("level", ""),
                        "trustMagnitude": s.get("trustMagnitude", 0),
                        "trustGrade": s.get("overallTrustGrade"),
                        "origin": bool(s.get("origin", False)),
                        "url": f"https://gaiaskilltree.com/named/#explorer/{s.get('id', '')}",
                    }
                    for s in (b.get("skills", []) or [])
                ],
            }
            for b in buckets
        ],
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _readVersion() -> str:
    """Best-effort gaia-cli version — importlib.metadata first, pyproject fallback."""
    try:
        from importlib.metadata import PackageNotFoundError, version as packageVersion
        try:
            return packageVersion("gaia-cli")
        except PackageNotFoundError:
            pass
    except ImportError:
        pass
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if m:
            return m.group(1)
    return "0.0.0"


def assembleReport(
    year: int,
    week: int,
    sections: dict,
    salvageLayer: str,
    generatedAt: str,
    version: str,
) -> dict:
    """Build the canonical report dict — this shape is frozen for Sprint F."""
    return {
        "schemaVersion": "1.0.0",
        "reportId": weekLabel(year, week),
        "isoYear": year,
        "isoWeek": week,
        "generatedAt": generatedAt,
        "generator": "gaia-content-engine",
        "generatorVersion": version,
        "salvageLayer": salvageLayer,
        "sections": {
            "trending": sections.get("trending", {"title": "Trending this week", "entries": []}),
            "ascended": sections.get("ascended", {"title": "Recently ascended", "entries": []}),
            "contested": sections.get("contested", {"title": "Most contested spaces", "entries": []}),
        },
        "urls": {
            "canonical": f"https://gaiaskilltree.com/reports/{weekLabel(year, week)}/",
            "json": f"https://gaiaskilltree.com/api/v1/reports/{weekLabel(year, week)}.json",
            "previous": f"https://gaiaskilltree.com/reports/{prevWeekLabel(year, week)}/",
            "archive": "https://gaiaskilltree.com/reports/",
        },
    }


# ---------------------------------------------------------------------------
# Publish target resolution — DRAFT vs canonical
# ---------------------------------------------------------------------------


def resolvePublishTarget(
    year: int,
    week: int,
    publishFlag: bool,
    docsRoot: Path,
) -> dict:
    """Return the set of output paths for the given publish flag.

    Publish OFF → draft-only. Written to `docs/reports/DRAFT/YYYY-WW.md`
                  (gitignored — never leaves the runner).
    Publish ON  → writes canonical JSON AND public HTML AND rebuilds index.

    Always returns absolute paths.
    """
    label = weekLabel(year, week)
    if publishFlag:
        return {
            "mode": "publish",
            "canonicalJson": docsRoot / "api" / "v1" / "reports" / f"{label}.json",
            "publicHtml": docsRoot / "reports" / label / "index.html",
            "archiveJson": docsRoot / "api" / "v1" / "reports" / "index.json",
            "archiveHtml": docsRoot / "reports" / "index.html",
            "draftMd": None,
        }
    return {
        "mode": "draft",
        "canonicalJson": None,
        "publicHtml": None,
        "archiveJson": None,
        "archiveHtml": None,
        "draftMd": docsRoot / "reports" / "DRAFT" / f"{label}.md",
    }


# ---------------------------------------------------------------------------
# Rendering — canonical JSON + Jinja markdown + HTML
# ---------------------------------------------------------------------------


def writeCanonicalJson(report: dict, outPath: Path) -> None:
    """Write the frozen-shape canonical JSON."""
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _jinjaEnv(templateDir: Path):
    """Lazy-import Jinja2 with a friendly error if missing."""
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError as exc:  # pragma: no cover — CI installs jinja2 in [dev]
        raise RuntimeError(
            "jinja2 is required to render Content Engine templates. "
            "Install with `pip install -e '.[dev]'` or `pip install jinja2`."
        ) from exc

    return Environment(
        loader=FileSystemLoader([
            str(templateDir),
            str(templateDir / "_partials"),
        ]),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def renderDraftMarkdown(report: dict, templateDir: Path, outPath: Path) -> None:
    """Render report.md.j2 → the DRAFT markdown file."""
    env = _jinjaEnv(templateDir)
    tpl = env.get_template("report.md.j2")
    text = tpl.render(report=report)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(text, encoding="utf-8")


def renderHtml(report: dict, templateDir: Path, outPath: Path) -> None:
    """Render report.html.j2 → the public /reports/YYYY-WW/index.html."""
    env = _jinjaEnv(templateDir)
    mdTpl = env.get_template("report.md.j2")
    markdownBody = mdTpl.render(report=report)
    htmlTpl = env.get_template("report.html.j2")
    text = htmlTpl.render(report=report, markdownBody=markdownBody)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(text, encoding="utf-8")


def _rebuildArchive(
    docsRoot: Path,
    templateDir: Path,
    archiveJsonPath: Path,
    archiveHtmlPath: Path,
    generatedAt: str,
    version: str,
) -> None:
    """Rebuild (not append) docs/api/v1/reports/index.json + docs/reports/index.html.

    Scans docs/reports/*/index.html and orders newest first by directory name.
    Rebuilds from scratch so a deleted report gets pruned in the same pass.
    """
    reportsDir = docsRoot / "reports"
    entries: list[dict] = []
    if reportsDir.exists():
        candidates = sorted(reportsDir.glob("*/index.html"))
        for htmlPath in candidates:
            label = htmlPath.parent.name
            if label == "DRAFT":
                continue
            if not re.match(r"^\d{4}-\d{2}$", label):
                continue
            jsonPath = docsRoot / "api" / "v1" / "reports" / f"{label}.json"
            report = _readJson(jsonPath)
            entries.append({
                "reportId": label,
                "url": f"/reports/{label}/",
                "json": f"/api/v1/reports/{label}.json",
                "generatedAt": report.get("generatedAt"),
                "salvageLayer": report.get("salvageLayer"),
                "isoYear": report.get("isoYear"),
                "isoWeek": report.get("isoWeek"),
            })
    entries.sort(key=lambda e: e["reportId"], reverse=True)

    archiveJsonPath.parent.mkdir(parents=True, exist_ok=True)
    archiveJsonPath.write_text(
        json.dumps({
            "schemaVersion": "1.0.0",
            "generatedAt": generatedAt,
            "reports": entries,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Landing HTML — thin Jinja render, same tokens.css conventions.
    env = _jinjaEnv(templateDir)
    tpl = env.get_template("archive.html.j2")
    archiveHtmlPath.parent.mkdir(parents=True, exist_ok=True)
    archiveHtmlPath.write_text(
        tpl.render(reports=entries, generatedAt=generatedAt, version=version),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# run() — the main entrypoint (also invoked from build_docs.py)
# ---------------------------------------------------------------------------


def _isoNow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(
    apiDir: Path,
    docsRoot: Path,
    publishFlag: bool,
    now: datetime | None = None,
) -> dict:
    """Execute one full content-engine cycle.

    Returns the assembled report dict (for tests / callers). Writes:
      - draft markdown if publishFlag is False
      - canonical JSON + public HTML + archive rebuild if publishFlag is True
    """
    from synthesizer import synthesize  # noqa: WPS433 — local import to avoid cycle

    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

    year, week = isoYearWeek(now)
    generatedAt = _isoNow()
    version = _readVersion()

    # 1. Load + shape sections (mechanical, always succeeds on valid data).
    trending = renderTrendingSection(loadTrending(apiDir, "7d", top=5))
    ascended = renderAscendedSection(loadAscended(apiDir, top=5))
    contested = renderContestedSection(loadContested(apiDir, top=3))

    sections = {
        "trending": trending,
        "ascended": ascended,
        "contested": contested,
    }

    # 2. Assemble a first-pass report so synthesize() has a stable input.
    firstPass = assembleReport(year, week, sections, "L3", generatedAt, version)

    # 3. L1 → L2 → L3 salvage — synthesize() reports its own layer flag.
    try:
        report, layerFlag = synthesize(firstPass)
    except ValueError as exc:
        # L3 refused because ALL sections are empty. Emit a stub report so
        # the URL still exists — the header tells readers no data was available.
        emptyStub = assembleReport(
            year, week, sections, "L3-empty", generatedAt, version
        )
        emptyStub["notice"] = f"No trending data available: {exc}"
        report, layerFlag = emptyStub, "L3-empty"

    report["salvageLayer"] = layerFlag

    # 4. Resolve publish target and write.
    targets = resolvePublishTarget(year, week, publishFlag, docsRoot)
    templateDir = Path(__file__).resolve().parent / "templates"

    if targets["mode"] == "draft":
        renderDraftMarkdown(report, templateDir, targets["draftMd"])
        print(f"[content-engine] wrote DRAFT: {targets['draftMd']}", file=sys.stderr)
    else:
        writeCanonicalJson(report, targets["canonicalJson"])
        renderHtml(report, templateDir, targets["publicHtml"])
        _rebuildArchive(
            docsRoot,
            templateDir,
            targets["archiveJson"],
            targets["archiveHtml"],
            generatedAt,
            version,
        )
        print(
            f"[content-engine] published: "
            f"{targets['canonicalJson']} + {targets['publicHtml']} "
            f"(layer={layerFlag})",
            file=sys.stderr,
        )

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolveFlag(rawValue: str | None, envValue: str | None) -> bool:
    """Truthy iff either CLI flag or env var is set to '1' (case-insensitive)."""
    for v in (rawValue, envValue):
        if v is None:
            continue
        if str(v).strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Gaia's weekly Content Engine report.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "docs"),
        help="Docs root directory (defaults to <repo>/docs). "
             "The report lands under <out-dir>/reports/ and <out-dir>/api/v1/reports/.",
    )
    parser.add_argument(
        "--publish",
        default=None,
        help="0 (default via env) → DRAFT. 1 → canonical + HTML + archive.",
    )
    parser.add_argument(
        "--dry-run",
        default=None,
        help="Write to this tempdir instead of --out-dir. Implies publish=1 "
             "so the full artefact set is emitted.",
    )
    parser.add_argument(
        "--api-dir",
        default=str(ROOT / "docs" / "api" / "v1"),
        help="Directory containing trending/{7d,ascended,contested}.json.",
    )
    args = parser.parse_args(argv)

    apiDir = Path(args.api_dir).resolve()

    if args.dry_run:
        dryRoot = Path(args.dry_run).resolve()
        dryRoot.mkdir(parents=True, exist_ok=True)
        # Dry-run writes a full publish tree so the operator sees every file.
        run(apiDir, dryRoot, publishFlag=True)
        return 0

    docsRoot = Path(args.out_dir).resolve()
    publishFlag = _resolveFlag(args.publish, os.environ.get("GAIA_CONTENT_ENGINE_PUBLISH"))
    run(apiDir, docsRoot, publishFlag=publishFlag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
