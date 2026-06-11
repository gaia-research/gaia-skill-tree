/**
 * site-nav.js — single source of truth for the main site nav.
 * Renders into <nav id="site-nav"> on every page.
 * Auto-detects root path depth and active page from window.location.
 */
(function () {
  const el = document.getElementById('site-nav');
  if (!el) return;

  // Detect how many levels deep we are from /docs/
  // depth 0 = docs/*.html, depth 1 = docs/en/*.html or docs/named/*.html, etc.
  const parts = window.location.pathname.replace(/\/$/, '').split('/');
  // Strip trailing filename
  const filename = parts[parts.length - 1];
  const isFile = filename.includes('.');
  const dirParts = isFile ? parts.slice(0, -1) : parts;

  // Find the docs root by looking for known subdirs
  // Works for: /docs/, /docs/en/, /docs/named/, /docs/u/username/, etc.
  // We need to figure out the relative prefix to reach docs root.
  const docsDirIndex = dirParts.findIndex(p => p === 'docs');
  const depth = docsDirIndex >= 0 ? dirParts.length - docsDirIndex - 1 : 0;
  const root = depth === 0 ? '' : '../'.repeat(depth);

  // Determine current page for aria-current
  const currentPath = window.location.pathname;
  function isActive(href) {
    const resolved = new URL(href, window.location.href).pathname.replace(/\/$/, '') || '/';
    const cur = currentPath.replace(/\/$/, '') || '/';
    return resolved === cur || (href === 'index.html' && (cur.endsWith('/docs') || cur.endsWith('/docs/')));
  }

  const links = [
    { href: root + 'index.html',   label: 'Home',          color: 'var(--text)',        i: 0 },
    { href: root + 'about.html',   label: 'About',         color: 'var(--apex-gold)',   i: 1 },
    {
      href: root + 'badges/',
      label: 'GitHub Badges',
      color: 'var(--tier-unique)',
      icon: `<svg class="ico" width="13" height="13" aria-hidden="true" style="vertical-align:-2px;margin-right:.35em"><use href="${root}assets/icons.svg#github"/></svg>`,
      i: 2
    },
    { href: root + 'named/',       label: 'Skills',        color: 'var(--honor-red)',   i: 3 },
    { href: root + 'en/',          label: 'Docs',          color: 'var(--tier-basic)',  i: 4 },
  ];

  const dropdown = [
    { type: 'btn',  id: 'treeNavBtn',    label: 'Skill Tree',         color: '#34d399',              cls: 'nav-tree' },
    { type: 'btn',  id: 'navGraphBtn',   label: 'Skill Graph',        color: '#38bdf8',              cls: 'nav-graph-trigger', attr: 'data-graph-trigger' },
    { type: 'link', href: root + 'codex.html',   label: 'The Codex',         color: 'var(--tier-basic)' },
    { type: 'link', href: root + 'starless.html', label: 'Starless',          color: 'var(--muted)' },
    { type: 'link', href: root + 'u/',            label: 'Named Contributors',color: 'var(--honor-red)' },
    { type: 'link', href: root + 'meta.html',     label: 'Meta Reports',      cls: 'nav-meta', id: 'metaNavBtn' },
  ];

  function li(item) {
    const active = isActive(item.href) ? ' aria-current="page"' : '';
    const icon = item.icon || '';
    return `<li style="--nav-i:${item.i}"><a href="${item.href}" style="color:${item.color}"${active}>${icon}${item.label}</a></li>`;
  }

  function dropdownItem(d) {
    if (d.type === 'btn') {
      const extra = d.attr ? ` ${d.attr}` : '';
      const cls = d.cls ? ` class="${d.cls}"` : '';
      const id = d.id ? ` id="${d.id}"` : '';
      return `<li><button type="button"${cls}${id} style="color:${d.color}"${extra}>${d.label}</button></li>`;
    }
    const active = isActive(d.href) ? ' aria-current="page"' : '';
    const cls = d.cls ? ` class="${d.cls}"` : '';
    const id = d.id ? ` id="${d.id}"` : '';
    return `<li><a href="${d.href}"${cls}${id} style="color:${d.color || ''}"${active}>${d.label}</a></li>`;
  }

  el.innerHTML = `
    <a href="${root}index.html" class="nav-logo" aria-label="Gaia home">
      <svg class="ico nav-seal" aria-hidden="true" focusable="false"><use href="${root}assets/icons.svg#seal-diamond"/></svg>
      <span class="nav-wordmark">Gaia</span>
    </a>
    <button type="button" class="nav-search-btn-mobile" id="navSearchBtnMobile" aria-label="Search named" hidden>
      <svg class="ico" width="18" height="18" aria-hidden="true"><use href="${root}assets/icons.svg#search"/></svg>
    </button>
    <button class="nav-menu-toggle" type="button" aria-label="Open navigation" aria-expanded="false">
      <span></span><span></span><span></span>
    </button>
    <ul class="nav-primary">
      ${links.map(li).join('\n      ')}
      <li class="nav-more-dropdown" style="--nav-i:5">
        <button class="nav-more-toggle" aria-label="More options" aria-expanded="false">More</button>
        <ul class="nav-more-menu">
          ${dropdown.map(dropdownItem).join('\n          ')}
        </ul>
      </li>
    </ul>
  `;
})();
