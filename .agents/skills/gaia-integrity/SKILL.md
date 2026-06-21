---
name: gaia-integrity
description: Verify and maintain the consistency of the Gaia Skill Registry via canonical validation and structural checks.
---

# Gaia Registry Integrity Skill

Use this skill to quickly verify and maintain the consistency of the Gaia Skill Registry. It combines canonical validation with structural checks.

## Quick Integrity Check

The primary tool for this skill is the consolidated integrity script. It runs canonical validation and checks for documentation/node alignment.

```bash
# Run all integrity checks
./.agents/skills/gaia-integrity/scripts/check_integrity.sh

# Archive all orphan documentation (stale/stray .md files)
./.agents/skills/gaia-integrity/scripts/archive_orphans.sh
```

### Checks Performed by `check_integrity.sh`:
1.  **Canonical Validation:** Runs `gaia validate` to check schema, cycles, and reference integrity.
2.  **Documentation Alignment:** Ensures every node in `registry/nodes/` has a matching `.md` file in `registry/skills/` of the **same type**.
3.  **Orphan Documentation:** Identifies `.md` files in `registry/skills/` that do not have a matching `.json` node in `registry/nodes/` of the **same type**.

## Archive & Cleanup

The `archive_orphans.sh` script provides a safe way to clean up the registry:
*   **Safe Storage:** Files are moved to `registry/archive/YYYYMMDD_HHMMSS/` rather than deleted.
*   **Structure Preservation:** The original type folders (`basic/`, `extra/`, etc.) are maintained in the archive.
*   **Automation:** Useful after renaming skills or changing skill types.

## Procedures

### Before Submitting a PR
1.  Run `gaia validate`.
2.  Run `./.agents/skills/gaia-integrity/scripts/check_integrity.sh`.
3.  Ensure all "Missing" and "Orphan" reports are resolved or justified.
4.  If nodes were added/removed, run `gaia docs build` to update `gaia.json` and site artifacts.
