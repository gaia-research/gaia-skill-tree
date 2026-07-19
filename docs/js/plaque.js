/* Gaia Plaque component family — Stage 3.
 *
 * Single source of truth for every plaque variant. One field-helper set
 * powers six render methods (mini / tile / row / detail / settled / og).
 * Only variant chrome — layout + which slots are visible — differs.
 *
 *   plaque.renderMini(ns, opts)      // HoH track plate
 *   plaque.renderTile(ns, opts)      // explorer grid card
 *   plaque.renderRow(ns, opts)       // explorer list row
 *   plaque.renderDetail(ns, opts)    // explorer modal hero (two-column)
 *   plaque.renderSettled(ns, opts)   // profile trophy card
 *   plaque.renderOg(ns, opts)        // 1200×630 social card (HTML mock;
 *                                     the canonical OG is server-rendered
 *                                     by scripts/generateOgCards.py)
 *
 * All variants emit `.plaque` + `.plaque--<variant>` with the DERIVED
 * `data-branch="<standard|suite|unique>"` (rubric E1 — computed at read-time
 * via window.GaiaSemantics, never from ns.type) plus `data-level="N"`. A
 * legacy `data-type="<basic|fusion>"` is retained for old hooks only; visual
 * selectors key on data-branch. Apex (6★) adds `plaque--apex-vi` for the
 * rainbow shimmer shadow animation defined in plaque.css.
 *
 * Forbidden: inline SVG strings, inline hex codes, inline rank chips.
 * - Icons: window.gaiaIcon(id, opts).
 * - Rank surfaces: window.rankBadge(level, opts).
 * - Slug/handle/profile helpers: window.namedSlug / window.handleLink.
 *
 * Loaded AFTER icons.js and rank-badge.js, BEFORE named-skills.js,
 * skill-explorer.js, page-ia.js.
 */
(function () {
  'use strict';

  // ── shared utilities ──────────────────────────────────────────────
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function jsStr(s) {
    return String(s == null ? '' : s).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
  }

  function levelNum(level) {
    if (level == null) return 0;
    if (typeof level === 'number') return level | 0;
    var n = parseInt(String(level).replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : Math.max(0, Math.min(6, n));
  }

  function icon(id, size) {
    return (typeof window.gaiaIcon === 'function')
      ? window.gaiaIcon(id, { size: size || 14 })
      : '<svg class="ico" width="' + (size || 14) + '" height="' + (size || 14) + '" aria-hidden="true"></svg>';
  }

  function rankBadge(level, opts) {
    if (typeof window.rankBadge !== 'function') return '';
    return window.rankBadge(level, opts || {});
  }

  // ── Yggdrasil II read-time semantics ─────────────────────────────
  // Branch/rankWord are READ from the emitted fields the taxonomy authority
  // resolved onto the entry (docs/graph/named/index.json), via the shared
  // GaiaSemantics seam (docs/js/skill-semantics.js). Rubric E1: no switching on
  // ns.type. Fallback keeps plaques rendering if skill-semantics.js somehow
  // failed to load (degrade to the standard branch) or on a starless entry with
  // no emitted branch.
  function branchOf(ns) {
    if (window.GaiaSemantics && typeof window.GaiaSemantics.branchOf === 'function') {
      return window.GaiaSemantics.branchOf(ns);
    }
    return 'standard';
  }

  function rankWordOf(level, branch, ns) {
    if (window.GaiaSemantics && typeof window.GaiaSemantics.rankWordOf === 'function' && ns) {
      return window.GaiaSemantics.rankWordOf(ns);
    }
    if (window.GaiaSemantics && typeof window.GaiaSemantics.rankWord === 'function') {
      return window.GaiaSemantics.rankWord(level, branch);
    }
    return '';
  }

  // Branch-keyed glyph + sort priority for the multi-skill stack variants
  // (mini-stack, hall plate). Rubric E1: keyed by the DERIVED branch, never by
  // ns.type. Glyphs mirror the tokens.css tier symbols (unique ◉, suite ◆,
  // standard ○). Sort priority ranks the flashier branches first within a
  // level tie (unique → suite → standard).
  var BRANCH_GLYPH = { unique: '◉', suite: '◆', standard: '○' };
  var BRANCH_SORT = { unique: 0, suite: 1, standard: 2 };

  // ── AOV4 medallion resolver ──────────────────────────────────────
  // The rank medallion IS the Ascension-Overdrive v4 stamp. Suite/standard
  // branches use the C family (c1..c6); the Unique branch uses the D family
  // (d4..d6). Size tier (badge/card/hero) is picked by the render variant.
  var AOV_SUITE_STEM = {
    1: 'c1-suite-awakened', 2: 'c2-suite-named', 3: 'c3-suite-evolved',
    4: 'c4-suite-extra', 5: 'c5-suite-ultimate', 6: 'c6-suite-apex',
  };
  var AOV_UNIQUE_STEM = {
    4: 'd4-unique', 5: 'd5-unique-ultimate', 6: 'd6-unique-impossible',
  };

  // Base path prefix ('' at site root, '../../' on profile pages). Reuses the
  // same derivation the icon sprite uses so relative asset URLs resolve on
  // every page depth.
  function _base() {
    return (typeof window.gaiaIconBase === 'function')
      ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
      : '';
  }

  // Resolve an AOV4 stamp URL for a branch + rank at a given size tier.
  function _aovStamp(branch, n, tier) {
    tier = (tier === 'badge' || tier === 'card' || tier === 'hero') ? tier : 'card';
    var stem;
    if (branch === 'unique') {
      stem = AOV_UNIQUE_STEM[Math.max(4, Math.min(6, n))];
    } else {
      stem = AOV_SUITE_STEM[Math.max(1, Math.min(6, n))];
    }
    return _base() + 'assets/ascension-overdrive/aov4-' + stem + '-' + tier + '.webp';
  }

  // Map the legacy CSS size modifier to an AOV size tier.
  //   'sm' → badge · 'lg' → hero · (none) → card
  function _sizeTier(sizeModifier) {
    if (sizeModifier === 'sm') return 'badge';
    if (sizeModifier === 'lg') return 'hero';
    return 'card';
  }


  function namedSlug(ns) {
    if (typeof window.namedSlug === 'function' && window.namedSlug !== namedSlug) return window.namedSlug(ns);
    if (!ns) return '';
    var id = ns.id || '';
    if (id.indexOf('/') !== -1) return '/' + id.split('/', 2)[1];
    return '/' + (ns.genericSkillRef || id || '');
  }

  function handleLink(handle, opts) {
    if (typeof window.handleLink === 'function' && window.handleLink !== handleLink) return window.handleLink(handle || '', opts || {});
    if (!handle) return '';
    var cls = 'atlas-handle' + (opts && opts.extraClass ? ' ' + opts.extraClass : '');
    var rel = (opts && opts.rel);
    if (!rel) {
      var prefix = (typeof window.gaiaIconBase === 'function')
        ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
        : '';
      rel = prefix + 'u/';
    }
    return '<a class="' + esc(cls) + '" href="' + esc(rel + encodeURIComponent(handle) + '/') + '">@' + esc(handle) + '</a>';
  }

  // ── shared field helpers (one source of truth) ───────────────────
  // Each field helper returns HTML for that slot. Variants opt in/out
  // by including or skipping the slot in their render method — variant
  // chrome lives in CSS, never JS.

  function _fieldOrb(ns, sizeModifier) {
    var branch = branchOf(ns);
    var n = levelNum(ns && ns.level);
    var mod = sizeModifier ? ' plaque-orb--' + sizeModifier : '';
    var apex = n >= 6 ? ' plaque-orb--vi' : '';
    // The medallion IS the AOV4 stamp (rubric E3): no CSS-gradient orb
    // stand-in on named skills. Branch (suite/unique) + rank pick the asset;
    // the surface's size modifier picks badge/card/hero. Standard-branch
    // named skills (rank 1..3) render the c1..c3 suite stamps.
    var tier = _sizeTier(sizeModifier);
    var src = _aovStamp(branch, n, tier);
    var rankName = rankWordOf(ns && ns.level, branch, ns);
    var alt = rankName ? rankName + ' medallion' : 'rank medallion';
    // Decorative but rank-bearing: keep an accessible label. onerror keeps the
    // element in flow (no empty hole) — falls back to the tier orb styling.
    return '<span class="plaque-orb plaque-orb--medallion plaque-orb--' + esc(branch) + mod + apex +
      '" data-branch="' + esc(branch) + '" role="img" aria-label="' + esc(alt) + '">' +
      '<img class="plaque-orb__stamp" src="' + esc(src) + '" alt="" decoding="async" loading="lazy" ' +
      'onerror="this.style.display=\'none\';this.parentNode.setAttribute(\'data-stamp-fail\',\'true\')">' +
      '</span>';
  }

  function _fieldSlug(ns) {
    var slug = namedSlug(ns);
    var id = ns && ns.id || '';
    var prefix = (typeof window.gaiaIconBase === 'function')
      ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
      : '';
    var href = prefix + 'named/#explorer/' + encodeURIComponent(id).replace(/%2F/g, '/');
    return '<a class="plaque__slug plaque-skill-name named-slug" href="' + esc(href) + '" title="' + esc(id) + '" onclick="event.stopPropagation();">' + esc(slug) + '</a>';
  }

  function _fieldTitle(ns) {
    var title = ns && (ns.title || ns.name) || '';
    if (!title) return '';
    return '<div class="plaque__title plaque-title">' + esc(title) + '</div>';
  }

  function _fieldHandleRow(ns) {
    var contributor = ns && ns.contributor || '';
    // No contributor → unclaimed/ghost skill: no handle row at all (never show
    // a redaction marker where there is no handle to hide).
    if (!contributor) return '';
    var level = ns && ns.level;
    // Pre-named/demoted (≤1★): redact the handle (slate, no honor-red link).
    // A pre-named skill has no Origin standing.
    if (window.isRedacted && window.isRedacted(level)) {
      return '<div class="plaque__handle plaque-contrib-row">' + window.redactedHandle() + '</div>';
    }
    var contribLink = handleLink(contributor, { level: level });
    if (!contribLink) return '';
    // Rubric E4: the red inline origin mark is gone — Origin now renders in
    // GOLD as the wreath framing the contributor avatar (_fieldAvatar).
    return '<div class="plaque__handle plaque-contrib-row">' + contribLink + '</div>';
  }

  // ── contributor avatar framed by the gold origin wreath (E3/E4) ──
  // Every skill surface renders the contributor's GitHub avatar, framed by
  // the gold origin wreath (docs/assets/origin-wreath-gold.svg) — this is the
  // NEW origin mark (red → gold). The avatar links to the skill's repo
  // (links.github), replacing the standalone GitHub button.
  //
  // Fallback: a missing avatar swaps to the GitHub identicon endpoint
  // (github.com/identicons/<handle>.png), NEVER hides the img (no empty hole).
  //
  // Redacted (≤1★) skills expose no handle → no avatar (handle is withheld
  // everywhere else too; showing a resolvable avatar would leak the handle).
  //   opts.size   px for the avatar (default 40)
  function _fieldAvatar(ns, opts) {
    opts = opts || {};
    var handle = (ns && ns.contributor) || '';
    if (!handle) return '';
    if (window.isRedacted && window.isRedacted(ns && ns.level)) return '';
    var clean = String(handle).replace(/^@/, '');
    var size = opts.size || 40;
    var wreathSrc = _base() + 'assets/origin-wreath-gold.svg';
    var avatarSrc = 'https://github.com/' + encodeURIComponent(clean) + '.png?size=' + (size * 2);
    var identicon = 'https://github.com/identicons/' + encodeURIComponent(clean) + '.png';
    var links = (ns && ns.links) || {};
    var repoUrl = links.github || links.npm || '';
    var isOrigin = !!(ns && ns.origin);
    var title = isOrigin ? 'Origin contributor @' + clean : '@' + clean;
    // onerror: fall back to the identicon once, then stop (avoid loops). Never
    // set display:none — the frame must never render as an empty hole.
    var errAttr = "if(this.dataset.fbk){this.onerror=null;}else{this.dataset.fbk='1';this.src='" +
      jsStr(identicon) + "';}";
    var img = '<img class="plaque__avatar-img" src="' + esc(avatarSrc) + '" ' +
      'alt="" decoding="async" loading="lazy" referrerpolicy="no-referrer" ' +
      'onerror="' + errAttr + '">';
    var wreath = '<img class="plaque__avatar-wreath" src="' + esc(wreathSrc) + '" alt="" aria-hidden="true">';
    var inner = img + wreath;
    var body;
    if (repoUrl) {
      body = '<a class="plaque__avatar plaque__avatar--link" href="' + esc(repoUrl) + '" ' +
        'target="_blank" rel="noopener" title="' + esc(title) + '" ' +
        'aria-label="' + esc(title) + ' — view repository" ' +
        'onclick="event.stopPropagation()" style="--avatar-size:' + (size | 0) + 'px"' +
        (isOrigin ? ' data-origin="true"' : '') + '>' + inner + '</a>';
    } else {
      body = '<span class="plaque__avatar" title="' + esc(title) + '" ' +
        'aria-label="' + esc(title) + '" style="--avatar-size:' + (size | 0) + 'px"' +
        (isOrigin ? ' data-origin="true"' : '') + '>' + inner + '</span>';
    }
    return body;
  }

  function _fieldDescription(ns) {
    var desc = ns && ns.description || '';
    if (!desc) return '';
    return '<p class="plaque__description plaque-description">' + esc(desc) + '</p>';
  }

  function _fieldTags(ns, limit) {
    var tags = (ns && Array.isArray(ns.tags)) ? ns.tags : [];
    var cap = (typeof limit === 'number') ? limit : tags.length;
    var sliced = tags.slice(0, cap);
    if (!sliced.length) return '';
    var inner = sliced.map(function (t) {
      return '<span class="plaque__tag plaque-tag">' + esc(t) + '</span>';
    }).join('');
    return '<div class="plaque__tags plaque-tags">' + inner + '</div>';
  }

  function _fieldRank(ns, variant) {
    var v = variant || 'stars';
    // Rubric E1/E2: pass the DERIVED branch (not ns.type) so rank-badge.js
    // colours the stars by branch register (unique = violet, suite = gold).
    var branch = branchOf(ns);
    var html = rankBadge(ns && ns.level, { variant: v, label: ns && ns.level, tier: branch });
    if (!html) return '';
    return '<div class="plaque__rank">' + html + '</div>';
  }

  // Deprecated — the standalone "GitHub" button is removed (rubric E3): the
  // wreathed avatar (_fieldAvatar) is now the repo link. Kept as a no-op so
  // any lingering call site emits nothing rather than a duplicate link.
  function _fieldGhLink(ns) {
    return '';
  }

  function _fieldVariantsBadge(ns) {
    if (!ns || !ns.variants || !ns.variants.length) return '';
    var count = ns.variants.length;
    return '<div class="plaque__variants-badge ns-variants-badge" title="' + count + ' additional implementation(s) available">' +
      '+' + count + ' implementation' + (count > 1 ? 's' : '') +
      '</div>';
  }

  // Deprecated (rubric E4): the honor-red #origin-badge laurel is gone.
  // Origin is now rendered in GOLD as the wreath framing the contributor
  // avatar (_fieldAvatar sets data-origin). No red origin icon survives —
  // this returns nothing so the old inline red mark never renders.
  function _fieldOriginBadge(ns) {
    return '';
  }

  // Install row — shared mini-terminal block (used by tile / detail / settled).
  // The copy button is wired in via inline onclick that delegates to
  // window.nsInstCopy (defined by named-skills.js). If that's not present
  // we fall back to navigator.clipboard inline.
  function _fieldInstallRow(ns) {
    if (!ns || !ns.id || ns.installable === false) return '';
    // Pre-named/demoted (≤1★): withhold the handle in the install command —
    // "gaia install ████████/slug" (lifted once the skill is named at 2★+).
    var installId = ns.id;
    if (window.isRedacted && window.isRedacted(ns.level) && ns.id.indexOf('/') !== -1) {
      installId = (window.REDACTED_BLOCK || '████████') + '/' + ns.id.split('/').slice(1).join('/');
    }
    var cmd = 'gaia install ' + installId;
    var copyClick = 'event.stopPropagation();' +
      'if(typeof window.nsInstCopy===\'function\'){window.nsInstCopy(this);}' +
      'else{navigator.clipboard.writeText(this.dataset.cmd);}';
    return '<div class="plaque__install-row ns-install-row">' +
      '<span class="plaque__install-prompt ns-install-prompt">$</span>' +
      '<span class="plaque__install-cmd ns-install-cmd-txt">' + esc(cmd) + '</span>' +
      '<button class="plaque__install-copy ns-install-copy" type="button" aria-label="Copy install command" title="Copy install command" data-cmd="' + esc(cmd) + '" onclick="' + copyClick + '">' +
      icon('copy', 13) + '</button>' +
      '</div>';
  }

  function _fieldSlugInteractive(ns, onclickAttr) {
    var slug = namedSlug(ns);
    var id = ns && ns.id || '';
    if (onclickAttr) {
      return '<button class="plaque__slug plaque-skill-name named-slug plaque__slug--clickable" type="button" title="' + esc(id) + '" onclick="event.stopPropagation(); ' + onclickAttr + '">' + esc(slug) + '</button>';
    }
    return _fieldSlug(ns);
  }

  function _fieldFullscreenBtn(ns) {
    if (!ns || !ns.id) return '';
    var skillId = ns.id;
    var handle = ns.contributor || '';
    var name = ns.name || '';
    var level = ns.level || '';
    var type = ns.type || '';
    var origin = ns.origin ? 'true' : 'false';
    var desc = ns.description || '';
    var tagsRaw = (ns.tags && ns.tags.length) ? JSON.stringify(ns.tags) : '';
    var slashIdx = skillId.indexOf('/');
    var skillIdShort = slashIdx !== -1 ? skillId.slice(slashIdx + 1) : skillId;
    var ogPath = handle && skillIdShort ? 'og/' + handle + '/' + skillIdShort + '.svg' : '';
    return '<button class="plaque__fs-btn" type="button" aria-label="Fullscreen View" title="Show Fullscreen Social Card" ' +
      'data-skill-id="' + esc(skillId) + '" ' +
      'data-handle="' + esc(handle) + '" ' +
      'data-skill-name="' + esc(name) + '" ' +
      'data-level="' + esc(level) + '" ' +
      'data-type="' + esc(type) + '" ' +
      'data-origin="' + esc(origin) + '" ' +
      'data-desc="' + esc(desc) + '" ' +
      'data-tags="' + esc(tagsRaw) + '" ' +
      'data-og="' + esc(ogPath) + '">' +
      icon('share', 14) +
      '</button>';
  }

  // ── Trust Grade notch field helper (I8) ─────────────────────────
  // ── Trust Grade notch field helper (I8) ─────────────────────────
  // Pixel-thin colored bar flush at the card bottom.
  // On plaque hover: bar expands to full label height, "MAG X.X" counts up
  // from 0 to the real TM in <0.4s.
  //
  // DOM structure:
  //   <div class="plaque__trust-notch" data-trust-grade="A" data-tm="122.8">
  //     <span class="trust-notch-label">MAG <span class="trust-notch-num">0</span></span>
  //   </div>
  //
  // The counter is wired in _wireTrustNotches(), called once per render cycle.
  var GRADE_NAMES = { S: 'Platinum', A: 'Gold', B: 'Silver', C: 'Bronze' };

  function _fieldTrustNotch(ns) {
    var TM = window.TM_CONFIG;
    var tg = (ns && (ns.overallTrustGrade || ns.trustGrade)) || '';
    var tm = (ns && (ns.trustMagnitude || ns.overallTrustMagnitude));
    var tmVal = (tm != null && tm !== '') ? parseFloat(Number(tm).toFixed(1)) : 0;
    if ((!tg || tg === 'ungraded' || !GRADE_NAMES[tg]) && !(tmVal > 0)) return '';
    // Static initial display = the real magnitude (not "0"). Hover triggers a
    // count-up animation that resets to 0 then eases back to tmVal — see
    // _wireTrustNotches(). When _wireTrustNotches isn't called (e.g. plaques
    // injected outside the named-skills.js render path), the static value
    // remains visible so MAG never shows as a literal "0".
    var initialDisplay = tmVal % 1 === 0 ? String(Math.round(tmVal)) : tmVal.toFixed(1);
    var gradeName = GRADE_NAMES[tg] || 'Ungraded';
    var ariaLabel = 'Trust grade: ' + gradeName + (tmVal > 0 ? ', magnitude ' + tmVal : '');

    // Build (i) tooltip from TM_CONFIG when available; degrade gracefully otherwise.
    var tooltipText;
    if (TM) {
      var lines = [];
      lines.push(gradeName + ' (' + tg + ') · MAG ' + (tmVal > 0 ? initialDisplay : '—'));
      lines.push('Aggregate Trust Magnitude — weighted sum across all evidence rows.');
      lines.push('');
      lines.push('Skill grade thresholds:');
      for (var i = 0; i < TM.OVERALL_GRADES.length; i++) {
        var g = TM.OVERALL_GRADES[i];
        var row = '  ' + g.grade + ' (' + g.name + ') · TM ≥ ' + g.floor;
        if (g.note) row += ' — ' + g.note;
        lines.push(row);
      }
      lines.push('  Ungraded · TM < 20');
      lines.push('');
      lines.push('Diversity gate (S only): ≥3 distinct evidence types AND');
      lines.push('  ≥1 non-self-producible type (' +
        TM.SELF_PRODUCIBLE.join(', ') + ' cannot anchor alone).');
      lines.push('');
      lines.push('Evidence cards show per-row artifact scores (pre-weight).');
      lines.push('Full methodology: ' + TM.RFC.grades);
      tooltipText = lines.join('\n');
    } else {
      tooltipText = gradeName + ' (' + tg + ') · MAG ' +
        (tmVal > 0 ? initialDisplay : '—') +
        '\nWeighted aggregate across all evidence rows.' +
        '\nEvidence cards show per-row artifact scores.' +
        '\nhttps://gaiaskilltree.com/trust/#grade-thresholds';
    }

    return '<div class="plaque__trust-notch" data-trust-grade="' + esc(tg || 'none') + '"' +
      ' data-tm="' + esc(String(tmVal)) + '"' +
      ' aria-label="' + esc(ariaLabel) + '"' +
      ' title="' + esc(tooltipText) + '">' +
      '<span class="trust-notch-label">MAG <span class="trust-notch-num">' + esc(initialDisplay) + '</span></span>' +
      '</div>';
  }

  // Wire up the count-up animation for all notches inside a container.
  // Safe to call multiple times — skips already-wired notches.
  function _wireTrustNotches(root) {
    root = root || document;
    var notches = root.querySelectorAll
      ? root.querySelectorAll('.plaque__trust-notch[data-tm]')
      : [];
    for (var i = 0; i < notches.length; i++) {
      (function(notch) {
        if (notch._tmWired) return;
        notch._tmWired = true;
        var target = parseFloat(notch.getAttribute('data-tm')) || 0;
        var numEl = notch.querySelector('.trust-notch-num');
        if (!numEl) return;
        var plaque = notch.closest ? notch.closest('.plaque') : notch.parentElement;
        if (!plaque) return;
        if (plaque.classList.contains('plaque--hall')) return;
        var raf, startTs;
        var DURATION = 380;
        function countUp(ts) {
          if (!startTs) startTs = ts;
          var progress = Math.min((ts - startTs) / DURATION, 1);
          var eased = 1 - (1 - progress) * (1 - progress);
          var current = eased * target;
          numEl.textContent = target % 1 === 0
            ? Math.round(current).toString()
            : current.toFixed(1);
          if (progress < 1) raf = requestAnimationFrame(countUp);
        }
        function onEnter() {
          cancelAnimationFrame(raf);
          startTs = null;
          numEl.textContent = '0';
          raf = requestAnimationFrame(countUp);
        }
        function onLeave() {
          cancelAnimationFrame(raf);
          // Restore the real magnitude on mouse-out (not a bare "0", which
          // would otherwise persist if the user hovered then quickly left).
          numEl.textContent = target % 1 === 0
            ? Math.round(target).toString()
            : target.toFixed(1);
        }
        plaque.addEventListener('mouseenter', onEnter);
        plaque.addEventListener('mouseleave', onLeave);
      }(notches[i]));
    }
  }

  if (typeof window !== 'undefined') window._wireTrustNotches = _wireTrustNotches;

  // ── plaque shell ─────────────────────────────────────────────────
  function _shell(variant, ns, innerHtml, extraOpts) {
    var type = (ns && ns.type) || 'basic';
    var branch = branchOf(ns);
    var n = levelNum(ns && ns.level);
    var apex = n >= 6 ? ' plaque--apex-vi' : '';
    extraOpts = extraOpts || {};
    var extraCls = extraOpts.extraClass ? ' ' + extraOpts.extraClass : '';
    var clickAttr = '';
    if (ns && ns.id && extraOpts.click !== false) {
      clickAttr = ' onclick="' + (extraOpts.onclick ||
        '(function(id){if(typeof openSkillExplorer===\'function\')openSkillExplorer(id);})(\'' + jsStr(ns.id) + '\')') + '"';
    }
    var role = extraOpts.role ? ' role="' + esc(extraOpts.role) + '" tabindex="0"' : '';
    var extraAttrs = extraOpts.attrs || '';
    // Inject trust notch at card bottom for all variants except mini-stack
    // (mini-stack is a contributor mosaic with multiple skills; HoH individual
    //  cards, tile, settled, row, og, detail, and hall all show the notch).
    var isMiniStack = extraOpts.extraClass &&
      extraOpts.extraClass.indexOf('plaque--mini-stack') !== -1;
    var trustNotch = (!isMiniStack) ? _fieldTrustNotch(ns) : '';
    // Rubric E3/E1: stamp the DERIVED data-branch (standard|suite|unique).
    // Every downstream visual selector (dark unique / gold suite) keys on
    // data-branch, NOT data-type. data-type is retained for legacy hooks only.
    return '<article class="plaque plaque--' + esc(variant) + apex + extraCls +
      '" data-type="' + esc(type) + '" data-branch="' + esc(branch) +
      '" data-level="' + esc(n) +
      '" data-skill-id="' + esc(ns && ns.id || '') + '"' +
      clickAttr + role + extraAttrs + '>' +
      innerHtml +
      trustNotch +
      '</article>';
  }

  // ── variant: mini (HoH track plate + tree-view DAG node) ────────
  // Field set: orb · slug · handle · rank stars (no description, no tags,
  // no install row).
  // Stage 4 — extra opts supported:
  //   opts.dagId   string  → emits data-id=<dagId> so the Tree-view
  //                          DAG layer can resolve nodes for arrow drawing.
  //   opts.ghost   boolean → emits data-ghost + a hatched-border CSS hook
  //                          (no GitHub icon for ghosts; suppress rank stars).
  //   opts.extraClass / attrs / onclick / click flow through _shell.
  function renderMini(ns, opts) {
    opts = opts || {};
    var isGhost = !!opts.ghost;
    var shellOpts = { click: false };
    var extra = opts.extraClass || '';
    if (isGhost) extra = (extra ? extra + ' ' : '') + 'plaque--ghost';
    if (extra) shellOpts.extraClass = extra;
    var attrs = opts.attrs || '';
    if (opts.dagId) attrs += ' data-id="' + esc(opts.dagId) + '"';
    if (isGhost) attrs += ' data-ghost="true"';
    if (attrs) shellOpts.attrs = attrs;

    var slugOnclick = opts.onclick || ('(function(id){if(typeof openSkillExplorer===\'function\')openSkillExplorer(id);})(\'' + jsStr(ns.id) + '\')');

    var inner =
      _fieldOrb(ns) +
      (isGhost ? '' : _fieldAvatar(ns, { size: 28 })) +
      (isGhost ? '' : _fieldHandleRow(ns)) +
      (isGhost ? '' : _fieldRank(ns, 'stars')) +
      (isGhost ? _fieldSlug(ns) : _fieldSlugInteractive(ns, slugOnclick)) +
      (isGhost ? '' : _fieldFullscreenBtn(ns));

    return _shell('mini', ns, inner, shellOpts);
  }

  // ── variant: tile (explorer grid) ────────────────────────────────
  // Field set: header (medallion + rank chip + wreathed avatar)
  //          · slug · title · handle · description · tags (3) · install row.
  function renderTile(ns, opts) {
    var header =
      '<div class="plaque__header plaque-header">' +
        _fieldOrb(ns) +
        _fieldRank(ns, 'chip') +
        _fieldAvatar(ns, { size: 32 }) +
      '</div>';

    var inner =
      header +
      _fieldSlug(ns) +
      _fieldTitle(ns) +
      _fieldHandleRow(ns) +
      _fieldDescription(ns) +
      _fieldTags(ns, 3) +
      _fieldInstallRow(ns);

    return _shell('tile', ns, inner, opts);
  }

  // ── variant: row (explorer list) ─────────────────────────────────
  // Field set: same as tile, laid horizontally. Description hidden via
  // CSS only — no silent field drops at the JS level.
  function renderRow(ns, opts) {
    var evText = _evidenceClass(ns);
    var evBadge = evText
      ? '<span class="plaque__ev-badge">' + esc(evText) + '</span>'
      : '';
    var inner =
      _fieldOrb(ns, 'sm') +
      _fieldSlug(ns) +
      _fieldTitle(ns) +
      _fieldHandleRow(ns) +
      _fieldTags(ns, 2) +
      _fieldInstallRow(ns) +
      _fieldRank(ns, 'chip') +
      _fieldAvatar(ns, { size: 28 }) +
      evBadge +
      '<span class="plaque__arrow ns-lr-arrow" aria-hidden="true">›</span>';

    return _shell('row', ns, inner, opts);
  }

  // ── variant: detail (explorer modal hero, two-column) ────────────
  // Left column: medallion (lg) · wreathed avatar · slug · handle · rank
  //   (full) · install row · share · claim
  // Right column: title · description · tags
  function renderDetail(ns, opts) {
    opts = opts || {};
    // Pre-named/demoted (≤1★): the repo link, share (OG path) and "Add to
    // README" (badges?u=<handle>) all expose the handle — suppress them until
    // the skill is named (2★+).
    var redacted = window.isRedacted && window.isRedacted(ns && ns.level);

    var skillId = (ns && ns.id) || '';
    var slashIdx = skillId.indexOf('/');
    var skillIdShort = slashIdx !== -1 ? skillId.slice(slashIdx + 1) : skillId;
    var handle = (ns && ns.contributor) || '';
    var skillName = (ns && ns.name) || '';
    var ogPath = handle && skillIdShort ? 'og/' + handle + '/' + skillIdShort + '.svg' : '';
    var shareBtn = redacted ? '' :
      '<button type="button" class="plaque__share-btn" ' +
        'data-skill-id="' + esc(skillId) + '" ' +
        'data-skill-name="' + esc(skillName) + '" ' +
        'data-handle="' + esc(handle) + '" ' +
        'data-og="' + esc(ogPath) + '" ' +
        'aria-label="Share this skill">' +
        icon('share', 14) +
      '</button>';

    // Rubric E3: the standalone "GitHub" button is removed — the wreathed
    // avatar (below) is the repo link. Only the share button remains here.
    var ghRow = shareBtn
      ? '<div class="plaque__gh-row">' + shareBtn + '</div>'
      : '';

    var prefix = (typeof window.gaiaIconBase === 'function')
      ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
      : '';

    var actions = redacted ? '' :
      '<div class="plaque__actions plaque-detail-actions">' +
        '<a class="plaque__claim-btn" ' +
          'href="' + esc(prefix + 'badges/?u=' + encodeURIComponent(handle) + '&s=' + encodeURIComponent(skillIdShort)) + '" ' +
          'target="_blank" rel="noopener">' +
          'Add to README' +
        '</a>' +
      '</div>';

    var left =
      '<div class="plaque__col plaque-detail-left">' +
        _fieldOrb(ns, 'lg') +
        _fieldAvatar(ns, { size: 56 }) +
        _fieldSlug(ns) +
        _fieldHandleRow(ns) +
        _fieldRank(ns, 'stars') +
        _fieldInstallRow(ns) +
        ghRow +
        actions +
      '</div>';

    var right =
      '<div class="plaque__col plaque-detail-right">' +
        _fieldTitle(ns) +
        _fieldDescription(ns) +
        _fieldTags(ns) +
      '</div>';

    // Detail is the modal content — it's not itself clickable.
    var shellOpts = Object.assign({}, opts, { click: false });
    return _shell('detail', ns, left + right, shellOpts);
  }

  // ── variant: settled (profile trophy card) ───────────────────────
  // Tile field set + rank stars + evidence-class chip + gold underline.
  function renderSettled(ns, opts) {
    opts = opts || {};
    var header =
      '<div class="plaque__header plaque-header">' +
        _fieldOrb(ns) +
        _fieldRank(ns, 'chip') +
        _fieldAvatar(ns, { size: 32 }) +
      '</div>';

    var evText = _evidenceClass(ns);
    var evHtml = evText
      ? '<div class="plaque__evidence plaque-evidence">' + esc(evText) + '</div>'
      : '';

    var inner =
      header +
      _fieldSlug(ns) +
      _fieldTitle(ns) +
      _fieldHandleRow(ns) +
      _fieldDescription(ns) +
      _fieldTags(ns, 5) +
      _fieldRank(ns, 'stars') +
      _fieldInstallRow(ns) +
      evHtml +
      '<div class="plaque__underline plaque-underline plaque-underline--settled"></div>';

    return _shell('settled', ns, inner, opts);
  }

  function _evidenceClass(ns) {
    var tg = (ns && (ns.overallTrustGrade || ns.trustGrade)) || '';
    if (tg && tg !== 'ungraded') {
      return 'GRADE ' + tg.toUpperCase();
    }
    return '';
  }

  // ── variant: og (HTML mock of the 1200×630 social card) ──────────
  // The canonical OG card is generated as SVG by generateOgCards.py.
  // This HTML mock exists so the sampler page can show what the OG card
  // looks like in-browser — at scaled-down size — without a raster step.
  function renderOg(ns, opts) {
    opts = opts || {};
    var header =
      '<div class="plaque__header plaque-header">' +
        '<span class="plaque__og-seal">' + icon('seal-diamond', 36) + '</span>' +
        _fieldRank(ns, 'full') +
      '</div>';

    var inner =
      header +
      _fieldOrb(ns, 'lg') +
      _fieldAvatar(ns, { size: 44 }) +
      _fieldSlug(ns) +
      _fieldTitle(ns) +
      _fieldHandleRow(ns) +
      _fieldDescription(ns) +
      _fieldTags(ns, 4) +
      _fieldInstallRow(ns);

    var shellOpts = Object.assign({}, opts, { click: false });
    return _shell('og', ns, inner, shellOpts);
  }

  // ── variant: mini-stack (HoH track plate, multi-skill per contributor) ─
  // Lists up to N qualifying slash-skills for ONE contributor, each in its
  // own row with row-level data-type/data-level so per-skill CSS rules
  // resolve the correct tier/rank colour. The plate's outer data-type +
  // data-level reflect the contributor's PRIMARY (highest-ranked) skill —
  // that's what drives the orb glow + Apex shimmer halo.
  //
  // Inputs:
  //   skills  Array of { id, name, contributor, level, type, origin,
  //                       canonicalId, onclick }  — pre-sorted highest first.
  //   opts.maxRows  default 3.  More than maxRows → "+N more" overflow row.
  function renderMiniStack(skills, opts) {
    opts = opts || {};
    if (!Array.isArray(skills) || !skills.length) return '';
    // Rubric E1: sort by level, then by DERIVED branch (unique → suite →
    // standard) — never by ns.type.
    var sorted = skills.slice().sort(function (a, b) {
      var ld = levelNum(b.level) - levelNum(a.level);
      if (ld !== 0) return ld;
      return (BRANCH_SORT[branchOf(a)] != null ? BRANCH_SORT[branchOf(a)] : 9) -
             (BRANCH_SORT[branchOf(b)] != null ? BRANCH_SORT[branchOf(b)] : 9);
    });
    var primary = sorted[0];
    var maxRows = (typeof opts.maxRows === 'number') ? opts.maxRows : 3;
    var visible = sorted.slice(0, maxRows);
    var overflow = Math.max(0, sorted.length - visible.length);

    var anyOrigin = sorted.some(function (s) { return !!s.origin; });
    var primaryNs = {
      id: primary.id,
      name: primary.name,
      contributor: primary.contributor,
      origin: anyOrigin,
      level: primary.level,
      type: primary.type,
      suiteComponents: primary.suiteComponents,
      links: primary.links,
    };

    var header =
      '<div class="plaque__stack-header">' +
        _fieldOrb(primaryNs) +
        _fieldHandleRow(primaryNs) +
        _fieldAvatar(primaryNs, { size: 28 }) +
        _fieldFullscreenBtn(primaryNs) +
      '</div>';

    var rows = visible.map(function (s) {
      var n = levelNum(s.level);
      var branch = branchOf(s);
      var glyph = BRANCH_GLYPH[branch] || BRANCH_GLYPH.standard;
      var slug = namedSlug(s);
      var slugTitle = s.id || '';
      var clickAttr = s.onclick
        ? 'event.stopPropagation(); ' + s.onclick
        : '(function(id){if(typeof openSkillExplorer===\'function\')openSkillExplorer(id);})(\'' + jsStr(s.canonicalId || s.id) + '\')';
      var stars = rankBadge(s.level, { variant: 'stars', label: s.level, tier: branch });
      return '<div class="plaque__stack-row" data-branch="' + esc(branch) +
        '" data-level="' + esc(n) + '">' +
          '<span class="plaque__stack-glyph tier-glyph" data-branch="' + esc(branch) +
            '" aria-hidden="true">' + glyph + '</span>' +
          '<button class="plaque__slug plaque-skill-name named-slug plaque__slug--clickable" type="button" ' +
            'title="' + esc(slugTitle) + '" onclick="' + clickAttr + '">' + esc(slug) + '</button>' +
          (stars ? '<span class="plaque__stack-rank">' + stars + '</span>' : '') +
        '</div>';
    }).join('');

    var moreRow = overflow
      ? '<div class="plaque__stack-more">+' + overflow + ' more</div>'
      : '';

    var inner = header + '<div class="plaque__stack-body">' + rows + moreRow + '</div>';
    var shellOpts = { click: false, extraClass: 'plaque--mini-stack' };
    return _shell('mini', primaryNs, inner, shellOpts);
  }

  // ── variant: hall (Hall of Heroes redesigned plate) ─────────────
  // Per-contributor plate with:
  //   • celestial-atlas crest medallion (contributor GitHub avatar)
  //   • faint blurred backdrop echo of the primary skill OG art
  //   • Honor Red @handle + share button
  //   • Roman-numeral rank divider for the contributor's primary
  //   • Up to N skill rows, each carrying its own data-type/data-level
  //
  // Featured plates (opts.featured === true) render larger with a
  // Garamond display handle; standard plates use the mono ledger style.
  // The crest <img> falls back to a rendered ring if the OG SVG 404s.
  function renderHallPlate(skills, opts) {
    opts = opts || {};
    if (!Array.isArray(skills) || !skills.length) return '';
    // Rubric E1: sort by level, then by DERIVED branch — never by ns.type.
    var sorted = skills.slice().sort(function (a, b) {
      var ld = levelNum(b.level) - levelNum(a.level);
      if (ld !== 0) return ld;
      return (BRANCH_SORT[branchOf(a)] != null ? BRANCH_SORT[branchOf(a)] : 9) -
             (BRANCH_SORT[branchOf(b)] != null ? BRANCH_SORT[branchOf(b)] : 9);
    });
    var primary = sorted[0];
    var maxRows = (typeof opts.maxRows === 'number') ? opts.maxRows : 3;
    var visible = sorted.slice(0, maxRows);
    var overflow = Math.max(0, sorted.length - visible.length);

    var anyOrigin = sorted.some(function (s) { return !!s.origin; });
    var primaryNs = {
      id: primary.id,
      name: primary.name,
      contributor: primary.contributor,
      origin: anyOrigin,
      level: primary.level,
      type: primary.type,
      suiteComponents: primary.suiteComponents,
      links: primary.links,
      trustMagnitude: primary.trustMagnitude,
    };
    var primaryBranch = branchOf(primary);

    // Resolve OG art path (primary skill).
    var handle = primary.contributor || '';
    var primaryId = primary.id || '';
    var slashIdx = primaryId.indexOf('/');
    var skillSlug = slashIdx !== -1 ? primaryId.slice(slashIdx + 1) : primaryId;
    var ogPath = handle && skillSlug ? 'og/' + handle + '/' + skillSlug + '.svg' : '';
    var avatarUrl = handle
      ? 'https://github.com/' + encodeURIComponent(String(handle).replace(/^@/, '')) + '.png?size=160'
      : '';

    // Backdrop <img> with onerror that flags the parent.
    var artHtml = '';
    if (ogPath) {
      var loadAttr =
        'this.parentNode.parentNode.setAttribute(\'data-art-loaded\',\'true\')';
      var errAttr =
        'this.parentNode.parentNode.setAttribute(\'data-art-loaded\',\'fail\');' +
        'this.style.display=\'none\'';
      artHtml =
        '<div class="plaque__hall-backdrop" aria-hidden="true" role="presentation">' +
          '<img src="' + esc(ogPath) + '" alt="" decoding="async" loading="lazy" ' +
            'onload="' + loadAttr + '" onerror="' + errAttr + '">' +
        '</div>';
    }

    var primaryGlyph = BRANCH_GLYPH[primaryBranch] || BRANCH_GLYPH.standard;
    // Crest uses the contributor's GitHub avatar; the OG art remains as backdrop.
    var crestImg = avatarUrl
      ? '<img class="plaque__hall-crest-img" src="' + esc(avatarUrl) + '" alt="" ' +
          'decoding="async" loading="lazy" referrerpolicy="no-referrer" ' +
          'onerror="this.parentNode.setAttribute(\'data-crest-fail\',\'true\');this.style.display=\'none\'">'
      : '';
    var crestHtml =
      '<div class="plaque__hall-crest" data-branch="' + esc(primaryBranch) + '" ' +
        'data-level="' + esc(levelNum(primary.level)) + '">' +
        crestImg +
        '<span class="plaque__hall-crest-glyph" aria-hidden="true">' + primaryGlyph + '</span>' +
      '</div>';

    // Meta row: handle + share button.
    var metaHtml =
      '<div class="plaque__hall-meta">' +
        _fieldHandleRow(primaryNs) +
        _fieldFullscreenBtn(primaryNs) +
      '</div>';

    // Trust magnitude divider showing trust magnitude instead of Roman numerals
    var tm = primary.trustMagnitude;
    var tmVal = (tm != null && tm !== '') ? parseFloat(Number(tm).toFixed(1)) : 0;
    var tmDisplay = tmVal % 1 === 0 ? String(Math.round(tmVal)) : tmVal.toFixed(1);
    var magText = tmDisplay;
    var dividerHtml =
      '<div class="plaque__hall-divider" aria-hidden="true">' +
        '<span class="plaque__hall-divider-line"></span>' +
        '<span class="plaque__hall-divider-numeral">' + esc(magText) + '</span>' +
        '<span class="plaque__hall-divider-line"></span>' +
      '</div>';

    // Skill rows — reuse the existing .plaque__stack-row markup so the
    // tier-aware per-row CSS in plaque.css just works.
    var rows = visible.map(function (s, idx) {
      var n = levelNum(s.level);
      var branch = branchOf(s);
      var glyph = BRANCH_GLYPH[branch] || BRANCH_GLYPH.standard;
      var slug = namedSlug(s);
      var slugTitle = s.id || '';
      var clickAttr = s.onclick
        ? 'event.stopPropagation(); ' + s.onclick
        : '(function(id){if(typeof openSkillExplorer===\'function\')openSkillExplorer(id);})(\'' + jsStr(s.canonicalId || s.id) + '\')';
      var stars = rankBadge(s.level, { variant: 'stars', label: s.level, tier: branch });
      return '<div class="plaque__stack-row" data-branch="' + esc(branch) +
        '" data-level="' + esc(n) + '" style="--row-index:' + idx + '">' +
          '<span class="plaque__stack-glyph tier-glyph" data-branch="' + esc(branch) +
            '" aria-hidden="true">' + glyph + '</span>' +
          '<button class="plaque__slug plaque-skill-name named-slug plaque__slug--clickable" type="button" ' +
            'title="' + esc(slugTitle) + '" onclick="' + clickAttr + '">' + esc(slug) + '</button>' +
          (stars ? '<span class="plaque__stack-rank">' + stars + '</span>' : '') +
        '</div>';
    }).join('');

    var moreRow = overflow
      ? '<div class="plaque__stack-more">+' + overflow + ' more</div>'
      : '';

    var inner =
      artHtml +
      '<div class="plaque__hall-content">' +
        crestHtml +
        metaHtml +
        dividerHtml +
        '<div class="plaque__hall-rows plaque__stack-body">' + rows + moreRow + '</div>' +
      '</div>';

    var extraClass = 'plaque--hall' + (opts.featured ? ' plaque--hall-featured' : '');
    var shellOpts = { click: false, extraClass: extraClass };
    return _shell('hall', primaryNs, inner, shellOpts);
  }

  // ── public API ───────────────────────────────────────────────────
  var plaque = {
    renderMini: renderMini,
    renderMiniStack: renderMiniStack,
    renderHallPlate: renderHallPlate,
    renderTile: renderTile,
    renderRow: renderRow,
    renderDetail: renderDetail,
    renderSettled: renderSettled,
    renderOg: renderOg,
    // Private helpers exposed for debugging only; do not depend on these
    // in call-site code — the public render methods are the contract.
    _fields: {
      orb: _fieldOrb,
      avatar: _fieldAvatar,
      slug: _fieldSlug,
      title: _fieldTitle,
      handle: _fieldHandleRow,
      description: _fieldDescription,
      tags: _fieldTags,
      rank: _fieldRank,
      install: _fieldInstallRow,
    },
  };

  window.plaque = plaque;

  // Phase 8d — export shared helpers to window if they are missing (e.g. on
  // the Named Skills Explorer where atlas-helpers.js is not loaded).
  if (typeof window.handleLink !== 'function') window.handleLink = handleLink;
  if (typeof window.namedSlug !== 'function') window.namedSlug = namedSlug;
  // isRedacted logic: only redacted if level is 0 or 1.
  if (typeof window.isRedacted !== 'function') {
    window.isRedacted = function(level) {
      var n = levelNum(level);
      return n >= 0 && n <= 1;
    };
  }
  if (typeof window.redactedHandle !== 'function') {
    window.redactedHandle = function() {
      return '<span class="plaque__redacted-handle" aria-label="Contributor not yet revealed">@[anonymous]</span>';
    };
  }
  // Fallback openSkillExplorer — on pages where skill-explorer.js is not
  // loaded (profile pages, badges page, etc.), clicking a skill slug button
  // calls openSkillExplorer() which otherwise doesn't exist.  Navigate to
  // the Named Skills Explorer with the correct hash fragment.
  if (typeof window.openSkillExplorer !== 'function') {
    window.openSkillExplorer = function (id) {
      if (!id) return;
      var prefix = (typeof window.gaiaIconBase === 'function')
        ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
        : '/';
      window.location.href = prefix + 'named/#explorer/' + encodeURIComponent(id).replace(/%2F/g, '/');
    };
  }
})();
