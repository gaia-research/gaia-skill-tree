(function() {
  'use strict';

  const FILTER_TYPES = {
    type: new Set(),
    rank: new Set()
  };

  let currentSort = 'rank';
  let currentGrid = null;

  function ensureLiveRegion() {
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
    return region;
  }

  function getVisibleCount() {
    if (!currentGrid) return 0;
    const articles = currentGrid.querySelectorAll('article');
    return Array.from(articles).filter(a => !a.hasAttribute('hidden')).length;
  }

  function getTotalCount() {
    if (!currentGrid) return 0;
    return currentGrid.querySelectorAll('article').length;
  }

  function applyFilters() {
    if (!currentGrid) return;

    const articles = currentGrid.querySelectorAll('article');
    articles.forEach(article => {
      const level = parseInt(article.getAttribute('data-level') || '0', 10);
      const type = article.getAttribute('data-type');

      const typeFilterActive = FILTER_TYPES.type.size > 0;
      const rankFilterActive = FILTER_TYPES.rank.size > 0;

      const typeMatch = !typeFilterActive || FILTER_TYPES.type.has(type);
      const rankMatch = !rankFilterActive || FILTER_TYPES.rank.has(String(level));

      if (typeMatch && rankMatch) {
        article.removeAttribute('hidden');
      } else {
        article.setAttribute('hidden', '');
      }
    });

    announceFilterStatus();
    sortArticles();
  }

  function announceFilterStatus() {
    const visible = getVisibleCount();
    const total = getTotalCount();
    const region = ensureLiveRegion();
    region.textContent = `Showing ${visible} of ${total} skills.`;
  }

  function sortArticles() {
    if (!currentGrid) return;

    const articles = Array.from(currentGrid.querySelectorAll('article'));
    const visible = articles.filter(a => !a.hasAttribute('hidden'));

    visible.sort((a, b) => {
      if (currentSort === 'rank') {
        const levelA = parseInt(a.getAttribute('data-level') || '0', 10);
        const levelB = parseInt(b.getAttribute('data-level') || '0', 10);
        return levelB - levelA;
      } else if (currentSort === 'alpha') {
        const nameA = (a.getAttribute('data-skill-name') || a.getAttribute('data-skill-id') || '').toLowerCase();
        const nameB = (b.getAttribute('data-skill-name') || b.getAttribute('data-skill-id') || '').toLowerCase();
        return nameA.localeCompare(nameB);
      } else if (currentSort === 'type') {
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
    visible.forEach(article => {
      fragment.appendChild(article);
    });
    currentGrid.appendChild(fragment);
  }

  function initBar(bar) {
    const grid = findFollowingGrid(bar);
    if (!grid) return;

    currentGrid = grid;

    const filterGroups = bar.querySelectorAll('.profile-filter-group');
    filterGroups.forEach(group => {
      const filterType = group.getAttribute('data-filter-type');
      const chips = group.querySelectorAll('.profile-filter-chip');

      chips.forEach(chip => {
        chip.addEventListener('click', () => {
          handleFilterChipClick(chip, filterType);
        });
      });
    });

    const sortSel = bar.querySelector('#profileSort');
    if (sortSel) {
      sortSel.addEventListener('change', () => {
        currentSort = sortSel.value;
        sortArticles();
        announceFilterStatus();
      });
    }

    const resetBtn = bar.querySelector('.profile-filter-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        FILTER_TYPES.type.clear();
        FILTER_TYPES.rank.clear();
        currentSort = 'rank';

        filterGroups.forEach(group => {
          const chips = group.querySelectorAll('.profile-filter-chip');
          chips.forEach(chip => {
            chip.setAttribute('aria-pressed', 'false');
          });
        });

        if (sortSel) sortSel.value = 'rank';

        const articles = grid.querySelectorAll('article');
        articles.forEach(a => a.removeAttribute('hidden'));

        currentGrid = grid;
        announceFilterStatus();
        sortArticles();
      });
    }
  }

  function handleFilterChipClick(chip, filterType) {
    const value = chip.getAttribute('data-value');
    const isPressed = chip.getAttribute('aria-pressed') === 'true';

    if (isPressed) {
      chip.setAttribute('aria-pressed', 'false');
      FILTER_TYPES[filterType].delete(value);
    } else {
      chip.setAttribute('aria-pressed', 'true');
      FILTER_TYPES[filterType].add(value);
    }

    applyFilters();
  }

  function findFollowingGrid(bar) {
    let current = bar.nextElementSibling;
    while (current) {
      if (current.classList.contains('plaque-grid')) {
        return current;
      }
      current = current.nextElementSibling;
    }

    const parent = bar.parentElement;
    if (parent) {
      return parent.querySelector('.plaque-grid');
    }

    return null;
  }

  document.addEventListener('DOMContentLoaded', () => {
    const bars = document.querySelectorAll('.profile-filter-bar');
    bars.forEach(bar => {
      initBar(bar);
    });
  });
})();
