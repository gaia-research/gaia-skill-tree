---
name: trust-methodology-consult
description: >
  Consult this skill BEFORE proposing a fix to any CLI gap or schema gap that
  touches evidence, trust magnitude, evidence types, evidence grades, the TM
  formula, or star-level promotion gates. Also read it whenever an issue
  mentions citations, stars, commits, contributors, views, reviewers,
  percentile, arxiv, github-stars-own, repo-own, social-signal,
  benchmark-result, peer-review, self-attestation, fusion-recipe,
  verifier-attestation, or proxy-containment — those are the 10 canonical
  evidence types and the raw inputs that feed their formulas. Also read it
  when asked whether a skill qualifies for a given star level (0★–6★): the
  Star Bar and promotion gates live in `META.md`, not in the TM methodology
  page. Reading both prevents proposing a calibration that satisfies the TM
  grade threshold but violates a Star Bar installability or link requirement.
---

# Consult the trust methodology before touching CLI/schema evidence surface

The Gaia trust surface is a three-layer contract. Skipping any layer when
proposing a fix guarantees you either widen or narrow it incorrectly:

| Layer | Source of truth |
|---|---|
| **Concept** — what the numbers mean and why they exist | `docs/codex/trust-methodology.html` (also mirrored in `docs/meta/2026-06-trust-methodology.md` and the G7 supersession note at `docs/meta/2026-06-17-g7-trust-magnitude-supersession.md`) |
| **Compute** — how the numbers are actually produced | `src/gaia_cli/trustMagnitude.py` (backend); `docs/js/tm-config.js` (frontend SoT) |
| **Persistence** — what shape the CLI writes and the schema bounds | `src/gaia_cli/commands/dev/evidence.py` (writer) + `registry/schema/skill.schema.json` + `registry/schema/namedSkill.schema.json` (bounds) |
| **Star level gates** — what a skill must satisfy to hold 0★–6★ | `META.md` §2 (Star Bar, installability, blob-link requirement, 4★+ live evidence rule, Specialist Path rubric, Apex 6-predicate gate) |

When an issue lands as "CLI gap" or "schema gap" on this surface, ONE of those
layers is out of step with the other two. Your first job is to identify which.

## Star Bar — read META.md before calibrating any 3★+

The TM methodology page covers *how scores are computed*. It does **not** cover
*what a skill must have to hold a given star level*. Those gates live in
`META.md` §2 and must be checked independently:

| Level | Gate |
|---|---|
| 0★–2★ | No link requirement; `installable: false` permitted |
| 3★+ | `links.github` **must** be a verified blob URL (`.../blob/<branch>/...`). Bare repo root → hard-demote to 1★. |
| 4★+ | Live, verifiable usage evidence required. Seed/placeholder evidence is insufficient. |
| 4★+ Specialist | Vendor-locked skills: Depth-of-Integration rubric (META.md §2.3) |
| 6★ Apex | Grade S + 6 active predicates from G7 Trust Taxonomy RFC |

When asked "should this skill be 4★?", run this check **before** computing TM:
1. Does `links.github` point to a concrete file via `/blob/`?
2. Is every scoring evidence row live and non-seed?
3. Does `overallTrustGrade` ≥ B (TM ≥ 50)? Grade A (TM ≥ 100) is the norm for 4★ in practice.

If any gate fails, the correct action is to fix the gate or demote — not to
add more evidence rows to compensate.

## The read pass — do this before writing code

1. **Read the methodology page.** Open `docs/codex/trust-methodology.html`.
   The "10 evidence types — base formula at a glance" table (search for
   `base formula`) lists every evidence type and the raw input fields its
   formula consumes. Confirm the field the issue names appears there.
2. **Confirm the CLI writes it.** Grep `src/gaia_cli/commands/dev/evidence.py`
   for the field name. If the flag exists and the writer stores it, the CLI
   already treats that field as persistable.
3. **Confirm the TM engine reads it.** Grep `src/gaia_cli/trustMagnitude.py`
   for the field name via `row.get("<field>", ...)`. If the engine reads it,
   the field is a first-class input, not a derived value.
4. **Confirm the schema declares it.** Open the relevant `evidenceEntry`
   definition and check the `properties` block. Because both schemas set
   `additionalProperties: false`, any field the CLI writes but the schema
   does not list will be rejected on the first `gaia dev validate` run —
   which is exactly what surfaces most of these gaps.
5. **Validate the failure locally, don't infer it.** Write a tiny probe file
   with the field, run `jsonschema.validate(instance, schema)`, and observe
   the exact rejection path. Do not trust an issue's diagnosis until the
   local repro matches.

## The design principle you must not violate

The methodology page states, verbatim:

> Trust Magnitude (TM) is the aggregate numeric signal for a skill's
> trustworthiness. It is computed at build time from a skill's evidence
> inventory, never stored on a node.

That sentence pins the direction of every fix:

- **Raw inputs are the persisted state.** Fields like `citations`, `stars`,
  `commits`, `contributors`, `views`, `reviewers`, `percentile`, and
  `skillCountInRepo` are the evidence inventory. They MUST be storable on an
  evidence row so `gaia dev calibrate-evidence-grades` can re-derive grades
  from them at any future time.
- **Derived fields are ephemeral.** `trustMagnitude` and `overallTrustGrade`
  are computed. They may appear on the merged graph or in reports but must
  not become the persistence contract — otherwise you cannot recompute them
  when the formula changes.
- **Do not "collapse" raw inputs into `trustNumber` as a workaround.** Writing
  only a pre-computed `trustNumber` to sidestep a schema rejection erases the
  audit chain ("why did this row score 73?") and breaks the recompute path.
  It is a legitimate one-off remediation when a schema fix is blocked; it is
  never a design.

## Decision matrix — what kind of gap is it?

| Symptom | Most likely gap | Fix direction |
|---|---|---|
| CLI writes field `X`; TM engine reads field `X`; schema rejects `X` | **Schema gap** — schemas lag documented reality | Add `X` to `evidenceEntry.properties` in both `skill.schema.json` and `namedSkill.schema.json`; keep the two schemas symmetric |
| CLI writes field `X`; TM engine ignores `X`; schema silent | **CLI over-writes** — the field is dead weight | Remove the write in `evidence.py`; document why |
| CLI has no flag for `X`; TM engine reads `X`; schema silent | **CLI gap** — TM depends on data no operator can add | Add the flag + writer, then verify schema accepts it (add if needed) |
| Methodology page mentions a metric not in the CLI or TM engine | **Doc drift** — treat as spec, not law | Open a discussion issue before touching any of the three layers |

## The write pass — order matters

The methodology page's own "if you change a formula" checklist applies, in
this exact order. Do not skip a step or reorder them:

1. `docs/js/tm-config.js` — frontend SoT for the formula
2. `src/gaia_cli/trustMagnitude.py` — backend implementation
3. `docs/codex/trust-methodology.html` — the doc itself
4. `registry/schema/meta.json` — `perRowGradeThresholds` and `gradeCeiling`
5. `tests/test_row_grading.py` + `tests/test_calibrate_evidence_grades.py`
6. `python scripts/build_docs.py` — regenerate everything
7. `gaia dev calibrate-evidence-grades --yes` — refresh stored grades

If the gap is schema-only (as in Issue #941 — the field is already read and
written, only the schema disagrees), most of that list does not apply —
only steps 4-ish (extend the schema), 6 (regen docs), and 7 (rerun the
calibration if any stored grade shifted) matter. Small schema changes still
belong on a `schema/*` branch per the branch-scope rules.

## Helper: recompute a single node's stored TM (`scripts/recompute_one_tm.py`)

A recurring flavour of CLI gap: the live CLI does **not** recompute and persist
a named skill's `trustMagnitude`/`overallTrustGrade` when evidence is added, a
suite is fused, or a level is calibrated. The leaderboard recomputes at build
time (`computeTrustMagnitude`) and looks correct, but consumers that trust the
**stored** frontmatter field — the contributors API, badges, and the
Hall-of-Heroes `topSkill` selection — keep showing the stale value.

Until that write-back is closed in `gaia dev`, use the vendored helper for a
surgical, idempotent, single-node fix (it reuses the canonical write-back logic
from `scripts/archive/migrateTrustMagnitude.py`, so no unrelated node is swept
into the diff):

    python3 .claude/skills/trust-methodology-consult/scripts/recompute_one_tm.py <owner/skill-id> --dry-run
    python3 .claude/skills/trust-methodology-consult/scripts/recompute_one_tm.py <owner/skill-id>
    gaia dev docs   # propagate the new value into docs/ artifacts

This is a *remediation*, not a design — the durable fix is to make the mutation
commands recompute+persist. Do not hand-edit the stored fields.

## What NOT to do

- Do not "just remove the field" from the CLI when the TM engine still reads
  it — you'll silently zero out every skill's citations-based magnitude.
- Do not add the field to only one of the two schemas. Named and generic
  evidence entries share the same shape; asymmetric schemas guarantee the
  next reviewer will re-file the same issue.
- Do not persist a pre-computed `trustNumber` in place of the raw input as a
  "design" — see "The design principle you must not violate" above.
- Do not re-derive the answer from memory. The methodology has been superseded
  once already (2026-06-17, G7). Always re-read the page before acting.
