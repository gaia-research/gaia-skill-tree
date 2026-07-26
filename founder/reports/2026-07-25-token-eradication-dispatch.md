# Dispatch Prompt — Token-Pollution Eradication (Yggdrasil II, grounded on 2026-07-25 Session 3 MEMORY)

> Hand this to the orchestrator/lead agent of the fresh session. It is self-contained.
> It supersedes `founder/reports/design-review-2026-07-20/TOKEN-POLLUTION-AUDIT.md`, which is
> **CONFIRMED STALE** on the Suite-vs-Unique question (it flattens two distinct ladders into one).

---

## Mission

Eradicate the deprecated design-token confusion across the Yggdrasil II frontend + CLI so that
(a) there is ONE clear source of truth, (b) `DESIGN.md` + `generateCssTokens.py` document/emit it
truthfully with **both rank ladders explicit**, and (c) PR #1185 carries ZERO token pollution and
merges green to `main`. Long-term: an Ygg III palette swap must be a one-file `gaia.json.meta` edit.

**Working branch:** `dev/yggdrasil-ii-staging` (staging tip was `2b54decea` at Session 3 close —
verify current tip first). All work lands on `design/*` PRs INTO staging, never `main`.
**Commit identity — MANDATORY on every commit:** `--author="mbtiongson1 <mbtiongson1@users.noreply.github.com>"`.

---

## RATIFIED 2026-07-25 — Unique branch moves to `--rank-*-unique` (the central workstream)

Founder ruling: the Suite/Unique **token asymmetry is itself the recurring pollution** and must be
fixed at the root. The Unique branch rank ladder migrates OFF the `--tier-unique*` branch-family names
ONTO the rank axis, symmetric with Suite:

| ★ | Suite (unchanged) | Unique — OLD name | Unique — NEW name | Unique hex (design-LOCKED) |
|---|---|---|---|---|
| 4★ | `--rank-4` #e879f9 | `--tier-unique` #7c3aed | **`--rank-4-unique`** | `#7c3aed` violet |
| 5★ | `--rank-5` #fbbf24 | `--tier-unique-5` #b26a3a | **`--rank-5-unique`** | `#b26a3a` burnished copper |
| 6★ | `--rank-6` #fbbf24 | `--tier-unique-6` #e0894a | **`--rank-6-unique`** | `#e0894a` ember copper |

Suffix families move too: `-rgb`, `-bg`, `-border`, `-edge`, and the 6★ `-ink` (`#2a1206`).
After migration BOTH branches are `--rank-N[...]` / `--rank-N-unique[...]` — one rank axis, two branches.

**CRITICAL — `--tier-unique` has DUAL DUTY. This is NOT a mechanical find-replace.** The bare
`--tier-unique` token is consumed in two distinct roles across 158 occurrences / 21 files:
- **Role A — Unique RANK color** (a 4★–6★ Unique-branch skill's rank tint): → rename to `--rank-*-unique`.
- **Role B — Unique BRANCH IDENTITY** (the `◉` glyph `--tier-unique-symbol`, generic "this is a Unique
  branch" accent, plaque orb `--tier-unique-bg/-border`, and MEMORY:73's `.tier-glyph[data-type="fusion"]`
  which REUSES `--tier-unique` violet for an unrelated *type* concept): these are BRANCH tokens, NOT rank —
  they must be classified per-consumer and either kept as a branch token or corrected, NOT blindly renamed.

Every one of the 158 consumers must be classified Role A vs Role B before migrating. Adversarially
verify the classification (the whole reason T19 keeps recurring is blind swaps on this exact surface).

**Generator changes** (`scripts/generateCssTokens.py` ~L195-236): the `_emit_tier_block("unique", …)`
call + the hardcoded `--tier-unique-5/-6` decoration ladder emit the Unique RANK family under
`--rank-*-unique`. Keep whatever Role-B branch-identity token the glyph/orb genuinely needs (likely a
retained `--tier-unique` for the `◉` symbol + branch accent). Reconcile `formatting.py RANK_COLORS_UNIQUE`
(stale violets `#8b5cf6/#7c3aed/#6d28d9`) to the CSS-locked Amethyst→Ember values — CSS wins.
`scripts/generateBadges.py unique_hex()`/`UNIQUE_INK` mirror this ladder — keep them in lockstep.

**Blast radius (verify before dispatch):** styles.css (44), plaque.css (28), tokens.css (15, generated),
ascension-overdrive-v2.css (11), skill-graph.js (7), leaderboard.js (5), badges/index.html (5),
skill-explorer.js (4), profile-timeline.js (4), + ~12 more files. `src/gaia_cli/tui/tokens.py` (1) is the
separate TUI namespace — out of scope.

---

## THE VERIFIED MODEL (ground truth — do not trust the stale audit doc)

Confirmed independently from THREE source files this session:
`scripts/generateCssTokens.py` (`UNIQUE_BRANCH_TIER`, "Unique decoration ladder" ~L210-236),
`src/gaia_cli/formatting.py` (`RANK_COLORS_UNIQUE`, `LEVEL_LABELS_SUITE/UNIQUE`, `rank_color_for`),
`docs/js/skill-semantics.js` (`SUITE_WORD`/`UNIQUE_WORD`).

**Ranks 4★–6★ FORK into two deliberately-distinct parallel ladders. 0★–3★ are shared.**
The table below shows the CURRENT (pre-migration) token names and the POST-migration target
(see the ratified rename section above — Unique moves onto the rank axis):

| ★ | Suite word | Suite token | Unique word | Unique token — CURRENT | Unique token — TARGET | Unique hex |
|---|---|---|---|---|---|---|
| 4★ | Extra | `--rank-4` #e879f9 | Unique | `--tier-unique` | **`--rank-4-unique`** | `#7c3aed` violet |
| 5★ | Ultimate | `--rank-5` #fbbf24 | Unique Ultimate | `--tier-unique-5` | **`--rank-5-unique`** | `#b26a3a` burnished copper |
| 6★ | Apex | `--rank-6` #fbbf24* | Unique Impossible | `--tier-unique-6` | **`--rank-6-unique`** | `#e0894a` ember copper |

\* `--rank-5` and `--rank-6` share `#fbbf24`; Apex differentiates by **doubled background opacity**, not hue. Not a bug.

**DEAD tokens (never defined, never emitted) — these are the pollution to kill:**
`--tier-extra` (faked Suite 4★ → migrate to `--rank-4`), `--tier-ultimate` (faked Suite 5★ → `--rank-5`),
bare `--extra`/`--ultimate`. Confirmed undefined everywhere except the self-contained page
`docs/evidence/verification_process.html` local `:root` (KEEP, out of scope) and the separate
TUI namespace `src/gaia_cli/tui/tokens.py` (Textual constants, NOT web CSS — out of scope).

**LEGITIMATE tokens — LEAVE ALONE:** `--tier-basic` (#38bdf8), `--tier-fusion` (#f59e0b),
`--rank-0..6`, `--apex-gold`. **`--tier-unique*` is being RENAMED** (Role A → `--rank-*-unique`), except
any retained Role-B branch-identity use (glyph `◉` symbol / generic Unique-branch accent) — classify per consumer.

### HAZARD — a THIRD layer of the confusion (flag, do not silently "fix")
The Unique ladder DISAGREES between CSS and Python:
- `tokens.css` (site render, **design-locked** per `colorize LOCKED 2026-07-18`): `#7c3aed`/`#b26a3a`/`#e0894a` (Amethyst→Ember).
- `formatting.py` `RANK_COLORS_UNIQUE` (CLI): `#8b5cf6`/`#7c3aed`/`#6d28d9` (stale violets).
The **CSS `tokens.css` Amethyst→Ember ladder is the locked design truth.** If reconciling, `formatting.py`
moves to match CSS — NOT the reverse. Surface this as a founder ruling before touching either; do not guess.

---

## Source of truth architecture (already correct — this is the GOOD part)
`registry/gaia.json → meta` (`typeColors` {basic,fusion}, `levelColors` {0★..6★}, `typeSymbols`) is the
ONE source. `scripts/generateCssTokens.py` reads it and emits BOTH `--tier-*` AND `--rank-*` into
`docs/css/tokens.css` (`--check`-guarded). The `--tier-unique*` family is hardcoded in the generator
(`UNIQUE_BRANCH_TIER`) because `unique` is a read-time branch, not a `type`. No hand-injection.
=> Ygg III palette swap = edit `gaia.json.meta` + regen. Preserve this property.

---

## PRIORITY ORDER (highest first — from MEMORY.md:66-72)

1. **`.nav-meta` regression (do FIRST, unambiguous).** `docs/css/styles.css:11681` `.nav-meta` is
   live-WRONG at `var(--rank-3, #a78bfa)`; correct value is `var(--rank-4, #e879f9)` (the Suite purple
   it had pre-session). A prior session broke it on a misread of "directory token purple." Revert to `--rank-4`.

2. **4 confirmed LIVE Suite/Unique branch-fork bugs** (real Unique skills render in Suite gold/fuchsia today):
   - **Hero cards** — `docs/heroes/heroes.css` (rank-keyed accents ~L499-532) need a `[data-branch="unique"]` override; ~25 dependent accent rules. Highest impact.
   - **Hall of Heroes side-rail** — `docs/heroes/heroes.js:471` emits `data-level` but not `data-branch`; add `data-branch` to markup + matching `[data-branch="unique"]` CSS. (Also: the rail is overpopulated + has alignment issues — founder wants an /impeccable redesign pass here: uncapped list, 4 fields/row at <232px, 3 mismatched section max-widths 680/720/800px.)
   - **Trust Ledger star badges** — `docs/trust/ledger/ledger.js` has NO branch awareness; join branch data in, add `[data-branch="unique"]` rules to `ledger.css`.
   - **badges legend** — `docs/badges/index.html:~1170` the site's own canonical color-ladder legend mislabels the 5★ Unique row in Suite gold.
   **Bug signal to grep:** a `[data-level="4|5|6"]` CSS color selector with NO sibling `[data-branch="unique"]` rule.

3. **DESIGN.md truth-up (founder ruling: finish this as its own PR).** Show BOTH ladders EXPLICITLY —
   never a single `--rank-N` "rank ramp" (that flattening IS the pollution). After the rename BOTH branches
   are on the rank axis: Suite `--rank-4/5/6`, Unique `--rank-4-unique/-5-unique/-6-unique`. Sections to fix:
   - §Color Palette (~L21-34): retire `--tier-extra`/`--tier-ultimate` language; document the
     `gaia.json.meta.{typeColors,levelColors}→generateCssTokens.py→tokens.css` chain; state that 4★-6★
     color FORKS into two rank sub-ladders (Suite `--rank-N` vs Unique `--rank-N-unique`), one axis, two branches.
   - §Skill Tiers→§Skill Types (~L31-48): replace 4-tier table with 2-type (basic/fusion) + Unique branch note.
   - §Rank System (~L52-70): the words table already forks Suite/Unique; ADD the forked TOKEN columns
     (`--rank-N` / `--rank-N-unique`). Fix §World Tree table (~L94-101) if it flattens.
   - §Evidence Type Pills (~L150-158): `github-stars/fusion-recipe/github-stars-own`→`--rank-5`;
     `benchmark-result/arxiv`→`--rank-4` (both currently name dead `--tier-*`).
   - §Graph Canvas (~L184-201): legacy Ygg-I `type` radius vocab — flag as prose-only, not color.
   - `docs/js/skill-graph.js:16/18` canvas-token contract comment lists dead `--tier-extra/-ultimate` → replace with `--tier-fusion` + the retained Role-B `--tier-unique` (branch glyph).
   NOTE: EOL — DESIGN.md is LF; ensure your editor doesn't rewrite to CRLF (churns 1187 lines). `sed -i 's/\r$//'` if needed.

4. **`docs/samples/*` dead-token bugs** (foundation.html, tree.html, registry-3d-fonts.html) — confirmed
   real (not just T19-adjacent). Migrate `--tier-extra`→`--rank-4`, `--tier-ultimate`→`--rank-5`, drop hex
   fallbacks. Founder should confirm "skip samples" no longer holds. (`skill-flowchart.html`/`flowchart.html`
   use hardcoded rgba on data-attrs — attribute-vocab, DEFER.)

5. **Authoritative `--tier-unique*` consumer map:** `founder/reports/2026-07-25-tier-unique-classification.md`
   (adversarially verified, 127 hits/19 files). **37 Role-A hits across 6 files RENAME** to `--rank-*-unique`
   (styles.css 12, skill-graph.js 7, ascension-overdrive-v2.css 6, leaderboard.js 5, badges/index.html 5,
   named-skills.js 2). ~90 Role-B hits KEEP as `--tier-unique` (branch glyph ◉ / plaque orbs / generic accent).
   Verifier overturned all 11 first-pass "keep" mistakes → rank, and leaned the 4 ambiguous → rank; confirm
   those on implementation. **One genuine correction** (not a rename): `.tier-glyph[data-type="fusion"]`
   misuses `--tier-unique` violet for the FUSION type — fix to `--tier-fusion`, do NOT rank-rename.
   **CONFIRMED CORRECT, do not "fix":** `profile-timeline.js` colors by finishing rank not branch (by design).

---

## OUT OF SCOPE (founder rulings 2026-07-25)
- **`docs/en/*`** — owned by the documentation team; its `--tier-*` fallback-hex residue is a SEPARATE
  post-Ygg-II PR for that team. Do NOT touch in this sprint. (Was already clean on staging anyway.)
- `docs/evidence/verification_process.html` local `:root` — KEEP (point-in-time evidence artifact).
- `src/gaia_cli/tui/tokens.py` — separate TUI namespace, not web CSS.
- `#1185` merge-conflict resolution (19 files, real content divergence, `skill-semantics.js` vs
  `plaque-reveal.js` survivor call) — **founder handling personally**, do NOT dispatch to an agent.

## Recoverable fan-out shape
`isolation: "worktree"` per agent (verify `pwd` first — worktrees have been unreliable here);
branch `design/ygg2-<topic>` off `origin/dev/yggdrasil-ii-staging`; ONE commit+push per file;
`--author` pinned; read-back after every .css/.html/.js edit (no merged lines, balanced braces,
Guard A: no bare banned hex outside `var(--x, #hex)`); report `{file, SHA}` as you go.

## Verification gate
- Grep ZERO (excl. verification_process.html + TUI): `--tier-(extra|ultimate)`, bare `var(--extra|--ultimate)`.
- Grep ZERO Role-A `--tier-unique*` at the 37 renamed sites; the ~90 Role-B keeps remain intentionally.
- Each LIVE fork bug: a Unique-branch skill renders violet/copper (not Suite gold/fuchsia). Playwright-verify.
- `.nav-meta` = `--rank-4`. `generateCssTokens.py --check` + `check_hex_colors.py` (Guard A) exit 0.
- Playwright high-visibility: homepage, about, nav, leaderboards, Hall of Heroes.
- Keep a localhost server open for the founder to watch throughout.

---

## FULL SESSION INTENT (retained from the original brief — do not lose these)

This sprint is the **final design pass before staging→main**. The token rename is the centerpiece but NOT
the whole job. The complete intent:

**A. CLI front (this is BOTH a frontend and CLI tech-debt sprint).** The web CSS is the main surface, but
verify the CLI palette source stays coherent: `src/gaia_cli/formatting.py` (`RANK_COLORS`, `TIER_COLORS`,
`RANK_COLORS_UNIQUE` — reconcile the stale violets to the CSS-locked Amethyst→Ember), and
`src/gaia_cli/tui/tokens.py` (separate TUI namespace — decide whether its `TIER_EXTRA`/`TIER_ULTIMATE`
constants should also retire for vocabulary consistency, or stay as an isolated terminal concern). Env note:
gaia-cli may be wonky — fall back to python scripts directly.

**B. Hall of Heroes `/impeccable` critique + redesign (its own design/* PR before final merge).**
`docs/heroes/{index.html,heroes.css (1408L),heroes.js (789L)}`. Founder flag: "some areas not aligned, left
rail overpopulated." Confirmed findings (Explore critique this session):
- **P1 branch-fork color bug** (also item 2 above): rail + stage accent color by `data-level` not `data-branch`
  → Suite/Unique mis-colored. Emit `data-branch` on the rail `<button>` (heroes.js:471), re-key CSS.
- **P2 overpopulated left rail:** uncapped `<li>` list (heroes.js:450-485); 4 fields/row at <232px width;
  the plate above already repeats the active hero's name+rank (redundant). Drop a field, collapse
  avatar+glyph to one mark, cap/scroll the list.
- **P3 alignment:** three stacked sections use mismatched max-widths (680/720/800px) — introduce one shared
  `--heroes-content-max`; keep `.hero-card__stats` centered ≥560px; normalize ordinal + footer padding.
- Fixed-nav clearance already compliant (5rem→8rem). Run `/impeccable` as the critique gate.

**C. EPIC #1002 closure review (orchestrator's final-boss job).** Do the EPIC "review" by checking PR-body
checkmarks. #994/#995/#996/#997 are ✅. #998 (Frontend), #999 (CI guards), #1000 (Agent skills) are UNCHECKED
but substantially landed — VERIFY against live state and check them: #999 guards live on staging
(`meta-guard.yml`, `rank-vocabulary-guard.yml`, `taxonomy-authority-guard.yml`); #1000 agent skills clean of
`type: ultimate/extra`; #998's genuine remainder IS this token sweep + Hall of Heroes. Confirm no follow-ups
(CLAUDE.md sprint-completeness: everything a reviewer would call a direct consequence lands in-sprint; the
flowchart.html attr-vocab defer is documented as pre-existing, NOT filed as follow-up).

**D. Endgame (short-term outcome).** #1185 has ZERO token pollution + GREEN + ready to merge to `main`.
Path: token rename PRs + DESIGN.md + Hall of Heroes all land on `dev/yggdrasil-ii-staging` → regen Class-S
(`gaia dev docs`, restore `docs/graph/` if tests dirty it, #1275 hazard) → **founder resolves the #1185
19-file merge conflict personally** (script-survivor call, site-dark risk) → CodeQL triage (7 alerts, likely
diff-size artifact) → mark #1185 ready → **merge with a merge commit, NEVER squash** (EPIC branching model).

**E. Process constraints (from the brief).** Small `design/*` PRs into staging; `skip-scope-check` label
pre-authorized for any script/generator touch (the generator rename needs it); infra CI changes allowed if
needed; commits `--author="mbtiongson1 <mbtiongson1@users.noreply.github.com>"` ONLY; keep localhost open for
the founder to watch; THOROUGH + RECOVERABLE fan-out (your call on agent count + model tier).

**Long-term success:** when Ygg II → Ygg III (or any new design) arrives, a palette change is a one-file
`registry/gaia.json.meta` edit + regen — no CSS hand-editing, no token-name confusion, both branches on a
symmetric `--rank-*` axis.
