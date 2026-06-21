---
name: gaia-preview
description: Triggers a remote documentation regeneration and Cloudflare deployment for the current branch to preview visual/design changes.
---

# Skill: gaia-preview

Triggers a remote documentation regeneration and Cloudflare deployment for the current branch. This is the preferred method for design previews when working in containerized environments where localhost is not available.

## Usage

Ask the agent to "preview this branch" or "trigger a design preview".

## Instructions for the Agent

When this skill is invoked:

1. **Commit current work**: Ensure all local changes are committed and pushed to the current branch.
2. **Dispatch Sync + Deploy**: Run the following command:
   ```bash
   gh workflow run sync-artifacts.yml --ref <current_branch> -f deploy=true
   ```
3. **Confirm**: Provide the user with the link to the GitHub Action run.

## Benefits
- **Zero Local Footprint**: No need for `gaia docs build` or `npm` in the local/container environment.
- **Consistent Artifacts**: The GitHub worker always uses the canonical build environment.
- **Automatic Deployment**: Cloudflare is triggered automatically once the build is confirmed.
