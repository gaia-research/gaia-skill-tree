# P1 Source Reconnaissance — `ruvnet/agentdb` and `ruvnet/ruflo`

- **Date:** 2026-11-16
- **Branch / Base:** `dev/upstream-backlog-watcher-2026-11` @ `91963ac2821dd5ee4e160faf743bb5b30139422e` (draft PR #2468 -> `dev/upstream-backlog-2026-11`, P0 merge `bfed2d777b76448f6ede5d40e1a834050dff07d0`)
- **Authority:** `PLAN.md` § F step 2, `CAMPAIGN.md` founder ruling 4, `docs/agents/upstream-watcher.md` release-identity contract, `founder/steward/FOUNDER_LOCK_2283.md` & `founder/steward/decisions/issue-question-q-08ecd62d.json` (C1)
- **Verdict:** **SOURCE GATE SATISFIED**

## 1. Existing Registry Records (`ruvnet/agentdb` and 5 `suiteComponents`)

| Record ID | Registry Path | Current `links.github` | Current `suiteRef` | Current `upstream` |
|---|---|---|---|---|
| `ruvnet/agentdb` (suite) | `registry/named/ruvnet/agentdb.md` | `https://github.com/ruvnet/ruflo` | `ruvnet/ruflo` | `repo: ruvnet/ruflo`, `version: v3.67.0`, `releasedAt: 2026-10-31T22:06:47Z`, `sourceUrl: https://github.com/ruvnet/ruflo/releases/tag/v3.67.0`, `mode: components` |
| `ruvnet/agentdb-advanced` | `registry/named/ruvnet/agentdb-advanced.md` | `https://github.com/ruvnet/ruflo` | `ruvnet/ruflo` | *(none)* |
| `ruvnet/agentdb-learning` | `registry/named/ruvnet/agentdb-learning.md` | `https://github.com/ruvnet/ruflo` | `ruvnet/ruflo` | *(none)* |
| `ruvnet/agentdb-memory-patterns` | `registry/named/ruvnet/agentdb-memory-patterns.md` | `https://github.com/ruvnet/ruflo` | `ruvnet/ruflo` | *(none)* |
| `ruvnet/agentdb-optimization` | `registry/named/ruvnet/agentdb-optimization.md` | `https://github.com/ruvnet/ruflo` | `ruvnet/ruflo` | *(none)* |
| `ruvnet/agentdb-vector-search` | `registry/named/ruvnet/agentdb-vector-search.md` | `https://github.com/ruvnet/ruflo` | `ruvnet/ruflo` | *(none)* |

## 2. Upstream Repository Metadata, Releases, and Pinned Refs

All values retrieved read-only via `gh api` (`GET /repos/{owner}/{repo}`, `/releases/latest`, `/git/ref/...`, `/git/trees/...?...recursive=1`).

### `ruvnet/agentdb`
- **Repository:** <https://github.com/ruvnet/agentdb> (`archived: false`, `fork: false`)
- **Authoritative `releases/latest`:**
  - `tag_name`: `v3.10.0` (lightweight tag)
  - `name`: `AgentDB 3.10.0 — learned memory reranking`
  - `published_at`: `2026-11-10T19:45:36Z`
  - `prerelease`: `false`, `draft`: `false`
  - `html_url`: <https://github.com/ruvnet/agentdb/releases/tag/v3.10.0>
  - **Pinned release commit SHA:** `2a8115de9ddbc672df4d725069b77228b43af53d`
- **Default branch (`main`):**
  - **Pinned `main` commit SHA:** `84081e21afa383f7f0849fed96c90b177ce27c8b`
  - **Lag / delta vs `releases/latest`:** `main` is `ahead_by: 1` commit (`84081e21af`, `2026-11-11T20:21:52Z`, `"release: 3.10.1 - migrate CLI schema fix, Docker entry paths, #45 test timeouts"`). No GitHub Release exists for `3.10.1`; `v3.10.0` remains the authoritative `releases/latest`.
  - **Tree completeness:** `truncated: false` on both `2a8115de9d` (1,942 entries) and `84081e21af` (1,943 entries). All 51 `SKILL.md` blobs are byte-identical between `v3.10.0` and `main`.

### `ruvnet/ruflo`
- **Repository:** <https://github.com/ruvnet/ruflo> (`archived: false`, `fork: false`)
- **Authoritative `releases/latest`:**
  - `tag_name`: `v3.77.1` (lightweight tag)
  - `name`: `v3.77.1 — AgentDB honours the configured embedding model`
  - `published_at`: `2026-11-13T21:05:38Z`
  - `prerelease`: `false`, `draft`: `false`
  - `html_url`: <https://github.com/ruvnet/ruflo/releases/tag/v3.77.1>
  - **Pinned release commit SHA:** `3a1479883b55b7f786ef0bf3141478e4dfb9444f`
- **Default branch (`main`):**
  - **Pinned `main` commit SHA:** `3a1479883b55b7f786ef0bf3141478e4dfb9444f` (matches `v3.77.1`; `ahead_by: 0`).
  - **Tree completeness:** `truncated: false` on `3a1479883b` (10,610 entries).

## 3. Component-by-Component Source Verification

All 5 existing suite components exist as substantive, full-length `SKILL.md` files (339–550 lines, 8.6–13.1 KB; no redirects or shims) in **both** `ruvnet/agentdb` and `ruvnet/ruflo`.

| Component ID | `ruvnet/agentdb` (`v3.10.0` & `main`) | `ruvnet/ruflo` (`v3.77.1` / `main`) | Content Identity Comparison |
|---|---|---|---|
| `ruvnet/agentdb-advanced` | **Exists** (`blob` `da61dc2ead79`, 13,060 B, 550 lines)<br>Path: `ui/.claude/skills/agentdb-advanced/SKILL.md`<br>`name: "AgentDB Advanced Features"`<br>[Evidence URL](https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/ui/.claude/skills/agentdb-advanced/SKILL.md) | **Exists** in 3 paths:<br>1. `.claude/skills/agentdb-advanced/SKILL.md` (`1caa8bc88bf0`, 13,049 B, 550 lines, `name: agentdb-advanced`) — [URL](https://github.com/ruvnet/ruflo/blob/3a1479883b55b7f786ef0bf3141478e4dfb9444f/.claude/skills/agentdb-advanced/SKILL.md)<br>2. `v3/@claude-flow/cli/.claude/skills/agentdb-advanced/SKILL.md` (same blob `1caa8bc88bf0`)<br>3. `.agents/skills/agentdb-advanced/SKILL.md` (`298845ea4703`, 13,123 B, 551 lines) | `agentdb` vs `ruflo/.claude/skills`: differs **only** in frontmatter `name:` line (`"AgentDB Advanced Features"` vs `agentdb-advanced`). `ruflo/.agents/skills` has `/` mangled to `$` in code snippets. |
| `ruvnet/agentdb-learning` | **Exists** (`blob` `874760cf29dd`, 11,916 B, 545 lines)<br>Path: `ui/.claude/skills/agentdb-learning/SKILL.md`<br>`name: "AgentDB Learning Plugins"`<br>[Evidence URL](https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/ui/.claude/skills/agentdb-learning/SKILL.md) | **Exists** in 3 paths:<br>1. `.claude/skills/agentdb-learning/SKILL.md` (`e21b17ff2f43`, 11,906 B, 545 lines, `name: agentdb-learning`) — [URL](https://github.com/ruvnet/ruflo/blob/3a1479883b55b7f786ef0bf3141478e4dfb9444f/.claude/skills/agentdb-learning/SKILL.md)<br>2. `v3/@claude-flow/cli/.claude/skills/agentdb-learning/SKILL.md` (same blob `e21b17ff2f43`)<br>3. `.agents/skills/agentdb-learning/SKILL.md` (`7864d784829a`, 11,916 B, 545 lines) | `agentdb` vs `ruflo/.claude/skills`: differs **only** in frontmatter `name:` line (`"AgentDB Learning Plugins"` vs `agentdb-learning`). `ruflo/.agents/skills` has `/` mangled to `$` in code snippets. |
| `ruvnet/agentdb-memory-patterns` | **Exists** (`blob` `84a3f106981d`, 8,687 B, 339 lines)<br>Path: `ui/.claude/skills/agentdb-memory-patterns/SKILL.md`<br>`name: "AgentDB Memory Patterns"`<br>[Evidence URL](https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/ui/.claude/skills/agentdb-memory-patterns/SKILL.md) | **Exists** in 3 paths:<br>1. `.claude/skills/agentdb-memory-patterns/SKILL.md` (`64d0ef99aa9d`, 8,685 B, 339 lines, `name: agentdb-memory-patterns`) — [URL](https://github.com/ruvnet/ruflo/blob/3a1479883b55b7f786ef0bf3141478e4dfb9444f/.claude/skills/agentdb-memory-patterns/SKILL.md)<br>2. `v3/@claude-flow/cli/.claude/skills/agentdb-memory-patterns/SKILL.md` (same blob `64d0ef99aa9d`)<br>3. `.agents/skills/agentdb-memory-patterns/SKILL.md` (`d9b6d5520e3c`, 8,687 B, 339 lines) | `agentdb` vs `ruflo/.claude/skills`: differs **only** in frontmatter `name:` line (`"AgentDB Memory Patterns"` vs `agentdb-memory-patterns`). `ruflo/.agents/skills` has `/` mangled to `$` in code snippets. |
| `ruvnet/agentdb-optimization` | **Exists** (`blob` `f19df8617d7a`, 12,132 B, 509 lines)<br>Path: `ui/.claude/skills/agentdb-optimization/SKILL.md`<br>`name: "AgentDB Performance Optimization"`<br>[Evidence URL](https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/ui/.claude/skills/agentdb-optimization/SKILL.md) | **Exists** in 3 paths:<br>1. `.claude/skills/agentdb-optimization/SKILL.md` (`dd8ae5982631`, 12,118 B, 509 lines, `name: agentdb-optimization`) — [URL](https://github.com/ruvnet/ruflo/blob/3a1479883b55b7f786ef0bf3141478e4dfb9444f/.claude/skills/agentdb-optimization/SKILL.md)<br>2. `v3/@claude-flow/cli/.claude/skills/agentdb-optimization/SKILL.md` (same blob `dd8ae5982631`)<br>3. `.agents/skills/agentdb-optimization/SKILL.md` (`103d2629e26b`, 12,132 B, 509 lines) | `agentdb` vs `ruflo/.claude/skills`: differs **only** in frontmatter `name:` line (`"AgentDB Performance Optimization"` vs `agentdb-optimization`). `ruflo/.agents/skills` has `/` mangled to `$` in code snippets. |
| `ruvnet/agentdb-vector-search` | **Exists** (`blob` `78cd76f1de12`, 8,944 B, 339 lines)<br>Path: `ui/.claude/skills/agentdb-vector-search/SKILL.md`<br>`name: "AgentDB Vector Search"`<br>[Evidence URL](https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/ui/.claude/skills/agentdb-vector-search/SKILL.md) | **Exists** in 3 paths:<br>1. `.claude/skills/agentdb-vector-search/SKILL.md` (`fe0740e7572a`, 8,942 B, 339 lines, `name: agentdb-vector-search`) — [URL](https://github.com/ruvnet/ruflo/blob/3a1479883b55b7f786ef0bf3141478e4dfb9444f/.claude/skills/agentdb-vector-search/SKILL.md)<br>2. `v3/@claude-flow/cli/.claude/skills/agentdb-vector-search/SKILL.md` (same blob `fe0740e7572a`)<br>3. `.agents/skills/agentdb-vector-search/SKILL.md` (`f664dd9be342`, 8,944 B, 339 lines) | `agentdb` vs `ruflo/.claude/skills`: differs **only** in frontmatter `name:` line (`"AgentDB Vector Search"` vs `agentdb-vector-search`). `ruflo/.agents/skills` has `/` mangled to `$` in code snippets. |

## 4. Ambiguities, HTTP Failures, and Governance Boundaries

- **HTTP / API status:** Zero HTTP failures; all `gh api` requests returned 200 OK and `truncated: false` on all recursive trees.
- **Release vs default-branch lag:** `ruvnet/agentdb` `main` (`84081e21af`) is 1 commit ahead of `v3.10.0` (`2a8115de9d`) with commit `"release: 3.10.1 ..."` (no GitHub Release published for `3.10.1`). Watcher's authoritative comparator (`releases/latest`) is `v3.10.0`.
- **Nested topology & provenance:** `ruvnet/agentdb` and all 5 components carry `suiteRef: ruvnet/ruflo` (and `ruvnet/ruflo` lists them in `suiteComponents`). Reconciling AgentDB's source repository to `ruvnet/agentdb` must preserve `suiteRef: ruvnet/ruflo` and existing timeline/evidence history.
- **No inferred release approval:** Confirming `v3.10.0` (`ruvnet/agentdb`) and `v3.77.1` (`ruvnet/ruflo`) is source verification only; neither release is approved by this report.

## 5. Conclusion & Proposed Bounded Next Engineering Task

**SOURCE GATE SATISFIED.** Founder ruling 4's premise holds at source: all 5 existing suite components exist as substantive `SKILL.md` files in `ruvnet/agentdb` (`ui/.claude/skills/agentdb-*/SKILL.md`, identical on `v3.10.0` and `main`), and `ruvnet/agentdb` has its own unambiguous GitHub Release (`v3.10.0`, `2026-11-10T19:45:36Z`, <https://github.com/ruvnet/agentdb/releases/tag/v3.10.0>).

### Proposed Bounded Next Engineering Task (NOT implemented in this run)
1. **CLI relink support (`src/gaia_cli/commands/dev/sync_upstream.py` + tests):** Add an explicit, timeline-logged repository-repoint path to `gaia dev sync-upstream` (per ruling 4), then re-point `ruvnet/agentdb` to `ruvnet/agentdb` @ `v3.10.0` (`2026-11-10T19:45:36Z`, <https://github.com/ruvnet/agentdb/releases/tag/v3.10.0>) and update the 5 component `links.github` pointers via `gaia dev update-named --github-link` to `https://github.com/ruvnet/agentdb/blob/v3.10.0/ui/.claude/skills/<slug>/SKILL.md` (preserving `suiteRef: ruvnet/ruflo` and history).
2. **Watcher `links.github` fallback (`scripts/upstream_watcher/` + tests):** Fall back to `upstream.repo` when `links.github` is empty so `gsd-build/get-shit-done` is tracked (`PLAN.md` § F step 3).
3. **Verification:** Run `pytest tests/upstream_watcher tests/test_upstream_approve_workflow.py tests/test_dev_upstream_verbs.py -q`, `python tests/upstream_watcher/parity_2283.py`, and an authorized runner `Upstream Watcher` dry run (`apply=false`) to confirm exit 0 and check whether `#2278` recurs.
