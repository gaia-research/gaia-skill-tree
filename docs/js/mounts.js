/**
 * mounts.js — single source of truth for URL-segment depth detection.
 *
 * When you add a new top-level docs/ subdirectory that uses site-nav or
 * site-footer, add its name here. Both scripts read window.GAIA_MOUNTS at
 * runtime so they only need to be updated in one place.
 *
 * Must be loaded BEFORE site-nav.js and site-footer.js on every page.
 */
window.GAIA_MOUNTS = [
  'named', 'en', 'badges', 'u', 'samples', 'graph',
  'evidence', 'share', 'trust', 'api', 'codex', 'trending', 'heroes',
];
