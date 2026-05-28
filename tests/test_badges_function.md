# Pages Function: badges validator — manual test checklist

The Cloudflare Pages Function at `functions/badges/[handle]/[file].js` gates SVG
serving on a `?repo=` query parameter matching the contributor's approved repos
in `docs/badges/registry.json`. Pages Functions don't run under pytest, so this
is a manual smoke-test list — run it locally before merging changes to the
function.

## Setup

```bash
npm install -g wrangler
wrangler pages dev docs --compatibility-date=2026-05-22
# Pages Functions auto-load from functions/ — no extra config needed.
# Local server: http://localhost:8788
```

## Cases

Replace `H` with a registered handle (e.g. `mbtiongson1`), `F` with a real
SVG (e.g. `handle.svg`), and `R` with a repo from
`docs/badges/registry.json[H].repos`.

| # | Request | Expected |
|---|---------|----------|
| 1 | `GET /badges/H/F.svg` | 200, real SVG, `x-gaia-badge-state: valid` |
| 2 | `GET /badges/H/F.svg?repo=R` | 200, real SVG, `x-gaia-badge-state: valid` |
| 3 | `GET /badges/H/F.svg?repo=evil/repo` | 200, validating SVG, `x-gaia-badge-state: validating`, `x-gaia-badge-repo-claimed: evil/repo` |
| 4 | `GET /badges/unknown-handle/handle.svg?repo=any/thing` | 200, validating SVG (handle not in registry) |
| 5 | `GET /badges/powered-by-gaia.svg` | passthrough (route doesn't match function — 1 segment after `/badges/`) |
| 6 | `GET /badges/H/powered-by-gaia.svg` | 200, real SVG (file in `PASSTHROUGH_FILES`) |
| 7 | `GET /badges/H/not-found.svg` | 200, real SVG (file in `PASSTHROUGH_FILES`) |
| 8 | `GET /badges/samples/rank-1.svg` | 200, real SVG (handle in `PASSTHROUGH_HANDLES`) |
| 9 | `GET /badges/samples/rank-1-seal.svg?repo=evil/repo` | 200, real SVG (samples never validated) |
| 10 | `GET /badges/H/F-seal.svg?repo=R` | 200, real seal-only SVG |
| 11 | `GET /badges/H/F-seal.svg?repo=evil/repo` | 200, validating SVG |

## Cache headers

Every response should carry `cache-control: public, max-age=86400, s-maxage=86400`
(24h, matching GitHub camo's TTL). Run case #2 twice and confirm the second
response is fast — the registry.json fetch should be served from the in-process
cache (no extra fetch in `wrangler pages dev` logs).

## Structured log lines

Every request emits one JSON line via `console.log`. In `wrangler pages dev`
they print to stdout; in production, `wrangler pages deployment tail` shows
them in real time, or use **Cloudflare → Pages → gaia-skill-tree → Logs**.

Schema:
```json
{"evt":"badge_request","handle":"...","file":"...","repo_claimed":"...|null","state":"valid|validating|passthrough_no_repo|passthrough_static"}
```

Quick aggregation queries (paste into a terminal once you've tailed for a bit):

```bash
# Top spoof attempts (claimed-but-wrong repos)
wrangler pages deployment tail \
  | jq -r 'select(.message | fromjson | .state == "validating") | .message | fromjson | .repo_claimed' \
  | sort | uniq -c | sort -rn | head -10

# Most-embedded contributors (valid hits)
wrangler pages deployment tail \
  | jq -r 'select(.message | fromjson | .state == "valid") | .message | fromjson | .handle' \
  | sort | uniq -c | sort -rn | head -10
```

## Curl one-liners

```bash
# 1 — back-compat (no ?repo=)
curl -sI http://localhost:8788/badges/mbtiongson1/handle.svg | grep -i 'x-gaia\|status\|cache-control'

# 2 — happy path
curl -sI 'http://localhost:8788/badges/mbtiongson1/handle.svg?repo=mbtiongson1/gaia-skill-tree' | grep -i 'x-gaia\|status'

# 3 — wrong repo
curl -sI 'http://localhost:8788/badges/mbtiongson1/handle.svg?repo=evil/repo' | grep -i 'x-gaia\|status'
curl -s  'http://localhost:8788/badges/mbtiongson1/handle.svg?repo=evil/repo' | grep -o 'validating' || echo 'MISSING validating text'

# 5 — samples passthrough
curl -sI 'http://localhost:8788/badges/samples/rank-1.svg?repo=evil/repo' | grep -i 'x-gaia\|status'
```

## Production smoke after deploy

After Cloudflare Pages picks up the new branch, re-run cases #2 / #3 against
`https://gaia.tiongson.co/...` and confirm the validating badge comes back. If
case #3 still serves the real SVG, the function isn't wired — check the
**Pages → Settings → Functions** tab in Cloudflare dashboard (it should auto-
detect `functions/` once a build completes).
