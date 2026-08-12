# Routine — CLI contract drift

| | |
|---|---|
| **Policy rule** | *(not wired — no sensor emits this debt yet)* |
| **Debt kind** | `cli_contract_drift` |
| **Authority** | Class B — bounded autonomous repair |
| **Cadence** | Before each release; otherwise monthly |
| **Routine catalog** | #6 — CLI and Runtime Contract Steward |

---

## What it is for

`gaia` has a promised surface: which commands exist, what `--help` says they do,
which flags are honored, how the registry path resolves, and what the docs claim
about all of it. Drift here is quiet — nothing fails, the CLI simply stops
meaning what it says.

Typical findings: a flag documented but ignored (`--global` on
`gaia skills install` is a live example), a command removed from the shape table
but still dispatchable, help text describing a behavior that changed, a doc
example that no longer runs.

## When it is worth looking

Release-triggered first, calendar second. A release is when the contract becomes
a promise to strangers, so that is when drift stops being cosmetic. Monthly
catches the rest.

Do **not** dispatch this on every CLI PR. A PR that changes the surface *and*
its contract together is correct behavior, not drift.

## Envelope to grant

- **May write:** `src/gaia_cli/**`, `tests/**`, CLI documentation
- **Never writes:** `registry/**`, `skill-trees/**`, `docs/graph/**`, `founder/**`
- **May run:** `gaia --help` and subcommand help, `python -m pytest`

Run the CLI from the checkout under review — `PYTHONPATH=src python -m gaia_cli …`
— never a globally installed wheel, or the routine tests the wrong code.

## Stop conditions

1. Closing the gap is a compatibility decision: whether to keep, deprecate, or
   remove a surface users may depend on.
2. The fix requires a change to registry-path resolution policy.
3. Fixing the documentation would misrepresent a behavior that is itself wrong —
   the code is the bug, and that is a separate dispatch.
4. Output that a human reads would change. **Visible CLI output is human-gated**;
   prepare before/after and stop.

## Done means

- Each drift item is either fixed or explicitly reported as a compatibility question
- A test pins the contract so the same drift cannot recur silently
- No help text was edited to match a behavior nobody decided to keep

## Founder notes

- The tempting failure mode is "make the docs match the code." Sometimes the
  code is what drifted. Ask which one you actually ratified.
- A known gap deliberately left open is not drift. If it is documented as a gap,
  the routine should confirm the documentation, not close the gap on its own
  authority.
