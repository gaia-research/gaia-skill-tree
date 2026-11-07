"""Regression tests for user-facing post report rendering."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "add_post.py"


def _load_add_post():
    spec = importlib.util.spec_from_file_location("add_post", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_md_to_html_preserves_accessible_figure_as_block():
    """A report's SVG figure must not be wrapped in a paragraph."""
    figure = (
        '<figure id="decision-funnel">\n'
        '  <img src="assets/chart.svg" alt="Decision outcomes" />\n'
        '  <figcaption>Figure 1. Outcomes.</figcaption>\n'
        "</figure>"
    )

    rendered = _load_add_post().md_to_html(f"Before the figure.\n\n{figure}\n\nAfter it.")

    assert "<p>Before the figure.</p>" in rendered
    assert figure in rendered
    assert "<p><figure" not in rendered
    assert "<p>After it.</p>" in rendered


def test_report_tables_remain_semantic_and_are_keyboard_scrollable():
    rendered = _load_add_post().md_to_html(
        "| Case | Challenger | Compared against | Runner outcome | Meta verification | Admitted |\n"
        "|---|---|---|---|---|---|\n"
        "| C1 | Graphify | graft caller lookup | Contradicted (a tie) | Upheld | No |"
    )

    assert '<div class="report-table-scroll" role="region"' in rendered
    assert 'aria-label="Scrollable report table" tabindex="0">' in rendered
    assert "<table><thead><tr><th>Case</th>" in rendered
    assert "<tbody><tr><td>C1</td>" in rendered
    assert rendered.index('<div class="report-table-scroll"') < rendered.index("<table>")
    assert rendered.endswith("</table></div>")


def test_report_html_has_no_trailing_whitespace_without_chart():
    rendered = _load_add_post().render_report_html(
        title="Test report",
        author="Gaia Research",
        display_date="September 25, 2026",
        abstract="A short abstract.",
        body_html="<p>Body.</p>",
        download_name="test-report.html",
    )

    assert ".paper-journal-header {" in rendered
    assert ".paper-journal-header {{" not in rendered
    assert ".report-table-scroll { max-width: 100%; overflow-x: auto;" in rendered
    assert ".report-table-scroll:focus-visible" in rendered
    assert "table { width: max-content; min-width: 100%;" in rendered
    assert "overflow-wrap: break-word;" in rendered
    assert "word-break: break-word;" in rendered
    assert all(line == line.rstrip() for line in rendered.splitlines())


def test_include_directive_inlines_a_fragment_as_a_block(tmp_path):
    (tmp_path / "figures.frag").write_text('<script id="fig-data">{"a":1}</script>\n', encoding="utf-8")
    module = _load_add_post()
    module.INCLUDE_BASE = tmp_path

    rendered = module.md_to_html("Before.\n\n{{include: figures.frag}}\n\nAfter.")

    assert '<script id="fig-data">{"a":1}</script>' in rendered
    assert "<p><script" not in rendered
    assert "<p>Before.</p>" in rendered
    assert "<p>After.</p>" in rendered


def test_include_directive_cannot_escape_the_source_directory(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (tmp_path / "secret.html").write_text("<p>outside</p>", encoding="utf-8")
    module = _load_add_post()
    module.INCLUDE_BASE = source

    for target in ("../secret.html", str(tmp_path / "secret.html")):
        try:
            module.md_to_html("{{include: " + target + "}}")
        except ValueError as error:
            assert "escapes the source directory" in str(error)
        else:
            raise AssertionError(f"include of {target} should have been refused")


def test_fig_directive_emits_a_mount_and_ignores_unsafe_names():
    module = _load_add_post()

    rendered = module.md_to_html("{{fig: grade-ceiling}}")
    assert '<div class="ygg-fig" data-fig="grade-ceiling"></div>' in rendered

    unsafe = module.md_to_html('{{fig: bad"name}}')
    assert "ygg-fig" not in unsafe


def test_post_and_report_escaping_markup(tmp_path):
    module = _load_add_post()

    post = {
        "title": '<script>alert(1)</script> "hello" & \'world\'',
        "summary": '<img src=x onerror=1> <b>bold</b>',
        "label": '<script>alert("label")</script>',
        "url": 'https://example.com/test?a=1&b=2"onload="alert(1)',
    }

    # 1. _pmq_card escaping
    rendered_pmq = module._pmq_card(post)
    assert "<script>" not in rendered_pmq
    assert "<img" not in rendered_pmq
    assert "<b>" not in rendered_pmq
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered_pmq
    assert "&lt;img src=x onerror=1&gt;" in rendered_pmq
    assert "&lt;b&gt;bold&lt;/b&gt;" in rendered_pmq
    assert "&amp;" in rendered_pmq
    assert 'href="https://example.com/test?a=1&amp;b=2&quot;onload=&quot;alert(1)"' in rendered_pmq

    # 2. _meta_card escaping
    meta_post = {
        "title": '<script>alert(1)</script> "hello" & \'world\'',
        "summary": '<img src=x onerror=1> <b>bold</b>',
        "url": 'https://example.com/test.html?a=1&b=2"onclick="alert(1)',
        "date": "2026-05-25",
    }
    rendered_meta = module._meta_card(meta_post)
    assert "<script>" not in rendered_meta
    assert "<img" not in rendered_meta
    assert "<b>" not in rendered_meta
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered_meta
    assert "&lt;img src=x onerror=1&gt;" in rendered_meta
    assert "&lt;b&gt;bold&lt;/b&gt;" in rendered_meta
    assert 'data-report-title="&lt;script&gt;alert(1)&lt;/script&gt; &quot;hello&quot; &amp; &#x27;world&#x27;"' in rendered_meta
    assert 'download="test.html?a=1&amp;b=2&quot;onclick=&quot;alert(1)"' in rendered_meta

    # 3. patch_index hero button escaping
    tmp_index = tmp_path / "index.html"
    tmp_index.write_text(
        "<!-- gaia-posts-start --><!-- gaia-posts-end -->\n"
        "<!-- gaia-hero-post-start --><!-- gaia-hero-post-end -->\n",
        encoding="utf-8",
    )
    saved_index = module.INDEX_FILE
    try:
        module.INDEX_FILE = tmp_index
        module.patch_index(
            posts=[post],
            hero_url='https://example.com/hero?a=1&b=2"onclick="alert(1)',
            hero_label='<script>alert("hero")</script> "hero" & \'hero\'',
        )
        patched = tmp_index.read_text(encoding="utf-8")
        assert "<script>" not in patched
        assert "<img" not in patched
        assert "&lt;script&gt;alert(&quot;hero&quot;)&lt;/script&gt;" in patched
        assert 'href="https://example.com/hero?a=1&amp;b=2&quot;onclick=&quot;alert(1)"' in patched
        assert 'aria-label="View &lt;script&gt;alert(&quot;hero&quot;)&lt;/script&gt; &quot;hero&quot; &amp; &#x27;hero&#x27;"' in patched
    finally:
        module.INDEX_FILE = saved_index

    # 4. render_report_html escaping
    rendered_report = module.render_report_html(
        title='<script>alert(1)</script> "hello" & \'world\'',
        author='<script>alert(1)</script> "Author"',
        display_date="May 25, 2026",
        abstract='<img src=x onerror=1> <b>bold</b> "abstract"',
        body_html="<p>Body</p>",
        download_name='test"onload="alert(1).html',
        back_href='../../index.html?a=1&b="2"',
    )
    assert "<script>alert" not in rendered_report
    assert "<img src=x" not in rendered_report
    assert "<b>bold</b>" not in rendered_report
    assert "&lt;img src=x onerror=1&gt;" in rendered_report
    assert "<title>&lt;script&gt;alert(1)&lt;/script&gt; &quot;hello&quot; &amp; &#x27;world&#x27; — Gaia</title>" in rendered_report
    assert "<h1>&lt;script&gt;alert(1)&lt;/script&gt; &quot;hello&quot; &amp; &#x27;world&#x27;</h1>" in rendered_report
    assert '<div class="authors">&lt;script&gt;alert(1)&lt;/script&gt; &quot;Author&quot;</div>' in rendered_report
    assert '<div class="abstract-content">&lt;img src=x onerror=1&gt; &lt;b&gt;bold&lt;/b&gt; &quot;abstract&quot;</div>' in rendered_report
    assert 'download="test&quot;onload=&quot;alert(1).html"' in rendered_report
    assert '<a href="../../index.html?a=1&amp;b=&quot;2&quot;">← Back to Gaia</a>' in rendered_report

    # 5. _CHANGELOG_JS DOM handling uses safe textContent assignments
    assert "header.textContent =" in module._CHANGELOG_JS
    assert "title.textContent = ev.skillName || '';" in module._CHANGELOG_JS
    assert "details.textContent = ev.details || '';" in module._CHANGELOG_JS
    assert ".innerHTML = `" not in module._CHANGELOG_JS


GOLDEN_REPORT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Autonomous Verification Pipelines — Gaia</title>
  <link rel="icon" type="image/svg+xml" href="../../assets/marks/diamond-seal.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">

  <style>
    :root {
      --paper-bg: #ffffff;
      --paper-text: #111111;
      --paper-muted: #666666;
      --accent: #ef4444;
      --font-serif: 'EB Garamond', Georgia, serif;
      --font-sans: 'Bricolage Grotesque', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; }
    body {
      background: #f4f4f2;
      color: var(--paper-text);
      font-family: var(--font-serif);
      font-variant-numeric: oldstyle-nums;
      line-height: 1.6;
      margin: 0;
      padding: 6rem 1rem;
      -webkit-font-smoothing: antialiased;
      overflow-wrap: break-word;
    }
    .paper {
      background: var(--paper-bg);
      max-width: 820px;
      margin: 0 auto;
      padding: 6rem 7rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 10px 40px rgba(0,0,0,0.02);
      position: relative;
      counter-reset: section;
      overflow-wrap: break-word;
    }
    header { text-align: center; margin-bottom: 5rem; }
    .paper-journal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 1.5rem;
      margin-bottom: 3rem;
      border-bottom: 1px solid #e0e0dc;
    }
    .paper-journal-logo {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      text-decoration: none;
      color: #c8a84b;
      font-family: var(--font-sans);
      font-weight: 600;
      font-size: 0.9rem;
      letter-spacing: 0.04em;
    }
    .paper-journal-logo img {
      filter: invert(72%) sepia(40%) saturate(600%) hue-rotate(5deg) brightness(95%);
    }
    .paper-journal-series {
      font-family: var(--font-sans);
      font-size: 0.75rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: #999;
    }
    h1 {
      font-family: var(--font-serif);
      font-size: 2.6rem;
      font-weight: 500;
      margin-bottom: 1.5rem;
      line-height: 1.1;
      letter-spacing: -0.01em;
    }
    .authors {
      font-family: var(--font-serif);
      font-variant-caps: small-caps;
      font-size: 1.2rem;
      margin-bottom: 0.5rem;
      letter-spacing: 0.02em;
    }
    .date { font-family: var(--font-serif); font-size: 1.1rem; color: var(--paper-text); }
    .abstract { margin: 4rem 0; padding: 0 3rem; }
    .abstract-title {
      font-family: var(--font-sans);
      font-weight: 700;
      text-align: center;
      margin-bottom: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.75rem;
      color: var(--paper-muted);
    }
    .abstract-content { font-style: italic; text-align: justify; hyphens: auto; font-size: 1.05rem; line-height: 1.5; }
    h2 {
      font-family: var(--font-sans);
      font-size: 0.9rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-top: 4rem;
      margin-bottom: 1.5rem;
      counter-increment: section;
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
    }
    h2::before { content: counter(section) ". "; }
    h3 { font-family: var(--font-serif); font-size: 1.3rem; font-weight: 600; margin-top: 2.5rem; margin-bottom: 1rem; }
    p { text-align: justify; margin-bottom: 1.5rem; hyphens: auto; overflow-wrap: break-word; }
    .two-column { display: grid; grid-template-columns: 1fr 1fr; gap: 3rem; margin: 2.5rem 0; }
    ul { padding-left: 1.2rem; list-style-type: square; }
    li { margin-bottom: 0.6rem; }
    code { font-family: var(--font-mono); background: #f7f7f7; padding: 0.15rem 0.35rem; font-size: 0.85em; border: 1px solid #eee; word-break: break-word; }
    pre { background: #f7f7f7; border: 1px solid #eee; padding: 1.2rem 1.5rem; overflow-x: auto; margin: 2rem 0; }
    pre code { background: none; border: none; padding: 0; font-size: 0.85rem; }
    blockquote { border-left: 3px solid #c8a84b; margin: 2rem 0; padding: 1rem 1.5rem; background: #fafaf8; color: #444; font-style: italic; }
    .report-table-scroll { max-width: 100%; overflow-x: auto; overscroll-behavior-inline: contain; -webkit-overflow-scrolling: touch; }
    .report-table-scroll:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
    table { width: max-content; min-width: 100%; border-collapse: collapse; margin: 3rem 0; font-family: var(--font-serif); font-size: 1rem; }
    thead tr { border-top: 2px solid var(--paper-text); border-bottom: 1px solid var(--paper-text); }
    th { font-weight: 600; text-align: left; padding: 0.8rem 0.5rem; font-variant-caps: small-caps; }
    td { padding: 0.8rem 0.5rem; border-bottom: 0.5px solid #eee; vertical-align: top; }
    tbody tr:last-child { border-bottom: 2px solid var(--paper-text); }
    .chart-container { margin: 4.5rem -2rem; padding: 2.5rem; background: #ffffff; border: 1px solid #eee; }
    .chart-caption { text-align: center; font-size: 0.85rem; color: var(--paper-muted); margin-top: 1.5rem; line-height: 1.4; }
    .references { margin-top: 6rem; padding-top: 3rem; border-top: 1px solid #eee; }
    .ref-item { font-size: 0.9rem; margin-bottom: 1.2rem; text-indent: -1.8rem; padding-left: 1.8rem; text-align: left; }
    .footer-nav { margin-top: 5rem; text-align: center; font-family: var(--font-sans); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; }
    .footer-nav a { color: var(--paper-text); text-decoration: none; border-bottom: 1px solid #ddd; padding-bottom: 2px; transition: border-color 0.2s; }
    .footer-nav a:hover { border-color: var(--accent); }
    .floating-cluster {
      position: fixed; top: 2rem; right: 2rem; z-index: 1000;
      display: flex; align-items: center; gap: 0.5rem;
    }
    .pja-btn {
      background: #fff; border: 1px solid #d0d0cc; border-radius: 0; color: #888;
      cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
      width: 2rem; height: 2rem; padding: 0; text-decoration: none;
      transition: color 0.15s, border-color 0.15s; flex-shrink: 0;
    }
    .pja-btn:hover { color: #111; border-color: #111; }
    .pja-btn.copied { color: #16a34a; border-color: #16a34a; }
    .pja-btn svg { width: 15px; height: 15px; display: block; }
    .floating-changelog-btn {
      background: #000; color: #fff; border: none;
      padding: 0.8rem 1.4rem;
      font-family: var(--font-sans); font-weight: 700; font-size: 0.7rem;
      text-transform: uppercase; letter-spacing: 0.15em; cursor: pointer;
      box-shadow: 0 10px 30px rgba(0,0,0,0.15);
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .floating-changelog-btn:hover { transform: translateY(-2px); box-shadow: 0 15px 40px rgba(0,0,0,0.2); background: #111; }
    .meta-sidebar {
      position: fixed; top: 0; right: 0; bottom: 0; width: 400px;
      background: #000; color: #fff; z-index: 2000;
      transform: translateX(100%); transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex; flex-direction: column; border-left: 1px solid #222;
    }
    .meta-sidebar.open { transform: translateX(0); }
    .ms-header { padding: 1.5rem; border-bottom: 1px solid #222; display: flex; justify-content: space-between; align-items: center; }
    .ms-header h2 { margin: 0 !important; border: none !important; font-size: 1.2rem !important; font-family: 'EB Garamond', serif !important; counter-reset: none !important; }
    .ms-header h2::before { content: none !important; }
    .ms-body { flex: 1; overflow-y: auto; padding: 1.5rem; font-family: 'Bricolage Grotesque', sans-serif; }
    .ms-close { background: none; border: none; color: #666; font-size: 1.5rem; cursor: pointer; }
    @media (max-width: 768px) {
      .paper { padding: 3rem 2rem; }
      body { padding: 1rem 0; }
      .floating-cluster { top: 0.75rem; right: 0.75rem; }
      .floating-changelog-btn { padding: 0.4rem 0.8rem; font-size: 0.7rem; }
      .meta-sidebar { width: 100%; }
    }
  </style>
</head>
<body>

  <div class="floating-cluster">
    <button type="button" class="pja-btn" id="reportShareBtn" aria-label="Share report">
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="15" cy="5" r="2"/><circle cx="5" cy="10" r="2"/><circle cx="15" cy="15" r="2"/>
        <line x1="7" y1="9" x2="13" y2="6"/><line x1="7" y1="11" x2="13" y2="14"/>
      </svg>
    </button>
    <a href="report.html" download="report.html" class="pja-btn" aria-label="Download report">
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M10 3v9m0 0l-3.5-3.5M10 12l3.5-3.5"/><path d="M4 15h12"/>
      </svg>
    </a>
    <button type="button" class="pja-btn" id="reportCopyLinkBtn" aria-label="Copy link">
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M8.5 11.5a4.5 4.5 0 006.364 0l2-2a4.5 4.5 0 00-6.364-6.364L9 4.636"/>
        <path d="M11.5 8.5a4.5 4.5 0 00-6.364 0l-2 2a4.5 4.5 0 006.364 6.364L11 15.364"/>
      </svg>
    </button>
    <button type="button" class="floating-changelog-btn" id="viewChangelogBtn">View Changelog</button>
  </div>

  <aside id="metaSidebar" class="meta-sidebar">
    <div class="ms-header">
      <h2>Meta Changelog</h2>
      <button type="button" class="ms-close" id="closeChangelogBtn">✕</button>
    </div>
    <div class="ms-body" id="changelogBody">
      <div style="color:#666;font-size:0.9rem">Loading Skill Tree history…</div>
    </div>
  </aside>

  <article class="paper">
    <div class="paper-journal-header">
      <a href="../../index.html" class="paper-journal-logo" aria-label="Gaia Skill Tree">
        <img src="../../assets/marks/diamond-seal.svg" alt="Gaia" width="28" height="28">
        <span>Gaia Skill Tree</span>
      </a>
      <span class="paper-journal-series">Meta Audit Series</span>
    </div>
    <header>
      <h1>Autonomous Verification Pipelines</h1>
      <div class="authors">Marcus Rafael Tiongson</div>
      <div class="date">May 25, 2026</div>
    </header>

    <section class="abstract">
      <div class="abstract-title">Abstract</div>
      <div class="abstract-content">Benchmarking agent verification across multi-model topologies.</div>
    </section>

    <p>Report body content.</p>

    <div class="footer-nav">
      <a href="../../index.html">← Back to Gaia</a>
    </div>
  </article>

  <script>
    const sidebar = document.getElementById('metaSidebar');
    const openBtn = document.getElementById('viewChangelogBtn');
    const closeBtn = document.getElementById('closeChangelogBtn');
    if (openBtn) openBtn.addEventListener('click', () => sidebar.classList.add('open'));
    if (closeBtn) closeBtn.addEventListener('click', () => sidebar.classList.remove('open'));
    async function loadChangelog() {
      try {
        const res = await fetch('../../graph/gaia.json');
        const gaia = await res.json();
        const body = document.getElementById('changelogBody');
        body.innerHTML = '';
        let events = [];
        gaia.skills.forEach(s => {
          if (s.timeline) s.timeline.forEach(e => events.push({ ...e, skillName: s.name }));
        });
        events.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        events.slice(0, 50).forEach(ev => {
          const item = document.createElement('div');
          item.style.cssText = 'margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid #111';
          const header = document.createElement('div');
          header.style.cssText = "font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:#666;margin-bottom:0.3rem";
          header.textContent = `${new Date(ev.timestamp).toLocaleDateString()} · ${(ev.action || '').toUpperCase()}`;
          const title = document.createElement('div');
          title.style.cssText = 'font-weight:500;font-size:0.9rem;color:#fff';
          title.textContent = ev.skillName || '';
          const details = document.createElement('div');
          details.style.cssText = 'font-size:0.8rem;color:#aaa;margin-top:0.2rem';
          details.textContent = ev.details || '';
          item.appendChild(header);
          item.appendChild(title);
          item.appendChild(details);
          body.appendChild(item);
        });
      } catch (e) { console.error('Failed to load changelog', e); }
    }
    loadChangelog();

    (function() {
      var shareBtn = document.getElementById('reportShareBtn');
      var copyBtn = document.getElementById('reportCopyLinkBtn');
      function flashBtn(b) { b.classList.add('copied'); setTimeout(function() { b.classList.remove('copied'); }, 1500); }
      if (shareBtn) shareBtn.addEventListener('click', function() {
        var url = location.href, title = document.title;
        if (navigator.share) { navigator.share({ title: title, url: url }).catch(function() {}); }
        else if (navigator.clipboard) { navigator.clipboard.writeText(url).then(function() { flashBtn(shareBtn); }); }
      });
      if (copyBtn) copyBtn.addEventListener('click', function() {
        if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(function() { flashBtn(copyBtn); });
      });
    })();

  </script>
</body>
</html>
"""


@pytest.fixture
def golden_report_html() -> str:
    return GOLDEN_REPORT_HTML


def test_benign_text_output_is_byte_identical(golden_report_html):
    module = _load_add_post()

    post = {
        "title": "Autonomous Verification Pipelines",
        "summary": "Benchmarking agent verification across multi-model topologies.",
        "label": "Audit",
        "url": "reports/2026-05-25-autonomous-verification.html",
        "date": "2026-05-25",
    }

    # Verify _pmq_card matches unescaped f-string directly
    expected_pmq = (
        f'          <a href="{post["url"]}" class="pmq-post">\n'
        f'            <span class="pmq-label">{post["label"]}</span>\n'
        f'            <h4 class="pmq-title">{post["title"]}'
        f' <span class="meta-peek-arrow" style="float: right;">↗</span></h4>\n'
        f'            <p class="pmq-summary">{post["summary"]}</p>\n'
        f'          </a>'
    )
    assert module._pmq_card(post) == expected_pmq

    # Verify _meta_card matches unescaped f-string directly
    fname = post["url"].rsplit("/", 1)[-1]
    expected_meta = (
        f'      <article class="meta-report-card">\n'
        f'        <div class="meta-report-date">May 25, 2026</div>\n'
        f'        <h3 class="meta-report-title">{post["title"]}</h3>\n'
        f'        <p class="meta-report-summary">{post["summary"]}</p>\n'
        f'        <div class="meta-report-footer">\n'
        f'          <a href="{post["url"]}" class="btn btn-ghost meta-report-link">Read Full Report →</a>\n'
        f'          <button type="button" class="meta-report-action" aria-label="Share report"'
        f' data-report-url="{post["url"]}" data-report-title="{post["title"]}" onclick="metaReportShare(this)">'
        f'<svg class="ico" width="16" height="16" aria-hidden="true"><use href="assets/icons.svg#share"/></svg></button>\n'
        f'          <a href="{post["url"]}" download="{fname}" class="meta-report-action" aria-label="Download report">'
        f'<svg class="ico" width="16" height="16" aria-hidden="true"><use href="assets/icons.svg#download"/></svg></a>\n'
        f'          <button type="button" class="meta-report-action" aria-label="Copy link"'
        f' data-report-url="{post["url"]}" onclick="metaReportCopyLink(this)">'
        f'<svg class="ico" width="16" height="16" aria-hidden="true"><use href="assets/icons.svg#link"/></svg></button>\n'
        f'        </div>\n'
        f'      </article>'
    )
    assert module._meta_card(post) == expected_meta

    # Verify render_report_html headers match unescaped text
    title = "Autonomous Verification Pipelines"
    author = "Marcus Rafael Tiongson"
    display_date = "May 25, 2026"
    abstract = "Benchmarking agent verification across multi-model topologies."
    body_html = "<p>Report body content.</p>"
    download_name = "report.html"
    back_href = "../../index.html"

    rendered = module.render_report_html(
        title=title,
        author=author,
        display_date=display_date,
        abstract=abstract,
        body_html=body_html,
        back_href=back_href,
        download_name=download_name,
    )
    assert f"<title>{title} — Gaia</title>" in rendered
    assert f"<h1>{title}</h1>" in rendered
    assert f'<div class="authors">{author}</div>' in rendered
    assert f'<div class="date">{display_date}</div>' in rendered
    assert f'<div class="abstract-content">{abstract}</div>' in rendered
    assert f'<a href="{download_name}" download="{download_name}" class="pja-btn"' in rendered
    assert f'<a href="{back_href}">← Back to Gaia</a>' in rendered

    # Full-output byte-identical comparison for render_report_html against independent static golden fixture
    assert rendered == golden_report_html


@pytest.mark.parametrize("download_name", ["javascript:alert(1)", "java\tscript:alert(1)", 'data:text/html,"x"'])
def test_report_download_neutralizes_dangerous_href(download_name):
    import html

    rendered = _load_add_post().render_report_html(
        title="Report", author="Author", display_date="May 25, 2026",
        abstract="Abstract", body_html="<p>Body</p>", download_name=download_name,
    )
    assert f'<a href="#" download="{html.escape(download_name, quote=True)}" class="pja-btn" aria-label="Download report">' in rendered


def test_chart_report_preserves_non_chart_structure(golden_report_html):
    rendered = _load_add_post().render_report_html(
        title="Autonomous Verification Pipelines", author="Marcus Rafael Tiongson",
        display_date="May 25, 2026",
        abstract="Benchmarking agent verification across multi-model topologies.",
        body_html="<p>Report body content.</p>", back_href="../../index.html",
        download_name="report.html", chart_data_file="chart.json",
    )
    script_tag = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
    section = ('<div class="chart-container"><canvas id="timelineChart"></canvas>'
               '<div class="chart-caption" id="chartCaption">Figure 1</div></div>')
    assert rendered.count(script_tag) == rendered.count(section) == 1
    assert 'const res = await fetch("chart.json");' in rendered
    assert 'new Chart(ctx, {' in rendered
    start = rendered.index('    async function initChart() {')
    end = rendered.index('    initChart();', start) + len('    initChart();')
    without_chart = rendered[:start] + rendered[end:]
    assert without_chart.replace(script_tag, '').replace(section, '') == golden_report_html


def test_changelog_js_uses_safe_dom_apis():
    module = _load_add_post()
    js = module._CHANGELOG_JS

    assert ".innerHTML = `" not in js
    assert "createElement" in js
    assert "textContent" in js
    assert "header.textContent =" in js
    assert "title.textContent = ev.skillName || '';" in js
    assert "details.textContent = ev.details || '';" in js
    assert "item.appendChild(header)" in js
    assert "item.appendChild(title)" in js
    assert "item.appendChild(details)" in js


def test_date_escaping_with_adversarial_input():
    module = _load_add_post()
    adv_date = "<script>2026</script>"

    # 1. _meta_card
    meta_post = {
        "title": "Adversarial Date Post",
        "summary": "Checking date escaping.",
        "url": "reports/adv-date.html",
        "date": adv_date,
    }
    rendered_card = module._meta_card(meta_post)
    assert "<script>" not in rendered_card
    assert "&lt;script&gt;2026&lt;/script&gt;" in rendered_card
    assert '<div class="meta-report-date">&lt;script&gt;2026&lt;/script&gt;</div>' in rendered_card

    # 2. render_report_html
    rendered_report = module.render_report_html(
        title="Adversarial Date Report",
        author="Author",
        display_date=adv_date,
        abstract="Abstract",
        body_html="<p>Body</p>",
        download_name="report.html",
    )
    assert "<script>2026</script>" not in rendered_report
    assert '<div class="date">&lt;script&gt;2026&lt;/script&gt;</div>' in rendered_report


def test_chart_data_file_escaping():
    module = _load_add_post()
    adv_chart_file = 'chart"data\'\\path</script><script>alert(1)</script>.json'

    rendered = module.render_report_html(
        title="Chart Escaping Test",
        author="Author",
        display_date="May 25, 2026",
        abstract="Abstract",
        body_html="<p>Body</p>",
        download_name="report.html",
        chart_data_file=adv_chart_file,
    )

    # </script> must not appear unescaped in the script block
    assert "</script><script>alert" not in rendered
    assert r"\u003c/script>\u003cscript>alert(1)\u003c/script>.json" in rendered
    expected_fetch = 'const res = await fetch("chart\\"data\'\\\\path\\u003c/script>\\u003cscript>alert(1)\\u003c/script>.json");'
    assert expected_fetch in rendered


def test_dangerous_url_schemes_neutralized(tmp_path):
    module = _load_add_post()

    dangerous_urls = [
        "javascript:alert(1)",
        "JAVASCRIPT:alert(2)",
        "  javascript:alert(3)  ",
        "data:text/html,<script>alert(1)</script>",
        "DATA:text/html;base64,PHNjcmlwdD4=",
        "vbscript:msgbox(1)",
        "VBSCRIPT:alert(1)",
        # Embedded whitespace and control characters (0x00-0x1F, 0x7F)
        "java\tscript:alert(1)",
        "java\nscript:alert(1)",
        "java\rscript:alert(1)",
        "java\x00script:alert(1)",
        "java\x1fscript:alert(1)",
        "java\x7fscript:alert(1)",
        "da\tta:text/html,<script>alert(1)</script>",
        "da\x00ta:text/html;base64,PHNjcmlwdD4=",
        "vb\tscript:alert(1)",
        "vb\nscript:alert(1)",
        "vb\x00script:alert(1)",
    ]

    for d_url in dangerous_urls:
        # 1. Direct _safe_url helper check
        assert module._safe_url(d_url) == "#"
        assert module._safe_url(d_url, default="../../index.html") == "../../index.html"

        # 2. _pmq_card
        post = {
            "title": "Dangerous Post",
            "summary": "Summary",
            "label": "Test",
            "url": d_url,
        }
        pmq = module._pmq_card(post)
        assert 'href="#"' in pmq
        assert "alert(1)" not in pmq
        assert "<script" not in pmq
        assert "javascript:" not in pmq.lower()
        assert "data:" not in pmq.lower()
        assert "vbscript:" not in pmq.lower()

        # 3. _meta_card
        meta_post = {
            "title": "Dangerous Meta",
            "summary": "Summary",
            "url": d_url,
            "date": "2026-05-25",
        }
        meta = module._meta_card(meta_post)
        assert 'href="#"' in meta
        assert 'data-report-url="#"' in meta
        assert 'download="#"' in meta
        assert "alert(1)" not in meta
        assert "<script" not in meta
        assert "javascript:" not in meta.lower()
        assert "data:" not in meta.lower()
        assert "vbscript:" not in meta.lower()

        # 4. Hero button via patch_index
        tmp_index = tmp_path / "index.html"
        tmp_index.write_text(
            "<!-- gaia-posts-start --><!-- gaia-posts-end -->\n"
            "<!-- gaia-hero-post-start --><!-- gaia-hero-post-end -->\n",
            encoding="utf-8",
        )
        saved_index = module.INDEX_FILE
        try:
            module.INDEX_FILE = tmp_index
            module.patch_index(
                posts=[post],
                hero_url=d_url,
                hero_label="Hero Label",
            )
            patched = tmp_index.read_text(encoding="utf-8")
            assert 'href="#"' in patched
            assert "alert(1)" not in patched
            assert "<script" not in patched
            assert "javascript:" not in patched.lower()
            assert "data:" not in patched.lower()
            assert "vbscript:" not in patched.lower()
        finally:
            module.INDEX_FILE = saved_index

        # 5. render_report_html back_href
        report = module.render_report_html(
            title="Dangerous Report",
            author="Author",
            display_date="May 25, 2026",
            abstract="Summary",
            body_html="<p>Body</p>",
            download_name="report.html",
            back_href=d_url,
        )
        assert '<a href="../../index.html">← Back to Gaia</a>' in report
        assert "alert(1)" not in report
        assert "<script>alert(1)</script>" not in report
        assert not d_url or d_url not in report
        assert "javascript:" not in report.lower()
        assert "data:" not in report.lower()
        assert "vbscript:" not in report.lower()


def test_patch_with_backslashes_in_content(tmp_path):
    module = _load_add_post()

    slash_title = r"Path\to\1 and \g<0>"
    slash_summary = r"Details in C:\User\1 and \g<named>"

    post = {
        "id": "slash-test",
        "type": "report",
        "title": slash_title,
        "summary": slash_summary,
        "label": "Audit",
        "url": "reports/test.html",
        "date": "2026-05-25",
    }

    tmp_index = tmp_path / "index.html"
    tmp_index.write_text(
        "<!-- gaia-posts-start --><!-- gaia-posts-end -->\n"
        "<!-- gaia-hero-post-start --><!-- gaia-hero-post-end -->\n",
        encoding="utf-8",
    )
    tmp_meta = tmp_path / "meta.html"
    tmp_meta.write_text(
        "<!-- gaia-meta-cards-start --><!-- gaia-meta-cards-end -->\n",
        encoding="utf-8",
    )

    saved_index = module.INDEX_FILE
    saved_meta = module.META_FILE
    try:
        module.INDEX_FILE = tmp_index
        module.META_FILE = tmp_meta

        # Should execute without re.error and without altering backslashes or corrupting group references
        module.patch_index(
            posts=[post],
            hero_url="reports/test.html",
            hero_label=slash_title,
        )
        patched_index = tmp_index.read_text(encoding="utf-8")

        assert r"Path\to\1 and \g&lt;0&gt;" in patched_index
        assert r"Details in C:\User\1 and \g&lt;named&gt;" in patched_index

        module.patch_meta_html(posts=[post])
        patched_meta = tmp_meta.read_text(encoding="utf-8")
        assert r"Path\to\1 and \g&lt;0&gt;" in patched_meta
        assert r"Details in C:\User\1 and \g&lt;named&gt;" in patched_meta
    finally:
        module.INDEX_FILE = saved_index
        module.META_FILE = saved_meta
