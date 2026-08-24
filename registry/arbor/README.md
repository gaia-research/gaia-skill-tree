# Arbor declaration-first sidecar

Arbor is Gaia Skill Tree's behavioral Tree. This sidecar implements the smallest
useful evidence loop from `founder/RATIFICATION.md` A1/A2: an expert declaration,
an optional focused benchmark receipt, and a generated interpretation. It does
not pre-label skills or create a bulk coverage campaign.

Canonical skill identity remains outside Arbor and is never rewritten. Every
Arbor source points to the exact canonical `skill.id` and the SHA-256 of its
source file's unmodified bytes. Resolution is deterministic: generic IDs resolve
to exactly one of `registry/nodes/{basic,fusion}/<id>.json`; named
`<contributor>/<slug>` IDs resolve to
`registry/named/<contributor>/<slug>.md`. Import, standalone/full check, and
replay reject a missing/ambiguous ID or a hash that differs from those exact
bytes. Import never edits canonical nodes, named skills, or a Skill Tree.

## The three contracts

Contracts are JSON Schema files under `contracts/` and reject unknown fields.

1. **`gaia.arbor-expert-declaration/v1`** — one or more operational claims. Each
   claim has its own `facet`, `conditions`, `rationale`, `authority`, and a
   measurable expectation. `human-led` and `model-led` are independent facets;
   both may describe the same skill when their stated conditions differ.
2. **`gaia.arbor-benchmark-receipt/v1`** — one focused observation targeting a
   declaration claim. It defines control and treatment arms, provenance, sample
   measurements, and confidence intervals. Each arm has a closed environment
   (`model`, `harness`, `taskSetSha256`, and `seedSha256`), and the two
   environments must be identical so only the arm definitions/capability
   exposure differ. The estimate must equal treatment mean minus control mean
   and lie inside its interval. A receipt contains no verdict, result,
   interpretation, assessment, conclusion, or support label.
3. **`gaia.arbor-profile/v1`** — a generated interpretation referencing exact
   declaration and receipt digests. Claim support is exactly one of
   `expert-declared`, `benchmark-confirmed`, `benchmark-qualified`,
   `benchmark-revised`, or `inconclusive`.

Stars, rank labels, Trust Magnitude, grades, trust/prestige fields, and source
interpretation variants are rejected recursively. They belong to Yggdrasil or
to generated Arbor interpretation, not authored Arbor sources.

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
bytes have a different digest, and a digest/file mismatch fails `check`. Before
publishing a declaration, import builds and validates the complete affected
profile, including claim-ID uniqueness across declarations. Before publishing a
receipt, it validates the target and affected interpretation. A receipt must
reference an already-imported declaration digest, one of its claim IDs, and the
same verified canonical skill identity/hash. Failed preflight publishes no
source, so an immutable poison record cannot be introduced.

`replay` reads only immutable sources and atomically materializes:

```text
registry/arbor/profiles/<skill-id path>/<skill-content-sha256>.json
```

No timestamp is embedded, so replay is deterministic. `check` recomputes every
profile in memory and fails if a source is altered, a reference is broken, or a
generated profile is stale. Import, replay, and check share one store-wide lock,
so an import cannot race a replay into a stale overwrite. Replay stages and
validates the complete generation in memory before publication, then uses atomic
per-file replacement and removes stale profiles. This is not a transactional
multi-file manifest switch: a process crash during publication can leave a mix
of individually complete old/new profile files, and a hard crash can leave
`.store-lock` behind for an operator to inspect and remove. A subsequent replay
reconciles the set; validation failures occur before any profile write.

## Interpretation rule

The authored declaration source is always unchanged. In the generated support
interpretation, a claim with no targeted receipt remains `expert-declared`; a
targeted receipt that does not decisively resolve the expected metric yields
`inconclusive` (the issue #196 semantics). For the claim's expected metric, the
interpreter compares the measured treatment-minus-control confidence interval
with the declared direction and minimum effect:

- interval clears the threshold: `benchmark-confirmed`;
- point estimate clears it but the interval does not: `benchmark-qualified`;
- interval lies wholly in the opposite direction: `benchmark-revised`;
- otherwise, or when the targeted metric is absent: `inconclusive`.

Conflicting positive and revised receipts are also `inconclusive`. The receipt
remains conclusion-free; only replay derives support, claim by claim. Additional
receipts can therefore confirm, qualify, revise, or leave a declaration
unresolved without any automatic intake campaign.
