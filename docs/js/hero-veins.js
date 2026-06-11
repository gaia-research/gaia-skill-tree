/* hero-veins.js
 *
 * Pointer-tracking + procedural SVG generation for the hero peek/glow
 * and nav vein effects defined in docs/css/hero-veins.css.
 *
 * Public API:
 *   initHeroVeins(heroEl)              — pointer tracker on #hero
 *   initNavVeins(navEl, opts)          — generate veins + tracker on <nav>
 *   regenerateNavVeins(navEl, opts)    — for resize / debug-panel re-runs
 *
 * Auto-initializes on DOMContentLoaded if document.body has the
 * [data-hero-veins] attribute. The sample page (docs/samples/nav.html)
 * deliberately omits that attribute and calls the named exports directly,
 * so the sample owns the lifecycle.
 *
 * Decisions documented in
 *   ~/.claude/plans/i-need-animation-on-spicy-nygaard.md
 */

const SVG_NS = 'http://www.w3.org/2000/svg';

/* On touch-only devices, pointerleave fires the moment the finger lifts.
 * That kills the aperture instantly and feels broken. Decision 4: linger
 * for a beat after the last touch event. */
const TOUCH_LINGER_MS = 1600;

/* ── Pointer tracker ──────────────────────────────────────────────── */

function attachPointerTracker(el, varX, varY) {
  let pendingX = 0;
  let pendingY = 0;
  let queued = false;
  const isTouchOnly =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(hover: none)').matches;

  const flush = () => {
    el.style.setProperty(varX, pendingX + 'px');
    el.style.setProperty(varY, pendingY + 'px');
    queued = false;
  };

  const onMove = (e) => {
    const r = el.getBoundingClientRect();
    pendingX = e.clientX - r.left;
    pendingY = e.clientY - r.top;
    if (!queued) {
      queued = true;
      requestAnimationFrame(flush);
    }
    // Any movement counts as "still hovering" on touch.
    if (isTouchOnly) {
      el.dataset.hover = '1';
      scheduleLingerOff();
    }
  };

  let lingerTimer = 0;
  const scheduleLingerOff = () => {
    if (lingerTimer) clearTimeout(lingerTimer);
    lingerTimer = setTimeout(() => {
      el.dataset.hover = '0';
      lingerTimer = 0;
    }, TOUCH_LINGER_MS);
  };

  el.addEventListener('pointermove', onMove, { passive: true });

  if (isTouchOnly) {
    // Tap-driven: treat any pointerdown as enter, fade out on linger.
    el.addEventListener(
      'pointerdown',
      (e) => {
        const r = el.getBoundingClientRect();
        pendingX = e.clientX - r.left;
        pendingY = e.clientY - r.top;
        if (!queued) {
          queued = true;
          requestAnimationFrame(flush);
        }
        el.dataset.hover = '1';
        scheduleLingerOff();
      },
      { passive: true }
    );
  } else {
    el.addEventListener('pointerenter', () => {
      el.dataset.hover = '1';
    });
    el.addEventListener('pointerleave', () => {
      el.dataset.hover = '0';
    });
  }
}

/* ── Hero ─────────────────────────────────────────────────────────── */

export function initHeroVeins(heroEl) {
  if (!heroEl) return;
  if (heroEl.dataset.heroVeinsBound === '1') return;
  heroEl.dataset.heroVeinsBound = '1';
  // Make sure the hover attribute starts in a known state (CSS gates the
  // mask removal on [data-hover="1"], not on the absence of the attribute).
  heroEl.dataset.hover = heroEl.dataset.hover || '0';
  attachPointerTracker(heroEl, '--hero-mx', '--hero-my');
}

/* ── Nav: SVG vein generator ──────────────────────────────────────── */

/* Deterministic-ish jitter that doesn't depend on Math.random per call —
 * useful so two runs at the same width produce visually similar layouts.
 * (Math.random is fine here; just keep it predictable enough that resize
 * regen doesn't strobe.) */
function jitter(amount, seed) {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return (x - Math.floor(x) - 0.5) * 2 * amount;
}

function buildVeinSvg(width, height, opts) {
  const {
    nodeCount = 18,
    columns = 5,
    rows = 3,
    yJitter = 12,
    xJitter = 14,
  } = opts;

  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
  svg.setAttribute('aria-hidden', 'true');

  // Lay nodes onto a column×row lattice with jitter.
  const padX = 24;
  const usableW = Math.max(1, width - padX * 2);
  const colGap = usableW / Math.max(1, columns - 1);
  const padY = Math.max(8, height * 0.18);
  const usableH = Math.max(1, height - padY * 2);
  const rowGap = usableH / Math.max(1, rows - 1);

  const nodes = [];
  let seed = 1;
  // Distribute nodeCount across columns roughly evenly.
  const perColumnCounts = new Array(columns).fill(0);
  for (let i = 0; i < nodeCount; i++) {
    perColumnCounts[i % columns]++;
  }

  for (let c = 0; c < columns; c++) {
    const count = perColumnCounts[c];
    for (let i = 0; i < count; i++) {
      const baseX = padX + c * colGap + jitter(xJitter, seed++);
      // Spread the column's nodes vertically across the rows.
      const rowSlot = count === 1 ? (rows - 1) / 2 : (i * (rows - 1)) / (count - 1);
      const baseY = padY + rowSlot * rowGap + jitter(yJitter, seed++);
      nodes.push({ col: c, x: baseX, y: baseY });
    }
  }

  // Build edges: each node connects to 1-2 nodes in the next column.
  const byColumn = new Map();
  nodes.forEach((n) => {
    if (!byColumn.has(n.col)) byColumn.set(n.col, []);
    byColumn.get(n.col).push(n);
  });

  const edges = [];
  for (let c = 0; c < columns - 1; c++) {
    const fromCol = byColumn.get(c) || [];
    const toCol = byColumn.get(c + 1) || [];
    if (toCol.length === 0) continue;
    fromCol.forEach((from, idx) => {
      // Primary connection: nearest in the next column.
      const sorted = [...toCol].sort(
        (a, b) => Math.abs(a.y - from.y) - Math.abs(b.y - from.y)
      );
      edges.push({ from, to: sorted[0] });
      // Optional Y-branch: ~50% of nodes get a second forward link.
      if (sorted.length > 1 && (idx + c) % 2 === 0) {
        edges.push({ from, to: sorted[1] });
      }
    });
  }

  // Render edges first so nodes draw on top.
  edges.forEach((edge, i) => {
    const path = document.createElementNS(SVG_NS, 'path');
    const dx = edge.to.x - edge.from.x;
    const handle = Math.max(40, dx * 0.5);
    const verticalOffset = jitter(8, i + 100);
    const cx1 = edge.from.x + handle;
    const cy1 = edge.from.y + verticalOffset;
    const cx2 = edge.to.x - handle;
    const cy2 = edge.to.y - verticalOffset;
    path.setAttribute(
      'd',
      `M ${edge.from.x.toFixed(1)} ${edge.from.y.toFixed(1)} ` +
        `C ${cx1.toFixed(1)} ${cy1.toFixed(1)}, ` +
        `${cx2.toFixed(1)} ${cy2.toFixed(1)}, ` +
        `${edge.to.x.toFixed(1)} ${edge.to.y.toFixed(1)}`
    );
    path.setAttribute('style', `--i: ${i};`);
    svg.appendChild(path);
  });

  nodes.forEach((node, i) => {
    const circle = document.createElementNS(SVG_NS, 'circle');
    circle.setAttribute('cx', node.x.toFixed(1));
    circle.setAttribute('cy', node.y.toFixed(1));
    circle.setAttribute('r', '3.5');
    circle.setAttribute('style', `--ni: ${i};`);
    svg.appendChild(circle);
  });

  return svg;
}

/* ── Nav: init + regenerate ───────────────────────────────────────── */

const navResizeObservers = new WeakMap();

export function initNavVeins(navEl, opts = {}) {
  if (!navEl) return;

  let host = navEl.querySelector(':scope > .nav-veins');
  if (!host) {
    host = document.createElement('div');
    host.className = 'nav-veins';
    host.setAttribute('aria-hidden', 'true');
    // Insert AFTER .nav-logo so the sibling-combinator CSS (Effect 3)
    // works. If .nav-logo is missing, fall back to the start of the nav.
    const logo = navEl.querySelector(':scope > .nav-logo');
    if (logo && logo.nextSibling) {
      navEl.insertBefore(host, logo.nextSibling);
    } else if (logo) {
      navEl.appendChild(host);
    } else {
      navEl.insertBefore(host, navEl.firstChild);
    }
  }

  regenerateNavVeins(navEl, opts);

  if (navEl.dataset.heroVeinsBound !== '1') {
    navEl.dataset.heroVeinsBound = '1';
    navEl.dataset.hover = navEl.dataset.hover || '0';
    attachPointerTracker(navEl, '--nav-mx', '--nav-my');

    // Resize: regenerate when the nav width changes meaningfully.
    if (typeof ResizeObserver !== 'undefined') {
      let lastWidth = navEl.clientWidth;
      let resizeTimer = 0;
      const ro = new ResizeObserver(() => {
        if (resizeTimer) clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
          if (Math.abs(navEl.clientWidth - lastWidth) >= 40) {
            lastWidth = navEl.clientWidth;
            regenerateNavVeins(navEl, opts);
          }
        }, 250);
      });
      ro.observe(navEl);
      navResizeObservers.set(navEl, ro);
    }
  }
}

export function regenerateNavVeins(navEl, opts = {}) {
  const host = navEl.querySelector(':scope > .nav-veins');
  if (!host) return;
  const width = Math.max(navEl.clientWidth || 1200, 320);
  const height = Math.max(navEl.clientHeight || 64, 48);
  const svg = buildVeinSvg(width, height, opts);
  // Replace contents in one shot.
  host.replaceChildren(svg);
}

/* ── Auto-init ────────────────────────────────────────────────────── */

function autoInit() {
  if (!document.body || !document.body.hasAttribute('data-hero-veins')) return;
  const hero = document.getElementById('hero') || document.querySelector('[data-hero]');
  const nav = document.querySelector('nav');
  if (hero) initHeroVeins(hero);
  if (nav) initNavVeins(nav);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', autoInit, { once: true });
} else {
  autoInit();
}
