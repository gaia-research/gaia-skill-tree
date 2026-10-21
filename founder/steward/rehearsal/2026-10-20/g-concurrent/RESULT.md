# G - concurrent invocation: PASS

Two separate clones (work, work2) of one bare remote (default branch main), real-repo content, each running `full run --ledger git --json` at the same instant. 5 iterations: 1-3 launched with `&` + `wait`; 4-5 held on a barrier file and released together, launch order swapped in iter4.
- Every iteration: exactly one invocation ran to `completed` (exit 0); the other returned `observing-existing` (exit 4) naming the winner's run id as holder, with no actions and no work started. Exit-code tally over 10 invocations: 0 x5, 4 x5. Zero exit 1 / 2 / 3, no lease or CAS failure surfaced.
- Final remote ledger (final-ledger.json, trimmed): exactly 5 runs for 5 iterations, all `completed`, `leases: {}` (released). No duplicate or orphan run records, no double observation.
- Caveat: the same clone (work2, the one started second in iter1-3 and first in iter4) won all 5 times, including the swapped/barrier iterations, so the winner is not random; cause not investigated (presumably start-up time skew before the lease CAS). The safety property (one winner) held regardless of who won.
- Files: iterN-<clone>.json/.rc/.err, iter1-ledger.json, final-ledger.json (trimmed), tally.txt.
