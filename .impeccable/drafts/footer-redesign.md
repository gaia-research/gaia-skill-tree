# Footer Redesign — Design Draft

**Affects:** All pages using the shared `<footer>` block (index.html, codex.html, starless.html, meta.html, privacy.html, about.html, badges/index.html, and generated profile pages)  
**Status:** Draft — requires CSS addition to `docs/css/styles.css` and HTML swap in each template  
**Branch prefix:** `design/footer-v2` (per branch-scope.yml: `design/` for `docs/` HTML/CSS/JS)

---

## Design rationale

The current footer is a single centered paragraph of dot-separated links — functional, but too thin to hold the growing site. As pages multiply (About, Meta Reports, Badges, Samples, contributor profiles), visitors need a structured way to navigate the full surface from the footer.

**Structure.** Four labeled columns: *Registry* (primary navigation), *Discover* (content destinations), *Contribute* (action paths), *About* (provenance and identity). A brand block on the left anchors the whole thing with the seal + wordmark + one-line tagline.

**Column headings.** Italic EB Garamond in `var(--muted)` — not uppercase tracked eyebrows (banned), not bold. This matches the "19th-century atlas plate section label" register: a quiet category marker, not a shout.

**Honor Red.** Used only for the `@mbtiongson1` handle link in the About column — consistent with the brand rule that Honor Red is reserved for contributor attribution.

**Bottom strip.** Mono font, subdued, carries license + version + copyright. The `Copy Page` button (agent context copy utility) moves here from the inline link paragraph.

**No glassmorphism, no gradient text, no cards.** The footer is a ledger closing page, not a marketing close section.

**Responsive.** 2-column brand+links layout on wide screens. Collapses to brand-over-2×2-grid on tablet, then brand-over-2×2 on mobile. Columns stay readable at any breakpoint.

---

## Step 1 — Add CSS to `docs/css/styles.css`

Add the following block after the existing `/* ── FOOTER ENHANCEMENT ── */` block (currently around line 5302). The `.footer-v2` class on the `<footer>` element scopes all new rules so the old styles don't conflict during rollout.

```css
/* ─────────────────────────────────────────────────────────────
   FOOTER v2 — multi-column ledger footer
   Add class="footer-v2" to every <footer> element to activate.
   ───────────────────────────────────────────────────────────── */

footer.footer-v2 {
  text-align: left;
  padding: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(15, 23, 42, .55) 100%);
}

footer.footer-v2::before {
  width: 60%;
}

.footer-v2 .footer-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: clamp(3rem, 6vw, 5rem) clamp(1.5rem, 4vw, 2.5rem) clamp(2.5rem, 5vw, 4rem);
  display: grid;
  grid-template-columns: minmax(170px, 230px) 1fr;
  gap: 3rem 4rem;
  align-items: start;
}

/* Brand column */
.footer-v2 .footer-brand-col {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.footer-v2 .footer-brand-mark {
  display: flex;
  align-items: center;
  gap: .6rem;
}

.footer-v2 .footer-seal {
  width: 26px;
  height: 26px;
}

.footer-v2 .footer-wordmark {
  font-size: 1.15rem;
}

.footer-v2 .footer-tagline {
  font-family: var(--font-body);
  font-size: .8rem;
  line-height: 1.6;
  color: var(--muted);
  margin: 0;
}

/* Link columns grid */
.footer-v2 .footer-cols {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 2rem;
  align-items: start;
}

.footer-v2 .footer-col {
  display: flex;
  flex-direction: column;
  gap: .7rem;
}

.footer-v2 .footer-col-heading {
  font-family: var(--font-display);
  font-style: italic;
  font-size: .875rem;
  font-weight: 400;
  color: var(--muted);
  letter-spacing: .01em;
  line-height: 1;
}

.footer-v2 .footer-col ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: .45rem;
}

.footer-v2 .footer-col ul li a,
.footer-v2 .footer-col ul li button.footer-link-btn {
  font-family: var(--font-body);
  font-size: .82rem;
  color: var(--muted);
  text-decoration: none;
  transition: color .18s;
  display: inline;
}

.footer-v2 .footer-col ul li a:hover,
.footer-v2 .footer-col ul li button.footer-link-btn:hover {
  color: var(--text);
}

/* Honor attribution — contributor handle only */
.footer-v2 .footer-link-honor {
  color: var(--honor-red) !important;
}

.footer-v2 .footer-link-honor:hover {
  color: var(--text) !important;
}

/* External link indicator */
.footer-v2 .footer-ext::after {
  content: ' ↗';
  font-size: .75em;
  opacity: .6;
}

/* Bottom strip */
.footer-v2 .footer-bottom {
  border-top: 1px solid var(--border);
  padding: 1.1rem clamp(1.5rem, 4vw, 2.5rem);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: .75rem;
  font-family: var(--font-mono);
  font-size: .7rem;
  color: var(--muted);
  flex-wrap: wrap;
  text-align: center;
}

.footer-v2 .footer-bottom-sep {
  color: var(--border);
  user-select: none;
}

/* Responsive */
@media (max-width: 900px) {
  .footer-v2 .footer-inner {
    grid-template-columns: 1fr;
    gap: 2.5rem;
  }
  .footer-v2 .footer-cols {
    grid-template-columns: repeat(2, 1fr);
    gap: 1.75rem 2.5rem;
  }
}

@media (max-width: 520px) {
  .footer-v2 .footer-cols {
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
  }
}
```

---

## Step 2 — Replace `<footer>` HTML in every template

Replace the current `<footer>…</footer>` block with the following. The `class="footer-v2"` activates all new styles while the existing base `footer` rules stay in place as a neutral fallback.

> **Note on `id="copyAgentFooterBtn"`:** This ID is referenced by `js/atlas-helpers.js` and `js/ui.js`. Keep it in place in every footer instance. The button moves to the About column's list.

> **Note on version string:** The `data-version` span is readable; wire `footerVersion` to `window.GAIA_VERSION` via a one-liner in `ui.js` if live versioning is wanted (see comment in HTML below).

```html
<!-- ─── FOOTER v2 ─── -->
<footer class="footer-v2">
  <div class="footer-inner">

    <!-- Brand column -->
    <div class="footer-brand-col">
      <div class="footer-brand-mark">
        <svg class="ico footer-seal" aria-hidden="true" focusable="false">
          <use href="assets/icons.svg#seal-diamond"/>
        </svg>
        <span class="footer-wordmark">Gaia</span>
      </div>
      <p class="footer-tagline">An evidence-backed atlas<br>of agent capabilities.</p>
    </div>

    <!-- Link columns -->
    <nav class="footer-cols" aria-label="Site navigation">

      <div class="footer-col">
        <span class="footer-col-heading">Registry</span>
        <ul>
          <li><a href="index.html">Home</a></li>
          <li><a href="index.html">Skill Tree</a></li>
          <li><a href="index.html">Skill Graph</a></li>
          <li><a href="starless.html">Starless</a></li>
          <li><a href="meta.html">Meta Reports</a></li>
        </ul>
      </div>

      <div class="footer-col">
        <span class="footer-col-heading">Discover</span>
        <ul>
          <li><a href="codex.html">The Codex</a></li>
          <li><a href="index.html#named">Named Skills</a></li>
          <li><a href="index.html#hall-of-heroes">Hall of Heroes</a></li>
          <li><a href="badges/">GitHub Badges</a></li>
          <li><a href="samples/index.html">Samples</a></li>
        </ul>
      </div>

      <div class="footer-col">
        <span class="footer-col-heading">Contribute</span>
        <ul>
          <li><a href="index.html#paths">Submit a Skill</a></li>
          <li><a href="https://github.com/mbtiongson1/gaia-skill-tree" target="_blank" rel="noopener" class="footer-ext">GitHub</a></li>
          <li><a href="https://github.com/mbtiongson1/gaia-skill-tree/issues" target="_blank" rel="noopener" class="footer-ext">Open Issues</a></li>
        </ul>
      </div>

      <div class="footer-col">
        <span class="footer-col-heading">About</span>
        <ul>
          <li><a href="about.html">About Gaia</a></li>
          <li><a href="u/mbtiongson1/" class="footer-link-honor">@mbtiongson1</a></li>
          <li><a href="privacy.html">Privacy</a></li>
          <li>
            <button id="copyAgentFooterBtn" type="button" class="footer-link-btn" aria-label="Copy page context for agents">
              Copy Page
            </button>
          </li>
        </ul>
      </div>

    </nav>
  </div>

  <!-- Bottom strip -->
  <div class="footer-bottom">
    <span>MIT License</span>
    <span class="footer-bottom-sep" aria-hidden="true">·</span>
    <!-- Optionally wire to window.GAIA_VERSION via ui.js: document.getElementById('footerVersion').textContent = 'v' + window.GAIA_VERSION -->
    <span id="footerVersion">v4.1.2</span>
    <span class="footer-bottom-sep" aria-hidden="true">·</span>
    <span>© 2026 Gaia</span>
  </div>
</footer>
```

---

## Step 3 — Update generated profile pages

Profile pages (`docs/u/*/index.html`) are generated by `scripts/generateProfilePages.py`. Update the footer template string in that script to use the `footer-v2` structure. Asset paths in profile pages use `../../` prefixes — update `href` and `src` values accordingly:

- `assets/icons.svg#seal-diamond` → `../../assets/icons.svg#seal-diamond`
- `index.html` → `../../`  (or `../../index.html`)
- `codex.html` → `../../codex.html`
- `starless.html` → `../../starless.html`
- `meta.html` → `../../meta.html`
- `badges/` → `../../badges/`
- `about.html` → `../../about.html`
- `u/mbtiongson1/` → `../../u/mbtiongson1/`
- `privacy.html` → `../../privacy.html`
- `samples/index.html` → `../../samples/index.html`

---

## Pages to update (checklist)

- [ ] `docs/index.html`
- [ ] `docs/codex.html`
- [ ] `docs/starless.html`
- [ ] `docs/meta.html`
- [ ] `docs/privacy.html`
- [ ] `docs/about.html` (new — uses this footer by default)
- [ ] `docs/badges/index.html`
- [ ] `scripts/generateProfilePages.py` (template update)
- [ ] Any other pages in `docs/` with a `<footer>` block
