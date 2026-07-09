# Step 1: Detect

Identify the two source skills to be fused.

## Input Resolution

- If the user provided two explicit skill names (e.g., `/fuse shape + audit` or `/fuse shape and audit`), use those directly.
- Otherwise, locate the skills directory and scan it for installed skills.

## Scanning Installed Skills

1. Scan directories under the detected skills directory (`.agents/skills/`, `.claude/skills/`, or `.cursor/rules/`).
2. For each directory:
   - Verify if a `SKILL.md` (or relevant `.md` rule/definition) exists.
   - Read the file and extract the skill `name` and the first line of the description from the YAML frontmatter.
3. Present the list of detected skills to the user as a numbered list.
4. Prompt the user to select two skills (e.g., `1 and 3` or `shape and audit`) or confirm a suggested pair.

## Script Automation

To get a quick machine-readable list of available candidates, run:
```bash
bash scripts/candidates.sh
```

## Output

Two verified file paths pointing to the source skill directories.
