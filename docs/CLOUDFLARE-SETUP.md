# Cloudflare Setup — Repo-bound badge validation

This document explains the **Worker** that gates Gaia README badges on a
`?repo=` query parameter, and how to verify it locally and in production.

## What this does

- Every badge under `https://gaia.tiongson.co/badges/<handle>/<file>.svg` is a
  static SVG committed in `docs/badges/`. On its own, anyone can drop
  `mattpocock`'s badge into any random repo's README — there's no validation.
- Badge URLs now include `?repo=<owner>/<repo>` (the badges page generates
  them). The site Worker (`worker/index.js`) looks `<owner>/<repo>` up in
  `docs/badges/registry.json` and serves the **validating badge**
  (`docs/badges/not-found.svg` — a faint *"validating…"* SVG) when the repo
  isn't registered to that handle.
- 24-hour cache TTL on both valid and invalid responses, matching GitHub
  camo's own caching window. Newly-registered repos go live within 24h via
  natural cache expiry.

## Why a Worker, not a Pages Function

This project deploys as a **Cloudflare Worker with Static Assets**
(`wrangler deploy`, `[assets] directory = "docs"`), *not* as Cloudflare Pages.
Two consequences drove this design:

1. **`functions/` is Pages-only.** A `functions/badges/[handle]/[file].js`
   Pages Function is **not deployed** by `wrangler deploy`. (An earlier version
   of this feature shipped exactly that file — it never ran in production.)
2. **Static assets beat Functions.** Even under `wrangler pages dev`, a
   Function cannot intercept a request that resolves to an existing static
   asset. Since every badge *is* a static SVG, static serving always won and
   the `?repo=` gate never executed.

The fix is `run_worker_first` in `wrangler.toml`:

```toml
name = "gaia-skill-tree"
main = "worker/index.js"
compatibility_date = "2026-05-22"

[assets]
directory = "docs"
binding = "ASSETS"
run_worker_first = ["/badges/*"]
```

`run_worker_first = ["/badges/*"]` makes the Worker execute **before**
static-asset serving for `/badges/*` only. The Worker inspects `?repo=`, then
serves either the real SVG (`env.ASSETS.fetch`) or the validating badge.
Everything outside `/badges/*` is served straight from static assets — the
Worker isn't even invoked, so there's no latency cost on the rest of the site.

## What's in the repo

| Path | Role |
|---|---|
| `wrangler.toml` | Worker entry (`main`) + `[assets]` + `run_worker_first = ["/badges/*"]`. **Authoritative** config; deploy root is `/`. |
| `worker/index.js` | The validator. Runs first on `/badges/*`, passes everything else through to static assets. |
| `docs/badges/registry.json` | Approved-repos lookup the Worker reads. Schema `gaia-badges-registry/2`. |
| `docs/badges/not-found.svg` | The "validating…" badge served on `?repo=` mismatch. |
| `docs/wrangler.toml` | Secondary/fallback config (assets only, no worker). Not used by the configured deploy. |
| `tests/test_badges_function.md` | 11-case manual smoke-test list runnable via `wrangler dev`. |

## Cloudflare side

No dashboard toggle is required — the Worker and its asset binding are defined
entirely in `wrangler.toml`. Confirm in the Cloudflare dashboard only that:

1. **Workers & Pages → `gaia-skill-tree` → Settings → Build** has **Root
   directory = `/`** (so the repo-root `wrangler.toml` is the one used).
2. The deploy command is `wrangler deploy` (it is, via the git-integrated
   Workers Build and `.github/workflows/cloudflare-deploy.yml`).
3. The wrangler version in the build environment supports `run_worker_first`
   (wrangler ≥ 3.84 / any current 4.x). If an older pinned wrangler ignores it,
   the Worker would fall back to *not* running ahead of assets — see the
   production check below to catch that.

## Local verification (before pushing)

```bash
# In the repo root:
npm install -g wrangler            # if you haven't already
wrangler dev                       # reads ./wrangler.toml; serves on :8787
```

Then run the curl checks from `tests/test_badges_function.md`, e.g.:

```bash
# 1 — back-compat (no ?repo=) → real badge, x-gaia-badge-state: valid
curl -sI http://localhost:8787/badges/mbtiongson1/handle.svg \
  | grep -i 'x-gaia\|cache-control'

# 3 — wrong repo → validating badge
curl -s 'http://localhost:8787/badges/mbtiongson1/handle.svg?repo=evil/repo' \
  | grep -o 'validating' || echo 'MISSING validating text'
curl -sI 'http://localhost:8787/badges/mbtiongson1/handle.svg?repo=evil/repo' \
  | grep -i 'x-gaia-badge-state'   # → validating
```

`x-gaia-badge-state` header values:
- `valid` — pass-through, real badge served
- `validating` — `?repo=` didn't match, faint badge served

## Production verification (after deploy)

Once Cloudflare deploys the branch:

```bash
# back-compat (existing badges keep working)
curl -sI https://gaia.tiongson.co/badges/mbtiongson1/handle.svg | grep -i 'x-gaia\|cache-control'

# happy path
curl -sI 'https://gaia.tiongson.co/badges/mbtiongson1/handle.svg?repo=mbtiongson1/gaia-skill-tree' | grep -i 'x-gaia'

# wrong repo (MUST serve validating badge)
curl -s 'https://gaia.tiongson.co/badges/mbtiongson1/handle.svg?repo=evil/repo' | grep -o 'validating'
```

If case #3 returns the real SVG (no `validating` text and no
`x-gaia-badge-state: validating` header), the Worker isn't running ahead of the
static asset. Check, in order:

- **Root directory** is `/` (so repo-root `wrangler.toml` is used, not
  `docs/wrangler.toml`).
- The build log shows `main = worker/index.js` bundled and the
  `run_worker_first` asset rule applied.
- The build-environment wrangler version supports `run_worker_first`.

## How invalidation works

- **Edge cache:** `Cache-Control: public, max-age=86400, s-maxage=86400`. After
  24h, Cloudflare re-runs the Worker and pulls fresh `registry.json`.
- **In-process registry cache:** the Worker holds the parsed `registry.json` in
  module scope for 24h. **A redeploy resets it** — pushing a commit spins up a
  fresh Worker bundle, so a newly-registered repo is live immediately for
  direct hits.
- **GitHub camo:** ~24h regardless of our headers. Users can force-refresh
  their README on github.com to bump it.

## Rollback

To revert to static-only behaviour (no `?repo=` validation):

```bash
# Remove the worker entry + run_worker_first; keep assets serving.
# wrangler.toml → delete `main` and the `run_worker_first` line.
git rm worker/index.js
git commit -m "revert: badge validation worker"
git push
```

Static SVGs are then served directly again, with no validation. No
infrastructure state to clean up.

## Known limitations / future work

- **No Referer-based validation.** GitHub camo strips `Referer`, so we can't
  prove the README *actually* lives on the claimed repo — we only check the
  `?repo=` string against the approved list. A bad actor could still copy
  someone's badge URL verbatim. **Tracked under #155** (sign in to GitHub);
  the real fix is OAuth → signed token-bound rendering.
- **Analytics — Path A is live.** The Worker emits one structured log line per
  request via `console.log`. Tail with `wrangler tail` or
  **Cloudflare → Workers & Pages → gaia-skill-tree → Logs**. Schema and jq
  queries are in `tests/test_badges_function.md` § "Structured log lines".
- **Analytics — Path B is queued.** Workers Analytics Engine for queryable
  time-series + an admin dashboard, tracked under #455.
