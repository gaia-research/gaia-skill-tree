# Meta-Audit Criteria and Policy Updates

As of the May 2026 Meta-Audit, the following criteria updates are active for Gaia registry curation:

## 1. Stricter Evidence for 4★+ Skills
Any skill claiming a level of **4★ (Hardened)** or higher must rely on live, verifiable, and composable usage evidence.
*   **Seed Evidence Ban:** The use of placeholder `gaia-registry/gaia` seed evidence (e.g., `docs/evidence/seed.md`, `docs/evidence/autonomousDebug.md`) is no longer sufficient to maintain a 4★+ ranking.
*   Skills currently relying on such seed evidence will be flagged in the meta-audit queue and are subject to demotion if live evidence is not provided.

## 2. Prohibition of Repo-Root Links for Named Claims
When adding entries to `registry/real-skills.json` or claiming a named skill, the source URL must point to a specific skill implementation.
*   **No Generic Repositories:** URLs resolving to generic repository roots (e.g., `https://github.com/karpathy/autoresearch`, `https://github.com/cognition-labs/devin`) or homepages are no longer accepted.
*   **Explicit Files Required:** Source links must point directly to a concrete `SKILL.md` file, an agent playbook, or an explicit source code implementation (e.g., `.md`, `.py`, `.ts`, `.json`).

Contributors are encouraged to review the queue in `docs/audits/` and update their evidence accordingly before the next major registry curation pass.
