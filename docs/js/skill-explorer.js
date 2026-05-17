(function(){
  var LEVEL_META_SE = null;
  var TYPE_SYMBOL = null;
  var lastActiveElement = null;

  function _initMeta(meta) {
    if (!meta) return;
    var lc = meta.levelColors || {};
    var ll = meta.levelLabels || {};
    LEVEL_META_SE = {};
    Object.keys(lc).forEach(function(k) {
      if (k === '0★' || k === '1★') return; // explorer only shows 2★+
      LEVEL_META_SE[k] = { name: ll[k] || k, color: lc[k].hex, bg: lc[k].bg, border: lc[k].border };
    });
    TYPE_SYMBOL = meta.typeSymbols || { basic:'○', extra:'◇', unique:'◉', ultimate:'◆' };
  }

  var REPO_SLUG = (function(){
    var m = location.hostname.match(/^(.+)\.github\.io$/);
    if (m) return m[1] + '/gaia-skill-tree';
    return 'mbtiongson1/gaia-skill-tree';
  })();

  function esc(v) {
    return String(v == null ? '':''+v)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function effectiveLabel(skill) {
    if (!skill) return '';
    var level = skill.level || '';
    var effective = skill.effectiveLevel || level;
    return effective && effective !== level ? (level + ' → ' + effective) : level;
  }

  function copyText(text, btn) {
    navigator.clipboard.writeText(text).then(function(){
      var orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(function(){ btn.textContent = orig; }, 1600);
    }).catch(function(){ btn.textContent = 'Error'; setTimeout(function(){ btn.textContent = 'Copy'; }, 1600); });
  }

  // ── DATA RESOLUTION ──────────────────────────────────────────
  function waitForData(cb) {
    // The named-skills IIFE exposes data on window after init
    var tries = 0;
    function check() {
      if (window._gaiaSkillMap && window._gaiaNamedBuckets) { cb(); return; }
      if (++tries > 40) { cb(); return; }
      setTimeout(check, 150);
    }
    check();
  }

  function findNamedSkill(id) {
    var buckets = window._gaiaNamedBuckets || {};
    for (var ref in buckets) {
      var arr = buckets[ref];
      for (var i = 0; i < arr.length; i++) {
        if (arr[i].id === id) return arr[i];
      }
    }
    return null;
  }

  function findGeneric(id) {
    return (window._gaiaSkillMap || {})[id] || null;
  }

  // ── RENDER HERO ──────────────────────────────────────────────
  // Stage 3 — hero is the .plaque--detail variant of the shared
  // component family. Markup emission moved entirely to plaque.js;
  // this function now just builds the ns object (merging generic
  // type/level when needed) and hands it to plaque.renderDetail.
  // The "Open Repo" topbar button is still wired here because it
  // lives in the surrounding modal chrome, not in the plaque.
  function renderHero(ns, generic) {
    var type = (generic && generic.type) || ns.type || 'basic';
    var links = ns.links || {};
    var repoUrl = links.github || links.npm || '';

    // Build the entry passed to plaque.renderDetail. Use the generic
    // type if the named entry doesn't carry one. Description falls
    // back to the generic description so the right column is never
    // empty for a wired-up generic skill.
    var detailNs = {
      id: ns.id,
      name: ns.name,
      title: ns.title,
      level: ns.level,
      type: type,
      contributor: ns.contributor,
      origin: ns.origin,
      description: ns.description || (generic && generic.description) || '',
      tags: Array.isArray(ns.tags) ? ns.tags : [],
      links: links,
      genericSkillRef: ns.genericSkillRef,
    };

    var heroHtml = (window.plaque && typeof window.plaque.renderDetail === 'function')
      ? window.plaque.renderDetail(detailNs)
      : '';

    document.getElementById('seHero').innerHTML = heroHtml;

    // wire Open Repo button (modal chrome — outside the plaque)
    var openBtn = document.getElementById('seOpenRepo');
    if (repoUrl) { openBtn.onclick = function(){ window.open(repoUrl,'_blank','noopener'); }; openBtn.style.display=''; }
    else { openBtn.style.display = 'none'; }
  }

  // ── RENDER DESCRIPTION TAB ───────────────────────────────────
  function renderDescription(ns, generic) {
    var el = document.getElementById('se-description');
    if (!el) return;
    var prereqsHtml = '';
    var derivsHtml = '';
    if (generic) {
      var sm = window._gaiaSkillMap || {};
      if (Array.isArray(generic.prerequisites) && generic.prerequisites.length) {
        prereqsHtml = '<div class="se-docs-block"><h4>Prerequisites</h4><div>' +
          generic.prerequisites.map(function(id){ var s=sm[id]||{name:id}; return '<span class="se-known-agent">' + esc(s.name||id) + '</span>'; }).join('') + '</div></div>';
      }
      if (Array.isArray(generic.derivatives) && generic.derivatives.length) {
        derivsHtml = '<div class="se-docs-block"><h4>Unlocks</h4><div>' +
          generic.derivatives.map(function(id){ var s=sm[id]||{name:id}; return '<span class="se-known-agent">' + esc(s.name||id) + '</span>'; }).join('') + '</div></div>';
      }
    }
    el.innerHTML = '<div class="se-flow-h">' + _se_icon('external-link') + ' About this skill</div>' +
      '<p style="line-height:1.75;margin-bottom:1.5rem">' + esc(ns.description || '') + '</p>' +
      prereqsHtml + derivsHtml;
  }

  // ── RENDER INSTALL TAB ───────────────────────────────────────
  // Stage 1 — sprite-driven copy icons via the shared gaiaIcon() helper.
  function _se_icon(id, size){
    return (typeof window.gaiaIcon === 'function')
      ? window.gaiaIcon(id, { size: size || 15 })
      : '<svg class="ico" width="' + (size || 15) + '" height="' + (size || 15) + '" aria-hidden="true"></svg>';
  }
  function COPY_ICON(){ return _se_icon('copy', 15); }

  function renderInstall(ns) {
    var el = document.getElementById('se-install');
    var id = ns.id;
    var links = ns.links || {};
    var repoUrl = links.github || links.npm || '';
    var cloneUrl = repoUrl && repoUrl.includes('github.com') ? repoUrl.replace(/\.git$/,'') : repoUrl;
    var skillsAddRef = repoUrl || id;
    if (repoUrl && repoUrl.includes('github.com')) {
      skillsAddRef = repoUrl
        .replace('/blob/', '/tree/')
        .replace(/\/SKILL\.md$/i, '')
        .replace(/\.git$/, '');
    }

    function installBlock(label, sublabel, cmd, recommended, copyable) {
      var cls = 'se-install-block' + (recommended ? ' recommended' : '');
      return '<div class="' + cls + '">' +
        '<div class="se-install-label">' + label + (sublabel ? '<span>' + sublabel + '</span>' : '') + '</div>' +
        '<code class="se-install-cmd">' + esc(cmd) + '</code>' +
        (copyable !== false ? '<button class="se-copy-btn" title="Copy to clipboard" data-cmd="' + esc(cmd) + '">' + COPY_ICON() + '</button>' : '') +
      '</div>';
    }

    el.innerHTML = '<div class="se-flow-h">' + COPY_ICON() + ' Installation</div>' +
      installBlock('Gaia', '★ recommended', 'gaia install ' + id, true) +
      installBlock('npx', 'skills package', 'npx skills add ' + skillsAddRef, false) +
      (cloneUrl ? installBlock('Git Clone', '', 'git clone ' + cloneUrl, false) : '');

    el.querySelectorAll('.se-copy-btn').forEach(function(btn){
      btn.onclick = function(){
        navigator.clipboard.writeText(btn.dataset.cmd).then(function(){
          btn.innerHTML = _se_icon('copy-check', 15);
          setTimeout(function(){ btn.innerHTML = COPY_ICON(); }, 1600);
        }).catch(function(){ btn.textContent = '!'; setTimeout(function(){ btn.innerHTML = COPY_ICON(); }, 1600); });
      };
    });
  }

  // ── RENDER DOCS TAB ──────────────────────────────────────────
  function renderDocs(ns, generic) {
    var el = document.getElementById('se-docs');
    var links = ns.links || {};
    var repoUrl = links.github || links.npm || '';
    var issuesUrl = repoUrl && repoUrl.includes('github.com') ? repoUrl.replace(/\.(git|\/?)$/,'') + '/issues' : '';
    var readmeUrl = repoUrl && repoUrl.includes('github.com') ? repoUrl.replace(/\.(git|\/?)$/,'') + '#readme' : '';

    var evidenceHtml = '';
    if (generic && Array.isArray(generic.evidence) && generic.evidence.length) {
      evidenceHtml = '<div class="se-docs-block"><h4>Evidence</h4>' +
        generic.evidence.map(function(ev){
          return '<div class="se-evidence-row">' +
            '<span class="se-ev-class">'+esc(ev.class||'?')+'</span>' +
            '<a class="se-ev-link" href="'+esc(ev.source||'#')+'" target="_blank" rel="noopener">'+esc(ev.source||'—')+'</a>' +
            '<span class="se-ev-date">'+esc(ev.date||'')+'</span>' +
          '</div>';
        }).join('') + '</div>';
    }

    var demeritText = (generic && Array.isArray(generic.demerits) && generic.demerits.length)
      ? ('  ·  Demerits: <strong style="color:var(--apex-gold)">' + esc(generic.demerits.join(', ')) + '</strong>')
      : '';
    var skillDefHtml = generic ? '<div class="se-docs-block"><h4>Generic Skill Definition</h4>' +
      '<p style="line-height:1.75;margin-bottom:.8rem">'+esc(generic.description||'')+'</p>' +
      '<p style="font-size:.82rem;color:var(--muted)">Status: <strong style="color:var(--text)">'+esc(generic.status||'provisional')+'</strong>  ·  Level: <strong style="color:var(--text)">'+esc(effectiveLabel(generic)||'')+'</strong>' + demeritText + '</p>' +
    '</div>' : '';

    var agentsHtml = '';
    if (generic && Array.isArray(generic.knownAgents) && generic.knownAgents.length) {
      agentsHtml = '<div class="se-docs-block"><h4>Known Agents</h4><div>' +
        generic.knownAgents.map(function(a){ return '<span class="se-known-agent">'+esc(a)+'</span>'; }).join('') +
      '</div></div>';
    }

    var linksHtml = '<div class="se-docs-block"><h4>Links</h4>' +
      (repoUrl ? '<p style="margin-bottom:.5rem"><a style="color:var(--basic)" href="'+esc(repoUrl)+'" target="_blank" rel="noopener">Repository ↗</a></p>' : '') +
      (readmeUrl ? '<p style="margin-bottom:.5rem"><a style="color:var(--basic)" href="'+esc(readmeUrl)+'" target="_blank" rel="noopener">README ↗</a></p>' : '') +
      (issuesUrl ? '<p><a style="color:var(--basic)" href="'+esc(issuesUrl)+'" target="_blank" rel="noopener">Issues ↗</a></p>' : '') +
    '</div>';

    el.innerHTML = '<div class="se-flow-h">' + _se_icon('external-link') + ' Documentation</div>' + skillDefHtml + evidenceHtml + agentsHtml + linksHtml;
  }

  // ── RENDER FLOWCHART (upgrade path) ─────────────────────────
  function renderFlowchart(ns, generic) {
    var el = document.getElementById('se-upgrade');
    var sm = window._gaiaSkillMap || {};
    var buckets = window._gaiaNamedBuckets || {};
    var lm = LEVEL_META_SE;

    // Stage 2 — flow-node level chips render through the rank-badge
    // component. The previous inline-style chip is replaced by a chip
    // variant; data-level on the .flow-node itself is preserved for
    // the glow / shimmer rules.
    function rankChip(level) {
      if (!level) return '';
      return (typeof window.rankBadge === 'function')
        ? window.rankBadge(level, { variant: 'chip', label: level })
        : '';
    }

    function flowNode(id, name, contrib, level, typeStr, isCurrent, isNamed) {
      var clsExtra = isCurrent ? ' current' : '';
      var ghostCls = isNamed ? '' : ' flow-node-ghost';
      // Stage 3 — Honor Red carried by the .fn-contrib CSS rule, not inline.
      var contribHtml = contrib ? '<span class="fn-contrib">' + esc(contrib) + '</span>' : '';
      var levelHtml = rankChip(level);
      return '<div class="flow-node' + clsExtra + ghostCls + '" data-level="' + esc(level||'') + '" data-id="' + esc(id) + '" onclick="openSkillExplorer(\'' + id.replace(/'/g,"\\'") + '\')" tabindex="0" role="button">' +
        levelHtml + '<span class="fn-name">' + esc(name||id) + '</span>' + contribHtml +
      '</div>';
    }

    // Row 0: prerequisite generic skills (show named if available)
    var prereqs = generic && Array.isArray(generic.prerequisites) ? generic.prerequisites : [];
    var prereqNodes = prereqs.map(function(id){
      var s = sm[id] || {};
      var namedBucket = buckets[id];
      if (namedBucket && namedBucket.length) {
        var nb = namedBucket[0];
        return flowNode(nb.id, nb.name||nb.id, nb.contributor, nb.level, '', false, true);
      }
      return flowNode(id, s.name||id, '', s.level||'', '', false, false);
    });

    // Row 1: named implementations — stacked card deck
    var siblings = (buckets[ns.genericSkillRef] || []);
    var namedHtml = '';
    if (siblings.length > 1) {
      namedHtml = '<div class="se-stack-deck" data-count="' + siblings.length + '">';
      siblings.forEach(function(sib, idx) {
        var isCur = sib.id === ns.id;
        var zIdx = isCur ? siblings.length : siblings.length - idx;
        var rot = isCur ? 0 : (idx % 2 === 0 ? -3 : 3) * (idx + 1) * 0.5;
        namedHtml += '<div class="se-stack-card' + (isCur ? ' se-stack-current' : '') +
          '" style="z-index:' + zIdx + ';transform:rotate(' + rot + 'deg)" ' +
          'onclick="openSkillExplorer(\'' + sib.id.replace(/'/g,"\\'") + '\')" tabindex="0" role="button">' +
          rankChip(sib.level) +
          '<span class="fn-name">' + esc(sib.name || sib.id) + '</span>' +
          '<span class="fn-contrib">' + esc(sib.contributor) + '</span>' +
        '</div>';
      });
      namedHtml += '</div>';
    } else {
      namedHtml = flowNode(ns.id, ns.name||ns.id, ns.contributor, ns.level, '', true, true);
    }

    // Row 2: derivative generic skills (show named if available, with lock icon for unnamed)
    var derivs = generic && Array.isArray(generic.derivatives) ? generic.derivatives : [];
    var derivNodes = derivs.map(function(id){
      var s = sm[id] || {};
      var namedBucket = buckets[id];
      if (namedBucket && namedBucket.length) {
        var nb = namedBucket[0];
        return flowNode(nb.id, nb.name||nb.id, nb.contributor, nb.level, '', false, true);
      }
      return '<div class="flow-node flow-node-ghost flow-node-locked" data-level="' + esc(s.level||'') + '" data-id="' + esc(id) + '" onclick="openSkillExplorer(\'' + id.replace(/'/g,"\\'") + '\')">' +
        '<span class="fn-lock">&#x1F512;</span>' +
        '<span class="fn-name">' + esc(s.name||id) + '</span>' +
      '</div>';
    });

    // Fusion requirements label
    var fusionHtml = '';
    if (prereqs.length >= 2) {
      fusionHtml = '<div class="se-fusion-label">&#x2728; Fuses from ' + prereqs.length + ' prerequisites</div>';
    }

    function makeRow(label, nodes, id) {
      if (!nodes.length) return '';
      return '<div>' +
        '<div class="se-flowchart-row-label">' + label + '</div>' +
        '<div class="se-flowchart-row" id="' + id + '">' + nodes.join('') + '</div>' +
      '</div>';
    }

    function makeRowHtml(label, html, id) {
      if (!html) return '';
      return '<div>' +
        '<div class="se-flowchart-row-label">' + label + '</div>' +
        '<div class="se-flowchart-row" id="' + id + '">' + html + '</div>' +
      '</div>';
    }

    el.innerHTML = '<div class="se-flow-h">' + _se_icon('sparkle') + ' Upgrade Path &amp; Adjacent Skills</div>' +
      fusionHtml +
      '<div class="se-flowchart-wrap" id="seFlowWrap">' +
        '<div class="se-flowchart-rows">' +
          makeRow('Prerequisites', prereqNodes, 'sfRow0') +
          makeRowHtml('Named Implementations', namedHtml, 'sfRow1') +
          makeRow('Unlocks', derivNodes, 'sfRow2') +
        '</div>' +
        '<svg class="se-flowchart-svg" id="seFlowSvg"></svg>' +
      '</div>';

    // Draw SVG edges after a brief layout settle
    setTimeout(function(){ drawFlowEdges(); }, 80);
  }

  function drawFlowEdges() {
    var wrap = document.getElementById('seFlowWrap');
    var svg = document.getElementById('seFlowSvg');
    if (!wrap || !svg) return;
    svg.innerHTML = '';
    var wRect = wrap.getBoundingClientRect();
    var rowIds = [['sfRow0','sfRow1'],['sfRow1','sfRow2']];
    rowIds.forEach(function(pair){
      var fromEl = document.getElementById(pair[0]);
      var toEl   = document.getElementById(pair[1]);
      if (!fromEl || !toEl) return;
      var fromNodes = fromEl.querySelectorAll('.flow-node');
      var toNodes   = toEl.querySelectorAll('.flow-node');
      if (!fromNodes.length || !toNodes.length) return;
      // connect each source to each target (for small counts); cap at 3x3
      var froms = Array.from(fromNodes).slice(0,3);
      var tos   = Array.from(toNodes).slice(0,3);
      froms.forEach(function(fn){
        var fr = fn.getBoundingClientRect();
        var fx = fr.left + fr.width/2 - wRect.left;
        var fy = fr.bottom - wRect.top;
        tos.forEach(function(tn){
          var tr = tn.getBoundingClientRect();
          var tx = tr.left + tr.width/2 - wRect.left;
          var ty = tr.top - wRect.top;
          var cy = (fy + ty) / 2;
          var path = document.createElementNS('http://www.w3.org/2000/svg','path');
          path.setAttribute('d','M'+fx+','+fy+' C'+fx+','+cy+' '+tx+','+cy+' '+tx+','+ty);
          path.setAttribute('stroke','rgba(56,189,248,.22)');
          path.setAttribute('stroke-width','1.5');
          path.setAttribute('fill','none');
          path.setAttribute('stroke-dasharray','4 3');
          svg.appendChild(path);
        });
      });
    });
  }

  // ── RENDER TIMELINE ──────────────────────────────────────────
  function demeritLabel(id) {
    var labels = {
      'niche-integration': 'Niche Integration',
      'experimental-feature': 'Experimental Feature',
      'heavyweight-dependency': 'Heavyweight Dependency',
    };
    return labels[id] || String(id || '').replace(/-/g, ' ');
  }

  function demeritTimelineEvents(generic) {
    if (!generic || !Array.isArray(generic.demerits) || !generic.demerits.length) return [];
    return [{
      date: '2026-05-09',
      msg: 'Demerit noted: ' + generic.demerits.map(demeritLabel).join(', '),
      sha: 'e336695',
    }];
  }

  function withDemeritTimeline(evts, generic) {
    return (evts || []).concat(demeritTimelineEvents(generic)).sort(function(a, b) {
      return String(b.date || '').localeCompare(String(a.date || ''));
    });
  }

  function renderTimeline(ns, generic) {
    var el = document.getElementById('se-timeline');
    el.innerHTML = '<div class="se-flow-h">' + _se_icon('hud-toggle') + ' Update Timeline</div><div class="se-empty">Loading history…</div>';
    var parts = ns.id.split('/');
    var contributor = parts[0], skillName = parts[1] || '';
    var apiUrl = 'https://api.github.com/repos/' + REPO_SLUG +
      '/commits?path=graph%2Fnamed%2F' + contributor + '%2F' + skillName + '.md&per_page=20';
    fetch(apiUrl)
      .then(function(r){ if(!r.ok) throw new Error(r.status); return r.json(); })
      .then(function(commits){
        if (!Array.isArray(commits) || !commits.length) {
          // fallback to static dates
          var evts = [];
          if (ns.createdAt) evts.push({ date: ns.createdAt, msg: 'Skill created', sha: '' });
          if (ns.updatedAt && ns.updatedAt !== ns.createdAt) evts.push({ date: ns.updatedAt, msg: 'Skill updated', sha: '' });
          renderTimelineEvents(el, withDemeritTimeline(evts, generic));
          return;
        }
        var evts = commits.map(function(c){
          return {
            date: (c.commit && c.commit.author && c.commit.author.date) ? c.commit.author.date.slice(0,10) : '',
            msg: (c.commit && c.commit.message) ? c.commit.message.split('\n')[0] : '',
            sha: c.sha ? c.sha.slice(0,7) : ''
          };
        });
        renderTimelineEvents(el, withDemeritTimeline(evts, generic));
      })
      .catch(function(){
        var evts = [];
        if (ns.createdAt) evts.push({ date: ns.createdAt, msg: 'Skill created', sha: '' });
        if (ns.updatedAt && ns.updatedAt !== ns.createdAt) evts.push({ date: ns.updatedAt, msg: 'Skill updated', sha: '' });
        renderTimelineEvents(el, withDemeritTimeline(evts, generic));
      });
  }

  function renderTimelineEvents(el, evts) {
    if (!evts.length) { el.innerHTML = '<div class="se-flow-h">' + _se_icon('hud-toggle') + ' Update Timeline</div><div class="se-empty">No history available.</div>'; return; }
    el.innerHTML = '<div class="se-flow-h">' + _se_icon('hud-toggle') + ' Update Timeline</div><div class="se-timeline">' +
      evts.map(function(ev){
        return '<div class="se-tl-event">' +
          '<div class="se-tl-dot"></div>' +
          '<div class="se-tl-date">' + esc(ev.date) + '</div>' +
          '<div class="se-tl-msg">' + esc(ev.msg) + '</div>' +
          (ev.sha ? '<div class="se-tl-sha">' + esc(ev.sha) + '</div>' : '') +
        '</div>';
      }).join('') +
    '</div>';
  }

  // ── MAIN OPEN / CLOSE ────────────────────────────────────────
  var TYPE_GLYPH = { ultimate: '◆', extra: '◇', basic: '○' };

  window.openUnnamedPopup = function(skill) {
    var pop = document.getElementById('unnamedSkillPopup');
    if (!pop) return;
    var glyph = TYPE_GLYPH[skill.type] || '◇';
    // Stage 4 — pull tier colour from the canonical tokens (--tier-<name>)
    // rather than hardcoding per-tier hex codes. Falls back to --tier-basic
    // for any unrecognised tier.
    var rootStyle = getComputedStyle(document.documentElement);
    var glyphColor = rootStyle.getPropertyValue('--tier-' + (skill.type || 'basic')).trim()
      || rootStyle.getPropertyValue('--tier-basic').trim();
    document.getElementById('uspGlyph').textContent = glyph;
    document.getElementById('uspGlyph').style.color = glyphColor;
    document.getElementById('uspName').textContent = skill.name || skill.id;
    if (skill.type === 'ultimate') {
      document.getElementById('uspName').style.color = 'var(--apex-gold)';
    } else {
      document.getElementById('uspName').style.color = 'var(--text)';
    }
    document.getElementById('uspId').textContent = skill.id;
    var cmd = 'gaia propose /' + skill.id + (skill.type === 'ultimate' ? ' --ultimate' : '');
    document.getElementById('uspCmd').textContent = cmd;
    document.getElementById('uspCmd').dataset.cmd = cmd;
    var bodyEl = pop.querySelector('.usp-body');
    if (bodyEl) bodyEl.innerHTML = 'This skill has no named implementation yet. <span class="usp-cta">Be the first to claim it</span> — build a real implementation, submit it for review, and your name goes on the canonical registry forever.';
    var existingLink = pop.querySelector('.usp-details-link');
    if (existingLink) existingLink.remove();
    pop.classList.add('open');
    document.body.style.overflow = 'hidden';
  };

  window.openNamedPopup = function(ns) {
    var pop = document.getElementById('unnamedSkillPopup');
    if (!pop) return;
    var lmEntry = (LEVEL_META_SE && LEVEL_META_SE[ns.level]) || {};
    // Stage 4 — fall back to --tier-basic via the token system (no hardcoded hex).
    var _rootStyle = getComputedStyle(document.documentElement);
    var _fallbackTier = _rootStyle.getPropertyValue('--tier-basic').trim();
    document.getElementById('uspGlyph').textContent = TYPE_GLYPH[ns.type] || '◇';
    document.getElementById('uspGlyph').style.color = lmEntry.color || _fallbackTier;
    // Phase 8c — wrap contributor mentions in handleLink so they route to
    // the profile page. uspName retains the slug + handle layout but the
    // contributor is now a hover-underlined link.
    var nspContribLink = (typeof window.handleLink === 'function')
      ? window.handleLink(ns.contributor || '')
      : '<span class="atlas-handle atlas-handle--inline">@' + esc(ns.contributor || '') + '</span>';
    document.getElementById('uspName').innerHTML = nspContribLink + ' / ' + esc(ns.name || ns.id.split('/')[1] || ns.id);
    document.getElementById('uspId').textContent = ns.id;
    var bodyEl = pop.querySelector('.usp-body');
    if (bodyEl) bodyEl.innerHTML = 'Named implementation by ' + nspContribLink + '. Select an install method:';
    var cmd = 'gaia install ' + ns.id;
    document.getElementById('uspCmd').textContent = cmd;
    document.getElementById('uspCmd').dataset.cmd = cmd;
    var existingLink = pop.querySelector('.usp-details-link');
    if (!existingLink) {
      var link = document.createElement('div');
      link.className = 'usp-details-link';
      link.innerHTML = '<a href="#" onclick="document.getElementById(\'unnamedSkillPopup\').classList.remove(\'open\');document.body.style.overflow=\'\';openSkillExplorer(\'' + ns.id.replace(/'/g,"\\'") + '\');return false;">View full details →</a>';
      pop.querySelector('.usp-card').appendChild(link);
    } else {
      existingLink.innerHTML = '<a href="#" onclick="document.getElementById(\'unnamedSkillPopup\').classList.remove(\'open\');document.body.style.overflow=\'\';openSkillExplorer(\'' + ns.id.replace(/'/g,"\\'") + '\');return false;">View full details →</a>';
    }
    pop.classList.add('open');
    document.body.style.overflow = 'hidden';
  };

  function openExplorer(id) {
    var explorerEl = document.getElementById('skillExplorer');
    if (explorerEl && !explorerEl.classList.contains('open')) {
      lastActiveElement = document.activeElement;
    }
    waitForData(function(){
      // Stage 4 — meta source-of-truth is registry/gaia.json.meta (loaded
      // by named-skills.js into window._gaiaMeta). No local fallback dicts;
      // if meta is missing, the open is a no-op + console error.
      _initMeta(window._gaiaMeta);
      if (!LEVEL_META_SE) {
        // eslint-disable-next-line no-console
        console.error('[gaia] Explorer meta missing — cannot open detail.');
        return;
      }

      var ns = findNamedSkill(id);
      if (!ns) {
        // fallback: generic skill ref bucket
        var buckets = window._gaiaNamedBuckets || {};
        if (buckets[id] && buckets[id].length) { ns = buckets[id][0]; }
      }
      if (!ns) {
        // no named implementation — show the "claim this skill" popup if it's a known generic skill
        var genericSkill = (window._gaiaSkillMap || {})[id];
        if (genericSkill) window.openUnnamedPopup(genericSkill);
        return;
      }
      var generic = ns.genericSkillRef ? findGeneric(ns.genericSkillRef) : null;

      var parts = ns.id.split('/');
      var handle = parts[0];
      var skillName = parts[1] || handle;
      var hasSlash = parts.length > 1;

      var type = (generic && generic.type) || ns.type || 'basic';
      var color = (type === 'ultimate') ? 'var(--apex-gold)' : ((LEVEL_META_SE && LEVEL_META_SE[ns.level]) ? LEVEL_META_SE[ns.level].color : 'inherit');

      var bHtml = '';
      if (hasSlash) {
        bHtml += '<span class="atlas-handle">@' + esc(handle) + '</span>';
        bHtml += '<span style="color:var(--muted); opacity: 0.5; margin: 0 4px;">/</span>';
      }
      var slugStyle = 'font-size: inherit; color: ' + color + ';';
      if (type === 'ultimate' && ns.level === '6★') {
        slugStyle += ' animation: tree-rainbow-glow 4s linear infinite;';
      } else if (type === 'ultimate') {
        slugStyle += ' animation: none;';
      }
      bHtml += '<span class="plaque__slug" style="' + slugStyle + '">' + esc(skillName) + '</span>';

      document.getElementById('skillExplorer').classList.add('open');
      document.getElementById('seBreadcrumb').innerHTML = bHtml;
      document.getElementById('skillExplorer').scrollTop = 0;
      document.body.style.overflow = 'hidden';

      renderHero(ns, generic);
      renderDescription(ns, generic);
      renderInstall(ns);
      renderDocs(ns, generic);
      renderFlowchart(ns, generic);
      renderTimeline(ns, generic);

      // Accessibility: Move focus to the modal close button
      var closeBtn = document.getElementById('seClose');
      if (closeBtn) closeBtn.focus();

      // Export button
      document.getElementById('seExport').onclick = function(){
        var data = JSON.stringify({ namedSkill: ns, generic: generic }, null, 2);
        var blob = new Blob([data], { type: 'application/json' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = ns.id.replace('/','_') + '.json';
        a.click();
      };

      // Share button
      document.getElementById('seShare').onclick = function(){
        var url = location.origin + location.pathname + '#explorer/' + ns.id;
        if (navigator.share) {
          navigator.share({ title: ns.name || ns.id, url: url }).catch(function(){});
        } else {
          navigator.clipboard.writeText(url).then(function(){
            var btn = document.getElementById('seShare');
            var orig = btn.textContent;
            btn.textContent = 'Copied!';
            setTimeout(function(){ btn.textContent = orig; }, 1600);
          });
        }
      };

      // Push hash (skip if already correct)
      var newHash = '#explorer/' + ns.id;
      if (location.hash !== newHash) history.pushState(null,'',newHash);
    });
  }

  function closeExplorer() {
    var el = document.getElementById('skillExplorer');
    if (el) el.classList.remove('open');
    document.body.style.overflow = '';
    if (lastActiveElement && typeof lastActiveElement.focus === 'function') {
      lastActiveElement.focus();
      lastActiveElement = null;
    }
  }

  // Expose globally for onclick handlers — must be synchronous, before DOMContentLoaded
  window.openSkillExplorer = openExplorer;

  // ── DOM EVENT SETUP (deferred — overlay HTML is parsed after this script) ──
  function initExplorerDOM() {
    var backEl = document.getElementById('seBack');
    if (backEl) backEl.onclick = function(){ closeExplorer(); history.back(); };

    var closeEl = document.getElementById('seClose');
    if (closeEl) closeEl.onclick = function(){ closeExplorer(); history.pushState(null, '', location.pathname); };

    // Unnamed popup close + copy
    var pop = document.getElementById('unnamedSkillPopup');
    function closeUnnamed() { if (pop) { pop.classList.remove('open'); document.body.style.overflow = ''; } }
    var uspClose = document.getElementById('uspClose');
    if (uspClose) uspClose.onclick = closeUnnamed;
    if (pop) pop.addEventListener('click', function(e){ if (e.target === pop) closeUnnamed(); });
    var uspCopy = document.getElementById('uspCopyBtn');
    // Stage 1 — sprite-driven icons (shared sprite via gaiaIcon helper).
    function _usp_icon(id){
      return (typeof window.gaiaIcon === 'function')
        ? window.gaiaIcon(id, { size: 13 })
        : '<svg class="ico" width="13" height="13" aria-hidden="true"></svg>';
    }
    if (uspCopy) uspCopy.addEventListener('click', function(){
      var cmd = document.getElementById('uspCmd').dataset.cmd || document.getElementById('uspCmd').textContent;
      navigator.clipboard.writeText(cmd).then(function(){
        uspCopy.innerHTML = _usp_icon('copy-check');
        setTimeout(function(){ uspCopy.innerHTML = _usp_icon('copy'); }, 1500);
      });
    });

    function routeHash() {
      var m = location.hash.match(/^#explorer\/(.+\/[^/?#]+)$/);
      if (m) { openExplorer(m[1]); }
      else { closeExplorer(); }
    }
    window.addEventListener('hashchange', routeHash);
    routeHash();

    // Focus trap and accessibility for skillExplorer
    var explorer = document.getElementById('skillExplorer');
    if (explorer) {
      explorer.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          // Trigger click for role="button" elements (like flow-node)
          if (e.target.getAttribute('role') === 'button' && e.target.tabIndex === 0) {
            e.preventDefault();
            e.target.click();
          }
        }
      });
    }

    document.addEventListener('keydown', function(e) {
      var explorer = document.getElementById('skillExplorer');
      if (!explorer || !explorer.classList.contains('open')) return;

      if (e.key === 'Escape') {
        var closeEl = document.getElementById('seClose');
        if (closeEl) closeEl.click();
        return;
      }

      if (e.key === 'Tab') {
        var focusables = explorer.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        var visibleFocusables = Array.from(focusables).filter(function(el) {
          return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length) && !el.hasAttribute('disabled');
        });

        if (visibleFocusables.length === 0) {
          e.preventDefault();
          return;
        }

        var first = visibleFocusables[0];
        var last = visibleFocusables[visibleFocusables.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            last.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === last) {
            first.focus();
            e.preventDefault();
          }
        }
      }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initExplorerDOM);
  } else {
    initExplorerDOM();
  }
})();

/* ─── SKILL EXPLORER OVERLAY ─── */
(function() {
  var treeDialog = document.getElementById('treeDialog');
  var treeNavBtn = document.getElementById('treeNavBtn');
  var treeCloseBtn = document.getElementById('treeCloseBtn');
  var treeCopyBtn = document.getElementById('treeCopyBtn');
  var treeDownloadBtn = document.getElementById('treeDownloadBtn');
  var treeDialogPre = document.getElementById('treeDialogPre');
  var treeHeader = treeDialog.querySelector('.tree-dialog-header');
  var _treeContent = null;

  var SKELETON = [
    'GAIA SKILL TREE  ─────────  ·  ───────────────────────',
    '══════════════════════════════════════════════════════',
    '──────────────────────────────────────────────────────',
    '══════════════════════════════════════════════════════',
    '',
    '◆ ──────────────────────────────────────────  [──]',
    '──────────────────────────────────────────────────────',
    '  ├─ ◇ ────────────────────  [───]',
    '  │  ├─ ○ ────────────  [─]',
    '  │  ├─ ○ ──────────  [0]',
    '  │  └─ ○ ──────────────────  [─]',
    '  ├─ ◇ ────────────────────────────  [──]',
    '  │  ├─ ◇ ────────────  [───]',
    '  │  │  ├─ ○ ────────────  [─]',
    '  │  │  ├─ ○ ──────────  [─]',
    '  │  │  └─ ○ ─────────────────────  [─]',
    '  │  ├─ ○ ───────────────  [─]',
    '  │  └─ ○ ──────────  [─]',
    '  └─ ◇ ────────────────────────  [──]',
    '     ├─ ○ ───────────────────────────  [─]',
    '     └─ ○ ─────────────────────  [─]',
    '',
    '◆ ──────────────────────────────────────  [──]',
    '──────────────────────────────────────────────────────',
    '  ├─ ○ ─────────────────  [──]',
    '  ├─ ◇ ─────────────────  [───]',
    '  │  ├─ ○ ────────────  [─]',
    '  │  ├─ ○ ──────────  [0]',
    '  │  └─ ○ ──────────────────  [─]',
    '  └─ ○ ─────────────────  [──]',
    '',
    '◆ ────────────────────────────────────────────  [──]',
    '──────────────────────────────────────────────────────',
    '  ├─ ◇ ────────────────────────────  [───]',
    '  │  ├─ ○ ─────────────────  [──]',
    '  │  ├─ ○ ──────────────────────  [─]',
    '  │  └─ ○ ────────────────  [─]',
    '  ├─ ◇ ──────────────────────────  [───]',
    '  │  ├─ ○ ──────────────────  [──]',
    '  │  ├─ ○ ────────────  [─]',
    '  │  └─ ○ ─────────────────────  [─]',
    '  └─ ○ ────────────────────────────────  [──]',
  ].join('\n');

  function openTreeDialog() {
    treeDialog.style.cssText = '';
    if (typeof treeDialog.showModal === 'function') treeDialog.showModal();
    else treeDialog.setAttribute('open', '');
    if (_treeContent === null) {
      treeDialogPre.textContent = SKELETON;
      treeDialogPre.classList.add('tree-skeleton');
      fetch('tree.md')
        .then(function(r) { return r.ok ? r.text() : Promise.reject(r.status); })
        .then(function(text) {
          _treeContent = text;
          treeDialogPre.innerHTML = highlightTree(text);
          treeDialogPre.classList.remove('tree-skeleton');
        })
        .catch(function() {
          treeDialogPre.textContent = 'Could not load tree.md.';
          treeDialogPre.classList.remove('tree-skeleton');
        });
    }
  }

  function esc(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // Phase 8d — wrap a contributor span in a profile-page anchor so the
  // tree dialog renders handles as hover-underlined links. Mirrors the
  // atlas-helpers handleLink() convention used everywhere else.
  function handleAnchor(handle, inner) {
    if (!handle) return inner;
    var href = './u/' + encodeURIComponent(handle) + '/';
    return '<a class="atlas-handle" href="' + href + '">' + inner + '</a>';
  }

  // ── Token helpers ──────────────────────────────────────────────────────
  function glyphSpan(cls, glyph) {
    return '<span class="' + cls + '">' + glyph + '</span>';
  }

  // Colorize rank pills like [3★], [3★ · Evolved], [3★ · Unclaimed]
  function colorizeRankPills(html) {
    // Match [N★ · Suffix] or plain [N★]
    return html.replace(
      /\[(\d★)(?:(\s·\s)([^\]]+))?\]/g,
      function(_, rank, dot, suffix) {
        var n = rank.charAt(0);
        var inner = '<span class="tree-rank-digit">' + rank + '</span>';
        if (dot && suffix) {
          var suffixClass = suffix.trim() === 'Unclaimed'
            ? 'tree-unclaimed'
            : 'tree-rank-suffix';
          inner += '<span class="tree-rank-sep">' + esc(dot) + '</span>'
                 + '<span class="' + suffixClass + '">' + esc(suffix) + '</span>';
        }
        return '<span class="tree-rank tree-rank-' + n + '">[' + inner + ']</span>';
      }
    );
  }

  // Colorize (↑ see above) shared-prereq markers
  function colorizeShared(html) {
    return html.replace(/\(↑ see above\)/g,
      '<span class="tree-shared">(&#x2191; see above)</span>');
  }

  // Colorize owned marker ✓ and unowned · markers
  function colorizeOwned(html) {
    return html.replace(/^(<span[^>]*>)?(✓)/,
      function(m, pre, mark) { return (pre || '') + '<span class="tree-owned">' + mark + '</span>'; });
  }

  function highlightTree(text) {
    var ultIdx = 0;
    var unqIdx = 0;
    var inBasics = false;
    var lines = text.split('\n');
    var output = [];

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      // Track when we enter the Basics section
      if (line.indexOf('Basics —') !== -1) {
        inBasics = true;
      }

      // 1. Ultimate Skill lines (◆)
      var m = line.match(/^(\s*[·✓]\s*)?(◆)(\s+)(\S+)(.*)$/);
      if (m) {
        var ownerMark = m[1] ? (m[1].indexOf('✓') >= 0
          ? '<span class="tree-owned">✓</span> '
          : '<span class="tree-unowned">·</span> ') : '';
        var glyph = glyphSpan('tree-glyph-ult', m[2]);
        var skillId = m[4];
        var suffix = m[5];
        var delay = -((ultIdx++ * 0.9) % 4);
        var slash = skillId.indexOf('/');
        var skillHtml;
        if (slash > 0) {
          var ultHandle = skillId.slice(0, slash);
          skillHtml = handleAnchor(ultHandle, '<span class="tree-ult-contributor">' + esc(ultHandle) + '</span>') +
                      '<span class="tree-ult-slash">/</span>' +
                      '<span class="tree-ult-skillname">' + esc(skillId.slice(slash + 1)) + '</span>';
        } else {
          skillHtml = '<span class="tree-ult-id">' + esc(skillId) + '</span>';
        }
        var suffixHtml = colorizeRankPills(colorizeShared(esc(suffix)));
        output.push('<span class="tree-ult-line" style="animation-delay:' + delay + 's">' +
               ownerMark + glyph + esc(m[3]) + skillHtml + suffixHtml + '</span>');
        continue;
      }

      // 2. Unique Skill lines (◉)
      var u = line.match(/^(\s*[·✓]\s*)?([\s│├└─]*)(◉)(\s+)(\S+)(.*)$/);
      if (u) {
        var uOwner = u[1] ? (u[1].indexOf('✓') >= 0
          ? '<span class="tree-owned">✓</span> '
          : '<span class="tree-unowned">·</span> ') : '';
        var uPrefix = esc(u[2]);
        var uGlyph = glyphSpan('tree-glyph-uni', u[3]);
        var uid = u[5];
        var usuffix = u[6];
        var udelay = -((unqIdx++ * 0.9) % 4);
        var uslash = uid.indexOf('/');
        var uskillHtml;
        var isGold = usuffix.indexOf('5★') >= 0 || usuffix.indexOf('6★') >= 0;
        var uniqueClass = isGold ? 'tree-unique-skillname tree-unique-gold' : 'tree-unique-skillname';
        if (uslash > 0) {
          var uHandle = uid.slice(0, uslash);
          uskillHtml = handleAnchor(uHandle, '<span class="tree-unique-contributor">' + esc(uHandle) + '</span>') +
                       '<span class="tree-unique-slash">/</span>' +
                       '<span class="' + uniqueClass + '">' + esc(uid.slice(uslash + 1)) + '</span>';
        } else {
          uskillHtml = '<span class="' + uniqueClass + '">' + esc(uid) + '</span>';
        }
        var usuffixHtml = colorizeRankPills(colorizeShared(esc(usuffix)));
        output.push('<span class="tree-unique-line" style="animation-delay:' + udelay + 's">' +
               uOwner + uPrefix + uGlyph + esc(u[4]) + uskillHtml + usuffixHtml + '</span>');
        continue;
      }

      // 3. Extra Skill lines (◇)
      var e = line.match(/^(\s*[·✓]\s*)?([\s│├└─]*)(◇)(\s+)(\S+)(.*)$/);
      if (e) {
        var eOwner = e[1] ? (e[1].indexOf('✓') >= 0
          ? '<span class="tree-owned">✓</span> '
          : '<span class="tree-unowned">·</span> ') : '';
        var ePrefix = esc(e[2]);
        var eGlyph = glyphSpan('tree-glyph-ext', e[3]);
        var eid = e[5];
        var esuffix = e[6];
        var eslash = eid.indexOf('/');
        var eskillHtml;
        if (eslash > 0) {
          var eHandle = eid.slice(0, eslash);
          eskillHtml = handleAnchor(eHandle, '<span class="tree-extra-contributor">' + esc(eHandle) + '</span>') +
                       '<span class="tree-extra-slash">/</span>' +
                       '<span class="tree-extra-skillname">' + esc(eid.slice(eslash + 1)) + '</span>';
        } else {
          eskillHtml = '<span class="tree-extra-id">' + esc(eid) + '</span>';
        }
        var esuffixHtml = colorizeRankPills(colorizeShared(esc(esuffix)));
        output.push('<span class="tree-extra-line">' + eOwner + ePrefix + eGlyph + esc(e[4]) + eskillHtml + esuffixHtml + '</span>');
        continue;
      }

      // 4. Basic Skill lines (○)
      var b = line.match(/^(\s*[·✓]\s*)?([\s│├└─]*)(○)(\s+)(\S+)(.*)$/);
      if (b) {
        var bOwner = b[1] ? (b[1].indexOf('✓') >= 0
          ? '<span class="tree-owned">✓</span> '
          : '<span class="tree-unowned">·</span> ') : '';
        var bPrefix = esc(b[2]);
        var bGlyph = glyphSpan('tree-glyph-basic', b[3]);
        var bid = b[5];
        var bsuffix = b[6];
        var bslash = bid.indexOf('/');
        var bskillHtml;
        if (bslash > 0) {
          var bHandle = bid.slice(0, bslash);
          bskillHtml = handleAnchor(bHandle, '<span class="tree-basic-contributor">' + esc(bHandle) + '</span>') +
                       '<span class="tree-basic-slash">/</span>' +
                       '<span class="tree-basic-skillname">' + esc(bid.slice(bslash + 1)) + '</span>';
        } else {
          bskillHtml = '<span class="tree-basic-id">' + esc(bid) + '</span>';
        }
        var bsuffixHtml = colorizeRankPills(colorizeShared(esc(bsuffix)));
        var lineClass = inBasics ? 'tree-basic-line tree-pure-line' : 'tree-basic-line';
        output.push('<span class="' + lineClass + '">' + bOwner + bPrefix + bGlyph + esc(b[4]) + bskillHtml + bsuffixHtml + '</span>');
        continue;
      }

      // 5. Separators and Catch-alls
      if (/^[═─]{3,}/.test(line.trim())) {
        output.push('<span class="tree-sep">' + esc(line) + '</span>');
        continue;
      }

      var out = esc(line);
      // Colorize standalone glyphs in non-skill lines (section headers etc.)
      out = out.replace(/◇/g, glyphSpan('tree-glyph-ext', '◇'));
      out = out.replace(/○/g, glyphSpan('tree-glyph-basic', '○'));
      out = out.replace(/◉/g, glyphSpan('tree-glyph-uni', '◉'));
      out = out.replace(/◆/g, glyphSpan('tree-glyph-ult', '◆'));
      out = colorizeRankPills(out);
      out = colorizeShared(out);
      output.push(out);
    }

    // Wrap basics lines in a container
    var finalOutput = '';
    var inContainer = false;
    for (var j = 0; j < output.length; j++) {
      if (output[j].indexOf('tree-pure-line') !== -1) {
        if (!inContainer) {
          finalOutput += '<div class="tree-pure-container">';
          inContainer = true;
        }
        finalOutput += output[j];
      } else {
        if (inContainer) {
          finalOutput += '</div>';
          inContainer = false;
        }
        finalOutput += output[j] + '\n';
      }
    }
    if (inContainer) finalOutput += '</div>';

    return finalOutput;
  }

  function closeTreeDialog() {
    if (treeDialog.close) treeDialog.close();
    else treeDialog.removeAttribute('open');
  }

  treeNavBtn.addEventListener('click', openTreeDialog);
  treeCloseBtn.addEventListener('click', closeTreeDialog);
  treeDialog.addEventListener('click', function(e) {
    if (e.target === treeDialog) closeTreeDialog();
  });

  treeCopyBtn.addEventListener('click', function() {
    var text = _treeContent || treeDialogPre.textContent;
    navigator.clipboard.writeText(text).then(function() {
      treeCopyBtn.textContent = 'Copied!';
      treeCopyBtn.classList.add('copied');
      setTimeout(function() {
        treeCopyBtn.textContent = 'Copy';
        treeCopyBtn.classList.remove('copied');
      }, 1800);
    });
  });

  treeDownloadBtn.addEventListener('click', function() {
    var text = _treeContent || treeDialogPre.textContent;
    var blob = new Blob([text], { type: 'text/plain' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'gaia-skill-tree.md';
    a.click();
    URL.revokeObjectURL(a.href);
  });

  /* ── drag ── */
  var drag = { on: false, ox: 0, oy: 0, startL: 0, startT: 0 };

  treeHeader.addEventListener('mousedown', function(e) {
    if (e.target.closest('button')) return;
    var rect = treeDialog.getBoundingClientRect();
    treeDialog.style.margin = '0★';
    treeDialog.style.position = 'fixed';
    treeDialog.style.left = rect.left + 'px';
    treeDialog.style.top = rect.top + 'px';
    drag.on = true;
    drag.ox = e.clientX;
    drag.oy = e.clientY;
    drag.startL = rect.left;
    drag.startT = rect.top;
    treeHeader.classList.add('dragging');
    e.preventDefault();
  });

  document.addEventListener('mousemove', function(e) {
    if (!drag.on) return;
    var W = window.innerWidth, H = window.innerHeight;
    var dw = treeDialog.offsetWidth, dh = treeDialog.offsetHeight;
    var l = Math.max(0, Math.min(W - dw, drag.startL + e.clientX - drag.ox));
    var t = Math.max(0, Math.min(H - dh, drag.startT + e.clientY - drag.oy));
    treeDialog.style.left = l + 'px';
    treeDialog.style.top = t + 'px';
  });

  document.addEventListener('mouseup', function() {
    if (!drag.on) return;
    drag.on = false;
    treeHeader.classList.remove('dragging');
  });
})();
