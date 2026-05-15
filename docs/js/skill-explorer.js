(function(){
  var LEVEL_META_SE = null;
  var TYPE_SYMBOL = null;

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
  function renderHero(ns, generic) {
    var lm = LEVEL_META_SE[ns.level] || LEVEL_META_SE['2★'];
    var typeColor = ns.type === 'ultimate' ? '#f59e0b' : ns.type === 'unique' ? '#7c3aed' : ns.type === 'extra' ? '#c084fc' : '#38bdf8';
    var typeSymbol = TYPE_SYMBOL[(generic && generic.type) || 'basic'];
    var links = ns.links || {};
    var repoUrl = links.github || links.npm || '';

    var badgesHtml = [
      '<span class="se-badge" style="color:' + lm.color + ';background:' + lm.bg + ';border-color:' + lm.border + '">' + esc(ns.level) + ' · ' + lm.name + '</span>',
      generic ? '<span class="se-badge" style="color:' + typeColor + ';background:rgba(0,0,0,.3);border-color:' + typeColor + '40">' + typeSymbol + ' ' + esc(generic.type || '') + '</span>' : '',
      ns.origin ? '<span class="se-badge" style="color:#fbbf24;background:rgba(251,191,36,.1);border-color:rgba(251,191,36,.3)">★ origin</span>' : '',
    ].filter(Boolean).join('');

    var installCmd = 'gaia install ' + ns.id;
    // Phase 8c — slash-name priority: lead with namedSlug(ns) in honor red
    // (e.g. /autoresearch), demote the long-form title to a muted subtitle.
    var slug = (typeof window.namedSlug === 'function') ? window.namedSlug(ns) : ('/' + (ns.id.split('/')[1] || ns.id));
    var contribLink = (typeof window.handleLink === 'function')
      ? window.handleLink(ns.contributor || '')
      : '<span style="color:#ef4444;font-weight:700">' + esc(ns.contributor || '') + '</span>';
    var heroLeft = '<div class="se-hero-card" data-level="' + esc(ns.level) + '" data-type="' + esc((generic && generic.type) || 'basic') + '">' +
      '<div class="se-node-orb se-node-orb--' + esc((generic && generic.type) || 'basic') + (ns.level === '6★' ? ' se-node-orb--vi' : '') + '"></div>' +
      (repoUrl ? '<a class="se-github-link" href="' + esc(repoUrl) + '" target="_blank" rel="noopener">Show in GitHub ↗</a>' : '') +
      '<div class="se-skill-name named-slug" title="' + esc(ns.id) + '">' + esc(slug) + '</div>' +
      (ns.name ? '<div class="se-skill-subtitle" style="font-family:var(--font-display);font-size:1rem;color:var(--muted);margin-top:.1rem;margin-bottom:.4rem">' + esc(ns.name) + '</div>' : '') +
      '<div class="se-contrib">' + contribLink + '</div>' +
      '<div class="se-badges">' + badgesHtml + '</div>' +
      (ns.title ? '<div style="font-style:italic;color:var(--muted);font-size:.88rem;margin-bottom:.8rem">"' + esc(ns.title) + '"</div>' : '') +
      (generic ? '<div style="font-size:.82rem;color:var(--muted)">Generic skill: <strong style="color:var(--text)">' + esc(generic.name || ns.genericSkillRef) + '</strong></div>' : '') +
      (generic ? '<div style="font-size:.8rem;color:var(--muted);margin-top:.2rem">Claimed/effective level: <strong style="color:var(--text)">' + esc(effectiveLabel(generic)) + '</strong></div>' : '') +
      '<div class="se-hero-install"><span class="se-hero-prompt">$</span><span class="se-hero-cmd">' + esc(installCmd) + '</span><button class="se-hero-copy" data-cmd="' + esc(installCmd) + '" onclick="event.stopPropagation();navigator.clipboard.writeText(this.dataset.cmd).then(function(){})">Copy</button></div>' +
    '</div>';

    var tags = Array.isArray(ns.tags) ? ns.tags : [];
    var heroRight = '<div class="se-desc-panel">' +
      '<h3>Description</h3>' +
      '<p class="se-desc-text">' + esc(ns.description || (generic && generic.description) || '') + '</p>' +
      (tags.length ? '<div class="se-tags">' + tags.map(function(t){ return '<span class="se-tag">' + esc(t) + '</span>'; }).join('') + '</div>' : '') +
    '</div>';

    document.getElementById('seHero').innerHTML = heroLeft + heroRight;

    // wire Open Repo button
    var openBtn = document.getElementById('seOpenRepo');
    if (repoUrl) { openBtn.onclick = function(){ window.open(repoUrl,'_blank','noopener'); }; openBtn.style.display=''; }
    else { openBtn.style.display = 'none'; }
  }

  // ── RENDER DESCRIPTION TAB ───────────────────────────────────
  function renderDescription(ns, generic) {
    var el = document.getElementById('se-description');
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
    el.innerHTML = '<div class="se-flow-h">&#9432; About this skill</div>' +
      '<p style="line-height:1.75;margin-bottom:1.5rem">' + esc(ns.description || '') + '</p>' +
      prereqsHtml + derivsHtml;
  }

  // ── RENDER INSTALL TAB ───────────────────────────────────────
  var COPY_ICON = '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M11 5V3a1 1 0 00-1-1H3a1 1 0 00-1 1v7a1 1 0 001 1h2"/></svg>';

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
        (copyable !== false ? '<button class="se-copy-btn" title="Copy to clipboard" data-cmd="' + esc(cmd) + '">' + COPY_ICON + '</button>' : '') +
      '</div>';
    }

    el.innerHTML = '<div class="se-flow-h">' + COPY_ICON + ' Installation</div>' +
      installBlock('Gaia', '★ recommended', 'gaia install ' + id, true) +
      installBlock('npx', 'skills package', 'npx skills add ' + skillsAddRef, false) +
      (cloneUrl ? installBlock('Git Clone', '', 'git clone ' + cloneUrl, false) : '');

    el.querySelectorAll('.se-copy-btn').forEach(function(btn){
      btn.onclick = function(){
        navigator.clipboard.writeText(btn.dataset.cmd).then(function(){
          btn.innerHTML = '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="#4ade80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8l4 4 8-8"/></svg>';
          setTimeout(function(){ btn.innerHTML = COPY_ICON; }, 1600);
        }).catch(function(){ btn.textContent = '!'; setTimeout(function(){ btn.innerHTML = COPY_ICON; }, 1600); });
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
      ? ('  ·  Demerits: <strong style="color:#fbbf24">' + esc(generic.demerits.join(', ')) + '</strong>')
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

    el.innerHTML = '<div class="se-flow-h">&#128196; Documentation</div>' + skillDefHtml + evidenceHtml + agentsHtml + linksHtml;
  }

  // ── RENDER FLOWCHART (upgrade path) ─────────────────────────
  function renderFlowchart(ns, generic) {
    var el = document.getElementById('se-upgrade');
    var sm = window._gaiaSkillMap || {};
    var buckets = window._gaiaNamedBuckets || {};
    var lm = LEVEL_META_SE;

    function makeLevelStyle(level) {
      var m = lm[level]; if (!m) return '';
      return 'color:' + m.color + ';background:' + m.bg + ';border-color:' + m.border;
    }

    function flowNode(id, name, contrib, level, typeStr, isCurrent, isNamed) {
      var lmEntry = lm[level] || {};
      var clsExtra = isCurrent ? ' current' : '';
      var ghostCls = isNamed ? '' : ' flow-node-ghost';
      var contribHtml = contrib ? '<span class="fn-contrib" style="color:#ef4444">' + esc(contrib) + '</span>' : '';
      var levelHtml = level ? '<span class="fn-level" style="' + makeLevelStyle(level) + '">' + esc(level) + '</span>' : '';
      return '<div class="flow-node' + clsExtra + ghostCls + '" data-level="' + esc(level||'') + '" data-id="' + esc(id) + '" onclick="openSkillExplorer(\'' + id.replace(/'/g,"\\'") + '\')">' +
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
          'onclick="openSkillExplorer(\'' + sib.id.replace(/'/g,"\\'") + '\')">' +
          '<span class="fn-level" style="' + makeLevelStyle(sib.level) + '">' + esc(sib.level) + '</span>' +
          '<span class="fn-name">' + esc(sib.name || sib.id) + '</span>' +
          '<span class="fn-contrib" style="color:#ef4444">' + esc(sib.contributor) + '</span>' +
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

    el.innerHTML = '<div class="se-flow-h">&#9650; Upgrade Path &amp; Adjacent Skills</div>' +
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
    el.innerHTML = '<div class="se-flow-h">&#9203; Update Timeline</div><div class="se-empty">Loading history…</div>';
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
    if (!evts.length) { el.innerHTML = '<div class="se-flow-h">&#9203; Update Timeline</div><div class="se-empty">No history available.</div>'; return; }
    el.innerHTML = '<div class="se-flow-h">&#9203; Update Timeline</div><div class="se-timeline">' +
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
    var glyphColor = skill.type === 'ultimate' ? '#f59e0b' : skill.type === 'extra' ? '#c084fc' : '#38bdf8';
    document.getElementById('uspGlyph').textContent = glyph;
    document.getElementById('uspGlyph').style.color = glyphColor;
    document.getElementById('uspName').textContent = skill.name || skill.id;
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
    document.getElementById('uspGlyph').textContent = TYPE_GLYPH[ns.type] || '◇';
    document.getElementById('uspGlyph').style.color = lmEntry.color || '#38bdf8';
    // Phase 8c — wrap contributor mentions in handleLink so they route to
    // the profile page. uspName retains the slug + handle layout but the
    // contributor is now a hover-underlined link.
    var nspContribLink = (typeof window.handleLink === 'function')
      ? window.handleLink(ns.contributor || '')
      : '<span style="color:#ef4444;font-weight:700">@' + esc(ns.contributor || '') + '</span>';
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
    waitForData(function(){
      // Initialize meta from loaded data (set by named-skills.js)
      _initMeta(window._gaiaMeta);
      // fallback if meta not in data
      if (!LEVEL_META_SE) {
        LEVEL_META_SE = {
          '2★':  { name:'Named', color:'#63cab7', bg:'rgba(99,202,183,.15)', border:'rgba(99,202,183,.4)' },
          '3★': { name:'Evolved', color:'#a78bfa', bg:'rgba(167,139,250,.15)', border:'rgba(167,139,250,.4)' },
          '4★':  { name:'Hardened', color:'#e879f9', bg:'rgba(232,121,249,.15)', border:'rgba(232,121,249,.4)' },
          '5★':  { name:'Transcendent', color:'#fbbf24', bg:'rgba(251,191,36,.15)', border:'rgba(251,191,36,.4)' },
          '6★': { name:'Transcendent ★', color:'#fbbf24', bg:'rgba(251,191,36,.22)', border:'rgba(251,191,36,.55)' },
        };
      }
      if (!TYPE_SYMBOL) {
        TYPE_SYMBOL = { basic:'○', extra:'◇', ultimate:'◆' };
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

      document.getElementById('skillExplorer').classList.add('open');
      document.getElementById('seBreadcrumb').textContent = ns.id;
      document.getElementById('skillExplorer').scrollTop = 0;
      document.body.style.overflow = 'hidden';

      renderHero(ns, generic);
      renderDescription(ns, generic);
      renderInstall(ns);
      renderDocs(ns, generic);
      renderFlowchart(ns, generic);
      renderTimeline(ns, generic);

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
    var CHECK_SM = '<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="#4ade80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8l4 4 8-8"/></svg>';
    var CLIP_SM = '<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M11 5V3a1 1 0 00-1-1H3a1 1 0 00-1 1v7a1 1 0 001 1h2"/></svg>';
    if (uspCopy) uspCopy.addEventListener('click', function(){
      var cmd = document.getElementById('uspCmd').dataset.cmd || document.getElementById('uspCmd').textContent;
      navigator.clipboard.writeText(cmd).then(function(){
        uspCopy.innerHTML = CHECK_SM;
        setTimeout(function(){ uspCopy.innerHTML = CLIP_SM; }, 1500);
      });
    });

    function routeHash() {
      var m = location.hash.match(/^#explorer\/(.+\/[^/?#]+)$/);
      if (m) { openExplorer(m[1]); }
      else { closeExplorer(); }
    }
    window.addEventListener('hashchange', routeHash);
    routeHash();
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

  function highlightTree(text) {
    var ultIdx = 0;
    var unqIdx = 0;
    return text.split('\n').map(function(line) {
      // 1. Ultimate Skill lines (◆)
      var m = line.match(/^(\s*◆\s*(?:Ultimate Skill:\s*)?)(\S+)(.*)$/);
      if (m) {
        var label = esc(m[1]);
        var skillId = m[2];
        var suffix = esc(m[3]);
        var delay = -((ultIdx++ * 0.9) % 4);
        var slash = skillId.indexOf('/');
        var skillHtml;
        if (slash > 0) {
          skillHtml = '<span class="tree-ult-contributor">' + esc(skillId.slice(0, slash)) + '</span>' +
                      '<span class="tree-ult-slash">/</span>' +
                      '<span class="tree-ult-skillname">' + esc(skillId.slice(slash + 1)) + '</span>';
        } else {
          skillHtml = '<span class="tree-ult-id">' + esc(skillId) + '</span>';
        }
        return '<span class="tree-ult-line" style="animation-delay:' + delay + 's">' +
               label + skillHtml + suffix + '</span>';
      }

      // 2. Unique Skill lines (◉)
      var u = line.match(/^([\s│├└─]*◉\s*(?:Unique Skill:\s*)?)(\S+)(.*)$/);
      if (u) {
        var ulabel = esc(u[1]);
        var uid = u[2];
        var usuffix = esc(u[3]);
        var udelay = -((unqIdx++ * 0.9) % 4);
        var uslash = uid.indexOf('/');
        var uskillHtml;
        var isGold = usuffix.indexOf('5★') >= 0 || usuffix.indexOf('6★') >= 0;
        var uniqueClass = isGold ? 'tree-unique-skillname tree-unique-gold' : 'tree-unique-skillname';
        if (uslash > 0) {
          uskillHtml = '<span class="tree-unique-contributor">' + esc(uid.slice(0, uslash)) + '</span>' +
                       '<span class="tree-unique-slash">/</span>' +
                       '<span class="' + uniqueClass + '">' + esc(uid.slice(slash + 1)) + '</span>';
        } else {
          uskillHtml = '<span class="' + uniqueClass + '">' + esc(uid) + '</span>';
        }
        return '<span class="tree-unique-line" style="animation-delay:' + udelay + 's">' +
               ulabel + uskillHtml + usuffix + '</span>';
      }

      // 3. Extra Skill lines (◇)
      var e = line.match(/^([\s│├└─]*◇\s*(?:Extra Skill:\s*)?)(\S+)(.*)$/);
      if (e) {
        var elabel = esc(e[1]);
        var eid = e[2];
        var esuffix = esc(e[3]);
        var eslash = eid.indexOf('/');
        var eskillHtml;
        if (eslash > 0) {
          eskillHtml = '<span class="tree-extra-contributor">' + esc(eid.slice(0, eslash)) + '</span>' +
                       '<span class="tree-extra-slash">/</span>' +
                       '<span class="tree-extra-skillname">' + esc(eid.slice(eslash + 1)) + '</span>';
        } else {
          eskillHtml = '<span class="tree-extra-id">' + esc(eid) + '</span>';
        }
        return '<span class="tree-extra-line">' + elabel + eskillHtml + esuffix + '</span>';
      }

      // 4. Basic Skill lines (○)
      var b = line.match(/^([\s│├└─]*○\s*)(\S+)(.*)$/);
      if (b) {
        var blabel = esc(b[1]);
        var bid = b[2];
        var bsuffix = esc(b[3]);
        var bslash = bid.indexOf('/');
        var bskillHtml;
        if (bslash > 0) {
          bskillHtml = '<span class="tree-basic-contributor">' + esc(bid.slice(0, bslash)) + '</span>' +
                       '<span class="tree-basic-slash">/</span>' +
                       '<span class="tree-basic-skillname">' + esc(bid.slice(bslash + 1)) + '</span>';
        } else {
          bskillHtml = '<span class="tree-basic-id">' + esc(bid) + '</span>';
        }
        return '<span class="tree-basic-line">' + blabel + bskillHtml + bsuffix + '</span>';
      }

      // 5. Separators and Catch-alls
      if (/^[═─]{3,}/.test(line.trim())) return '<span class="tree-sep">' + esc(line) + '</span>';
      
      var out = esc(line);
      out = out.replace(/◇/g, '<span class="tree-extra-glyph">◇</span>');
      out = out.replace(/○/g, '<span class="tree-basic-glyph">○</span>');
      out = out.replace(/◉/g, '<span class="tree-unique-glyph">◉</span>');
      out = out.replace(/◆/g, '<span class="tree-ult-glyph">◆</span>');
      return out;
    }).join('\n');
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
