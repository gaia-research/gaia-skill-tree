# PR Previews via Cloudflare Pages

Production stays on GitHub Pages (`main/docs/`, custom domain `gaia.tiongson.co`).
Cloudflare Pages handles **PR previews only**, giving each pull request a unique
URL like `pr-42.gaia-skill-tree.pages.dev` without touching the production
branch or the `gh-pages` branch.

## Why this approach

- **Zero workflow maintenance** — Cloudflare reads the PR branch directly; no
  GitHub Actions, no copying, no cross-branch sync.
- **Isolated previews** — each PR gets its own subdomain; no risk to
  production.
- **Fast** — Cloudflare's edge build + CDN; previews appear within ~30 seconds
  of a push.
- **Free tier covers it** — 500 builds/month is comfortably above this repo's
  PR volume.

The `.github/workflows/pr-preview.yml` workflow added in #366 is removed on
this branch because Cloudflare replaces it entirely.

## One-time setup (Cloudflare dashboard)

1. Sign in at https://dash.cloudflare.com and go to **Workers & Pages** →
   **Create application** → **Pages** → **Connect to Git**.
2. Authorize Cloudflare on the `mbtiongson1/gaia-skill-tree` repo
   (read-only is enough).
3. Configure the build:

   | Field                | Value                |
   | -------------------- | -------------------- |
   | Project name         | `gaia-skill-tree`    |
   | Production branch    | `main`               |
   | Framework preset     | `None`               |
   | Build command        | *(leave blank)*      |
   | Build output dir     | `docs`               |
   | Root directory       | `/`                  |
   | Environment vars     | *(none)*             |

4. **Save and Deploy**. Cloudflare builds `main` first — this is fine; we
   ignore the production URL since GitHub Pages still serves
   `gaia.tiongson.co`.
5. In the project's **Settings → Builds & deployments → Preview branches**,
   enable previews for **All non-Production branches** (or restrict to specific
   prefixes like `infra/*`, `docs/*`, `design/*`, `claude/*`).

## How previews work after setup

- Open a PR → Cloudflare builds it → bot comment lands on the PR with a URL:
  `https://<commit-sha>.gaia-skill-tree.pages.dev/`
- Each push to the PR branch triggers a new build at the same URL pattern.
- An alias URL `https://<branch-slug>.gaia-skill-tree.pages.dev/` always
  points at the latest commit of that branch.
- Previews are auto-removed when the branch is deleted.

## Limiting build scope (optional)

If we want Cloudflare to **only** build PRs that touch HTML (mirroring the
original workflow intent), add a `wrangler.toml`-free filter via Cloudflare's
**Build watch paths**:

- Settings → Builds & deployments → **Build watch paths** → include `docs/**`.

That skips builds when a PR only touches `registry/`, `src/`, etc.

## Rollback

If we ever want the old GitHub-Pages-based preview back, revert the deletion
of `.github/workflows/pr-preview.yml` on this branch and remove the
Cloudflare Pages project from the dashboard.

## Cost / quota notes

- Free tier: 500 builds/month, unlimited bandwidth, unlimited requests.
- This repo's PR volume averages well under that. If we ever hit it, the
  watch-paths filter above will cut build count by ~70%.

## Decision record

- **Decided:** 2026-05-22
- **Alternatives considered:** GitHub-Pages-based preview workflow
  (`rossjrw/pr-preview-action`, merged in #366), separate previews repo
  (see `option-3-separate-previews-repo.md`).
- **Why Cloudflare over those:** no copying, no shared-asset
  synchronization, no second repo to maintain.
