"""
tests/test_seo.py — W5 SEO surface smoke tests.

Covers:
  - sitemap contains all required routes
  - JSON-LD injection is idempotent
  - docs/okf/index.json is deterministic (same inputs → same JSON)
  - robots.txt allows /skills/ and /benchmarks/
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
SCRIPTS_DIR = REPO_ROOT / "scripts"


# ── helpers ───────────────────────────────────────────────────────────────────

def _run(script: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


# ── sitemap tests ─────────────────────────────────────────────────────────────

def test_sitemap_contains_all_known_routes():
    """docs/sitemap.xml must contain all six required W5 routes."""
    sitemap_path = DOCS_DIR / "sitemap.xml"
    assert sitemap_path.exists(), "docs/sitemap.xml missing"
    content = sitemap_path.read_text(encoding="utf-8")
    required = [
        "https://gaia.tiongson.co/skills/",
        "https://gaia.tiongson.co/benchmarks/",
        "https://gaia.tiongson.co/reports/",
        "https://gaia.tiongson.co/api/",
        "https://gaia.tiongson.co/heroes/",
        "https://gaia.tiongson.co/trending/",
    ]
    for url in required:
        assert url in content, f"sitemap.xml missing expected URL: {url}"


def test_sitemap_script_check_passes():
    """generateSitemap.py --check should exit 0 (sitemap is up to date)."""
    result = _run("generateSitemap.py", "--check")
    assert result.returncode == 0, (
        f"generateSitemap.py --check failed:\n{result.stdout}\n{result.stderr}"
    )


def test_sitemap_has_skills_priority():
    """The /skills/ entry should carry priority 0.8."""
    sitemap_path = DOCS_DIR / "sitemap.xml"
    content = sitemap_path.read_text(encoding="utf-8")
    # Find the skills url block
    m = re.search(
        r"<url>\s*<loc>https://gaia\.tiongson\.co/skills/</loc>.*?</url>",
        content,
        re.DOTALL,
    )
    assert m, "/skills/ not found in sitemap"
    assert "<priority>0.8</priority>" in m.group(0), "/skills/ priority should be 0.8"


# ── JSON-LD tests ─────────────────────────────────────────────────────────────

def test_jsonld_check_passes():
    """injectJsonLd.py --check should pass after the injection pass already ran."""
    result = _run("injectJsonLd.py", "--check")
    assert result.returncode == 0, (
        f"injectJsonLd.py --check failed:\n{result.stdout}\n{result.stderr}"
    )


def test_jsonld_idempotent():
    """Running injectJsonLd.py twice produces the same output (idempotent)."""
    import tempfile, shutil

    # Copy docs to a temp dir, inject once, inject again, compare
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_docs = Path(tmpdir) / "docs"
        shutil.copytree(str(DOCS_DIR), str(tmp_docs))

        # Helper: inject into the temp docs dir via direct module call
        def _inject_dir(docs_path: Path):
            import importlib.util, types
            spec = importlib.util.spec_from_file_location(
                "injectJsonLd", str(SCRIPTS_DIR / "injectJsonLd.py")
            )
            mod = importlib.util.module_from_spec(spec)
            # Override DOCS_DIR in the module
            spec.loader.exec_module(mod)
            # Patch the module's DOCS_DIR and re-run main
            orig = mod.DOCS_DIR
            mod.DOCS_DIR = docs_path
            mod.main([])
            mod.DOCS_DIR = orig

        _inject_dir(tmp_docs)
        # Capture state after first injection
        state1 = {
            str(p.relative_to(tmp_docs)): p.read_text(encoding="utf-8")
            for p in sorted(tmp_docs.rglob("*.html"))
            if "data-injector=\"gaia-json-ld\"" in p.read_text(encoding="utf-8")
        }

        _inject_dir(tmp_docs)
        # Capture state after second injection
        state2 = {
            str(p.relative_to(tmp_docs)): p.read_text(encoding="utf-8")
            for p in sorted(tmp_docs.rglob("*.html"))
            if "data-injector=\"gaia-json-ld\"" in p.read_text(encoding="utf-8")
        }

    assert state1 == state2, "JSON-LD injection is NOT idempotent (second pass changed output)"
    assert len(state1) > 0, "Expected at least one HTML file with JSON-LD after injection"


def test_jsonld_home_has_website_type():
    """docs/index.html should contain a WebSite JSON-LD block."""
    home = DOCS_DIR / "index.html"
    assert home.exists()
    content = home.read_text(encoding="utf-8")
    assert "data-injector=\"gaia-json-ld\"" in content, "docs/index.html missing JSON-LD block"
    assert '"@type": "WebSite"' in content, "docs/index.html should have WebSite schema type"


# ── OKF index tests ───────────────────────────────────────────────────────────

def test_okf_index_exists():
    """docs/okf/index.json should exist after buildSkillsIndex.py ran."""
    assert (DOCS_DIR / "okf" / "index.json").exists(), "docs/okf/index.json missing"


def test_okf_index_deterministic():
    """buildSkillsIndex.py --check exits 0 (index matches what would be generated)."""
    result = _run("buildSkillsIndex.py", "--check")
    assert result.returncode == 0, (
        f"buildSkillsIndex.py --check failed:\n{result.stdout}\n{result.stderr}"
    )


def test_okf_index_shape():
    """docs/okf/index.json matches expected schema shape."""
    index_path = DOCS_DIR / "okf" / "index.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data.get("schemaVersion") == "1.0.0", "schemaVersion should be '1.0.0'"
    assert data.get("generatedAt") is None, "generatedAt should be null (frozen)"
    assert isinstance(data.get("families"), list), "families should be a list"
    family_ids = [f["id"] for f in data["families"]]
    for required_id in ["basic", "extra", "ultimate"]:
        assert required_id in family_ids, f"Expected family '{required_id}' in index.json"
    for family in data["families"]:
        assert "count" in family
        assert "skills" in family
        assert family["count"] == len(family["skills"])


# ── robots.txt tests ──────────────────────────────────────────────────────────

def test_robots_allows_skills():
    """docs/robots.txt must allow /skills/."""
    robots = (DOCS_DIR / "robots.txt").read_text(encoding="utf-8")
    assert "Allow: /skills/" in robots, "robots.txt missing 'Allow: /skills/'"


def test_robots_allows_benchmarks():
    """docs/robots.txt must allow /benchmarks/."""
    robots = (DOCS_DIR / "robots.txt").read_text(encoding="utf-8")
    assert "Allow: /benchmarks/" in robots, "robots.txt missing 'Allow: /benchmarks/'"


def test_robots_skills_not_disallowed():
    """robots.txt must not disallow /skills/."""
    robots = (DOCS_DIR / "robots.txt").read_text(encoding="utf-8")
    assert "Disallow: /skills/" not in robots, "robots.txt has 'Disallow: /skills/'"
