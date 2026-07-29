/**
 * site-footer.js — single source of truth for the main site footer.
 * Renders into <div id="site-footer-mount"> on every page.
 * Auto-detects root path depth from window.location.
 */
(function () {
  const el = document.getElementById('site-footer-mount');
  if (!el) return;

  // Load the Syne webfont for the Gaia Research sibling lockup. We load it
  // ourselves (our own CSS/DOM) and never import gaia-research files — the
  // cross-repo content rule allows hyperlinks + legible kinship, not merger.
  // Injected once from the footer so it propagates on every page the footer
  // mounts into, no per-page <head> edits.
  if (!document.getElementById('gaia-research-font')) {
    const rf = document.createElement('link');
    rf.id = 'gaia-research-font';
    rf.rel = 'stylesheet';
    rf.href = 'https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&display=swap';
    document.head.appendChild(rf);
  }

  // Fallback mirrors docs/js/mounts.js — keep in lockstep. Every top-level
  // docs/ subdirectory that uses site-nav or site-footer must appear here so
  // path-depth math still resolves when mounts.js hasn't loaded yet.
  const MOUNTS = window.GAIA_MOUNTS || [
    'named', 'en', 'badges', 'u', 'samples', 'graph',
    'evidence', 'share', 'trust', 'api', 'codex', 'trending', 'heroes',
    'reports', 'benchmarks',
  ];
  const segs = window.location.pathname.replace(/\/+$/, '').split('/').filter(Boolean);
  const dir = /\.html?$/i.test(segs[segs.length - 1]) ? segs.slice(0, -1) : segs;
  let depth = 0;
  for (let i = 0; i < dir.length; i++) {
    if (MOUNTS.includes(dir[i])) { depth = dir.length - i; break; }
  }
  const r = depth === 0 ? '' : '../'.repeat(depth);

  el.innerHTML = `
    <footer class="footer-v2">
      <div class="footer-roots" style="--footer-tree:url('${r}assets/world-tree/yggdrasil-backdrop-941.webp')" aria-hidden="true"></div>

      <div class="footer-inner">

        <!-- Closing invitation — the emotional sign-off, one clear action, centered. -->
        <div class="footer-close">
          <svg class="ico footer-close-seal" aria-hidden="true" focusable="false">
            <use href="${r}assets/icons.svg#seal-diamond"/>
          </svg>
          <h2 class="footer-close-headline">Every capability, earned.</h2>
          <p class="footer-close-sub">An evidence-backed atlas of what agents can really do.</p>
          <a class="footer-close-cta" href="${r}index.html" aria-label="Explore the Gaia Skill Tree">
            <span>Explore the Skill Tree</span>
            <span class="footer-close-cta-arrow" aria-hidden="true">→</span>
          </a>
        </div>

        <!-- Horizontal nav rail — every section, one wrapping row, grouped by heading. -->
        <nav class="footer-rail" aria-label="Site navigation">
          <div class="footer-rail-group">
            <span class="footer-rail-heading">Registry</span>
            <a href="${r}index.html">Home</a>
            <a href="${r}index.html?field=1">Skill Graph</a>
            <a href="${r}starless.html">Starless</a>
            <a href="${r}meta.html">Meta Changelog</a>
          </div>
          <div class="footer-rail-group">
            <span class="footer-rail-heading">Discover</span>
            <a href="${r}codex.html">The Codex</a>
            <a href="${r}named/">Named Skills</a>
            <a href="${r}u/">Contributors</a>
            <a href="${r}badges/">GitHub Badges</a>
          </div>
          <div class="footer-rail-group">
            <span class="footer-rail-heading">Evidence</span>
            <a href="${r}benchmarks/">Benchmarks</a>
            <a href="${r}reports/">Weekly Reports</a>
            <a href="${r}trending/">Trending</a>
            <a href="${r}heroes/">Hall of Heroes</a>
          </div>
          <div class="footer-rail-group">
            <span class="footer-rail-heading">Docs</span>
            <a href="${r}en/">Docs Home</a>
            <a href="${r}en/getting-started.html">Getting Started</a>
            <a href="${r}en/cli-reference.html">CLI Reference</a>
          </div>
          <div class="footer-rail-group">
            <span class="footer-rail-heading">Contribute</span>
            <a href="${r}index.html#paths">Push a skill</a>
            <a href="https://github.com/gaia-research/gaia-skill-tree" target="_blank" rel="noopener" class="footer-ext">GitHub</a>
            <a href="https://github.com/gaia-research/gaia-skill-tree/issues" target="_blank" rel="noopener" class="footer-ext">Open Issues</a>
          </div>
          <div class="footer-rail-group">
            <span class="footer-rail-heading">About</span>
            <a href="${r}about.html">About Gaia</a>
            <a href="https://research.gaiaskilltree.com/about" target="_blank" rel="noopener" class="footer-ext">The Gaia ecosystem</a>
            <a href="https://github.com/mbtiongson1" target="_blank" rel="noopener" class="footer-link-honor">@mbtiongson1</a>
            <a href="${r}privacy.html">Privacy</a>
            <button id="copyAgentFooterBtn" type="button" class="footer-link-btn" aria-label="Copy page context for agents">Copy Page</button>
          </div>
        </nav>
      </div>

      <!-- Root anchor — the site's name at full scale, growing from the roots,
           with the parent-org attribution tucked beside it. -->
      <div class="footer-anchor">
        <span class="footer-display-word" aria-hidden="true">Skill <span class="footer-display-tree">Tree</span></span>
        <p class="footer-parentage">
          A project of
          <a class="footer-parent-link" href="https://research.gaiaskilltree.com"
             target="_blank" rel="noopener"
             aria-label="Gaia Research — the parent lab, at research.gaiaskilltree.com">
            Gaia Research<span class="footer-parent-arrow" aria-hidden="true">↗</span>
          </a>
        </p>
      </div>

      <div class="footer-bottom">
        <svg class="ico footer-seal" width="16" height="16" aria-hidden="true">
          <use href="${r}assets/icons.svg#seal-diamond"/>
        </svg>
        <span class="footer-bottom-sep">—</span>
        <span>Gaia Skill Tree</span>
        <span class="footer-bottom-sep">·</span>
        <a href="https://github.com/gaia-research/gaia-skill-tree" target="_blank" rel="noopener">GitHub</a>
        <span class="footer-bottom-sep">·</span>
        <a href="${r}privacy.html">Privacy</a>
      </div>
    </footer>
  `;
})();
