# Gaia Steward policy

`POLICY.yaml` is the machine-enforced authority and priority policy for the
report-only `gaia steward scan` foundation. The scanner refuses unclassified
debt kinds, unsafe state paths, unknown policy keys, and any mode other than
`report-only`.

V1 writes only ignored local state under `.gaia/steward/`. It does not repair,
dispatch, create issues or pull requests, regenerate projections, mutate the
registry, use a model, or call the network.

Each checkout permits one debt transaction at a time via the atomic
`.gaia/steward/.scan.lock` directory. A process crash may leave this lock in
place; subsequent scans fail closed, and the lock may be removed manually only
after confirming that no Steward scan is active.

Authority is a ceiling. A future runtime may downgrade A to B or B to C when
proof becomes ambiguous; it may never upgrade authority automatically.
