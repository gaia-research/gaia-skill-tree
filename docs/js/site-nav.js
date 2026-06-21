/**
 * site-nav.js — single source of truth for the main site nav.
 * Renders into <nav id="site-nav"> on every page.
 *
 * Three pieces emitted by this script:
 *   1. .nav-logo                 — Gaia diamond seal + wordmark (always)
 *   2. .nav-breadcrumb           — only on docs/en/*; sits beside the logo
 *   3. .nav-primary              — desktop top-level + More dropdown
 *   4. .nav-menu-toggle (☰)      — opens the mobile drawer (≤700px)
 *   5. .nav-mobile-drawer        — flat list of EVERY destination (no nesting,
 *                                   no dropdown). One screen, 13 items, no scroll.
 *
 * The mobile drawer is a sibling of .nav-primary (not its mobile reflow) so
 * the long cascade war we kept losing — desktop dropdown rules vs. media
 * queries vs. animation transforms — is bypassed entirely. The drawer has
 * its own dedicated class names that NO other rules touch.
 */
(function () {
  const el = document.getElementById('site-nav');
  if (!el) return;

  // ── Path / depth detection ─────────────────────────────────────────────
  const MOUNTS = window.GAIA_MOUNTS || ['named', 'en', 'badges', 'u', 'samples', 'graph', 'evidence', 'share', 'trust', 'api', 'codex'];
  const segs = window.location.pathname.replace(/\/+$/, '').split('/').filter(Boolean);
  const dir = /\.html?$/i.test(segs[segs.length - 1]) ? segs.slice(0, -1) : segs;

  let depth = 0;
  for (let i = 0; i < dir.length; i++) {
    if (MOUNTS.includes(dir[i])) {
      depth = dir.length - i;
      break;
    }
  }
  const root = depth === 0 ? '' : '../'.repeat(depth);

  function iconBase() {
    if (typeof window.gaiaIconBase === 'function') return window.gaiaIconBase();
    return root + 'assets/icons.svg';
  }

  // Diamond Seal inlined — avoids <use href> sprite-load race and cross-origin blocks.
  const SEAL_SVG = `<svg class="ico nav-seal" viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M 32 4 L 60 32 L 32 60 L 4 32 Z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="miter"/><text x="32" y="34" font-family="EB Garamond, Georgia, serif" font-weight="600" font-size="28" fill="currentColor" text-anchor="middle" dominant-baseline="central">G</text></svg>`;

  const currentPath = window.location.pathname;
  function isActive(href) {
    const resolved = new URL(href, window.location.href).pathname.replace(/\/$/, '') || '/';
    const cur = currentPath.replace(/\/$/, '') || '/';
    return resolved === cur;
  }

  // ── Link inventories ──────────────────────────────────────────────────
  const links = [
    { href: root + 'index.html', label: 'Home',          color: 'var(--text)',       i: 0 },
    { href: root + 'about.html', label: 'About',         color: 'var(--apex-gold)',  i: 1 },
    {
      href: root + 'badges/',
      label: 'GitHub Badges',
      color: 'var(--tier-unique)',
      icon: function() { return '<svg class="ico" width="13" height="13" aria-hidden="true" style="vertical-align:-2px;margin-right:.35em"><use href="' + iconBase() + '#github"/></svg>'; },
      i: 2
    },
    { href: root + 'named/', label: 'Skills', color: 'var(--honor-red)',  i: 3 },
    { href: root + 'en/',    label: 'Docs',   color: 'var(--tier-basic)', i: 4 },
  ];

  const dropdown = [
    { type: 'btn',  id: 'treeNavBtn',  label: 'Skill Tree',          color: '#34d399', cls: 'nav-tree' },
    { type: 'btn',  id: 'navGraphBtn', label: 'Skill Graph',          color: 'var(--tier-basic)', cls: 'nav-graph-trigger', attr: 'data-graph-trigger' },
    { type: 'link', href: root + 'codex.html',    label: 'The Codex',          color: 'var(--tier-basic)' },
    { type: 'link', href: root + 'trust/ledger/', label: 'Trust Ledger', color: 'var(--evidence-gold)' },
    { type: 'link', href: root + 'starless.html', label: 'Starless',           color: 'var(--muted)' },
    { type: 'link', href: root + 'u/',            label: 'Named Contributors', color: 'var(--honor-red)' },
    { type: 'link', href: root + 'meta.html',     label: 'Meta Reports',       cls: 'nav-meta', id: 'metaNavBtn' },
    { type: 'link', href: root + 'evidence/',     label: 'Evidence Library',   color: 'var(--rank-3)' },
  ];

  function li(item) {
    const active = isActive(item.href) ? ' aria-current="page"' : '';
    const icon = typeof item.icon === 'function' ? item.icon() : '';
    return '<li style="--nav-i:' + item.i + '"><a href="' + item.href + '" style="color:' + item.color + '"' + active + '>' + icon + item.label + '</a></li>';
  }

  function dropdownItem(d) {
    if (d.type === 'btn') {
      const extra = d.attr ? ' ' + d.attr : '';
      const cls = d.cls ? ' class="' + d.cls + '"' : '';
      const id = d.id ? ' id="' + d.id + '"' : '';
      return '<li><button type="button"' + cls + id + ' style="color:' + d.color + '"' + extra + '>' + d.label + '</button></li>';
    }
    const active = isActive(d.href) ? ' aria-current="page"' : '';
    const cls = d.cls ? ' class="' + d.cls + '"' : '';
    const id = d.id ? ' id="' + d.id + '"' : '';
    return '<li><a href="' + d.href + '"' + cls + id + ' style="color:' + (d.color || '') + '"' + active + '>' + d.label + '</a></li>';
  }

  // ── docs/en breadcrumb ────────────────────────────────────────────────
  // Inline strip beside the logo. Only rendered for /en/* pages.
  // Page → label map is the single source of truth for breadcrumb names.
  const DOCS_PAGE_LABELS = {
    'index.html':           null,            // Docs root: only show "Docs", no second crumb
    'getting-started.html': 'Getting Started',
    'cli-reference.html':   'CLI Reference',
    'contributing.html':    'Contributing',
    'evidence-classes.html':'Evidence Classes',
    'faq.html':             'FAQ',
    'fusion.html':          'Fusion',
    'mcp-server.html':      'MCP Server',
    'named-skills.html':    'Named Skills',
    'share-bundles.html':   'Share Bundles',
    'skill-hierarchy.html': 'Skill Hierarchy',
    'timeline-audit.html':  'Timeline Audit'
  };

  function renderBreadcrumb() {
    // Detect /en/* pages by scanning the URL segments.
    const enIdx = dir.indexOf('en');
    if (enIdx === -1) return '';

    const lastSeg = segs[segs.length - 1] || '';
    const isHtml = /\.html?$/i.test(lastSeg);
    const filename = isHtml ? lastSeg : 'index.html';
    const label = DOCS_PAGE_LABELS[filename];   // undefined if unknown page
    const docsRoot = root + 'en/';

    let html =
      '<div class="nav-breadcrumb" role="navigation" aria-label="Breadcrumb">' +
        '<span class="nav-breadcrumb-sep" aria-hidden="true">/</span>' +
        '<a href="' + docsRoot + '" class="nav-breadcrumb-link"' +
          (filename === 'index.html' ? ' aria-current="page"' : '') + '>Docs</a>';

    if (label) {
      html +=
        '<span class="nav-breadcrumb-sep" aria-hidden="true">/</span>' +
        '<span class="nav-breadcrumb-current" aria-current="page">' + label + '</span>';
    }

    html += '</div>';
    return html;
  }

  // ── Render ────────────────────────────────────────────────────────────
  el.innerHTML =
    // Logo + (optional) breadcrumb sit together as the left cluster.
    '<div class="nav-left">' +
      '<a href="' + root + 'index.html" class="nav-logo" aria-label="Gaia home">' +
        SEAL_SVG +
        '<span class="nav-wordmark">Gaia</span>' +
      '</a>' +
      renderBreadcrumb() +
    '</div>' +
    '<button class="nav-menu-toggle" type="button" aria-label="Open navigation" aria-expanded="false">' +
      '<span></span><span></span><span></span>' +
    '</button>' +
    // Desktop top-level nav (with hover-flyout More dropdown).
    '<ul class="nav-primary">' +
      links.map(li).join('') +
      '<li class="nav-more-dropdown" style="--nav-i:5">' +
        '<button class="nav-more-toggle" aria-label="More options" aria-expanded="false">More</button>' +
        '<ul class="nav-more-menu">' +
          dropdown.map(dropdownItem).join('') +
        '</ul>' +
      '</li>' +
    '</ul>' +
    // Mobile drawer — completely separate element with its own class names.
    // Flat list of every destination, no nesting, fits one screen.
    '<div class="nav-mobile-drawer" aria-hidden="true">' +
      '<button class="nav-mobile-close" type="button" aria-label="Close navigation">×</button>' +
      '<ul class="nav-mobile-list">' +
        // Top-level links (clone, not the same nodes).
        links.map(function (item) {
          const active = isActive(item.href) ? ' aria-current="page"' : '';
          const icon = typeof item.icon === 'function' ? item.icon() : '';
          return '<li><a href="' + item.href + '" style="color:' + item.color + '"' + active + '>' + icon + item.label + '</a></li>';
        }).join('') +
        // Dropdown items, flattened. Buttons (Skill Tree / Skill Graph) become
        // <a> links to home with the right query param so taps Just Work — the
        // dedicated handlers (skill-graph.js, hud-toggle.js) pick up the param.
        '<li><a href="' + root + 'index.html?tree=1" style="color:#34d399">Skill Tree</a></li>' +
        '<li><a href="' + root + 'index.html?field=1" style="color:var(--tier-basic)">Skill Graph</a></li>' +
        '<li><a href="' + root + 'codex.html" style="color:var(--tier-basic)">The Codex</a></li>' +
        '<li><a href="' + root + 'trust/ledger/" style="color:var(--evidence-gold)">Trust Ledger</a></li>' +
        '<li><a href="' + root + 'starless.html" style="color:var(--muted)">Starless</a></li>' +
        '<li><a href="' + root + 'u/" style="color:var(--honor-red)">Named Contributors</a></li>' +
        '<li><a href="' + root + 'meta.html">Meta Reports</a></li>' +
        '<li><a href="' + root + 'evidence/" style="color:var(--rank-3)">Evidence Library</a></li>' +
      '</ul>' +
    '</div>';

  // Skill Graph button: on the home page skill-graph.js owns [data-graph-trigger].
  // On any other page, navigate to home with ?field=1 which hud-toggle.js picks up.
  var graphBtn = el.querySelector('[data-graph-trigger]');
  if (graphBtn && root !== '') {
    graphBtn.addEventListener('click', function () {
      window.location.href = root + 'index.html?field=1';
    });
  }

  // ── Mobile drawer wiring ──────────────────────────────────────────────
  // We own this here (not in ui.js) because the drawer is a sibling element,
  // not a reflow of .nav-primary, and the open/close behavior is local.
  const toggle = el.querySelector('.nav-menu-toggle');
  const drawer = el.querySelector('.nav-mobile-drawer');
  const closeBtn = el.querySelector('.nav-mobile-close');
  if (toggle && drawer) {
    function openDrawer() {
      drawer.classList.add('open');
      drawer.setAttribute('aria-hidden', 'false');
      toggle.setAttribute('aria-expanded', 'true');
      document.body.classList.add('nav-drawer-open');
    }
    function closeDrawer() {
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('nav-drawer-open');
    }
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      drawer.classList.contains('open') ? closeDrawer() : openDrawer();
    });
    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
    drawer.querySelectorAll('a, button').forEach(function (link) {
      // Don't close on the close button itself (already wired).
      if (link === closeBtn) return;
      link.addEventListener('click', closeDrawer);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && drawer.classList.contains('open')) closeDrawer();
    });
  }
})();
