/**
 * docs-nav-mobile.js — adds a small hamburger toggle and a slide-down drawer
 * to the .docs-nav breadcrumb on mobile (≤700px). Each docs/en page has its
 * own inline CSS for .docs-nav; we inject a tiny stylesheet at runtime so we
 * don't have to edit 12 page <style> blocks.
 *
 * Drawer links mirror the main site-nav so docs readers can reach Skills,
 * GitHub Badges, Trust Ledger, etc. without going back to the home page.
 */
(function () {
  'use strict';

  var nav = document.querySelector('nav.docs-nav');
  if (!nav || nav.querySelector('.docs-nav-mobile-toggle')) return;

  var GAIA_VER = window.GAIA_VERSION || '';
  var v = GAIA_VER ? '?v=' + GAIA_VER : '';

  // Inject styles once
  var styleId = 'docs-nav-mobile-style';
  if (!document.getElementById(styleId)) {
    var st = document.createElement('style');
    st.id = styleId;
    st.textContent = [
      '.docs-nav-mobile-toggle { display: none; align-items: center; justify-content: center; flex-direction: column; gap: 3px; width: 30px; height: 30px; background: transparent; border: 0; border-radius: 6px; cursor: pointer; color: inherit; padding: 0; margin-left: auto; }',
      '.docs-nav-mobile-toggle span { display: block; width: 16px; height: 1.5px; border-radius: 999px; background: currentColor; }',
      '.docs-nav-mobile-toggle:hover, .docs-nav-mobile-toggle:focus-visible { background: rgba(255,255,255,.06); outline: 0; }',
      '.docs-nav-mobile-drawer { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #000; padding: 4rem 1.25rem 2rem; z-index: 9998; display: none; flex-direction: column; gap: 0; overflow-y: auto; -webkit-overflow-scrolling: touch; }',
      '.docs-nav-mobile-drawer.open { display: flex; }',
      '.docs-nav-mobile-drawer a { display: block; width: 100%; padding: .55rem .25rem; font-family: inherit; font-size: .95rem; color: var(--muted, #64748b); text-decoration: none; text-align: center; border: 0; background: transparent; transition: color .2s, text-shadow .2s; }',
      '.docs-nav-mobile-drawer a:hover { text-shadow: 0 0 10px currentColor; }',
      '.docs-nav-mobile-drawer .group-label { font-family: var(--font-mono, monospace); font-size: .65rem; color: var(--muted, #64748b); letter-spacing: .12em; text-transform: uppercase; padding: 1rem .25rem .35rem; text-align: center; }',
      '.docs-nav-mobile-drawer .close-btn { position: fixed; top: .9rem; right: 1.1rem; width: 30px; height: 30px; background: transparent; border: 0; color: var(--text, #e2e8f0); font-size: 1.4rem; line-height: 1; cursor: pointer; z-index: 9999; }',
      '@media (max-width: 700px) {',
      '  .docs-nav-mobile-toggle { display: flex; }',
      '  nav.docs-nav .nav-version, nav.docs-nav .docs-nav-version { display: none !important; }',
      '  nav.docs-nav .nav-spacer, nav.docs-nav .docs-nav-spacer { display: none !important; }',
      '}'
    ].join('\n');
    document.head.appendChild(st);
  }

  // Build the hamburger toggle
  var toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'docs-nav-mobile-toggle';
  toggle.setAttribute('aria-label', 'Open site menu');
  toggle.setAttribute('aria-expanded', 'false');
  toggle.innerHTML = '<span></span><span></span><span></span>';
  nav.appendChild(toggle);

  // Build the drawer with main-site links
  var drawer = document.createElement('div');
  drawer.className = 'docs-nav-mobile-drawer';
  drawer.setAttribute('aria-hidden', 'true');
  // Path back to docs root (../) — every docs/en/*.html sits at depth 1.
  var root = '../';
  drawer.innerHTML = [
    '<button type="button" class="close-btn" aria-label="Close menu">×</button>',
    '<a href="' + root + 'index.html" style="color:var(--text)">Home</a>',
    '<a href="' + root + 'about.html" style="color:var(--apex-gold)">About</a>',
    '<a href="' + root + 'badges/' + v + '" style="color:var(--tier-unique)">GitHub Badges</a>',
    '<a href="' + root + 'named/' + v + '" style="color:var(--honor-red)">Skills</a>',
    '<a href="index.html" style="color:var(--tier-basic)">Docs</a>',
    '<div class="group-label">More</div>',
    '<a href="' + root + 'index.html?tree=1" style="color:#34d399">Skill Tree</a>',
    '<a href="' + root + 'index.html?field=1" style="color:var(--tier-basic)">Skill Graph</a>',
    '<a href="' + root + 'codex.html" style="color:var(--tier-basic)">The Codex</a>',
    '<a href="' + root + 'trust/ledger/' + v + '" style="color:var(--evidence-gold)">Trust Ledger</a>',
    '<a href="' + root + 'starless.html" style="color:var(--muted)">Starless</a>',
    '<a href="' + root + 'u/' + v + '" style="color:var(--honor-red)">Named Contributors</a>',
    '<a href="' + root + 'meta.html">Meta Reports</a>',
    '<a href="' + root + 'evidence/' + v + '" style="color:var(--rank-3)">Evidence Library</a>'
  ].join('');
  document.body.appendChild(drawer);

  function open() {
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    toggle.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  }
  function close() {
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    toggle.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  toggle.addEventListener('click', function (e) {
    e.stopPropagation();
    drawer.classList.contains('open') ? close() : open();
  });
  drawer.querySelector('.close-btn').addEventListener('click', close);
  drawer.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', close);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && drawer.classList.contains('open')) close();
  });
})();
