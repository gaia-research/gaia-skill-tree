/**
 * site-footer.js — single source of truth for the main site footer.
 * Renders into <div id="site-footer-mount"> on every page.
 * Auto-detects root path depth from window.location.
 */
(function () {
  const el = document.getElementById('site-footer-mount');
  if (!el) return;

  const MOUNTS = window.GAIA_MOUNTS || ['named', 'en', 'badges', 'u', 'samples', 'graph', 'evidence', 'share', 'trust', 'api', 'codex'];
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
          <div class="footer-brand-mark">
            <svg class="ico footer-seal" aria-hidden="true" focusable="false">
              <use href="${r}assets/icons.svg#seal-diamond"/>
            </svg>
            <span class="footer-wordmark">Gaia</span>
          </div>
          <p class="footer-tagline">An evidence-backed atlas<br>of agent capabilities.</p>
        </div>

        <nav class="footer-cols" aria-label="Site navigation">

          <div class="footer-col">
            <span class="footer-col-heading">Registry</span>
            <ul>
              <li><a href="${r}index.html">Home</a></li>
              <li><a href="${r}index.html">Skill Tree</a></li>
              <li><a href="${r}index.html?field=1">Skill Graph</a></li>
              <li><a href="${r}starless.html">Starless</a></li>
              <li><a href="${r}meta.html">Meta Reports</a></li>
            </ul>
          </div>

          <div class="footer-col">
            <span class="footer-col-heading">Discover</span>
            <ul>
              <li><a href="${r}codex.html">The Codex</a></li>
              <li><a href="${r}named/">Named Skills</a></li>
              <li><a href="${r}index.html#hall-of-heroes">Hall of Heroes</a></li>
              <li><a href="${r}u/">Named Contributors</a></li>
              <li><a href="${r}badges/">GitHub Badges</a></li>
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
              <li><a href="https://github.com/mbtiongson1/gaia-skill-tree" target="_blank" rel="noopener" class="footer-ext">GitHub</a></li>
              <li><a href="https://github.com/mbtiongson1/gaia-skill-tree/issues" target="_blank" rel="noopener" class="footer-ext">Open Issues</a></li>
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
        <a href="https://github.com/mbtiongson1/gaia-skill-tree" target="_blank" rel="noopener">GitHub</a>
        <span class="footer-bottom-sep">·</span>
        <a href="${r}privacy.html">Privacy</a>
      </div>
    </footer>
  `;
})();
