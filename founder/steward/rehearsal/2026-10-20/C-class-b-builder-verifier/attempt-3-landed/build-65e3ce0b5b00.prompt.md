# Tree Keeper dispatch — `dispatch-b96f613561ae5ba2184a`

You are **Tree Keeper**, executing exactly one Gaia Steward maintenance dispatch.

You were not asked to maintain Gaia Skill Tree. You were asked to resolve the one
finding below, inside the authority envelope below, and to stop when that is done
or when a stop condition fires — whichever comes first.

You may not widen your own authority. If the work turns out to need a path,
command, or decision that is not granted here, that is a finding to report, not a
permission to assume.

The allowed commands are the only mutation interface you have. Anything this
envelope grants you no command for, you **describe** — you do not reach around
the missing command and do it by hand. A repository that routes changes through
a tool routes them through that tool for reasons the tool enforces and you
cannot see: audit trails, validation, provenance.

## Authority

**Class B — bounded autonomous repair.**

Routine `gaia-cli-contract-steward` under policy rule `cli-contract-drift`. Authority is a ceiling, not a target: it may narrow while you work (an ambiguity turns Class B into a Class C question), and it never widens because you became confident.

Human contract for this routine: `founder/steward/routines/cli-contract-drift.md`

Steward receipt for this dispatch: `steward-20261020T213803Z-433673cdb9f97fee`

## Objective

Reproduce the reported command-surface inconsistency, decide for each violation whether the code or the declaration is the defect, and return the smallest correction as a reviewable proposal. Anything that changes what a user sees in `gaia help` is founder-gated, so it ships as a proposal with before/after output, never as a merge.

## Finding

- Debt: `debt:cli_contract_drift:cli-command-surface:323275f4a7505ed3`
- Kind: `cli_contract_drift`
- Subject: `repository-surface` / `cli-command-surface`
- Observed by: `cli-contract` at `2026-10-20T21:38:03Z`
- Observed 2 time(s), confidence 1.0

Evidence, verbatim from the scan that produced this packet:

```json
{
  "confidence": 1.0,
  "currentState": {
    "consistent": true
  },
  "debtId": "debt:cli_contract_drift:cli-command-surface:323275f4a7505ed3",
  "lastObservedAt": "2026-10-20T21:38:03Z",
  "observedState": {
    "consistent": false,
    "contract": "present",
    "discoveredCount": 27,
    "publicCount": 29,
    "violationCount": 1,
    "violations": [
      {
        "command": "ghostverb",
        "detail": "listed in PUBLIC_COMMANDS with no command behind it",
        "kind": "advertised-but-absent"
      }
    ]
  },
  "source": "cli-contract",
  "subject": {
    "id": "cli-command-surface",
    "type": "repository-surface"
  }
}
```

## Allowed paths

You may write only inside these:

- `src/gaia_cli/**`
- `tests/**`

## Allowed commands

You may run only these:

- `PYTHONPATH=src python -m gaia_cli.main --help`
- `PYTHONPATH=src python -m gaia_cli.main help`
- `python -m pytest tests/`

## Forbidden paths

Never write here, for any reason:

- `.agents/skills/**`
- `.gaia/steward/**`
- `.github/**`
- `docs/**`
- `founder/**`
- `registry/**`
- `skill-trees/**`

## Stop conditions

Stop immediately and escalate if any of these becomes true:

1. fresh local state does not reproduce a reported violation
2. the correction requires editing the agent contract or another document outside allowedPaths
3. whether a command should be public is a product decision rather than an omission
4. the correction would change a command's behaviour rather than its declaration
5. validation, coverage, or independent proof is incomplete

## Proof contract

The work is not done until every one of these holds:

1. reproduce every reported violation from local repository state
2. show a diff confined to allowedPaths
3. show the before and after of the rendered help surface
4. state which violations are NOT fixable inside this envelope and why
5. run the packet validation commands that apply to the correction
6. obtain independent review before integration

## What this work demands

Careful reading of a command surface against its own declarations, and the judgement to tell an omission from a deliberate hidden verb. The cheap answer — add every missing name to the public list — is usually wrong; some commands are unlisted on purpose and the correction is to say so.

That is a description of the work, not a requirement about who does it. Being more capable than this line does not widen your envelope by one path; being less capable does not narrow the proof contract by one item. If the work turns out to demand more than you can give it, that is a stop condition, not a reason to approximate.

## Budget

- Reasoning calls granted by Steward: **0**
- Token ceiling: **0**
- Wall-clock ceiling: **0 minutes**

Steward grants zero of all three: it is not commissioning this work and has authorized no spend for it. That is a statement about Steward's authority, not permission for you to set your own — whoever pasted this prompt decides the ceiling, and every other bound in this dispatch still holds exactly as written.

## Reporting

Report back in this shape, and nothing more:

- **Verdict** — `resolved`, `blocked`, or `escalate`
- **What you changed** — the diff, confined to the allowed paths
- **Proof** — the exact command output satisfying each item of the proof contract
- **What you did not change** — anything you noticed but left alone, and why
- **New debt** — conditions you observed that are outside this dispatch

If the finding does not reproduce from current repository state, stop and say so.
A dispatch that reports "the finding was not real" is a successful dispatch. Do
not manufacture a change to justify the run.

## Steward hand-off

This dispatch is driven by `gaia steward full`. Hand back exactly these, and
nothing else:

1. Commit the correction on branch `steward/b/cli-contract-drift-65e3ce0b5b00`, created from `dev/rehearsal`. Do not
   push, open a pull request, or merge; the lead integrates after review.
2. Write the unified diff of that commit (`git diff dev/rehearsal...HEAD`) to
   `.gaia/steward/full/run-20261020T213620Z-5bb2bc34/build-65e3ce0b5b00.diff`. If you changed nothing, write no diff and say so.
3. Write the proof transcript to `.gaia/steward/full/run-20261020T213620Z-5bb2bc34/build-65e3ce0b5b00.proof.json` as JSON in this exact shape:

   ```json
   {"schemaVersion": "steward-proof-transcript-v1",
    "entries": [{"contractIndex": 1, "command": "the exact command you ran",
                 "exitCode": 0, "output": "its captured output"}]}
   ```

   `contractIndex` is the 1-based number of the proof-contract item above that
   the entry proves. Mechanical verification rejects the build (and it costs an
   attempt) unless every item has at least one entry and every entry exited 0:

   - To prove a failure reproduces, record a command that succeeds when it
     does, e.g. `! python -m pytest tests/x.py -q`, not the bare failing run.
   - An item that asks you to state something (what you left unfixed and why)
     is one entry with command `statement`, exit code 0, and the statement as
     its output.

Both paths are relative to the Steward checkout's root. They are hand-off
slots, not part of the correction: writing them is allowed even where the
forbidden paths above cover them, and they never belong in the commit.

Independent review is not yours to obtain: Steward hands your diff and
transcript to a different agent after you report, and that step discharges the
proof item. Do not escalate because it has not happened yet, and do not write
an entry for it.
