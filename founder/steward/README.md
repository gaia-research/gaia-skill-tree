# Gaia Steward policy

`POLICY.yaml` is the machine-enforced authority and priority policy for Gaia
Steward. `gaia steward scan` remains report-only. `gaia steward run` is the
explicit local closed loop for one policy-authorized Class A repair; it refuses
unclassified debt, unsafe paths, unknown coverage, and authority beyond its
single executor.

V1 writes ignored local state under `.gaia/steward/` and, only for the declared
Class A executor, the bundled schema mirror under
`src/gaia_cli/data/registry/schema/**`. It does not dispatch, create issues or
pull requests, mutate canonical registry data, use a model, or call the network.

Each checkout permits one debt transaction at a time via the atomic
`.gaia/steward/.scan.lock` directory. A process crash may leave this lock in
place; subsequent scans fail closed, and the lock may be removed manually only
after confirming that no Steward scan is active.

Authority is a ceiling. A future runtime may downgrade A to B or B to C when
proof becomes ambiguous; it may never upgrade authority automatically.
