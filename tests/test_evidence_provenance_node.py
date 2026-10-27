"""Run the evidence-provenance Node suite under pytest, and pin where it is wired.

CI runs `pytest tests/`; nothing else invokes `node --test` for this file.
Evidence rows must read the same on every surface, so the static checks below
keep the surfaces on the shared renderer and keep it loaded wherever the Skill
Explorer renders evidence cards.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCRIPT = re.compile(r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)


def scriptNames(html: str) -> list[str]:
    return [match.group(1).split("?", 1)[0].rsplit("/", 1)[-1] for match in SCRIPT.finditer(html)]


def test_evidence_provenance_node_suite() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the evidence-provenance browser-module suite")
    result = subprocess.run(
        [node, "--test", str(ROOT / "tests" / "test_evidence_provenance.js")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]


def test_every_skill_explorer_page_loads_the_provenance_renderer() -> None:
    problems = []
    for page in sorted(DOCS.rglob("*.html")):
        names = scriptNames(page.read_text(encoding="utf-8"))
        if "skill-explorer.js" in names and "evidence-provenance.js" not in names:
            problems.append(page.relative_to(DOCS).as_posix())
    assert not problems, "missing evidence-provenance.js: " + ", ".join(problems)


@pytest.mark.parametrize("page", ["evidence/index.html", "named/report.html"])
def test_evidence_pages_load_the_provenance_renderer_first(page: str) -> None:
    names = scriptNames((DOCS / page).read_text(encoding="utf-8"))
    assert "evidence-provenance.js" in names, page
    consumer = "evidence-library.js" if page.startswith("evidence/") else "ui.js"
    assert names.index("evidence-provenance.js") < names.index(consumer)


def test_profile_generator_template_loads_the_provenance_renderer() -> None:
    source = (ROOT / "scripts" / "generateProfilePages.py").read_text(encoding="utf-8")
    assert "evidence-provenance.js" in scriptNames(source)


@pytest.mark.parametrize("name", ["skill-explorer.js", "evidence-library.js"])
def test_card_surfaces_use_the_shared_renderer_and_hide_nothing(name: str) -> None:
    source = (DOCS / "js" / name).read_text(encoding="utf-8")
    assert "GaiaEvidenceProvenance" in source
    # The old per-surface renderers hid these evaluators and linked raw `source`.
    assert "ev.evaluator !== 'unknown'" not in source
    assert "esc(ev.source||'#')" not in source and "esc(ev.source || '#')" not in source


def test_skill_explorer_does_not_dedupe_the_displayed_rows() -> None:
    source = (DOCS / "js" / "skill-explorer.js").read_text(encoding="utf-8")
    body = source[source.index("var combinedEvidence = [];"):source.index("var TM_SCORE = window.TM_CONFIG;")]
    # Display list is pushed unconditionally; only the scoring baseline dedupes.
    assert "combinedEvidence.push(tagged);" in body
    assert body.index("combinedEvidence.push(tagged);") > body.index("_duplicate: true")
    assert "scoringEvidence.push(tagged)" in body
    assert body.count("combinedEvidence.push(") == 1


def test_evidence_index_is_cache_busted_by_the_docs_build() -> None:
    build = (ROOT / "scripts" / "build_docs.py").read_text(encoding="utf-8")
    assert '"evidence/index.html"' in build


def test_duplicates_are_marked_on_every_surface() -> None:
    explorer = (DOCS / "js" / "skill-explorer.js").read_text(encoding="utf-8")
    library = (DOCS / "js" / "evidence-library.js").read_text(encoding="utf-8")
    report = (DOCS / "named" / "report.html").read_text(encoding="utf-8")
    assert "_duplicate: true" in explorer
    assert "_duplicate: true" in library
    assert "markDuplicates(evidence)" in report and "renderDuplicate" in report


def test_missing_type_is_not_defaulted_to_a_real_type_on_any_surface() -> None:
    report = (DOCS / "named" / "report.html").read_text(encoding="utf-8")
    library = (DOCS / "js" / "evidence-library.js").read_text(encoding="utf-8")
    assert "ev['class']" not in report
    assert "type: ev.typeRecorded" in library
