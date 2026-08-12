# Routine — Knowledge contradiction

| | |
|---|---|
| **Policy rule** | *(not wired — no sensor emits this debt yet)* |
| **Debt kind** | `knowledge_contradiction` |
| **Authority** | Class B — bounded autonomous repair |
| **Cadence** | Monthly, and after any founder ruling |
| **Routine catalog** | #17 — Knowledge, Nomenclature, and Agent-Surface Editor |

---

## What it is for

Gaia carries a lot of prose that agents treat as executable: `CLAUDE.md`,
`CONTEXT.md`, `META.md`, `founder/**`, the agent skill trees, `docs/agents/**`.
When two of those disagree, every agent that reads them inherits the
disagreement — and picks a side silently.

This routine finds **exact** contradictions: two documents stating incompatible
facts about the same thing. A stale example, a dead link, a mirror that fell
behind its twin.

It does **not** do editorial improvement. Rewriting for clarity is not a
maintenance debt, and a routine that starts polishing prose will never stop.

## When it is worth looking

Monthly for accumulated drift, and immediately after a founder ruling lands —
that is when a decision exists in one place and not yet in the others, which is
the highest-value moment for this routine by a wide margin.

## Envelope to grant

- **May write:** the directory subtree holding the documents named in the finding. Policy expresses scopes as `<dir>/**` subtrees, so a routine touching a root-level file such as `CLAUDE.md` cannot be wired without widening that scope — prefer running it by hand over granting the repository root.
- **Never writes:** `registry/**`, `skill-trees/**`, `docs/graph/**`, `founder/**`, source code
- **May run:** read-only search, link checks, the mirror check commands

## Stop conditions

1. The two sources disagree because the underlying question is **unsettled**.
   That is a Class C decision, not a wording fix.
2. The wording encodes a product or policy ruling — naming, positioning, what a
   thing *is*. Only the founder retires a term.
3. It is not clear which document is authoritative.
4. The "contradiction" is a document describing a past state on purpose
   (a retro, a handover, an archived decision). History is allowed to disagree
   with the present.

Condition 4 catches most false positives. `founder/handovers/**` records what was
true then; correcting it destroys the audit trail.

## Done means

- Every correction points at the authoritative source that settles it
- Mirrored files (`.agents/skills/` ↔ `.claude/skills/`) stay byte-identical —
  and note that this specific drift is **Class A**, repaired automatically by
  the `agent-skill-mirror` executor, so it should never reach this routine
- No lexicon entry was touched. A ban retires a word, not the method it named;
  the lexicon changes only when a ruling is actually made

## Founder notes

- The lexicon serves the work. If this routine ever proposes a vocabulary
  review, reject it — that is exactly the ceremony the founder ruling of
  2026-07-29 forbade.
- The highest-value dispatch of this routine is the one you run the day after
  you decide something. Consider it part of ratifying a ruling rather than a
  monthly chore.
