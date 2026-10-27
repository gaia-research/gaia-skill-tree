# Yggdrasil IV — delivered proof set

Byte-identical copies of the campaign's verification evidence, committed so the
proof survives session archives and device loss. Sources live under
`.gaia/yggdrasil-iv/recovery/` (gitignored working evidence); these copies were
hash-compared against them when committed and are listed in
[`SHA256SUMS`](SHA256SUMS).

Campaign context and resume instructions:
[`founder/handovers/yggdrasil-iv/YGGDRASIL_IV_HANDOVER_2026-10-27.md`](../../handovers/yggdrasil-iv/YGGDRASIL_IV_HANDOVER_2026-10-27.md).

> **These are engineering proofs, not approvals.** Passing tests, green CI, matching
> hashes and reviewer model agreement do not constitute acceptance, schema adoption,
> production authorization, or founder approval.

## Contents

| Directory | What it proves | Scope limit |
|---|---|---|
| [`pause/`](pause/) | The graceful-pause preservation receipt: per-lane WIP patches/status, copied task JSON/output for `b7a08db9e`, `b535be684`, `b2a3126ec`, `b2617eb0c`, `bd66ba05c`, `b8188eac7`, plus the cost receipt | WIP refs, not accepted source |
| [`publication-b81/`](publication-b81/) | **Full publication proof at `b81a737a1`**: `verification-result.json`, regressions log, source before/after, both replay logs, harness, CI-delta review, preservation receipt | Engineering proof only; draft PR unmerged |
| [`publication-93/`](publication-93/) | Earlier full proof at `93fb731`, valid **at 93 only** — includes the runtime-mismatch counterprobe and the scoped review | Must not be relabelled to a later head |
| [`frontier-e4/`](frontier-e4/) | Both paired-protocol attempts at `e4df38cfb`, including the successful isolated-index queries and the exact failure reasons | **Not** a clean paired proof; no admission or superiority claim |
| [`canonical-9cd/`](canonical-9cd/) | Canonical CLI combined-verification run at `9cdcd8553` (134 tests + 5 subtests) and its preserved task records | Superseded by the later `96d329995` run; not acceptance |
| [`schema-proposal/`](schema-proposal/) | Exact held proposal schema bytes and provenance manifest for disposable test roots | **Proposal only** — two Core approvals and founder rollout held |
| [`reviews/`](reviews/) | Independent lifecycle review (hold for repair, two P2 defects), static publication CI-delta review, strict schema contract report, lifecycle producer report | Reviews are advisory; no reviewer approval exists |

## Deliberately not committed

The four declared-artifact archives (≈94 MB each, 2,558 members per b81 replay) stay
local only, because committing ~380 MB of binaries to a branch is not appropriate.
Their identities are recorded and independently verified:

| Archive | Bytes | SHA256 |
|---|---|---|
| `publication-93-parent-evidence/replay-one-declared-artifacts.tar.gz` | 94,102,633 | `cb4ff118c256e96eb423e3fec2a31e75e3d30e7d90beec6791f6793e14b019e4` |
| `publication-93-parent-evidence/replay-two-declared-artifacts.tar.gz` | 94,102,350 | `85e3738fd7b0146965633f445a05cff484059d7196c7572778800a179bc05f4c` |
| `publication-b81-parent-evidence/replay-one-declared-artifacts.tar.gz` | 94,514,034 | `480e52f90b672081c9237140431e3a72c6a2b196e0573f8ce47b0110cd3b24d7` |
| `publication-b81-parent-evidence/replay-two-declared-artifacts.tar.gz` | 94,513,754 | `b92df38bb9880b26ab6a1fe030ee304a67ebaca56b48b92f0e8342ff5782446a` |

Each archive is reconstructible from the committed manifests plus the pinned source
SHA and the fixed evaluation timestamp (`2026-10-25T12:00:00Z`) recorded in
`publication-b81/verification-result.json`.

Also not committed: full child-session JSONL transcripts and older pause bundles
under `.gaia/yggdrasil-iv/recovery/{pause-2026-10-27-gaia,continuation-session-evidence,continuation-working-sessions,crash-2026-10-26-1857,orchestration-pause-2026-10-26}/`.
They contain operator working state and stay local; their digests are recorded in the
session manifests there.

## Verifying a copy

```bash
cd founder/reports/yggdrasil-iv-evidence && sha256sum -c SHA256SUMS
```
