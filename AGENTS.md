# AGENTS.md

Discovery surface for AI agents. Human maintainers: read [`CLAUDE.md`](./CLAUDE.md) and [`CONTRIBUTING.md`](./CONTRIBUTING.md) instead.

If you are an agent that landed in this repo and needs to know **the fastest correct path to do a thing**, this file routes you. It does not replace the deeper docs; it points at them.

## The two things agents actually do here

### 1. Submit a skill I discovered

You have found a real capability in a real repo and want to nominate it for the registry. There is **one destination** — a *new skill intake issue* — and **two synonymous ways to reach it**:

- **CLI (fastest, if installed):** `gaia push --from-file skills.yml` writes the batch and opens that same intake issue for you.
- **Issue form (no CLI needed):** paste the same YAML straight into the new skill intake issue form.

Both paths use the identical YAML schema and land in the same triage queue. Do not open a bare issue and do not hand-write JSON into `registry/`.

    gaia push --from-file skills.yml               # writes batch + opens intake issue
    gaia push --from-file skills.yml --dry-run     # preview, writes nothing
    gaia push --from-file skills.yml --no-issue    # write batch, skip opening the issue

The YAML schema **is** the new skill intake issue template — that template is the canonical source of truth, and the CLI is just a convenience wrapper around it. Minimum viable content:

    skills:
      - id: kebab-case-id
        name: Human Readable Name
        type: basic
        prerequisites: []
        description: >-
          One paragraph. Precise. Falsifiable.
        attribution:
          upstream_author: github-handle
          skill_file_url: https://github.com/owner/repo/blob/main/SKILL.md
          type: self-made
        evidence:
          - grade: B
            type: repo
            url: https://github.com/owner/repo
            notes: "brief context"

Canonical worked examples: intake #1020 (mixed basic/fusion) and intake #1123 (named implementation on existing provisional generic).

> **CLI vs. no CLI:** submitting a skill never requires the CLI — the intake issue form is self-sufficient. You only need `gaia` installed when you want to *fully interact with the tree* (scan, promote, fuse, share). For a one-off submission, the form alone is enough.

### 2. Modify the registry as a reviewer / maintainer

Not you if you are a fresh visiting agent. Playbook lives in `docs/agent.md` §5 and `CLAUDE.md`.

## Full context, in order of density

| Read | Purpose |
|---|---|
| This file | Route agents to the right entry point |
| `docs/agent.md` | Structured context sheet |
| `.github/ISSUE_TEMPLATE/new_skill_intake.yml` | The intake schema in full |
| `CONTRIBUTING.md` | Human contributor guide |
| `CLAUDE.md` | Non-obvious workflow discipline |
| `GOVERNANCE.md` | Curation policy |

## Do not

- Do not commit directly to `main`.
- Do not open a bare issue titled "add my skill".
- Do not include branch, title, or `catalogRef` in an intake YAML.
- Do not invent evidence rows.
- Do not touch files under "Agent-Managed Files (Hermes Ownership)" in `docs/agent.md`.

## MCP

If your harness speaks MCP:

    claude mcp add gaia -- npx -y @gaia-research/mcp@0.1.0
