# Step 2: Compose

Apply the composition protocol to merge the two source skills into a single fused capability.

## Source Analysis

1. Read the full `SKILL.md` (or main definition) file for both source skills.
2. Read all files inside the `reference/` directory of both source skills, if they exist.
3. Read all files inside the `scripts/` directory of both source skills, if they exist.

## Composition Prompt

Submit the gathered sources to the LLM (using the user's preferred model, or any available model) with the following template:

```
You are composing two AI agent skills into a single fused skill.

=== SKILL A ===
{paste full SKILL.md of skill A}

=== SKILL B ===  
{paste full SKILL.md of skill B}

Create a single SKILL.md that:

1. TRIGGERS: Union of both skills' trigger phrases, deduplicated. Add new triggers that describe the combined capability.
2. SETUP: Merge setup steps. Remove redundancy. If both skills read project context, do it once.
3. WORKFLOW: Create a unified flow that leverages both capabilities together. This is not concatenation -- find the natural integration points where skill A's output feeds skill B, or where they complement each other.
4. REFERENCES: If both skills have reference/ files, list them all. Prefix with the source skill name if there are filename conflicts (e.g., reference/skillA-audit.md).
5. GRACEFUL DEGRADATION: If only one skill's capability is needed in a given invocation, the fused skill should handle that cleanly (not force both workflows).

Output: A complete SKILL.md file with YAML frontmatter (name, description) and markdown body.
Do not add meta-commentary. Output only the SKILL.md content.
```

## Validation

1. Verify that the generated output contains valid YAML frontmatter:
   - Starts with `---` as the first line.
   - Contains a `name:` field.
   - Contains a `description:` field.
   - Closes with `---` on its own line.
2. Run validation script on the output:
   ```bash
   bash scripts/validate.sh <path-to-output-SKILL.md>
   ```

## Preview & Consent

Show a preview of the composed skill definition to the user and prompt for approval before creating files on disk.
