# Step 4: Register

Finalize the skill fusion by creating the new directory structure, copying files, logging the event, and outputting the summary.

## Registration Steps

1. Create a new directory for the fused skill:
   ```bash
   mkdir -p <skills-dir>/<chosen-name>/
   ```
2. Write the newly composed `SKILL.md` to `<skills-dir>/<chosen-name>/SKILL.md`.
3. Copy all files from `reference/` and `scripts/` of both source skills to the target directory. If there is a naming collision (e.g. `reference/audit.md` exists in both), prefix the file with the source skill's name (e.g., `reference/skillA-audit.md`).

## Optional Gaia Integration

1. Check if the `.gaia/` directory exists in the project root.
2. If `.gaia/` exists:
   - Read or create `.gaia/fuse-log.json`.
   - Append a new JSON object to the log:
     ```json
     {
       "timestamp": "<ISO8601>",
       "sourceSkills": ["<source-a>", "<source-b>"],
       "fusedSkill": "<chosen-name>",
       "outputPath": "<skills-dir>/<chosen-name>/"
     }
     ```
   - Print: `Fusion logged to .gaia/fuse-log.json`
   - Print: `Run 'gaia push' to propose this skill to the Gaia registry (optional)`
3. If `.gaia/` does NOT exist:
   - Skip logging and printing any Gaia-related suggestions.

## Summary

Print the following completion summary:
```
Fused skill created: <chosen-name>
  Source: <source-a> + <source-b>
  Path:   <skills-dir>/<chosen-name>
  Invoke: /<chosen-name>
```
