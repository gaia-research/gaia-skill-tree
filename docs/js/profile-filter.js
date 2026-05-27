(function() {
  'use strict';

  // Active filter state
  const state = {
    search: '',
    types: new Set(),
    ranks: new Set(),
    preset: 'all', // '30d', '6m', 'all'
    minDate: '',
    maxDate: '',
    sort: 'rank'
  };

  let plaquesGrid = null;
  let timelineContainer = null;

  function init() {
    plaquesGrid = document.querySelector('.plaque-grid');
    timelineContainer = document.getElementById('profile-timeline');

    // Bind Search Input
    const searchInput = document.getElementById('profileSearch');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        state.search = e.target.value.toLowerCase().trim();
        applyFilters();
      });
    }

    // Bind Type & Rank Chips
    const filterGroups = document.querySelectorAll('.profile-filter-group');
    filterGroups.forEach(group => {
      const filterType = group.getAttribute('data-filter-type');
      const chips = group.querySelectorAll('.profile-filter-chip');

      chips.forEach(chip => {
        chip.addEventListener('click', () => {
          const val = chip.getAttribute('data-value');
          const isPressed = chip.getAttribute('aria-pressed') === 'true';

          if (isPressed) {
            chip.setAttribute('aria-pressed', 'false');
            if (filterType === 'type') state.types.delete(val);
            if (filterType === 'rank') state.ranks.delete(val);
          } else {
            chip.setAttribute('aria-pressed', 'true');
            if (filterType === 'type') state.types.add(val);
            if (filterType === 'rank') state.ranks.add(val);
          }
          applyFilters();
        });
      });
    });

    // Bind Date Manual Inputs
    const dateMinInput = document.getElementById('profileDateMin');
    const dateMaxInput = document.getElementById('profileDateMax');

    function handleManualDateChange() {
      state.minDate = dateMinInput ? dateMinInput.value : '';
      state.maxDate = dateMaxInput ? dateMaxInput.value : '';
      
      // Clear preset selection visually
      const presets = document.querySelectorAll('.date-presets .profile-filter-chip');
      presets.forEach(p => {
        p.setAttribute('aria-pressed', 'false');
      });
      state.preset = null;

      applyFilters();
    }

    if (dateMinInput) dateMinInput.addEventListener('change', handleManualDateChange);
    if (dateMaxInput) dateMaxInput.addEventListener('change', handleManualDateChange);

    // Bind Date Preset Chips
    const presetChips = document.querySelectorAll('.date-presets .profile-filter-chip');
    presetChips.forEach(chip => {
      chip.addEventListener('click', () => {
        // Toggle active pressed state
        presetChips.forEach(c => c.setAttribute('aria-pressed', 'false'));
        chip.setAttribute('aria-pressed', 'true');

        const preset = chip.getAttribute('data-preset');
        state.preset = preset;

        // Synchronize manual inputs based on preset
        const now = new Date();
        if (preset === '30d') {
          const d = new Date();
          d.setDate(d.getDate() - 30);
          state.minDate = d.toISOString().split('T')[0];
          state.maxDate = now.toISOString().split('T')[0];
        } else if (preset === '6m') {
          const d = new Date();
          d.setMonth(d.getMonth() - 6);
          state.minDate = d.toISOString().split('T')[0];
          state.maxDate = now.toISOString().split('T')[0];
        } else {
          // All time
          state.minDate = '';
          state.maxDate = '';
        }

        if (dateMinInput) dateMinInput.value = state.minDate;
        if (dateMaxInput) dateMaxInput.value = state.maxDate;

        applyFilters();
      });
    });

    // Bind Sort Order Selector
    const sortSel = document.getElementById('profileSort');
    if (sortSel) {
      sortSel.addEventListener('change', () => {
        state.sort = sortSel.value;
        sortArticles();
      });
    }

    // Bind Reset Affiliate
    const resetBtn = document.querySelector('.profile-filter-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        state.search = '';
        state.types.clear();
        state.ranks.clear();
        state.preset = 'all';
        state.minDate = '';
        state.maxDate = '';
        state.sort = 'rank';

        // Reset Inputs & Chips DOM
        if (searchInput) searchInput.value = '';
        
        const chips = document.querySelectorAll('.profile-filter-chip');
        chips.forEach(c => {
          const parentGroup = c.closest('.profile-filter-group');
          if (parentGroup) {
            c.setAttribute('aria-pressed', 'false');
          }
        });

        presetChips.forEach(c => {
          if (c.getAttribute('data-preset') === 'all') {
            c.setAttribute('aria-pressed', 'true');
          } else {
            c.setAttribute('aria-pressed', 'false');
          }
        });

        if (dateMinInput) dateMinInput.value = '';
        if (dateMaxInput) dateMaxInput.value = '';
        if (sortSel) sortSel.value = 'rank';

        applyFilters();
      });
    }

    // Bind Sliding Filter Panel Toggles (Desktop & Mobile buttons)
    const sidebar = document.getElementById('profileSidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    const desktopToggle = document.getElementById('desktopFilterToggle');
    const mobileToggle = document.getElementById('mobileFilterToggle');

    function toggleSidebar() {
      if (sidebar) sidebar.classList.toggle('is-open');
      if (backdrop) backdrop.classList.toggle('is-open');
    }

    function closeSidebar() {
      if (sidebar) sidebar.classList.remove('is-open');
      if (backdrop) backdrop.classList.remove('is-open');
    }

    if (desktopToggle) desktopToggle.addEventListener('click', toggleSidebar);
    if (mobileToggle) mobileToggle.addEventListener('click', toggleSidebar);
    if (backdrop) backdrop.addEventListener('click', closeSidebar);

    // Initial Filter Run
    applyFilters();
  }

  function applyFilters() {
    if (!plaquesGrid) return;

    const articles = plaquesGrid.querySelectorAll('article.plaque');
    const matchingSkillIds = new Set();

    // ── 1. Filter Plaques Grid ──
    articles.forEach(article => {
      const skillId = article.getAttribute('data-skill-id') || '';
      const skillName = (article.getAttribute('data-skill-name') || '').toLowerCase();
      const type = article.getAttribute('data-type') || 'basic';
      const level = parseInt(article.getAttribute('data-level') || '0', 10);
      const desc = (article.querySelector('.plaque__desc') ? article.querySelector('.plaque__desc').textContent : '').toLowerCase();
      const tags = (article.getAttribute('data-tags') || '').toLowerCase();

      // Text query match (ID, name, description, tags)
      const textMatch = !state.search || 
        skillId.toLowerCase().includes(state.search) || 
        skillName.includes(state.search) || 
        desc.includes(state.search) || 
        tags.includes(state.search);

      // Type match
      const typeMatch = state.types.size === 0 || state.types.has(type);

      // Rank match
      const rankMatch = state.ranks.size === 0 || state.ranks.has(String(level));

      if (textMatch && typeMatch && rankMatch) {
        article.removeAttribute('hidden');
        matchingSkillIds.add(skillId);
      } else {
        article.setAttribute('hidden', '');
      }
    });

    // ── 2. Filter & Re-render timeline ──
    if (timelineContainer && window.PROFILE_TIMELINE) {
      window.renderProfileTimeline(timelineContainer, window.PROFILE_TIMELINE, {
        activeSkills: matchingSkillIds,
        minDate: state.minDate,
        maxDate: state.maxDate
      });
    }

    sortArticles();
    announceFilterStatus();

    // Show inline empty state when every plaque is hidden
    let emptyState = plaquesGrid.querySelector('.profile-empty-state');
    if (!emptyState) {
      emptyState = document.createElement('p');
      emptyState.className = 'profile-empty-state';
      emptyState.innerHTML = 'No skills match these filters. <button type="button" class="profile-empty-reset">Reset</button>';
      emptyState.querySelector('.profile-empty-reset').addEventListener('click', function() {
        const mainReset = document.querySelector('.profile-sidebar .profile-filter-reset');
        if (mainReset) mainReset.click();
      });
      plaquesGrid.after(emptyState);
    }
    emptyState.style.display = matchingSkillIds.size === 0 ? 'block' : 'none';
  }

  function sortArticles() {
    if (!plaquesGrid) return;

    const articles = Array.from(plaquesGrid.querySelectorAll('article.plaque'));

    articles.sort((a, b) => {
      if (state.sort === 'rank') {
        const levelA = parseInt(a.getAttribute('data-level') || '0', 10);
        const levelB = parseInt(b.getAttribute('data-level') || '0', 10);
        return levelB - levelA;
      } else if (state.sort === 'alpha') {
        const nameA = (a.getAttribute('data-skill-name') || a.getAttribute('data-skill-id') || '').toLowerCase();
        const nameB = (b.getAttribute('data-skill-name') || b.getAttribute('data-skill-id') || '').toLowerCase();
        return nameA.localeCompare(nameB);
      } else if (state.sort === 'type') {
        const typeOrder = { ultimate: 0, unique: 1, extra: 2, basic: 3 };
        const typeA = typeOrder[a.getAttribute('data-type')] || 999;
        const typeB = typeOrder[b.getAttribute('data-type')] || 999;
        if (typeA !== typeB) return typeA - typeB;

        const levelA = parseInt(a.getAttribute('data-level') || '0', 10);
        const levelB = parseInt(b.getAttribute('data-level') || '0', 10);
        return levelB - levelA;
      }
      return 0;
    });

    const fragment = document.createDocumentFragment();
    articles.forEach(article => {
      fragment.appendChild(article);
    });
    plaquesGrid.appendChild(fragment);
  }

  function announceFilterStatus() {
    let region = document.querySelector('[data-filter-announce]');
    if (!region) {
      region = document.createElement('div');
      region.setAttribute('aria-live', 'polite');
      region.setAttribute('aria-atomic', 'true');
      region.setAttribute('data-filter-announce', '');
      region.style.position = 'absolute';
      region.style.left = '-9999px';
      document.body.appendChild(region);
    }
    const visible = Array.from(plaquesGrid.querySelectorAll('article.plaque')).filter(a => !a.hasAttribute('hidden')).length;
    const total = plaquesGrid.querySelectorAll('article.plaque').length;
    region.textContent = `Showing ${visible} of ${total} skills.`;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
