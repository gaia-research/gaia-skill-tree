# Cloudflare Setup — Repo-bound badge validation

This document walks through enabling the **Pages Function** that gates Gaia
README badges on a `?repo=` query parameter, and verifies the deploy
end-to-end.

## What this does

- Today, every badge under `https://gaia.tiongson.co/badges/<handle>/<file>.svg`
  is a static SVG. Anyone can drop `mattpocock`'s badge into any random repo's
  README — there's no validation.
- After this rolls out, badge URLs include `?repo=<owner>/<repo>` (the page
  generator already produces them). Cloudflare runs a Pages Function on every
  request, looks up `<owner>/<repo>` in `docs/badges/registry.json`, and
  serves the **validating badge** (`docs/badges/not-found.svg` — a faint
  *"validating…"* SVG) when the repo isn't registered to that handle.
- 24-hour cache TTL on both valid and invalid responses. Newly-registered
  repos go live within 24h via natural cache expiry, matching GitHub camo's
  own caching window.

## Prerequisites

- A Cloudflare account with the `gaia-skill-tree` Pages project already
  connected to the GitHub repo. (You're presumably already deploying
  `docs/` from `wrangler.toml` — that part stays unchanged.)
- The branch `design/profile-enhancements-rev` (or whichever branch this
  lands on) merged to `main`, or a Preview deployment of the branch.

## What's already in the repo

| Path | Role |
|---|---|
| `wrangler.toml` | Asset binding `directory = "docs"`. **No change needed** — Pages auto-picks up the `functions/` directory below. |
| `functions/badges/[handle]/[file].js` | The validator. Pages auto-discovers it on the next deploy. |
| `docs/badges/registry.json` | Approved-repos lookup the function reads. Schema `gaia-badges-registry/2`. |
| `docs/badges/not-found.svg` | The "validating…" badge served on `?repo=` mismatch. |
| `tests/test_badges_function.md` | 11-case manual smoke-test list runnable via `wrangler pages dev docs`. |

## Cloudflare side: enable Pages Functions

If your project was created before Pages Functions launched, the **Functions**
toggle may need flipping once:

1. Cloudflare Dashboard → **Pages** → `gaia-skill-tree` → **Settings** → **Functions**.
2. Confirm **"Enable Pages Functions"** is on. (For projects deployed in 2023+
   this is on by default.)
3. Confirm the **Compatibility date** is `2026-05-22` or later (matches
   `wrangler.toml`). Older dates won't break things but newer JS features
   may fall back.
4. **Build & deploy** settings — no change. Pages auto-detects the
   `functions/` directory at the repo root and builds it. There's nothing to
   set in `Build command` or `Build output directory` beyond what's already
   there.
5. **Compatibility flags** — none needed. The function uses only standard
   Workers APIs (`Request`, `Response`, `URL`, `env.ASSETS.fetch`).

## Local verification (before pushing)

```bash
# In the repo root:
npm install -g wrangler         # if you haven't already
wrangler pages dev docs --compatibility-date=2026-05-22
# Pages Functions auto-load from functions/ — no extra flags needed.
# Local server: http://localhost:8788
```

Then run the curl checks from `tests/test_badges_function.md`:

```bash
# 1 — back-compat (no ?repo=) → real badge
curl -sI http://localhost:8788/badges/mbtiongson1/handle.svg \
  | grep -i 'x-gaia\|status\|cache-control'

# 2 — happy path (registered repo) → real badge
curl -sI 'http://localhost:8788/badges/mbtiongson1/handle.svg?repo=mbtiongson1/gaia-skill-tree' \
  | grep -i 'x-gaia\|status'

# 3 — wrong repo → validating badge
curl -sI 'http://localhost:8788/badges/mbtiongson1/handle.svg?repo=evil/repo' \
  | grep -i 'x-gaia\|status'
curl -s 'http://localhost:8788/badges/mbtiongson1/handle.svg?repo=evil/repo' \
  | grep -o 'validating' || echo 'MISSING validating text'
```

Expected `x-gaia-badge-state` header values:
- `valid` — pass-through, real badge served
- `validating` — `?repo=` didn't match, blank/faint badge served

## Production verification (after deploy)

Once Cloudflare picks up the new branch:

```bash
# 1 — production back-compat (existing badges in READMEs keep working)
curl -sI https://gaia.tiongson.co/badges/mbtiongson1/handle.svg \
  | grep -i 'x-gaia\|cache-control'

# 2 — production happy path
curl -sI 'https://gaia.tiongson.co/badges/mbtiongson1/handle.svg?repo=mbtiongson1/gaia-skill-tree' \
  | grep -i 'x-gaia'

# 3 — production wrong repo (should serve validating badge)
curl -s 'https://gaia.tiongson.co/badges/mbtiongson1/handle.svg?repo=evil/repo' \
  | grep -o 'validating'
```

If case #3 returns the real SVG (no `validating` text), the function isn't
wired. Check the deploy log in **Cloudflare → Pages → gaia-skill-tree →
Deployments → latest → Functions** — there should be one function listed:
`/badges/[handle]/[file]`. If it's missing, the build didn't pick up
`functions/`. Most common causes:

- The build's output directory is set to a subfolder that doesn't include
  `functions/`. Check **Settings → Build & deployments → Build output
  directory** is empty or set to `docs` (root pages assets).
- The Functions toggle is off (see above).
- The Pages project is older than 2022-11. Re-deploy with a fresh project
  if so.

## How invalidation works

- **Edge cache:** `Cache-Control: public, max-age=86400, s-maxage=86400`. After
  24h, Cloudflare re-runs the function and pulls fresh `registry.json`.
- **In-process registry cache:** the function holds the parsed `registry.json`
  in module scope for 24h to avoid re-fetching on every hit. **A redeploy
  resets this** — pushing a commit to `main` automatically invalidates the
  module-scope cache because Cloudflare spins up a fresh worker bundle.
- **GitHub camo:** ~24h regardless of our headers. Users can force-refresh
  their own README on github.com to bump it.

So the worst-case "I just registered my repo" timeline is:

1. PR merged → CI regenerates `registry.json` → Cloudflare auto-deploys
   (~2 min).
2. Edge function picks up the new registry on the next request to any badge
   (the in-process cache is fresh because the worker was just spun up).
3. The user's README still shows the validating badge for up to 24h because
   GitHub camo cached the old response.
4. The user (or anyone) hits the badge URL directly in a browser → sees the
   real badge → loads their README → camo refetches → valid badge appears.

This is documented in `docs/badges/index.html` under the **"Why might my
badge appear blank in my README?"** disclosure on the badges page.

## Rollback

If something goes wrong and you want the old static-only behaviour back:

```bash
git rm functions/badges/[handle]/[file].js
git commit -m "revert: badges Pages Function"
git push
```

Cloudflare auto-deploys without the function on the next push. Static SVGs
are served directly again, with no `?repo=` validation. No infrastructure
state to clean up.

## Open questions / future work

- **No Referer-based validation.** GitHub camo strips `Referer`, so we can't
  prove the README *actually* lives on the claimed repo — we only check the
  `?repo=` string against the approved list. A bad actor could still copy
  someone's badge URL verbatim into their own README. **Tracked as a sub-task
  of #155** (NEW UI - sign in to github) since the real fix is GitHub OAuth
  → signed token-bound rendering.
- **Per-repo analytics — Path A is live.** The function emits one structured
  log line per request via `console.log`. Tail with
  `wrangler pages deployment tail` or **Cloudflare Dashboard → Pages →
  gaia-skill-tree → Logs**. Schema is documented in
  `tests/test_badges_function.md` § "Structured log lines", with ready-made
  jq queries for "top spoof attempts" and "most-embedded contributors".
- **Per-repo analytics — Path B is queued.** Workers Analytics Engine for
  queryable historical time-series + admin dashboard tracked under #455
  (Github Badges).

