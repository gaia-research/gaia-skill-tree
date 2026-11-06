## Lane A integrated; genuine campaign persistence check started

- **Merged #2284 into the authorized integration branch**, merge commit `d694986b8` (not main).
- Independently accepted source/test head: `6bc3688705c14b10f7ded3e6caeb721dd278c3bd`.
- Fresh Terra-high verification: **134 passed** (130 ledger, two legacy retention tests, two 6/26-run preservation scenarios). Includes temporary shared-Git >1 MiB roundtrip, exact 8 MiB UTF-8 boundaries and fail-closed invalid configuration on missing/seeded stores.
- Active checkout now reports **8,388,608 bytes** as its uniform ledger bound. Immediately before continuation, actual shared status showed no active run, holder or in-flight dispatch.
- A genuine canonical next cycle is now running against the existing unused-`Path` debt in `src/gaia_cli/steward/issuehygiene/reconcile.py`, using explicit `--ledger git` and the unchanged one-dispatch/lease/CAS limits. This is not a restart of the abandoned trust attempt. **Live >1 MiB persistence is not claimed until its actual shared commit is independently fetched and inspected.**

### Lane B and assurance

Archival memory remains **not complete / not merge-approved**. Independent review of the first prototype passed 42 tests but identified missing ordinary-reader hydration, evidence-byte portability, compatibility and provenance gaps. The original worker’s later partial work was preserved at `d58f6b1bf2a42b6929b903b6c3f584c11d119a0e`; it is not counted as a delivered fix.

Founder requested no agent timeouts or turn limits. Continuing archival engineering now uses a dedicated durable worktree and direct Pi execution with **no imposed run timeout or turn cap**, exact OpenAI Sol-high routing, extension discovery disabled and no Antigravity/failover agent. The same approach will be used for future workers. No global Pi settings were changed.

The parallel new-sensor work will be reconciled by merging its actual main changes into integration later, preserving both workstreams and rerunning affected tests. No reset/rebase or replacement of that work is planned.

Class C remains queued and unchanged; the accurate, sanitized 43-row inventory is attached above. No main merge, release, deployment or history deletion has occurred.
