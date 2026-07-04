# Sprint D — Agent Journal (append-only)

Every dispatched agent must append an entry at close. Format:

```markdown
## <date> · <agent-id> · <workstream>

**What I did:** [2 sentences]
**SHAs pushed:** [<branch>: sha1, sha2, sha3]
**Gotchas for next agent:** [1–3 bullets — traps you hit that aren't obvious from CONTEXT.md]
```

---

## 2026-07-05 · orchestrator · Sprint D kickoff

**What I did:** Cut `dev/sprint-d` off `main@3bc629be9` after confirming PR #895 (Sprint B closure) merged. Seeded `founder/handovers/sprint-d/CONTEXT.md` and this journal.
**SHAs pushed:** `dev/sprint-d`: 3bc629be9 (initial, matches main; the seed commit for CONTEXT.md + journal follows this entry)
**Gotchas for next agent:**
- The plan mentions v6.0.0 but Sprint B closure did NOT cut a v6.0.0 tag (orchestrator holding off; v6.0.0 will be cut at Sprint D close bundling Sprint B API + Sprint D content).
- `docs/api/v1/trending/*.json` are live and populated — safe to consume from W1.
- W4 leaderboard is frontend design — do NOT merge W4 PR without Marcus review. Everything else follows normal dev/sprint-d merge flow.


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


