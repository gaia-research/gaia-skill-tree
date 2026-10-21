# Routine — Unused-import cleanup

| | |
|---|---|
| **Policy rule** | `unused-import-cleanup` |
| **Sensor** | `dead-code` — module-level imports with no in-module read |
| **Debt kind** | `unused_import` |
| **Authority** | Class B — bounded autonomous repair |
| **Cadence** | Worth looking on a normal scan |
| **Routine catalog** | #1 — Dead-Code Gardener |
| **Decision** | `steward-class-b-route-unused-import` (founder authorization 2026-10-21) |

---

## What it is for

Remove imports the detector proved are never read in their own module. One
debt is one source file; the builder touches that file and nothing else.

## Envelope to grant

The `POLICY.yaml` rule is authoritative; this guide cannot widen it.

- **May write:** the debt's subject file only. The policy glob is wider
  (`src/gaia_cli/**`, `scripts/**`, `tests/**`) because policy paths are static;
  the stop conditions below narrow it to the one file and the verifier rejects
  any other path in the diff.
- **Never writes:** registry data, docs, founder surfaces, workflows, skills.
- **May run:** `python -m pytest` on the importing package and
  `python -m compileall` on the file.

## Keep, do not remove

1. `__init__.py` re-export surfaces, star imports, guarded (`try` / `TYPE_CHECKING`) imports and `noqa` lines (the detector already skips these; stop if one appears in the packet).
2. Plain `import x` the packet marks `sideEffectPossible`, unless the side effect is proven absent.
3. Anything another module imports from this one.

## Stop conditions

1. The diff would touch any file other than the subject file.
2. A flagged import may have a side effect you cannot rule out.
3. Tests or compileall fail after the change.
4. The finding does not reproduce on the current head.

"I cannot find a consumer" is not "there is no consumer". Report and stop.

## Proof

Reproduce the finding, show a one-file diff, run the pytest and compileall
commands above and paste their exact results. A different, fresh agent verifies.
