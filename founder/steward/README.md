# Gaia Steward policy

`POLICY.yaml` is the machine-enforced authority and priority policy for Gaia
Steward. `gaia steward scan` remains report-only. `gaia steward run` is the
explicit local closed loop for one policy-authorized Class A repair; it refuses
unclassified debt, unsafe paths, unknown coverage, and authority beyond its
single executor.

Steward writes ignored local state under `.gaia/steward/` and, only for the
declared Class A executors, the two mirror surfaces below. It does not dispatch,
create issues or pull requests, mutate canonical registry data, use a model, or
call the network.

| Executor | Canonical (read-only) | Writable mirror | Independent proof |
|---|---|---|---|
| `bundled-schema-mirror` | `registry/schema/**` | `src/gaia_cli/data/registry/schema/**` | `python scripts/sync_bundled_schemas.py --check` |
| `agent-skill-mirror` | `.agents/skills/**` | `.claude/skills/**` | `python scripts/sync_agent_skill_mirror.py --check` |

An executor is an authority envelope over a repair that is *registered in code*
(`src/gaia_cli/steward/mirrors.py`). Policy may narrow the authorized set by
omitting an executor; it can never invent one, point one at another surface, or
grant one a writable path outside `allowedWrites`. `maxRepairsPerRun` caps how
many surfaces a single run may change.

The two surfaces are independent. A mirror whose repair cannot be proven — a
mirror-only path that would have to be deleted, a dirty user edit, a symlink —
is recorded in the receipt's `blocked` list and left open; it never suppresses
the other surface's proven repair.

`agent-skill-mirror` treats `skill-creator/**` and Python bytecode as locally
owned by `.claude/skills/`. Those paths are neither compared nor overwritten,
and the repair carries them across its atomic replacement byte-for-byte.

Each checkout permits one debt transaction at a time via the atomic
`.gaia/steward/.scan.lock` directory. A process crash may leave this lock in
place; subsequent scans fail closed, and the lock may be removed manually only
after confirming that no Steward scan is active.

A successful changed run retains the displaced pre-repair mirror under
`.gaia/steward/`. The repair receipt records its repository-relative recovery
path and pre-repair SHA-256 manifest. This recovery is intentionally retained
for manual audit or restoration until a maintainer removes that receipt-recorded
local recovery directory; failed transactions restore the target and clean
their temporary recovery instead.

Authority is a ceiling. A future runtime may downgrade A to B or B to C when
proof becomes ambiguous; it may never upgrade authority automatically.
