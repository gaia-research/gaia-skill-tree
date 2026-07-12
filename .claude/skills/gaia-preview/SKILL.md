---
name: gaia-preview
description: >
  Use this skill whenever the user wants to see how their changes will look on the live Gaia website
  before merging — "preview this branch", "show me what this looks like", "deploy a preview",
  "trigger a design preview", "can I see the site with these changes", "preview the skill profile",
  "check how this renders on the site", "spin up a preview deployment". This skill dispatches a
  remote documentation regeneration and Cloudflare preview deployment for the current branch via
  GitHub Actions — no local build tooling required. Ideal for containerized environments, design
  reviews, and confirming that newly curated skills or profile pages render correctly before a PR
  is merged to main.
---

# Skill: gaia-preview

Dispatches a remote docs regeneration and Cloudflare preview deployment for the current branch. Use this instead of running `gaia dev docs` locally — the GitHub Actions worker uses the canonical build environment, so what you see is exactly what production will serve.

## When to use

- You've made design, layout, or content changes and want to see them live before opening a PR.
- You're working in a container or remote environment where `localhost` is unavailable.
- You want to verify a newly curated skill or contributor profile renders correctly on the site.
- You've edited `docs/` files and want a sanity check before merging.

## Steps

1. **Push your work.** Commit and push all local changes to the current branch. The workflow runs against what's on the remote, so anything uncommitted won't appear in the preview.

2. **Dispatch the preview workflow.** Run:
   ```bash
   gh workflow run cf-pr-preview.yml -f branch=<current_branch>
   ```
   Replace `<current_branch>` with the actual branch name (get it with `git rev-parse --abbrev-ref HEAD`). This deploys a Cloudflare Worker preview for the branch. Do **not** use `sync-artifacts.yml` — its job is gated to `main` (`if: github.ref_name == default_branch`), so dispatching it on a feature branch silently skips.

3. **Share the run link.** After dispatching, retrieve the run URL and give it to the user:
   ```bash
   gh run list --workflow=cf-pr-preview.yml --limit 1
   ```
   The Cloudflare preview URL is posted as a workflow output once the build completes (typically 2–4 minutes).

## Local inspection (fastest path)

For a quick local look without waiting on the remote build, serve `docs/` directly:
```bash
python -m http.server 8080 --directory docs
```
Then open `http://localhost:8080/`. This serves the static site exactly as GitHub Pages would, minus the Cloudflare Worker badge-validation layer.
