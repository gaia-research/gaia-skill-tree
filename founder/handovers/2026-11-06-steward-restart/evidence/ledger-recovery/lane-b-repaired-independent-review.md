# Independent Lane B review — repaired safety checkpoint #2283

## Verdict and finding

**REJECT — safe repair checkpoint only**, exact candidate `9aa9db35f85da35636130eaf2cad6f4b0311b615`, compared with accepted Lane A `6bc3688705c14b10f7ded3e6caeb721dd278c3bd`. This is not a verdict on expanded actual-data archival or authority to transfer pending data.

**High: extensionless artifact references can still pass the claimed portability gate in an allowed generic text field.** `src/gaia_cli/steward/archive.py:285-307, 337-349, 374-377` declares the legacy `observe.payload` to be inline text, but `phaseText` accepts any string without slash, backslash, tilde, colon, or an internal filename-like dot. It therefore cannot distinguish a bare extensionless relative artifact reference from prose. In an independent disposable bare remote, with settled synthetic run phases

```python
{"observe": {"payload": "proof"}, "retro": {"detail": "x" * 10000}}
```

`phase_hold` returned `None`, `plan` listed `run-a`, `migrate` archived it, hot phases became `{}`, and `show` returned the string `proof`. No file named `proof` was opened or bundled; if it denotes a relative evidence file, its bytes are not portable. The extra safe text simply makes the transfer space-saving. This demonstrates a filename-shape bypass in an allowed arbitrary payload slot, not a claim that `proof` actually existed or that every prose string denotes a file. The schema does reject unknown sibling keys and nested unknown shapes; that does not establish the semantics of a generic `payload` value. The explicitly required fail-closed extensionless/non-blacklist guarantee is therefore not demonstrated and this checkpoint should not be accepted. A repair needs a genuinely producer-constrained non-reference schema, or to hold ambiguous generic text, or independently verified bounded byte bundling; adding extensions to a blacklist is insufficient.

## Original counterexample, independently reproduced

Using a temporary bare Git remote and the identical synthetic phases `{"observe":{"receipt":"receipts/proof.bin","evidence":"evidence/build-output","payload":"x" * 10000}}`, I extracted only `phase_hold` via Python AST from `git show 598e45b01a848f45be100b06b094e99b5a9f4938:src/gaia_cli/steward/archive.py` and substituted it in process, leaving all other code at the reviewed SHA. Old guard: `None`, eligible `['run-a']`, archived `['run-a']`, hot phases `{}`. Repaired guard: explicit hold, eligible `[]`, archived `[]`, original phases remain hot. This is an old-predicate comparison, not an entire old checkout integration test. No original artifact bytes were bundled, read, or claimed portable.

## Other independent evidence

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/steward/test_archive_phase_schema.py tests/steward/test_archive_safety.py tests/steward/test_archive_readers.py` — **155 passed in 159.71s**.
- Same environment/options, `tests/steward/test_archive.py tests/steward/test_archive_contracts.py` — **70 passed in 417.96s**. Total independently run: **225 distinct selected tests**. These include >2 MiB disposable durable transfer, hydration/rollback, different source-commit provenance, conflict and lease/work protections, schema boundary, corruption/refusal and replay cases. They do not prove all possible interleavings or actual evidence-byte portability.
- The phase-schema suite independently executed the actual-operation-count test on a 3,145,728-character input, late dot/path and repeated-dot cases, plus 4,681 short Unicode/dot/slash semantic combinations; it used no deadline and did not skip the large input. It also covered null/false/nonstring/nested unknown siblings, canonical unknown/not-evaluated/historical shapes and a current-work settlement CAS race. These successes do not resolve the ambiguous allowed generic-text finding.
- `git diff --check 6bc3688705c14b10f7ded3e6caeb721dd278c3bd HEAD` succeeded; `git status --porcelain=v1` was empty. `git merge-tree cc2522c293d15d9e01606dcee741f5e9b04136d9 9aa9db35f85da35636130eaf2cad6f4b0311b615` exited 0 and returned tree `3a8f112bddde70a8e214958dadb214d48a96e5ee`; this is automatic composition only, not semantic integration testing or a merge.
- Parent's separate `lane-b-full-steward-9aa9.log` showed progress through 28% with no final summary when read. **Full Steward suite pending, not passed**; I neither duplicated it nor modified its output. The worker's reported 554 and prior review's 429 tests are not counted as independent executions here.

## Runtime, limits and remaining gates

Runtime environment reported `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`; no nested agent or fallback. The required graft skill and root/founder instructions were read. `graft/` was absent; graft commands auto-refresh/write their index, so per assignment I did not invoke them or build an index. I used bounded Git/source reads instead. No Skill Heaven plugin surface was available; this is not plugin validation.

Read-only review and tests used only disposable temporary remotes; no actual shared ledger operations, origin writes, forge actions, credential probes, activation, release or deployment. The worktree was clean at the end. I did not exhaustively verify every changed line, every crash ordering, or the parent suite's eventual outcome.

Actual archival DoD is **not complete**: no live archive, fresh-host live retrieval, forward rollback or current authoritative eligibility observation. Old historical snapshots reported zero eligible terminal runs; they cannot establish today's eligibility. A later canonical run completed and one work item resolved, but other authoritative work remains pending. Current Class C, pending/blocked/escalated work, leases, actions and replay/idempotency references must remain hot and unchanged. Do not settle or archive pending work by inference. The separate planner owns the remaining actual-data design; this review does not adjudicate Class C or authorize partial-detail archival. PR #2287 remains draft pending genuine DoD and authority closure, regardless of any eventual repaired checkpoint acceptance.
