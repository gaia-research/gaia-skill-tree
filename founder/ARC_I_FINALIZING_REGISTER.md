# Arc I — finalizing register

Everything that must land before `integration/arc-i-lane-a` (in
`gaia-research/skill-heaven`) merges to `main`.

Founder instruction, 2026-07-29: collect the in-scope remainder and tackle it
together as a **finalizing PR on the integration branch** — not as follow-up
issues. This is the sprint's own work, per CLAUDE.md § Sprint Completeness.

Status at time of writing: Session 8G. Integration tip `bec8dbd`, suite
**180 passing** (orchestrator-run, not reported).

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

### A2. Codex `execSupport: "recipe"` is stale — IN FLIGHT (Sonnet, 8G)

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

### A5. Open placeholder — findings from work still in flight

KC6 (honest refusal) and the read-only review of KC1/KC2 were still running.
Their findings land here.

---

## A6. FOUNDER DECISION REQUIRED — KC4 cannot be closed as written

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
