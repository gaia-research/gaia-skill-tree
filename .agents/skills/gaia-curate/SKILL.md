---
name: gaia-curate
description: >
  Expand the Gaia skill registry with new, well-evidenced AI agent skills and open a PR.
  Use this skill when the user says "update the tree", "add new skills to Gaia",
  "curate the registry", "expand the skill graph", "research what's trending in AI skills",
  "populate the registry", "find skills to add", "run a curation pass", "grow the catalog",
  or types /gaia-curate explicitly. This is the primary single-pass curation workflow —
  it handles research, evidence gathering, batch review, CLI execution, validation,
  docs regeneration, and PR creation in one linear pass. Use gaia-curate-chain for
  higher-stakes multi-agent curation, or gaia-curate-dynamic for large parallel sweeps.
version: 1.8.0
---

# gaia-curate

Expand `registry/gaia.json` with new popular AI agent skills, fully evidenced and validated, then push a PR. One linear pass: research → design → review → execute → validate → PR.

---

## Step 0 — Load known sources before researching

Read `registry/skill-sources.md` first. This file lists every known skill marketplace, GitHub org, and registry the project has already identified — using it prevents redundant research and surfaces the highest-signal repos immediately. When you discover a new source not yet listed, append it (following the format at the bottom of that file) and include the update in the same PR.

Also load `registry/gaia.json` to map every existing skill ID — you need this to avoid proposing duplicates and to identify upgrade candidates (step 2d).

---

## Step 1 — Research candidates

Gather evidence across four channels. Aim for a 50/20/10/20 split of effort:

### 1a. GitHub search (50% — primary signal)

Search for repos that implement the skill. On local runs use `gh`; on cloud/remote runs where `gh` is unavailable, fall back to GitHub MCP tools (`search_repositories`, `get_file_contents`) — never report GitHub as unreachable before trying MCP.

```bash
gh search repos --topic="<skill-topic>" --sort=stars --limit=20
gh search repos "<skill-name> agent" --sort=stars --limit=10
```

Qualifying bar: stars > 50, last commit < 1 year, has README + license. Prefer repos with CI and tests.

**Inspect repos before using them as evidence.** A repo is often a collection of many distinct skills, not a single one. Check the common skill-directory layouts before deciding what the evidence URL should be:

```bash
gh api repos/{owner}/{repo}/contents/skills --jq '.[].name'
gh api repos/{owner}/{repo}/contents/.Codex/skills --jq '.[].name'
gh api repos/{owner}/{repo}/contents/codex/skills --jq '.[].name'
gh api repos/{owner}/{repo}/contents/.codex/skills --jq '.[].name'
gh api repos/{owner}/{repo}/contents/cursor/skills --jq '.[].name'
```

If a skills directory exists, each subdirectory is a distinct candidate. For each:
1. Confirm it contains a `SKILL.md` (or `skill.md`).
2. Fetch and read that file for its description.
3. Use the **raw file URL** (`https://github.com/{owner}/{repo}/blob/main/<skills-dir>/<skill-name>/SKILL.md`) as the evidence source — not the repo root URL, which is too coarse to be meaningful.
4. Evaluate each skill independently (accept / rename / drop on its own merits).

If no skills directory exists, the repo root URL is an acceptable evidence source.

### 1b. Paper search (20% — highest trust signal)

For any Level II+ candidate or a skill with only community evidence:

```
WebSearch: "<skill-name> arxiv 2024 2025 2026 agent benchmark"
WebSearch: "<skill-name> survey" site:arxiv.org
```

Use the arXiv `abs/` URL as the evidence source. Only include papers that directly measure or demonstrate this skill, not tangentially related surveys.

### 1c. SkillsMP community search (10% — supplementary)

```
WebFetch: https://skillsmp.com/api/v1/skills/search?q=<skill-name>
```

Treat matching entries as supplementary evidence. Rate limit: 50 requests/day unauthenticated.

### 1d. Existing tree audit (20% — strengthen before widening)

Before proposing net-new skills, scan the loaded `registry/gaia.json` for:
- Skills at level 0/I with only community evidence (upgrade these first)
- Skills with `status: "provisional"` that could be validated with better evidence
- Skills at level II+ missing peer-reviewed evidence

Upgrading weak existing skills delivers more value than pure breadth expansion.

---

## Step 2 — Design the batch

### Registry terminology and generic-ref gate

- An **upstream skill** is a `SKILL.md` found in another repository (for example, Anthropic's `mcp-builder`). It is evidence, not automatically a Gaia entry.
- A **starless (generic) skill** is a reusable, vendor-neutral capability. Its Gaia ID must be generic enough to cover multiple implementations and must not be copied from an upstream slash skill name merely because that name is convenient.
- A **named skill** is a specific implementation attributed to a contributor or repository. It is represented by a slash-style skill setup such as `/mcp-builder`, while its `--generic-ref` must point to an existing starless (generic) Gaia ID such as `mcp-server-development`.
- Before proposing a named skill, verify that its generic ref already exists and is the correct generic skill type. Use `gaia dev list --generic --description` (or `gaia dev list --generic --json`) as the source of truth. If it does not exist, decide whether to create the starless (generic) parent; do not use the implementation's name as a substitute generic ref.
- Never use an upstream repository name, slash skill name, or `SKILL.md` filename as a generic ref unless it independently satisfies the vendor-neutral generic taxonomy.

#### Generic-parent decision tree

1. **Exact generic exists** — reuse its ID; do not create a duplicate.
2. **Equivalent generic exists under a broader name** — reuse it when the implementation is a valid specialization; propose a named entry mapped to that parent.
3. **Only a vendor-specific or implementation-specific node exists** — do not reuse it as a generic parent; propose a vendor-neutral starless parent first.
4. **No suitable generic exists** — create a starless parent only when the capability is reusable across multiple implementations, has a precise falsifiable definition, and is not merely a product, repository, or slash skill name.
5. **Capability is too narrow or has only one inseparable implementation** — do not create a generic; hold or reject the named proposal pending evidence of broader applicability.

The normal curation path is therefore: list generics programmatically → map each upstream implementation to an existing parent where possible → create a new starless parent only when the decision tree requires it → propose the named implementation with that parent's `generic-ref`.

For each candidate, decide:

**Taxonomy tier** (what type of skill is it?):
- `basic` — primitive capability, no prerequisites
- `extra` — emerges from ≥2 prerequisite basics
- `ultimate` — high-complexity emergent, ≥3 prerequisites, and multiple independent evidence artifacts
- `unique` — graph-isolated basic that reached 4★+ through depth alone

**Fusion-first design** — Resist the temptation to create one generic skill per vendor API. Multiple named implementations of the same concept (e.g. `pubmed`, `arxiv`, `biorxiv`) should map to a single elegant generic (e.g. `literature-search`). This keeps the global graph readable and prevents registry bloat.

**Composite extras** — When multiple distinct skills combine into a multi-step workflow, design a composite Extra that names them as prerequisites. Calibrate the named implementations at 3★–4★ max, referencing the composite.

**Generic skill levels** — Starless (generic) skills have no star level. Only named implementations receive stars (2★–6★). Omit `--level` from `gaia dev add` for starless (generic) skills.

**Named promotion** — If a specific implementation warrants its own entry in `registry/named/`, mark it for named promotion and show its slash skill setup (for example, `/mcp-builder`) separately from its generic ref. Submit with `status: awakened`. Never hand-set `title` or `catalogRef` during curation — those are set by a reviewer at Named promotion time.

**Demerit checks** — Only apply `heavyweight-dependency`, `niche-integration`, or `experimental-feature` demerits to skills at 3★+. Cross-platform universal skills at high levels should omit demerits.

**Rarity** — Do not choose or mention a rarity value. The rarity axis is deprecated; `gaia dev add` writes the legacy default automatically.

---

## Step 3 — Present draft for review

Before writing anything to disk, show the full proposed batch:

| Name | Starless (generic) | Named (`/slash-skill`) | Type | Stars | Prereqs | Generic ref | Action |
|---|---|---|---|---:|---|---|---|
| Example Capability | Example Capability | — | starless (generic) | — | — | — | accept |
| Example Implementation | Example Capability | `/example-implementation` | named | 2★–6★ | — | `example-capability` | accept |
| … | … | … | … | … | … | … |

For each row, ask the user to mark one of:
- `accept` — proceed as designed
- For every `named` row, confirm that the listed generic ref already exists and is the correct generic skill type.
- For every `starless (generic)` row, confirm that the name is vendor-neutral and broad enough to support multiple named implementations.
- `rename <new-id>` — change the ID before generating
- `duplicate` — already covered; drop it
- `needs-evidence` — hold until a valid, resolvable evidence artifact is supplied
- `reject` — remove entirely

Do not proceed to Step 4 until the user has reviewed and at least one skill is marked `accept`. Apply all `rename` decisions before writing. Drop everything not `accept`/`rename`.

---

## Step 4 — Execute via CLI

Run `gaia dev add` for each accepted skill. Mutating registry files directly is prohibited — the CLI handles timeline logging, schema integrity, and automated assembly.

**Generic (starless) skill:**
```bash
gaia dev add "Skill Name" --id <id> --type <type> --description "At least 10 chars"
```
Do NOT pass `--level` for generics.

**Named implementation:**
```bash
gaia dev add "Skill Name" --id <id> --named --contributor <user> --generic-ref <ref> --status awakened
```
Submit as `awakened`. Calibrate stars with `gaia dev calibrate` after evidence is reviewed.

---

## Step 5 — Validate, regenerate, and commit

```bash
gaia validate          # must exit 0 before proceeding
gaia dev docs          # regenerates registry.md, combinations.md, skills/**/*.md, gaia.gexf
```

Branch name: `review/meta/<slug>`  
Commit message format: `[type] Title — brief description`

---

## Step 6 — Open the PR

Push the branch and open a PR via the GitHub API. The auto-triage CI classifies it using computed evidence artifact scores and provenance; do not manually assign a class, trust grade, or aggregate trust value.
- `draft-skills` or `needs-review` labels → routed to a human reviewer
- Ultimate skill proposals → always require maintainer approval

---

## Step 7 — Record contributor and batch evidence

Add the contributor's GitHub username to the `## Contributors` section of `README.md` (create the section if it doesn't exist, before the License section):

```markdown
| @username | Brief description of contribution |
```

Also register the curation batch itself as a `registryCuration` evidence entry if new demonstrations were produced during research.

---

## Two-phase intake (gaia push path)

For contributors using `gaia push`, a separate draft intake path exists that does NOT directly modify `registry/gaia.json`:

1. `gaia push` scans the source repo and writes `registry-for-review/skill-batches/<batchId>.json`
2. Maintainers review and mark each skill: `accept` / `rename` / `duplicate` / `needs-evidence` / `reject`
3. Accepted skills are promoted in a follow-up PR that runs `gaia validate` and `gaia validate --intake`

Run `/gaia-draft-curate` to triage pending intake batches before this skill.

Validate intake batches locally:
```bash
gaia validate --intake
```

---

## Hard constraints

- Never hand-edit `registry/nodes/` or `registry/gaia.json`. Use `gaia dev add`, `gaia dev merge`, `gaia dev split`, `gaia dev evidence`.
- All evidence source URLs must be real and resolvable. Record the evidence type, source URL, provenance, and concise notes; artifact scores and per-row grades are computed by the registry tooling. Never hand-author deprecated `class` values or aggregate trust fields.
- Ultimate skills must land as `provisional` — the maintainer sets `validated` after review.
- No cycles in the DAG. No orphaned composite nodes.
- Skill IDs: `lowercase-dash` format (`^[a-z][a-z0-9]*(-[a-z0-9]+)*$`). No camelCase, no vendor names, no unexplained abbreviations.
- Edges use `sourceSkillId`/`targetSkillId` (not `from`/`to`). Valid `edgeType` values: `prerequisite`, `corequisite`, `enhances`. There is no `derivative` edge type — use `enhances` for skill→derivative edges.
- All Python `open()` calls must use `encoding='utf-8'` to avoid CP-1252 drift on Windows.

---

## Evidence recording reference

| Artifact type | Typical source | Curation treatment |
|---|---|---|
| `arxiv` | `https://arxiv.org/abs/<id>` | Record as a directly relevant paper artifact |
| `repo` | GitHub repository or specific `blob/` skill file | Record as a reproducible implementation artifact |
| `registryCuration` | Curation batch or documented demonstration | Record only when the curation work produced new evidence |
| community/vendor artifact | SkillsMP or vendor documentation | Supplementary evidence only |

The registry computes artifact scores, freshness, provenance weighting, per-row grades, and overall trust grades. Curation proposes evidence artifacts and their raw source measurements; it does not assign `class`, `trustNumber`, `trustMagnitude`, `artifact_score`, or manual A/B/C grades.

### Repository-owned source measurements

For a named implementation backed by its own upstream repository, record the raw measurements that the scoring formulas consume:

- `repo-own`: `commits` and `contributors`
- `github-stars-own`: `stars` and, when applicable, `skillCountInRepo`

Use the specific implementation `blob/` URL as the source where available. These are source facts, not trust grades. Capture them with `gaia dev evidence`:

```bash
gaia dev evidence <skill-id> <source-url> \\
  --type repo-own --commits <n> --contributors <n> \\
  --notes "source measurements captured <date>"

gaia dev evidence <skill-id> <repo-url> \\
  --type github-stars-own --stars <n> --skill-count-in-repo <n> \\
  --notes "GitHub source measurements captured <date>"
```

Do not pass `--trust`; the CLI computes derived values. If the implementation is submitted through intake, preserve these raw measurements in its evidence entries or named evidence payload so maintainers can reproduce the calculation.

---

## Output

At the end, report:
- PR URL
- Skills added (count by type)
- Validation result
- Any existing skills whose `derivatives` arrays were patched
- Review decisions applied (accepted / renamed / dropped)
- Contributor recorded in README
