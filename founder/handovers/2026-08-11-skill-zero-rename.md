# Handover — Skill Zero: split the launcher out of "Skill Heaven" (cross-repo rename)

One-line summary: Rename the `skill-heaven` repo → **`gaia-skill-heaven`** (umbrella runtime brand), rename its launcher out to **Skill Zero** (`skill-zero` engine; doors `claude-zero`/`pi-zero`/…), free **Heaven/Hell/Ultra** to be the behavioral axis (summon directions + governor, HH Index WIP), keep **skill-hell** summon unchanged in `gaia-mcp`, split the lexicon (`gaia.zero` carved out of `gaia.heaven`), and fix the Heaven-means-subtraction inversion everywhere — evolving the surface toward `ENDGAME.md`.

Status: PLAN — REVIEW-READY (execution gated on founder approval)
Date: 2026-08-11
Branches: `dev/skill-zero-rename` in each of the four repos
Decision authority: `gaia-research/founder/RATIFICATION.md` (amends N8/N9)
Governing RFC: `gaia-research/docs/plans/2026-08-11-skill-zero-rename-rfc-issue-draft.md` → to be posted as a `gaia-research/gaia-research` issue
Covers: amends `gaia-research#68`; touches `skill-heaven` #25/#29/#30/#31/#32, `gaia-mcp#15`

---

## 1. Problem / Motivation

"Skill Heaven" does triple duty: umbrella product, clean-slate **launcher**, and
one pole of the behavioral **axis**. ENDGAME separates these. Scouting all four
repos showed the prototype's user-facing surface is **almost entirely the
launcher** (posture/floor/curated/native, eviction, "strip context — run
clean," the doors, the compiler), which is *a launcher with zero skills* — not
Heaven the axis pole, and not the umbrella. The launcher never had a name, so it
wore "Skill Heaven."

This handover gives the launcher its name — **Skill Zero** — evolves the surface
toward ENDGAME, and delivers the messaging the founder wants:

1. **`skill-heaven → skill-zero` is now a complete, usable prototype.** Promote
   the launcher copy from "WORK IN PROGRESS" to "usable prototype" (it is
   M0-verified, 30 tests, KC4 passing).
2. **"Skill Heaven" = the umbrella runtime brand** users associate with
   everything we do at runtime (repo `gaia-skill-heaven`).
3. **The Hell-Heaven (HH) Index is in the works** — the axis/research is the new
   WIP banner.
4. **Future:** the summon side (today `skill-hell`, explore-only) gains a
   `skill-heaven` converge/curated summon — making summon bidirectional. Noted,
   not built here.

## 2. Locked decisions (not open — settled in the shaping session)

- Umbrella brand **Skill Heaven**; repo `skill-heaven` → **`gaia-skill-heaven`**.
- Launcher = **Skill Zero**, a deep standalone module *inside* `gaia-skill-heaven`
  (NOT a new repo — ENDGAME MIGRATION §13). Engine `packages/core` → npm
  `skill-zero`, bin `skill-zero`.
- Doors → short user-facing identities: **`claude-zero`, `pi-zero`,
  `codex-zero`, `hermes-zero`, `grok-zero`**. `gaia-` prefix is for **repos
  only**.
- **Heaven / Hell = summon directions** (axis); **Ultra = the auto-switch**.
  HH Index stays in `gaia-research`, marked WIP.
- **skill-hell** (summon) stays in `gaia-mcp` **unchanged**, except outward
  references to the old `skill-heaven` name/URL.
- Lexicon: **carve `gaia.zero` out of `gaia.heaven`**, both owned by the
  gaia-research HQ; `gaia-skill-heaven` consumes. Two migrations deferred
  (see RFC §5).
- **Heaven semantic inversion fixed**: subtraction/strip/evict/floor → Skill
  Zero; Heaven-mode redefined as converge/curated summon.
- Prefix taxonomy ratified: `gaia-*` = ecosystem, `skill-*` = standalone skill
  (so `skill-hell` correctly keeps `skill-*`).

## 3. Full surface inventory (from the scout pass — the edit targets)

### 3a. `skill-heaven` → `gaia-skill-heaven` (repo/brand; contents = Skill Zero relabel)
- `README.md` — **near-total rewrite**: launcher framing → Skill Zero, "complete
  usable prototype" banner; retain "Skill Heaven" as the umbrella H1 + keep the
  HH Index paragraph tagged as axis/research WIP.
- `package.json` (root) `skill-heaven-monorepo` → `gaia-skill-heaven-monorepo`.
- `packages/core/package.json` name+bin `skill-heaven` → `skill-zero`; desc.
- `packages/claude-heaven/` → `packages/claude-zero/`: name `claude-zero`; bins
  `claude-zero`, `claude-zero-statusline`; `README.md`; `src/{launcher,cli,census,statusline*,statusline-cli}.ts`;
  `test/*`; `scripts/{generate-p2-gate,probe-kc4-listing-residual,verify-marketplace-install}`;
  `plugin/.claude-plugin/plugin.json` (name/desc); `plugin/commands/skill-heaven.md`
  → `skill-zero.md`; `plugin/scripts/render-posture.mjs`; `plugin/data/p2-gate.json`.
- `packages/pi-heaven/` → `packages/pi-zero/`: name `pi-zero`; `README.md` (stub).
- `.claude-plugin/marketplace.json` — name/plugin/description (`skill-heaven` →
  `gaia-skill-heaven`; `claude-heaven` → `claude-zero`; keep `/skill-hell` door
  language reframed as the Hell summon door).
- `packages/site/*`, `CLAUDE.md`, `docs/assets/*` references.

### 3b. `gaia-research` (brand + axis/research; launcher-desc relabels + inversion fix)
- `docs/skill-heaven/VISION.md`, `MISSION.md` — **the Heaven-inversion fix**
  (largest edit): subtraction/strip/evict/floor → Skill Zero; Heaven = converge
  summon; keep the dir path (brand history) or leave — dir rename optional/defer.
- `content/reports/skill-heaven/**` (VISION/MISSION mirrors, RFC-68 archives),
  `content/reports/hh-benchmark/{m2-live-demo,kc9-three-minute-demo,claim-index}.md`
  (`skill-heaven --posture …` examples → `skill-zero`).
- `docs/plans/skill-heaven-hell-mvp-plan.md`, `docs/plans/m2-heaven-launcher-plan.md`,
  `docs/plans/archived/*skill-heaven*`.
- `founder/RATIFICATION.md` — **oracle amendment**: add the "Skill Zero split"
  delta under N8/N9 (D9: ships with first implementation PR).
- Site: `app/page.tsx` ("Stop installing skills…", "Heaven clears the room. Hell
  fills it." → axis copy; launcher pitch → Skill Zero), `app/mcp/page.tsx`,
  `app/research/hh-benchmark/page.tsx`, `components/MilimPet/tooltips.ts`.
- `data/mcp.ts` (summon selectors — **unchanged**), `.github/workflows/{lexicon-ci,hh-benchmark-ci}.yml`
  (path globs if dirs move).
- **Lexicon** (see §4).

### 3c. `gaia-mcp` (skill-hell stays; outward references only)
- `alias/skill-hell/package.json` `homepage` `https://gaia-research.github.io/skill-heaven/`
  → new umbrella URL; keyword `skill-heaven`.
- `alias/skill-hell/README.md` — "additive half of the **Skill Heaven** ladder"
  + "launchers live at gaia-research/**skill-heaven**" → `gaia-skill-heaven` +
  reframe (launcher = Skill Zero).
- `docs/SKILL-HELL.md` — "high-entropy end of the Skill Heaven ladder… *subtracts*
  to a clean floor" → subtract = Skill Zero; Hell = summon direction of the axis.
- `VERSIONING.md`, `README.md`. **No code/bin/session-prefix changes.**

### 3d. `gaia-skill-tree` (founder governance)
- `founder/ENDGAME.md` §9 (split "Skill Heaven" execution system → Skill Zero
  launcher + Arbor axis), §10 CLI grouping, §11 frontend lens.
- `founder/ENDGAME - MIGRATION.md` §11/§12/§13/§14 (repo doctrine
  `skill-heaven`→`gaia-skill-heaven`; "execution product" framing → Skill Zero +
  axis); `ENDGAME - SCHEMA.md` (HH Index = axis — confirm, minimal).
- `founder/GAIA_ROADMAP v5 (BUILD).md`, `founder/STEWARD.md` §13,
  `founder/MEMORY.md` (four-name story: Tree · **Skill Heaven** (umbrella) ·
  Skill Zero (launcher) · Hell · Research), `founder/handovers/done/ARC_I.md`.
- `founder/LEXICON.md` regenerated + `scripts/lexicon/lexicon.foreign.json` mirror.

## 4. Lexicon change spec (`gaia-research/founder/`)
- Edit `lexicon.gaia.heaven.json`: rewrite `about`; keep axis terms; add
  `heaven`, `hell`, `polarity` (axis directions); retire the door product names
  with `state: banned` + `replacement` (`claude-heaven`→`claude-zero`, …);
  redefine `skill-heaven` term = the umbrella repo `gaia-skill-heaven`.
- New file `lexicon.gaia.zero.json` (namespace `gaia.zero`, `extends: core`):
  move `launcher`, `door`, `floor`, `product-floor`, `clean-room`, `native`,
  `curated`, `level`, `posture`, `eviction`, `context source`; add `skill-zero`,
  `claude-zero`, `pi-zero`, `codex-zero`, `hermes-zero`, `grok-zero`,
  `/skill-zero`, `/skill-ultra`.
- Register `gaia.zero` in `lexicon.json` `owns`; regenerate `LEXICON.md`;
  update foreign mirror in **gaia-skill-tree** (`scripts/lexicon/lexicon.foreign.json`)
  and its `LEXICON.md`. Run `check-lexicon` in both repos — must pass.

## 5. Execution sequence (low-risk ordering)
1. **Docs / founder / lexicon / RFC / issue comments** (all in-repo, reversible):
   ENDGAME + adjacent, VISION/MISSION inversion fix, lexicon split + regen,
   RATIFICATION delta, post the governing RFC issue, comment the connected issues.
2. **In-repo package/code renames** in `skill-heaven` (repo still named that):
   `packages/*` folders, package.json names/bins, README rewrite, marketplace,
   plugin, commands, tests. Run `npm test` (expect 30 green) + `check-lexicon`.
3. **Repo rename LAST** `skill-heaven` → `gaia-skill-heaven`, then **immediately**
   fix `gaia-mcp` outward URLs and, if the homepage matters, publish a `skill-hell`
   patch. (GitHub redirects the repo; raw asset paths in already-published npm
   tarballs do not.)

## 6. Proposed workflow (post-approval)
Phased fan-out; roster mapped to difficulty:
- **Phase 1 (docs+governance)** — `worker-sol`: ENDGAME/MIGRATION/SCHEMA edits +
  VISION/MISSION inversion fix (highest judgement). `worker-terra`: RATIFICATION
  delta + lexicon split/regen + RFC issue post + issue comments. `worker-luna`:
  ROADMAP/STEWARD/MEMORY/ARC_I mechanical relabels.
- **Phase 2 (code)** — `worker-terra`: `skill-heaven` package/folder renames +
  marketplace/plugin/commands + tests green. `worker-luna`: `gaia-mcp` outward-ref
  edits. `worker-terra`: `gaia-research` reports/demos/site copy.
- **Phase 3 (repo rename)** — `worker-terra` (or manual `gh repo rename`) + the
  gaia-mcp URL fix. Executed by the workflow if approved.
- **Review gate** — I (the orchestrator) review the full diff of every repo
  against §2/§3/§4 and the four messaging goals before anything merges.

## 7. Review checklist (what the orchestrator verifies before merge)
- [ ] No user-facing surface still calls the **launcher** "heaven" (grep
      `claude-heaven|pi-heaven|skill-heaven --posture|/skill-heaven` in code/README/site).
- [ ] "Skill Heaven" appears **only** as the umbrella brand or the axis; never
      the launcher or a bin.
- [ ] The Heaven-subtraction inversion is fixed in VISION.md + MISSION.md +
      homepage (Heaven = summon, not strip).
- [ ] `skill-zero` reads as a **complete, usable prototype** (WIP banner moved
      to the HH Index).
- [ ] `skill-hell` bins/sessions/tests **unchanged**; only outward URLs/brand fixed.
- [ ] `check-lexicon` green in both HQs; `LEXICON.md` + foreign mirrors regenerated.
- [ ] `npm test` green in `gaia-skill-heaven` (30) and `gaia-mcp`.
- [ ] RFC issue posted; connected issues commented + linked; RATIFICATION delta present.
- [ ] Repo rename done last; gaia-mcp outward URLs point to `gaia-skill-heaven`.

## 8. Explicitly out of scope (recorded)
- Building the `skill-heaven` (converge) summon — future; makes summon bidirectional.
- Promoting `gaia.zero` to its own lexicon HQ; migrating the axis vocab to the
  gaia-skill-tree HQ (waits on Arbor I).
- Any HH Index scoring/computation work — it stays WIP.
- `docs/skill-heaven/` directory rename (kept as brand history; revisit later).
