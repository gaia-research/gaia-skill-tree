/**
 * Gaia Benchmark Leaderboard — shared renderer
 *
 * Reads data-benchmark="<slug>" from #lb-content (or falls back to the slug
 * inferred from the URL path) and fetches:
 *   <root>/api/v1/benchmarks/<slug>.json
 *
 * Renders three sections:
 *   1. Verified  — provenance/lane verified (or legacy ci-reproduced/verifier-attested), 2.0x TM lane
 *   2. Reported  — provenance/lane reported (or legacy mirrored), 1.0x TM lane
 *   3. Rejected  — rejected/pending/candidate/unknown rows, 0x TM lane
 *
 * Aesthetic: mirrors scripts/leaderboard.html (grade-banded tables, sortable,
 * mono font, --grade-* tokens).  No new design — Sprint F rewrites this.
 */
(function () {
  'use strict';

  /* ── Helpers ─────────────────────────────────────────────────── */

  function getRootPath() {
    // The site is served from its root on localhost (python -m http.server)
    // and on GitHub Pages (custom domain gaiaskilltree.com), so an absolute
    // path reaches the API regardless of page depth. This avoids the
    // depth-miscount that fetched /benchmarks/api/... instead of /api/...
    if (window.location.protocol !== 'file:') return '/';
    // file:// fallback: walk up to the docs root by counting the segments
    // from the first known mount to the page (…/benchmarks/<slug>/index.html).
    var parts = window.location.pathname.replace(/\/[^/]*$/, '').replace(/\/+$/, '').split('/');
    var mounts = (window.GAIA_MOUNTS || []);
    for (var i = parts.length - 1; i >= 0; i--) {
      if (mounts.indexOf(parts[i]) !== -1) {
        var rel = '';
        for (var j = 0; j < parts.length - i; j++) rel += '../';
        return rel;
      }
    }
    return '../../'; // safe default for /benchmarks/<slug>/
  }

  function scoreColor(score, unit) {
    if (score === null || score === undefined) return '#64748b';
    var pct = unit === 'pct' ? score : score * 100;
    if (pct >= 85) return 'var(--grade-S, #e2d5f8)';
    if (pct >= 70) return 'var(--grade-A, #fbbf24)';
    if (pct >= 50) return 'var(--grade-B, #94a3b8)';
    return 'var(--grade-C, #b87333)';
  }

  function scoreGrade(score, unit) {
    if (score === null || score === undefined) return 'u';
    var pct = unit === 'pct' ? score : score * 100;
    if (pct >= 85) return 'S';
    if (pct >= 70) return 'A';
    if (pct >= 50) return 'B';
    return 'C';
  }

  function fmtScore(score, unit) {
    if (score === null || score === undefined) return '—';
    if (unit === 'pct') return score.toFixed(1) + '%';
    if (unit === 'pass@1') return (score * 100).toFixed(1) + '% pass@1';
    return String(score);
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    try { return iso.slice(0, 10); } catch (e) { return iso; }
  }

  function skillLink(skillId, root) {
    if (!skillId) return '—';
    var parts = skillId.split('/');
    if (parts.length !== 2) return esc(skillId);
    var url = root + 'named/' + parts[0] + '/' + parts[1] + '.html';
    return '<a href="' + url + '">' + esc(skillId) + '</a>';
  }

  function attestorLink(url) {
    if (!url) return '—';
    var label = url.replace(/^https?:\/\//, '').slice(0, 48);
    return '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + label + '</a>';
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ── Table builder ────────────────────────────────────────────── */

  function buildTable(rows, unit, root, showRank) {
    if (!rows || !rows.length) return '<p class="lb-empty">No entries.</p>';

    var html = '<div class="lb-table-wrap"><table><thead><tr>';
    if (showRank) html += '<th class="lb-rank">Rank</th>';
    html += '<th>Skill</th><th>Score</th><th>Model</th><th>Run</th><th>Attestor</th>';
    html += '</tr></thead><tbody>';

    rows.forEach(function (row, idx) {
      var grade = scoreGrade(row.score, unit);
      html += '<tr>';
      if (showRank) html += '<td class="lb-rank lb-mono">' + (idx + 1) + '</td>';
      html += '<td class="lb-skill">' + skillLink(row.skillId, root) + '</td>';
      html += '<td class="lb-score lb-mono" style="color:' + scoreColor(row.score, unit) + '">';
      html += '<span class="lb-badge lb-badge-' + grade + '">' + grade + '</span> ';
      html += esc(fmtScore(row.score, unit)) + '</td>';
      html += '<td class="lb-mono lb-dim">' + esc(row.modelRef || '—') + '</td>';
      html += '<td class="lb-mono lb-dim">' + esc(fmtDate(row.runAt)) + '</td>';
      html += '<td class="lb-attns">' + attestorLink(row.attestor) + '</td>';
      html += '</tr>';
    });

    html += '</tbody></table></div>';
    return html;
  }

  /* ── Section builder ──────────────────────────────────────────── */

  function buildSection(title, badge, rows, unit, root, opts) {
    opts = opts || {};
    var dimClass = opts.dim ? ' lb-section-dim' : '';
    var noteHtml = opts.note ? '<p class="lb-note">' + opts.note + '</p>' : '';

    var html = '<section class="lb-section' + dimClass + '">';
    html += '<h2 class="lb-section-title">';
    html += esc(title);
    if (badge) html += ' <span class="lb-badge lb-badge-prov lb-badge-' + badge.cls + '">' + esc(badge.text) + '</span>';
    html += ' <span class="lb-count">' + rows.length + '</span>';
    html += '</h2>';
    if (noteHtml) html += noteHtml;
    html += buildTable(rows, unit, root, !opts.noRank);
    html += '</section>';
    return html;
  }

  /* ── Search + sort ─────────────────────────────────────────────── */

  var _allRows = [];
  var _unit = '';
  var _root = '';
  var _benchmarkId = '';
  var _searchEl = null;
  var _mount = null;

  function filterRows(rows, query) {
    if (!query) return rows;
    var q = query.toLowerCase();
    return rows.filter(function (r) {
      return (r.skillId || '').toLowerCase().indexOf(q) !== -1 ||
        (r.modelRef || '').toLowerCase().indexOf(q) !== -1;
    });
  }

  function laneOf(row) {
    var p = String(row.provenance || '').toLowerCase();
    if (p === 'verified' || p === 'ci-reproduced' || p === 'verifier-attested') return 'verified';
    if (p === 'reported' || p === 'mirrored') return 'reported';
    return 'rejected';
  }

  function render(rows, query) {
    var filtered = filterRows(rows, query);
    var verified = filtered.filter(function (r) { return laneOf(r) === 'verified'; });
    var reported = filtered.filter(function (r) { return laneOf(r) === 'reported'; });
    var rejected = filtered.filter(function (r) { return laneOf(r) === 'rejected'; });

    // Lanes are row-level: a benchmark page shows whichever of Verified,
    // Reported, and Rejected its own rows populate. No benchmark carries a
    // single global lane.
    var html = '';

    if (verified.length) {
      html += buildSection('Verified', { text: 'Verified · 2× TM lane', cls: 'verified' }, verified, _unit, _root);
    }
    if (reported.length) {
      html += buildSection(
        'Reported',
        { text: 'Reported · 1× TM lane', cls: 'cited' },
        reported, _unit, _root,
        { note: 'Reported rows are public claims or mirrored benchmark evidence accepted by the human gate. They count at the reported 1.0× lane and do not imply Gaia CI/verifier reproduction.' }
      );
    }
    if (rejected.length) {
      html += buildSection(
        'Rejected / no score',
        { text: '0× TM lane', cls: 'pending' },
        rejected, _unit, _root,
        {
          dim: true,
          noRank: true,
          note: 'Rejected, pending, unknown, candidate, and catalog-blacklisted rows score zero. They remain visible as audit history.'
        }
      );
    }

    if (!html) html = '<p class="lb-empty">No entries match your search.</p>';
    _mount.innerHTML = html;
  }

  function onSearch() {
    render(_allRows, _searchEl ? _searchEl.value : '');
  }

  /* ── Init ─────────────────────────────────────────────────────── */

  function init() {
    _mount = document.getElementById('lb-content');
    if (!_mount) return;

    var slug = _mount.getAttribute('data-benchmark');
    if (!slug) {
      // Infer from URL path: /benchmarks/<slug>/
      var m = window.location.pathname.match(/\/benchmarks\/([^/]+)\//);
      slug = m ? m[1] : '';
    }
    if (!slug) { _mount.innerHTML = '<p class="lb-empty">Could not determine benchmark slug.</p>'; return; }

    _root = getRootPath();
    var apiUrl = _root + 'api/v1/benchmarks/' + slug + '.json';

    _mount.innerHTML = '<p class="lb-loading">Loading leaderboard\u2026</p>';

    _searchEl = document.getElementById('lb-search');
    if (_searchEl) _searchEl.addEventListener('input', onSearch);

    fetch(apiUrl)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        _allRows = data.rows || [];
        _unit = data.unit || '';
        _benchmarkId = data.benchmarkId || slug;

        // Update meta elements if present
        var metaEl = document.getElementById('lb-meta');
        if (metaEl) {
          var total = _allRows.length;
          metaEl.textContent = total + ' entr' + (total === 1 ? 'y' : 'ies') + ' \u00b7 benchmarkId: ' + _benchmarkId + ' \u00b7 unit: ' + _unit;
        }

        render(_allRows, _searchEl ? _searchEl.value : '');
      })
      .catch(function (err) {
        _mount.innerHTML = '<p class="lb-empty">Failed to load leaderboard data: ' + esc(String(err)) + '</p>';
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
