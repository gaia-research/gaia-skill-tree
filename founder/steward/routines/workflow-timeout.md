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
2. **Sample real durations (mandatory).** The `ci-runs` input carries no durations, so read
   them: `gh run list --workflow <file> --status completed --limit 50 --json databaseId,conclusion,createdAt,startedAt,updatedAt`
   for the workflow, then
   `gh api repos/gaia-research/gaia-skill-tree/actions/runs/<run-id>/jobs --jq '.jobs[] | {name, conclusion, started_at, completed_at}'`
   for per-job times. Use **successful** runs only; a run that was cancelled or
   timed out says nothing about how long healthy work takes.
3. **Apply the rule.** `timeout = ceil to 5 minutes of max(2 x p95, 1.5 x max)`
   of the successful durations, never below 5. State the sample size, p95, max
   and the result for every job in the proof.
4. **Cap by semantics.** A job with no external wait that already runs in under
   two minutes does not get a 60-minute bound. A job that deploys or fetches
   over the network may need more headroom than its median suggests; say why.
5. **Placement.** Put `timeout-minutes` directly under the job's `runs-on` (or
   `needs`/`if`), at the job's own indentation. Never edit an existing key.

If no successful completed-run duration history can be read for a flagged job, stop.
Job semantics alone never substitute for history: there is no semantics-only fallback.

## Stop conditions

1. The finding does not reproduce on the current head.
2. The subject is a lock file or has a gh-aw source beside it.
3. Any change besides adding `timeout-minutes` keys would be needed, or the debt
   carries any finding besides `missing-timeout` (such a debt is not routed here;
   if you were handed one anyway, report it and stop).
4. Successful completed-run duration history cannot be read for a flagged job.
5. The job legitimately waits on a human or an environment approval.
6. A flagged job is a reusable-workflow call (cannot declare `timeout-minutes`).
7. The edited file does not parse as YAML.

## Proof

Reproduce every finding, show a one-file diff that only adds `timeout-minutes`
keys, paste the per-job sample and arithmetic, parse the edited file as YAML,
run `python scripts/check_steward_coverage.py --check` and
`python -m pytest tests/steward/test_sensors_ci.py`, and paste exact results. A
different, fresh agent verifies independently, and the PR still goes through
normal CI and review. A workflow file is a security-relevant surface; Steward
never merges its own change.
