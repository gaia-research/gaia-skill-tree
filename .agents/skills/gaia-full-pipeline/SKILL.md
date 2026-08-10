---
name: gaia-full-pipeline
description: >-
  End-to-end Gaia curation pipeline orchestrator. Routes each phase to its dedicated
  skill and keeps you on track from first discovery to closed intake. Use when starting
  a fresh curation run or when you want a single skill to hold the sequence together
  without duplicating each phase's instructions. Trigger phrases: "/gaia-full-pipeline",
  "run the full pipeline", "start a curation from scratch", "take this skill through
  the full pipeline", "curate end-to-end", "pipeline run", "full curation flow".
  Fused from: gaia-curate + ev-pipeline + gaia-ingest + gaia-intake-close.
version: 1.0.0
---

# gaia-full-pipeline

Orchestrates the complete curation lifecycle. Each phase delegates to its canonical skill — this skill is the **routing layer**, not the implementation. Read the referenced skill for the exact commands at each phase.

> **Lost at any point?** Run `/gaia-consult` to open the reference document with the exact command for your current phase.

---

## Pipeline sequence

```
① /gaia-curate  →  ② L4 (human gate)  →  ③ gaia push + /pr
→  ④ /ev-pipeline  →  ⑤ /gaia-ingest  →  ⑥ /gaia-intake-close
```

Suite detour (if applicable): between ⑤ and ⑥ → `/gaia-fuse-full-suite`

---

## Phase 1 — Discovery

**Skill:** `/gaia-curate`

Fetch the upstream SKILL.md, run prefill, apply the 6-rule mapping decision, write a `discovery-packet-v2` to `registry-for-review/discovery-packets/`, and validate the packet. Stop at L4.

Key constraints:
- Snapshot generics *before* worker dispatch: `gaia dev list --generic --json > /tmp/generic-snapshot.json`
- Decision is mechanical (first matching rule wins) — no re-ranking
- Packet must exit `python3 scripts/validate_discovery_packet.py --generic-snapshot ... <packet>` with 0 errors

→ See full commands: [`/gaia-curate`](../gaia-curate/SKILL.md) and [`CURATION-CORE.md`](../gaia-curate/CURATION-CORE.md)

---

## Phase 2 — L4 Human Gate 🛑

**No skill — human only.**

Open the packet JSON. Check:
1. Mapping decision is correct for the skill's actual capability
2. `source.url` is a `blob/` URL (not `tree/`)
3. `normalized.description` is verbatim from frontmatter

Append `l4Resolution` with the ratified `generic`, `named`, and `upstreamSkillFileUrl`. Re-validate.

---

## Phase 3 — Branch + Push + PR

**Skills:** [`/pr`](../pr/SKILL.md)

```bash
git checkout -b review/meta/<handle>--<skill>
gaia push --from-file <packet>.json --dry-run   # preview
gaia push --from-file <packet>.json             # opens intake issue
git add . && git commit -m "feat(intake): ..." && git push -u origin <branch>
gh pr create --draft --title "..." --body-file /tmp/pr-body.md
```

---

## Phase 4 — Evidence Verification

**Skill:** [`/ev-pipeline`](../ev-pipeline/SKILL.md)

Runs five sub-phases in order. Each has a dedicated skill if you need to re-run one in isolation:

| Sub-phase | Skill | When to skip |
|---|---|---|
| Phase 0 — ev-discovery | [`/ev-discovery`](../ev-discovery/SKILL.md) | Skip for Stage-1 intakes; run only for promotion candidates needing `benchmark-result`, `arxiv`, or `peer-review` |
| Phase 1 — ev-collection | [`/ev-collection`](../ev-collection/SKILL.md) | Never skip — rebuilds the whole-registry lake |
| Phase 2 — ev-star-verification | [`/ev-star-verification`](../ev-star-verification/SKILL.md) | Skip only if no `github-stars-own` rows exist |
| Phase 2B — ev-benchmark-verification | [`/ev-benchmark-verification`](../ev-benchmark-verification/SKILL.md) | Skip if no `benchmark-result` rows |
| Phase 3 — ev-adversarial-audit | [`/ev-adversarial-audit`](../ev-adversarial-audit/SKILL.md) | Never skip |
| Phase 4 — ev-link-validation | [`/ev-link-validation`](../ev-link-validation/SKILL.md) | Never skip |

**Human gate:** Review the source report. Approve rows for ingest. Remove dead-link, subjective, or type-mismatched rows.

---

## Phase 5 — Evidence Ingest

**Skill:** [`/gaia-ingest`](../gaia-ingest/SKILL.md) (single row) · [`/gaia-ingest-batch`](../gaia-ingest-batch/SKILL.md) (multiple rows)

Pattern for every row: one `gaia dev evidence` call with `--no-build`, then one final `gaia dev build`.

```bash
GAIA_OPERATOR_OVERRIDE=1 gaia dev evidence contributor/skill "<url>" \
  --type <evidence-type> <numeric-flags> \
  --notes "..." --source-started-at YYYY-MM-DD --no-build

# ... repeat per row ...

GAIA_OPERATOR_OVERRIDE=1 gaia dev build
PYTHONPATH=src python3 scripts/trust_appraise.py --skill contributor/skill
```

**Human gate:** Review TM output. Approve the star calibration explicitly before running `gaia dev calibrate`.

Trust Magnitude → star grade reference:

| Grade | TM | Max stars |
|---|---|---|
| D | 1.0–1.9 | 1★ |
| C | 2.0–3.9 | 2★ (badge floor) |
| B | 4.0–6.9 | 3★ |
| A | 7.0–9.9 | 4★ |
| S | 10.0+ | 5★–6★ |

→ For methodology details: [`/trust-methodology-consult`](../trust-methodology-consult/SKILL.md)

---

## Suite detour (between Phase 5 and Phase 6) 🔀

**Run this only when curating a suite capstone** — i.e. the contributor has 3+ named skills and the intake is fusing them into a single fusion node.

**Skill:** [`/gaia-fuse-full-suite`](../gaia-fuse-full-suite/SKILL.md)

```bash
# Verify all component named skills are in the registry
ls registry/named/<contributor>/

# Run the fusion
gaia dev fuse <fusion-id> \
  --name "<Fusion Name>" \
  --description "<one-sentence synthesis>" \
  --prereqs <id-1>,<id-2>,... \
  --named-capstone <contributor>/<capstone-slug> \
  --suite-components <named-id-1>,<named-id-2>,...

GAIA_OPERATOR_OVERRIDE=1 gaia dev validate
```

Suite rank gates (TM is the sole gate — no per-star Evidence Floor):
- **4★ Extra** — Origin Contributor recorded + TM ≥ 100
- **5★ Ultimate** — Origin in `suiteComponents` + 5 A-graded origins + TM ≥ 250
- **6★ Apex** — full 6-predicate Apex Gate (see `META.md`)

---

## Phase 6 — Close

**Skill:** [`/gaia-intake-close`](../gaia-intake-close/SKILL.md)

```bash
gh pr ready <PR>
gh pr checks <PR>                                   # wait for green
gh pr merge <PR> --subject "feat(registry): ... [closes #ISSUE]"
gh pr comment <PR> --body-file /tmp/pr-close-comment.md
gh issue comment <ISSUE> --body-file /tmp/issue-close-comment.md
gh issue close <ISSUE>
GAIA_OPERATOR_OVERRIDE=1 gaia dev docs             # regenerate Class S artifacts
```

Closing comment structure (PR): evidence findings table + `/trust-appraise` output + badge status note.
Closing comment structure (issue): decision + TM grade + path-to-next-level + `@contributor` tag.

→ See full comment templates: [`/gaia-intake-close`](../gaia-intake-close/SKILL.md)

---

## Triggers for sub-skills

If you need to re-enter the pipeline mid-flow, invoke the sub-skill directly:

| Where you are | Invoke |
|---|---|
| Just validated packet, ready for L4 | (human step — no skill) |
| Post-L4, ready to push | `/pr` |
| Evidence collection only | `/ev-collection` |
| Star verification only | `/ev-star-verification` |
| Adversarial audit only | `/ev-adversarial-audit` |
| Link validation only | `/ev-link-validation` |
| Single evidence row | `/gaia-ingest` |
| Batch evidence rows | `/gaia-ingest-batch` |
| Suite fusion only | `/gaia-fuse-full-suite` |
| Closing comments only | `/gaia-intake-close` |
| Regenerate artifacts only | `/regen` or `/gaia-docs-sync` |
| Lost / unsure of command | `/gaia-consult` |
