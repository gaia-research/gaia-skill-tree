/**
 * site-nav.js — single source of truth for the main site nav.
 * Renders into <nav id="site-nav"> on every page.
 * Auto-detects root path depth and active page from window.location.
 */
(function () {
  const el = document.getElementById('site-nav');
  if (!el) return;

  // Compute depth via known mount names — works on both localhost (/docs/named/)
  // and GH Pages (gaia.tiongson.co/named/) where 'docs' never appears in the URL.
  //
  //   /                          → depth 0  → root = ''
  //   /named/                    → depth 1  → root = '../'
  //   /en/getting-started.html   → depth 1  → root = '../'
  //   /badges/                   → depth 1  → root = '../'
  //   /u/                        → depth 1  → root = '../'
  //   /u/mbtiongson1/            → depth 2  → root = '../../'
  //
  const MOUNTS = ['named', 'en', 'badges', 'u', 'samples', 'graph', 'evidence', 'share', 'trust', 'api', 'codex'];
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

  // Resolve icon sprite — prefer icons.js's gaiaIconBase() if already loaded.
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
    { type: 'link', href: root + 'trust/leaderboard/', label: 'Trust Leaderboard', color: 'var(--evidence-gold)' },
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

  el.innerHTML =
    '<a href="' + root + 'index.html" class="nav-logo" aria-label="Gaia home">' +
      SEAL_SVG +
      '<span class="nav-wordmark">Gaia</span>' +
    '</a>' +
    '<button type="button" class="nav-search-btn-mobile" id="navSearchBtnMobile" aria-label="Search named" hidden>' +
      '<svg class="ico" width="18" height="18" aria-hidden="true"><use href="' + root + 'assets/icons.svg#search"/></svg>' +
    '</button>' +
    '<button class="nav-menu-toggle" type="button" aria-label="Open navigation" aria-expanded="false">' +
      '<span></span><span></span><span></span>' +
    '</button>' +
    '<ul class="nav-primary">' +
      links.map(li).join('') +
      '<li class="nav-more-dropdown" style="--nav-i:5">' +
        '<button class="nav-more-toggle" aria-label="More options" aria-expanded="false">More</button>' +
        '<ul class="nav-more-menu">' +
          dropdown.map(dropdownItem).join('') +
        '</ul>' +
      '</li>' +
    '</ul>';

  // Skill Graph button: on the home page skill-graph.js owns [data-graph-trigger].
  // On any other page, navigate to home with ?field=1 which hud-toggle.js picks up.
  var graphBtn = el.querySelector('[data-graph-trigger]');
  if (graphBtn && root !== '') {
    graphBtn.addEventListener('click', function () {
      window.location.href = root + 'index.html?field=1';
    });
  }
})();
