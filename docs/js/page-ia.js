(function () {
  var GRAPH_URL = 'graph/gaia.json';
  var NAMED_URL = 'graph/named/index.json';

  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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

  function openExplorer(id) {
    if (typeof window.openSkillExplorer === 'function') window.openSkillExplorer(id);
  }

  Promise.all([
    fetch(GRAPH_URL).then(function (r) { return r.ok ? r.json() : Promise.reject(); }),
    fetch(NAMED_URL).then(function (r) { return r.ok ? r.json() : Promise.reject(); }),
  ]).then(function (results) {
    var graphData = results[0];
    var namedData = results[1];
    var skills = graphData.skills || [];
    var buckets = namedData.buckets || {};

    // Build set of skill IDs that have a named implementation
    var namedRefs = new Set();
    Object.keys(buckets).forEach(function (skillId) {
      (buckets[skillId] || []).forEach(function (e) {
        namedRefs.add(e.genericSkillRef || skillId);
      });
    });

    var ultimates = skills.filter(function (s) { return s.type === 'ultimate'; });
    var unclaimed = ultimates.filter(function (u) { return !namedRefs.has(u.id); });
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

    // Path B — unclaimed ultimates
    var list = document.getElementById('ultimatesList');
    if (list) {
      if (unclaimed.length) {
        list.innerHTML = unclaimed.map(function (u) {
          var name = u.name || u.id.replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
          var cmd = 'gaia propose /' + u.id;
          var safCmd = cmd.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
          return '<div class="ultimate-item">' +
            '<span class="ult-glyph">◆</span>' +
            '<span class="ult-name">' + esc(name) + '</span>' +
            '<span class="ult-level">' + esc(u.level || '') + '</span>' +
            '<button class="ult-claim" title="Copy claim command" onclick="(function(c){navigator.clipboard&&navigator.clipboard.writeText(c).then(function(){var b=event.target;var t=b.textContent;b.textContent=\'Copied!\';setTimeout(function(){b.textContent=t;},1400);})})(\''+safCmd+'\')">' +
            'Claim →</button>' +
            '</div>';
        }).join('');
      } else {
        list.innerHTML = '<p style="color:var(--muted);font-size:.9rem">All Ultimates currently claimed. ' +
          '<a href="https://github.com/mbtiongson1/gaia-skill-tree/issues" target="_blank" style="color:var(--basic)">Propose a new one →</a></p>';
      }
    }

    // Hall of Heroes — top 5 origin named skills by level
    var allOrigin = [];
    Object.keys(buckets).forEach(function (skillId) {
      (buckets[skillId] || []).forEach(function (e) {
        if (e.origin) allOrigin.push(Object.assign({ _skillId: skillId }, e));
      });
    });
    allOrigin.sort(function (a, b) { return levelNum(b.level) - levelNum(a.level); });

    // Named count for ledger
    var elNamed = document.getElementById('ledgerNamed');
    if (elNamed) elNamed.textContent = allOrigin.length;

    var top5 = allOrigin.slice(0, 5);
    var plates = document.getElementById('hohPlates');
    if (plates && top5.length) {
      plates.innerHTML = top5.map(function (e) {
        var n = levelNum(e.level);
        var glyph = n >= 6 ? '◆' : n >= 4 ? '◇' : '○';
        var glyphColor = n >= 6 ? 'var(--apex-gold)' : n >= 4 ? 'var(--extra)' : 'var(--basic)';
        var safeId = e.id.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        var safeContrib = (e.contributor || '').replace(/"/g, '&quot;');
        var profileHref = './u/' + encodeURIComponent(e.contributor || '') + '/';
        return '<a href="' + profileHref + '" class="hoh-plate-link" aria-label="View profile of ' + safeContrib + '">' +
          '<article class="hoh-plate" role="button" tabindex="0"' +
          ' data-skill-id="' + safeId + '"' +
          ' onclick="(function(evt){evt.preventDefault();if(typeof openSkillExplorer===\'function\')openSkillExplorer(\'' + safeId + '\');})(event)"' +
          ' onkeydown="if(event.key===\'Enter\'||event.key===\' \')this.click()">' +
          '<div class="hoh-plate-glyph" style="color:' + glyphColor + '">' + glyph + '</div>' +
          '<div class="hoh-handle">' + esc(e.contributor || '') + '</div>' +
          '<div class="hoh-title">' + esc(e.title || e.name || e._skillId) + '</div>' +
          '<div class="hoh-level">' + esc(e.level || '') + '</div>' +
          '</article>' +
          '</a>';
      }).join('');
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
  });
})();
