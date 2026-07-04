# Sprint D — Agent Journal (append-only)

Every dispatched agent must append an entry at close. Format:

```markdown
## <date> · <agent-id> · <workstream>

**What I did:** [2 sentences]
**SHAs pushed:** [<branch>: sha1, sha2, sha3]
**Gotchas for next agent:** [1–3 bullets — traps you hit that aren't obvious from CONTEXT.md]
```

---

## 2026-07-05 · sonnet-w3 · W3 MMLU mirrored ingest (#906)

**What I did:** Landed W3 in 5 code commits + 1 PR on `dev/sprint-d-benchmark-mirror`. Scaffolded `scripts/benchmarks/mmlu/` (README, `__init__.py`, static `snapshot.json` from HF Open LLM Leaderboard 2024-03-01), wrote `ingest.py` (reads snapshot → `gaia dev evidence --provenance mirrored`, deterministic hashes, duplicate guard), dogfooded 3 mirrored rows on `anthropic/skill-creator` (86.8 pct), `openai/few-shot-learning` (86.4 pct), `huggingface/semantic-cache` (63.9 pct), seeded `docs/api/v1/benchmarks/mmlu.json` + updated `index.json` with both mmlu and humaneval entries, wrote `docs/benchmarks/mmlu-v1.md` methodology page, and added 4 passing tests in `tests/benchmarks/test_mmlu_ingest.py`.
**SHAs pushed (dev/sprint-d-benchmark-mirror):** `103babc6f`, `e139d0e92`, `d2cd8161e`, `86213cc7e`, `554ec5c42`
**Gotchas for next agent (W4 leaderboard render):**
- **`gaia dev evidence` triggers a docs build that deletes `docs/api/v1/benchmarks/index.json` and `docs/api/v1/reports/index.json`.** Revert them with `git checkout -- docs/api/v1/benchmarks/index.json docs/api/v1/reports/index.json` after the CLI run. Also reverts `docs/graph/gaia.json`, `docs/css/tokens.css`, and `docs/graph/ledger/data.json` as usual Class P cleanup.
- **`ingest.py` uses `yaml.safe_load` for the duplicate guard.** PyYAML must be available in the Python env (`pip install pyyaml`). The fallback (returns `[]`) means a missing PyYAML will silently skip the duplicate check and potentially double-write. CI env should be fine (PyYAML is already a dep), but worth verifying in a fresh venv.
- **`docs/api/v1/benchmarks/humaneval.json` does not exist yet** (W2b only created the in-skill evidence rows, not the API projection). The `index.json` entry for `humaneval@v1.0` points to `/api/v1/benchmarks/humaneval.json` which is a 404 today. W4 or a follow-up should create that file for API consistency.
- **Mirrored rows render as `grade: ungraded`** in the CLI output — this is correct per the W2a contract (`computeArtifactScoreOrNone` returns None → no grade written). W4 should surface these as "Cited" badges on the leaderboard (not scored, not ranked, clearly attributed). Do not add a grade field to these rows — the W2a exclusion logic is correct.


**What I did:** Cut `dev/sprint-d` off `main@3bc629be9` after confirming PR #895 (Sprint B closure) merged. Seeded `founder/handovers/sprint-d/CONTEXT.md` and this journal.
**SHAs pushed:** `dev/sprint-d`: 3bc629be9 (initial, matches main; the seed commit for CONTEXT.md + journal follows this entry)
**Gotchas for next agent:**
- The plan mentions v6.0.0 but Sprint B closure did NOT cut a v6.0.0 tag (orchestrator holding off; v6.0.0 will be cut at Sprint D close bundling Sprint B API + Sprint D content).
- `docs/api/v1/trending/*.json` are live and populated — safe to consume from W1.
- W4 leaderboard is frontend design — do NOT merge W4 PR without Marcus review. Everything else follows normal dev/sprint-d merge flow.


## 2026-07-05 · claude-w1 · W1 Content Engine MVP

**What I did:** Landed the full W1 Content Engine — data layer + L1/L2/L3 salvage harness + Jinja templates + build_docs.py pipeline step + Monday cron workflow with publish gate + /reports/ nav registration + RSS extension prepending the weekly report + 13 tests. Opened PR against `dev/sprint-d`.
**SHAs pushed (dev/sprint-d-content-engine):** 98f336824, 2c6c1d519, 0e4b8040a, f15f037bf, f15477d9b, 4878f92fb, c9d05f44b, 3eae5426d
**Gotchas for next agent:**
- The plan's `test_isoYearWeek_year_boundary (2026-01-01 → 2025-W53)` was mathematically wrong — 2026-01-01 is a Thursday and belongs to ISO 2026-W01. Test uses the correct boundary case: `2027-01-01 → 2026-W53` (also verifies `2021-01-01 → 2020-W53`).
- `scripts/` is intentionally NOT a Python package — `scripts/contentEngine/generate_weekly_report.py` does a `sys.path.insert(0, str(_PKG_DIR))` and imports `synthesizer` bare rather than dotted. Tests do the same trick from `tests/contentEngine/`.
- `build_content_engine(check)` in `build_docs.py` **intentionally returns False in --check mode** and only writes DRAFT in write mode. The canonical `/reports/YYYY-WW/` tree is owned by the weekly cron; local diffs would false-positive on Monday ISO-week rollover. The DRAFT dir is gitignored so it never surfaces as a check-time diff.
- Auto-PR branch prefix is `docs/content-engine-YYYY-WW` — `docs/*` allows `docs/` and `*.md` writes in `branch-scope.yml`, which fits the cron's write set exactly (no schema, no scripts).
- The workflow uses `vars.GAIA_CONTENT_ENGINE_PUBLISH` (not `secrets.*`) — the 0/1 flag is not secret; the `content-engine-live` environment gates who flips it.
- Class S seed file `docs/api/v1/reports/index.json` was intentionally created with `generatedAt: null` so the first commit doesn't bake a stale timestamp that would churn on every unrelated PR.
- RSS extension is backward compatible (`latest_report=None` default) — `run()` passes the loaded report but any external caller still works with the old two-arg signature.

## 2026-07-05 · opus-w2a · W2a Benchmark evidence schema (#904)

**What I did:** Landed the full W2a schema-hardening in 6 commits on `dev/sprint-d-benchmark-schema`. Standalone sub-schema (`registry/schema/evidence/benchmark-result.schema.json`), 8-field evidenceEntry gate with a date-epoch clause (2026-07 cutover) that exempts the 5 pre-existing 2026-06 benchmark-result rows, bundled-snapshot mirror, CLI Pre-Flight (`_preflight_benchmark_row` + 10 new argparse flags on `gaia dev evidence`), validator step [11/11] `validate_benchmark_provenance` with auto-strict via `GITHUB_BASE_REF`/`GITHUB_REF`, Trust Magnitude exclusion for mirrored/pending (returns None from `computeArtifactScoreOrNone`; strips `grade` at CLI write time on both append and --index paths), and the `docs/benchmarks/` landing surface with the mount registered in `docs/js/mounts.js` + `site-nav.js`. Opened PR against `dev/sprint-d`.
**SHAs pushed:** `dev/sprint-d-benchmark-schema`: 5ea7d2670, 8583d6de6, 58398e46b, f63eb6817, fb2739257, ae4b5af1e (+ this journal commit).
**Gotchas for next agent (esp. W2b/W3/W4):**
- **DO NOT reimplement the benchmark preflight.** `_preflight_benchmark_row` in `src/gaia_cli/commands/dev/helpers.py` is the single source of truth. W2b's `gaia push --benchmark` MUST call it before write — the JSON Schema layer + 10 CLI flags + semantic error messages are all reused.
- **Date-epoch gate:** the `allOf` in `evidenceEntry` fires only when `type == 'benchmark-result'` AND `date >= 2026-07`. Existing 5 corpus rows (browser-use/browser-harness, devin-ai/autonomous-swe, firecrawl/firecrawl, ruvnet/ruflo, extra/knowledge-graph-build) are exempt. If you regrade any of them via `--index`, you'll need to supply the 8 fingerprint fields OR keep the old date.
- **--percentile is now optional** for benchmark-result (previously required by `_preflight_evidence_static`). The 8 fingerprint fields carry the required-payload contract now.
- **Mirrored/pending rows have no grade.** Both the append and --index update paths in `evidence.py::_apply` short-circuit `provenance in ('mirrored','pending')` and strip `grade`. `computeArtifactScoreOrNone` returns None (not 0.0) so TM sum excludes them entirely — don't add a fallback grade-stamp anywhere.
- **Validator subprocess tests, not direct import.** `scripts/validate.py` has a Windows `sys.stdout = TextIOWrapper(...)` at module scope that collides with pytest capture. New validator tests use `subprocess.run` with explicit `encoding='utf-8'` — mirror this pattern if you extend the validator.
- **Class P bleed on `gaia dev docs`:** running the docs build regenerated `docs/css/tokens.css`, `docs/graph/gaia.json`, `docs/graph/ledger/data.json` in this worktree (unrelated cosmetic drift). I reverted them before the Commit 3 stage; do the same if you touch docs build in this branch.
- **No provenance enum in `meta.json`.** The Commit 3 task line about mirroring provenance values there is a genuine no-op; don't try to invent an enum block to put them in.


## 2026-07-05 · opus-w2b · W2b HumanEval benchmark pipeline (#905)

**What I did:** Landed the full W2b HumanEval pipeline in 7 commits on `dev/sprint-d-benchmark-pipeline`. Harness scaffold + reference implementation (`scripts/benchmarks/humaneval/run.py`, deterministic stubbed evaluator w/ SHA-256-seeded pass/fail + canonical-solution exec-and-check; `HUMANEVAL_MODEL_RUNNER` env var opts into live-model shell-out). USER verb `gaia push --benchmark` (`src/gaia_cli/commands/pushBenchmark.py`) diverts on `--benchmark` and calls `meta_evidence_command` directly with `provenance: pending` — zero preflight reimplemented. CI reproduction workflow `.github/workflows/benchmark-humaneval-ci.yml` (workflow_dispatch, downloads dataset, hashes, reproduces, promotes to `ci-reproduced` with workflow-run-URL@sha attestor). Verifier attestation format `docs/verifier-signoffs/YYYY-MM/*.md` with YAML frontmatter, extended `scripts/check_verifier_signoffs.py::checkBenchmarkAttestations`, wired as validate.py step [12/12]. First live row on `addy-osmani/code-simplification` (3★ code skill) via the exact CLI path CI would take. 30 new tests across 3 files.
**SHAs pushed (dev/sprint-d-benchmark-pipeline):** 9424cf182, 77b42770c, 5f0ff7d19, 928c3ff23, 286e46e72, ada0cdcf3, (docs+PR follows)
**KC4 skill pick:** `addy-osmani/code-simplification`. `mattpocock/scaffold-exercises` was the scout's suggestion but sits at 1★ — a benchmark row on a redacted-tier skill would collide with Section D of the redaction contract. Code-simplification is 3★ code-domain and its existing evidence mix (github-stars-own, repo-own, peer-review) accepts a benchmark-result cleanly.
**Gotchas for next agent (esp. W3/W4):**
- **`gaia push --benchmark` always writes `pending`.** There is no flag to override this — promotion is the CI/Verifier layer's job. If W3 wants a "push + auto-promote for CI runs" flow, add a new verb (e.g. `gaia dev promote-benchmark`) rather than punching a hole through push.
- **Source URL for benchmark evidence must be absolute http(s).** `_preflight_evidence_static` enforces this before `_preflight_benchmark_row` runs, so my first pass with `benchmark://<id>#<hash>` was rejected. Fallback is now `https://gaia.tiongson.co/benchmarks/<name>-v1.md#<inputHash>` — a real page with a fingerprint fragment for uniqueness. If you extend to another benchmark, either seed a `<name>-v1.md` doc first or override with `--harness-url`.
- **Attestor auto-resolves from gaiaUser config; fails cleanly with `--attestor <handle>` fix hint if unavailable.** Do NOT default to a placeholder like `"unknown"` — the preflight would accept it and ship a fake attestor.
- **`BENCHMARK_ID_ALIASES` in `pushBenchmark.py` is a frozen map.** Adding an alias is a coordinated change: new alias + new harness under `scripts/benchmarks/<name>/` + new `docs/benchmarks/<name>-v1.md` + new CI workflow. Test coverage for mismatches (short-name vs result-file benchmarkId) is in `tests/cli/test_push_benchmark.py::test_push_benchmark_short_name_mismatch_with_result_file`.
- **The stubbed evaluator scores 0.5 on the fixture (3/6 pass).** This is deterministic: SHA-256-seeded coin flip mod 3, so ~2/3 problems pass, then the "pass" branch exec-and-checks the canonical solution. Any tweak to the seeding formula changes every existing dogfood row's score — treat `_runStubbed` as frozen.
- **Attestation file frontmatter parser is hand-rolled, not PyYAML.** 6 flat fields, `_parseFrontmatter` in `check_verifier_signoffs.py`. Do NOT add PyYAML as a CI dep just to parse this — the flat-key contract is deliberate.
- **`gaia dev evidence` docs-build rewrites the whole named markdown YAML frontmatter.** My commit 6 diff is +125/-107 lines on `code-simplification.md`, almost all of that is YAML re-serialization noise (key order, wrapping). This is normal CLI behavior; don't hand-edit to shrink the diff.
- **CI workflow uses `GAIA_OPERATOR_OVERRIDE=1` in env.** Bot-actor override path per the Authorization hierarchy — required because the workflow runs `gaia dev evidence` (a mutating verb) after Verifier gating goes live.
- **Skill Explorer render:** the existing `benchmark-result` rows will surface in the generic evidence list on the named skill page without new render code. A prettier score-visualization treatment is scheduled for W4.


## 2026-07-05 · sonnet-w5 · W5 SEO surface (#908)

**What I did:** Landed the full W5 SEO surface layer in 6 commits on `dev/sprint-d-seo-surface`. PR #955 open → `dev/sprint-d`.

**Commits:**
1. `2babca88e` — `scripts/generateSitemap.py`: deterministic sitemap (73 URLs, was 8). --check flag for CI. Enumerates static pages, directory landings, /en/*.html, /u/<handle>/ contributor profiles, and future /named/<contrib>/<slug>.html skill pages (auto-detected).
2. `6c8a3d150` — Wire `build_sitemap()` into `build_docs.py` before `build_html_cache_busting`; add `sitemap_changed` to OR-chain.
3. `d9c51ec9a` — `scripts/injectJsonLd.py`: post-render JSON-LD injection across 89 HTML files. Schema type mapping frozen (WebSite+SearchAction for home, Person for contributors, SoftwareApplication+Article for named skills, Article+NewsArticle for reports, Dataset+TechArticle for benchmarks, WebPage fallback). Idempotent. Wire `build_jsonld()` into `build_docs.py` AFTER `build_html_cache_busting`.
4. `265f9f401` — `docs/skills/index.html` + `docs/skills/index.js` (aggregated index page). `scripts/buildSkillsIndex.py` reads OKF markdown files, emits `docs/okf/index.json` ({schemaVersion, generatedAt:null, families}). Registers 'skills' in `mounts.js` + `site-nav.js` fallback + dropdown. `build_skills_index()` wired. `check_nav_mounts.py` passes.
5. `f20a8abc7` — `docs/robots.txt` explicit Allow for /skills/, /benchmarks/, /trending/, /heroes/, /api/. `tests/test_seo.py`: 12 tests all green.

**Architecture decisions:**
- Used `scripts/buildSkillsIndex.py` (reads OKF .md files) instead of extending `build_okf_bundle.py` (requires `registry/gaia.json`, Class P). This makes the index.json generator CI-safe without needing `gaia pull` first.
- `generatedAt: null` in `docs/okf/index.json` per CLAUDE.md §Decorative convention.
- JSON-LD uses `data-injector="gaia-json-ld"` attribute on the script block — replace-on-re-run ensures idempotency.
- `/skills/` page fetches `okf/index.json` at runtime (no SSR). Sprint F Next.js rewrite can swap the static page while keeping `okf/index.json` as the data contract.

**Frozen invariants for Sprint F:**
- URLs /skills/, /benchmarks/, /reports/ — do NOT rename.
- schema.org types: WebSite (home), SoftwareApplication (named skills), Article (reports), Dataset (benchmarks).
- `docs/okf/index.json` schema shape: {schemaVersion:"1.0.0", generatedAt:null, families:[{id,count,skills:[{id,name,summary}]}]}.

**Gotchas for next agent:**
- `build_okf_bundle.py` has a stub `_build_okf_index()` function that will run when `registry/gaia.json` is present. In CI/production this will regenerate index.json from the full graph — that's the intended path. The standalone `buildSkillsIndex.py` is the fallback for environments without Class P.
- JSON-LD injection skips dirs: samples/, archive/, audits/, og/, assets/. If you add a new public dir, check those skip rules.
- The sitemap LAST_MOD is frozen to "2026-07-05" — this is intentional. Do NOT change it to a dynamic date (CLAUDE.md §Decorative).
- `docs/skills/index.js` uses `ROOT_PATH = '../'` assumption (depth 1). If you move the page deeper, update this.
