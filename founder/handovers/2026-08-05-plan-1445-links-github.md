# Plan — Issue #1445: 22 skills with `links.github` pointing at a non-skill directory

**Status:** draft plan, awaiting founder ratification. No code, registry, or doc changes made.
**Author:** planning agent, 2026-08-05.
**Inputs:** issue #1445 + its research comment (per-skill table, 22 rows); sibling issue #1441; `scripts/install_parity.py`; `src/gaia_cli/install.py`; `src/gaia_cli/commands/dev/{named.py,helpers.py}`; `docs/agents/curation-guidelines.md`; `docs/agents/install-parity.md`; CONTRIBUTING.md §12; `.claude/skills/gaia-audit/SKILL.md`.

---

## 0. Executive summary — the research table needs three corrections before it is executable

The existing research comment on #1445 is good field work and its per-skill upstream findings are reused wholesale below. But three of its conclusions do not survive contact with `_parse_github_url` / `_install_single`, and a plan built directly on it would ship a PR that changes ~10 links and fixes **zero** parity failures.

### C1 — `blob/main/README.md` fallbacks are a no-op, not a fix

`_parse_github_url` (`src/gaia_cli/install.py` L90-99) takes `os.path.dirname(path)` when the blob path ends in `.md`:

```
https://github.com/browserbase/stagehand/blob/main/README.md   ->  subpath = ""   (repo root)
https://github.com/owner/repo                                   ->  subpath = ""   (repo root)
```

Both resolve to the **same** symlink target. The 9 rows the research proposes to "fix" with a `README.md` fallback would still fail `NO_SKILL_MD` on the very next sweep, having consumed a curation PR and a timeline event each. **Recommendation: ban `README.md` as a relink target outright.** A skill with no SKILL.md-bearing directory upstream is an `installable: false` decision, not a link decision.

### C2 — the suite-component "false positive" is a real defect, and it is 8 skills, not 3

The research flags the `disler/*` trio as an `install_parity.py` false positive. Verified against the registry and the installer, it is not:

- **8 of the 22 are suite components**, not 3 — `disler/{auto-review,opinion,plan-synthesis}` (`suiteRef: disler/agent-fusion`, 2★) **and** `gsd-build/{discuss-phase,execute-phase,plan-phase,ship,verify-work}` (`suiteRef: gsd-build/get-shit-done`, 3★). Both parent suites exist in the registry with matching `suiteComponents` arrays. (The research's claim that `disler/agent-fusion` "does not exist" is true of GitHub, false of the registry.)
- `install_suite` installs each component through `_install_single`, which symlinks `cache/<subpath>` into `.agents/skills/<slug>`. For the disler trio, `dirname()` of all three `.md` links is the **same** directory — `extensions/fusion-harness/` — so three registry slugs symlink one directory, three times, under three names, and that directory has no `SKILL.md`. No agent harness can discover any of them.
- Curation guideline **#3** exempts *suites* (the parent, which needs no `links.github`). Guideline **#4** explicitly requires *components* to carry a `blob/branch/subpath` pointing at their actual skill directory. Teaching the checker to skip components would suppress precisely the defect guideline #4 exists to catch.

**Recommendation: do not add a `suiteRef`/`suiteComponents` exemption to `NO_SKILL_MD`.** See §4 for the narrower change worth making instead.

### C3 — `installable: false` is star-gated, and 8 of the candidates are 3★+

CONTRIBUTING.md §12: `installable: false` is available at **0★–2★**. At **3★+** it is *not allowed* — the skill must be demoted first. `.claude/skills/gaia-audit/SKILL.md` is harsher still: 3★+ with no working blob URL is a **hard reset to 1★/awakened**, not a soft step-down. Affected: `stanfordnlp/dspy` (4★), `safishamsi/graphify` (4★), `panniantong/agent-reach` (3★), and the five 3★ `gsd-build/*`. Writing `--installable false` on any of them creates a state that contradicts §12 — exactly the class of "CLI shipped a state that fails the invariant" the CLI Pre-Flight Rule forbids.

Related live drift worth noting: CONTRIBUTING.md §12's exempt table **already lists** `stanfordnlp/dspy` and `pexp13/sentiment-analysis` as registry-only, while `dspy`'s frontmatter today reads `level: 4★, installable: true` — and its own timeline carries a 2026-06-02 `demote` event reading *"No installable code available (research framework); marked installable: false."* The flag was flipped back at some point. This plan does not silently re-litigate that; see Q2.

### Net effect on the 22

Exactly **one** of the 22 (`bradautomates/claude-video`) is a clean relink that actually clears parity. The other 21 are policy decisions, contributor-blocked, or upstream-blocked. That is the honest shape of this issue and the plan is sized to it.

---

## 1. Grouping and sequencing

Star level, status, and `suiteRef` below are read from live frontmatter, not from the issue.

### Group A — clean relink, clears parity (1 skill)

| Skill | ★ | New `links.github` | Resolves to |
|---|---|---|---|
| `bradautomates/claude-video` | 2★ | `https://github.com/bradautomates/claude-video/blob/main/skills/watch/SKILL.md` | `skills/watch/` — contains SKILL.md ✅ |

Safe to batch. This is the only row where a link change alone turns the check green.

### Group B — suite components, upstream has no SKILL.md-bearing dir (8 skills)

| Skill | ★ | suiteRef | Action |
|---|---|---|---|
| `disler/auto-review` | 2★ | `disler/agent-fusion` | hold — see Q1 |
| `disler/opinion` | 2★ | `disler/agent-fusion` | hold — see Q1 |
| `disler/plan-synthesis` | 2★ | `disler/agent-fusion` | hold — see Q1 |
| `gsd-build/discuss-phase` | 3★ | `gsd-build/get-shit-done` | relink to successor (necessary, not sufficient) |
| `gsd-build/execute-phase` | 3★ | " | " |
| `gsd-build/plan-phase` | 3★ | " | " |
| `gsd-build/ship` | 3★ | " | " |
| `gsd-build/verify-work` | 3★ | " | " |

The `gsd-build/*` relink to `open-gsd/gsd-core@next` is worth doing on its own merits — the current upstream `gsd-build/get-shit-done` was **archived 2026-06-26**, so the links are pointing at a dead repo. But #1441's own sweep confirms `commands/gsd` has no `SKILL.md`, and the successor carries the same relative layout, so **parity stays red after the relink**. Land the relink as link hygiene; do not claim it closes these five.

### Group C — no upstream SKILL.md, ≤2★, `installable: false` is available (6 skills)

| Skill | ★ | Status |
|---|---|---|
| `browserbase/stagehand` | 1★ | named |
| `getagentseal/codeburn` | 2★ | named |
| `laravel/upgrade-laravel-v13` | 2★ | named — current link is a GitHub **issue thread**, never a file |
| `nousresearch/feed-monitoring` | 2★ | named |
| `pexp13/sentiment-analysis` | 1★ | awakened — already in CONTRIBUTING §12's exempt table |
| `upsonic/unittest-generator` | 2★ | named |

Safe to batch. `--installable false` pops the whole `links` block automatically (`named.py` L102-103), so no separate link edit is needed and no `preflightGithubLink` runs.

### Group D — 3★+ with no installable source; demotion required first (3 skills)

| Skill | ★ | Note |
|---|---|---|
| `panniantong/agent-reach` | 3★ | skill guide is generated into the agent dir at install time; nothing static upstream |
| `safishamsi/graphify` | 4★ | `NOT_A_SKILL_DIR` — links at `graphify/__init__.py`; skill files generated at install time |
| `stanfordnlp/dspy` | 4★ | `NOT_A_SKILL_DIR` — general ML framework; already listed exempt in CONTRIBUTING §12 |

**Blocked on Q2.** Do not touch these until the founder rules on the demotion ladder.

### Group E — needs contributor confirmation of the real subpath (2 skills)

| Skill | ★ | Blocker |
|---|---|---|
| `gooseworks/notte-browser` | 1★ | registry slug says `gooseworks`, org is `gooseworks-ai`; `goose-skills` is a large catalog with no notte/browser-named dir found |
| `yonatangross/orchestkit-rag` | 1★ | `orchestkit` bundles ~105 skills; none matched "rag" at top level |

Both are 1★, so `installable: false` is available and **reversible** the moment a contributor supplies a subpath. See Q4.

### Group F — self-hosted pair; the proposed relink also does not clear parity (2 skills)

| Skill | ★ | Proposed by research | Why it fails |
|---|---|---|---|
| `gaiabot/repo-docs-before-pr` | 2★ (awakened) | `…/blob/main/registry/named/gaiabot/repo-docs-before-pr.md` | `dirname` → `registry/named/gaiabot/` — **no SKILL.md there**; verified `find registry/named -name SKILL.md` returns nothing repo-wide |
| `rico-favor/implement-with-discernment` | 1★ | `…/blob/main/registry/named/rico-favor/implement-with-discernment.md` | same |

The research is right that the current links are wrong (`gaiabot` points at this repo's bare root; `rico-favor` points at `CLAUDE.md` in an unrelated **fork** of this repo — arguably the worst link in the set). But `registry/named/` is a markdown catalog, not an installable skill tree. Both are ≤2★ → treat as Group C. See Q3.

### Sequencing

1. Group C + F (8 skills, `--installable false`) — no upstream dependency, no ratification needed beyond Q3.
2. Group A (1 relink) — same PR.
3. Group B `gsd-build` relinks (5) — same PR, labelled as hygiene-not-closure.
4. Group D (3) — only after Q2.
5. Group B `disler` (3) — only after Q1.
6. Group E (2) — after Q4, or park with a contributor ping.

---

## 2. Exact command sequence

Branch: `review/meta/1445-links-github` off `origin/main`. All `gaia dev` mutations need Verifier authorization — export `GAIA_OPERATOR_OVERRIDE=1` if the operator is not a 4★ holder (`gaia whoami` to confirm the `via` path first).

`--no-build` on every mutation; one `gaia dev docs` at the end. Running the docs build 14 times is slow and produces interleaved artifact churn.

```bash
git fetch origin && git switch -c review/meta/1445-links-github origin/main
export GAIA_OPERATOR_OVERRIDE=1
gaia whoami   # confirm authorization path before mutating
```

**Step 1 — Group A, the one clean relink**

```bash
gaia dev update-named bradautomates/claude-video \
  --github-link "https://github.com/bradautomates/claude-video/blob/main/skills/watch/SKILL.md" \
  --no-build
```

**Step 2 — Group C + F, registry-only (8 skills, all ≤2★)**

```bash
for s in browserbase/stagehand \
         getagentseal/codeburn \
         laravel/upgrade-laravel-v13 \
         nousresearch/feed-monitoring \
         pexp13/sentiment-analysis \
         upsonic/unittest-generator \
         gaiabot/repo-docs-before-pr \
         rico-favor/implement-with-discernment; do
  gaia dev update-named "$s" --installable false --no-build
done
```

`--installable false` removes the `links` block and logs a `note` timeline event (`"Set installable to false"`). No `--github-link` needed and none should be passed.

**Step 3 — Group B, `gsd-build/*` relink off the archived repo (5 skills, hygiene only)**

```bash
for p in discuss-phase execute-phase plan-phase ship verify-work; do
  gaia dev update-named "gsd-build/$p" \
    --github-link "https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/$p.md" \
    --no-build
done
```

**Precondition (must be verified by the worker, not assumed):** this planning session had no network access to third-party repos. Before running Step 3, confirm `open-gsd/gsd-core@next` exists, is not archived, and carries `commands/gsd/<name>.md` for all five. If the layout differs, stop and report — do not improvise a path.

**Step 4 — regenerate and stage the deterministic artifact set once**

```bash
gaia dev docs
```

Stage only the curation-PR set from CLAUDE.md § "Curation PR — which artifacts to commit":

```bash
git add registry/named/ \
        docs/graph/gaia.json docs/graph/named/index.json docs/graph/gaia.gexf docs/graph/gaia.svg \
        docs/api/v1/ docs/tree.md registry/registry.md
git checkout origin/main -- docs/og/ docs/api/v1/trending/ \
        docs/graph/ledger/data.json docs/experiments/ml-graph-viz/layouts_3d.json docs/okf/
```

**Step 5 — CONTRIBUTING.md §12 exempt table**

Append the newly registry-only skills to the "Skills currently exempt" table in the same commit (it is `*.md`, inside `review/meta/` scope). Leaving the table stale is the drift that produced the `dspy` contradiction in C3.

**Not in this PR, at any point:** `scripts/install_parity.py`, `src/gaia_cli/**`. Both are outside the `review/meta/` branch-scope allowlist (`registry/` excluding schema, plus `docs/`, plus `*.md`) and would trip `branch-scope.yml`. That scope boundary is doing real work here — it is what forces the checker and CLI changes into their own PRs.

---

## 3. `install_parity.py` suite-component change — recommendation: **narrower, and a separate PR**

Per C2, the blanket exemption in the research should **not** be built. What is worth building:

- Keep `NO_SKILL_MD` firing for suite components. The install is genuinely broken for all 8.
- Add `suite_ref` to the `Skill` dataclass (read `suiteRef` from the index entry alongside the existing `suiteComponents` read in `build_skills`, ~L235-262) and surface it in the report line and JSON. Today a triager cannot tell from the output that `gsd-build/ship`'s failure is upstream-packaging-shaped and shared with four siblings; five identical rows read as five independent defects.
- Optionally collapse components of one suite into a single grouped finding in `render()` so the sweep reports "1 suite, 5 components, no SKILL.md upstream" rather than 5 rows.

**Scope: separate PR on an `infra/` branch** (`scripts/` is `infra/` scope), landing on the shared integration branch alongside the curation PR. It is a reporting-ergonomics change, not a correctness change, and bundling it into the curation PR is a branch-scope violation regardless.

---

## 4. `preflightGithubLink()` live-check — recommendation: **separate CLI-hardening PR, and #1441 is the higher-value half**

Current state (`helpers.py` L941-966): shape-only. Rejects non-`github.com`, rejects `/tree/`, requires `/blob/`, requires a full `owner/repo/blob/branch/subpath` match. It would have accepted **every one of the 22 bad links**, including the `laravel` issue-thread URL (`…/boost/issues/698` — wait: that one has no `/blob/`, so it would be rejected today; it predates the preflight) and every `README.md` fallback.

Recommendation, in priority order:

1. **Ship #1441 first.** Validating `source_skill_path` exists / is a dir / contains `SKILL.md` in `_install_single` before `makeLink` is the load-bearing fix: it converts 34 silent successes into honest failures for every user, not just for links written through `gaia dev`. It is also strictly required by the CLI Pre-Flight Rule.
2. **Then extend `preflightGithubLink()`**, in the same CLI PR or a fast-follow, with:
   - an **offline** rule that costs nothing and blocks the largest class seen here: reject a blob path whose `dirname()` is empty (i.e. `README.md`, `LICENSE`, any repo-root file) with the message that it resolves to the repo root — this alone would have blocked 9 of the proposed "fixes" in the research table;
   - an **optional live check** (`GET` the raw URL, plus the sibling `SKILL.md`) behind an opt-out flag (`--no-verify-link`) so bulk and offline runs still work, defaulting to on for interactive use.
3. **Do not** make `install_parity.py` a required CI gate (the research's alternative option 3b). `docs/agents/install-parity.md` is explicit that it is a standalone operator tool, not a CI gate — a full sweep is 40-60 min and ~2 GB of clones, and it depends on third-party repo availability, so it would be a flaky required check gating unrelated PRs.

**Scope: not in this plan's curation PR.** `src/gaia_cli/**` is `cli/` branch scope.

---

## 5. Validation plan

Before opening the curation PR:

```bash
gaia dev validate                          # schema + meta sync
python scripts/build_docs.py --check        # MUST exit 0; warn-only categories may still print
python scripts/validate_timelines.py        # every mutation above appends a timeline event
git diff --stat origin/main...HEAD          # confirm no staging leak; expect registry/named + docs/graph + docs/api + *.md only
```

Then the targeted parity re-run (not the full sweep):

```bash
python scripts/install_parity.py \
  --only bradautomates/claude-video \
  --only browserbase/stagehand --only getagentseal/codeburn \
  --only laravel/upgrade-laravel-v13 --only nousresearch/feed-monitoring \
  --only pexp13/sentiment-analysis --only upsonic/unittest-generator \
  --only gaiabot/repo-docs-before-pr --only rico-favor/implement-with-discernment \
  --json generated-output/parity/1445-after.json
```

**Expected end state — state it in the PR body, do not overclaim:**

- `bradautomates/claude-video` → PASS.
- The 8 `installable: false` skills → they move out of `NO_SKILL_MD` into the `NO_SOURCE` category, where the expected behaviour is a clean non-zero exit with "no source repository link" (`check_no_source`). That is a *pass* for the harness and an honest failure for the user.
- The 5 `gsd-build/*` → still `NO_SKILL_MD`. Expected. Documented, not hidden.
- Groups D and E → untouched, still failing, blocked on Q2/Q4.

So: **22 → 9 resolved, 5 relinked-but-still-red, 8 blocked on ratification.** Any PR body claiming #1445 is closed by this pass is wrong; the issue stays open with the remaining groups checklisted on it.

---

## 6. PR shape — recommendation: **integration branch, three PRs**

Per CLAUDE.md § "Integration branches", multi-PR work does not aim at `main` one PR at a time.

```
integration/1445-install-parity          <- opens the PR against main; founder-gated
├── review/meta/1445-links-github        <- Steps 1-5 above (registry + docs + CONTRIBUTING)
├── infra/1445-parity-suite-reporting    <- §3, suiteRef in the report
└── cli/1441-install-validation          <- §4, _install_single validation + preflight hardening
```

**Why not one PR:** branch-scope makes it structurally impossible. `registry/` + `scripts/` + `src/` cannot coexist on any single allowed prefix, and reaching for `skip-scope-check` to force it is exactly the habit CLAUDE.md says not to form.

**Why not three independent PRs to `main`:** they interlock. The CLI validation change (#1441) will make previously-passing local installs fail for the same skills this curation PR is marking registry-only; landing them out of order produces a window where `gaia install` errors on skills the registry still advertises as installable. The integration branch lets the founder see the whole change and gate the single merge to `main`.

**Sprint completeness:** all three PRs are the same sprint's work. The remaining #1445 groups (D, E, and disler) are *ratification-blocked*, not deferred engineering — they belong on this sprint too and should land on the integration branch as a fourth PR once Q1/Q2/Q4 are answered, rather than being filed as follow-ups.

---

## 7. Open questions for founder ratification

**Q1 — Suite components: honor the failure, or exempt them?** *(the one that matters most)*

The brief for this plan pre-committed to teaching `install_parity.py` about `suiteComponents` so the `disler/*` trio stops being flagged. Verified against the installer, that exemption would suppress a real defect affecting **8** skills, not silence a false positive affecting 3: all three `disler` components symlink the *same* `extensions/fusion-harness/` directory, which has no `SKILL.md`, so none of them are discoverable by any harness — and curation guideline #4 exists specifically to require that components point at a real skill directory.

> **Ruling requested (yes/no): keep `NO_SKILL_MD` firing for suite components, and instead mark the `disler` trio `installable: false` (all 2★, so permitted) until `disler/fusion-harness` ships packaged skill dirs upstream?**
> Answering **no** (i.e. exempt them) is a defensible product call — it says component-level installability is not something the registry promises — but it needs to be made explicitly, because it also retires guideline #4 and should be written into `docs/agents/curation-guidelines.md` in the same pass.

**Q2 — 3★+ skills with no installable source: demote, or carve an exception?** CONTRIBUTING §12 says 3★+ cannot carry `installable: false`; `gaia-audit` says 3★+ with no working blob link is a hard reset to 1★/awakened. Applying that literally demotes `stanfordnlp/dspy` 4★→1★, `safishamsi/graphify` 4★→1★, `panniantong/agent-reach` 3★→1★, and puts the five 3★ `gsd-build/*` in the same bucket. For `dspy` and `graphify` the rank reflects genuine evidence (papers, adoption) and the missing SKILL.md is a *packaging shape* problem, not an evidence problem — a hard reset would be the rank lying in the other direction. Recommend: ratify a narrow "evidence-backed, install-shape-blocked" carve-out that permits `installable: false` above 2★ *when the Trust Magnitude evidence is independently sound*, and fix the §12 table to match. Founder call.

**Q3 — Self-hosted skills (`gaiabot/repo-docs-before-pr`, `rico-favor/implement-with-discernment`).** Mark registry-only per Step 2, or ship a real `registry/named/<contributor>/<slug>/SKILL.md` directory so this repo's own named skills are installable from this repo? The second is more work but removes an embarrassment — `rico-favor`'s link currently points into an unrelated **fork** of this repo.

**Q4 — Contributor-blocked pair (`gooseworks/notte-browser`, `yonatangross/orchestkit-rag`).** Mark `installable: false` now (both 1★, fully reversible, stops the sweep re-flagging them), or hold them out and open contributor pings first? Recommend marking now and pinging in parallel.

---

## 8. Explicit scope boundaries

- **In scope for the curation PR:** `registry/named/**`, the Class S / API / stats artifacts listed in Step 4, `CONTRIBUTING.md`.
- **Out of scope for the curation PR:** `scripts/install_parity.py`, `src/gaia_cli/**`, `registry/schema/**`, anything under `docs/` not produced by `gaia dev docs`.
- **Never in this work:** `docs/og/`, `docs/api/v1/trending/`, `docs/graph/ledger/data.json`, `docs/experiments/ml-graph-viz/layouts_3d.json`, `docs/okf/` (warn-only / platform-sensitive).
- **No `--github-link` pointing at a repo-root file** (`README.md`, `LICENSE`, etc.) anywhere in this work — see C1.
- **No hand-edits** to frontmatter or timeline arrays; every mutation via `gaia dev update-named` (Programmatic-First Policy).
- **No merge to `main`** from any branch here; the integration→`main` merge is founder-gated.
