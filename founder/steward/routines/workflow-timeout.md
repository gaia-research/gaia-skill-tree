# Routine — Workflow timeout repair

| | |
|---|---|
| **Policy rule** | `workflow-timeout-repair` |
| **Sensor** | `ci-workflow` — rule `missing-timeout` |
| **Debt kind** | `workflow_hygiene` |
| **Authority** | Class B — bounded autonomous repair |
| **Cadence** | Worth looking on a normal scan |
| **Routine catalog** | #13 — CI Architecture and Efficiency Steward |
| **Decision** | `steward-workflow-timeout-route` (founder ruling #14, #2283, 2026-11-06) |

---

## What it is for

Give a job that has no `timeout-minutes` an explicit one, so a hung job stops
after a sensible time instead of after the six-hour platform default. One debt
is one workflow file; the builder edits that file and nothing else.

## What a finding does and does not prove

A `missing-timeout` finding is a **configuration** finding. It says a job has no
declared bound. It does **not** say the job ever hung, ever timed out, or ever
ran long. The open debts of this kind (dozens of jobs across the workflow
directory) are not evidence of a runtime timeout problem, and this routine must
not be described as fixing one. Whether real runs actually time out, and on
which step, is a separate measurement:
`founder/reports/steward-campaign-2026-11-05/WORKFLOW_TIMEOUT_ATTRIBUTION.md`.

## The one exception to the `.github/**` floor

Every other dispatch rule forbids `.github/**`, and `policy.py` refuses to load a
policy that lets any other debt kind write there. This rule is the single,
code-pinned exception, and it is as narrow as the ruling:

- **May write:** direct-child `.github/workflows/*.yml` files only, and only by
  **inserting whole lines**. Verification applies two gates against the baseline
  (the file at the verifier checkout's `HEAD`), and both must pass.
  1. *Byte preservation (primary).* The diff has zero removed or modified lines and
     no no-newline marker, so every existing byte (whitespace, CRLF, BOM, comments,
     quoting, trailing newline) is untouched. A YAML loader calling two versions
     "equal" is never accepted as proof: `on` and `yes`, `012` and `10` are different
     to GitHub Actions. Each inserted line must match exactly
     `^( +)timeout-minutes: (1..360)$`: no comment, quotes or trailing space.
  2. *Structure.* The patched file loads as a single anchor-free, alias-free,
     tag-free, duplicate-key-free YAML document; the only semantic change is that
     integer key, as the key of a top-level job in a block mapping, at that job's
     own child-key indentation, at most once per job, and only where the job had none.
  A step-level key, text in a `run:` scalar, a key under `strategy`, `steps` or `on`,
  a flow-mapping job, a second key overriding a first, an alias or anchor,
  multi-document input, a non-ASCII or non-decimal numeral, any rewrite, and any
  workflow creation or deletion are rejected, as is a diff that does not apply.
- **Only for debts that are purely `missing-timeout`.** Dispatch (lane or explicit
  `--debt`) refuses this packet for a debt with any other finding, mixed or alone,
  for a capped finding list, a lock file, or a non-`.yml` subject.
- **Never writes:** `.github/workflows/*.lock.yml` (compiled gh-aw output, whose
  repair is the `.md` source plus a founder-gated recompile, see
  `FOUNDER_LOCK_2283.md` C4), `.github/workflows/shared/**`,
  `.github/workflows/_disabled/**`, `.github/actions/**`, any other part of
  `.github/`, and everything outside it.
- The sensor marks lock-file findings `laneEligible: false`, so they stay
  visible on the desk but never occupy a lane slot.

## Choosing the value

A timeout is a per-job judgement. Too low kills legitimate long jobs; too high is
the same as none.

1. **Read the job.** What does it do, and where can it legitimately wait
   (installs, test suites, a deploy, an approval gate, a network fetch)?
2. **Sample real durations (mandatory) with one command per flagged job**
   (decision `steward-workflow-timeout-history-fetch-2283`):
   `python -m gaia_cli.steward.workflowproof fetch --workflow <file> --job <job-key> --out <history-dir>/<job-key>.json`,
   where `<history-dir>` is `${TMPDIR:-/tmp}/gaia-steward-history/<dispatch-id>/build`,
   **outside** the repository checkout (fetch refuses a path inside it; the rows file is
   never committed). It resolves the YAML job key to the display name(s) the jobs API
   reports (`name:`, literal matrix legs) and refuses what it cannot resolve exactly,
   samples the latest 50 completed runs, reads each run's jobs for the attempt the run
   list reported, keeps rows for the job's **current** display name only (a renamed job
   contributes no rows under its old name), and prints the rows file's `sha256` and the
   pinned `run-ids`. Rows and runs are written in canonical order, so the bytes never
   depend on the order the API listed them. It exits 3 and writes nothing when history cannot be read (API
   failure, a truncated jobs page, no completed runs, no row for the job). Never
   assemble the rows file by hand; `gh run list` and `gh api` stay allowed for reading.
3. **Apply the rule.** `timeout = ceil to 5 minutes of max(2 x p95, 1.5 x max)`
   of the **successful** durations (a cancelled or timed-out run says nothing about how
   long healthy work takes), never below 5. State the sample size, p95, max and the
   result for every job in the proof, and compute it from the fetched rows with
   `python -m gaia_cli.steward.workflowproof history --history <history-dir>/<job-key>.json`.
   It stops (exit 3) on an
   empty sample and on any sampled run that was not skipped but has malformed,
   missing, timezone-less or reversed times, whatever its conclusion: an unusable
   row is never dropped silently.
4. **Cap by semantics.** A job with no external wait that already runs in under
   two minutes does not get a 60-minute bound. A job that deploys or fetches
   over the network may need more headroom than its median suggests; say why.
5. **Placement.** Put `timeout-minutes` directly under the job's `runs-on` (or
   `needs`/`if`), at the job's own indentation. Never edit an existing key.

### A job with no successful history (decision `steward-workflow-timeout-no-history-2283`)

Two different situations, never confused:

- **History cannot be read** (the API fails, the workflow has no completed runs at
  all, or fewer runs than the sample asks for were returned and none is usable):
  **stop**, as before; there is no semantics-only fallback for unreadable history.
- **History was read and the job has no successful run in it** (for example the
  job was `skipped` on every one of the 50 sampled runs, because its `if:` rarely
  holds): apply the **no-history default**, below. It is the only case where the
  value comes from the job's own steps rather than its durations.

The no-history default, in order:

1. **Classify the job by what its own steps do** (all steps, not the workflow):
   - `api-script` (base 10 min): only GitHub API / CLI / shell or `github-script`
     calls; no dependency checkout, install or build;
   - `checkout-script` (base 15 min): checks out the repository and runs a
     repository script, still with no dependency install;
   - `install-build-test` (base 30 min): installs dependencies, builds or runs tests.
   Anything else has no default: **stop**.
2. **Add the job's own declared waits.** Sum every explicit, bounded wait its steps
   declare (a poll loop's `rounds x sleep`, an action's wait/timeout input), each at
   its **worst case resolved from this job's own YAML**:
   - a bound that comes from an `env:` value or a `matrix:` must be resolved to its
     largest value from this job's YAML (job, workflow or matrix definitions in the
     same file); a bound that depends on an input, a secret, a repository variable or
     anything not written in this file cannot be resolved: **stop**;
   - **stop** for an unbounded wait (a loop with no cap, `while true`), an
     environment approval or any wait on a human, a `gh run watch` or a
     `gh workflow run` (or any other wait on another workflow or deploy), and any
     composite or third-party action whose waits cannot be read and bounded from
     its pinned source: an opaque action is never assumed to be bounded.
3. **Collect this job's raw history rows** with the same `workflowproof fetch` command
   (step 2 above). Do not pick or drop rows by hand: the tool selects them.
4. **Compute and recompute mechanically:** `python -m gaia_cli.steward.workflowproof
   no-history --class <class> --declared-wait-seconds <s> --history <history-dir>/<job-key>.json`.
   It selects the rows itself and prints that selection and the value:
   - every row that **actually executed** counts as an observed duration: any
     conclusion other than `skipped` with a start and a completion time (`success`,
     `failure`, `cancelled`, `timed_out`, ...). A cancelled or timed-out run consumed
     that time; it is a lower bound, never ignored;
   - value = `ceil to 5 minutes of max(base + 2 x declared waits, 1.5 x longest
     executed run)`, never below 10;
   - **stop** (exit 3) when the sample is empty, when a non-skipped row has no
     usable times, when the job has a successful run (use the history rule), or
     when the result is above **60**, for
     example because an executed run was long (a job that may legitimately need more
     than an hour needs real history first).
   Paste the fetch command and output, the no-history command and its output
   (selection and value), the class and the waits you summed (step names, resolved
   worst case, arithmetic) in the proof.

### How the verifier recomputes

Mechanical verification parses the item-2 `fetch` entries once and rejects the build
unless every flagged job has exactly one successful `fetch` entry whose captured output
carries exactly one each of `workflow`, `job-key`, `sha256` and `run-ids`, matching
its own `--workflow` / `--job`, and a `history` or `no-history` entry reading exactly
that fetch's `--out`. Metadata is never read from any other entry. The recompute
commands are built from those same records and recorded on the machine verdict;
the verifier prompt refuses to render without them. The
verifier prompt then lists, per job,
`workflowproof fetch --run-ids <pinned> --expect-sha256 <digest> --out ${TMPDIR:-/tmp}/gaia-steward-history/<dispatch-id>/verify/<job-key>.json`
(exit 4 on any byte difference), then `history` on that file; for a job with no
successful run the verifier runs `no-history` with the class and declared waits it
derives itself from the job's YAML. The verifier compares the selection and value with
the builder's item-2 output and the diff. These commands are built from the packet
(subject, flagged jobs, dispatch id) and validated digests only, never from builder text.

Why this is safe: the value only ever bounds a job, never changes what it does;
the bases are an order of magnitude above what jobs of that class take in this
repository (sibling API jobs finish in 3 to 14 seconds) while still bounding a
hang to a sixth of the 360-minute platform default or less; the floor of 1.5 x
every observed execution (cancelled and timed-out runs included) means it can
never be shorter than time this job was already seen to consume; and sibling jobs' history is deliberately **not** used, because a
sibling with different steps says nothing about this job's waits.

Worked examples (batch 9): `auto-label-bot-prs.yml` job `label-bots`, a single
`github-script` labeling call, `api-script`, no waits, never executed: **10**.
`auto-triage.yml` job `auto-merge`, `gh`/`jq` steps with a declared poll of 60
rounds x 10 s (600 s): `api-script`, 10 + 2 x 10 = **30**.

## Stop conditions

1. The finding does not reproduce on the current head.
2. The subject is a lock file or has a gh-aw source beside it.
3. Any change besides adding `timeout-minutes` keys would be needed, or the debt
   carries any finding besides `missing-timeout` (such a debt is not routed here;
   if you were handed one anyway, report it and stop).
4. Completed-run duration history cannot be read for a flagged job; or it was read,
   has no successful run, and the no-history default does not apply (no class,
   an unbounded wait, or a result above 60).
5. The job legitimately waits on a human or an environment approval, runs
   `gh run watch` / `gh workflow run` or otherwise waits on another workflow or a
   deploy, has an unbounded wait, a wait bound that cannot be resolved to a worst
   case from this job's YAML, or a composite/third-party action whose waits cannot
   be read and bounded.
6. A flagged job is a reusable-workflow call (cannot declare `timeout-minutes`).
7. The edited file does not parse as YAML.

## Proof

Reproduce every finding, show a one-file diff that only adds `timeout-minutes`
keys, paste the per-job sample and arithmetic (and, for a no-history job, the class,
declared waits, observed durations and the `workflowproof no-history` output), parse the edited file as YAML,
run `python scripts/check_steward_coverage.py --check` and
`python -m pytest tests/steward/test_sensors_ci.py`, and paste exact results. A
different, fresh agent verifies independently, and the PR still goes through
normal CI and review. A workflow file is a security-relevant surface; Steward
never merges its own change.
