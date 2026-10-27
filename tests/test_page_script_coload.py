"""Every page that loads skill-explorer.js must also load trust-lifecycle.js.

skill-explorer.js renders the Yggdrasil IV trust lifecycle into #se-tm by
calling window.GaiaTrustLifecycle; when the module is absent the section is
silently empty. The module must come first so it is defined before the
explorer can open (including the ?tree=1 auto-open path).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCRIPT = re.compile(r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)


def scriptSources(html: str) -> list[str]:
    """Script srcs in document order, ignoring query strings."""
    return [match.group(1).split("?", 1)[0] for match in SCRIPT.finditer(html)]


def indexOfScript(sources: list[str], name: str) -> int:
    for position, src in enumerate(sources):
        if src.rsplit("/", 1)[-1] == name:
            return position
    return -1


def explorerPages() -> list[Path]:
    pages = []
    for path in sorted(DOCS.rglob("*.html")):
        if indexOfScript(scriptSources(path.read_text(encoding="utf-8")), "skill-explorer.js") >= 0:
            pages.append(path)
    return pages


def test_explorer_pages_are_discovered() -> None:
    names = {page.relative_to(DOCS).as_posix() for page in explorerPages()}
    # Guard against the scan silently matching nothing.
    assert {"index.html", "named/index.html", "badges/index.html", "meta.html"} <= names
    assert any(name.startswith("u/") for name in names)


def test_every_skill_explorer_page_loads_trust_lifecycle_first() -> None:
    problems = []
    for page in explorerPages():
        sources = scriptSources(page.read_text(encoding="utf-8"))
        lifecycle = indexOfScript(sources, "trust-lifecycle.js")
        explorer = indexOfScript(sources, "skill-explorer.js")
        rel = page.relative_to(DOCS).as_posix()
        if lifecycle < 0:
            problems.append(f"{rel}: missing trust-lifecycle.js")
        elif lifecycle > explorer:
            problems.append(f"{rel}: trust-lifecycle.js must load before skill-explorer.js")
    assert not problems, "\n".join(problems)


def test_profile_generator_template_loads_trust_lifecycle_first() -> None:
    """Profiles are generated; fix the template or the next regeneration reverts the pages."""
    source = (ROOT / "scripts" / "generateProfilePages.py").read_text(encoding="utf-8")
    sources = scriptSources(source)
    lifecycle = indexOfScript(sources, "trust-lifecycle.js")
    explorer = indexOfScript(sources, "skill-explorer.js")
    assert 0 <= lifecycle < explorer
