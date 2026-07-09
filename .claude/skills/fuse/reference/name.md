# Step 3: Name

Select a unique name for the new fused skill.

## Naming Protocol

1. Propose 3 candidate names in `kebab-case` based on the combined capabilities of both source skills.
2. Ensure each proposed name meets these criteria:
   - Descriptive of the merged behavior.
   - Maximum 30 characters in length.
   - Does not already exist in the skills directory.
3. Check for collisions by listing the active skills directory:
   ```bash
   ls -d <skills-dir>/*/
   ```
   Verify that none of the proposed candidates match an existing subdirectory name.
4. Present the 3 candidates to the user.
5. Accept either a user selection from the candidates or a custom name provided by the user.
6. The final selected name becomes the subdirectory name for the fused skill.
