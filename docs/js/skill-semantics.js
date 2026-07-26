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
 * Yggdrasil II PR3b close-out — READ EMITTED FIELDS, never recompute.
 * The taxonomy authority (src/gaia_cli/taxonomy.py) EMITS resolved
 * { branch, rank, rankWord, medallion } onto every named entry in
 * docs/graph/named/index.json, and the origin mechanic stamps the same fields
 * onto starless generic-graph nodes (docs/graph/gaia.json) that have a bucket
 * origin (§7). branchOf/rankWordOf/medallionOf READ those emitted fields; a node
 * with NO emitted branch is a PLAIN node (starless, no origin) — we return the
 * neutral default and guess NOTHING from type+rank+suiteComponents. The client
 * computeBranch resolver is DELETED (founder ruling 2026-07-18): the resolver is
 * type-blind and reads only what the authority resolved.
 *
 * Exposes on window (IIFE, no build step, dependency-free, idempotent):
 *   window.GaiaSemantics = {
 *     branchOf(entry),                // emitted entry.branch, else 'standard'
 *     rankWordOf(entry),              // emitted entry.rankWord, else rankWord()
 *     medallionOf(entry),             // emitted entry.medallion, else medallion()
 *     rankWord(level, branch),        // branch-forked rank name (e.g. 'Unique Ultimate')
 *     rankLabel(level, branch),       // '<rankWord> · N★'
 *     medallion(branch, rank),        // ◇ | ◉ | ◆ from a RESOLVED branch
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

  // Shared rank words for 1★–3★ (branch-agnostic). 0★ = Basic (starless).
  var SHARED_WORD = { 0: 'Basic', 1: 'Awakened', 2: 'Named', 3: 'Evolved' };
  // Suite branch 4★–6★.
  var SUITE_WORD = { 4: 'Extra', 5: 'Ultimate', 6: 'Apex' };
  // Unique branch 4★–6★.
  var UNIQUE_WORD = { 4: 'Unique', 5: 'Unique Ultimate', 6: 'Unique Impossible' };

  // rankWord — the branch-forked rank NAME. Never emits Transcendent/Hardened.
  //   level:  "5★" | 5 | "5"
  //   branch: 'standard' | 'suite' | 'unique' (default 'standard')
  // Called only with an ALREADY-RESOLVED branch (from the emitted field via
  // rankWordOf, or a branch the authority resolved). It does not derive branch.
  function rankWord(level, branch) {
    var n = levelNum(level);
    if (n <= 3) return SHARED_WORD[n] || 'Basic';
    // 4★+ forks by branch. 'suite' and 'unique' are the only forked branches;
    // a 'standard' skill above 3★ has no forked name yet, so it reads as the
    // suite ladder word (the neutral default). In practice a 4★+ named skill
    // carries an emitted branch of 'suite' or 'unique'.
    if (branch === 'unique') return UNIQUE_WORD[n] || UNIQUE_WORD[6];
    return SUITE_WORD[n] || SUITE_WORD[6];
  }

  // rankLabel — "<rankWord> · N★" (e.g. "Unique Ultimate · 5★").
  function rankLabel(level, branch) {
    var n = levelNum(level);
    return rankWord(level, branch) + ' · ' + n + '★';
  }

  // Structural-class medallion glyphs (mirror taxonomy.py MEDALLION_*). Suite +
  // standard branches share the white diamond until 4★; the unique branch owns
  // the circled bullet; suite ≥4★ owns the black diamond. Derives the glyph from
  // an ALREADY-RESOLVED branch — prefer the emitted entry.medallion via
  // medallionOf(entry).
  var MEDALLION_UNIQUE = '◉';
  var MEDALLION_SUITE = '◆';
  var MEDALLION_STANDARD = '◇';
  function medallion(branch, rank) {
    var n = levelNum(rank);
    if (n >= 4) {
      if (branch === 'unique') return MEDALLION_UNIQUE;
      if (branch === 'suite') return MEDALLION_SUITE;
    }
    return MEDALLION_STANDARD;
  }

  // ── Emitted-field seams — READ the resolved field, guess nothing ────
  // branchOf/rankWordOf/medallionOf read the field the taxonomy authority
  // already resolved onto the entry (docs/graph/named/index.json, or the
  // origin-stamped starless node in docs/graph/gaia.json — §7). When the field
  // is absent the node is a PLAIN node (no origin / pre-emit payload): return the
  // neutral default. We NEVER re-derive branch from type+rank+suiteComponents —
  // the client-side computeBranch guess is deleted (founder ruling 2026-07-18).
  // entry may be a named entry OR a generic skill object.
  function branchOf(entry) {
    if (entry && typeof entry.branch === 'string' && entry.branch) return entry.branch;
    return 'standard';
  }
  function rankWordOf(entry) {
    if (entry && typeof entry.rankWord === 'string' && entry.rankWord) return entry.rankWord;
    return rankWord(entry && entry.level, branchOf(entry));
  }
  function medallionOf(entry) {
    if (entry && typeof entry.medallion === 'string' && entry.medallion) return entry.medallion;
    return medallion(branchOf(entry), entry && entry.level);
  }

  var api = {
    branchOf: branchOf,
    rankWordOf: rankWordOf,
    medallionOf: medallionOf,
    rankWord: rankWord,
    rankLabel: rankLabel,
    medallion: medallion,
  };

  if (typeof window !== 'undefined') window.GaiaSemantics = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
