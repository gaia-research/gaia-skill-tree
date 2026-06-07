(function(){
  var LEVEL_META_SE = null;
  var TYPE_SYMBOL = null;
  var lastActiveElement = null;
  var _currentNs = null; // tracks the skill open in the explorer

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
      .replace(/\\/g,'\\\\').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
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
    // Pre-named/demoted (≤1★): the repo URL exposes the contributor — withhold it.
    var redacted = window.isRedacted && window.isRedacted(ns.level);
    var repoUrl = (!redacted && (links.github || links.npm)) || '';

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

  function _renderTabbedInstall(ns) {
    var md = ns.installBody || '';
    if (!md) return '';

    var lines = md.split('\n');
    var sections = [];
    var currentSection = { heading: '', content: [] };
    var introLines = [];

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      var match = line.match(/^(###?)\s+(.+)$/);
      if (match) {
        if (currentSection.heading || currentSection.content.length) {
          sections.push(currentSection);
        }
        currentSection = { heading: match[2].trim(), content: [] };
      } else {
        if (currentSection.heading) {
          currentSection.content.push(line);
        } else {
          introLines.push(line);
        }
      }
    }
    if (currentSection.heading || currentSection.content.length) {
      sections.push(currentSection);
    }

    function getTabName(heading) {
      var lower = heading.toLowerCase();
      if (lower.indexOf('step 1') !== -1 || lower.indexOf('machine') !== -1) {
        return 'Machine Setup';
      }
      if (lower.indexOf('step 2') !== -1 || lower.indexOf('team') !== -1) {
        return 'Team Mode';
      }
      if (lower.indexOf('native') !== -1) {
        return 'Native Skills';
      }
      if (lower.indexOf('openclaw') !== -1) {
        return 'OpenClaw';
      }
      if (lower.indexOf('other') !== -1 || lower.indexOf('agent') !== -1 || lower.indexOf('host') !== -1) {
        return 'Host Targets';
      }
      var words = heading.split(/\s+/).filter(Boolean).slice(0, 2);
      return words.map(function(w) {
        return w.charAt(0).toUpperCase() + w.slice(1);
      }).join(' ');
    }

    function renderMarkdownContent(contentLines, isHostTab, tabId) {
      var htmlParts = [];
      var inCodeBlock = false;
      var codeLines = [];
      var tableHeader = null;
      var tableRows = [];

      for (var j = 0; j < contentLines.length; j++) {
        var line = contentLines[j];
        var trimmed = line.trim();

        if (trimmed.startsWith('```')) {
          if (inCodeBlock) {
            inCodeBlock = false;
            var codeText = codeLines.join('\n').trim();
            if (isHostTab && (codeText.indexOf('./setup') !== -1 || codeText.indexOf('./install') !== -1)) {
              htmlParts.push('<div class="se-install-block se-install-block--code">' +
                '<pre class="se-install-code"><code id="se-code-' + tabId + '" data-base="' + esc(codeText) + '">' + esc(codeText) + '</code></pre>' +
                '<button class="se-copy-btn" title="Copy to clipboard" aria-label="Copy to clipboard" id="se-copy-' + tabId + '" data-cmd="' + esc(codeText) + '">' + COPY_ICON() + '</button>' +
                '</div>');
            } else {
              htmlParts.push('<div class="se-install-block se-install-block--code">' +
                '<pre class="se-install-code"><code>' + esc(codeText) + '</code></pre>' +
                '<button class="se-copy-btn" title="Copy to clipboard" aria-label="Copy to clipboard" data-cmd="' + esc(codeText) + '">' + COPY_ICON() + '</button>' +
                '</div>');
            }
            codeLines = [];
          } else {
            inCodeBlock = true;
          }
          continue;
        }

        if (inCodeBlock) {
          codeLines.push(line);
          continue;
        }

        if (trimmed.startsWith('|')) {
          var cells = line.split('|').map(function(s) { return s.trim(); }).filter(function(s, idx, arr) {
            return idx > 0 && idx < arr.length - 1;
          });
          if (cells.length > 0) {
            if (!tableHeader) {
              tableHeader = cells;
            } else if (cells[0].indexOf('---') === -1) {
              tableRows.push(cells);
            }
          }
          continue;
        }

        if (trimmed === '') {
          htmlParts.push('<p></p>');
          continue;
        }

        if (trimmed.startsWith('- ')) {
          htmlParts.push('<li>' + esc(trimmed.slice(2)) + '</li>');
          continue;
        }

        var lineHtml = esc(line)
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/g, '<em>$1</em>')
          .replace(/`(.*?)`/g, '<code>$1</code>');
        htmlParts.push('<p>' + lineHtml + '</p>');
      }

      if (tableHeader && tableRows.length > 0) {
        var agentIdx = -1;
        var flagIdx = -1;
        var pathIdx = -1;

        for (var c = 0; c < tableHeader.length; c++) {
          var h = tableHeader[c].toLowerCase();
          if (h.indexOf('agent') !== -1 || h.indexOf('host') !== -1 || h.indexOf('platform') !== -1) agentIdx = c;
          if (h.indexOf('flag') !== -1 || h.indexOf('argument') !== -1 || h.indexOf('option') !== -1) flagIdx = c;
          if (h.indexOf('path') !== -1 || h.indexOf('install') !== -1 || h.indexOf('destination') !== -1) pathIdx = c;
        }

        if (isHostTab && agentIdx !== -1 && flagIdx !== -1) {
          var dropdownHtml = '<div class="se-dropdown-container">' +
            '<span class="se-dropdown-label">Select Host Agent Target:</span>' +
            '<select class="se-hosts-dropdown" id="se-select-' + tabId + '" data-tabid="' + tabId + '">';
          
          dropdownHtml += '<option value="" data-path="Auto-detects installed agents">Default (Auto-Detect)</option>';
          for (var r = 0; r < tableRows.length; r++) {
            var row = tableRows[r];
            var agentName = row[agentIdx] || '';
            var flagVal = row[flagIdx] || '';
            var pathVal = row[pathIdx] || '';
            dropdownHtml += '<option value="' + esc(flagVal) + '" data-path="' + esc(pathVal) + '">' + esc(agentName) + ' (' + esc(flagVal) + ')' + '</option>';
          }
          dropdownHtml += '</select></div>';
          dropdownHtml += '<div class="se-target-path" id="se-path-' + tabId + '">' +
            '<span>Destination Path:</span>' +
            '<span class="se-mono-path">Auto-detects installed agents</span>' +
            '</div>';

          htmlParts.unshift(dropdownHtml);
        } else {
          var tblHtml = '<div class="se-table-container" style="overflow-x:auto;"><table class="se-markdown-table"><thead><tr>';
          for (var th = 0; th < tableHeader.length; th++) {
            tblHtml += '<th>' + esc(tableHeader[th]) + '</th>';
          }
          tblHtml += '</tr></thead><tbody>';
          for (var tr = 0; tr < tableRows.length; tr++) {
            tblHtml += '<tr>';
            for (var td = 0; td < tableRows[tr].length; td++) {
              tblHtml += '<td>' + esc(tableRows[tr][td]) + '</td>';
            }
            tblHtml += '</tr>';
          }
          tblHtml += '</tbody></table></div>';
          htmlParts.push(tblHtml);
        }
      }

      return htmlParts.join('\n');
    }

    var introHtml = '';
    var validIntroLines = introLines.filter(function(l) { return l.trim() !== ''; });
    if (validIntroLines.length > 0) {
      introHtml = '<div class="se-install-intro" style="margin-bottom:0.75rem; font-size:0.85rem; color:var(--muted);">' + 
        validIntroLines.map(function(l) {
          return esc(l)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
        }).join('<br>') + 
        '</div>';
    }

    var tabHeadersHtml = '<div class="se-tabs-header">';
    var tabPanelsHtml = '<div class="se-tabs-content">';

    for (var idx = 0; idx < sections.length; idx++) {
      var sec = sections[idx];
      var tName = getTabName(sec.heading);
      var tabId = 'tab-' + idx;
      var activeClass = idx === 0 ? ' active' : '';

      tabHeadersHtml += '<button class="se-tab-btn' + activeClass + '" data-target="' + tabId + '">' + esc(tName) + '</button>';
      
      var isHostTab = tName.toLowerCase().indexOf('host') !== -1 || tName.toLowerCase().indexOf('other') !== -1;
      var panelBody = renderMarkdownContent(sec.content, isHostTab, tabId);
      tabPanelsHtml += '<div class="se-tab-panel' + activeClass + '" id="' + tabId + '">' + panelBody + '</div>';
    }

    tabHeadersHtml += '</div>';
    tabPanelsHtml += '</div>';

    return '<div class="se-install-custom">' +
      '<div class="se-flow-h se-install-guide-h">Setup Guide</div>' +
      introHtml +
      '<div class="se-install-tabs-container">' +
      tabHeadersHtml +
      tabPanelsHtml +
      '</div>' +
      '</div>';
  }

  function isGithubUrl(url) {
    try {
      var h = new URL(url).hostname;
      return h === 'github.com' || h === 'raw.githubusercontent.com' || h.endsWith('.github.com');
    } catch(e) { return false; }
  }

  function renderInstall(ns) {
    var el = document.getElementById('se-install');
    var id = ns.id;
    var links = ns.links || {};
    var repoUrl = links.github || links.npm || '';
    var cloneUrl = repoUrl && isGithubUrl(repoUrl) ? repoUrl.replace(/\.git$/,'') : repoUrl;
    var skillsAddRef = repoUrl || id;
    if (repoUrl && isGithubUrl(repoUrl)) {
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
        (copyable !== false ? '<button class="se-copy-btn" title="Copy to clipboard" aria-label="Copy to clipboard" data-cmd="' + esc(cmd) + '">' + COPY_ICON() + '</button>' : '') +
      '</div>';
    }

    var isUlt = ns.level === '5★';
    // Pre-named/demoted (≤1★): withhold the handle in the install id, and hide
    // the npx/git-clone methods (their repo URLs expose the contributor). This
    // is lifted once the skill is named (2★+).
    var redacted = window.isRedacted && window.isRedacted(ns.level);
    var installId = (redacted && id.indexOf('/') !== -1)
      ? ((window.REDACTED_BLOCK || '████████') + '/' + id.split('/').slice(1).join('/'))
      : id;
    var gaiaCmd = isUlt ? 'gaia install --ultimate ' + installId : 'gaia install ' + installId;
    var gaiaLabel = isUlt ? '◆ ultimate suite' : '★ recommended';

    if (ns.suiteComponents && ns.suiteComponents.length > 0 && ns.installBody) {
      el.innerHTML = '<div class="se-flow-h">' + COPY_ICON() + ' Installation</div>' +
        installBlock('Gaia', gaiaLabel, gaiaCmd, true) +
        (redacted ? '' : _renderTabbedInstall(ns));
    } else if (redacted) {
      el.innerHTML = '<div class="se-flow-h">' + COPY_ICON() + ' Installation</div>' +
        installBlock('Gaia', gaiaLabel, gaiaCmd, true) +
        '<div class="se-install-note">Source &amp; package install unlock when this skill is named (2★+).</div>';
    } else {
      el.innerHTML = '<div class="se-flow-h">' + COPY_ICON() + ' Installation</div>' +
        installBlock('Gaia', gaiaLabel, gaiaCmd, true) +
        installBlock('npx', 'skills package', 'npx skills add ' + skillsAddRef, false) +
        (cloneUrl ? installBlock('Git Clone', '', 'git clone ' + cloneUrl, false) : '') +
        (ns.installBody ? _renderInstallBody(ns.installBody) : '');
    }

    el.querySelectorAll('.se-tab-btn').forEach(function(btn) {
      btn.onclick = function() {
        var container = btn.closest('.se-install-tabs-container');
        container.querySelectorAll('.se-tab-btn').forEach(function(b) {
          b.classList.remove('active');
        });
        container.querySelectorAll('.se-tab-panel').forEach(function(p) {
          p.classList.remove('active');
        });
        btn.classList.add('active');
        var targetId = btn.dataset.target;
        var panel = container.querySelector('#' + targetId);
        if (panel) {
          panel.classList.add('active');
        }
      };
    });

    el.querySelectorAll('.se-hosts-dropdown').forEach(function(sel) {
      sel.onchange = function() {
        var tabId = sel.dataset.tabid;
        var codeEl = el.querySelector('#se-code-' + tabId);
        var copyEl = el.querySelector('#se-copy-' + tabId);
        var pathEl = el.querySelector('#se-path-' + tabId);

        if (!codeEl) return;
        var baseCmd = codeEl.dataset.base;
        var selectedVal = sel.value;
        var selectedOpt = sel.options[sel.selectedIndex];
        var pathVal = selectedOpt ? selectedOpt.dataset.path : 'Auto-detects installed agents';

        var updatedCmd = baseCmd;
        if (selectedVal) {
          updatedCmd = baseCmd.replace(/(\.\/setup|\.\/install)(\s+--host\s+\S+)?/g, '$1 ' + selectedVal);
        } else {
          updatedCmd = baseCmd.replace(/(\.\/setup|\.\/install)(\s+--host\s+\S+)?/g, '$1');
        }

        codeEl.textContent = updatedCmd;
        if (copyEl) {
          copyEl.dataset.cmd = updatedCmd;
        }
        if (pathEl) {
          pathEl.innerHTML = '<span>Destination Path:</span><span class="se-mono-path">' + esc(pathVal) + '</span>';
        }
      };
    });

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
    // Pre-named/demoted (≤1★): the repo URL exposes the contributor — withhold it.
    var redacted = window.isRedacted && window.isRedacted(ns.level);
    var repoUrl = (!redacted && (links.github || links.npm)) || '';
    var issuesUrl = 'https://github.com/' + REPO_SLUG + '/issues';
    var readmeUrl = repoUrl && isGithubUrl(repoUrl) ? repoUrl.replace(/\.(git|\/?)$/,'') : '';

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
      (repoUrl ? '<p style="margin-bottom:.5rem; display:flex; align-items:center; gap:.25rem;"><a style="color:var(--basic); display:flex; align-items:center; gap:.35rem;" href="'+esc(repoUrl)+'" target="_blank" rel="noopener">' + _se_icon('github') + ' Repo ↗</a></p>' : '') +
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

    var genericId = generic ? generic.id : ns.genericSkillRef || ns.id;
    var genericObj = sm[genericId] || generic || { id: genericId, type: ns.type, level: ns.level, name: ns.name };
    var currentType = (ns && ns.type) || genericObj.type || 'basic';

    // Slash-name label: contributor in honor-red, skill name in text.
    function createNodeLabel(labelSource, navType, navTarget, level) {
      var parts = String(labelSource).split('/');
      var contrib = parts[0] || '';
      var skillName = parts[1] || labelSource;
      var redacted = window.isRedacted && window.isRedacted(level);
      var inner;
      if (contrib && parts.length > 1) {
        // Pre-named/demoted (≤1★): redact the contributor with the slate block.
        var contribHtml = redacted
          ? '<span class="dag-node-label-contrib plaque__redacted-handle" aria-label="Contributor not yet revealed">████████</span>'
          : '<span class="dag-node-label-contrib">' + esc(contrib) + '</span>';
        inner = contribHtml +
                '<span style="color:var(--muted)">/</span>' +
                '<span class="dag-node-label-name">' + esc(skillName) + '</span>';
      } else {
        inner = '<span class="dag-node-label-name">' + esc(labelSource) + '</span>';
      }
      var navAttr = (navType && navTarget) ? ' data-nav-type="' + esc(navType) + '" data-nav-target="' + esc(navTarget) + '"' : '';
      return '<div class="dag-node-label"' + navAttr + '>' + inner + '</div>';
    }

    // Action-buttons header (Show Fusion).
    function buildFlowActions() {
      return '<div class="se-flow-actions">' +
        '<button type="button" class="se-flow-btn" id="seFlowShowFusion" title="Highlight prerequisites">' +
          _se_icon('sparkle') + 'Show Fusion' +
        '</button>' +
      '</div>';
    }

    // Wire Show Fusion button handlers. Called after innerHTML set.
    function wireFlowActions(focusId) {
      var btnFusion = document.getElementById('seFlowShowFusion');
      if (btnFusion) {
        btnFusion.addEventListener('click', function(e) {
          e.stopPropagation();
          if (window.showFusionOnly) window.showFusionOnly(focusId);
          btnFusion.classList.toggle('active');
        });
      }
    }

    // Short-circuit for Unique-tier current skills: render the current
    // skill alone inside the void zone, with nothing else around it.
    if (currentType === 'unique') {
      var uColor = (ns && ns.level && String(ns.level).indexOf('6') !== -1)
        ? '#ffffff'
        : 'var(--tier-unique, var(--muted))';
      var labelId = (ns && ns.id) ? ns.id : genericId;
      var uniqueNodeHtml = '<div class="git-node git-node--main" data-id="' + esc(genericId) +
          '" data-type="unique" data-level="' + esc((ns && ns.level) || '') + '" data-ghost="false">' +
        '<div class="git-commit-dot" style="--dot-color:' + uColor + '"></div>' +
        createNodeLabel(labelId) +
      '</div>';

      el.innerHTML = '<div class="se-flow-h">' + _se_icon('sparkle') +
          ' Upgrade Path &amp; Adjacent Skills' + buildFlowActions() + '</div>' +
        '<div class="se-flowchart-wrap" id="seFlowWrap">' +
          '<div class="se-flowchart-rows unique-alone">' +
            '<div class="se-flowchart-row void-zone" data-depth="0">' + uniqueNodeHtml + '</div>' +
          '</div>' +
          '<svg class="se-flowchart-svg" id="seFlowSvg"></svg>' +
        '</div>';
      wireFlowActions(genericId);
      return;
    }

    var relatedNodes = {};
    
    function collectAncestors(id) {
      if (relatedNodes[id]) return;
      var s = sm[id];
      if (!s) return;
      relatedNodes[id] = s;
      (s.prerequisites || []).forEach(collectAncestors);
    }
    
    function collectDescendants(id) {
      if (relatedNodes[id]) return;
      var s = sm[id];
      if (!s) return;
      relatedNodes[id] = s;
      (s.prerequisites || []).forEach(function(pid) {
        if (!relatedNodes[pid] && sm[pid]) collectAncestors(pid);
      });
      (s.derivatives || []).forEach(collectDescendants);
    }
    
    if (genericId) {
      relatedNodes[genericId] = sm[genericId] || {id: genericId, name: ns.name, type: ns.type, level: ns.level, prerequisites: generic ? generic.prerequisites : [], derivatives: generic ? generic.derivatives : []};
      (relatedNodes[genericId].prerequisites || []).forEach(collectAncestors);
      (relatedNodes[genericId].derivatives || []).forEach(collectDescendants);
    }

    var depth = {};
    function getDepth(id) {
      if (depth[id] !== undefined) return depth[id];
      depth[id] = -1;
      var maxPre = 0;
      var node = relatedNodes[id];
      if (node && node.prerequisites) {
        node.prerequisites.forEach(function(pid) {
          if (relatedNodes[pid]) maxPre = Math.max(maxPre, getDepth(pid) + 1);
        });
      }
      depth[id] = maxPre;
      return maxPre;
    }
    Object.keys(relatedNodes).forEach(getDepth);
    
    var maxD = 0;
    Object.values(depth).forEach(function(d) { if (d > maxD) maxD = d; });
    var ranks = [];
    for (var r = 0; r <= maxD; r++) ranks.push([]);
    var apexNodes = [];
    var uniqueNodes = [];
    Object.keys(relatedNodes).forEach(function(id) {
      if (depth[id] >= 0) {
        var s = relatedNodes[id];
        if (s.level && String(s.level).indexOf('6') !== -1) {
          apexNodes.push(id);
        } else if (s.type === 'unique') {
          uniqueNodes.push(id);
        } else {
          ranks[depth[id]].push(id);
        }
      }
    });
    if (uniqueNodes.length) {
      ranks.push(uniqueNodes);
    }
    if (apexNodes.length) {
      ranks.push(apexNodes);
      maxD = ranks.length - 1;
    }

    var edges = [];
    Object.keys(relatedNodes).forEach(function(id) {
      var s = relatedNodes[id];
      (s.prerequisites || []).forEach(function(pid) {
        if (relatedNodes[pid]) edges.push({from: pid, to: id});
      });
    });

    var htmlRows = '';
    
    function hashString(str) {
      var h = 0;
      for (var i = 0; i < str.length; i++) h = Math.imul(31, h) + str.charCodeAt(i) | 0;
      return Math.abs(h);
    }
    
    for (var ri = 0; ri <= maxD; ri++) {
      var rank = ranks[ri];
      if (!rank || !rank.length) continue;
      
      var isUniqueRow = rank.every(function(id) { return relatedNodes[id].type === 'unique'; });
      
      var rowHtml = rank.map(function(id, idx) {
        var s = relatedNodes[id];
        var staggerY = (ri === 0 || isUniqueRow) ? 0 : (hashString(id) % 80);

        var isMainSkill = (id === genericId || id === ns.id);
        var extraMainClass = isMainSkill ? ' git-node--main' : '';

        // Resolve the node's data: prefer a named impl, fall back to generic/ghost.
        var namedBucket = buckets[id];
        var hasNamed = !!(namedBucket && namedBucket.length);
        var nb = hasNamed ? namedBucket[0] : null;
        var nodeType = (nb && nb.type) || s.type || 'basic';
        var nodeLevel = (nb && nb.level) || s.level || '';
        var isApex = nodeLevel && String(nodeLevel).indexOf('6') !== -1;
        var dotColor = isApex
          ? '#ffffff'
          : 'var(--tier-' + nodeType + ', var(--muted))';

        // Label source: slash-form for named, raw id for ghost.
        var labelSource = hasNamed ? nb.id : id;

        // Label-click navigation: named → open skill explorer, ghost → propose dialog.
        var navAttr;
        if (hasNamed) {
          navAttr = ' onclick="event.stopPropagation();openSkillExplorer(\'' + nb.id.replace(/\\/g,'\\\\').replace(/'/g,"\\'") + '\');"';
        } else {
          navAttr = ' onclick="event.stopPropagation();(function(id){var sm=window._gaiaSkillMap||{};var g=sm[id];if(g&&typeof window.openUnnamedPopup===\'function\')window.openUnnamedPopup(g);})(\'' + id.replace(/\\/g,'\\\\').replace(/'/g,"\\'") + '\');"';
        }

        return '<div class="git-node' + extraMainClass + '"' +
            ' data-id="' + esc(id) + '"' +
            ' data-type="' + esc(nodeType) + '"' +
            ' data-level="' + esc(nodeLevel) + '"' +
            ' data-ghost="' + (hasNamed ? 'false' : 'true') + '"' +
            ' style="--staggerY:' + staggerY + 'px"' +
            '>' +
          '<div class="git-commit-dot" style="--dot-color: ' + dotColor + '"></div>' +
          createNodeLabel(labelSource, hasNamed ? 'named' : 'ghost', hasNamed ? nb.id : id, nodeLevel) +
        '</div>';
      }).join('');
      
      var voidClass = isUniqueRow ? ' void-zone' : '';
      htmlRows += '<div class="se-flowchart-row' + voidClass + '" data-depth="' + ri + '">' + rowHtml + '</div>';
    }

    // Fusion requirements label
    var fusionHtml = '';
    if (relatedNodes[genericId] && relatedNodes[genericId].prerequisites && relatedNodes[genericId].prerequisites.length >= 2) {
      fusionHtml = '<div class="se-fusion-label">&#x2728; Fuses from ' + relatedNodes[genericId].prerequisites.length + ' prerequisites</div>';
    }

    el.innerHTML = '<div class="se-flow-h">' + _se_icon('sparkle') +
        ' Upgrade Path &amp; Adjacent Skills' + buildFlowActions() + '</div>' +
      '<div class="se-flowchart-wrap" id="seFlowWrap">' +
        '<div class="se-flowchart-rows">' + htmlRows + '</div>' +
        '<svg class="se-flowchart-svg" id="seFlowSvg"></svg>' +
      '</div>' +
      fusionHtml;

    wireFlowActions(genericId);

    // Centralized event delegation for the flowchart
    if (!el._flowWired) {
      el.addEventListener('click', function(e) {
        var node = e.target.closest('.git-node');
        if (node && node.dataset.id) {
          if (window.selectFlowNode) window.selectFlowNode(node.dataset.id);
          return;
        }
        var label = e.target.closest('.dag-node-label');
        if (label && label.dataset.navType && label.dataset.navTarget) {
          e.stopPropagation();
          var target = label.dataset.navTarget;
          if (label.dataset.navType === 'named') {
            openExplorer(target);
          } else {
            var sm = window._gaiaSkillMap || {};
            var g = sm[target];
            if (g && typeof window.openUnnamedPopup === 'function') window.openUnnamedPopup(g);
          }
        }
      });
      el.addEventListener('mouseover', function(e) {
        var node = e.target.closest('.git-node');
        if (node && node.dataset.id) {
          if (!window._selectedFlowNode && window.highlightPaths) window.highlightPaths(node.dataset.id);
        }
      });
      el.addEventListener('mouseout', function(e) {
        var node = e.target.closest('.git-node');
        if (node && node.dataset.id) {
          if (!window._selectedFlowNode && window.unhighlightPaths) window.unhighlightPaths();
        }
      });
      el._flowWired = true;
    }

    setTimeout(function(){ drawFlowEdges(edges); }, 80);
  }

  function drawFlowEdges(edges) {
    var wrap = document.getElementById('seFlowWrap');
    var svg = document.getElementById('seFlowSvg');
    if (!wrap || !svg) return;
    svg.innerHTML = '';
    var wRect = wrap.getBoundingClientRect();
    var sourceOuts = {};
    var targetIns = {};
    (edges || []).forEach(function(e) {
      sourceOuts[e.from] = (sourceOuts[e.from] || 0) + 1;
      targetIns[e.to] = (targetIns[e.to] || 0) + 1;
    });
    var curSourceOut = {};
    var curTargetIn = {};
    
    // Attach edges for hover highlighting
    window._currentDagEdges = edges || [];
    window.highlightPaths = function(nodeId) {
      document.querySelectorAll('.git-path').forEach(function(p) { p.classList.remove('active-path'); });
      var edgesMap = window._currentDagEdges;
      function trace(id) {
        edgesMap.forEach(function(e) {
          if (e.to === id) {
            var p = document.getElementById('path-' + e.from + '-' + e.to);
            if (p) p.classList.add('active-path');
            trace(e.from); // trace down to prerequisites
          }
        });
      }
      trace(nodeId);
    };
    window.unhighlightPaths = function() {
      if (!window._selectedFlowNode) {
        document.querySelectorAll('.git-path').forEach(function(p) { p.classList.remove('active-path', 'dimmed'); });
        document.querySelectorAll('.git-node.show-label').forEach(function(n) { n.classList.remove('show-label'); });
      }
    };

    if (!window._seClickHandlerAdded) {
      document.addEventListener('click', function(e) {
        var clickedNode = e.target.closest('.git-node');
        if (!clickedNode && !e.target.closest('.se-flowchart-wrap')) {
          window._selectedFlowNode = null;
          document.querySelectorAll('.git-node.selected').forEach(function(n) { n.classList.remove('selected'); });
          document.querySelectorAll('.git-node.show-label').forEach(function(n) { n.classList.remove('show-label'); });
          document.querySelectorAll('.git-path.dimmed').forEach(function(p) { p.classList.remove('dimmed'); });
          window.unhighlightPaths && window.unhighlightPaths();
        }
      });
      window._seClickHandlerAdded = true;
    }

    window.selectFlowNode = function(nodeId) {
      var relatedNodes = window.getSeRelatedNodes(nodeId, edges);

      document.querySelectorAll('.git-node.selected').forEach(function(n) { n.classList.remove('selected'); });
      document.querySelectorAll('.git-node.show-label').forEach(function(n) { n.classList.remove('show-label'); });

      var node = document.querySelector('.git-node[data-id="' + nodeId.replace(/\\/g,'\\\\').replace(/"/g, '\\"') + '"]');
      if (node) {
        node.classList.add('selected');
        window._selectedFlowNode = nodeId;
        window.highlightPaths && window.highlightPaths(nodeId);
        window.dimUnrelatedFlowPaths && window.dimUnrelatedFlowPaths(nodeId, edges);
      }
    };
    window._selectedFlowNode = null;

    var edgeMap = {};
    (edges || []).forEach(function(e) {
      var id = 'path-' + e.from + '-' + e.to;
      if (!edgeMap[id]) edgeMap[id] = e;
    });

    window.getSeRelatedNodes = function(nodeId, edgeList) {
      var related = {};
      related[nodeId] = true;

      function traceUp(id) {
        (edgeList || []).forEach(function(e) {
          if (e.to === id && !related[e.from]) {
            related[e.from] = true;
            traceUp(e.from);
          }
        });
      }

      function traceDown(id) {
        (edgeList || []).forEach(function(e) {
          if (e.from === id && !related[e.to]) {
            related[e.to] = true;
            traceDown(e.to);
          }
        });
      }

      traceUp(nodeId);
      traceDown(nodeId);
      return related;
    };

    window.dimUnrelatedFlowPaths = function(nodeId, edgeList) {
      var relatedNodes = window.getSeRelatedNodes(nodeId, edgeList);
      document.querySelectorAll('.git-path').forEach(function(p) {
        p.classList.remove('dimmed');
      });

      (edgeList || []).forEach(function(e) {
        if (!relatedNodes[e.from] || !relatedNodes[e.to]) {
          var pathId = 'path-' + e.from + '-' + e.to;
          var p = document.getElementById(pathId);
          if (p) p.classList.add('dimmed');
        }
      });

      Object.keys(relatedNodes).forEach(function(id) {
        var node = document.querySelector('.git-node[data-id="' + id.replace(/\\/g,'\\\\').replace(/"/g, '\\"') + '"]');
        if (node) node.classList.add('show-label');
      });
    };

    // Show Fusion: lock the focus node and reveal only its prerequisite
    // chain (ancestors). Descendants and sibling branches dim out.
    window.showFusionOnly = function(nodeId) {
      var ancestors = {};
      ancestors[nodeId] = true;
      (edges || []).forEach(function(e) {
        if (e.to === nodeId && !ancestors[e.from]) {
          ancestors[e.from] = true;
        }
      });

      document.querySelectorAll('.git-node.selected').forEach(function(n) { n.classList.remove('selected'); });
      document.querySelectorAll('.git-node.show-label').forEach(function(n) { n.classList.remove('show-label'); });
      document.querySelectorAll('.git-path').forEach(function(p) { p.classList.remove('active-path','dimmed'); });

      var focus = document.querySelector('.git-node[data-id="' + nodeId.replace(/\\/g,'\\\\').replace(/"/g, '\\"') + '"]');
      if (focus) focus.classList.add('selected');
      window._selectedFlowNode = nodeId;

      (edges || []).forEach(function(e) {
        var inAncestry = ancestors[e.from] && ancestors[e.to];
        var pathId = 'path-' + e.from + '-' + e.to;
        var p = document.getElementById(pathId);
        if (!p) return;
        if (inAncestry) p.classList.add('active-path');
        else p.classList.add('dimmed');
      });

      Object.keys(ancestors).forEach(function(id) {
        var n = document.querySelector('.git-node[data-id="' + id.replace(/\\/g,'\\\\').replace(/"/g, '\\"') + '"]');
        if (n) n.classList.add('show-label');
      });
    };

    // Layout thrashing optimization: Pre-calculate all node rects in a single pass
    // to avoid interleaved read/write DOM operations inside the loop.
    var nodeRects = {};
    var nodeEls = {};
    (edges || []).forEach(function(e) {
      if (!nodeEls[e.from]) {
        var el = wrap.querySelector('.git-node[data-id="' + e.from + '"]');
        if (el) {
          nodeEls[e.from] = el;
          var dot = el.querySelector('.git-commit-dot');
          nodeRects[e.from] = (dot || el).getBoundingClientRect();
        }
      }
      if (!nodeEls[e.to]) {
        var el = wrap.querySelector('.git-node[data-id="' + e.to + '"]');
        if (el) {
          nodeEls[e.to] = el;
          var dot = el.querySelector('.git-commit-dot');
          nodeRects[e.to] = (dot || el).getBoundingClientRect();
        }
      }
    });

    var fragment = document.createDocumentFragment();

    (edges || []).forEach(function(e, i) {
      var fromEl = nodeEls[e.from];
      var toEl   = nodeEls[e.to];
      if (!fromEl || !toEl || !nodeRects[e.from] || !nodeRects[e.to]) return;

      var fr = nodeRects[e.from];
      var tr = nodeRects[e.to];

      var fx = fr.left + fr.width/2 - wRect.left + wrap.scrollLeft;
      var fy = fr.top + fr.height/2 - wRect.top + wrap.scrollTop;
      var tx = tr.left + tr.width/2 - wRect.left + wrap.scrollLeft;
      var ty = tr.top + tr.height/2 - wRect.top + wrap.scrollTop;

      var dx = tx - fx;
      var dy = ty - fy;

      // Organic S-curve: control points pull vertically out of each endpoint,
      // creating a flowing vein / river-branch appearance instead of sharp elbows.
      var ctrlDist = Math.abs(dy) * 0.25 + Math.abs(dx) * 0.05;
      var d = 'M' + fx + ',' + fy +
              ' C' + fx + ',' + (fy + ctrlDist) +
              ' ' + tx + ',' + (ty - ctrlDist) +
              ' ' + tx + ',' + ty;

      // Detect tier from source node — drives CSS color via [data-tier]
      var fromType = fromEl.getAttribute('data-type') || 'basic';
      var fromLevel = fromEl.getAttribute('data-level') || '';
      var tier = fromLevel.indexOf('6') !== -1 ? 'apex'
               : ['ultimate','unique','extra','basic'].indexOf(fromType) !== -1 ? fromType
               : 'basic';

      var path = document.createElementNS('http://www.w3.org/2000/svg','path');
      path.setAttribute('id', 'path-' + e.from + '-' + e.to);
      path.setAttribute('d', d);
      path.setAttribute('class', 'git-path');
      path.setAttribute('data-tier', tier);
      fragment.appendChild(path);
    });

    svg.appendChild(fragment);
  }

  // ── RENDER TIMELINE ──────────────────────────────────────────
  var SE_ACTION_ICON = {
    rank_up: '↑', ascend: '✦', name: '@', fuse: '⊕',
    push: '+', evidence: '✓', demote: '↓', propose: '◆',
    bond: '⊙', register: '◎', commit: '·',
    verified: '✓', disputed: '⚠', evidence_added: '⊕'
  };

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
      action: 'demote',
      msg: 'Demerit noted: ' + generic.demerits.map(demeritLabel).join(', '),
      sha: 'e336695',
    }];
  }

  function structuredTimelineEvents(node) {
    if (!node || !Array.isArray(node.timeline) || !node.timeline.length) return [];
    return node.timeline.map(function(t) {
      return {
        date: (t.timestamp || t.date || '').slice(0, 10),
        action: t.action || 'commit',
        msg: t.details || (t.action ? t.action.replace('_', ' ') : ''),
        sha: '',
        contributor: t.contributor || '',
      };
    });
  }

  function mergeTimeline(evts, generic, ns) {
    var all = (evts || [])
      .concat(demeritTimelineEvents(generic))
      .concat(structuredTimelineEvents(generic))
      .concat(structuredTimelineEvents(ns));
    // Deduplicate by date+action+msg
    var seen = {};
    var deduped = [];
    all.forEach(function(ev) {
      var key = (ev.date || '') + '|' + (ev.action || 'commit') + '|' + (ev.msg || '').slice(0, 60);
      if (!seen[key]) { seen[key] = true; deduped.push(ev); }
    });
    return deduped.sort(function(a, b) {
      return String(b.date || '').localeCompare(String(a.date || ''));
    });
  }

  function renderTimeline(ns, generic) {
    var el = document.getElementById('se-changelog');
    el.innerHTML = '<div class="se-flow-h">' + _se_icon('hud-toggle') + ' Evolution Changelog</div><div class="se-empty">Loading history…</div>';
    var parts = ns.id.split('/');
    var contributor = parts[0], skillName = parts[1] || '';
    var apiUrl = 'https://api.github.com/repos/' + REPO_SLUG +
      '/commits?path=registry%2Fnamed%2F' + contributor + '%2F' + skillName + '.md&per_page=20';
    fetch(apiUrl)
      .then(function(r){ if(!r.ok) throw new Error(r.status); return r.json(); })
      .then(function(commits){
        if (!Array.isArray(commits) || !commits.length) {
          var evts = [];
          if (ns.createdAt) evts.push({ date: ns.createdAt, action: 'push', msg: 'Skill created', sha: '' });
          if (ns.updatedAt && ns.updatedAt !== ns.createdAt) evts.push({ date: ns.updatedAt, action: 'commit', msg: 'Skill updated', sha: '' });
          renderTimelineEvents(el, mergeTimeline(evts, generic, ns));
          return;
        }
        var evts = commits.map(function(c){
          return {
            date: (c.commit && c.commit.author && c.commit.author.date) ? c.commit.author.date.slice(0,10) : '',
            action: 'commit',
            msg: (c.commit && c.commit.message) ? c.commit.message.split('\n')[0] : '',
            sha: c.sha ? c.sha.slice(0,7) : ''
          };
        });
        renderTimelineEvents(el, mergeTimeline(evts, generic, ns));
      })
      .catch(function(){
        var evts = [];
        if (ns.createdAt) evts.push({ date: ns.createdAt, action: 'push', msg: 'Skill created', sha: '' });
        if (ns.updatedAt && ns.updatedAt !== ns.createdAt) evts.push({ date: ns.updatedAt, action: 'commit', msg: 'Skill updated', sha: '' });
        renderTimelineEvents(el, mergeTimeline(evts, generic, ns));
      });
  }

  function renderTimelineEvents(el, evts) {
    if (!evts.length) { el.innerHTML = '<div class="se-flow-h">' + _se_icon('hud-toggle') + ' Evolution Changelog</div><div class="se-empty">No history available.</div>'; return; }
    el.innerHTML = '<div class="se-flow-h">' + _se_icon('hud-toggle') + ' Evolution Changelog</div><div class="se-timeline">' +
      evts.map(function(ev){
        var action = ev.action || 'commit';
        var icon = SE_ACTION_ICON[action] || '·';
        var actionLabel = action.replace('_', ' ');
        var contributorHtml = ev.contributor
          ? '<span class="se-tl-contributor">@' + esc(ev.contributor) + '</span> '
          : '';
        return '<div class="se-tl-event">' +
          '<div class="se-tl-dot" data-action="' + esc(action) + '"></div>' +
          '<div class="se-tl-body">' +
            '<div class="se-tl-row">' +
              '<span class="se-tl-action" data-action="' + esc(action) + '"><span class="se-tl-action-icon">' + icon + '</span>' + esc(actionLabel) + '</span>' +
              '<span class="se-tl-date">' + esc(ev.date) + '</span>' +
            '</div>' +
            '<div class="se-tl-msg">' + contributorHtml + esc(ev.msg) + '</div>' +
            (ev.sha ? '<div class="se-tl-sha">' + esc(ev.sha) + '</div>' : '') +
          '</div>' +
        '</div>';
      }).join('') +
    '</div>';
  }

  function renderVariants(ns) {
    var el = document.getElementById('se-upgrade');
    if (!el) return;
    
    // Wire up variant clicks via delegation
    if (!el._wired) {
      el.addEventListener('click', function(e) {
        var item = e.target.closest('.se-variant-item');
        if (item && item.dataset.id) {
          openExplorer(item.dataset.id);
        }
      });
      el._wired = true;
    }

    if (!ns.variants || !ns.variants.length) { el.innerHTML = ''; return; }
    
    var html = '<div class="se-variants-list">' +
      '<div class="se-flow-h">' + _se_icon('view-list') + ' Other Implementations (' + ns.variants.length + ')</div>' +
      '<div class="se-variants-grid">' +
        ns.variants.map(function(v) {
          return '<div class="se-variant-item" data-id="' + esc(v.id) + '">' +
            '<span class="se-variant-handle">@' + esc(v.contributor) + '</span>' +
            '<span class="se-variant-level">' + esc(v.level) + '</span>' +
          '</div>';
        }).join('') +
      '</div></div>';
    el.innerHTML = html;
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
      ? window.handleLink(ns.contributor || '', { level: ns.level })
      : '<span class="atlas-handle atlas-handle--inline">@' + esc(ns.contributor || '') + '</span>';
    document.getElementById('uspName').innerHTML = nspContribLink + ' / ' + esc(ns.name || ns.id.split('/')[1] || ns.id);
    // Withhold the handle in the canonical id for pre-named/demoted (≤1★) skills.
    var uspIdText = ns.id;
    if (window.isRedacted && window.isRedacted(ns.level) && ns.id.indexOf('/') !== -1) {
      uspIdText = (window.REDACTED_BLOCK || '████████') + '/' + ns.id.split('/').slice(1).join('/');
    }
    document.getElementById('uspId').textContent = uspIdText;
    var bodyEl = pop.querySelector('.usp-body');
    if (bodyEl) bodyEl.innerHTML = 'Named implementation by ' + nspContribLink + '. Select an install method:';
    var cmd = 'gaia install ' + ns.id;
    document.getElementById('uspCmd').textContent = cmd;
    document.getElementById('uspCmd').dataset.cmd = cmd;
    var existingLink = pop.querySelector('.usp-details-link');
    if (!existingLink) {
      var link = document.createElement('div');
      link.className = 'usp-details-link';
      link.innerHTML = '<a href="#" class="usp-details-anchor">View full details →</a>';
      pop.querySelector('.usp-card').appendChild(link);
      existingLink = link;
    } else {
      existingLink.innerHTML = '<a href="#" class="usp-details-anchor">View full details →</a>';
    }

    // Wire up the link click
    var anchor = existingLink.querySelector('.usp-details-anchor');
    if (anchor) {
      anchor.onclick = function(e) {
        e.preventDefault();
        document.getElementById('unnamedSkillPopup').classList.remove('open');
        document.body.style.overflow = '';
        openExplorer(ns.id);
      };
    }
    pop.classList.add('open');
    document.body.style.overflow = 'hidden';
  };

  // Cache the original .se-body markup so we can restore it after a
  // cold-load placeholder is shown. Captured lazily on the first call.
  var _seBodyOriginalHTML = null;
  function _ensureSeLoadingStyles() {
    if (document.getElementById('se-loading-styles')) return;
    var style = document.createElement('style');
    style.id = 'se-loading-styles';
    style.textContent =
      '.skill-explorer-loading,.skill-explorer-error{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1rem;padding:4rem 2rem;text-align:center;color:var(--muted);}' +
      '.skill-explorer-spinner{width:36px;height:36px;border:3px solid var(--border,rgba(255,255,255,.1));border-top-color:var(--rank-5,#fbbf24);border-radius:50%;animation:se-spin 0.8s linear infinite;}' +
      '.se-loading-install{margin-top:.5rem;max-width:min(420px,90%);font-size:12px;opacity:.85;}' +
      '@keyframes se-spin{to{transform:rotate(1turn);}}' +
      '.skill-explorer-error button{margin-left:.5rem;padding:.4rem .9rem;font:inherit;background:var(--rank-5,#fbbf24);color:#0f172a;border:none;border-radius:6px;cursor:pointer;}';
    document.head.appendChild(style);
  }
  function _showSeLoading(explorerEl, id) {
    _ensureSeLoadingStyles();
    var bodyEl = explorerEl.querySelector('.se-body');
    if (!bodyEl) return;
    if (_seBodyOriginalHTML === null) _seBodyOriginalHTML = bodyEl.innerHTML;
    // Install command is computable from the id alone — render it on the
    // same paint as the spinner so the user sees the value of opening the
    // modal even on a cold data fetch (~6s in the worst case). The full
    // plaque renders over this once data arrives, replacing this row in
    // place without a flash if the cmd matches.
    var preview = '';
    if (id && typeof id === 'string') {
      var safeId = id.replace(/[<>&"']/g, function(c) {
        return { '<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;' }[c];
      });
      var cmd = 'gaia install ' + safeId;
      var copyClick = "event.stopPropagation();" +
        "if(typeof window.nsInstCopy==='function'){window.nsInstCopy(this);}" +
        "else{navigator.clipboard.writeText(this.dataset.cmd);}";
      preview =
        '<div class="se-loading-install plaque__install-row ns-install-row" aria-label="Install command">' +
          '<span class="plaque__install-prompt ns-install-prompt">$</span>' +
          '<span class="plaque__install-cmd ns-install-cmd-txt">' + cmd + '</span>' +
          '<button class="plaque__install-copy ns-install-copy" type="button" aria-label="Copy install command" ' +
            'data-cmd="' + cmd + '" onclick="' + copyClick + '">' +
            '<svg width="13" height="13" aria-hidden="true"><use href="assets/icons.svg#copy"/></svg>' +
          '</button>' +
        '</div>';
    }
    bodyEl.innerHTML =
      '<div class="skill-explorer-loading" data-testid="loading">' +
        '<div class="skill-explorer-spinner" aria-hidden="true"></div>' +
        '<p>Loading skill…</p>' +
        preview +
      '</div>';
  }
  function _showSeError(explorerEl, id) {
    _ensureSeLoadingStyles();
    var bodyEl = explorerEl.querySelector('.se-body');
    if (!bodyEl) return;
    bodyEl.innerHTML =
      '<div class="skill-explorer-error" role="alert">' +
        '<p>Couldn\'t load skill data. <button type="button" id="skillExplorerRetry">Try again</button></p>' +
      '</div>';
    var retry = bodyEl.querySelector('#skillExplorerRetry');
    if (retry) retry.onclick = function(){ openExplorer(id); };
  }
  function _restoreSeBody(explorerEl) {
    if (_seBodyOriginalHTML === null) return;
    var bodyEl = explorerEl.querySelector('.se-body');
    if (bodyEl) bodyEl.innerHTML = _seBodyOriginalHTML;
  }

  function openExplorer(id) {
    var explorerEl = document.getElementById('skillExplorer');
    if (explorerEl && !explorerEl.classList.contains('open')) {
      lastActiveElement = document.activeElement;
    }
    // Immediately open modal with loading placeholder — no 6s silent wait.
    if (explorerEl) {
      explorerEl.classList.add('open');
      explorerEl.scrollTop = 0;
      document.body.style.overflow = 'hidden';
      _showSeLoading(explorerEl, id);
    }
    // Wrap waitForData to distinguish cold-cache timeout vs. success.
    function _waitWithTimeout(cb) {
      var tries = 0;
      function check() {
        if (window._gaiaSkillMap && window._gaiaNamedBuckets) {
          cb(true);
          return;
        }
        if (++tries > 40) {
          cb(false);
          return;
        }
        setTimeout(check, 150);
      }
      check();
    }
    _waitWithTimeout(function(success){
      if (!success) {
        // Cold-load timeout — show error with retry
        if (explorerEl) _showSeError(explorerEl, id);
        return;
      }
      // Data is ready — restore the original .se-body skeleton so the
      // child ids (#seHero, #se-install, etc.) exist for render functions.
      if (explorerEl) _restoreSeBody(explorerEl);
      // Stage 4 — meta source-of-truth is registry/gaia.json.meta (loaded
      // by named-skills.js into window._gaiaMeta). No local fallback dicts;
      // if meta is missing, the open is a no-op + console error.
      _initMeta(window._gaiaMeta);
      if (!LEVEL_META_SE) {
        // eslint-disable-next-line no-console
        console.error('[gaia] Explorer meta missing — cannot open detail.');
        if (explorerEl) _showSeError(explorerEl, id);
        return;
      }

      var ns = findNamedSkill(id);
      if (!ns) {
        // fallback: generic skill ref bucket
        var buckets = window._gaiaNamedBuckets || {};
        if (buckets[id] && buckets[id].length) { ns = buckets[id][0]; }
      }
      if (!ns) {
        // no named implementation — close the explorer (it was opened
        // immediately with a loading placeholder) and show the "claim
        // this skill" popup if it's a known generic skill.
        if (explorerEl) {
          explorerEl.classList.remove('open');
          document.body.style.overflow = '';
          _restoreSeBody(explorerEl);
        }
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
      var handleRedacted = window.isRedacted && window.isRedacted(ns.level);
      var color = (LEVEL_META_SE && LEVEL_META_SE[ns.level]) ? LEVEL_META_SE[ns.level].color : 'inherit';
      // LEVEL_META_SE only carries 2★+; a pre-named/demoted (≤1★) skill keeps
      // its plain rank color (--rank-N) — never type rainbow/glow, never the
      // inherited honor-red.
      if (handleRedacted) {
        var _lvlN = parseInt(String(ns.level || '').replace(/\D+/g, ''), 10) || 0;
        color = 'var(--rank-' + _lvlN + ', #38bdf8)';
      } else {
        if (type === 'unique') { color = 'var(--tier-unique, #7c3aed)'; }
        else if (type === 'ultimate') { color = 'var(--apex-gold, #fbbf24)'; }
      }

      var bHtml = '';
      if (hasSlash) {
        if (handleRedacted) {
          // Pre-named/demoted: redact the breadcrumb handle (slate block, mono).
          bHtml += window.redactedHandle({ block: true });
        } else {
          bHtml += '<span class="atlas-handle">@' + esc(handle) + '</span>';
        }
        if (!handleRedacted && ns.origin && typeof window.gaiaIcon === 'function') {
          bHtml += ' <span class="plaque__origin" data-tooltip="Origin contributor: The creator of the first skill version" aria-label="Origin contributor: The creator of the first skill version">' +
            window.gaiaIcon('origin-badge', { size: 16 }) +
            '<span class="origin-info" style="margin-left: 3px; color: var(--muted); opacity: 0.7;">' + window.gaiaIcon('info', { size: 10 }) + '</span>' +
            '</span>';
        }
        bHtml += '<span style="color:var(--muted); opacity: 0.5; margin: 0 4px;">/</span>';
      }
      var slugStyle = 'font-size: inherit; color: ' + color + ';';
      if (!handleRedacted) {
        if (type === 'ultimate') {
          slugStyle += ' animation: tree-rainbow-glow 4s linear infinite;';
        } else if (type === 'extra') {
          slugStyle += ' animation: tree-extra-glow 4s linear infinite;';
        } else if (type === 'unique') {
          slugStyle += ' text-shadow: 0 0 12px rgba(124,58,237,0.6), 0 0 4px rgba(124,58,237,0.3);';
        }
      }
      bHtml += '<span class="plaque__slug" style="' + slugStyle + '">' + esc(skillName) + '</span>';
      document.getElementById('skillExplorer').classList.add('open');
      document.getElementById('seBreadcrumb').innerHTML = bHtml;
      document.getElementById('skillExplorer').scrollTop = 0;
      document.body.style.overflow = 'hidden';

      renderHero(ns, generic);
      _currentNs = ns;
      renderDescription(ns, generic);
      renderInstall(ns);
      renderDocs(ns, generic);
      renderFlowchart(ns, generic);
      renderTimeline(ns, generic);

      // Accessibility: Move focus to the modal close button
      var closeBtn = document.getElementById('seClose');
      if (closeBtn) closeBtn.focus();

      // SKILL.md docs button
      var docsBtn = document.getElementById('seSkillDocs');
      if (docsBtn) {
        var readmeUrlRaw = '';
        // Pre-named/demoted (≤1★): the repo URL exposes the contributor — hide it.
        var docsRedacted = window.isRedacted && window.isRedacted(ns.level);
        var repoUrl = (!docsRedacted && (ns.links && (ns.links.github || ns.links.npm))) || '';
        if (repoUrl && isGithubUrl(repoUrl)) {
          var base = repoUrl.replace(/\.(git|\/?)$/, '').replace('github.com', 'raw.githubusercontent.com');
          readmeUrlRaw = base + '/main/SKILL.md';
        }
        if (!readmeUrlRaw) {
          docsBtn.style.display = 'none';
        } else {
          docsBtn.style.display = '';
          docsBtn.onclick = function() {
            if (window.openDocumentDialog) {
              window.openDocumentDialog(ns.id + ' — SKILL.md', readmeUrlRaw, ns.id.replace('/', '_') + '_SKILL.md');
            }
          };
        }
      }

      // Topbar Share button: a pre-named/demoted (≤1★) skill isn't shareable
      // (no OG card / public permalink) — hide it.
      var seShareBtn = document.getElementById('seShare');
      if (seShareBtn) {
        seShareBtn.style.display = (window.isRedacted && window.isRedacted(ns.level)) ? 'none' : '';
      }

      // Push hash (skip if already correct)
      var newHash = '#explorer/' + ns.id;
      if (location.hash !== newHash) history.pushState(null,'',newHash);
    });
  }

  function closeExplorer() {
    var el = document.getElementById('skillExplorer');
    if (el) el.classList.remove('open');
    _currentNs = null;
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

    // Topbar Share button → same HOH fullscreen modal as the plaque share button
    var shareBtn = document.getElementById('seShare');
    if (shareBtn) {
      shareBtn.onclick = function() {
        if (!_currentNs) return;
        if (typeof window.openHohFullscreenModal !== 'function') return;
        var skillId = _currentNs.id || '';
        var handle  = _currentNs.contributor || skillId.split('/')[0];
        var slug    = skillId.split('/').pop();
        window.openHohFullscreenModal({
          id: skillId,
          contributor: handle,
          name: _currentNs.name || slug,
          level: _currentNs.level || '',
          type: _currentNs.type || 'basic',
          origin: !!_currentNs.origin,
          ogPath: handle && slug ? 'og/' + handle + '/' + slug + '.svg' : '',
          description: _currentNs.description || '',
          tags: Array.isArray(_currentNs.tags) ? _currentNs.tags : [],
        });
      };
    }

    // Delegate plaque__share-btn clicks inside the explorer → HOH fullscreen modal
    var explorerBody = document.getElementById('skillExplorer');
    if (explorerBody) {
      explorerBody.addEventListener('click', function(e) {
        var btn = e.target.closest('.plaque__share-btn');
        if (!btn) return;
        e.stopPropagation();
        if (typeof window.openHohFullscreenModal !== 'function') return;
        var skillId = btn.getAttribute('data-skill-id') || '';
        var handle  = btn.getAttribute('data-handle') || skillId.split('/')[0];
        var name    = btn.getAttribute('data-skill-name') || skillId.split('/').pop();
        var ogPath  = btn.getAttribute('data-og') || ('og/' + handle + '/' + skillId.split('/').pop() + '.svg');
        // Pull level/type from the rendered plaque if available
        var ns = (window._gaiaNamedBuckets && window._gaiaNamedBuckets[handle]) || [];
        var nsEntry = ns.find(function(s){ return s.id === skillId; }) || {};
        window.openHohFullscreenModal({
          id: skillId,
          contributor: handle,
          name: name,
          level: nsEntry.level || '',
          type: nsEntry.type || 'basic',
          origin: !!nsEntry.origin,
          ogPath: ogPath,
          description: nsEntry.description || '',
          tags: Array.isArray(nsEntry.tags) ? nsEntry.tags : [],
        });
      });
    }

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
  // Bootstrap guard: tree-dialog UI lives only on the homepage. On profile
  // pages, #treeDialog is absent and any treeDialog.* access below would
  // throw and silently abort the rest of this IIFE (per CLAUDE.md note on
  // skill-graph.js PR #365). Early-return keeps profile pages clean.
  if (!treeDialog) return;
  var treeNavBtn = document.getElementById('treeNavBtn');
  var treeCloseBtn = document.getElementById('treeCloseBtn');
  var treeCopyBtn = document.getElementById('treeCopyBtn');
  var treeDownloadBtn = document.getElementById('treeDownloadBtn');
  var treeDialogPre = document.getElementById('treeDialogPre');
  var treeHeader = treeDialog.querySelector('.tree-dialog-header');
  var treeDialogTitle = document.getElementById('treeDialogTitle');
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
    treeDialogTitle.textContent = 'Gaia Skill Tree';
    window._treeDownloadName = 'gaia-skill-tree.md';
    if (typeof treeDialog.showModal === 'function') treeDialog.showModal();
    else treeDialog.setAttribute('open', '');
    
    if (_treeContent === null) {
      treeDialogPre.textContent = SKELETON;
      treeDialogPre.classList.add('tree-skeleton');
      var version = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';
      var prefix = (typeof window.gaiaIconBase === 'function') ? window.gaiaIconBase().replace('assets/icons.svg', '') : '';
      fetch(prefix + 'tree.md' + version)
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
    } else {
      treeDialogPre.innerHTML = highlightTree(_treeContent);
    }
  }

  window.openDocumentDialog = function(title, url, downloadName) {
    treeDialog.style.cssText = '';
    treeDialogTitle.textContent = title;
    window._treeDownloadName = downloadName;
    if (typeof treeDialog.showModal === 'function') treeDialog.showModal();
    else treeDialog.setAttribute('open', '');
    
    treeDialogPre.textContent = 'Loading...';
    treeDialogPre.classList.add('tree-skeleton');
    
    fetch(url)
      .then(function(r) { return r.ok ? r.text() : Promise.reject(r.status); })
      .then(function(text) {
        treeDialogPre.textContent = text;
        treeDialogPre.classList.remove('tree-skeleton');
      })
      .catch(function() {
        treeDialogPre.textContent = 'Could not load document.\n(' + url + ')';
        treeDialogPre.classList.remove('tree-skeleton');
      });
  };

  function esc(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // Phase 8d — wrap a contributor span in a profile-page anchor so the
  // tree dialog renders handles as hover-underlined links. Mirrors the
  // atlas-helpers handleLink() convention used everywhere else.
  function handleAnchor(handle, inner) {
    if (!handle) return inner;
    // The tree.md text is already redacted at source (handle = "████████" for
    // pre-named/demoted skills). Render it as the slate redaction marker — never
    // an honor-red profile link.
    if (handle === (window.REDACTED_BLOCK || '████████') || handle === '[anonymous]') {
      return '<span class="plaque__redacted-handle" aria-label="Contributor not yet revealed">' + esc(handle) + '</span>';
    }
    var prefix = (typeof window.gaiaIconBase === 'function')
      ? window.gaiaIconBase().replace('assets/icons.svg', '')
      : '';
    var href = prefix + 'u/' + encodeURIComponent(handle) + '/';
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
    a.download = window._treeDownloadName || 'gaia-skill-tree.md';
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
