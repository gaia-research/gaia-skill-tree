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
 * Yggdrasil II PR3b — READ EMITTED FIELDS, don't recompute.
 * The taxonomy authority (src/gaia_cli/taxonomy.py) now EMITS resolved
 * { branch, rank, rankWord, medallion } onto every named entry in
 * docs/graph/named/index.json. Consumers MUST prefer those emitted fields.
 * The compute* mirror below survives ONLY as the fallback for the STARLESS
 * generic graph (docs/graph/gaia.json), whose nodes carry no emitted branch
 * (type is basic|fusion only). branchOf/rankWordOf/medallionOf are the seam:
 * they read the emitted field when present and recompute otherwise.
 *
 * Exposes on window (IIFE, no build step, dependency-free, idempotent):
 *   window.GaiaSemantics = {
 *     branchOf(entry),                // emitted entry.branch, else computeBranch
 *     rankWordOf(entry),              // emitted entry.rankWord, else rankWord()
 *     medallionOf(entry),             // emitted entry.medallion, else medallion()
 *     computeBranch(node, effRank),   // FALLBACK ONLY — starless generic graph
 *     rankWord(level, branch),        // FALLBACK ONLY — e.g. 'Unique Ultimate'
 *     rankLabel(level, branch),       // FALLBACK ONLY
 *     medallion(branch, rank),        // FALLBACK ONLY — ◇ | ◉ | ◆
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

  // computeBranch — DORMANT fallback resolver.
  //
  // Yggdrasil II ORIGIN RULE: the starless generic graph (docs/graph/gaia.json)
  // NO LONGER routes through this. Its nodes now carry a build-time-STAMPED
  // branch (surfaced from the bucket's CLI-declared origin entry) or none at all
  // — and skill-graph.js READS node.branch directly, guessing nothing. This
  // mirror survives only as a defensive fallback inside branchOf(entry) for a
  // payload that predates the branch emit; no live consumer exercises the
  // rank-from-type guess for a rank-less node anymore.
  //
  // node:    the source skill object (carries .type, .suiteComponents).
  // effRank: the skill's effective star level ("5★" | 5 | "5" all accepted).
  //
  // Read order mirrors resolveSemantics §3.2 and taxonomy.py and must not be
  // reordered:
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

  // Structural-class medallion glyphs (mirror taxonomy.py MEDALLION_*). Suite +
  // standard branches share the white diamond until 4★; the unique branch owns
  // the circled bullet; suite ≥4★ owns the black diamond. FALLBACK ONLY — prefer
  // the emitted entry.medallion via medallionOf(entry).
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

  // ── Emitted-field seams (PR3b) — PREFER these everywhere ─────────
  // branchOf/rankWordOf/medallionOf read the field the taxonomy authority
  // already resolved onto the entry (docs/graph/named/index.json). They fall
  // back to the compute* mirror ONLY when the field is absent — i.e. a starless
  // generic-graph node. entry may be a named entry OR a generic skill object.
  function branchOf(entry) {
    if (entry && typeof entry.branch === 'string' && entry.branch) return entry.branch;
    return computeBranch(entry, entry && entry.level);
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
    computeBranch: computeBranch,
    rankWord: rankWord,
    rankLabel: rankLabel,
    medallion: medallion,
  };

  if (typeof window !== 'undefined') window.GaiaSemantics = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
