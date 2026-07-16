/* Gaia skill-semantics — shared client branch resolver (Yggdrasil II).
 *
 * SINGLE SOURCE OF TRUTH for read-time branch derivation on the client.
 * Mirrors docs/js/world-tree-layout.js resolveSemantics() (L356-413) so every
 * consumer (plaque.js, heroes.js, named-skills.js, leaderboard.js,
 * skill-explorer.js) derives branch + rank vocabulary identically.
 *
 * §Ygg-II rubric E1: branch MUST be derived at read-time — NEVER from
 * skill.type === 'ultimate'|'unique'|'extra' and NEVER from a stored
 * branch/tier field. The only valid `type` values are 'basic' and 'fusion'.
 *
 * §Ygg-II rubric E2: rank WORDS fork by branch at 4★+. BANNED anywhere:
 * 'Transcendent', 'Hardened'. Correct ladder:
 *   shared {1 Awakened, 2 Named, 3 Evolved}
 *   suite  {4 Extra, 5 Ultimate, 6 Apex}
 *   unique {4 Unique, 5 Unique Ultimate, 6 Unique Impossible}
 *
 * Exposes on window (IIFE, no build step, dependency-free, idempotent):
 *   window.GaiaSemantics = {
 *     computeBranch(node, effRank),   // 'standard' | 'suite' | 'unique'
 *     rankWord(level, branch),        // e.g. 'Unique Ultimate'
 *     rankLabel(level, branch),       // e.g. 'Unique Ultimate · 5★'
 *   }
 *
 * Load BEFORE every consumer (plaque.js, heroes.js, named-skills.js, …).
 */
(function () {
  'use strict';

  // Idempotent: if a prior include already installed GaiaSemantics, keep it.
  if (typeof window !== 'undefined' && window.GaiaSemantics) return;

  // Accept a level like "5★", "5", or 5 → clamped integer 0..6.
  function levelNum(level) {
    if (level == null) return 0;
    if (typeof level === 'number') return level | 0;
    var n = parseInt(String(level).replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : Math.max(0, Math.min(6, n));
  }

  // computeBranch — the ONLY correct client branch resolver (Ygg II).
  //
  // node:    the source skill object (carries .type, .suiteComponents).
  // effRank: the skill's effective star level ("5★" | 5 | "5" all accepted).
  //
  // Read order mirrors resolveSemantics §3.2 and must not be reordered:
  //   1. unique = type === 'basic' && effRank >= 4 && !suiteComponents
  //   2. suite  = suiteComponents present (length > 0)
  //   3. else     standard
  function computeBranch(node, effRank) {
    node = node || {};
    var type = node.type;
    var rank = levelNum(effRank != null ? effRank : node.level);
    var hasSuiteComponents = Array.isArray(node.suiteComponents)
      && node.suiteComponents.length > 0;

    // 1. Unique FIRST — a Basic that ascended to elite rank without fusing.
    if (type === 'basic' && rank >= 4 && !hasSuiteComponents) return 'unique';

    // 2. Suite — the generic parent carries suiteComponents.
    if (hasSuiteComponents) return 'suite';

    // 3. Everything else is the standard (shared) branch.
    return 'standard';
  }

  // Shared rank words for 1★–3★ (branch-agnostic). 0★ = Basic (starless).
  var SHARED_WORD = { 0: 'Basic', 1: 'Awakened', 2: 'Named', 3: 'Evolved' };
  // Suite branch 4★–6★.
  var SUITE_WORD = { 4: 'Extra', 5: 'Ultimate', 6: 'Apex' };
  // Unique branch 4★–6★.
  var UNIQUE_WORD = { 4: 'Unique', 5: 'Unique Ultimate', 6: 'Unique Impossible' };

  // rankWord — the branch-forked rank NAME. Never emits Transcendent/Hardened.
  //   level:  "5★" | 5 | "5"
  //   branch: 'standard' | 'suite' | 'unique' (default 'standard')
  function rankWord(level, branch) {
    var n = levelNum(level);
    if (n <= 3) return SHARED_WORD[n] || 'Basic';
    // 4★+ forks by branch. 'suite' and 'unique' are the only forked branches;
    // a 'standard' skill above 3★ has no forked name yet, so it reads as the
    // suite ladder word (the neutral default) — but in practice a 4★+ skill
    // always resolves to 'suite' or 'unique' via computeBranch.
    if (branch === 'unique') return UNIQUE_WORD[n] || UNIQUE_WORD[6];
    return SUITE_WORD[n] || SUITE_WORD[6];
  }

  // rankLabel — "<rankWord> · N★" (e.g. "Unique Ultimate · 5★").
  function rankLabel(level, branch) {
    var n = levelNum(level);
    return rankWord(level, branch) + ' · ' + n + '★';
  }

  var api = {
    computeBranch: computeBranch,
    rankWord: rankWord,
    rankLabel: rankLabel,
  };

  if (typeof window !== 'undefined') window.GaiaSemantics = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
