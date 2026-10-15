# Routine — Repository hygiene

| | |
|---|---|
| **Policy rule** | `repository-hygiene` — founder-review proposal in #2105 |
| **Sensor** | `repository-hygiene` — partial, read-only tracked Class P inventory |
| **Debt kind** | `repository_hygiene` |
| **Authority** | Class B — bounded autonomous repair |
| **Cadence** | Worth looking weekly |
| **Routine catalog** | #12 — Artifact, Branch, and Repository Hygiene Sentinel |

---

## What it is for

The slow accumulation nobody owns: generated artifacts that drifted from their
sources, branches whose PRs merged months ago, files referenced by nothing,
duplicated fixtures, dead scripts.

Hygiene is particularly likely to manufacture work if you let it. The discipline
is: report first, propose only what is proven.

The current sensor covers only the eight Class P paths enumerated in
`src/gaia_cli/steward/repository_hygiene.py`. It reports their presence in Git's
tracked index, not their age or apparent usefulness. Intentionally tracked
`registry/real-skills.{json,md}` and the bundled benchmark catalog are excluded
because their ownership is not settled by the Class P prose alone. Class S
files, untracked output, mirrors and generated projection content are not this
sensor's responsibility. Git failure, wrong root or incomplete inventory becomes
unknown coverage, never a healthy result.

## When it is worth looking

Observe on a normal scan. Weekly is a ceiling on attention, not a debt trigger.
A clean index is a successful no-op regardless of how much time has passed.

## Envelope to grant

The proposed `POLICY.yaml` packet is authoritative; this routine cannot widen it.

- **May write:** `scripts/**` and `tests/steward/**`, solely for a bounded proposal.
- **Never writes:** tracked Class P data, `registry/**`, `skill-trees/**`,
  `docs/graph/**`, `founder/**`, `.github/**`, either skill tree, or `src/**`.
- **May run:** only the packet's read-only Git inventory/status and focused tests.
- **No deletion:** an index leak normally requires an owner-reviewed disposition
  outside this envelope. Return the exact diagnosis and stop; no `git rm`,
  regeneration, branch removal or canonical write is granted.

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

- Each finding reproduces from the read-only index inventory
- Any out-of-envelope disposition is explicit; no deletion or regeneration ran
- Equivalent scans have stable identity; clean input produces no maintenance debt
- No guard, ignore rule, or test was weakened to make the diff clean
- Independent review is required before integration

## Founder notes

- Deletion is not reversible in the way a content fix is. Prefer a report you
  approve over a repair you have to audit.
- Class P vs Class S is the trap here. `docs/graph/**` is served to browsers and
  belongs in git; `registry/gaia.json` is pipeline-internal and does not. A
  hygiene routine that "cleans up" a Class S artifact takes the site dark — this
  has happened once already (PR #798 retro).
