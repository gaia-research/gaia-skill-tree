## Yggdrasil IV — cost receipt at graceful pause (2026-10-27)

Engineering cost for the orchestrator run that carried the campaign from the resumed continuation through the current pause. **This is a cost receipt only — not acceptance, approval, release authorization, or merge consent.**

### Totals (harness subagent runtime accounting)

| Item | Cost | Tokens |
|---|---|---|
| Root orchestrator session | **$31.8769** | 4,115,868 |
| Subagents — 106 runs / 115 tasks | **$19.3798** | 23,806,025 |
| **Combined** | **$51.2566** | **27,921,893** |

`/pi-cost`'s JSONL parse of the active session independently reported main $31.8751 / nested subagent $3.1719 / total $35.0470; it prices only models present in its table (many entries resolve to $0.0000), so the harness totals above are authoritative.

### What the spend produced

- **Canonical CLI**: `96d3299951a6dcd5969f11c78396f2a4d7983957` — optional non-POSIX imports, stdlib `msvcrt` legacy lock, fail-closed POSIX-only durable apply/rollback. Verified **141 passed + 5 subtests / 80.06s** at exact head with clean source guards (prior **134 + 5 / 80.92s** at `9cdcd8553`). Uncommitted strict-held-schema fixture work preserved at `recovery/yggdrasil-iv-pause-canonical-fixtures-96d329995` (`fbf9f203d`).
- **Publication**: **full proof completed at `b81a737a1`** — two disjoint roots, 2,555 artifacts each, identical snapshot `a0e07524…`, both independent verifies, two-root byte equal, 326 regressions exit 0, source unchanged. Separate independent CI-delta review (static) found no substantive defect.
- **Lifecycle**: producer/build/consumer increment at `6fa482665`; independent dynamic review returned **hold for repair** with two P2 defects (hero-metric contradiction; malformed DTO acceptance) plus reduced legacy coverage.
- **Schema**: strict contract proposal at `bf9097b7a` — 73 tests, Draft7 + three-mirror parity, zero new raw-schema failures; the 371 pre-existing failures disclosed unchanged.
- **Frontier**: recorder accepted; paired execution still not a clean proof (second attempt's own source-invariance gate failed because `graft build` rewrote tracked `.gitignore`).

### Campaign state at pause

Integration `dev/yggdrasil-iv` remains **`bed78e716bc56d61cddc039c88ac95980be2ddf7`**; `main` is **`5196d552a`** from unrelated work. No merge, deployment, schema adoption, issuer activation, or approval claim occurred. Resume path: `founder/YGGDRASIL_IV_HANDOVER_2026-10-27.md` on `dev/yggdrasil-iv-execution-continued` (`c70855fbe`).
