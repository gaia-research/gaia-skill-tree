---
name: gaia-triage
description: >
  Triage the Gaia issue backlog and skill-batch intake queue. Use this skill when someone
  asks to: "triage issues", "clean up the issue tracker", "review the backlog", "close
  stale issues", "process the intake queue", "review skill-batches", "evaluate draft skill
  proposals", "approve or reject pending skills", "is this issue still valid?", "what's
  clogging the backlog?", "run a triage pass", or /gaia-triage. Covers two workstreams:
  (1) GitHub issue lifecycle — identifying resolved, stale, or need-more-info issues and
  acting on them via gh CLI; (2) skill-batch intake — evaluating draft proposals in
  registry-for-review/skill-batches/ and routing them toward promotion or rejection. This
  is the gatekeeping step before new skills enter the canonical registry.
---

# gaia-triage

Triage has two distinct workstreams — GitHub issue hygiene and skill-batch intake review.
Run them independently or together depending on what the user asks for. Both workstreams
produce documented, auditable decisions rather than silent changes.

---

## Workstream 1: GitHub Issue Triage

The goal is a clean, signal-rich backlog — not a closed one. Closing issues prematurely
hides real work; leaving stale issues open buries actionable items. For each issue, make
an explicit call: close (resolved), update (needs narrowing), or keep (valid, still open).

### Step 1 — Pull the open issue list

```bash
gh issue list --repo mbtiongson1/gaia-skill-tree --state open --limit 100
```

Group by theme (CLI bug, registry data, docs drift, enhancement). This shapes the
decision pattern — CLI bugs and registry issues require code evidence; enhancement requests
require a current-relevance check against the roadmap.

### Step 2 — Audit each issue against the codebase

Before commenting or closing, verify the claim. Check the evidence paths in
`references/evidence-check.md` for common file locations:

| Issue type | Where to look |
|---|---|
| CLI command request or bug | `src/gaia_cli/commands/` |
| Registry data or duplicate skills | `registry/gaia.json`, `registry/nodes/` |
| Documentation drift | Run `python scripts/build_docs.py --check` |
| Packaging / dependency | `pyproject.toml`, `uv.lock` |
| Test coverage | `tests/` |

### Step 3 — Act via gh CLI

**Post a triage comment** (findings without closing — use when the issue needs narrowing
or a reproduction, or when you want to flag it for a human maintainer):

```bash
gh issue comment <issue-number> --repo mbtiongson1/gaia-skill-tree \
  --body "Triage update: <findings and recommendation>"
```

**Close a resolved issue** (only when codebase evidence confirms it is implemented):

```bash
gh issue close <issue-number> --repo mbtiongson1/gaia-skill-tree \
  --reason completed \
  --comment "Closing as implemented. Evidence: <specific file + line or command output>"
```

**Dry-run first**: the `scripts/triage_batch.sh` script supports `--apply` and
`--close-resolved` flags. Run without flags to preview all comments before posting:

```bash
bash .claude/skills/gaia-triage/scripts/triage_batch.sh
# Then, when ready:
bash .claude/skills/gaia-triage/scripts/triage_batch.sh --apply --close-resolved
```

### Decision guide

| Finding | Action |
|---|---|
| Issue is implemented and tests pass | Close as completed with evidence pointer |
| Issue is valid but under-specified | Comment with narrowing questions; keep open |
| Issue references a stale command name | Comment updating the correct current command; keep open unless fully superseded |
| Issue is a duplicate | Close with a link to the canonical issue |
| Issue is an enhancement blocked on design | Comment with current blocker; keep open |

---

## Workstream 2: Skill-Batch Intake Review

Draft skill proposals land in `registry-for-review/skill-batches/` after a contributor
runs `gaia push`. This workstream gates them before they enter `registry/nodes/`.

Rejecting bad batches here is cheaper than demoting skills after promotion — every skill
that enters the canonical registry acquires timeline history, evidence links, and
downstream references that make later removal messy.

### Step 1 — List pending batches

```bash
ls registry-for-review/skill-batches/
```

Each batch is a JSON file. Read its metadata to understand the contributor and scope before
evaluating individual skills.

### Step 2 — Evaluate each skill proposal

For each skill in the batch, work through these checks in order:

1. **Schema validity** — does the node satisfy the canonical JSON schema?
   ```bash
   gaia validate --intake
   ```
2. **Nomenclature** — does the skill name and description match `CONTEXT.md` vocabulary?
   Flag banned synonyms; the rarity field is deprecated and should not appear in new proposals.
3. **Evidence quality** — at minimum one Class B source (a real published artifact, not a homepage).
   Class C-only evidence is grounds for rejection unless the skill is clearly foundational.
4. **Prerequisite existence** — all `prerequisites[]` IDs must resolve in the current registry.
   ```bash
   gaia dev list --generic | grep <prerequisite-id>
   ```
5. **Duplication check** — does a substantially equivalent skill already exist?
   ```bash
   gaia dev list --generic | grep -i "<skill-name>"
   ```

### Step 3 — Label and route

Apply one of three dispositions per skill:

| Label | Meaning | Next action |
|---|---|---|
| **approve** | Schema valid, evidence solid, no duplicate | Promote via `gaia dev add` |
| **needs-info** | Fixable gap (weak evidence, missing prereq, naming issue) | Comment on the batch file with specifics; do not promote yet |
| **reject** | Duplicate, out of scope, or unfixable schema violation | Document reason; discard batch entry |

For approved skills, promote via CLI (never hand-edit registry nodes directly):

```bash
gaia dev add "<Skill Name>" --type basic --description "<description>"
gaia dev evidence <skill-id> "<url>" --class B
```

After promotion, regenerate Class S artifacts:

```bash
gaia dev docs
```

---

## Output

At the end of a triage pass, report:

- How many issues were reviewed, closed, and left open with comments
- How many batch skills were evaluated, approved, flagged needs-info, and rejected
- Any recurring patterns worth tracking (e.g. a common prereq that's missing from the registry)

This summary helps the next maintainer understand what happened without re-reading every issue thread.
