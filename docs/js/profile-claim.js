(function() {
  'use strict';

  function ensureAnnounceRegion() {
    let region = document.querySelector('[data-claim-announce]');
    if (!region) {
      region = document.createElement('div');
      region.setAttribute('aria-live', 'polite');
      region.setAttribute('aria-atomic', 'true');
      region.setAttribute('data-claim-announce', '');
      region.style.position = 'absolute';
      region.style.left = '-9999px';
      document.body.appendChild(region);
    }
    return region;
  }

  function getSkillIdFromArticle(btn) {
    let current = btn.parentElement;
    while (current) {
      if (current.hasAttribute('data-skill-id')) {
        return current.getAttribute('data-skill-id');
      }
      current = current.parentElement;
    }
    return null;
  }

  function restoreClaimState(btn) {
    const skillId = getSkillIdFromArticle(btn);
    if (!skillId) return;

    const key = `plaque-claim-${skillId}`;
    const stored = sessionStorage.getItem(key);
    if (stored === 'claimed') {
      btn.setAttribute('data-claim', 'claimed');
      updateButtonText(btn);
    }
  }

  function updateButtonText(btn) {
    const isClaimed = btn.getAttribute('data-claim') === 'claimed';
    btn.textContent = isClaimed ? '✓ Claimed' : 'Add to README';
  }

  function handleClaimClick(e) {
    e.stopPropagation();

    const btn = e.currentTarget;
    const isClaimed = btn.getAttribute('data-claim') === 'claimed';
    const newState = isClaimed ? 'unclaimed' : 'claimed';

    btn.setAttribute('data-claim', newState);
    updateButtonText(btn);

    const skillId = getSkillIdFromArticle(btn);
    if (skillId) {
      const key = `plaque-claim-${skillId}`;
      if (newState === 'claimed') {
        sessionStorage.setItem(key, 'claimed');
      } else {
        sessionStorage.removeItem(key);
      }
    }

    const region = ensureAnnounceRegion();
    region.textContent = 'Badge claim coming soon — your selection is saved locally.';
  }

  document.addEventListener('DOMContentLoaded', () => {
    const claimBtns = document.querySelectorAll('.plaque__claim-btn');
    claimBtns.forEach(btn => {
      restoreClaimState(btn);
      updateButtonText(btn);
      btn.addEventListener('click', handleClaimClick);
    });
  });
})();
