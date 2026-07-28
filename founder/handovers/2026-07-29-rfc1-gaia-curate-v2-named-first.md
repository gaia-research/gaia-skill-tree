# RFC1 — gaia-curate v2: named-first intake with embedding-driven prefill

One-line summary: Invert `/gaia-curate` from generic-node-first to **named-first** as a pure presentation REORDER (never a decouple), fix the zero-named-embeddings root cause, and move mapping reasoning out of the LLM into a deterministic, unit-tested prefill module so a Haiku/Luna worker runs curation with minimal reasoning.

Status: BUILD-READY
Date: 2026-07-29
Branch: `dev/gaia-curate-v2-pipeline`
Milestone: Program 5 — Gaia Skill Tree Core (#16)
Covers: #1244 ([RFC] gaia-curate: named-first intake path)

---

## 1. Problem / Motivation

Today `/gaia-curate` (contract: `.claude/skills/gaia-curate/CURATION-CORE.md`) presents only **generic (starless) nodes** for curation. It queries `gaia dev list --generic --json`, dedupes, and asks a worker to emit exactly one bounded decision (`MAP`/`NEW_GENERIC`/`DUPLICATE`/`NOT_A_SKILL`/`DEFER`) mapping the candidate onto an existing generic or proposing a new one.

But the real intake shape for a mature registry is the inverse: a **trending NAMED skill** arrives (a contributor's concrete implementation, e.g. `mattpocock/grill-me`), and the curator's job is to map that named skill onto the correct **generic** node — creating the generic if none exists. The generic-node-first framing forces the worker to reason "which of these starless nodes might this be," when the natural, lower-reasoning question is "here is a named skill; here is its closest generic (pre-computed); confirm or correct."

Two compounding defects make the current flow unable to support named-first:

1. **Zero named coverage in embeddings (ROOT CAUSE).** `src/gaia_cli/embeddings.py::load_skills()` reads named skills from `registry/named/*.json`, but named skills are authored as **`.md` frontmatter**, not `.json`. Result: `graph/embeddings.json` has **211 entries, all generic, ZERO named** (verified 2026-07-29). Similarity-based mapping and suite-component appointing are therefore impossible today — there is nothing named to match against.
2. **No defined output path (Gap A).** `/gaia-curate` produces review-ready packets but the contract never says WHERE they land, so nothing downstream can consume them.

RFC1 fixes both, adds embedding-similarity prefill, and reorders the presentation to named-first — without ever decoupling the required generic mapping.

---

## 2. Locked Decisions (founder rulings — not open questions)

- **REORDER, not decouple (option A).** Named-first changes only the order in which the worker considers things. The generic mapping edge is never removed.
- **`genericSkillRef` is REQUIRED for ALL skills, always.** 1 named skill = exactly 1 `genericSkillRef`. Named-first never makes the generic mapping optional.
- **Three structural axes stay ORTHOGONAL:**
  - **Axis A — generic MAPPING**: the edge named→generic (`genericSkillRef` → generic id). Always required.
  - **Axis B — generic TYPE `basic|fusion`**: PURELY the prerequisite count on the **generic node** (`basic` = 0 prereqs, `fusion` ≥ 1). Curation must DISCOVER implied fusions (e.g. `ui-design` + `ux-design` nodes imply a `uiux-design` fusion node). `genericSkillRef`s usually already encode this structure, but undiscovered implied fusions ("missing links") MUST be surfaced. `type` lives on the generic node — never on the named skill.
  - **Axis C — suite membership**: `suiteComponents`, **NAMED-SKILL-ONLY** (issue #996). NEVER on a generic node. Suite is the DEFAULT framing (no resolvers; branch derived read-time per `taxonomy.py`), so curation simply ASKS whether to add `suiteComponents`; if none, none. Each component STILL has its own `genericSkillRef`. NESTED suites exist. Suite fan-out = 1 discovery packet per component + 1 capstone packet, linked by a shared `suiteId`; the capstone is declared (the repo/library name).
- **ML layer = EMBEDDING SIMILARITY** (`all-MiniLM-L6-v2`, cosine), NOT random forest. RF/SHAP is a separate decoupled study (gaia-research #129 / PR #128) referenced as the **v3** future — out of scope here.
- **Root-cause fix**: `embeddings.py::load_skills()` must read named `.md` frontmatter so named skills get embedded.
- **Prefill is deterministic Python**, front-loaded, fully unit-tested, tunable via a Haiku/dynamic-workflow loop, and exposed as a **CLI verb** (repo standards + docs). It pre-computes mapping candidates + cosine similarity + `matchTier` BEFORE the worker sees the packet.
- **Worker job shrinks to**: confirm STRONG matches; decide MAP-vs-`NEW_GENERIC` only on WEAK matches; carry the WHY (signal + source) into the L4 report. The worker still emits **exactly one decision** and generic mapping is still required.
- **L4 ratifies ALL new topology** (new generics, new fusions, new suites) and MUST see WHY each MAP-vs-`NEW_GENERIC` choice was made (cosine + `matchTier` + which generic/named it matched).
- **STRONG_MAP / WEAK_MAP thresholds** live in `registry/schema/meta.json` (tracked, hand-authored — NOT Class P, NOT Class S) and MUST be mirrored to `src/gaia_cli/data/registry/schema/meta.json` (lockstep enforced by `scripts/validate.py` "Meta sync check"). Tunable via the Haiku loop.
- **`discovery-packet-v2`** is a new contract version; **v1 packets still validate under the v1 schema** (do not break existing).
- **`/gaia-curate` output path** = `registry-for-review/discovery-packets/` (alongside the existing `registry-for-review/skill-batches/` intake), which becomes the input to the packet→intake-YAML adapter defined in **RFC2 (evidence-seed + provisional TM)**.

---

## 3. Design detail

### 3.1 The 80 / 15 / 5 split (infra / agent / human)

Move reasoning OUT of the LLM into deterministic infra. Target division of labor per candidate:

| Share | Owner | What it does |
|---|---|---|
| **80% — infra (deterministic Python)** | prefill module + `embeddings.py` fix + validator | Load candidate → embed `{name}: {description}` → cosine against ALL embeddings (now including named) → rank top-K generics → derive `matchTier` (strong/weak) from `meta.json` thresholds → detect exact dedupe → assemble a pre-filled `discovery-packet-v2` with `mappingOptions[].similarity` + `mappingOptions[].matchTier` populated → self-validate against the schema BEFORE the worker sees it. Suite fan-out (component packets + capstone packet sharing a `suiteId`) is emitted structurally. Implied-fusion "missing links" are surfaced as flags. |
| **15% — agent (Haiku / Luna, minimal reasoning)** | worker | Confirm STRONG matches (rubber-stamp the pre-filled `MAP`). Decide MAP-vs-`NEW_GENERIC` **only on WEAK matches**. Answer the single suite question (add `suiteComponents` or not). Carry the WHY (cosine + matchTier + matched id) into the packet so it survives to L4. Emit exactly one bounded decision. |
| **5% — human (L4)** | maintainer | Ratify ALL new topology (new generics, fusions, suites). Read the WHY column. Shortlist acceptance is not registry acceptance. Stop at the L4 artifact. |

Rule of thumb: if a step is a lookup, a threshold comparison, a hash, or a ranked list — it is infra. The agent only decides the genuinely ambiguous WEAK cases and the one suite question.

### 3.2 Root-cause fix — embed named `.md` frontmatter

`src/gaia_cli/embeddings.py::load_skills()` currently only reads `registry/named/*.json` (there are none). Fix: parse the YAML frontmatter of `registry/named/**/*.md` so each named skill contributes `id` (contributor/slug), `name`, and `description` to the embedded set. Reuse the same frontmatter-reading path the CLI already uses for named skills (`treeManager` / `localContext` read `genericSkillRef` frontmatter — see `src/gaia_cli/CLAUDE.md`). No new function underscores (repo style); name new helpers e.g. `loadNamedFrontmatter`.

Acceptance signal: after regenerating, `graph/embeddings.json` contains entries whose `id` includes `"/"` (contributor-scoped named skills), not just the 211 bare generic ids.

> `graph/embeddings.json` is **tracked** in git (an intake/analysis artifact), NOT Class P and NOT Class S. Regenerate and commit it in the same PR as the loader fix.

### 3.3 Prefill module + CLI verb

A new deterministic module (propose `src/gaia_cli/prefill.py`) reusing `src/gaia_cli/semantic_search.py` (`load_embeddings`, `cosine_similarity`, `embed_query`, `search_precomputed`). Responsibilities:

- Embed the candidate's `{name}: {description}` (or reuse a precomputed vector).
- Rank the top-K **generic** entries by cosine similarity (`search_precomputed` already returns `{id, score}` sorted desc).
- Derive `matchTier` per option from `meta.json` thresholds (§3.5): `strong` if `similarity >= STRONG_MAP`, else `weak` (a `similarity < WEAK_MAP` option is dropped, not emitted).
- Populate at most three `mappingOptions[]`, each with `genericId`, `rationale`, `similarity`, `matchTier`.
- For suite fan-out: also rank named candidates to help appoint suite components (now possible because named skills are embedded).
- Surface implied-fusion "missing links" as `flags` when two closely-related generics have no fusion node covering their union.
- Emit a schema-valid `discovery-packet-v2` and self-validate it before handing to the worker.

Exposed as a CLI verb (naming to fit the existing `gaia dev` surface, no underscores in new public names — propose `gaia dev prefill`). Fully unit-tested; thresholds tunable via the Haiku/dynamic-workflow loop.

### 3.4 `discovery-packet-v2` schema deltas

New schema file: `.claude/skills/gaia-curate/schemas/discovery-packet-v2.schema.json` (v1 file stays for back-compat). Deltas from v1:

**(a) `decision.proposal.prerequisites`** — array of generic ids; REQUIRED when `proposal.type == "fusion"` (≥ 1). This is how implied-fusion discovery is recorded (Axis B).

```json
"proposal": {
  "type": "object",
  "required": ["name", "description", "type"],
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "description": {"type": "string", "minLength": 1},
    "type": {"enum": ["basic", "fusion"]},
    "prerequisites": {
      "type": "array",
      "items": {"type": "string", "minLength": 1}
    }
  },
  "allOf": [
    {
      "if": {"properties": {"type": {"const": "fusion"}}},
      "then": {
        "required": ["prerequisites"],
        "properties": {"prerequisites": {"minItems": 1}}
      }
    }
  ]
}
```

**(b) top-level `suite` object** — present ONLY when the packet is part of a suite fan-out:

```json
"suite": {
  "type": "object",
  "required": ["role", "suiteId"],
  "properties": {
    "role": {"enum": ["component", "capstone"]},
    "suiteId": {"type": "string", "minLength": 1},
    "componentCandidateIds": {
      "type": "array",
      "items": {"type": "string", "minLength": 1}
    }
  }
}
```

`suiteComponents` is a NAMED-SKILL-ONLY concept (Axis C); the packet's `suite` block carries the fan-out linkage, not a `suiteComponents` array on a generic. Nested suites are expressed by a component packet that itself carries `role: "capstone"` for a lower `suiteId`.

**(c) `mappingOptions[]` enrichment** — add `similarity` (cosine 0..1, from prefill) and `matchTier` (enum `strong|weak`, derived from `meta.json`):

```json
"mappingOptions": {
  "type": "array",
  "maxItems": 3,
  "items": {
    "type": "object",
    "required": ["genericId", "rationale", "similarity", "matchTier"],
    "properties": {
      "genericId": {"type": "string", "minLength": 1},
      "rationale": {"type": "string", "minLength": 1},
      "similarity": {"type": "number", "minimum": 0, "maximum": 1},
      "matchTier": {"enum": ["strong", "weak"]}
    }
  }
}
```

**(d) `contractVersion`** bumps to `"discovery-packet-v2"` (`{"const": "discovery-packet-v2"}`). Everything else in v1 (lifecycle enum, source provenance, `genericSnapshot`, exact-dedupe proof, bounded decision enum, stable validator codes) is inherited unchanged. `scripts/validate_discovery_packet.py` gains a v2 code path selected on `contractVersion`; v1 packets continue to validate under the v1 schema.

### 3.5 Thresholds in `meta.json` (+ lockstep mirror)

Add a `curationPrefill` block to **`registry/schema/meta.json`** and mirror it byte-for-byte to **`src/gaia_cli/data/registry/schema/meta.json`** (the two must move in lockstep; `scripts/validate.py` "Meta sync check" fails on divergence):

```json
"curationPrefill": {
  "description": "Embedding-similarity thresholds for gaia-curate v2 prefill. Tunable via the Haiku dynamic-workflow loop. Cosine (all-MiniLM-L6-v2).",
  "strongMap": 0.72,
  "weakMap": 0.45,
  "topK": 3
}
```

(Threshold values are the seed defaults; the Haiku loop tunes them against the Luna oracle fixtures. `strongMap` = auto-confirmable MAP; between `weakMap` and `strongMap` = `weak` option the worker must adjudicate; below `weakMap` = dropped.) `meta.json` is tracked, hand-authored — NOT Class P, NOT Class S.

### 3.6 Gap A — `/gaia-curate` output path

Define it: `/gaia-curate` writes each review-ready `discovery-packet-v2` JSON to `registry-for-review/discovery-packets/` (alongside `registry-for-review/skill-batches/`). This directory is the input to the packet→intake-YAML adapter (RFC2 Gap B). Document the path in `CURATION-CORE.md` (§ Human checkpoint) and in the schema README.

### 3.7 `CURATION-CORE.md` update — named-first ordering

Update the contract to describe named-first ordering while preserving the invariants:

- The worker still emits **exactly one decision** from the unchanged enum.
- Generic mapping (`genericSkillRef` → generic id) is **still required** for every review-ready packet (`MAP` selects a supplied id; `NEW_GENERIC` proposes one — deterministic downstream intake assigns/validates the canonical id).
- Bounded mapping now consumes the prefill's pre-ranked `mappingOptions` (still ≤ 3) instead of the worker constructing them; the worker confirms STRONG, adjudicates WEAK.
- Add the L4 presentation requirement (§3.8) and the output path (§3.6).
- **RFC1 does NOT touch evidence/TM/grades** — that carve-out belongs to RFC2. Leave the "do not collect evidence, score evidence, assign grades/classes, calculate Trust Magnitude" boundary intact here.

### 3.8 L4 presentation requirement

At L4 the packet MUST show WHY the worker chose MAP vs `NEW_GENERIC` — the **signal** (cosine `similarity` + `matchTier`) AND the **source** (which generic/named id it matched). This is the human ratification surface for all new topology. The `mappingOptions[].similarity/matchTier` fields plus the matched id carry this through from prefill → worker → L4 report.

---

## 4. Gaps closed

- **Zero named embeddings (ROOT CAUSE)** — `load_skills()` now reads named `.md` frontmatter; similarity usable for generic-mapping prefill AND suite-component appointing.
- **Gap A (no /gaia-curate output path)** — defined as `registry-for-review/discovery-packets/`, feeding RFC2's adapter.

---

## 5. Acceptance criteria

- [ ] `embeddings.py::load_skills()` reads named `.md` frontmatter; regenerated `graph/embeddings.json` contains named entries (ids containing `"/"`), committed in the same PR.
- [ ] Prefill module (`src/gaia_cli/prefill.py`) implemented, reusing `semantic_search.py`; exposed as a CLI verb (`gaia dev prefill`); fully unit-tested (strong/weak/dropped tiers, suite fan-out, implied-fusion flags, exact dedupe).
- [ ] `discovery-packet-v2.schema.json` validates the three new fields with the conditional (`prerequisites` required iff `type == "fusion"`); `suite` block optional and only when part of a fan-out; `mappingOptions[]` carry `similarity` + `matchTier`.
- [ ] v1 packets still validate under the v1 schema (no break); `validate_discovery_packet.py` selects the code path on `contractVersion`.
- [ ] `curationPrefill` thresholds present in `registry/schema/meta.json` AND mirrored to `src/gaia_cli/data/registry/schema/meta.json`; `scripts/validate.py` "Meta sync check" passes.
- [ ] `/gaia-curate` output path defined + documented (`registry-for-review/discovery-packets/`).
- [ ] `CURATION-CORE.md` updated for named-first ordering: worker emits exactly one decision; generic mapping still required; evidence/TM boundary left intact (RFC2 owns the carve-out).
- [ ] L4 report surfaces cosine `similarity` + `matchTier` + matched id for every MAP-vs-`NEW_GENERIC` choice.

---

## 6. Out of scope / non-goals

- **RF/SHAP trust appraisal** — the ML-**v3** study lives in gaia-research (`docs/idea-bank/rf-shap-trust-appraisal.md`, PR #128 / issue #129, labels RFC+research). Decoupled; v2 uses embeddings, not random forest.
- **Evidence, Trust Magnitude, grades, stars** — RFC1 does not touch them. The provisional-TM carve-out is RFC2's.
- **The evidence bridge, intake-YAML adapter, ev-pipeline** — RFC2.
- **Provenance sidecar, stage timeline events, status ladder, audit coverage** — RFC3.
- **nova-gaia (`sourceProposal.schema.json`)** — separate pipeline, out of scope.

---

## 7. Cross-references

- Issue #1244 (this RFC).
- **RFC2 (evidence-seed + provisional TM)** — consumes the `registry-for-review/discovery-packets/` output; #1148-dependent.
- **RFC3 (pipeline continuity umbrella)** — depends on RFC1 + RFC2 landing.
- #1148 — evidence-lake type-partitioning (RFC2 dependency).
- `founder/handovers/archive/2026-07-13-evidence-lake-type-partitioning.md` — Target Flow the RFCs implement.
- gaia-research #129 / PR #128 — RF/SHAP v3 study (decoupled).
- Contracts touched: `.claude/skills/gaia-curate/CURATION-CORE.md`, `.claude/skills/gaia-curate/schemas/discovery-packet.schema.json` (+ new `-v2`), `src/gaia_cli/embeddings.py`, `src/gaia_cli/semantic_search.py`, `src/gaia_cli/taxonomy.py`, `registry/schema/meta.json` (+ mirror `src/gaia_cli/data/registry/schema/meta.json`), `graph/embeddings.json`.
