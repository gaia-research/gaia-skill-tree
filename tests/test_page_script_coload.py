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


def pagesLoading(script: str) -> list[Path]:
    return [page for page in sorted(DOCS.rglob("*.html"))
            if indexOfScript(scriptSources(page.read_text(encoding="utf-8")), script) >= 0]


def test_challenge_surface_pages_are_discovered() -> None:
    names = {page.relative_to(DOCS).as_posix() for page in pagesLoading("challenge-surfaces.js")}
    # Guard against the scan silently matching nothing.
    assert {"trust/challenges/index.html", "trust/leaderboard/index.html", "trust/ledger/index.html"} <= names


def test_every_challenge_surface_page_loads_its_dependencies_in_order() -> None:
    """challenge-surfaces.js draws marks and toggletips through GaiaTrustLifecycle and fails closed
    without it, so the lifecycle module must come first; a host script must come after both."""
    problems = []
    for page in pagesLoading("challenge-surfaces.js"):
        text = page.read_text(encoding="utf-8")
        sources = scriptSources(text)
        rel = page.relative_to(DOCS).as_posix()
        lifecycle = indexOfScript(sources, "trust-lifecycle.js")
        surfaces = indexOfScript(sources, "challenge-surfaces.js")
        if lifecycle < 0:
            problems.append(f"{rel}: missing trust-lifecycle.js")
        elif lifecycle > surfaces:
            problems.append(f"{rel}: trust-lifecycle.js must load before challenge-surfaces.js")
        for host in ("leaderboard.js", "ledger.js", "challenges.js"):
            position = indexOfScript(sources, host)
            if position >= 0 and position < surfaces:
                problems.append(f"{rel}: {host} must load after challenge-surfaces.js")
        if "challenge-surfaces.css" not in text:
            problems.append(f"{rel}: missing challenge-surfaces.css")
    assert not problems, "\n".join(problems)


def test_challenges_page_is_wired_into_nav_mounts_and_cache_busting() -> None:
    page = (DOCS / "trust" / "challenges" / "index.html").read_text(encoding="utf-8")
    sources = scriptSources(page)
    assert 0 <= indexOfScript(sources, "mounts.js") < indexOfScript(sources, "site-nav.js")
    mounts = (DOCS / "js" / "mounts.js").read_text(encoding="utf-8")
    assert "'trust'" in mounts  # /trust/challenges/ is served under the existing trust mount
    build = (ROOT / "scripts" / "build_docs.py").read_text(encoding="utf-8")
    assert '"trust/challenges/index.html"' in build
    assert "?v=" in page and "challenge-surfaces.js?v=" in page


def test_challenges_page_has_the_held_heading_and_no_contested_wording_around_it() -> None:
    page = (DOCS / "trust" / "challenges" / "index.html").read_text(encoding="utf-8")
    held = page.split('id="csHeld"', 1)[1].split("</section>", 1)[0]
    assert "Admission held, no effect on standing" in held
    assert "under review" not in held
    assert "contested" not in held.lower()
