# Daily cloud Steward — operating brief addendum (issue #2448)

**Status: NOT INSTALLED.** The daily job is an external scheduled task, not a file
in this repository: `Gaia Steward Daily` (`trig_01NLfT4PzgwkWh8utSzRRopE`, cron
`CRON_TZ=Asia/Manila 45 10 * * *`, model `claude-sonnet-5-5`, fresh session each
fire, `persist_session: false`). Its prompt is a prose brief ("Daily Steward
operating boundaries (November 2026)") that names **no** `gaia steward` command, so
whether the agents run `gaia steward full` or standalone `scan` / `dispatch` /
`lane next` is decided by the agent each day. The text below covers both. Nothing
here has been applied to the scheduled task; a founder (or an agent the founder
authorizes) must paste it in. The GitHub Actions pulse `.github/workflows/steward.yml`
(cron `10 7 * * *`, Class A only) is a different job and needs no change.

Append this section to the scheduled task's prompt, after "Integration" and before
"Cost reporting". It adds rules; it removes none, and changes no model authority
(Sonnet 5.5 High leads, Haiku 5.5 Medium/High builds, Sonnet 5.5 Medium reviews,
no Opus).

```text
Evidence custody (mandatory for every Class B action; issue #2448)

Cloud agents are destroyed when they finish, and their .gaia/steward/ directory
goes with them. A dispatch's authority, the candidate diff and the proof
transcript must therefore be made durable on the shared steward/evidence ref
before the agent that produced them exits, and read back from the remote.

- First command of every run: export GAIA_STEWARD_EVIDENCE=git, then confirm
  `gaia steward evidence --help` works. If the installed gaia lacks it, stop:
  report "BLOCKED: provenance unavailable (gaia lacks evidence custody)". Do not
  continue without custody and do not fall back to local receipts.
- Full-run mode: `gaia steward full run --trigger scheduled ...` and
  `gaia steward full record ...` honour GAIA_STEWARD_EVIDENCE=git and publish
  automatically. Standalone mode: `gaia steward dispatch` / `lane next` publish the
  dispatch automatically; the builder runs `gaia steward evidence accept DEBT`
  first and `gaia steward evidence publish-build DEBT --diff ... --proof ...
  --summary ... --model M --effort E` before exiting.
- The verifier is a DIFFERENT agent and, after the builder's container is gone,
  runs `gaia steward evidence verify DEBT` (or `gaia steward full run --verify`)
  in a fresh checkout. Never re-run `dispatch` to make a verification possible.
- Before any PR is marked ready, run `gaia steward evidence ready DEBT` and put
  its bundle ids and hashes (never the payloads) in the PR body.
- Any "BLOCKED: provenance unavailable" (exit 4) is a final outcome for that item:
  report it verbatim in the completion email, name the missing record, keep the
  item blocked, and move on. No retroactive receipts, no silent local fallback,
  no new dispatch to legitimize an existing patch, no "verified" claim.
- A mechanical verdict of pending is not acceptance; the independent Sonnet 5.5
  Medium verdict is still required. A quiet day (nothing eligible, nothing
  dispatched) publishes nothing and is reported as a genuine no-op.
```

Verification that the scheduled task was changed must come from reading it back
(`list_triggers` / the scheduled-task settings), not from this file.
