---
name: dev-ingest-named
description: >-
  Playbook for landing one evidence-approved single-skill intake whose L4
  topology is a NEW fusion generic plus one named implementation: create the
  generic and its prerequisites, create the named skill, ingest each verified
  evidence row, and appraise Trust Magnitude — then stop at the calibration
  gate. Use when: an intake issue carries intake:topology-approved and
  intake:evidence-approved, the promotion PR review/meta/intake-<N> is open, and
  a reviewed evidence manifest exists. Triggers: "ingest the approved intake",
  "land intake #N", "add the generic and named skill for this intake", "run the
  ingest for the evidence-approved batch". Not for suites (use
  gaia-fuse-full-suite), not for an existing generic (add the named skill with
  `gaia dev add --named` directly), and not for star calibration (dev-calibrate).
playbookVersion: 1
class: B
objective: >-
  Take one L4-approved, evidence-approved single-skill intake whose ratified
  topology is a new fusion generic, and reach a state where the generic, its
  prerequisites, the named skill and every approved evidence row exist through
  CLI verbs only, Trust Magnitude is appraised, and the calibration decision is
  left, unapplied, to a human.
capability: >-
  Reading an intake's recorded L4 decision and its reviewed evidence manifest,
  confirming the ratified generic does not already exist, translating each
  approved manifest row into the exact typed evidence flags the CLI supports
  without guessing a number, and reporting the appraised Trust Magnitude with
  its sensitivity to rows a prior audit flagged.
preconditions:
  - the intake issue carries intake:topology-approved and intake:evidence-approved, and its L4 decision comment names the generic id, type, prerequisites and the named contributor/skill
  - a reviewed evidence manifest exists whose every row lists source URL, evidence type, source-start date, verifiable numeric payload and notes, and every excluded row is recorded with its reason
  - gaia whoami resolves to verifier, override, or bootstrap, not denied
  - the working tree is on the promotion branch review/meta/intake-<N>, never main
  - the active gaia is this repo's source (compare `python3 -m gaia_cli.main --version` to pyproject.toml), and registry/gaia.json is fresh
steps:
  - id: snapshot-generics
    run: gaia dev list --generic --json > {generic_snapshot}
    proves: the live generic catalog is captured before any write
  - id: confirm-new-generic
    judgment: PROCEED_NEW_GENERIC | GENERIC_EXISTS | BLOCKED_NO_L4_RECORD
    rules: >-
      PROCEED_NEW_GENERIC only when the L4 decision comment names the generic id
      and the id is absent from the snapshot, and every prerequisite id is
      present in it. GENERIC_EXISTS when the id is already in the snapshot.
      BLOCKED_NO_L4_RECORD when the ratified id, type, prerequisites or named
      identity cannot be read from the intake record. Never invent or rename an
      id, and never treat retrieval similarity as the decision.
  - id: add-generic
    run: gaia dev add {generic_name} --id {generic_id} --type fusion --description {generic_description} --no-build
    proves: registry/nodes/fusion/<generic_id>.json exists with a CLI-written add timeline event
  - id: link-prerequisites
    run: gaia dev link {generic_id} {prerequisite_ids} --no-build
    proves: the generic node lists exactly the ratified prerequisite ids
  - id: add-named
    run: gaia dev add {named_name} --named --contributor {contributor} --generic-ref {generic_id} --description {named_description} --title {named_title} --extra-fields {links_json} --no-build
    proves: registry/named/<contributor>/<skill>.md exists with genericSkillRef set and links.github on a blob/<branch>/ URL
  - id: ingest-evidence
    run: gaia dev evidence {skill_id} {source_url} --type {evidence_type} --notes {notes} --source-started-at {source_started_at} --no-build
    proves: one row for one manifest entry is written by the CLI; repeat this step once per approved row, adding the numeric flags that evidence type supports (gaia dev evidence --help) and only values the manifest states
  - id: appraise
    run: python3 scripts/trust_appraise.py --skill {skill_id}
    proves: live Trust Magnitude, Overall Trust Grade and per-row scores are captured from the named frontmatter
  - id: inspect
    run: python3 scripts/inspectTrustMagnitude.py --skill {skill_id}
    proves: the canonical inspector agrees with the appraisal and shows the rows ingested and the stars the engine would resolve
  - id: report-sensitivity
    judgment: SENSITIVITY_REPORTED | NO_FLAGGED_ROWS
    rules: >-
      When the evidence audit flagged any row (for example author-amplifying
      coverage or a repository-level count with unverified velocity), compute in
      memory, on a copy of the frontmatter with no registry write, the Trust
      Magnitude and grade without each flagged row, and present them beside the
      full result. NO_FLAGGED_ROWS when the audit flagged none. Never remove a
      row or rewrite a note to move the grade.
stopConditions:
  - confirm-new-generic resolves GENERIC_EXISTS — this playbook does not apply; land in the review packet, add the named skill against the existing generic with gaia dev add --named
  - confirm-new-generic resolves BLOCKED_NO_L4_RECORD — land in the founder queue; do not infer the topology
  - a CLI pre-flight rejects any add, link or evidence write — land in the review packet with the verbatim error; the fix is the input, not a hand edit of registry files
  - a manifest row lacks a verifiable numeric payload for its evidence type — land in the review packet and ingest no guessed number
  - calibration is next — land in the founder queue with the appraisal table; this playbook never runs gaia dev calibrate
proof:
  - the generic node, the named skill and one evidence row per approved manifest entry exist, each written by a gaia dev verb with its timeline event, and no registry file was hand edited
  - appraise and inspect both ran after the last evidence row and report the same Trust Magnitude and grade
  - the stored level was not changed by this playbook
done: >-
  The generic, its prerequisites, the named skill and every approved evidence row
  exist through CLI writes only, Trust Magnitude is appraised with sensitivity to
  flagged rows reported, no star level has been applied, and the calibration
  decision is waiting in the review packet for a human.
---

## Overview

This playbook is the ingest half of an approved single-skill intake whose L4
decision created a new fusion generic. It exists because the order matters and
is easy to get wrong: a named skill cannot be created before its generic, and
evidence cannot be written before the named skill. It deliberately stops before
calibration.

## Handoffs

- **Calibration:** run the `dev-calibrate` playbook only after a human approves
  the star level against the appraisal table. A newly added named skill starts at
  a placeholder level; the Trust Magnitude band is not applied automatically.
- **Build, stage, validate, PR:** `/gaia-review-meta-close` owns the single build,
  the allowlisted staging, `gaia dev validate` (which needs the build because the
  build stamps Trust Magnitude), and the pull request. Do not build here.
- **Suites:** a contributor's suite capstone is `/gaia-fuse-full-suite`.

## Batch use

One intake, one named skill. For several skills in one batch, repeat
`add-named` through `report-sensitivity` per skill after the shared generics
exist. Evidence rows are written one at a time; stop on the first failure.

## Reference

- `founder/steward/PLAYBOOKS.md` — the playbook contract this file opts into.
- `.agents/skills/gaia-ingest-batch/SKILL.md` — the row-level ingestion contract.
- `.agents/skills/gaia-review-meta-close/SKILL.md` — build, stage, validate, PR.
- `trigger-prompts.md` — realistic positive and negative prompts for triggering.
