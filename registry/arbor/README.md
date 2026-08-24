# Arbor declaration-first sidecar

Arbor is Gaia Skill Tree's behavioral Tree. This sidecar implements the smallest
useful evidence loop from `founder/RATIFICATION.md` A1/A2: an expert declaration,
an optional focused benchmark receipt, and a generated interpretation. It does
not pre-label skills or create a bulk coverage campaign.

Canonical skill identity remains outside Arbor. Every Arbor source points to the
exact canonical `skill.id` and the SHA-256 of the skill content it describes.
Import never edits `registry/nodes/`, `registry/named/`, or a Skill Tree.

## The three contracts

Contracts are JSON Schema files under `contracts/` and reject unknown fields.

1. **`gaia.arbor-expert-declaration/v1`** — one or more operational claims. Each
   claim has its own `facet`, `conditions`, `rationale`, `authority`, and a
   measurable expectation. `human-led` and `model-led` are independent facets;
   both may describe the same skill when their stated conditions differ.
2. **`gaia.arbor-benchmark-receipt/v1`** — one focused observation targeting a
   declaration claim. It defines control and treatment arms, provenance, sample
   measurements, and confidence intervals. It contains no verdict, conclusion,
   or support label.
3. **`gaia.arbor-profile/v1`** — a generated interpretation referencing exact
   declaration and receipt digests. Claim support is exactly one of
   `expert-declared`, `benchmark-confirmed`, `benchmark-qualified`,
   `benchmark-revised`, or `inconclusive`.

Stars, rank labels, Trust Magnitude, and prestige fields are rejected recursively.
They belong to Yggdrasil, not Arbor.

## Programmatic workflow

Use the dynamic developer command. Mutating operations use the existing Verifier
authorization guard; `check` is read-only.

```bash
gaia dev arbor check declaration.json
gaia dev arbor import declaration.json
gaia dev arbor import focused-receipt.json
gaia dev arbor replay
gaia dev arbor check
```

`import` validates and canonicalizes JSON, computes its SHA-256, then atomically
publishes it under:

```text
registry/arbor/sources/declarations/<sha256>.json
registry/arbor/sources/receipts/<sha256>.json
```

Source files are immutable. Re-importing identical bytes is idempotent; altered
bytes have a different digest, and a digest/file mismatch fails `check`. A
receipt must reference an already-imported declaration digest, one of its claim
IDs, and the same exact skill identity/hash.

`replay` reads only immutable sources and atomically materializes:

```text
registry/arbor/profiles/<skill-id path>/<skill-content-sha256>.json
```

No timestamp is embedded, so replay is deterministic. `check` recomputes every
profile in memory and fails if a source is altered, a reference is broken, or a
generated profile is stale.

## Interpretation rule

A declaration stays `expert-declared` until a receipt targets it. For the claim's
expected metric, the interpreter compares the measured treatment-minus-control
confidence interval with the declared direction and minimum effect:

- interval clears the threshold: `benchmark-confirmed`;
- point estimate clears it but the interval does not: `benchmark-qualified`;
- interval lies wholly in the opposite direction: `benchmark-revised`;
- otherwise, or when the targeted metric is absent: `inconclusive`.

Conflicting positive and revised receipts are also `inconclusive`. The receipt
remains conclusion-free; only replay derives support, claim by claim. Additional
receipts can therefore confirm, qualify, revise, or leave a declaration
unresolved without any automatic intake campaign.
