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
    'reports', 'benchmarks', 'skills',
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
      <div class="footer-inner">
        <div class="footer-brand-col">
          <div class="footer-family" aria-label="Gaia brand family">

            <div class="footer-brand-mark">
              <svg class="ico footer-seal" aria-hidden="true" focusable="false">
                <use href="${r}assets/icons.svg#seal-diamond"/>
              </svg>
              <span class="footer-wordmark">Gaia</span>
            </div>
            <p class="footer-tagline">An evidence-backed atlas<br>of agent capabilities.</p>

            <div class="footer-kinship">
              <span class="footer-kinship-line" aria-hidden="true"></span>
              <p class="footer-kinship-copy">
                The flagship registry of
              </p>
            </div>

            <a class="footer-research" href="https://research.gaiaskilltree.com"
               target="_blank" rel="noopener"
               aria-label="Gaia Research — visit research.gaiaskilltree.com">
              <span class="footer-research-lens" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
                  <path d="M12 2.5 20.5 7v10L12 21.5 3.5 17V7L12 2.5Z"
                        stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
                  <circle cx="12" cy="12" r="3.4" stroke="currentColor" stroke-width="1.4"/>
                </svg>
              </span>
              <span class="footer-research-mark">
                <span class="footer-research-name">Gaia Research</span>
                <span class="footer-research-cta">Enter the lab <span aria-hidden="true">→</span></span>
              </span>
            </a>

          </div>
        </div>

        <nav class="footer-cols" aria-label="Site navigation">

          <div class="footer-col">
            <span class="footer-col-heading">Registry</span>
            <ul>
              <li><a href="${r}index.html">Home</a></li>
              <li><a href="${r}index.html">Skill Tree</a></li>
              <li><a href="${r}index.html?field=1">Skill Graph</a></li>
              <li><a href="${r}starless.html">Starless</a></li>
              <li><a href="${r}meta.html">Meta Changelog</a></li>
            </ul>
          </div>

          <div class="footer-col">
            <span class="footer-col-heading">Discover</span>
            <ul>
              <li><a href="${r}codex.html">The Codex</a></li>
              <li><a href="${r}named/">Named Skills</a></li>
              <li><a href="${r}u/">Named Contributors</a></li>
              <li><a href="${r}badges/">GitHub Badges</a></li>
            </ul>
          </div>

          <div class="footer-col">
            <span class="footer-col-heading">Evidence</span>
            <ul>
              <li><a href="${r}benchmarks/">Benchmarks</a></li>
              <li><a href="${r}reports/">Weekly Reports</a></li>
              <li><a href="${r}trending/">Trending</a></li>
              <li><a href="${r}heroes/">Hall of Heroes</a></li>
            </ul>
          </div>

          <div class="footer-col">
            <span class="footer-col-heading">Docs</span>
            <ul>
              <li><a href="${r}en/">Docs Home</a></li>
              <li><a href="${r}en/getting-started.html">Getting Started</a></li>
              <li><a href="${r}en/cli-reference.html">CLI Reference</a></li>
            </ul>
          </div>

          <div class="footer-col">
            <span class="footer-col-heading">Contribute</span>
            <ul>
              <li><a href="${r}index.html#paths">Push a skill</a></li>
              <li><a href="https://github.com/gaia-research/gaia-skill-tree" target="_blank" rel="noopener" class="footer-ext">GitHub</a></li>
              <li><a href="https://github.com/gaia-research/gaia-skill-tree/issues" target="_blank" rel="noopener" class="footer-ext">Open Issues</a></li>
            </ul>
          </div>

          <div class="footer-col">
            <span class="footer-col-heading">About</span>
            <ul>
              <li><a href="${r}about.html">About Gaia</a></li>
              <li><a href="https://github.com/mbtiongson1" target="_blank" rel="noopener" class="footer-link-honor">@mbtiongson1</a></li>
              <li><a href="${r}privacy.html">Privacy</a></li>
              <li>
                <button id="copyAgentFooterBtn" type="button" class="footer-link-btn" aria-label="Copy page context for agents">
                  Copy Page
                </button>
              </li>
            </ul>
          </div>

        </nav>
      </div>

      <div class="footer-bottom">
        <svg class="ico footer-seal" width="16" height="16" aria-hidden="true">
          <use href="${r}assets/icons.svg#seal-diamond"/>
        </svg>
        <span class="footer-bottom-sep">—</span>
        <span>Gaia Registry</span>
        <span class="footer-bottom-sep">·</span>
        <a href="https://github.com/gaia-research/gaia-skill-tree" target="_blank" rel="noopener">GitHub</a>
        <span class="footer-bottom-sep">·</span>
        <a href="${r}privacy.html">Privacy</a>
      </div>
    </footer>
  `;
})();
