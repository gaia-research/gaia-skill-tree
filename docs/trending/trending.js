/**
 * trending.js — /trending/ page logic.
 *
 * Fetches /api/v1/trending/{7d,30d,ascended,contested}.json and renders:
 *   - Trending skill cards with rank badge, TM, delta, grade
 *   - Recently Ascended list
 *   - Most Contested buckets
 *
 * Gracefully handles 404 / fetch errors (Worker A data may not exist yet).
 * No jQuery, no external dependencies — vanilla JS only.
 */
(function () {
  'use strict';

  /* ── Configuration ──────────────────────────────────────────── */
  var API_BASE = '../api/v1/trending/';
  var ENDPOINTS = {
    '7d':      API_BASE + '7d.json',
    '30d':     API_BASE + '30d.json',
    ascended:  API_BASE + 'ascended.json',
    contested: API_BASE + 'contested.json',
  };

  /* ── State ──────────────────────────────────────────────────── */
  var state = {
    activeWindow: '7d',
    data: { '7d': null, '30d': null, ascended: null, contested: null },
    loaded: { '7d': false, '30d': false, ascended: false, contested: false },
    errors: { '7d': false, '30d': false, ascended: false, contested: false },
  };

  /* ── DOM references ─────────────────────────────────────────── */
  var trendingList    = document.getElementById('trending-list');
  var ascendedList    = document.getElementById('ascended-list');
  var contestedList   = document.getElementById('contested-list');
  var bootstrapBanner = document.getElementById('trending-bootstrap-banner');
  var tabs            = document.querySelectorAll('.trending-tab');

  /* ── Utilities ──────────────────────────────────────────────── */

  /**
   * Fetch JSON from a URL; resolves to {ok: true, data} or {ok: false, status}.
   */
  function fetchJSON(url) {
    return fetch(url)
      .then(function (res) {
        if (!res.ok) {
          return { ok: false, status: res.status };
        }
        return res.json().then(function (data) {
          return { ok: true, data: data };
        });
      })
      .catch(function () {
        return { ok: false, status: 0 };
      });
  }

  /** Escape HTML to prevent XSS. */
  function esc(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /**
   * Format an ISO 8601 date string as a human-readable relative or absolute
   * label, e.g. "3 days ago" or "Jun 20, 2026".
   */
  function formatDate(isoString) {
    var d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    var now = Date.now();
    var diffMs = now - d.getTime();
    var diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 30) return diffDays + ' days ago';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  /** Build a "data not available" card for sections that failed to load. */
  function unavailableCard(message) {
    var el = document.createElement('div');
    el.className = 'trending-unavailable';
    el.innerHTML =
      '<strong>Data not yet available</strong>' +
      '<span>' + esc(message || 'Check back after the next registry update.') + '</span>';
    return el;
  }

  /* ── Render: trending cards (7d / 30d) ──────────────────────── */

  function renderTrending(window) {
    trendingList.innerHTML = '';

    var result = state.data[window];
    var hasError = state.errors[window];

    if (hasError || !result) {
      trendingList.appendChild(unavailableCard(
        'Trending data for the ' + window + ' window is not yet available.'
      ));
      return;
    }

    /* Bootstrap banner */
    if (result.firstRun) {
      bootstrapBanner.removeAttribute('hidden');
    }

    var skills = result.skills || [];

    if (skills.length === 0) {
      trendingList.appendChild(unavailableCard('No trending skills found for this window.'));
      return;
    }

    /* Count line */
    var countLine = document.createElement('p');
    countLine.className = 'trending-count-line';
    countLine.textContent = skills.length + ' skill' + (skills.length !== 1 ? 's' : '') + ' trending';
    trendingList.appendChild(countLine);

    var cards = document.createElement('div');
    cards.className = 'trending-cards';

    skills.forEach(function (skill, idx) {
      var rank = idx + 1;
      var isTop3 = rank <= 3;
      var delta = typeof skill.tmDelta === 'number' ? skill.tmDelta : null;
      var deltaClass = delta === null ? 'neutral' : (delta > 0 ? 'positive' : (delta < 0 ? 'negative' : 'neutral'));
      var deltaArrow = delta > 0 ? '↑' : (delta < 0 ? '↓' : '');
      var deltaText = delta !== null
        ? (deltaArrow ? ('<span class="trending-delta-arrow">' + esc(deltaArrow) + '</span>') : '') +
          esc((delta > 0 ? '+' : '') + delta.toFixed(1))
        : '—';

      var card = document.createElement('div');
      card.className = 'trending-card';
      card.setAttribute('role', 'listitem');

      /* Rank badge */
      var rankBadge = '<div class="trending-rank' + (isTop3 ? ' top3' : '') + '" aria-label="Rank ' + rank + '">' + rank + '</div>';

      /* Body */
      var newTag = skill.new ? '<span class="trending-new-tag">New</span>' : '';
      var levelBadge = skill.level
        ? '<span class="trending-level-badge">' + esc(skill.level) + '</span>'
        : '';
      var body =
        '<div class="trending-card-body">' +
          '<div class="trending-card-name">' + esc(skill.name || skill.id) + '</div>' +
          '<div class="trending-card-meta">' +
            '<span class="trending-card-contributor">@' + esc(skill.contributor || '') + '</span>' +
            levelBadge +
            newTag +
          '</div>' +
        '</div>';

      /* Right: TM + delta + grade */
      var tm = typeof skill.trustMagnitude === 'number' ? skill.trustMagnitude.toFixed(1) : '—';
      var grade = skill.overallTrustGrade || '';
      var gradeBadge = grade
        ? '<span class="trending-grade-badge" data-grade="' + esc(grade) + '">' + esc(grade) + '</span>'
        : '';
      var right =
        '<div class="trending-card-right">' +
          '<span class="trending-tm">' + esc(tm) + '</span>' +
          '<span class="trending-delta ' + deltaClass + '">' + deltaText + '</span>' +
          gradeBadge +
        '</div>';

      card.innerHTML = rankBadge + body + right;
      cards.appendChild(card);
    });

    trendingList.appendChild(cards);
  }

  /* ── Render: recently ascended ──────────────────────────────── */

  function renderAscended() {
    ascendedList.innerHTML = '';

    var result = state.data.ascended;
    var hasError = state.errors.ascended;

    if (hasError || !result) {
      ascendedList.appendChild(unavailableCard('Ascension data is not yet available.'));
      return;
    }

    var skills = result.skills || [];

    if (skills.length === 0) {
      ascendedList.appendChild(unavailableCard('No recently ascended skills.'));
      return;
    }

    var list = document.createElement('div');
    list.className = 'ascended-list';

    skills.forEach(function (skill) {
      var card = document.createElement('div');
      card.className = 'ascended-card';
      card.setAttribute('role', 'listitem');

      /* Gold accent when skill has a level badge (it ascended to something visible) */
      var levelDisplay = '';
      if (skill.previousLevel && skill.level) {
        /* Show previous → current level transition */
        levelDisplay =
          '<span class="ascended-level-transition">' +
            '<span class="ascended-prev-level">' + esc(skill.previousLevel) + '</span>' +
            '<span class="ascended-transition-arrow" aria-hidden="true">→</span>' +
            '<span class="trending-level-badge ascended-cur-level">' + esc(skill.level) + '</span>' +
          '</span>';
      } else if (skill.level) {
        levelDisplay = '<span class="trending-level-badge">' + esc(skill.level) + '</span>';
      }

      var gradeBadge = skill.overallTrustGrade
        ? '<span class="trending-grade-badge" data-grade="' + esc(skill.overallTrustGrade) + '">' + esc(skill.overallTrustGrade) + '</span>'
        : '';
      var dateStr = skill.ascendedAt ? formatDate(skill.ascendedAt) : '';

      /* Gold accent for ascended cards */
      card.classList.add('ascended-card--gold');

      card.innerHTML =
        '<div class="ascended-card-left">' +
          '<div class="ascended-card-name">' + esc(skill.name || skill.id) + '</div>' +
          '<div class="ascended-card-contributor">@' + esc(skill.contributor || '') + '</div>' +
        '</div>' +
        '<div class="ascended-card-right">' +
          levelDisplay +
          gradeBadge +
          (dateStr ? '<span class="ascended-date">' + esc(dateStr) + '</span>' : '') +
        '</div>';

      list.appendChild(card);
    });

    ascendedList.appendChild(list);
  }

  /* ── Render: most contested ─────────────────────────────────── */

  function renderContested() {
    contestedList.innerHTML = '';

    var result = state.data.contested;
    var hasError = state.errors.contested;

    if (hasError || !result) {
      contestedList.appendChild(unavailableCard('Contested skills data is not yet available.'));
      return;
    }

    var buckets = result.buckets || [];

    if (buckets.length === 0) {
      contestedList.appendChild(unavailableCard('No contested skill buckets found.'));
      return;
    }

    var list = document.createElement('div');
    list.className = 'contested-list';

    buckets.forEach(function (bucket) {
      var bucketEl = document.createElement('div');
      bucketEl.className = 'contested-bucket';

      var impls = bucket.implementations || (bucket.skills || []).length;
      var countBadge = '<span class="contested-count-badge">' + impls + ' impl' + (impls !== 1 ? 's' : '') + '</span>';

      var chips = (bucket.skills || []).map(function (s) {
        var gradeBadge = s.overallTrustGrade
          ? '<span class="trending-grade-badge" data-grade="' + esc(s.overallTrustGrade) + '">' + esc(s.overallTrustGrade) + '</span>'
          : '';
        var tm = typeof s.trustMagnitude === 'number'
          ? '<span class="contested-chip-tm">' + s.trustMagnitude.toFixed(1) + '</span>'
          : '';
        /* Origin highlight: highest TM implementation in the bucket */
        var originTag = s.origin
          ? '<span class="contested-chip-origin" aria-label="Origin implementation">origin</span>'
          : '';
        var chipClass = 'contested-chip' + (s.origin ? ' contested-chip--origin' : '');
        return '<span class="' + chipClass + '">' +
          '<span class="contested-chip-id">' + esc(s.id) + '</span>' +
          tm +
          gradeBadge +
          originTag +
          '</span>';
      }).join('');

      /* Show generic skill node name prominently in header */
      bucketEl.innerHTML =
        '<div class="contested-bucket-header">' +
          '<span class="contested-bucket-name">' + esc(bucket.genericSkillRef || '') + '</span>' +
          countBadge +
        '</div>' +
        '<div class="contested-chips">' + chips + '</div>';

      list.appendChild(bucketEl);
    });

    contestedList.appendChild(list);
  }

  /* ── Tab switching ──────────────────────────────────────────── */

  function activateTab(win) {
    state.activeWindow = win;
    tabs.forEach(function (tab) {
      var isActive = tab.dataset.window === win;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    renderTrending(win);
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      activateTab(tab.dataset.window);
    });
  });

  /* ── Fetch all endpoints in parallel ───────────────────────── */

  var fetches = Object.keys(ENDPOINTS).map(function (key) {
    return fetchJSON(ENDPOINTS[key]).then(function (result) {
      state.loaded[key] = true;
      if (result.ok) {
        state.data[key] = result.data;
        state.errors[key] = false;
      } else {
        state.data[key] = null;
        state.errors[key] = true;
      }
    });
  });

  /* Render sections progressively as each fetch completes. */
  fetchJSON(ENDPOINTS['7d']).then(function (result) {
    state.loaded['7d'] = true;
    state.data['7d'] = result.ok ? result.data : null;
    state.errors['7d'] = !result.ok;
    renderTrending('7d');
  });

  fetchJSON(ENDPOINTS['30d']).then(function (result) {
    state.loaded['30d'] = true;
    state.data['30d'] = result.ok ? result.data : null;
    state.errors['30d'] = !result.ok;
    /* Only re-render if 30d is currently active (user already clicked) */
    if (state.activeWindow === '30d') {
      renderTrending('30d');
    }
  });

  fetchJSON(ENDPOINTS.ascended).then(function (result) {
    state.loaded.ascended = true;
    state.data.ascended = result.ok ? result.data : null;
    state.errors.ascended = !result.ok;
    renderAscended();
  });

  fetchJSON(ENDPOINTS.contested).then(function (result) {
    state.loaded.contested = true;
    state.data.contested = result.ok ? result.data : null;
    state.errors.contested = !result.ok;
    renderContested();
  });

  /* Suppress unused-variable lint on `fetches` — it's kept for reference. */
  void fetches;

})();
