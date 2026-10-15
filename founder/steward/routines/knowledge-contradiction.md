# Routine — Knowledge contradiction

| | |
|---|---|
| **Policy rule** | `knowledge-contradiction` — founder-review routing proposal in #2105 |
| **Sensor** | Existing `knowledge-contradiction` sensor — partial coverage, extended rather than duplicated |
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

The current sensor checks selected policy/schema/document invariants and a
finite shared set of retired trust-guidance claims from #2052. The shared helper
`src/gaia_cli/steward/knowledge_contracts.py` lists the active inputs; its tests
reuse the authority-map agreement contract rather than defining a new trust
formula. Equal skill mirrors do not prove semantic consistency. Missing, empty,
unreadable or oversized required semantic inputs fail to unknown coverage.
Historical handovers, retrospectives and unlisted archives are not scanned.
This is not a general natural-language contradiction detector.

## When it is worth looking

Monthly for accumulated drift, and immediately after a founder ruling lands —
that is when a decision exists in one place and not yet in the others, which is
the highest-value moment for this routine by a wide margin.

## Envelope to grant

The proposed `POLICY.yaml` packet is authoritative; this routine cannot widen it.

- **May write:** `docs/agents/**` and `tests/steward/**`, only for a reproduced,
  source-settled correction/proposal.
- **Never writes:** root documents, either skill tree, `registry/**`,
  `skill-trees/**`, `docs/graph/**`, `founder/**`, `.github/**`, `.gaia/steward/**`
  or source code.
- **May run:** only the packet's read-only status and focused test commands.

A finding in a protected source can still be observed. The packet must diagnose
it and stop, not grant itself that source. Naming/product decisions and unsettled
source precedence remain human-governed. The routing proposal requires founder
review before integration to main.

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
- Protected-source findings return a diagnosis and stop without widening scope
- Historical positive fixtures and active negative controls reproduce the claim
- Independent review is required before integration
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
