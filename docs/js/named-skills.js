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
  // Rank-tier group headers show the SUITE ladder word as the representative
  // label for a whole rank layer (individual items carry their own emitted
  // branch via the plaque shell). Held as a const so the branch key is not an
  // inline literal at each call site (taxonomy-authority guard).
  var SUITE_LADDER = 'suite';
  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/\\/g,'\\\\').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function nsClick(id) { return 'onclick="openSkillExplorer(\''+id.replace(/\\/g,'\\\\').replace(/'/g,"\\'")+'\')\"'; }
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
      return ['slug','title','handle','tags','install','level','origin','gh'];
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
  function renderFlowchartView(filteredNamed, sortMode) {
    var skillMap = window._gaiaSkillMap || {};
    var namedIds = {};
    // Pick each bucket's CHAMPION (origin, else highest level) as its
    // representative — not last-wins, which could surface a ≤1★ sibling over a
    // real 2★+ champion and wrongly redact the node.
    filteredNamed.forEach(function(ns) {
      var key = ns.genericSkillRef || ns.id;
      var cur = namedIds[key];
      if (!cur || ns.origin || levelNum(ns.level) > levelNum(cur.level)) namedIds[key] = ns;
    });

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

    // Group DAG nodes by the ORIGIN named skill's rank (ns.level). Starless generic
    // nodes carry no level of their own — rank comes from namedIds[id].level only.
    // Ghost nodes (no named skill) land in rank-0 (ungrouped at bottom).
    var dagRankGroups = {};
    Object.keys(dagNodes).forEach(function(id) {
      var ns = namedIds[id];
      var rn = ns ? parseInt(String(ns.level || '').replace(/\D+/g, ''), 10) : NaN;
      if (isNaN(rn) || rn < 0) rn = 0;
      if (!dagRankGroups[rn]) dagRankGroups[rn] = [];
      dagRankGroups[rn].push(id);
    });
    // Rank order follows the sort direction: level-desc → 6★ at top, level-asc →
    // 1★ at top (the container's column-reverse maps this list to the display).
    var rankTiers = Object.keys(dagRankGroups).map(Number).sort(function(a, b) {
      return (sortMode === 'level-asc') ? (a - b) : (b - a);
    });
    var ranks = rankTiers.map(function(rn) { return dagRankGroups[rn]; });

    function levelNum(level) {
      var n = parseInt(String(level || '').replace(/\D+/g, ''), 10);
      return isNaN(n) ? 0 : n;
    }
    function sortDagRank(a, b) {
      var nsa = namedIds[a], nsb = namedIds[b];
      var la = levelNum(nsa && nsa.level), lb = levelNum(nsb && nsb.level);
      if (la !== lb) return lb - la;
      return ((nsa && nsa.name) || a).localeCompare((nsb && nsb.name) || b);
    }
    
    function hashString(str) {
      var h = 0;
      for (var i = 0; i < str.length; i++) h = Math.imul(31, h) + str.charCodeAt(i) | 0;
      return Math.abs(h);
    }

    // Flow is declared outside the post-fetch closure, so it can't see
    // nsBranch/rankWordFor from renderCurrent — resolve branch locally.
    function fBranch(ns) {
      return (window.GaiaSemantics && typeof window.GaiaSemantics.branchOf === 'function')
        ? window.GaiaSemantics.branchOf(ns) : ((ns && ns.branch) || 'standard');
    }
    // Renders one DAG node (git-node); shared by single and branch-split layers.
    function renderDagNode(id) {
      var staggerY = hashString(id) % 150;
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
        // Ghost plaque click opens the "gaia propose" dialog so the user can claim the unnamed skill.
        dagOpts.onclick = 'event.stopPropagation();(function(id){var sm=window._gaiaSkillMap||{};var g=sm[id];if(g&&typeof window.openUnnamedPopup===\'function\')window.openUnnamedPopup(g);})(\'' + String(id).replace(/\\/g,'\\\\').replace(/'/g,"\\'") + '\')';
      }
      var miniHtml = (window.plaque && typeof window.plaque.renderMini === 'function')
        ? window.plaque.renderMini(miniNs, dagOpts)
        : '';
      var dotRank = ns ? levelNum(ns.level) : 0;
      var colorVar = isGhost ? 'var(--muted)' : 'var(--rank-' + dotRank + ', var(--muted))';
      // Label source: prefer slash-formatted named ID; fall back to generic ID for ghost nodes.
      var labelSource = (ns && ns.id) ? ns.id : id;
      var labelParts = String(labelSource).split('/');
      var labelContrib = labelParts.length > 1 ? labelParts[0] : '';
      var labelName = labelParts.length > 1 ? labelParts[1] : labelSource;
      // Pre-named/demoted (≤1★): redact the contributor segment. Key on the
      // NAMED skill's own level (ns.level) — the generic node (s.level) is
      // rank-less, so using it would redact every node (false positive).
      var labelRedacted = ns && window.isRedacted && window.isRedacted(ns.level);
      var labelContribHtml = labelRedacted
        ? '<span class="dag-node-label-contrib plaque__redacted-handle" aria-label="Contributor not yet revealed">████████</span>'
        : '<span class="dag-node-label-contrib">' + esc(labelContrib) + '</span>';
      var labelHtml = labelContrib
        ? '<div class="dag-node-label">' + labelContribHtml + '<span style="color:var(--muted)">/</span><span class="dag-node-label-name">' + esc(labelName) + '</span></div>'
        : '<div class="dag-node-label"><span class="dag-node-label-name">' + esc(labelSource) + '</span></div>';
      return '<div class="git-node" data-id="' + esc(id) + '" data-type="' + esc(s.type) + '" data-level="' + esc(s.level || '') + '" data-ghost="' + isGhost + '" style="--staggerY:' + staggerY + 'px"' +
              ' onclick="if(window.selectNodeTree)window.selectNodeTree(\''+esc(id)+'\')"' +
              ' onmouseenter="if(!window._selectedTreeNode&&window.highlightPathsTree)window.highlightPathsTree(\''+esc(id)+'\')"' +
              ' onmouseleave="if(!window._selectedTreeNode&&window.unhighlightPathsTree)window.unhighlightPathsTree()">' +
              '<div class="git-commit-dot" style="--dot-color: ' + colorVar + '"></div>' +
              labelHtml +
              miniHtml +
              '</div>';
    }
    // Emits a labeled DAG layer. At 4★+ `branch` forks the rank word (Extra/
    // Ultimate/Apex vs Unique/Unique Ultimate/Unique Impossible) and adds the
    // Standalone (unique) / Suite chip; below 4★ pass null for the shared word.
    function emitDagLayer(rankNum, depth, layerId, branch, ids) {
      var word = (window.GaiaSemantics && typeof window.GaiaSemantics.rankWord === 'function')
        ? window.GaiaSemantics.rankWord(rankNum, branch || SUITE_LADDER) : (rankNum + '★');
      var kind = branch ? (branch === 'unique' ? 'Standalone' : 'Suite') : '';

      // Branch-aware zone color token
      var zoneColor = branch === 'suite'
        ? 'var(--tier-fusion)'
        : branch === 'unique'
          ? 'var(--tier-unique)'
          : 'var(--rank-' + rankNum + ',var(--muted))';

      // AOV4 badge medallion for this rank+branch
      var base = (typeof window.gaiaIconBase === 'function')
        ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '')
        : '';
      var AOV_SUITE = { 1:'c1-suite-awakened', 2:'c2-suite-named', 3:'c3-suite-evolved',
                        4:'c4-suite-extra', 5:'c5-suite-ultimate', 6:'c6-suite-apex' };
      var AOV_UNIQUE = { 4:'d4-unique', 5:'d5-unique-ultimate', 6:'d6-unique-impossible' };
      var stemMap = (branch === 'unique') ? AOV_UNIQUE : AOV_SUITE;
      var stem = stemMap[rankNum];
      var medallionHtml = stem
        ? '<img class="ns-zone-medallion" src="' + esc(base + 'assets/ascension-overdrive/aov4-' + stem + '-badge.webp') + '" alt="" aria-hidden="true" width="20" height="20">'
        : '';

      var out = '<div class="ns-dag-zone" data-branch="' + esc(branch || '') + '" data-rank="' + esc(String(rankNum)) + '" style="--zone-color:' + zoneColor + '">';
      // Top-left label with medallion
      out += '<div class="ns-dag-rank-label">' +
        medallionHtml +
        '<span class="ns-zone-word" style="color:' + zoneColor + '">' + esc(word) + ' · ' + rankNum + '★</span>' +
        (kind ? '<span class="ns-group-kind">' + esc(kind) + '</span>' : '') +
        '</div>';
      out += '<div class="ns-dag-rank" data-depth="' + depth + '" data-rank="' + esc(String(rankNum)) + '" id="' + esc(layerId) + '"' + (branch ? ' data-branch="' + esc(branch) + '"' : '') + '>';
      ids.forEach(function(id) { out += renderDagNode(id); });
      out += '</div>';
      out += '</div>';
      return out;
    }

    var html = '<div class="ns-dag-container git-style" id="nsDag">';
    html += '<svg class="ns-dag-svg" id="nsDagSvg"></svg>';

    if (sortMode === 'name' || sortMode === 'creator') {
      // A-Z mode: bucket all DAG nodes by first letter of name or contributor,
      // emit one zone per letter (no branch split — alpha grouping overrides rank).
      var keyOf = sortMode === 'creator'
        ? function(id) {
            var ns = namedIds[id];
            var contrib = ns ? (ns.contributor || String(ns.id || id).split('/')[0]) : String(id).split('/')[0];
            var c = String(contrib).trim().charAt(0).toUpperCase();
            return /[A-Z]/.test(c) ? c : '#';
          }
        : function(id) {
            var ns = namedIds[id];
            var name = ns ? (ns.name || ns.id || id) : id;
            var c = String(name).trim().charAt(0).toUpperCase();
            return /[A-Z]/.test(c) ? c : '#';
          };
      var azBuckets = {};
      Object.keys(dagNodes).forEach(function(id) {
        var letter = keyOf(id);
        if (!azBuckets[letter]) azBuckets[letter] = [];
        azBuckets[letter].push(id);
      });
      var letters = Object.keys(azBuckets).sort();
      // column-reverse: emit Z→A so A renders at top
      for (var li = letters.length - 1; li >= 0; li--) {
        var letter = letters[li];
        var ids = azBuckets[letter].sort(function(a, b) {
          return keyOf(a).localeCompare(keyOf(b)) || (namedIds[a] && namedIds[b]
            ? (namedIds[a].name || a).localeCompare(namedIds[b].name || b) : 0);
        });
        var zoneColor = 'var(--muted)';
        var out = '<div class="ns-dag-zone" data-az="' + esc(letter) + '" style="--zone-color:' + zoneColor + '">';
        out += '<div class="ns-dag-rank-label"><span class="ns-zone-word" style="color:var(--muted)">' + esc(letter) + '</span></div>';
        out += '<div class="ns-dag-rank" data-rank="az" id="ns-rank-az-' + esc(letter) + '">';
        ids.forEach(function(id) { out += renderDagNode(id); });
        out += '</div></div>';
        html += out;
      }
    } else {
      // Build the full expected rank ladder so every tier always gets a zone,
      // even when no named skills occupy it (empty zones show the label only).
      var FULL_LADDER = sortMode === 'level-asc'
        ? [0, 1, 2, 3, 4, 5, 6]
        : [6, 5, 4, 3, 2, 1, 0];

      // Merge observed rank tiers with the full ladder so we never drop a tier.
      var seenRanks = {};
      rankTiers.forEach(function(rn) { seenRanks[rn] = true; });

      // DOM is built visual-bottom first; the container's column-reverse flips it,
      // so rankTiers (already sorted by direction) lands 6★ on top for level-desc.
      // At 4★+ each rank splits into a SUITE band and a STANDALONE (unique) band;
      // the suite band is appended first so the unique band renders above it after
      // column-reverse — matching the tile/list unique-first ordering.
      var allRanks = sortMode === 'level-asc' ? [6, 5, 4, 3, 2, 1, 0] : [0, 1, 2, 3, 4, 5, 6];
      for (var ri = 0; ri < allRanks.length; ri++) {
        var rankNum = allRanks[ri];
        var rank = (dagRankGroups[rankNum] || []).slice();
        rank.sort(sortDagRank);
        if (rankNum < 4) {
          html += emitDagLayer(rankNum, ri, 'ns-rank-' + rankNum, null, rank);
          continue;
        }
        var uniqueIds = [], suiteIds = [];
        rank.forEach(function(id) {
          (fBranch(namedIds[id]) === 'unique' ? uniqueIds : suiteIds).push(id);
        });
        if (suiteIds.length) html += emitDagLayer(rankNum, ri, 'ns-rank-' + rankNum + '-suite', 'suite', suiteIds);
        if (uniqueIds.length) html += emitDagLayer(rankNum, ri, 'ns-rank-' + rankNum + '-unique', 'unique', uniqueIds);
      }
    }
    html += '</div>';

    setTimeout(function() {
      var container = document.getElementById('nsDag');
      var svg = document.getElementById('nsDagSvg');
      if (!container || !svg) return;

      window._currentDagEdgesTree = edges || [];
      window._selectedTreeNode = window._selectedTreeNode || null;

      // Yggdrasil II E1: path color keys on rank integer, never dead type enum.
      // The data-rank attribute is set on the parent .ns-dag-rank layer.
      // Edge color follows the RANK of the source (parent) node's layer. The
      // parent .ns-dag-rank carries data-rank="<star rank>" (0..6); the CSS keys
      // .git-path on [data-rank]. Mirrors the per-skill DAG in skill-explorer.js.
      // A-Z sort layers carry data-rank="az" → parses to 0 (neutral gray edge).
      function rankFor(fromEl) {
        var rankLayer = fromEl.closest ? fromEl.closest('.ns-dag-rank') : null;
        var rn = rankLayer ? (parseInt(rankLayer.getAttribute('data-rank') || '', 10) || 0) : 0;
        return rn;
      }

      function getRelatedTreeNodes(nodeId) {
        var related = {};
        related[nodeId] = true;
        var edgesMap = window._currentDagEdgesTree;
        function traceUp(id) {
          edgesMap.forEach(function(e) {
            if (e.to === id && !related[e.from]) { related[e.from] = true; traceUp(e.from); }
          });
        }
        function traceDown(id) {
          edgesMap.forEach(function(e) {
            if (e.from === id && !related[e.to]) { related[e.to] = true; traceDown(e.to); }
          });
        }
        traceUp(nodeId);
        traceDown(nodeId);
        return related;
      }

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
          var node = document.querySelector('#nsDag .git-node[data-id="' + id.replace(/\\/g,'\\\\').replace(/"/g, '\\"') + '"]');
          if (node) node.classList.add('show-label');
        });
      };
      window.unhighlightPathsTree = function() {
        if (window._selectedTreeNode) return;
        document.querySelectorAll('#nsDagSvg .git-path').forEach(function(p) { p.classList.remove('active-path'); });
        document.querySelectorAll('#nsDag .git-node.show-label').forEach(function(n) { n.classList.remove('show-label'); });
      };

      window.selectNodeTree = function(nodeId) {
        var related = getRelatedTreeNodes(nodeId);
        // If a path is already locked AND the clicked node is part of it, keep the current lock.
        if (window._selectedTreeNode) {
          var currentRelated = getRelatedTreeNodes(window._selectedTreeNode);
          if (currentRelated[nodeId]) return;
        }
        document.querySelectorAll('#nsDag .git-node.selected').forEach(function(n) { n.classList.remove('selected'); });
        document.querySelectorAll('#nsDag .git-node.show-label').forEach(function(n) { n.classList.remove('show-label'); });
        document.querySelectorAll('#nsDagSvg .git-path').forEach(function(p) { p.classList.remove('active-path','dimmed'); });

        var node = document.querySelector('#nsDag .git-node[data-id="' + nodeId.replace(/\\/g,'\\\\').replace(/"/g, '\\"') + '"]');
        if (!node) return;
        node.classList.add('selected');
        window._selectedTreeNode = nodeId;

        // Active-path ancestors only (the lit vein)
        var edgesMap = window._currentDagEdgesTree;
        function traceAncestors(id) {
          edgesMap.forEach(function(e) {
            if (e.to === id) {
              var p = document.getElementById('path-tree-' + e.from + '-' + e.to);
              if (p) p.classList.add('active-path');
              traceAncestors(e.from);
            }
          });
        }
        traceAncestors(nodeId);

        // Dim everything that isn't fully inside the related set
        edgesMap.forEach(function(e) {
          if (!related[e.from] || !related[e.to]) {
            var p = document.getElementById('path-tree-' + e.from + '-' + e.to);
            if (p) p.classList.add('dimmed');
          }
        });

        // Show labels on every related node (ancestors + descendants)
        Object.keys(related).forEach(function(id) {
          var n = document.querySelector('#nsDag .git-node[data-id="' + id.replace(/\\/g,'\\\\').replace(/"/g, '\\"') + '"]');
          if (n) n.classList.add('show-label');
        });
      };

      if (!window._nsDagClickHandlerAdded) {
        document.addEventListener('click', function(e) {
          if (!e.target.closest('.git-node') && !e.target.closest('#nsDag')) {
            window._selectedTreeNode = null;
            document.querySelectorAll('#nsDag .git-node.selected').forEach(function(n) { n.classList.remove('selected'); });
            document.querySelectorAll('#nsDag .git-node.show-label').forEach(function(n) { n.classList.remove('show-label'); });
            document.querySelectorAll('#nsDagSvg .git-path').forEach(function(p) { p.classList.remove('active-path','dimmed'); });
          }
        });
        window._nsDagClickHandlerAdded = true;
      }

      var cRect = container.getBoundingClientRect();
      svg.style.width = container.scrollWidth + 'px';
      svg.style.height = container.scrollHeight + 'px';

      // Layout thrashing optimization: Pre-calculate node rects
      var nodeRects = {};
      var nodeEls = {};
      edges.forEach(function(e) {
        if (!nodeEls[e.from]) {
          var el = container.querySelector('[data-id="' + e.from + '"]');
          if (el) {
            nodeEls[e.from] = el;
            var dot = el.querySelector('.git-commit-dot');
            nodeRects[e.from] = (dot || el).getBoundingClientRect();
          }
        }
        if (!nodeEls[e.to]) {
          var el = container.querySelector('[data-id="' + e.to + '"]');
          if (el) {
            nodeEls[e.to] = el;
            var dot = el.querySelector('.git-commit-dot');
            nodeRects[e.to] = (dot || el).getBoundingClientRect();
          }
        }
      });

      // Mobile: the narrow column + node stagger turns the vertical-tangent
      // curves into heavy S-bends. Flatten the control offset on small widths so
      // edges read as gentle, near-direct veins instead of swooping loops.
      var isNarrow = cRect.width < 640;
      var paths = '';
      edges.forEach(function(e) {
        var fromEl = nodeEls[e.from];
        var toEl   = nodeEls[e.to];
        if (!fromEl || !toEl || !nodeRects[e.from] || !nodeRects[e.to]) return;

        var fr = nodeRects[e.from];
        var tr = nodeRects[e.to];

        var fx = fr.left + fr.width / 2 - cRect.left + container.scrollLeft;
        var fy = fr.top  + fr.height / 2 - cRect.top  + container.scrollTop;
        var tx = tr.left + tr.width / 2 - cRect.left + container.scrollLeft;
        var ty = tr.top  + tr.height / 2 - cRect.top  + container.scrollTop;

        var dx = tx - fx;
        var dy = ty - fy;
        var ctrl = Math.abs(dy) * (isNarrow ? 0.12 : 0.25) + Math.abs(dx) * (isNarrow ? 0.03 : 0.05);
        var d = 'M' + fx.toFixed(1) + ',' + fy.toFixed(1) +
                ' C' + fx.toFixed(1) + ',' + (fy + ctrl).toFixed(1) +
                ' ' + tx.toFixed(1) + ',' + (ty - ctrl).toFixed(1) +
                ' ' + tx.toFixed(1) + ',' + ty.toFixed(1);

        // Color by the PARENT skill's rank — the higher-rank node the edge
        // feeds INTO (e.to), not the prerequisite it comes from. The parent
        // owns the tree, so its rank wins.
        var rank = rankFor(toEl);
        paths += '<path id="path-tree-' + e.from + '-' + e.to + '" class="git-path" data-rank="' + rank + '" d="' + d + '"/>';
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

    var viewMode = 'tile';
    var typeFilter = 'all';
    var searchQuery = '';
    // Stage 4 — Direction rule: 'level-desc' is the new default. The legacy
    // 'level' value is treated as level-desc for back-compat with stored UI
    // state and existing <option value="level"> markup.
    var sortMode = 'level-desc';

    // Bind search inputs synchronously so keystrokes work even if the registry
    // fetch is slow or fails. triggerRender() is a no-op until the Promise
    // resolves and assigns it to the real renderCurrent().
    var triggerRender = function(){};
    // 200ms debounce so the grid only re-renders after the user pauses typing —
    // re-rendering on every keystroke is visibly janky on the full registry.
    var searchDebounceTimer = null;
    function debouncedRender() {
      if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(function(){
        searchDebounceTimer = null;
        triggerRender();
      }, 200);
    }
    var mobileSearchEl = document.getElementById('navMobileSearch');
    if (searchEl) {
      searchEl.addEventListener('input', function(){
        searchQuery = searchEl.value;
        if(mobileSearchEl && mobileSearchEl.value !== searchQuery) mobileSearchEl.value = searchQuery;
        debouncedRender();
      });
    }
    if (mobileSearchEl) {
      mobileSearchEl.addEventListener('input', function(){
        searchQuery = mobileSearchEl.value;
        if(searchEl && searchEl.value !== searchQuery) searchEl.value = searchQuery;
        debouncedRender();
      });
    }

    // Stage 4 — Schema source-of-truth. The named index and meta block both
    // come from generated assets. If either fetch fails we render an empty
    // state with a hint to run the sync script. No fallbacks, no silent drift.
    var version = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
    var prefix = (typeof window.gaiaIconBase === 'function') ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '') : '';
    Promise.all([
      fetch(prefix + 'graph/named/index.json' + version).then(function(r){ if (!r.ok) throw r; return r.json(); }),
      fetch(prefix + 'graph/gaia.json' + version).then(function(r){ if (!r.ok) throw r; return r.json(); }),
    ]).then(function(results) {
      var indexData = results[0], fullGraph = results[1];
      var skillMap = {};
      (fullGraph.skills || []).forEach(function(s){ skillMap[s.id] = s; });

      var buckets = indexData.buckets || {};
      var allNamed = [];
      Object.values(buckets).forEach(function(arr){ if (Array.isArray(arr)) Array.prototype.push.apply(allNamed, arr); });
      var awaiting = indexData.awaitingClassification || [];
      Array.prototype.push.apply(allNamed, awaiting);

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
        if (grid) grid.innerHTML = '<div class="ns-empty">No named skills yet. Publish the first with <code>gaia name</code>.</div>';
        return;
      }

      // Meta source-of-truth: registry/gaia.json.meta. Mirrored to
      // docs/graph/gaia.json by syncDocsGraphAssets.py.
      var _meta = fullGraph.meta;
      if (!_meta || !_meta.levelColors || !_meta.typeColors || !_meta.typeSymbols || !_meta.typeLabels) {
        // eslint-disable-next-line no-console
        console.error('[gaia] Missing meta in graph/gaia.json. Run `python scripts/syncDocsGraphAssets.py`.');
        if (grid) grid.innerHTML = '<div class="ns-empty">Registry meta missing — run <code>python scripts/syncDocsGraphAssets.py</code>.</div>';
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
      // Yggdrasil II — TYPE_META_G still maps 'basic'/'fusion' for glyph/label lookups
      // on the type filter axis. The dead type enum (ultimate/unique/extra) is gone.
      var TYPE_META_G = {};
      Object.keys(_meta.typeColors).forEach(function(t) {
        TYPE_META_G[t] = { glyph: (_meta.typeSymbols || {})[t] || '', label: (_meta.typeLabels || {})[t] || t, color: _meta.typeColors[t].hex };
      });
      // RANK_ORDER: 6★ first (highest prestige), descending to 1★/2★ at bottom.
      // Branch (suite/unique/standard) is a VISUAL VARIANT within each rank group —
      // it is not a separate tier bucket. Labels come from GaiaSemantics.rankWord.
      var RANK_ORDER = [6, 5, 4, 3, 2, 1];

      window._gaiaMeta = _meta;

      function nsType(ns) { return ns.type || 'basic'; }
      function levelNum(level) {
        var n = parseInt(String(level || '').replace(/\D+/g, ''), 10);
        return isNaN(n) ? 0 : n;
      }

      function trustScore(ns) {
        var score = 0;
        var level = levelNum(ns.level) || 2;
        score += level * 1000;
        if (ns.origin) score += 500;
        var evidence = Array.isArray(ns.evidence) ? ns.evidence : [];
        evidence.forEach(function(e) {
          if (e.class === 'A') score += 300;
          else if (e.class === 'B') score += 100;
          else if (e.class === 'C') score += 10;
          if (e.verified) score += 200;
          if (e.disputed) score -= 400;
        });
        return score;
      }

      // Rank group header — uses GaiaSemantics.rankWord (suite ladder for the
      // representative label). The suite label is the displayed rank name for the
      // group; unique/standard items within the group carry their own data-branch
      // from the plaque shell (_shell) for visual differentiation (darker/gold).
      // Rank group header. At 4★+ the rank WORD forks by branch (suite → Extra/
      // Ultimate/Apex, unique → Unique/Unique Ultimate/Unique Impossible), so the
      // caller passes the sub-group's branch; below 4★ the word is branch-agnostic
      // and `branch` is omitted (falls back to the suite ladder default). Glyph is
      // the branch medallion at 4★+ (◉ unique / ◆ suite), ○ below.
      function groupHeader(rankNum, id, branch) {
        var rn = parseInt(rankNum, 10) || 0;
        var word = (window.GaiaSemantics && typeof window.GaiaSemantics.rankWord === 'function')
          ? window.GaiaSemantics.rankWord(rn, branch || SUITE_LADDER)
          : (rn + '★');
        var colorVar = branch === 'suite'
          ? 'var(--tier-fusion)'
          : branch === 'unique'
            ? 'var(--tier-unique)'
            : 'var(--rank-' + rn + ', var(--muted))';
        var _base = (typeof window.gaiaIconBase === 'function')
          ? window.gaiaIconBase().replace(/assets\/icons\.svg(\?.*)?$/, '') : '';
        var _suiteMap = { 1:'c1-suite-awakened', 2:'c2-suite-named', 3:'c3-suite-evolved',
                          4:'c4-suite-extra', 5:'c5-suite-ultimate', 6:'c6-suite-apex' };
        var _uniqueMap = { 4:'d4-unique', 5:'d5-unique-ultimate', 6:'d6-unique-impossible' };
        var _stem = ((branch === 'unique') ? _uniqueMap : _suiteMap)[rn];
        var medallionHtml = _stem
          ? '<img class="ns-zone-medallion" src="' + esc(_base + 'assets/ascension-overdrive/aov4-' + _stem + '-badge.webp') + '" alt="" aria-hidden="true" width="20" height="20">'
          : '';
        // 4★+ groups carry a branch descriptor: the unique ladder is STANDALONE
        // skills, the suite ladder (Extra/Ultimate/Apex) is skill SUITES.
        var kind = branch ? (branch === 'unique' ? 'Standalone' : 'Suite') : '';
        return '<div class="ns-group-header ns-group-rank" id="ns-group-' + esc(String(id)) + '" data-rank="' + esc(String(rn)) + '"' + (branch ? ' data-branch="' + esc(branch) + '"' : '') + '>' +
          medallionHtml +
          '<span class="ns-group-rank-word" style="color:' + colorVar + '">' + esc(word) + ' · ' + rn + '★</span>' +
          (kind ? '<span class="ns-group-kind">' + kind + '</span>' : '') +
        '</div>';
      }

      // Alpha-mode header (Name / Contributor sorts regroup the explorer — and
      // therefore the global AlphaRail — into A-Z buckets instead of types).
      function groupHeaderAlpha(letter) {
        return '<div class="ns-group-header ns-group-az" id="ns-group-az-'+esc(letter)+'">' +
          '<span class="ns-group-glyph ns-group-az-glyph">'+esc(letter)+'</span>'+
        '</div>';
      }

      function firstLetterOf(str) {
        var c = String(str || '').trim().charAt(0).toUpperCase();
        return /[A-Z]/.test(c) ? c : '#';
      }
      // Name and Contributor sorts switch the explorer to alphabetical grouping.
      function groupingMode() {
        return (sortMode === 'name' || sortMode === 'creator') ? 'alpha' : 'type';
      }

      // Yggdrasil II — within a rank group, Unique and Suite are DISTINCT
      // branches and must never co-mingle: cluster Unique first, then Suite,
      // then standard. Reads the emitted branch via GaiaSemantics.branchOf
      // (never a client-side type guess).
      function nsBranch(ns) {
        return (window.GaiaSemantics && typeof window.GaiaSemantics.branchOf === 'function')
          ? window.GaiaSemantics.branchOf(ns)
          : ((ns && ns.branch) || 'standard');
      }
      function branchOrder(ns) {
        var b = nsBranch(ns);
        return b === 'unique' ? 0 : b === 'suite' ? 1 : 2;
      }

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
            if (d !== 0) return d;
            var bo = branchOrder(a) - branchOrder(b);
            if (bo !== 0) return bo;
            return String(a.id).localeCompare(String(b.id));
          });
        }
        return items.slice().sort(function(a,b){
          var d = levelNum(b.level) - levelNum(a.level);
          if (d !== 0) return d;
          var bo = branchOrder(a) - branchOrder(b);
          if (bo !== 0) return bo;
          var tsA = trustScore(a), tsB = trustScore(b);
          if (tsA !== tsB) return tsB - tsA;
          return String(a.id).localeCompare(String(b.id));
        });
      }

      function renderCurrent() {
        if (!grid) return;
        var q = searchQuery.toLowerCase();
        var filtered = allNamed.filter(function(ns) {
          if (typeFilter !== 'all' && (ns.type || 'basic') !== typeFilter) return false;
          if (q) {
            var hay = (nsDisplayName(ns)+' '+ns.id+' '+(Array.isArray(ns.tags)?ns.tags:[]).join(' ')+' '+(ns.contributor||'')).toLowerCase();
            if (hay.indexOf(q) === -1) return false;
          }
          return true;
        });
        if (!filtered.length) { grid.innerHTML='<div class="ns-empty">No skills match.</div>'; return; }

        if (viewMode === 'flow') {
          grid.className = 'ns-grid-flow';
          grid.innerHTML = renderFlowchartView(filtered, sortMode);
          if (typeof window._wireTrustNotches === 'function') window._wireTrustNotches(grid);
          return;
        }

        // Champion System: Group by genericSkillRef to featured the highest trust implementation
        var buckets = {};
        filtered.forEach(function(ns) {
          var ref = ns.genericSkillRef || ns.id;
          if (!buckets[ref]) buckets[ref] = [];
          buckets[ref].push(ns);
        });

        var champions = [];
        Object.keys(buckets).forEach(function(ref) {
          var items = buckets[ref];
          items.sort(function(a, b) {
            return trustScore(b) - trustScore(a);
          });
          var champ = items[0];
          champ.variants = items.slice(1);
          champions.push(champ);
        });

        var renderItem = (viewMode === 'list')
          ? function(ns){ return renderListRow(ns); }
          : function(ns){ return renderTile(ns); };
        var html = '';

        if (groupingMode() === 'alpha') {
          // A-Z buckets keyed by display name (name sort) or contributor (creator).
          var keyOf = (sortMode === 'creator')
            ? function(ns){ return firstLetterOf(ns.contributor); }
            : function(ns){ return firstLetterOf(nsDisplayName(ns)); };
          var azGroups = {};
          champions.forEach(function(ns){ var L = keyOf(ns); (azGroups[L] || (azGroups[L] = [])).push(ns); });
          var letters = Object.keys(azGroups).sort(function(a, b){
            if (a === '#') return 1; if (b === '#') return -1; return a < b ? -1 : a > b ? 1 : 0;
          });
          letters.forEach(function(L) {
            var items = withinGroupSort(azGroups[L]);
            html += groupHeaderAlpha(L);
            html += items.map(renderItem).join('');
          });
        } else {
          // Yggdrasil II E2 — group by rank INTEGER (6★ first), NOT by dead type
          // enum. At 4★+ the rank WORD forks by branch, so each 4★+ rank is
          // PARTITIONED into per-branch sub-groups: a 4★ unique standalone reads
          // "Unique · 4★" and a 4★ suite reads "Extra · 4★" — never co-mingled
          // under a single suite-word header. Standard 4★+ (no forked word)
          // collapses into the suite-word bucket (rankWord maps it there), so no
          // empty/duplicate header appears. Below 4★ the word is branch-agnostic
          // (Awakened/Named/Evolved) → one group per rank. Branch is read from the
          // emitted field via GaiaSemantics.branchOf; the plaque shell's
          // data-branch still drives the gold/dark plaque skin per skill.
          var rankGroups = {};
          champions.forEach(function(ns) {
            var rn = levelNum(ns.level) || 2;
            if (!rankGroups[rn]) rankGroups[rn] = [];
            rankGroups[rn].push(ns);
          });
          var rankWordFor = function(rn, branch) {
            return (window.GaiaSemantics && typeof window.GaiaSemantics.rankWord === 'function')
              ? window.GaiaSemantics.rankWord(rn, branch) : (rn + '★');
          };
          // Group ORDER follows the sort direction: level-desc → 6★ first,
          // level-asc → 1★ first. RANK_ORDER is descending; reverse it for asc so
          // the rank headers themselves flip, not just the cards within a group.
          var rankSeq = (sortMode === 'level-asc') ? RANK_ORDER.slice().reverse() : RANK_ORDER;
          rankSeq.forEach(function(rn) {
            var items = rankGroups[rn]; if (!items || !items.length) return;
            // withinGroupSort already clusters unique → suite → standard, so the
            // first-seen sub-group order below is unique-first (matches branchOrder).
            items = withinGroupSort(items);
            if (rn < 4) {
              html += groupHeader(rn, rn);
              html += items.map(renderItem).join('');
              return;
            }
            // Partition this rank by its branch-forked rank WORD. Keying on the
            // word (not the raw branch) merges standard 4★+ into the suite bucket.
            var order = [];
            var sub = {};
            items.forEach(function(ns) {
              var word = rankWordFor(rn, nsBranch(ns));
              if (!sub[word]) {
                sub[word] = { branch: (word === rankWordFor(rn, 'unique') ? 'unique' : 'suite'), items: [] };
                order.push(word);
              }
              sub[word].items.push(ns);
            });
            order.forEach(function(word) {
              var sg = sub[word];
              html += groupHeader(rn, rn + '-' + sg.branch, sg.branch);
              html += sg.items.map(renderItem).join('');
            });
          });
        }

        grid.className = viewMode === 'list' ? 'ns-grid-list' : 'ns-grid-tile';
        grid.innerHTML = html;
        if (typeof window._wireTrustNotches === 'function') window._wireTrustNotches(grid);
      }

      if (tabsEl) {
        tabsEl.addEventListener('click', function(e) {
          var btn = e.target.closest('.ns-tab');
          if (!btn) return;
          tabsEl.querySelectorAll('.ns-tab').forEach(function(t) {
            t.classList.remove('active');
            t.setAttribute('aria-selected', 'false');
          });
          btn.classList.add('active');
          btn.setAttribute('aria-selected', 'true');
          typeFilter = btn.dataset.type || 'all';
          renderCurrent();
        });
      }

      if (viewBtnsEl) {
        viewBtnsEl.addEventListener('click', function(e) {
          var btn = e.target.closest('.ns-view-btn');
          if (!btn) return;
          viewBtnsEl.querySelectorAll('.ns-view-btn').forEach(function(b) {
            b.classList.remove('active');
            b.setAttribute('aria-pressed', 'false');
          });
          btn.classList.add('active');
          btn.setAttribute('aria-pressed', 'true');
          viewMode = btn.dataset.view || 'tile';
          renderCurrent();
        });
      }

      // Search input listeners are bound at init time (outside the Promise).
      // Activate them now that data has loaded.
      triggerRender = renderCurrent;

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
      if (grid) grid.innerHTML = '<div class="ns-empty">Registry index missing — run <code>python scripts/syncDocsGraphAssets.py</code>.</div>';
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
