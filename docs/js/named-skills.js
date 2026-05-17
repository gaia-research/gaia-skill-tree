/* Gaia Named Skills Explorer — Stage 4.
 *
 * View-mode field-set unification
 * --------------------------------
 * The explorer renders the same data in three view modes (Tile / List / Tree).
 * Pre-Stage-4 these three render paths each picked their own field subset and
 * silently dropped origin star, description, tags, or the install row from
 * one mode but not the others. Stage 4 routes all three through a single
 * `viewFields(mode)` helper so the *field manifest* is the only source of
 * truth, and so a field that "exists" in one view exists in every view —
 * variant chrome (which slots are visible) lives in CSS, not JS.
 *
 *   viewFields('tile')  → full info per card.    Rationale: scan + decide.
 *   viewFields('list')  → scan-friendly row.     Rationale: scan density.
 *   viewFields('tree')  → minicard, spatial DAG. Rationale: relationship.
 *
 * Direction rule (cross-surface)
 * ------------------------------
 * Every catalog (a list/grid/tree the user is browsing or selecting from)
 * reads Ultimate-first (top-right → bottom-left for spatial layouts):
 *
 *   Tier sort:   ultimate → unique → extra → basic       (top groups first)
 *   Rank sort:   6★ → 5★ → 4★ → 3★ → 2★    (within each tier; level-desc)
 *
 * The only exemption is "journeys" (temporal/progression narratives) which
 * keep their natural ascending direction. The Ascension Cycle (0★→6★) is
 * the canonical journey and carries data-pattern="journey" in index.html so
 * a future linter doesn't auto-flip it.
 *
 * Schema source-of-truth
 * ----------------------
 * Stage 4 deletes the FALLBACK_NAMED_INDEX / LEVEL_META / TYPE_META_G
 * fallback dictionaries. Meta lives only in registry/gaia.json.meta (mirrored
 * to docs/graph/gaia.json by scripts/syncDocsGraphAssets.py). If the named
 * index or meta is missing, the explorer renders an empty state instead of
 * silently masking the asset drift.
 */
(function () {
  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function nsClick(id) { return 'onclick="openSkillExplorer(\''+id.replace(/'/g,"\\'")+'\')\"'; }
  function nsDisplayName(ns) { return ns.name || ns.id.split('/')[1] || ns.id; }
  // Phase 8d — atlas-helpers fallbacks if the helper script failed to load.
  function nsSlug(ns) {
    return (typeof window.namedSlug === 'function')
      ? window.namedSlug(ns)
      : '/' + (ns && ns.id ? (ns.id.split('/')[1] || ns.id) : '');
  }

  // ── ICON HELPER (sprite via icons.js) ──
  function icon(id, size){
    return (typeof window.gaiaIcon === 'function')
      ? window.gaiaIcon(id, { size: size || 13 })
      : '<svg class="ico" width="' + (size || 13) + '" height="' + (size || 13) + '" aria-hidden="true"></svg>';
  }

  // ── INSTALL ROW (still used by the embedded copy-btn wiring) ──
  window.nsInstCopy = function(btn){
    navigator.clipboard.writeText(btn.dataset.cmd).then(function(){
      var prev=btn.innerHTML; btn.innerHTML=icon('copy-check', 13);
      setTimeout(function(){btn.innerHTML=prev;},1500);
    }).catch(function(){});
  };

  // ── VIEW-MODE FIELD MANIFEST (Stage 4) ──
  // Single source of truth for which fields each view emits. The render
  // functions consume this manifest; variant chrome (layout/visibility)
  // lives in CSS only, never in JS. Adding a new view? Add a row here.
  //
  //   slug         — italic serif handle/skillname slug
  //   title        — Honor Red title line
  //   handle       — @contributor link row
  //   description  — body prose (collapsed in row via CSS; never JS-dropped)
  //   tags         — token-colored tag chips (cap by tile=3, row=2, full=all)
  //   install      — gaia install … terminal block
  //   level        — rank chip (uses window.rankBadge in 'chip' variant)
  //   origin       — origin-star sprite slot
  //   gh           — right-edge GitHub link slot
  function viewFields(mode) {
    if (mode === 'list')
      return ['slug','title','handle','tags','level','origin','gh'];
    if (mode === 'tree' || mode === 'flow')
      return ['slug','level','gh'];
    // tile (default)
    return ['slug','title','handle','description','tags','install','level','origin','gh'];
  }

  // Render delegations. The .plaque component family (docs/js/plaque.js)
  // is the single emitter; this file just orchestrates iteration and sort.
  function renderTile(ns) {
    if (window.plaque && typeof window.plaque.renderTile === 'function') {
      return window.plaque.renderTile(ns);
    }
    return '';
  }
  function renderListRow(ns) {
    if (window.plaque && typeof window.plaque.renderRow === 'function') {
      return window.plaque.renderRow(ns);
    }
    return '';
  }

  // ── DAG (Tree view) ─────────────────────────────────────────────
  // Stage 4 changes vs. earlier flowchart:
  //  - Iterate ranks[maxD..0] so Ultimate anchors the top of the DOM
  //    (visually top-right after CSS layout). Bases trail bottom-left.
  //  - Within each rank, sort by type DESC then level DESC (matches Tile/List).
  //  - Rename data-rank=N (depth tier 0..maxD) → data-depth=N so a future CSS
  //    rule on [data-rank] doesn't accidentally hit DAG layers — the rank-star
  //    system already owns rank-as-level (0★..6★).
  //  - .ns-dag-arrow rule moved to CSS (no inline style).
  //  - Ghost cards (no named implementation) routed through plaque.renderMini
  //    with { ghost: true } so their hatched-border CSS hook is shared.
  function renderFlowchartView(filteredNamed) {
    var skillMap = window._gaiaSkillMap || {};
    var namedIds = {};
    filteredNamed.forEach(function(ns) { namedIds[ns.genericSkillRef || ns.id] = ns; });

    var dagNodes = {};
    Object.values(skillMap).forEach(function(s) {
      dagNodes[s.id] = s;
    });

    var edges = [];
    Object.values(dagNodes).forEach(function(s) {
      (s.prerequisites || []).forEach(function(pid) {
        if (dagNodes[pid]) edges.push({from: pid, to: s.id});
      });
    });

    var groups = { 'apex': [], 'ultimate': [], 'unique': [], 'extra': [], 'basic': [] };
    Object.keys(dagNodes).forEach(function(id) {
      var t = dagNodes[id].type || 'basic';
      if (dagNodes[id].level && String(dagNodes[id].level).indexOf('6') !== -1) {
        groups['apex'].push(id);
      } else if (groups[t]) {
        groups[t].push(id);
      }
    });

    var ranks = [groups['apex'], groups['ultimate'], groups['unique'], groups['extra'], groups['basic']].filter(function(r) { return r.length > 0; });

    function levelNum(level) {
      var n = parseInt(String(level || '').replace(/\D+/g, ''), 10);
      return isNaN(n) ? 0 : n;
    }
    function sortDagRank(a, b) {
      var sa = dagNodes[a], sb = dagNodes[b];
      var la = levelNum(sa.level), lb = levelNum(sb.level);
      if (la !== lb) return lb - la;
      return (sa.name || a).localeCompare(sb.name || b);
    }
    
    function hashString(str) {
      var h = 0;
      for (var i = 0; i < str.length; i++) h = Math.imul(31, h) + str.charCodeAt(i) | 0;
      return Math.abs(h);
    }

    var html = '<div class="ns-dag-container git-style" id="nsDag">';
    html += '<svg class="ns-dag-svg" id="nsDagSvg"></svg>';

    // Bottom to top (Basic -> Extra -> Unique -> Ultimate) in DOM, column-reverse in CSS
    for (var ri = ranks.length - 1; ri >= 0; ri--) {
      var rank = ranks[ri];
      if (!rank.length) continue;
      rank.sort(sortDagRank);
      
      var isUnique = rank.every(function(id) { return dagNodes[id].type === 'unique'; });
      var voidClass = isUnique ? ' void-zone' : '';
      html += '<div class="ns-dag-rank' + voidClass + '" data-depth="' + ri + '">';
      rank.forEach(function(id, idx) {
        var staggerY = (isUnique) ? 0 : (hashString(id) % 150); // don't stagger in void
        var s = dagNodes[id];
        var ns = namedIds[id];
        var isGhost = !ns;
        var miniNs = ns || {
          id: id,
          name: s.name || id,
          level: s.level,
          type: s.type,
          links: {},
          genericSkillRef: id,
        };
        var dagOpts = {
          extraClass: 'ns-dag-card',
          dagId: id,
          ghost: isGhost,
          attrs: ' data-type="' + esc(s.type) + '"',
        };
        if (isGhost) {
          dagOpts.onclick = '(function(id){if(typeof openSkillExplorer===\'function\')openSkillExplorer(id);})(\'' + String(id).replace(/'/g,"\\'") + '\')';
        }
        var miniHtml = (window.plaque && typeof window.plaque.renderMini === 'function')
          ? window.plaque.renderMini(miniNs, dagOpts)
          : '';
        var colorVar = isGhost ? 'var(--muted)' : 'var(--tier-' + (s.type || 'basic') + ', var(--muted))';
        if (!isGhost && s.level && String(s.level).indexOf('6') !== -1) {
          colorVar = '#ffffff';
        }
        var labelParts = String(id).split('/');
        var labelContrib = labelParts.length > 1 ? labelParts[0] : '';
        var labelName = labelParts.length > 1 ? labelParts[1] : id;
        var labelHtml = labelContrib
          ? '<div class="dag-node-label"><span class="dag-node-label-contrib">' + esc(labelContrib) + '</span><span style="color:var(--muted)">/</span><span class="dag-node-label-name">' + esc(labelName) + '</span></div>'
          : '<div class="dag-node-label"><span class="dag-node-label-name">' + esc(id) + '</span></div>';
        html += '<div class="git-node" data-id="' + esc(id) + '" data-type="' + esc(s.type) + '" data-level="' + esc(s.level || '') + '" data-ghost="' + isGhost + '" style="--staggerY:' + staggerY + 'px" onmouseenter="if(window.highlightPathsTree)window.highlightPathsTree(\''+esc(id)+'\')" onmouseleave="if(window.unhighlightPathsTree)window.unhighlightPathsTree()">' +
                '<div class="git-commit-dot" style="--dot-color: ' + colorVar + '"></div>' +
                labelHtml +
                miniHtml +
                '</div>';
      });
      html += '</div>';
    }
    html += '</div>';

    setTimeout(function() {
      var container = document.getElementById('nsDag');
      var svg = document.getElementById('nsDagSvg');
      if (!container || !svg) return;
      
      window._currentDagEdgesTree = edges || [];
      window.highlightPathsTree = function(nodeId) {
        document.querySelectorAll('#nsDagSvg .git-path').forEach(function(p) { p.classList.remove('active-path'); });
        document.querySelectorAll('#nsDag .git-node.show-label').forEach(function(n) { n.classList.remove('show-label'); });
        var edgesMap = window._currentDagEdgesTree;
        var related = {};
        related[nodeId] = true;
        function trace(id) {
          edgesMap.forEach(function(e) {
            if (e.to === id) {
              var p = document.getElementById('path-tree-' + e.from + '-' + e.to);
              if (p) p.classList.add('active-path');
              if (!related[e.from]) { related[e.from] = true; trace(e.from); }
            }
          });
        }
        trace(nodeId);
        Object.keys(related).forEach(function(id) {
          var node = document.querySelector('#nsDag .git-node[data-id="' + id.replace(/"/g, '\\"') + '"]');
          if (node) node.classList.add('show-label');
        });
      };
      window.unhighlightPathsTree = function() {
        document.querySelectorAll('#nsDagSvg .git-path').forEach(function(p) { p.classList.remove('active-path'); });
        document.querySelectorAll('#nsDag .git-node.show-label').forEach(function(n) { n.classList.remove('show-label'); });
      };

      var cRect = container.getBoundingClientRect();
      svg.style.width = container.scrollWidth + 'px';
      svg.style.height = container.scrollHeight + 'px';
      var paths = '';
      edges.forEach(function(e, i) {
        var fromEl = container.querySelector('[data-id="' + e.from + '"]');
        var toEl = container.querySelector('[data-id="' + e.to + '"]');
        if (!fromEl || !toEl) return;
        var dotFrom = fromEl.querySelector('.git-commit-dot');
        var dotTo = toEl.querySelector('.git-commit-dot');
        var fr = (dotFrom || fromEl).getBoundingClientRect();
        var tr = (dotTo || toEl).getBoundingClientRect();
        
        var x1 = fr.left + fr.width / 2 - cRect.left + container.scrollLeft;
        var y1 = fr.top + fr.height / 2 - cRect.top + container.scrollTop;
        var x2 = tr.left + tr.width / 2 - cRect.left + container.scrollLeft;
        var y2 = tr.top + tr.height / 2 - cRect.top + container.scrollTop;
        var dx = x2 - x1;
        var dy = y2 - y1;
        var sign = dx >= 0 ? 1 : -1;
        
        var y_mid = y1 + dy / 2 + ((i % 7) - 3) * 14;
        
        var isSixStar = fromEl.getAttribute('data-level') && fromEl.getAttribute('data-level').indexOf('6') !== -1;
        var colorStr = isSixStar ? '#ffffff' : 'var(--apex-gold, #fbbf24)';
        
        if (Math.abs(dx) < 25) {
          paths += '<path id="path-tree-' + e.from + '-' + e.to + '" class="git-path" d="M' + x1 + ' ' + y1 + ' L' + x2 + ' ' + y2 + '" style="stroke: ' + colorStr + '; stroke-width: 1px;"/>';
        } else {
          var max_hx = Math.abs(dx) / 2;
          var hx1 = Math.min(Math.abs(y_mid - y1) / 1.73205, max_hx);
          var hx2 = Math.min(Math.abs(y2 - y_mid) / 1.73205, max_hx);
          var mx1 = x1 + sign * hx1;
          var mx2 = x2 - sign * hx2;
          paths += '<path id="path-tree-' + e.from + '-' + e.to + '" class="git-path" d="M' + x1 + ' ' + y1 + ' L' + mx1 + ' ' + y_mid + ' L' + mx2 + ' ' + y_mid + ' L' + x2 + ' ' + y2 + '" style="stroke: ' + colorStr + '; stroke-width: 1px;"/>';
        }
      });
      svg.innerHTML = paths;
    }, 60);

    return html;
  }

  function initNamedSkills() {
    var grid = document.getElementById('nsGrid');
    var tabsEl = document.getElementById('nsTypeTabs');
    var viewBtnsEl = document.getElementById('nsViewBtns');
    var searchEl = document.getElementById('nsSearch');
    var sortEl = document.getElementById('nsSort');
    if (!grid) return;

    var viewMode = 'tile';
    var typeFilter = 'all';
    var searchQuery = '';
    // Stage 4 — Direction rule: 'level-desc' is the new default. The legacy
    // 'level' value is treated as level-desc for back-compat with stored UI
    // state and existing <option value="level"> markup.
    var sortMode = 'level-desc';

    // Stage 4 — Schema source-of-truth. The named index and meta block both
    // come from generated assets. If either fetch fails we render an empty
    // state with a hint to run the sync script. No fallbacks, no silent drift.
    Promise.all([
      fetch('graph/named/index.json').then(function(r){ if (!r.ok) throw r; return r.json(); }),
      fetch('graph/gaia.json').then(function(r){ if (!r.ok) throw r; return r.json(); }),
    ]).then(function(results) {
      var indexData = results[0], fullGraph = results[1];
      var skillMap = {};
      (fullGraph.skills || []).forEach(function(s){ skillMap[s.id] = s; });

      var buckets = indexData.buckets || {};
      var allNamed = [];
      Object.values(buckets).forEach(function(arr){ if (Array.isArray(arr)) Array.prototype.push.apply(allNamed, arr); });

      window._gaiaSkillMap = skillMap;
      window._gaiaNamedBuckets = buckets;
      window._gaiaNamedAll = allNamed;
      window._gaiaFullGraph = fullGraph;

      // Augment each named skill with type + level from the generic skill in gaia.json
      allNamed.forEach(function(ns) {
        var g = skillMap[ns.genericSkillRef];
        if (g) {
          if (!ns.type) ns.type = g.type;
          if (g.level) ns.level = g.level;
        }
      });

      if (!allNamed.length) {
        grid.innerHTML = '<div class="ns-empty">No named skills yet. Publish the first with <code>gaia name</code>.</div>';
        return;
      }

      // Meta source-of-truth: registry/gaia.json.meta. Mirrored to
      // docs/graph/gaia.json by syncDocsGraphAssets.py.
      var _meta = fullGraph.meta;
      if (!_meta || !_meta.levelColors || !_meta.typeColors || !_meta.typeSymbols || !_meta.typeLabels) {
        // eslint-disable-next-line no-console
        console.error('[gaia] Missing meta in graph/gaia.json. Run `python scripts/syncDocsGraphAssets.py`.');
        grid.innerHTML = '<div class="ns-empty">Registry meta missing — run <code>python scripts/syncDocsGraphAssets.py</code>.</div>';
        return;
      }

      var LEVEL_META = {};
      var _lc = _meta.levelColors;
      var _ll = _meta.levelLabels || {};
      Object.keys(_lc).forEach(function(k) {
        // Explorer surfaces 2★+ only; 0★ and 1★ exist in meta for completeness
        // (used by the rank-badge component and the unnamed-popup) but aren't
        // bucketed into named skills.
        if (k === '0★' || k === '1★') return;
        LEVEL_META[k] = { name: _ll[k] || k, color: _lc[k].hex, bg: _lc[k].bg, border: _lc[k].border };
      });
      var TYPE_META_G = {};
      Object.keys(_meta.typeColors).forEach(function(t) {
        TYPE_META_G[t] = { glyph: (_meta.typeSymbols || {})[t] || '', label: (_meta.typeLabels || {})[t] || t, color: _meta.typeColors[t].hex };
      });
      // Direction rule — Ultimate-first across groups; level-desc within group.
      // Ascension Cycle is the only journey exemption (data-pattern='journey').
      var TYPE_ORDER = Object.keys(_meta.typeColors).sort(function(a, b) {
        var order = { ultimate: 0, unique: 1, extra: 2, basic: 3 };
        return (order[a] !== undefined ? order[a] : 99) - (order[b] !== undefined ? order[b] : 99);
      });

      window._gaiaMeta = _meta;

      function nsType(ns) { return ns.type || 'basic'; }
      function levelNum(level) {
        var n = parseInt(String(level || '').replace(/\D+/g, ''), 10);
        return isNaN(n) ? 0 : n;
      }

      function groupHeader(type, id) {
        var tm = TYPE_META_G[type]; if (!tm) return '';
        return '<div class="ns-group-header" id="ns-group-'+id+'">' +
          '<span class="ns-group-glyph tier-glyph" data-type="'+esc(type)+'">'+tm.glyph+'</span>'+
          esc(tm.label)+
        '</div>';
      }

      // Within-group sort. Direction rule:
      //   default (level-desc) — most-prestigious first (6★ → 2★)
      //   level-asc            — easiest first (rare; the "what can I unlock?" use case)
      //   creator              — alphabetical by contributor
      //   name                 — alphabetical by skill name
      // Group order itself (ultimate→unique→extra→basic) is owned by TYPE_ORDER.
      function withinGroupSort(items) {
        if (sortMode === 'creator') {
          return items.slice().sort(function(a,b){return (a.contributor||'').localeCompare(b.contributor||'');});
        }
        if (sortMode === 'name') {
          return items.slice().sort(function(a,b){return nsDisplayName(a).localeCompare(nsDisplayName(b));});
        }
        if (sortMode === 'level-asc') {
          return items.slice().sort(function(a,b){
            var d = levelNum(a.level) - levelNum(b.level);
            return d !== 0 ? d : String(a.id).localeCompare(String(b.id));
          });
        }
        // 'level-desc' (default) — also catches legacy 'level' value.
        return items.slice().sort(function(a,b){
          var d = levelNum(b.level) - levelNum(a.level);
          return d !== 0 ? d : String(a.id).localeCompare(String(b.id));
        });
      }

      function renderCurrent() {
        var q = searchQuery.toLowerCase();
        var filtered = allNamed.filter(function(ns) {
          if (typeFilter !== 'all' && (ns.type || 'basic') !== typeFilter) return false;
          if (q) {
            var hay = (nsDisplayName(ns)+' '+ns.id+' '+(ns.tags||[]).join(' ')+' '+(ns.contributor||'')).toLowerCase();
            if (hay.indexOf(q) === -1) return false;
          }
          return true;
        });
        if (!filtered.length) { grid.innerHTML='<div class="ns-empty">No skills match.</div>'; return; }

        if (viewMode === 'flow') {
          // Tree-view DAG owns its own ordering (depth + type+level within
          // each depth) — see renderFlowchartView for the direction rule.
          grid.className = 'ns-grid-flow';
          grid.innerHTML = renderFlowchartView(filtered);
          return;
        }

        // Group by type: ultimate → unique → extra → basic (TYPE_ORDER).
        var groups = { ultimate:[], unique:[], extra:[], basic:[] };
        filtered.forEach(function(ns){ var t=nsType(ns); (groups[t]||(groups[t]=[])).push(ns); });
        var html = '';
        TYPE_ORDER.forEach(function(type) {
          var items = groups[type]; if (!items || !items.length) return;
          items = withinGroupSort(items);
          html += groupHeader(type, type);
          if (viewMode === 'list') html += items.map(function(ns){ return renderListRow(ns); }).join('');
          else html += items.map(function(ns){ return renderTile(ns); }).join('');
        });
        grid.className = viewMode === 'list' ? 'ns-grid-list' : 'ns-grid-tile';
        grid.innerHTML = html;
      }

      if (tabsEl) {
        tabsEl.addEventListener('click', function(e) {
          var btn = e.target.closest('.ns-tab');
          if (!btn) return;
          tabsEl.querySelectorAll('.ns-tab').forEach(function(t){ t.classList.remove('active'); });
          btn.classList.add('active');
          typeFilter = btn.dataset.type || 'all';
          renderCurrent();
        });
      }

      if (viewBtnsEl) {
        viewBtnsEl.addEventListener('click', function(e) {
          var btn = e.target.closest('.ns-view-btn');
          if (!btn) return;
          viewBtnsEl.querySelectorAll('.ns-view-btn').forEach(function(b){ b.classList.remove('active'); });
          btn.classList.add('active');
          viewMode = btn.dataset.view || 'tile';
          renderCurrent();
        });
      }

      var mobileSearchEl = document.getElementById('navMobileSearch');
      if (searchEl) {
        searchEl.addEventListener('input', function(){
          searchQuery = searchEl.value;
          if(mobileSearchEl && mobileSearchEl.value !== searchQuery) mobileSearchEl.value = searchQuery;
          renderCurrent();
        });
      }
      if (mobileSearchEl) {
        mobileSearchEl.addEventListener('input', function(){
          searchQuery = mobileSearchEl.value;
          if(searchEl && searchEl.value !== searchQuery) searchEl.value = searchQuery;
          renderCurrent();
        });
      }

      if (sortEl) {
        // Initialise to current sortMode (back-compat: 'level' → 'level-desc').
        try {
          if (sortEl.value === 'level') sortEl.value = 'level-desc';
          if (sortEl.value && sortEl.value !== sortMode) sortMode = sortEl.value;
        } catch (e) { /* ignore */ }
        sortEl.addEventListener('change', function(){
          var v = sortEl.value;
          sortMode = v === 'level' ? 'level-desc' : v;
          renderCurrent();
        });
      }

      // Dock: click to jump to group
      renderCurrent();
    }).catch(function(err) {
      // eslint-disable-next-line no-console
      console.error('[gaia] Failed to load named index or graph:', err);
      grid.innerHTML = '<div class="ns-empty">Registry index missing — run <code>python scripts/syncDocsGraphAssets.py</code>.</div>';
    });

    // Grab-to-scroll: click+drag anywhere in the Named Skills section scrolls the page
    var named = document.getElementById('named');
    if (named) {
      var _startY, _startSY, _pressing = false, _dragged = false;
      named.addEventListener('mousedown', function(e) {
        if (e.button !== 0) return;
        if (e.target.closest('button,input,select,a,[role="button"]')) return;
        _pressing = true; _dragged = false;
        _startY = e.clientY; _startSY = window.scrollY;
      }, { passive: true });
      window.addEventListener('mousemove', function(e) {
        if (!_pressing) return;
        var dy = e.clientY - _startY;
        if (!_dragged && Math.abs(dy) > 4) { _dragged = true; named.classList.add('ns-grabbing'); }
        if (_dragged) window.scrollTo(0, _startSY - dy);
      });
      window.addEventListener('mouseup', function() {
        if (!_pressing) return;
        _pressing = false;
        named.classList.remove('ns-grabbing');
        if (_dragged) {
          named.addEventListener('click', function killClick(ev) {
            ev.stopPropagation(); named.removeEventListener('click', killClick, true);
          }, true);
        }
      });
    }
  }

  // Expose viewFields for callers (samplers, page-ia, debugging).
  window.gaiaViewFields = viewFields;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNamedSkills);
  } else {
    initNamedSkills();
  }
})();
