# ARC I — The Door · Builder Handover

**Status:** Active · **Opened:** 2026-07-28 · **Authority:** `founder/GAIA_ROADMAP v5 (BUILD).md` (ratified 2026-07-28)

**Who reads this:** every builder/worker agent dispatched against Arc I, in any Gaia repo. Read the whole thing once before your first edit, then work only your lane.

---

## 0. What Arc I is

Arc I is called **The Door**. Its thesis: Skill Heaven should be able to show, honestly and reproducibly, that it controls what enters a session — and anyone who lands on a Gaia page should be able to understand what they are looking at.

Arc I is **three independent lanes**. They do not block each other. There is exactly **one** cross-lane dependency in the whole arc, named in §5.

> ⚠️ **CONCURRENCY CAP — founder ruling, 2026-07-29.** Lane independence describes the *work*, not the *dispatch*. Implementation concurrency is capped at **1 orchestrator + 2 workers**, permanently. Running seven agents at once exhausted the account session limit and killed five of them mid-flight — the work survived only because each was swept for unpushed commits afterward. Sequence the lanes; do not fan them out. Where this section and §7 say to run lanes in parallel, they mean *in any order*, not *at the same time*.

| Lane | Program | Repo(s) | Tracking |
|---|---|---|---|
| **A — Skill Heaven** | 1 | `gaia-research/skill-heaven` | issues **#5–#13**, milestone #1 |
| **B — Lexicon** | 2 | `gaia-research`, `gaia-skill-tree` | Program 2 milestone in HQ |
| **C — Adoption** | 7 | `gaia-research`, `gaia-skill-tree`, `skill-heaven` | Program 7 milestone in HQ |

**Not in Arc I:** Program 3 (Arc II), Program 4 (Arc III — and blocked, see §5), Program 5 (background maintenance lane, its own orchestrator), Program 6 (continuous cadence).

---

## 1. Worktree rules — READ BEFORE EDITING ANY FILE

If you are running with `isolation: "worktree"`, your working directory is a **separate checkout**. That means:

1. Your edits are **not visible** to the parent session until pushed.
2. **Branch from origin** — `git checkout -b <branch> origin/<base>`, never from a local base ref, which may be stale.
3. **Commit and push after each logical unit.** Never batch. A pushed commit survives a cutoff; a local commit dies with the worktree.
4. **Push to `origin/<your-branch>`.** The worktree gets a synthetic branch on creation — always create and check out your real feature branch first.
5. **Branch scope is CI-enforced** in `gaia-skill-tree`. `design/*` → `docs/` + `*.md`; `cli/*` → `src/`, `tests/`, `packages/`, `*.md`; `schema/*` → `registry/schema/` + `src/gaia_cli/data/registry/schema/` + `*.md`; `docs/*` → `docs/` + `*.md`; `infra/*` → `.github/`, `scripts/`, `docs/*.html`, `docs/badges/`, `*.md`. Do not cross lanes.
6. **Do not commit regenerated artifacts as side effects.** If you run something that rewrites `docs/graph/*` or `registry/gaia.json` with timestamp-only diffs, `git restore` them before committing.
7. **Report each commit's SHA and push status as you go**, not in a final summary.
8. **If you hit ~80k tokens before finishing, commit what you have, push, and report.** Do not try to fit the rest into one dispatch.
9. **Commit identity.** Worktrees and fresh clones inherit whatever global git identity the machine carries. Set repo-local `user.name`/`user.email` to the approved project identity before your first commit, and check `git log --format='%an <%ae>'` before pushing.

**Never push directly to `main`, in any repo.**

---

## 2. Federation Invariants — mandatory in every PR body

Ratified V5-10. Every non-trivial PR in **any** Gaia repo carries this block:

```markdown
## Federation notes

- **Contracts touched:** [which versioned contracts this reads or writes, or "none"]
- **Cross-repo effect:** [what another plane must do, or "none"]
- **Evidence:** [benchmark record / matrix cell / "no public claim made"]
```

The standing rules behind it:

1. **No plane imports another plane's source.** Vendor small pure pieces; prove parity by fixture (D6).
2. **Every cross-plane read goes through a versioned contract.** Never read another repo's internals.
3. **No claim ships ahead of its benchmark** (B4). A "will not work" record is as first-class as a "will work" one.
4. **Ratification and implementation land in the same PR cycle** (D9). A PR citing a retired decision id is a defect.
5. **Doses are priced separately, never as one number** (B1).
6. **Canon is read-only from outside** (G1).
7. **One term, one owner.** Redefining a term another namespace owns is a CI failure.
8. **Class P / Class S is unchanged.** If a browser fetches it at runtime it is Class S and belongs in git; if only tooling reads it, Class P and gitignored.

---

## 3. The lanes

### Lane A — Skill Heaven (Program 1)

**Repo:** `gaia-research/skill-heaven` · **Issues:** #5–#13 · **Tests today:** **64 on `origin/main`** (75 on the `feat/p1-floor-split` branch)

> ⚠️ **Corrected 2026-07-28.** This line previously read "95/95 green." That number was wrong. **Measure the baseline yourself before claiming your branch keeps tests green** — a wrong baseline makes every later "still green" claim unverifiable.

The demonstration, in order: native session dose honestly scoped → a visible session posture → a manually curated lower-dose launch → trusted capability discovery → one safe summon path → a measured before/after result.

**Start here, in this order:**

1. **#6 — the floor split.** Ratified V5-5. The **benchmark floor stays completely doorless** — it is the placebo-of-record (B2). A separate **doorful product floor** ships, retaining the minimum control surface. The two are measured and named separately and priced as **separate arms** (B1) — never averaged. Evidence already in hand: PR #4's finding **F6** (`--disable-slash-commands` at the T9b floor suppresses plugin commands too, so `/skill-heaven` does not exist at the ratified floor — "the clean room as currently composed has no door") and **F7** (the door costs **+515 tokens**: 20,176 vs T9b's 19,661, still −28.9% off native's 28,379). Consequence: the `floor` term in `gaia-research/founder/lexicon.json` currently instructs readers not to assume one term covers both floors — once this lands, **split it into two terms**.
2. **#5 — re-cut PR #4.** Ratified V5-6. The PR binds itself to "D12, **D13**, P2, P3, D6". **D13 is retired** — it is on `gaia-research/founder/RATIFICATION.md`'s never-reused list, deleted 2026-07-24. Re-bind to live decisions, drop D13, absorb #6's floor split, and land the ratification delta **in the same PR cycle** (D9). This is a governance defect, not a code defect — the tests are green.
3. **#7 — complete `/skill-heaven` (N8).** Closes ledger OPEN 10. Four uncovered scenarios: posture adjustment, capability discovery, clean-room access, refusal transparency. It **explains** posture and available transitions; it must never imply an in-session subtraction the harness cannot perform (D12).
4. **#9 — honest standing-dose scope.** PR #3's unresolved item: the census covers **user + project only**; bundled and plugin-provided skills are excluded. Confirm the scope and disclose the exclusion on every surface that reports the number, *before* it anchors any public "native = Nk" claim.
5. **#8, #10, #11, #12** — packaging, zero listing residual, zero shared-state mutation, honest refusal.
6. **#13 — the three-minute demo.** This is the arc's gate artifact.

**Kill criteria KC1–KC9** are quoted verbatim on the individual issues. Do not paraphrase them into a PR — cite them.

**Hell stays visibly locked (P2)** throughout. Do not build it, do not describe it as available.

### Lane B — Lexicon (Program 2)

**Repos:** `gaia-research` and `gaia-skill-tree` only.

**What already exists — do not rebuild it.** `gaia-research/founder/lexicon.json` on `main` is live: 51 terms, schema 1, namespace `core`, 29 `canonical` / 13 `parked` / 9 `banned`. `founder/LEXICON.md` is generated from it (`npx tsx scripts/lexicon/check-lexicon.ts --emit`) and **must not be hand-edited**. `.github/workflows/lexicon-ci.yml` **already runs green** — 19 self-test assertions, 8 fixtures, then the vocabulary gate. This lane is a **restructure of a working system**.

**Two tasks:**

1. **Migrate flat `core` into the six ratified namespaces**, across **two HQs**:

   | Repo | Owns |
   |---|---|
   | `gaia-research` | `core` · `gaia.research` · `gaia.brand` · `gaia.heaven` · `gaia.mcp` |
   | `gaia-skill-tree` | `gaia.skills` · `gaia.trust` |

   `skill-heaven` and `gaia-mcp` hold **no** namespace files — they consume. **`gaia.registry` is rejected; the namespace is `gaia.skills`.** That is the same ruling as #1258 ("Gaia Registry" is not the product name). Extend, never redefine: a term is defined in exactly one file, ever. Extend the CI gate to the second HQ.

2. **Record the prototype MCP tool names as `banned` vocabulary intent.** `summon` is `canonical` with oracle **D4**, and its definition names `search_skills` as its partner tool. Add `gaia_search`, `gaia_inspect`, `gaia_status` as `banned` with `replacement: search_skills` and an oracle citation, in `gaia.mcp`. Small; do it early. **Landed in `gaia-research` PR #126.**

   ⚠️ **But see §5.** Those three names are **published and live** on `@gaia-research/mcp` v0.1.0. The lexicon entry records **intent**; it does **not** authorize renaming the shipped surface. Final tool names are **OPEN** under roadmap **V5-19**.

**Out of scope for Arc I:** #1302's authority hierarchy (Arc II/III).

### Lane C — Adoption (Program 7)

**Repos:** all three public ones.

1. **The ecosystem About surface.** Ratified V5-11 and V5-15. **Canonical on Gaia Research**, with a prominent **pointer** from `gaiaskilltree.com`. It answers, for a first-time reader: What is Gaia? What are these things and why are they separate? Which one do I want right now? What changed?

   **Two hard constraints.** *(a)* It tells the **four-name story — Tree · Heaven · Hell · Research** — and **never names a repo or an npm package**, because the package topology (V5-4) is deliberately open and must be free to move without rewriting the page. *(b)* It must not become a competing north-star doc: **it owns the relationships**; each line doc keeps its own thesis and is **linked, never restated**. `VISION.md`/`MISSION.md` stay Skill Heaven's line docs. `docs/about.html` stays the founder-story page at its current path.

2. **Adoption paths**, one per plane, each ending in something a reader can do, each labelled with its **true state** — shipped, prototype, or gated. A false path costs more trust than a missing one. This is B4 applied to product surfaces. Note: this is *not* a revival of the retired `docs/archive/ADOPTION.html`, which was deleted precisely because nothing linked to it.

3. **A standing, versioned What Changed surface** (V5-16) covering Yggdrasil II and v5 — dated, linked from About, stating what a returning reader must relearn.

4. **The four proven surface breaks** — fix only these in Arc I:
   - **#1130** — re-enable the Latest Weekly Report and Benchmarks Leaderboard entrypoints in `docs/index.html`. Their blocking condition (EPIC #1002) closed. Both surfaces exist and render at `docs/reports/2026-28/` and `docs/benchmarks/{humaneval,mmlu}/`. **Do this first — it is the cheapest credibility win in the arc.**
   - **`skill-heaven/README.md` lines 26–27** — the Vision and Mission badges point at `gaia-research` repo-root `VISION.md`/`MISSION.md`, which **404**. The files live at `docs/skill-heaven/VISION.md` and `docs/skill-heaven/MISSION.md`.
   - **#1328** — 14 stale `@gaia-registry/mcp-server` refs in `docs/en/mcp-server.html`. **No active surface may present an unpublished package as installable.**
   - **#1258** — the "Gaia Registry" branding audit. Same ruling as Lane B's `gaia.skills` rename; coordinate the copy.

   The **full** canonical / pointer / retired classification audit is a **background lane**, explicitly not an Arc I blocker (V5-17).

**Design Entrypoints applies.** Any new user-facing page must plan its entrypoints during design — nav, footer, homepage, `window.GAIA_MOUNTS`, cross-page links, cache-busting — and the PR body must carry an **Entrypoints** section. CI Guard D enforces `mounts.js` registration. Fixed-nav clearance: base **5rem**, desktop **6rem** (thin strips) or **8rem** (full page shells). No other values.

---

## 4. What is deliberately NOT decided

**V5-4 — the plane count and package topology is OPEN by founder ruling.** The founder leans toward four names (Tree · Heaven · Hell · Research) with Skill Heaven as one package containing MCP and Skill Hell. Program 4's destination — standalone `gaia-mcp` versus folded into the Heaven package — is likewise open.

**Do not close this by implication.** If your work would only make sense under one topology, stop and say so rather than picking one. Lane C's constraint against naming repos and packages exists precisely to keep this open at zero cost.

**Enterprise is not discussed publicly** (V5-9). Skill Hell is described only as a gated Heaven tier. Do not write enterprise copy, do not describe an enterprise path.

---

## 5. The one cross-lane dependency

> **Lane B records the prototype MCP tool names as `banned` vocabulary intent before Program 4 writes its first tool definition.**

> ## ⚠️ CORRECTED 2026-07-28 — READ THIS, THE ORIGINAL PREMISE WAS FALSE
>
> This section previously said the ordering was "available exactly once, **because nothing is published yet**." **That is wrong.**
>
> **`@gaia-research/mcp` v0.1.0 was published to npm on 2026-07-16**, and its README documents `gaia_search`, `gaia_inspect`, and `gaia_status`. The stale `@gaia-registry/mcp-server` references on our own docs were stale because of a **RENAME**, not because nothing shipped. See roadmap **V5-18**.
>
> **What this changes:** recording those names as `banned` is **vocabulary intent** and is fine. **Renaming the published tool surface is a breaking change to a live public interface** and is **NOT** authorized by the lexicon entry. Roadmap **V5-19** rules the final tool names **OPEN** — neither D4's `search_skills`/`summon` nor the shipped trio is final.
>
> **Do not treat Lane B's work as licence to change the published server.** Do not write copy claiming the package is unpublished — it is not.

Program 4 is Arc III, so this does not block Arc I. Lane B's task 2 is still small and still worth landing early — it captures the intent while it is cheap. What it no longer buys is a free rename.

Everything else in Arc I runs in parallel.

---

## 6. The Arc I gate

Arc I closes when all three hold:

- Skill Heaven v0.1 kill criteria **KC1–KC9** pass
- **No shipped Gaia surface is unreachable from its own homepage**
- A first-time reader can land on **one page** and correctly describe what the planes are and which one they want

---

## 7. Model routing

| Work | Model |
|---|---|
| Contract schemas, HH methodology, routing determinism, floor-vs-floor ratification | Opus, max effort |
| Lexicon migration, projection work, MCP profiles | Opus, high |
| Docs, link migrations, test additions, CI YAML | Sonnet |
| Dependency bumps, mechanical renames | Haiku, with a schema |

---

## 8. Hard boundaries — these do not bend

- Never push to `main` in any repo.
- All registry mutations go through `gaia dev` CLI verbs. Never hand-edit `registry/nodes/`.
- **Never fabricate a timeline event.** If `gaia dev timeline` cannot write it, leave it out, note the CLI gap in the PR, and file a follow-up. A missing entry is auditable; a synthetic one is not.
- Class P stays gitignored; Class S (`docs/graph/*`) stays tracked. If a browser fetches it, it belongs in git.
- Auto-sync never touches `docs/badges/`.
- The eight redaction-exempt contributor handles are permanent — do not remove them, do not file issues about them.
- Design tokens only. No hex color fallbacks — CI rejects them.
- Do not commit binary masters. Optimized `.webp` and native SVG only.

---

*Authority: `founder/GAIA_ROADMAP v5 (BUILD).md` §5 (programs), §6 (arcs), §7 (Federation Invariants), §10 (decision log). Repo rules: `CLAUDE.md`, `founder/CLAUDE.md`. Where this handover and the roadmap disagree, the roadmap wins — and tell the orchestrator.*
