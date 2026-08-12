# Routine — Repository hygiene

| | |
|---|---|
| **Policy rule** | *(not wired — no sensor emits this debt yet)* |
| **Debt kind** | `repository_hygiene` |
| **Authority** | Class B — bounded autonomous repair |
| **Cadence** | Worth looking weekly |
| **Routine catalog** | #12 — Artifact, Branch, and Repository Hygiene Sentinel |

---

## What it is for

The slow accumulation nobody owns: generated artifacts that drifted from their
sources, branches whose PRs merged months ago, files referenced by nothing,
duplicated fixtures, dead scripts.

Hygiene is the *cheapest* Class B routine and the one most likely to
manufacture work if you let it. The discipline is: report first, repair only
what is unambiguous.

## When it is worth looking

Weekly. Hygiene debt genuinely accrues with time rather than with events, which
makes it one of the few routines where a calendar is a defensible trigger — but
the run must still be allowed to find nothing and stop.

## Envelope to grant

- **May write:** the specific artifact paths named in the finding, `scripts/**`, `tests/**`
- **Never writes:** `registry/**`, `skill-trees/**`, `docs/graph/**`, `founder/**`, `.github/workflows/**`
- **May run:** the repository's own regeneration and validation commands, `git status`, `python -m pytest`

## Stop conditions

1. A file's "unused" status depends on dynamic discovery, packaging, or a public
   entry point — anything where deletion could break a consumer you cannot see.
2. Removing an artifact would change what the website serves (Class S).
3. A branch's work is not provably merged.
4. The cleanup is larger than the finding that justified it.

Condition 1 retires more hygiene dispatches than every other condition combined.
"I cannot find a reference" is not "there is no reference." Report it and let a
human decide.

## Done means

- Every removal names the evidence that made it safe
- The regeneration is reproducible: running it twice produces no second diff
- No guard, ignore rule, or test was weakened to make the diff clean

## Founder notes

- Deletion is not reversible in the way a content fix is. Prefer a report you
  approve over a repair you have to audit.
- Class P vs Class S is the trap here. `docs/graph/**` is served to browsers and
  belongs in git; `registry/gaia.json` is pipeline-internal and does not. A
  hygiene routine that "cleans up" a Class S artifact takes the site dark — this
  has happened once already (PR #798 retro).
