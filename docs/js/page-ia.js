(function () {
  var version = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
  var GRAPH_URL = 'graph/gaia.json' + version;
  var NAMED_URL = 'graph/named/index.json' + version;

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

  // Stage 2 — stars are rendered by the shared .rank-badge component.
  // window.rankBadge(level, { variant: 'stars' }) returns the full
  // <span class="rank-badge"…> markup; the previous starsRow helper
  // only produced the inner stars, so call sites that wrapped it in
  // a <span class="hoh-star">…</span> or <span class="ult-stars">…</span>
  // now drop that wrapper.
  function starsBadge(level) {
    return (typeof window.rankBadge === 'function')
      ? window.rankBadge(level, { variant: 'stars' })
      : '';
  }
  function chipBadge(level) {
    return (typeof window.rankBadge === 'function')
      ? window.rankBadge(level, { variant: 'chip' })
      : '';
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
    // Also treat awakened (status != "named") ultimate entries as claimed so they
    // don't surface as free-to-claim in the ultimates list.
    (namedData.awaitingClassification || []).forEach(function (e) {
      var primary = e.genericSkillRef || (e.id && e.id.split('/').pop());
      if (primary && byId[primary] && byId[primary].type === 'ultimate' && !claimedBy[primary]) {
        claimedBy[primary] = e;
      }
    });

    var ultimates = skills.filter(function (s) { return s.type === 'ultimate'; });
    var unclaimed = ultimates.filter(function (u) { return !claimedBy[u.id]; });
    var apexCount = ultimates.length - unclaimed.length;

    // Resolve effective level from the named entry because canonical nodes
    // don't carry a level field — only named/claimed entries do.
    var levelFor = {};
    ultimates.forEach(function (u) {
      var claim = claimedBy[u.id];
      levelFor[u.id] = (claim && claim.level) || u.level || null;
    });

    // Ledger strip
    var elSkills = document.getElementById('ledgerSkills');
    var elUlts = document.getElementById('ledgerUlts');
    var elDate = document.getElementById('ledgerDate');
    if (elSkills) elSkills.textContent = skills.length;
    if (elUlts) elUlts.textContent = ultimates.length;
    var dateStr = formatDate(graphData.generatedAt || (graphData.meta && graphData.meta.updatedAt));
    if (elDate && dateStr) elDate.textContent = dateStr;

    // Door B caption
    var doorCap = document.getElementById('doorBCaption');
    if (doorCap) doorCap.textContent = ultimates.length + ' ultimate' + (ultimates.length !== 1 ? 's' : '');

    // Path B — all Ultimates (claimed + unclaimed), sorted unclaimed first
    var list = document.getElementById('ultimatesList');
    if (list) {
      var sorted = ultimates.slice().sort(function (a, b) {
        // order by level desc first
        var lvlDiff = levelNum(levelFor[b.id]) - levelNum(levelFor[a.id]);
        if (lvlDiff !== 0) return lvlDiff;
        // then by claimed status (unclaimed first)
        var aClaimed = !!claimedBy[a.id];
        var bClaimed = !!claimedBy[b.id];
        if (aClaimed !== bClaimed) return aClaimed ? 1 : -1;
        // then alphabetically
        return a.id.localeCompare(b.id);
      });

      // Delegate Claim button clicks once (idempotent: only attach if not already)
      if (!list.dataset.claimDelegated) {
        list.addEventListener('click', function (ev) {
          var btn = ev.target.closest && ev.target.closest('.ult-claim');
          if (!btn) return;
          var contributor = btn.dataset.contributor;
          var prefix = (typeof window.gaiaIconBase === 'function') ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '') : '';
          window.location.href = contributor
            ? prefix + 'badges/?u=' + encodeURIComponent(contributor) + '#generate-section'
            : prefix + 'badges/#generate-section';
        });
        list.dataset.claimDelegated = '1';
      }

      list.innerHTML = sorted.map(function (u) {
        var claim = claimedBy[u.id];
        var uLevel = levelFor[u.id];
        var levelChip = chipBadge(uLevel);
        if (claim) {
          // Phase 8c — claimed Ultimates lead with the named slug in honor red
          // (the second segment of the named id, e.g. /autoresearch). The
          // canonical id moves out of the visible row; hover-title preserves it.
          var claimedSlug = (typeof window.namedSlug === 'function')
            ? window.namedSlug(claim)
            : '/' + u.id;
          var contribLink = (typeof window.handleLink === 'function')
            ? window.handleLink(claim.contributor || '', { extraClass: 'ult-contrib', level: claim.level || uLevel })
            : '<a class="ult-contrib atlas-handle" href="./u/' + encodeURIComponent(claim.contributor || '') + '/">@' + esc(claim.contributor || '') + '</a>';
          
          var lvlN = levelNum(uLevel);
          var colorStyle = 'color: var(--rank-' + lvlN + '); cursor: pointer;';
          if (lvlN === 6) colorStyle += ' animation: tree-rainbow-glow 4s linear infinite;';
          var clickAttr = ' role="button" tabindex="0" onclick="if(typeof openSkillExplorer===\'function\')openSkillExplorer(\'' + jsStr(u.id) + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();this.click();}"';

          var originHtml = '';
          if (claim.origin && typeof window.gaiaIcon === 'function') {
            originHtml = '<span class="plaque__origin" data-tooltip="Origin contributor: The creator of the first skill version" aria-label="Origin contributor: The creator of the first skill version">' +
              window.gaiaIcon('origin-badge', { size: 16 }) +
              '<span class="origin-info" style="margin-left: 3px; color: var(--muted); opacity: 0.7;">' + window.gaiaIcon('info', { size: 10 }) + '</span>' +
              '</span>';
          }
          
          return '<div class="ultimate-item ultimate-item--claimed">' +
            '<span class="ult-glyph">◆</span>' +
            '<span class="ult-slug named-slug" title="' + esc(u.id) + '" style="' + colorStyle + '"' + clickAttr + '>' + esc(claimedSlug) + '</span>' +
            '<div class="ult-contrib-wrap" style="display:inline-flex; align-items:center; flex-shrink:0;">' +
            contribLink + originHtml +
            '</div>' +
            levelChip +
            '<button class="ult-claim" type="button" ' +
              'data-skill-id="' + esc(u.id) + '"' +
              ' data-skill-name="' + esc(u.name || u.id) + '"' +
              ' data-skill-level="' + esc(uLevel || '') + '"' +
              ' data-contributor="' + esc(claim.contributor || '') + '">Claim →</button>' +
            '</div>';
        }
        // Phase 8c — unclaimed Ultimates keep the canonical slug, rendered in
        // muted text (no name to honor yet).
        var slash = '/' + u.id;
        return '<div class="ultimate-item">' +
          '<span class="ult-glyph">◆</span>' +
          '<span class="ult-slug named-slug named-slug--muted" title="' + esc(u.name || '') + '">' + esc(slash) + '</span>' +
          levelChip +
          '<button class="ult-claim" type="button" ' +
            'data-skill-id="' + esc(u.id) + '"' +
            ' data-skill-name="' + esc(u.name || u.id) + '"' +
            ' data-skill-level="' + esc(uLevel || '') + '">Claim →</button>' +
          '</div>';
      }).join('');
    }

    // Hall of Heroes — diverse top-N origin plates with type-aware glyphs
    var allOrigin = [];
    var totalNamedCount = 0;
    Object.keys(buckets).forEach(function (skillId) {
      (buckets[skillId] || []).forEach(function (e) {
        if (!e.origin) return;
        // Defensive: never surface a pre-named/demoted (≤1★) skill in the
        // public Hall of Heroes, even if flagged origin.
        if (window.isRedacted && window.isRedacted(e.level)) return;
        totalNamedCount++;
        var refId = e.genericSkillRef || skillId;
        var canonical = byId[refId];
        if (!canonical && e.id && e.id.indexOf('/') !== -1) {
          canonical = byId[e.id.split('/').pop()];
        }
        if (!canonical) return;
        if (canonical.type !== 'ultimate' && canonical.type !== 'unique') return;
        if (canonical.level) e.level = canonical.level;
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
    if (elNamed) elNamed.textContent = totalNamedCount;

    // Pick diverse top-8 contributors: GROUP all of a contributor's
    // qualifying origin skills into a single plate (instead of dropping
    // their lower-ranked entries). This lets ruvnet's /ruflo (Ultimate)
    // and /hive-mind-coordination (Unique) appear in one plate together,
    // each row coloured by its OWN tier/level via .plaque__stack-row.
    var byContrib = Object.create(null);
    allOrigin.forEach(function (item) {
      var c = item.entry.contributor || '';
      if (!c) return;
      if (!byContrib[c]) byContrib[c] = [];
      byContrib[c].push(item);
    });
    // Sort within each group: highest-rank skill first.
    Object.keys(byContrib).forEach(function (c) {
      byContrib[c].sort(function (a, b) {
        var ld = levelNum(b.entry.level) - levelNum(a.entry.level);
        if (ld !== 0) return ld;
        return (TYPE_RANK[a.type] || 9) - (TYPE_RANK[b.type] || 9);
      });
    });
    // Order contributors by their primary (best) skill.
    var contribOrder = Object.keys(byContrib).sort(function (a, b) {
      var ai = byContrib[a][0], bi = byContrib[b][0];
      var ld = levelNum(bi.entry.level) - levelNum(ai.entry.level);
      if (ld !== 0) return ld;
      return (TYPE_RANK[ai.type] || 9) - (TYPE_RANK[bi.type] || 9);
    });
    var top = contribOrder.slice(0, 8).map(function (c) { return byContrib[c]; });
    // Diversity guard — ensure ≥2 contributors whose group includes a Unique.
    var hasUnique = function (group) { return group.some(function (it) { return it.type === 'unique'; }); };
    var uniqueProviding = top.filter(hasUnique).length;
    if (uniqueProviding < 2) {
      var needed = 2 - uniqueProviding;
      var topContribs = new Set(contribOrder.slice(0, 8));
      var spareUniqueContribs = contribOrder.slice(8).filter(function (c) {
        return !topContribs.has(c) && hasUnique(byContrib[c]);
      }).slice(0, needed);
      // Replace lowest-ranked non-Unique-providing groups.
      for (var i = top.length - 1; i >= 0 && spareUniqueContribs.length; i--) {
        if (!hasUnique(top[i])) {
          top[i] = byContrib[spareUniqueContribs.shift()];
        }
      }
    }

    var plates = document.getElementById('hohPlates');
    if (plates && top.length) {
      // Phase 9 — Hall of Heroes redesigned plates. Each contributor's
      // group is rendered through plaque.renderHallPlate (atlas crest +
      // faint backdrop + Roman-numeral divider + stack rows). Plates whose
      // primary skill is 6★ get featured: true (larger card, Garamond
      // handle); the first plate is always featured even if no 6★ exists,
      // so the hero never feels flat. Featured plates render in
      // .hoh-featured (responsive 1–2 columns); the rest in .hoh-grid.
      var groupsRendered = top.map(function (group) {
        var skills = group.map(function (it) {
          var e = it.entry;
          return {
            id: e.id,
            name: e.name,
            contributor: e.contributor,
            origin: e.origin,
            level: e.level,
            type: it.type,
            genericSkillRef: e.genericSkillRef,
            canonicalId: it.canonicalId,
            onclick: '(function(){if(typeof openSkillExplorer===\'function\')openSkillExplorer(\'' +
              jsStr(it.canonicalId) + '\');})()',
          };
        });
        return { skills: skills, primaryLevel: levelNum(group[0].entry.level) };
      });

      var hasApex = groupsRendered.some(function (g) { return g.primaryLevel >= 6; });
      var featuredCap = hasApex ? 2 : 1;
      var featured = [];
      var standard = [];
      groupsRendered.forEach(function (g) {
        if (g.primaryLevel >= 6 && featured.length < featuredCap) {
          featured.push(g);
        } else if (!hasApex && featured.length < featuredCap) {
          // No 6★ in the set — promote the very top group to featured.
          featured.push(g);
        } else {
          standard.push(g);
        }
      });

      var renderGroup = function (g, isFeatured) {
        if (!window.plaque || typeof window.plaque.renderHallPlate !== 'function') {
          // Fallback to mini-stack if the new plate isn't available.
          if (window.plaque && typeof window.plaque.renderMiniStack === 'function') {
            return window.plaque.renderMiniStack(g.skills, { maxRows: 3 });
          }
          return '';
        }
        return window.plaque.renderHallPlate(g.skills, {
          maxRows: isFeatured ? 4 : 3,
          featured: !!isFeatured,
        });
      };

      var featuredHtml = featured.length
        ? '<div class="hoh-featured">' +
            featured.map(function (g) { return renderGroup(g, true); }).join('') +
          '</div>'
        : '';
      var standardHtml = standard.length
        ? '<div class="hoh-grid">' +
            standard.map(function (g) { return renderGroup(g, false); }).join('') +
          '</div>'
        : '';
      plates.innerHTML = featuredHtml + standardHtml;
    }

    // --- META REPORT (Synthesize Changelog) ---
    var tlEvents = [];
    var ACTION_ICON = {
      rank_up: 'sparkle',
      ascend: 'sparkle',
      name: 'user',
      fuse: 'sparkle',
      push: 'claim-arrow',
      evidence: 'copy-check',
      demote: 'arrow-back',
      propose: 'claim-arrow',
      bond: 'sparkle',
      register: 'claim-arrow'
    };
    var TYPE_GLYPH_MR = { ultimate:'tier-glyph-ultimate', unique:'tier-glyph-unique', extra:'tier-glyph-extra', basic:'tier-glyph-basic' };
    var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

    // 1. Synthesize canonical skill timeline events
    skills.forEach(function (s) {
      if (s.createdAt) {
        tlEvents.push({
          date: new Date(s.createdAt).getTime(),
          action: 'push',
          skillId: s.id,
          name: s.name,
          type: s.type || 'basic',
          details: 'Canonical skill ' + s.name + ' added to registry.'
        });
      }

      // Evidence events
      if (s.evidence && s.evidence.length) {
        s.evidence.forEach(function (ev) {
          tlEvents.push({
            date: new Date(ev.date).getTime(),
            action: 'evidence',
            skillId: s.id,
            name: s.name,
            type: s.type || 'basic',
            details: 'Class ' + ev.class + ' evidence reviewed by @' + ev.evaluator
          });
        });
      }

      // Explicit timeline events in canonical skill
      if (s.timeline && s.timeline.length) {
        s.timeline.forEach(function (t) {
          tlEvents.push({
            date: new Date(t.timestamp || t.date).getTime(),
            action: t.action,
            skillId: s.id,
            name: s.name,
            type: s.type || 'basic',
            contributor: t.contributor || '',
            details: t.details || ''
          });
        });
      }
    });

    // 2. Synthesize named skill timeline events
    Object.keys(buckets).forEach(function (skillId) {
      (buckets[skillId] || []).forEach(function (ns) {
        var slug = (typeof window.namedSlug === 'function') ? window.namedSlug(ns) : '/' + (ns.id.split('/')[1] || ns.id);
        var refId = ns.genericSkillRef || skillId;
        var canonical = byId[refId];
        var nsType = (canonical && canonical.type) || ns.type || 'basic';

        if (ns.createdAt) {
          tlEvents.push({
            date: new Date(ns.createdAt).getTime(),
            action: 'name',
            skillId: ns.id,
            name: ns.name || slug,
            type: nsType,
            contributor: ns.contributor || '',
            details: 'Named skill implementation claimed by @' + ns.contributor + '.'
          });
        }

        if (ns.timeline && ns.timeline.length) {
          ns.timeline.forEach(function (t) {
            tlEvents.push({
              date: new Date(t.timestamp || t.date).getTime(),
              action: t.action,
              skillId: ns.id,
              name: ns.name || slug,
              type: nsType,
              contributor: t.contributor || ns.contributor || '',
              details: t.details || ''
            });
          });
        }
      });
    });

    // Sort descending by date
    tlEvents.sort(function (a, b) {
      return b.date - a.date;
    });

    // Build year-filter select dynamically from event data
    (function() {
      var yearSet = {};
      tlEvents.forEach(function(ev) { yearSet[new Date(ev.date).getFullYear()] = true; });
      var years = Object.keys(yearSet).sort(function(a, b) { return b - a; });
      var mrControls = document.querySelector('.mr-controls');
      if (!mrControls || !years.length) return;
      var row = document.createElement('div');
      row.className = 'mr-date-row';
      var sel = document.createElement('select');
      sel.className = 'mr-year-select';
      sel.id = 'mrYearSelect';
      sel.setAttribute('aria-label', 'Filter by year');
      var optAll = document.createElement('option');
      optAll.value = 'all';
      optAll.textContent = 'All years';
      sel.appendChild(optAll);
      years.forEach(function(y) {
        var opt = document.createElement('option');
        opt.value = y;
        opt.textContent = y;
        sel.appendChild(opt);
      });
      row.appendChild(sel);
      mrControls.appendChild(row);
    })();
    var mrTimeline = document.getElementById('mrTimeline');
    var mrFooter = document.getElementById('mrFooter');
    var mrFilterTabs = document.getElementById('mrFilterTabs');
    var currentPage = 1;
    var pageSize = 15;
    var currentFilter = 'all';
    var currentYear = 'all';

    // Maps tab data-action → array of raw schema actions that match
    var FILTER_GROUPS = {
      'all':      null,
      'promoted': ['rank_up', 'ascend'],
      'named':    ['name'],
      'evidence': ['evidence'],
      'added':    ['push', 'propose', 'register'],
      'fused':    ['fuse', 'bond'],
      'demoted':  ['demote']
    };
    
    // Count events per filter group for tab badges
    function countByAction(action) {
      var base = currentYear === 'all' ? tlEvents : tlEvents.filter(matchesYear);
      if (action === 'all') return base.length;
      var actions = FILTER_GROUPS[action];
      if (!actions) return 0;
      return base.filter(function (ev) { return actions.indexOf(ev.action) !== -1; }).length;
    }

    function matchesFilter(ev) {
      if (currentFilter === 'all') return true;
      var actions = FILTER_GROUPS[currentFilter];
      return actions ? actions.indexOf(ev.action) !== -1 : false;
    }

    function matchesYear(ev) {
      if (currentYear === 'all') return true;
      return new Date(ev.date).getFullYear() === parseInt(currentYear, 10);
    }

    function updateTabCounts() {
      if (!mrFilterTabs) return;
      mrFilterTabs.querySelectorAll('.mr-tab').forEach(function (tab) {
        var action = tab.dataset.action || 'all';
        var count = countByAction(action);
        var badge = tab.querySelector('.mr-count');
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'mr-count';
          tab.appendChild(badge);
        }
        badge.textContent = count;
      });
    }

    function monthKey(ts) {
      var d = new Date(ts);
      return MONTHS[d.getMonth()] + ' ' + d.getFullYear();
    }

    function renderMetaReport() {
      if (!mrTimeline) return;

      var filteredEvents = tlEvents.filter(function (ev) {
        return matchesFilter(ev) && matchesYear(ev);
      });

      var totalEvents = filteredEvents.length;
      var totalPages = Math.max(1, Math.ceil(totalEvents / pageSize));
      
      // Ensure page is within boundaries
      if (currentPage > totalPages) currentPage = totalPages;
      if (currentPage < 1) currentPage = 1;

      if (!totalEvents) {
        var emptyIcon = '';
        if (typeof window.gaiaIcon === 'function') {
          emptyIcon = window.gaiaIcon('info', { size: 24 });
        } else {
          emptyIcon = '<svg class="ico" width="24" height="24" aria-hidden="true"><use href="assets/icons.svg#info"/></svg>';
        }
        mrTimeline.innerHTML = '<div class="mr-empty">' +
          '<div class="mr-empty-icon">' + emptyIcon + '</div>' +
          '<div class="mr-empty-text">No changelog events match this filter.</div>' +
          '</div>';
        var mrPagination = document.getElementById('mrPagination');
        if (mrPagination) mrPagination.style.display = 'none';
        return;
      }

      var startIndex = (currentPage - 1) * pageSize;
      var endIndex = Math.min(startIndex + pageSize, totalEvents);
      var toShow = filteredEvents.slice(startIndex, endIndex);

      var html = '';
      var lastMonth = '';
      var staggerIdx = 0;

      toShow.forEach(function (ev) {
        // Date group header
        var mk = monthKey(ev.date);
        if (mk !== lastMonth) {
          lastMonth = mk;
          html += '<div class="mr-month-header">' + esc(mk) + '</div>';
        }

        var actionLabel = ev.action.replace('_', ' ');
        var iconId = ACTION_ICON[ev.action] || 'info';
        var iconHtml = '';
        if (typeof window.gaiaIcon === 'function') {
          iconHtml = window.gaiaIcon(iconId, { size: 12 });
        } else {
          iconHtml = '<svg class="ico" width="12" height="12" aria-hidden="true"><use href="assets/icons.svg#' + iconId + '"/></svg>';
        }

        var dateStr = new Date(ev.date).toISOString().split('T')[0];
        var delay = (staggerIdx % 15) * 0.03;
        staggerIdx++;

        var clickAttr = ' role="button" tabindex="0" onclick="if(typeof openSkillExplorer===\'function\')openSkillExplorer(\'' + jsStr(ev.skillId) + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();this.click();}"';

        // @mentions → profile links via handleLink when available
        var detailsHtml = esc(ev.details).replace(/@([a-zA-Z0-9_-]+)/g, function (match, handle) {
          if (typeof window.handleLink === 'function') {
            return window.handleLink(handle, { extraClass: 'mr-contributor' });
          }
          return '<a class="mr-contributor atlas-handle" href="./u/' + encodeURIComponent(handle) + '/">@' + esc(handle) + '</a>';
        });

        // Tier glyph - uses proper SVG sprite icons from foundation.html
        var tierHtml = '';
        if (ev.type) {
          var tierIconId = TYPE_GLYPH_MR[ev.type] || 'tier-glyph-basic';
          if (typeof window.gaiaIcon === 'function') {
            tierHtml = '<span class="mr-tier-glyph" data-type="' + esc(ev.type) + '">' +
              window.gaiaIcon(tierIconId, { size: 12 }) +
              '</span>';
          } else {
            tierHtml = '<span class="mr-tier-glyph" data-type="' + esc(ev.type) + '">' +
              '<svg class="ico" width="12" height="12" aria-hidden="true"><use href="assets/icons.svg#' + tierIconId + '"/></svg>' +
              '</span>';
          }
        }

        html += '<div class="mr-event" style="animation-delay: ' + delay + 's">';
        html += '<div class="mr-dot" data-action="' + esc(ev.action) + '"></div>';
        html += '<div class="mr-header">';
        html += '<span class="mr-action" data-action="' + esc(ev.action) + '"><span class="mr-action-icon">' + iconHtml + '</span>' + esc(actionLabel) + '</span>';
        html += '<div class="mr-skill-wrap">';
        html += tierHtml;
        html += '<span class="mr-skill"' + clickAttr + ' title="' + esc(ev.skillId) + '">' + esc(ev.name) + '</span>';
        html += '</div>';
        html += '<span class="mr-date">' + esc(dateStr) + '</span>';
        html += '</div>';
        html += '<div class="mr-details">' + detailsHtml + '</div>';
        html += '</div>';
      });

      mrTimeline.innerHTML = html;

      // Render Pagination controls
      var mrPagination = document.getElementById('mrPagination');
      if (mrPagination) {
        mrPagination.style.display = totalEvents > pageSize ? 'flex' : 'none';
        
        var mrPageNum = document.getElementById('mrPageNum');
        if (mrPageNum) {
          mrPageNum.textContent = 'Page ' + currentPage + ' of ' + totalPages;
        }
        
        var mrPrevPage = document.getElementById('mrPrevPage');
        if (mrPrevPage) {
          mrPrevPage.disabled = currentPage === 1;
        }
        
        var mrNextPage = document.getElementById('mrNextPage');
        if (mrNextPage) {
          mrNextPage.disabled = currentPage === totalPages;
        }
      }
    }

    if (mrTimeline) {
      renderMetaReport();
      updateTabCounts();

      // Filter logic
      if (mrFilterTabs) {
        mrFilterTabs.addEventListener('click', function(e) {
          var btn = e.target.closest('.mr-tab');
          if (!btn) return;

          mrFilterTabs.querySelectorAll('.mr-tab').forEach(function(t) {
            t.classList.remove('active');
            t.setAttribute('aria-selected', 'false');
          });
          btn.classList.add('active');
          btn.setAttribute('aria-selected', 'true');

          currentFilter = btn.dataset.action || 'all';
          currentPage = 1;
          renderMetaReport();
        });
      }

      // Year filter
      var mrYearSelect = document.getElementById('mrYearSelect');
      if (mrYearSelect) {
        mrYearSelect.addEventListener('change', function() {
          currentYear = this.value;
          currentPage = 1;
          renderMetaReport();
          updateTabCounts();
        });
      }

      // Pagination click handlers
      var mrPrevPage = document.getElementById('mrPrevPage');
      if (mrPrevPage) {
        mrPrevPage.addEventListener('click', function() {
          if (currentPage > 1) {
            currentPage--;
            renderMetaReport();
            mrTimeline.scrollTop = 0;
          }
        });
      }

      var mrNextPage = document.getElementById('mrNextPage');
      if (mrNextPage) {
        mrNextPage.addEventListener('click', function() {
          currentPage++;
          renderMetaReport();
          mrTimeline.scrollTop = 0;
        });
      }

      // --- META REPORT SIDEBAR CONTROL LOGIC ---
      var metaSidebar = document.getElementById('metaSidebar');
      var metaSidebarBackdrop = document.getElementById('metaSidebarBackdrop');
      var metaNavBtn = document.getElementById('metaNavBtn');
      var metaFooterBtn = document.getElementById('metaFooterBtn');
      var metaChangelogBtnPath = document.getElementById('metaChangelogBtnPath');
      var metaCloseBtn = document.getElementById('metaCloseBtn');

      function openMetaSidebar() {
        if (!metaSidebar) return;
        metaSidebar.classList.add('open');
        metaSidebar.setAttribute('aria-hidden', 'false');
        metaSidebar.focus();
        
        if (window.innerWidth <= 768) {
          if (metaSidebarBackdrop) metaSidebarBackdrop.classList.add('open');
          document.body.style.overflow = 'hidden'; // lock scrolling on mobile
        } else {
          // Explicitly and defensively force scroll unlocking on desktop!
          document.body.style.overflow = '';
          document.documentElement.style.overflow = '';
        }
      }

      function closeMetaSidebar() {
        if (!metaSidebar) return;
        metaSidebar.classList.remove('open');
        if (metaSidebarBackdrop) metaSidebarBackdrop.classList.remove('open');
        metaSidebar.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        document.documentElement.style.overflow = '';
      }

      if (metaNavBtn) metaNavBtn.addEventListener('click', function(e) {
        // Navigate if it's a link, but maybe open sidebar?
        // User said: '"Meta Report" on the nav bar should open the meta report.'
        // It's currently an <a> to the report page.
      });
      
      if (metaChangelogBtnPath) metaChangelogBtnPath.addEventListener('click', openMetaSidebar);
      if (metaFooterBtn) metaFooterBtn.addEventListener('click', openMetaSidebar);
      if (metaCloseBtn) metaCloseBtn.addEventListener('click', closeMetaSidebar);
      if (metaSidebarBackdrop) metaSidebarBackdrop.addEventListener('click', closeMetaSidebar);


      // ESC key support
      document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && metaSidebar && metaSidebar.classList.contains('open')) {
          closeMetaSidebar();
        }
      });

      // Swipe-to-close on Mobile
      var startX = 0;
      var startY = 0;
      var currentTranslate = 0;
      var isSwiping = false;

      if (metaSidebar) {
        metaSidebar.addEventListener('touchstart', function(e) {
          if (window.innerWidth > 768) return;
          startX = e.touches[0].clientX;
          startY = e.touches[0].clientY;
          isSwiping = true;
          metaSidebar.classList.add('swiping');
        }, { passive: true });

        metaSidebar.addEventListener('touchmove', function(e) {
          if (!isSwiping) return;
          var currentX = e.touches[0].clientX;
          var currentY = e.touches[0].clientY;
          var diffX = currentX - startX;
          var diffY = currentY - startY;

          if (diffX > 0 && Math.abs(diffX) > Math.abs(diffY)) {
            metaSidebar.style.transform = 'translateX(' + diffX + 'px)';
            currentTranslate = diffX;
          }
        }, { passive: true });

        metaSidebar.addEventListener('touchend', function(e) {
          if (!isSwiping) return;
          isSwiping = false;
          metaSidebar.classList.remove('swiping');
          metaSidebar.style.transform = '';
          
          if (currentTranslate > 80) {
            closeMetaSidebar();
          }
          currentTranslate = 0;
        });
      }

      // Copy entire changelog in Markdown format
      var metaCopyBtn = document.getElementById('metaCopyBtn');
      if (metaCopyBtn) {
        metaCopyBtn.addEventListener('click', function() {
          var text = '# Gaia Skill Tree - Meta Changelog\n';
          text += 'Generated: ' + new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC\n\n';
          text += 'A living chronicle of registry evolution: every rank-up, name claim, fusion, and evidence review recorded.\n\n';
          
          var filteredEvents = tlEvents.filter(function (ev) { return matchesFilter(ev) && matchesYear(ev); });

          filteredEvents.forEach(function(ev) {
            var dateStr = new Date(ev.date).toISOString().split('T')[0];
            var actionStr = ev.action.toUpperCase().replace('_', ' ');
            text += '- **[' + dateStr + ']** [' + actionStr + '] ' + ev.name + ' (' + ev.type + '): ' + ev.details + '\n';
          });

          if (window.copyToClipboard) {
            window.copyToClipboard(text).then(function() {
              var svgUse = metaCopyBtn.querySelector('use');
              if (svgUse) {
                // Highly premium visual check - swap SVG sprite target path dynamically!
                svgUse.setAttribute('href', 'assets/icons.svg#copy-check');
                metaCopyBtn.classList.add('copied');
                setTimeout(function() {
                  svgUse.setAttribute('href', 'assets/icons.svg#copy');
                  metaCopyBtn.classList.remove('copied');
                }, 1800);
              }
            }).catch(function() {
              alert('Failed to copy to clipboard.');
            });
          }
        });
      }

      // Download entire changelog in Markdown format
      var metaDownloadBtn = document.getElementById('metaDownloadBtn');
      if (metaDownloadBtn) {
        metaDownloadBtn.addEventListener('click', function() {
          var text = '# Gaia Skill Tree - Meta Changelog\n';
          text += 'Generated: ' + new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC\n\n';
          text += 'A living chronicle of registry evolution: every rank-up, name claim, fusion, and evidence review recorded.\n\n';
          
          var filteredEvents = tlEvents.filter(function (ev) { return matchesFilter(ev) && matchesYear(ev); });

          filteredEvents.forEach(function(ev) {
            var dateStr = new Date(ev.date).toISOString().split('T')[0];
            var actionStr = ev.action.toUpperCase().replace('_', ' ');
            text += '- **[' + dateStr + ']** [' + actionStr + '] ' + ev.name + ' (' + ev.type + '): ' + ev.details + '\n';
          });

          var blob = new Blob([text], { type: 'text/markdown;charset=utf-8;' });
          var url = URL.createObjectURL(blob);
          var link = document.createElement('a');
          link.href = url;
          link.setAttribute('download', 'gaia-meta-report.md');
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        });
      }
    }
    
  }).catch(function () {});

  // "Browse all named skills" → now an <a href="named/">, no JS needed.
  // Browse-all is no longer a scroll target since the explorer moved off the home page.
  document.addEventListener('DOMContentLoaded', function () {
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

    // Cross-page: if landed with #meta-report, open the Meta Report sidebar
    if (location.hash === '#meta-report' || location.hash === '#meta') {
      var navMeta = document.getElementById('metaNavBtn');
      if (navMeta) setTimeout(function () { navMeta.click(); }, 50);
    }

    // Legacy search-trigger buttons. Most pages no longer ship them; this code
    // is defensive — if the buttons are still present (e.g. cached HTML) we
    // route them at the standalone /named/ page where the explorer search lives.
    function goToSearch() {
      var prefix = (typeof window.gaiaIconBase === 'function') ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '') : '';
      window.location.href = prefix + 'named/';
    }
    var navSearch = document.getElementById('navSearchBtn');
    if (navSearch) navSearch.addEventListener('click', goToSearch);
    var navSearchMobileTrigger = document.getElementById('navSearchBtnMobile');
    if (navSearchMobileTrigger) navSearchMobileTrigger.addEventListener('click', goToSearch);

    var navMobileSearch = document.getElementById('navMobileSearch');
    var navSearchBack = document.getElementById('navSearchBack');
    var isSearchMode = false;

    function exitSearchMode() {
      if (!isSearchMode) return;
      isSearchMode = false;
      document.body.classList.remove('search-mode');
      if (navMobileSearch) {
        navMobileSearch.value = '';
        navMobileSearch.dispatchEvent(new Event('input')); // Reset list
        navMobileSearch.blur();
      }
      if (window._preSearchScrollY !== undefined) {
        window.scrollTo(0, window._preSearchScrollY);
      }
    }

    if (navMobileSearch) {
      navMobileSearch.addEventListener('focus', function() {
        if (isSearchMode) return;
        window._preSearchScrollY = window.scrollY;
        isSearchMode = true;
        document.body.classList.add('search-mode');
        window.scrollTo(0, 0);
      });
    }

    if (navSearchBack) {
      navSearchBack.addEventListener('click', exitSearchMode);
    }

    // Exit search mode if clicking outside of the search area and not inside the named skills section.
    // However, since search-mode hides everything except nav and #named, clicking anywhere other
    // than #named, the input itself, or the back button should exit.
    document.addEventListener('click', function(e) {
      if (!isSearchMode) return;
      if (!e.target.closest('#named') && !e.target.closest('nav')) {
        exitSearchMode();
      }
    });

    if (location.hash === '#search') goToSearch();

  });
})();
