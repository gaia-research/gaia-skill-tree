# Arc I — finalizing register

Everything that must land before `integration/arc-i-lane-a` (in
`gaia-research/skill-heaven`) merges to `main`.

Founder instruction, 2026-07-29: collect the in-scope remainder and tackle it
together as a **finalizing PR on the integration branch** — not as follow-up
issues. This is the sprint's own work, per CLAUDE.md § Sprint Completeness.

Status at time of writing: Session 8G. Integration tip `bec8dbd`, suite
**180 passing** (orchestrator-run, not reported).

---

## FOUNDER RULINGS — Session 8H, 2026-07-30

All three open decisions in this register are now **closed**. Recorded here
verbatim in substance; the roadmap §10 amendment and the `gaia.heaven` lexicon
entry follow from these, not the reverse.

### R1. `curated` is a personal-profile posture, not a benchmark arm

A clean room plus **a hand-picked fraction of the user's own skills** — a
fraction of what they have, named explicitly. It is intended to be
**onboardable and personalizable**, with an option to source outsourced skills
via **gaia mcp**, and it is **saved as a personal profile**.

**Because it is personalized, it is not measured.** The measured arms are
three, and curated is not among them:

| Arm | What it is |
|---|---|
| **clean room** | the doorless benchmark floor — placebo-of-record (B2) |
| **door** | the doorful product floor (+515 tok per F7) |
| **native** | claude untouched |

Ratify on the lexicon under `gaia.heaven`, **not locked** — the entry is
amendable as the posture's product shape settles.

**Arc scope (orchestrator reading, founder to correct if wrong):** Arc I's KC4
is the **clean-room composition only**. Onboarding flow, profile persistence,
and MCP-sourced skills are the curated *product's* later arcs — gaia mcp is
Program 4, Arc III. Recorded now as a ruling; built later.

### R2. KC4 stands as written; the composition changes

Empty `--setting-sources` — chosen deliberately over `local`, because `local`
returning a clean listing on one machine may only mean that machine had no
local-scope skills, whereas empty is structurally "no ambient sources."
**Empty value ≠ omitting the flag**; omitting it restores the full listing.

`doctor` remains the single permitted, disclosed residual (upstream harness
limitation, previously ruled as-is).

**KC8 and KC9 restate to match R1**: the *measured* claims are floor/door vs
native. Curated appears in the demo as the product moment, not the measurement
moment. Possible consequence flagged by the founder and accepted: we are not
measuring against curated at all.

### R3. KC3 — closed. Cite, do not reopen

The orchestrator flagged that KC3's wording ("against its own same-harness
placebo") reads against the **doorless** floor, versus which the product floor
is **+515 tokens higher**, while the −28.9% is against native. **Founder ruling:
KC3 is closed. Cite the #6 / F7 record; do not restate the baseline.**

A5d (product-floor renders "0 standing" while its door costs a measured +515)
therefore stays informational.

### R4. Codex deferred — corrections land, the flip is held

**Codex is unavailable**, so nothing can be re-probed, no guard can be verified
against the real thing, and the mechanism cannot be redesigned. The flip's only
benefit is enabling `exec` for a harness we cannot currently run, so it buys
nothing today and risks a benchmark recorded under a posture the session never
had.

Land `71c87d5`'s comment/README/test corrections with `execSupport` **staying
`"recipe"`**. **No guard authored** — a guard we cannot exercise against real
codex is a second unverified claim beside the first.

Note: **codex is not on the Arc I gate.** Program 1 is deliberately one harness.
A7 never blocked Arc I.

### R5. A5a / A5b / A5c — do them, no further decision

### R6. #1258 folded in

The "Gaia Registry" branding audit is the **last open Program 7 issue** and the
only Arc I gate item outside Lane A. Scoping pass dispatched.

---

## Arc I remainder — CORRECTED, 2026-07-30

The orchestrator reported in Session 8H that Program 7 looked unstarted. **That
was wrong** — it searched `gaia-skill-tree` for `docs/ecosystem/`, but #1339
ruled the ecosystem page **canonical on Gaia Research with a pointer from the
Tree**. It landed as `gaia-research` PR #130; `gaia-skill-tree` #1371 added the
pointer. The local `gaia-research` checkout was stale.

Verified state of the three Arc I gate conditions:

| Gate condition | Owner | State |
|---|---|---|
| KC1–KC9 pass | Program 1 | **The real remainder** — see below |
| No shipped surface unreachable from its homepage | Program 7 | #1130, #1328, #1339, #1341 all **closed**. **#1258 open** |
| First-time reader can describe the five planes | Program 7 | #1339 **closed** (gaia-research #130) |

Program 2's Arc I share is **complete** and was verified from the files, not
assumed: six namespaces live across the two ratified HQs — `gaia-research` holds
core + `gaia.brand` + `gaia.heaven` + `gaia.mcp` + `gaia.research`;
`gaia-skill-tree` holds `gaia.skills` (10 terms, in `scripts/lexicon/lexicon.json`)
+ `gaia.trust` (7 terms). #1337 and #1338 closed. The Program 2 → Program 4
unblock is in place: `gaia_search` / `gaia_inspect` / `gaia_status` are all
`banned` → `search_skills`, making D4 enforceable. #1302 is Arc II/III by the
roadmap's own scoping, not an Arc I blocker.

**So Arc I = Program 1's kill criteria + #1258.**

---

## A. In scope — must land in the finalizing PR

### A1. KC5 re-run against the widened door — NOT DONE, highest priority

PR #17 verified zero shared-state mutation (P3) and closed issue #11. It ran
**before** #18 widened `LAUNCHABLE_POSTURES` from `["native"]` to
`["native","curated","product-floor"]`.

The curated route carries an `fsPlan` that writes
`heaven-set/.claude-plugin/plugin.json` and copies each selected skill into
`$SESSION/heaven-set/skills/<id>`. **A criterion about not mutating shared
state was verified against a composition that could not write anything, and
the door was then widened to one that writes a directory tree.** Issue #11 is
marked closed and the guarantee has not been re-established.

Flagged in the Session 8F compaction as "this sprint's remainder, not a
follow-up." Still true.

### A2. Codex `execSupport` — premise HELD, work authored, **DELIBERATELY UNMERGED**

Branch `dev/a2-codex-execsupport`, commit `71c87d5`. **Not merged into the
integration branch.** Orchestrator call — see A7 for why.

The premise held, and it was verified properly rather than assumed: on
`codex-cli 0.145.0`, `-c 'skills.config=[{path="<abs>",enabled=false}]'` moved
the listing **74 → 73 entries, exactly the targeted fixture skill, zero others
changed**, byte-identical across 2 reps. That is a positive result, not a
"flag parsed" negative control. Real `~/.codex/config.toml` sha256 unchanged
before/after; probe ran against an isolated `$CODEX_HOME`.

The comment/README/test corrections in that commit are good and should land.
The `execSupport: "recipe"` → `"exec"` flip itself is what is held.



`packages/core/src/compile.ts` `compileCodex()` returns `execSupport: "recipe"`,
and the comment above it says codex *"stays a recipe unless the per-session
`-c` scoping cell resolves."* It resolved:
`-c 'skills.config=[{path="<abs>",enabled=false}]'` confirmed on codex
**0.145.0**, 2/2 byte-identical, recorded in `gaia-research` #133 (merged).
`compile()` currently describes codex less capably than codex is.

Agent is briefed to **verify the premise before changing anything** and to stop
and report if its own check contradicts the matrix.

### A3. KC2's silent branch — CONFIRMED FALSE, correction now mandatory

No longer conditional. KC4's probe settled it.

`statusline.ts` `scopeCaveat()` and `render-posture.mjs` `scopeNote()` emit
**no** exclusion disclosure when `scope === "session"` (curated /
product-floor), reasoning that the profile *is* the session set and saw all of
it. That rested on "zero listing residual observed on the T9 route" — a code
comment, not a measurement. **The measurement now says otherwise.** Both silent
branches are proven false claims and must gain a caveat.

### A4. Issue closure + Arc I ledger

Close on the integration merge: **#8** (KC1), **#9** (KC2), **#10** (KC4),
**#12** (KC6), **#13** (KC9 **and** KC8 — that issue carries two criteria,
confirmed by reading its body). **#7** (KC7) and **#11** (KC5) already closed —
but see A1 before trusting #11.

Also owed, per R1/R2: **#13's body must be restated** so KC8/KC9 measure
floor/door vs native and curated is the product moment rather than a measured
arm. And `gaia-skill-tree` **#1258** closes on the Program 7 side.

### A5. Read-only review findings (KC1 + KC2) — all orchestrator-verified

Review ran green on the merged tip: 180/180 tests, typecheck clean, reviewer-run.
It confirmed the KC1↔KC2 merge on `render-posture.mjs` lost nothing, the
cross-renderer parity test is real rather than decorative, no banned vocabulary
entered, and the `plugin.json`/`marketplace.json` copy edits corrected a genuine
overclaim rather than introducing one.

Four findings, ranked. **A5a is the one that keeps KC1 from being fully closed.**

**A5a (Medium) — `verify-marketplace-install.mjs` never reads
`marketplace.json`.** It hardcodes `PLUGIN_SRC = join(PKG_ROOT, "plugin")` at
line 33 while its own header comment (line 5) says the path comes from the
manifest's `source` field. Orchestrator-verified: `grep -an "marketplace.json"`
matches **only inside a comment.** So the check proves *"the current `plugin/`
layout is self-contained and runs standalone"* — **not** *"the marketplace
manifest routes an installer here."* If `source` ever drifts (typo, path move,
a second plugin entry), the check keeps copying the correct hand-picked
directory and passes green while a real install breaks. Fix: derive the path
from the manifest instead of asserting it twice independently.

**A5b (Low-Medium) — the `realpathSync` fix was never dogfooded, and the
verifier carries the same class of bug it was written to catch.**
`verify-marketplace-install.mjs:160` still guards with
``import.meta.url === `file://${process.argv[1]}` `` — no `pathToFileURL`, no
`realpath`, weaker than even the pre-fix idiom in `render-posture.mjs`.
Orchestrator-verified. Separately, the reviewer reproduced a real crash: on
`import()` (not direct invocation) with a non-existent `process.argv[1]`,
`realpathSync` throws `ENOENT` uncaught where the old code silently evaluated
`false`. Not live-breaking today — no current consumer hits it — but it turned a
silent no-op into an uncaught throw with no test covering either direction.

**A5c (Low, structural) — the KC2 disclosure fails OPEN, not closed.** Both
`statusline.ts:60` and `render-posture.mjs:435` are allowlists:
`scope === "user+project" ? caveat : nothing`. `ProfileManifest.scope` is typed
plain `string`, so **any future third scope renders with no exclusion caveat by
default** — the optimistic direction. This contradicts the fail-closed
discipline the same file states for `readGatedLevels` / `readLaunchablePostures`.
Harmless today (exactly two producers, and `census.test.ts` pins the literal so
a rename trips), but a new scope value would trip nothing.

**A5d (Informational, not a defect) — `product-floor` renders "0 standing"
while the door it mounts costs a measured +515 tok** (F7: 20,176 vs 19,661).
`doseSummary()` sums `skills[]` only, and `product-floor` always launches with
none. Consistent with the README's explicit skills-only definition of "standing"
at every posture, so not overclaiming — but a real evidenced number a user
cannot discover from the runtime surface. Maintainer decision, not a bug.

---

## A6. ~~FOUNDER DECISION REQUIRED~~ — **RULED, see R1/R2.** KC4 stands; the composition changes to empty `--setting-sources`. Original finding preserved below.

**KC4 fails as composed.** Verified independently by the orchestrator: the
committed probe was re-run a third time on `claude 2.1.220`, byte-identical to
the worker's two runs.

```
S1 curated, project marker planted:
   ["kc4-project-marker","heaven-set:kc4-curated-marker","doctor"]
S2 curated, clean project:
   ["heaven-set:kc4-curated-marker","doctor"]
```

Two independent leaks:

1. **Project-scope skills survive.** `--setting-sources project` *keeps*
   project scope — that is the flag's documented behaviour, not a bug. S1 vs S2
   isolates it causally with a planted marker; S3 (same plugin-dir mount, flag
   removed) shows the full ~68-entry listing return, so the flag is doing real
   narrowing work.
2. **`doctor` survives `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1`.** Comparing S2
   against the native baseline S4, the env var suppresses every other bundled
   skill and not that one. A harness limitation, not ours to fix.

Clean result: `system:init`'s `plugins` array showed only `heaven-set` — **no
marketplace-plugin skill leakage.**

The decision is not an agent's to make. P1 says curated is *"a hand-gated few,
source-agnostic, the user's own skills first"* — under which **project-scope
survival may be intended**, and the criterion's wording is what is wrong. The
`doctor` leak is upstream regardless. Options are: restate the criterion,
change the composition, or accept and disclose. Founder call.

---

## A7. ~~FOUNDER DECISION REQUIRED~~ — **RULED, see R4.** Corrections land, flip held, no guard, codex deferred. Original finding preserved below.

Surfaced by A2's probe, verified independently by the orchestrator. This is
the same shape as KC4, one harness over.

`compileCodex`'s note claims *"`$CODEX_HOME` scoping gives an empty skills
surface (floor)"*. **It does not.** Codex reads skill roots that
`$CODEX_HOME` does not govern — `.agents/skills` (repo), `~/.agents/skills`
(user), `/etc/codex/skills`, and bundled system skills. A2's probe saw **74
skills from a fresh, `config.toml`-less `$CODEX_HOME`**, the majority from
`~/.agents/skills`. Orchestrator confirmed directly: `~/.agents/skills` exists
on this machine with **70 entries**, and `/etc/codex/skills` is absent.

**Why the flip is held rather than merged.** This gap was *inert* while
`execSupport` was `"recipe"` — a recipe is printed, never spawned:

- `packages/core/src/exec.ts:43` refuses to run unless `execSupport === "exec"`.
- `packages/core/src/cli.ts:169` prints a recipe instead of running.

Flipping to `"exec"` removes exactly that refusal. The core bin is **the
research driver** (N9), so the flip would let it spawn a codex "floor" that is
actually near-native — and record a benchmark number under a posture label
the session never had. Corrupting a measurement is worse than lacking one.

The flip is *correct in isolation* and *unsafe in composition*. Options:
land the comment/README/test corrections and hold the flip until the codex
floor mechanism actually evicts; land the flip with a guard that refuses codex
floor/curated until then; or redesign the codex mechanism first. Founder call.

Note the agent did **not** silently fix or silently ship past this — it
documented the caveat in code and README and reported it. That is the correct
behaviour and worth preserving.

---

## B. Acknowledged by the founder, explicitly NOT this sprint

- **Statusline falls back to command UI.** Fine for now; worth a UI pass after
  MVP drops.
- **Marketplace-only install ships the command only** — no launcher, no
  statusline. A plugin's own settings support only `agent` and
  `subagentStatusLine`; wiring the main session statusline needs a `--settings`
  file written before session start, which only the launcher does. Pre-existing
  boundary, documented in the README before this sprint.
- **`version: "0.0.0"` removed** from `plugin.json` + `marketplace.json` so
  Claude Code falls back to git-SHA versioning. Packaging policy call.

---

## C. EXCLUDED — founder ruling, 2026-07-29: "handle another time"

Recorded so it is not silently lost, and explicitly **not** Arc I work.

- Census scope widening to bundled + plugin-provided skills. KC2 required
  *disclosing* the boundary, not moving it.
- Lexicon gate extension to `skill-heaven`. Belongs to
  `integration/lexicon-heaven` / gaia-research #134.
- `scripts/lexicon/check-lexicon.ts` reads as `data` to `file(1)`, so plain
  `grep` silently returns zero matches with no warning. Cost this session two
  wrong conclusions. Use `grep -a`. gaia-research repo.
- Harness matrix row 38 (codex M2a prompt-control flags) — third
  quota-deferred cell.

---

## D. Standing constraints for the finalizing PR

- **Nothing merges to `main` without the founder.**
- CI is a **signal** on the integration branch; green is required only at
  integration → `main`.
- `skill-heaven` **requires squash** on merge. `gaia-skill-tree` and
  `gaia-research` **forbid** it (merge commits).
- Never cite a test count not personally run.
- Probe hygiene: snapshot the starting state before the first run; **never
  delete artifacts to tidy up.**
