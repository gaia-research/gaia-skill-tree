(function () {
  var GRAPH_URL = 'graph/gaia.json';
  var NAMED_URL = 'graph/named/index.json';

  var TYPE_GLYPH = {
    ultimate: '◆',
    unique: '◉',
    extra: '◇',
    basic: '○',
  };
  var TYPE_COLOR_VAR = {
    ultimate: 'var(--apex-gold)',
    unique: 'var(--unique)',
    extra: 'var(--extra)',
    basic: 'var(--basic)',
  };

  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function jsStr(str) {
    return String(str == null ? '' : str).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
  }

  function formatDate(isoStr) {
    if (!isoStr) return '';
    var d = new Date(isoStr);
    if (isNaN(d.getTime())) return '';
    var months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    return d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
  }

  function levelNum(lvl) {
    if (!lvl) return 0;
    var n = parseInt(String(lvl).replace(/[^\d]/g, ''));
    return isNaN(n) ? 0 : n;
  }

  function starsRow(level) {
    var n = levelNum(level);
    var out = '';
    for (var i = 1; i <= 6; i++) {
      out += '<span class="hoh-star' + (i <= n ? '' : ' hoh-star--dim') + '">★</span>';
    }
    return out;
  }

  function openExplorer(id) {
    if (typeof window.openSkillExplorer === 'function') window.openSkillExplorer(id);
  }

  function openClaim(skill) {
    if (typeof window.openUnnamedPopup === 'function') {
      window.openUnnamedPopup(skill);
    }
  }
  window.openClaim = openClaim;

  Promise.all([
    fetch(GRAPH_URL).then(function (r) { return r.ok ? r.json() : Promise.reject(); }),
    fetch(NAMED_URL).then(function (r) { return r.ok ? r.json() : Promise.reject(); }),
  ]).then(function (results) {
    var graphData = results[0];
    var namedData = results[1];
    var skills = graphData.skills || [];
    var buckets = namedData.buckets || {};

    // Index canonical skills by id (for type lookup)
    var byId = {};
    skills.forEach(function (s) { byId[s.id] = s; });

    // Build "claimed by" map: canonical skill id → named entry.
    // Handles the genericSkillRef-mismatch case (e.g. mattpocock/grill-with-docs
    // points at design-review but the canonical ultimate is grill-with-docs)
    // by also keying off the slug from the named entry's id.
    var claimedBy = {};
    Object.keys(buckets).forEach(function (skillId) {
      (buckets[skillId] || []).forEach(function (e) {
        var primary = e.genericSkillRef || skillId;
        if (!claimedBy[primary]) claimedBy[primary] = e;
        if (e.id && e.id.indexOf('/') !== -1) {
          var slug = e.id.split('/').pop();
          if (byId[slug] && !claimedBy[slug]) claimedBy[slug] = e;
        }
      });
    });

    var ultimates = skills.filter(function (s) { return s.type === 'ultimate'; });
    var unclaimed = ultimates.filter(function (u) { return !claimedBy[u.id]; });
    var apexCount = ultimates.length - unclaimed.length;

    // Ledger strip
    var elSkills = document.getElementById('ledgerSkills');
    var elApex = document.getElementById('ledgerApex');
    var elDate = document.getElementById('ledgerDate');
    if (elSkills) elSkills.textContent = skills.length;
    if (elApex) elApex.textContent = apexCount;
    var dateStr = formatDate(graphData.generatedAt || (graphData.meta && graphData.meta.updatedAt));
    if (elDate && dateStr) elDate.textContent = dateStr;

    // Door B caption
    var doorCap = document.getElementById('doorBCaption');
    if (doorCap) doorCap.textContent = unclaimed.length + ' currently unclaimed';

    // Path B — all Ultimates (claimed + unclaimed), sorted unclaimed first
    var list = document.getElementById('ultimatesList');
    if (list) {
      var sorted = ultimates.slice().sort(function (a, b) {
        var aClaimed = !!claimedBy[a.id];
        var bClaimed = !!claimedBy[b.id];
        if (aClaimed !== bClaimed) return aClaimed ? 1 : -1;
        // within group, by level desc then id asc
        var lvlDiff = levelNum(b.level) - levelNum(a.level);
        if (lvlDiff !== 0) return lvlDiff;
        return a.id.localeCompare(b.id);
      });

      // Delegate Claim button clicks once (idempotent: only attach if not already)
      if (!list.dataset.claimDelegated) {
        list.addEventListener('click', function (ev) {
          var btn = ev.target.closest && ev.target.closest('.ult-claim');
          if (!btn) return;
          openClaim({
            id: btn.dataset.skillId,
            name: btn.dataset.skillName || btn.dataset.skillId,
            level: btn.dataset.skillLevel || '',
            type: 'ultimate',
          });
        });
        list.dataset.claimDelegated = '1';
      }

      list.innerHTML = sorted.map(function (u) {
        var claim = claimedBy[u.id];
        var stars = '<span class="ult-stars">' + starsRow(u.level) + '</span>';
        var levelChip = '<span class="ult-level">' + esc(u.level || '') + '</span>';
        if (claim) {
          // Phase 8c — claimed Ultimates lead with the named slug in honor red
          // (the second segment of the named id, e.g. /autoresearch). The
          // canonical id moves out of the visible row; hover-title preserves it.
          var claimedSlug = (typeof window.namedSlug === 'function')
            ? window.namedSlug(claim)
            : '/' + u.id;
          var contribLink = (typeof window.handleLink === 'function')
            ? window.handleLink(claim.contributor || '', { extraClass: 'ult-contrib' })
            : '<a class="ult-contrib atlas-handle" href="./u/' + encodeURIComponent(claim.contributor || '') + '/">@' + esc(claim.contributor || '') + '</a>';
          return '<div class="ultimate-item ultimate-item--claimed">' +
            '<span class="ult-glyph">◆</span>' +
            '<span class="ult-slug named-slug" title="' + esc(u.id) + '">' + esc(claimedSlug) + '</span>' +
            contribLink +
            stars + levelChip +
            '<span class="ult-claimed">Claimed</span>' +
            '</div>';
        }
        // Phase 8c — unclaimed Ultimates keep the canonical slug, rendered in
        // muted text (no name to honor yet).
        var slash = '/' + u.id;
        return '<div class="ultimate-item">' +
          '<span class="ult-glyph">◆</span>' +
          '<span class="ult-slug named-slug named-slug--muted" title="' + esc(u.name || '') + '">' + esc(slash) + '</span>' +
          stars + levelChip +
          '<button class="ult-claim" type="button" ' +
            'data-skill-id="' + esc(u.id) + '"' +
            ' data-skill-name="' + esc(u.name || u.id) + '"' +
            ' data-skill-level="' + esc(u.level || '') + '">Claim →</button>' +
          '</div>';
      }).join('');
    }

    // Hall of Heroes — diverse top-N origin plates with type-aware glyphs
    var allOrigin = [];
    Object.keys(buckets).forEach(function (skillId) {
      (buckets[skillId] || []).forEach(function (e) {
        if (!e.origin) return;
        var refId = e.genericSkillRef || skillId;
        var canonical = byId[refId];
        if (!canonical && e.id && e.id.indexOf('/') !== -1) {
          canonical = byId[e.id.split('/').pop()];
        }
        if (!canonical) return;
        allOrigin.push({
          entry: e,
          canonicalId: canonical.id,
          type: canonical.type || 'basic',
        });
      });
    });
    // Sort by level desc, then by type rank (Ultimate first), then by name
    var TYPE_RANK = { ultimate: 0, unique: 1, extra: 2, basic: 3 };
    allOrigin.sort(function (a, b) {
      var ld = levelNum(b.entry.level) - levelNum(a.entry.level);
      if (ld !== 0) return ld;
      return (TYPE_RANK[a.type] || 9) - (TYPE_RANK[b.type] || 9);
    });

    // Named count for ledger (count of all origin entries)
    var elNamed = document.getElementById('ledgerNamed');
    if (elNamed) elNamed.textContent = allOrigin.length;

    // Pick diverse top-8: at most one per contributor, ensure at least 2 Uniques if available
    var seenContrib = new Set();
    var primary = [];
    allOrigin.forEach(function (item) {
      var c = item.entry.contributor || '';
      if (!seenContrib.has(c)) {
        primary.push(item);
        seenContrib.add(c);
      }
    });
    var top = primary.slice(0, 8);
    var topIds = new Set(top.map(function (it) { return it.canonicalId; }));
    var uniqueCount = top.filter(function (it) { return it.type === 'unique'; }).length;
    if (uniqueCount < 2) {
      var needed = 2 - uniqueCount;
      var extraUniques = allOrigin.filter(function (it) {
        return it.type === 'unique' && !topIds.has(it.canonicalId);
      }).slice(0, needed);
      // Replace the lowest-ranked non-Unique entries with these Uniques
      var nonUniqueIdxs = [];
      for (var i = top.length - 1; i >= 0 && extraUniques.length; i--) {
        if (top[i].type !== 'unique') {
          top[i] = extraUniques.shift();
        }
      }
    }

    var plates = document.getElementById('hohPlates');
    if (plates && top.length) {
      // Phase 8c — render each Hall of Heroes plate as a .plaque--mini.
      // The named slug (e.g. /autoresearch) leads in honor red, the linked
      // @handle sits below, and the 6-star row anchors the card. The plate
      // is the click target; openSkillExplorer takes the canonical id.
      var rendered = top.map(function (it) {
        var e = it.entry;
        var type = it.type;
        var canonId = it.canonicalId;
        var n = levelNum(e.level);
        var slug = (typeof window.namedSlug === 'function')
          ? window.namedSlug(e)
          : '/' + canonId;
        var contribLink = (typeof window.handleLink === 'function')
          ? window.handleLink(e.contributor || '', { extraClass: 'plaque-contributor' })
          : '<a class="atlas-handle plaque-contributor" href="./u/' + encodeURIComponent(e.contributor || '') + '/">@' + esc(e.contributor || '') + '</a>';
        return '<article class="plaque plaque--mini" data-type="' + esc(type) + '"' +
          ' data-skill-id="' + esc(canonId) + '"' +
          ' role="button" tabindex="0"' +
          ' onclick="(function(){if(typeof openSkillExplorer===\'function\')openSkillExplorer(\'' + jsStr(canonId) + '\');})()"' +
          ' onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();this.click();}">' +
          '<div class="plaque-orb plaque-orb--' + esc(type) + (n >= 6 ? ' plaque-orb--vi' : '') + '" aria-hidden="true"></div>' +
          '<div class="plaque-skill-name named-slug" title="' + esc(canonId) + '">' + esc(slug) + '</div>' +
          contribLink +
          '<div class="plaque-stars" aria-label="' + esc(e.level || '') + '">' + starsRow(e.level) + '</div>' +
          '</article>';
      }).join('');
      // Duplicate the rendered set so the CSS marquee can translate -50% and
      // loop seamlessly (the second half occupies the visual gap left behind).
      plates.innerHTML = rendered + rendered;
    }
  }).catch(function () {});

  // "Browse all named skills" → scroll to #named section
  document.addEventListener('DOMContentLoaded', function () {
    var browseBtn = document.getElementById('browseAllBtn');
    if (browseBtn) {
      browseBtn.addEventListener('click', function () {
        var target = document.getElementById('named');
        if (target) target.scrollIntoView({ behavior: 'smooth' });
      });
    }

    // Footer tree button → proxy to nav tree button
    var treeBtn2 = document.getElementById('treeFooterBtn');
    if (treeBtn2) {
      treeBtn2.addEventListener('click', function () {
        var navTree = document.getElementById('treeNavBtn');
        if (navTree) navTree.click();
      });
    }

    // Cross-page: if landed with #tree, open the Tree dialog
    if (location.hash === '#tree') {
      var navTree = document.getElementById('treeNavBtn');
      if (navTree) setTimeout(function () { navTree.click(); }, 50);
    }

    // Global search nav: scroll to Named Skills section and focus the search input
    function focusNamedSearch() {
      var named = document.getElementById('named');
      if (named) named.scrollIntoView({ behavior: 'smooth' });
      setTimeout(function () {
        var input = document.getElementById('nsSearch');
        if (input) { input.focus(); input.select(); }
      }, 520);
    }
    var navSearch = document.getElementById('navSearchBtn');
    if (navSearch) navSearch.addEventListener('click', focusNamedSearch);
    if (location.hash === '#search') focusNamedSearch();

    // Phase 8c — Hall of Heroes manual-override: if the visitor drags or
    // scroll-wheels the track, switch to manual mode (animation paused,
    // scroll-snap enabled). Auto-resume the ambient drift 4s after they
    // leave or focus moves elsewhere. The CSS handles reduced-motion
    // unconditionally; this JS only enhances the default-motion path.
    var track = document.getElementById('hohPlates');
    if (track) {
      var manualTimer = null;
      function enterManual() {
        track.classList.add('is-manual');
        if (manualTimer) clearTimeout(manualTimer);
      }
      function scheduleAutoResume() {
        if (manualTimer) clearTimeout(manualTimer);
        manualTimer = setTimeout(function () {
          track.classList.remove('is-manual');
        }, 4000);
      }
      track.addEventListener('pointerdown', enterManual);
      track.addEventListener('wheel', enterManual, { passive: true });
      track.addEventListener('mouseleave', scheduleAutoResume);
      track.addEventListener('blur', scheduleAutoResume, true);
    }
  });
})();
