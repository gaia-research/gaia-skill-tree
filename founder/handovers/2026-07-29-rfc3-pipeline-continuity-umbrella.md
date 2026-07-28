# RFC3 — Pipeline continuity umbrella: no gaps from curation to tree

One-line summary: Close the end-to-end continuity gaps so a skill's path `curation → evidence → verification → tree` has NO holes — a provenance sidecar ledger at ingest, discovery + intake timeline events, a reconciled action enum, an intermediate status ladder, re-enabled intake validation, and a documented (deferred) audit-coverage extension.

Status: PLANNED (depends RFC1 + #1148 + RFC2)
Date: 2026-07-29
Branch: `dev/gaia-curate-v2-pipeline`
Milestone: Program 5 — Gaia Skill Tree Core (#16)
Covers: end-to-end pipeline continuity; depends on **RFC1 (gaia-curate v2 named-first)** + #1148 + **RFC2 (evidence-seed + provisional TM)** landing.

---

## 1. Problem / Motivation

RFC1 fixes named-first curation + prefill; RFC2 builds the evidence bridge (adapter, evidence-seed, additive loop). What remains are the **continuity** gaps — the places where a skill loses its history or becomes un-queryable as it moves through the pipeline:

- A registry node has **no back-link** to the discovery packet / intake batch / intake issue / crawler origin that produced it (GAP10), and **crawler provenance is dropped** entirely (GAP11).
- Timeline events exist only **post-ingest** — there are no events at **discovery** (GAP1) or **intake** (GAP3), so progression history is incomplete end-to-end.
- **Audit coverage** is post-ingest only (GAP9) — the discovery→ingest phase is never swept.
- The timeline **action enum drifts** from what's actually written (GAP5).
- The **status field is underused** — no intermediate states between `discovered` and `ingested` (GAP6/GAP7), so a skill's pipeline position isn't queryable.
- `validate --intake` is **commented out** in CI — intake packets aren't validated.

RFC3 is the umbrella that closes these so the pipeline is auditable and queryable end-to-end.

---

## 2. Locked Decisions (founder rulings — not open questions)

- **Provenance = SIDECAR LEDGER.** Write `registry/provenance/<skill-id>.json` at ingest — a ledger linking the registry node back to its discovery packet / intake batch / intake issue / crawler origin. **NO change to `skill.schema.json`** (keeps the node clean). Closes GAP10 + GAP11.
- **Stage timeline events.** Add timeline events at the **discovery** and **intake** stages (today only post-ingest exist). Route through `gaia dev timeline` CLI — **NEVER hand-edit timeline arrays.** If the CLI cannot write a given stage event, **file the CLI gap; do not fabricate** (per founder/CLAUDE.md "Timeline events — NEVER fabricate by hand").
- **Additive evidence loop (restated at umbrella level).** The ev-pipeline runs as a continuous additive loop (RFC2); document how `gaia-meta-sweep` triggers it.
- **Audit coverage (GAP9) is DEFERRED but planned.** `gaia-meta-sweep` (monthly dynamic workflow) + `gaia-meta-audit` (the curate-core-like core) SHOULD sweep the discovery→ingest phase too. Blocked by RFC1 + #1148 + this umbrella. Reference the **audit-coverage tracking issue (deferred, blocked)** — number filed separately.
- **Reconcile the timeline action enum (GAP5).** Observed-but-absent values: `note`, `suite_ref_set`, `migrate_trust_magnitude`, `installation_updated`. Add the real ones to the schema enum, or reject them at the CLI. Point at the timeline action enum in the schema.
- **Define the intermediate status ladder (GAP6/GAP7).** Represent the states between `discovered` and `ingested` so a skill's pipeline position is always queryable.
- **Re-enable `validate --intake`** in `.github/workflows/validate.yml` (currently commented at ~L71-73) once the `discovery-packet-v2` schema (RFC1) is in.
- **nova-gaia (`sourceProposal.schema.json`) is OUT OF SCOPE** — a separate pipeline for already-named skills that MAY converge later pending founder review; no convergence design here.

---

## 3. Design detail

### 3.1 Provenance sidecar ledger (GAP10 + GAP11)

At ingest, write `registry/provenance/<skill-id>.json` — a ledger separate from the node (no `skill.schema.json` change). Shape:

```json
{
  "skillId": "contributor/slug",
  "genericSkillRef": "generic-id",
  "discoveryPacket": "registry-for-review/discovery-packets/<candidate>.json",
  "intakeBatch": "registry-for-review/skill-batches/<batch>.json",
  "intakeIssue": "https://github.com/mbtiongson1/gaia-skill-tree/issues/<n>",
  "crawlerOrigin": {
    "sourceLane": "marketplace | source-repository | github-topic",
    "canonicalUrl": "https://…",
    "contentSha256": "…"
  },
  "evidenceSeed": "…path to the RFC2 evidence-seed artifact…",
  "ingestedAt": "2026-07-29T00:00:00Z"
}
```

- Back-links the node to every upstream marker (packet lifecycle → intake batch → intake issue → crawler origin → evidence seed).
- `crawlerOrigin` closes GAP11 (crawler provenance currently dropped) by carrying the `source` provenance the discovery packet already captured (`canonicalUrl`, `sourceLane`, `contentSha256`).
- New sidecar directory `registry/provenance/` — tracked, hand-authored-adjacent but CLI-written at ingest. Written via the ingest/promotion CLI path (the maintainer promotion step in the RFC2 narrative), not by hand.

### 3.2 Stage timeline events (GAP1 + GAP3)

Add timeline events at two new stages, both routed through `gaia dev timeline`:

- **discovery** — logged when a candidate reaches `review-ready` (RFC1 packet lifecycle).
- **intake** — logged when the intake issue opens (RFC2 Gap B adapter → `gaia push`).

Route: `gaia dev timeline <skillId> --user <username> --action <action> --notes "…"` (backfill with `--timestamp` if reconstructing history). **If `gaia dev timeline` cannot write a discovery-stage or intake-stage event** (e.g. no skill node exists yet at discovery time — the skill isn't in the tree until ingest), **file the CLI gap and leave the event out**; do NOT fabricate a frontmatter entry. This is the likely gap: pre-ingest stages have no node/tree target, so the timeline may need a provenance-ledger event log rather than a node-timeline entry — record that finding in the CLI-gap issue rather than papering over it.

### 3.3 Schema action-enum reconciliation (GAP5)

The timeline `action` enum in the schema is missing values actually in use: `note`, `suite_ref_set`, `migrate_trust_magnitude`, `installation_updated` (plus the new discovery/intake stage actions from §3.2). Reconcile by adding the real, sanctioned values to the enum in the schema, OR having the CLI reject unknown actions at write time (per the CLI Pre-Flight Rule — validate the invariant before writing). Point implementers at the timeline `action` enum location in `skill.schema.json` (the timeline event definition). Note the repo underscore-style caveat: these observed enum values already contain underscores (`suite_ref_set` etc.) — they are pre-existing data literals, so keep them verbatim; the no-underscore rule applies only to NEW function/variable names, not to reconciling existing enum data.

### 3.4 Intermediate status ladder (GAP6/GAP7)

Define an explicit ladder so a skill's pipeline position is always queryable. Align it to the discovery-packet lifecycle (RFC1) and the RFC2 narrative:

```
discovered → review-ready → intake-open → evidence-seeded → in-appraisal → ingested
```

- `discovered` → candidate found (crawler).
- `review-ready` → packet passed to L4 (RFC1 packet lifecycle terminal).
- `intake-open` → intake issue opened (RFC2 Gap B).
- `evidence-seeded` → evidence-seed emitted post-L4 (RFC2 Gap C).
- `in-appraisal` → ev-pipeline additive loop running (RFC2 §3.5).
- `ingested` → maintainer CLI promotion complete; skill in tree; provenance sidecar written (§3.1).

Codify the ladder in the schema `status` field enum (or the provenance-ledger `status` if the pre-ingest states have no node yet — resolve per the §3.2 CLI-gap finding). Deferred/rejected branches (`deferred`, `rejected`) come from the packet lifecycle and remain terminal off-ramps.

### 3.5 Re-enable `validate --intake`

In `.github/workflows/validate.yml`, un-comment the block currently at L71-73:

```yaml
      # - name: Run intake validation
      #   run: gaia dev validate --intake
```

Wire it once the `discovery-packet-v2` schema (RFC1) is in so CI validates intake packets under `registry-for-review/discovery-packets/`. Ensure `gaia dev validate --intake` resolves the v2 schema and the seed/adapter artifacts.

### 3.6 Additive loop trigger via gaia-meta-sweep

Document that `gaia-meta-sweep` (monthly dynamic workflow) triggers the RFC2 continuous additive ev-pipeline loop — no green gate, evidence accumulates additively, TM/rank recomputed at appraisal time.

### 3.7 Audit coverage extension (GAP9, DEFERRED)

`gaia-meta-sweep` + `gaia-meta-audit` currently sweep only POST-ingest. The planned extension sweeps the discovery→ingest phase too (packets, intake issues, evidence seeds, provenance sidecars). **DEFERRED** — blocked by RFC1 + #1148 + this umbrella landing. Tracked by the **audit-coverage tracking issue (deferred, blocked)** (filed separately). Do not build here; document the deferral and the block.

---

## 4. Gaps closed (and deferred)

- **GAP10** (no back-link node→batch/issue) — provenance sidecar (§3.1).
- **GAP11** (crawler provenance dropped) — `crawlerOrigin` in the sidecar (§3.1).
- **GAP1** (no discovery timeline event) + **GAP3** (no intake timeline event) — stage timeline events (§3.2).
- **GAP5** (schema enum drift) — action-enum reconciliation (§3.3).
- **GAP6 / GAP7** (no intermediate status states) — status ladder (§3.4).
- **`validate --intake` disabled** — re-enabled (§3.5).
- **GAP9** (audit coverage post-ingest only) — **DEFERRED**, tracked separately (§3.7).

---

## 5. Acceptance criteria

- [ ] Provenance sidecar `registry/provenance/<skill-id>.json` written at ingest, back-linking node → discovery packet / intake batch / intake issue / crawler origin / evidence seed; NO `skill.schema.json` change.
- [ ] Discovery + intake timeline events added via `gaia dev timeline` (never hand-edited); if the CLI cannot write a pre-ingest stage event, the CLI gap is filed (not fabricated).
- [ ] Timeline `action` enum reconciled with observed values (`note`, `suite_ref_set`, `migrate_trust_magnitude`, `installation_updated`) + new stage actions — added to schema or rejected at CLI.
- [ ] Intermediate status ladder defined + codified (`discovered → review-ready → intake-open → evidence-seeded → in-appraisal → ingested`), a skill's pipeline position queryable.
- [ ] `validate --intake` re-enabled in `.github/workflows/validate.yml` (L71-73 un-commented) and resolves the `discovery-packet-v2` schema.
- [ ] `gaia-meta-sweep` documented as the additive-loop trigger.
- [ ] Audit-coverage extension documented as deferred + blocked, pointing at the tracking issue.
- [ ] nova-gaia one-line non-goal present.

---

## 6. Out of scope / non-goals

- **nova-gaia (`sourceProposal.schema.json`)** — a separate pipeline for already-named skills that MAY converge later pending founder review; no convergence design here.
- **Audit coverage of discovery→ingest (GAP9)** — DEFERRED + blocked (RFC1 + #1148 + this umbrella); tracked by a separate issue.
- **RF/SHAP trust appraisal** — the ML-**v3** study (gaia-research #129 / PR #128). Decoupled.
- **The embedding fix, prefill, discovery-packet-v2 schema, thresholds** — RFC1.
- **The provisional-TM carve-out, packet→intake-YAML adapter, evidence-seed emission, additive loop implementation** — RFC2.
- **The dropped GREEN gate** — abandoned (RFC2).

---

## 7. Cross-references

- **RFC1 (gaia-curate v2 named-first)** — #1244; packet lifecycle feeding §3.2/§3.4.
- **RFC2 (evidence-seed + provisional TM)** — the adapter/evidence-seed/additive-loop this umbrella wraps; #1148-dependent.
- #1148 — evidence-lake type-partitioning (dependency).
- `founder/handovers/archive/2026-07-13-evidence-lake-type-partitioning.md` — Target Flow the continuity closes around.
- `.github/workflows/validate.yml` (L71-73) — `validate --intake` re-enable.
- `gaia dev timeline` CLI + `skill.schema.json` timeline `action` enum — §3.2/§3.3.
- Skills: `gaia-meta-sweep`, `gaia-meta-audit` — §3.6/§3.7.
- Audit-coverage tracking issue (deferred, blocked) — filed separately.
- gaia-research #129 / PR #128 — RF/SHAP v3 study (decoupled).
