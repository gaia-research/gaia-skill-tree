# Plan: Separate Previews Repo (Option 3)

A fallback / alternative to the Cloudflare Pages plan
(`cloudflare-pages-preview.md`). Keeps everything inside GitHub by routing PR
previews to a dedicated repository whose GitHub Pages site is wired to a
preview subdomain.

## Status

**Planned — not implemented.** Pursue this only if Cloudflare Pages becomes
unviable (account loss, build-quota issues, or a desire to keep the entire
stack inside GitHub).

## Architecture

```
mbtiongson1/gaia-skill-tree            (this repo — production)
  └── main/docs/                       served at gaia.tiongson.co (GitHub Pages)

mbtiongson1/gaia-skill-tree-previews   (new repo — previews only)
  └── main/                            served at previews.tiongson.co
       ├── pr-42/index.html            (full doc tree per PR)
       ├── pr-43/...
       └── _shared/css|js|assets       (synced from production)
```

Production repo's Pages config is untouched. The previews repo is
write-only from GitHub Actions; no humans push to it.

## Why this exists as an option

- **All-GitHub stack** — no third-party dashboards, no Cloudflare account
  dependency.
- **Strong branch isolation** — preview artifacts can never accidentally
  affect production because they live in a different repo.
- **Permission boundary** — the deploy token only has write access to the
  previews repo, not the main one.

## Implementation steps

### 1. Create the previews repo

- Owner: `mbtiongson1`
- Name: `gaia-skill-tree-previews`
- Visibility: public (Pages requires this on free tier) or private with
  Pro/Enterprise.
- Initial commit: a README and an empty `.nojekyll` file at root.
- Settings → Pages: deploy from `main / (root)`.
- Settings → Custom domain: `previews.tiongson.co` (add a `CNAME` file at
  the root of `main`).

### 2. DNS

In the DNS provider for `tiongson.co`, add a CNAME record:

```
previews   CNAME   mbtiongson1.github.io.
```

Wait for GitHub to issue the certificate (typically minutes).

### 3. Cross-repo deploy token

- Generate a fine-grained PAT scoped **only** to
  `mbtiongson1/gaia-skill-tree-previews` with **Contents: read & write**.
- Add it to `mbtiongson1/gaia-skill-tree` repo secrets as
  `PREVIEWS_REPO_TOKEN`.
- Token rotation: annually, calendared.

### 4. New preview workflow

Replace the deleted `.github/workflows/pr-preview.yml` with a new workflow
that:

- Triggers on PR `opened | synchronize | reopened | closed`, paths
  `docs/**`.
- On open/sync/reopen:
  1. Checks out the PR branch.
  2. Computes changed files via `git diff --name-only $base...HEAD --
     docs/**`.
  3. Builds a minimal artifact tree containing **only the changed HTML
     pages plus a symlink/reference to `_shared/`**.
  4. Pushes the artifact to `gaia-skill-tree-previews` at path
     `pr-<number>/` using `peaceiris/actions-gh-pages` (or a raw
     `git push` with the cross-repo token).
  5. Comments the URL `https://previews.tiongson.co/pr-<number>/` on the
     PR.
- On close:
  1. Clones the previews repo.
  2. Removes the `pr-<number>/` directory.
  3. Pushes the deletion.

### 5. Shared-asset sync

CSS, JS, fonts, and OG assets change rarely. A second workflow on
`gaia-skill-tree` triggers on push to `main` whenever `docs/css/**`,
`docs/js/**`, `docs/assets/**`, or `docs/og/**` changes, and mirrors them
to `_shared/` in the previews repo. PR HTML references shared assets via
absolute paths like `/_shared/css/main.css`.

This avoids re-copying assets per PR (the original "super unoptimized"
concern) while still keeping each PR's HTML self-contained from a routing
perspective.

### 6. HTML path rewriting

PR HTML in `docs/` references assets via relative paths
(e.g. `./css/main.css`). Two options for the previews site:

- **A. Build-step rewrite:** the preview workflow runs a small `sed`/
  Python pass that rewrites `./css/`, `./js/`, `./assets/`, `./og/` to
  `/_shared/css/`, etc., before pushing.
- **B. Source-side change:** update the actual `docs/` HTML to reference
  assets via root-absolute paths now and forever. Production stays
  identical; previews "just work."

**Recommendation: B.** One-time change, no per-PR rewriting cost, and
makes the codebase friendlier to any future preview surface.

### 7. Cleanup retention

A nightly scheduled workflow on the previews repo deletes any `pr-N/`
directory whose corresponding PR has been closed for more than 30 days.
This bounds repo size growth even if the close-event cleanup ever misses.

## Migration steps (if/when we adopt this)

1. Land step 6B (root-absolute asset paths) on a `docs/` branch first;
   verify production still renders correctly.
2. Create the previews repo (step 1) and DNS (step 2).
3. Provision the token (step 3).
4. Add the preview workflow and the shared-asset sync workflow
   (steps 4–5) on an `infra/previews-repo` branch.
5. Open a test PR that touches `docs/index.html`; verify the preview URL
   resolves and assets load.
6. Tear down Cloudflare Pages project.

## Trade-offs vs Cloudflare Pages

| Dimension              | Cloudflare Pages       | Separate Previews Repo |
| ---------------------- | ---------------------- | ---------------------- |
| Setup complexity       | Low (dashboard only)   | Medium (token, DNS, two workflows) |
| Ongoing maintenance    | None                   | Token rotation, retention job |
| Build speed            | ~30s edge build        | ~1–2 min GitHub Actions |
| Per-PR cost            | Free tier              | Free (GitHub Actions minutes) |
| Vendor lock-in         | Cloudflare             | None (all GitHub) |
| "Only changed pages"   | Whole site per PR      | Native — diff-driven copy |
| Custom-domain story    | `*.pages.dev` subdomains | `previews.tiongson.co/pr-N/` |
| Failure blast radius   | Cloudflare outage = no previews | GitHub outage = no previews (same as main repo) |

## Open questions for whoever implements this

- Do we want previews public or behind GitHub auth? Public is simpler;
  private requires the previews repo to be private, which voids the free
  Pages tier.
- Retention window: 30 days post-close enough, or longer for audit?
- Should the cleanup also delete previews for stale, never-closed PRs
  (e.g. open for 90+ days, no activity)?
