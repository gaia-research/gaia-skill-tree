# Worker: badges validator — manual test checklist

The site Worker at `worker/index.js` gates SVG serving on a `?repo=` query
parameter matching the contributor's approved repos in
`docs/badges/registry.json`. It runs ahead of static-asset serving for
`/badges/*` via `run_worker_first` in `wrangler.toml`. Worker fetch handlers
don't run under pytest, so this is a manual smoke-test list — run it locally
before merging changes to the Worker.

## Setup

```bash
npm install -g wrangler
wrangler dev          # reads ./wrangler.toml (Worker + [assets]); serves on :8787
```

## Cases

Replace `H` with a registered handle (e.g. `mbtiongson1`), `F` with a real
SVG (e.g. `handle.svg`), and `R` with a repo from
`docs/badges/registry.json.contributors[H].repos`.

| # | Request | Expected |
|---|---------|----------|
| 1 | `GET /badges/H/F.svg` | 200, real SVG, `x-gaia-badge-state: valid` (back-compat, no `?repo=`) |
| 2 | `GET /badges/H/F.svg?repo=R` | 200, real SVG, `x-gaia-badge-state: valid` |
| 3 | `GET /badges/H/F.svg?repo=evil/repo` | 200, validating SVG, `x-gaia-badge-state: validating`, `x-gaia-badge-repo-claimed: evil/repo` |
| 4 | `GET /badges/unknown-handle/handle.svg?repo=any/thing` | 200, validating SVG (handle not in registry) |
| 5 | `GET /badges/powered-by-gaia.svg` | 200, real SVG (1 segment — doesn't match the badge route; worker passes through) |
| 6 | `GET /badges/H/powered-by-gaia.svg` | 404 (in `PASSTHROUGH_FILES` so never validated, but no such asset exists under a handle dir) |
| 7 | `GET /badges/H/not-found.svg` | 404 (same — the real not-found.svg is the 1-segment `/badges/not-found.svg`) |
| 8 | `GET /badges/samples/rank-1.svg` | 200, real SVG (`samples` in `PASSTHROUGH_HANDLES`) |
| 9 | `GET /badges/samples/rank-1-seal.svg?repo=evil/repo` | 200, real SVG (samples never validated) |
| 10 | `GET /badges/H/F-seal.svg?repo=R` | 200, real seal-only SVG, `valid` |
| 11 | `GET /badges/H/F-seal.svg?repo=evil/repo` | 200, validating SVG |
| 12 | `GET /` and other non-`/badges/` paths | 200, served straight from static assets — **no** `x-gaia-badge-state` header (worker not invoked) |

Byte checks worth running:
- case 2 served bytes `md5sum` == `docs/badges/H/F.svg`
- case 3 served bytes `md5sum` == `docs/badges/not-found.svg`

## Cache headers

Every validated/back-compat response carries
`cache-control: public, max-age=86400, s-maxage=86400` (24h, matching GitHub
camo's TTL). Run case #2 twice and confirm the second is fast — `registry.json`
is served from the in-process module cache (no extra fetch in `wrangler dev`
logs).

## Structured log lines

Every badge decision emits one JSON line via `console.log`. In `wrangler dev`
they print to stdout; in production, `wrangler tail` shows them in real time, or
use **Cloudflare → Workers & Pages → gaia-skill-tree → Logs**.

Schema:
```json
{"evt":"badge_request","handle":"...","file":"...","repo_claimed":"...|null","state":"valid|validating|passthrough_no_repo|passthrough_static"}
```

Quick aggregation queries (after tailing for a bit):

```bash
# Top spoof attempts (claimed-but-wrong repos)
wrangler tail \
  | jq -r 'select(.message | fromjson | .state == "validating") | .message | fromjson | .repo_claimed' \
  | sort | uniq -c | sort -rn | head -10

# Most-embedded contributors (valid hits)
wrangler tail \
  | jq -r 'select(.message | fromjson | .state == "valid") | .message | fromjson | .handle' \
  | sort | uniq -c | sort -rn | head -10
```

## Curl one-liners

```bash
# 1 — back-compat (no ?repo=)
curl -sI http://localhost:8787/badges/mbtiongson1/handle.svg | grep -i 'x-gaia\|status\|cache-control'

# 2 — happy path
curl -sI 'http://localhost:8787/badges/mbtiongson1/handle.svg?repo=mbtiongson1/gaia-skill-tree' | grep -i 'x-gaia\|status'

# 3 — wrong repo
curl -sI 'http://localhost:8787/badges/mbtiongson1/handle.svg?repo=evil/repo' | grep -i 'x-gaia\|status'
curl -s  'http://localhost:8787/badges/mbtiongson1/handle.svg?repo=evil/repo' | grep -o 'validating' || echo 'MISSING validating text'

# 8 — samples passthrough
curl -sI 'http://localhost:8787/badges/samples/rank-1.svg?repo=evil/repo' | grep -i 'x-gaia\|status'
```

## Production smoke after deploy

After Cloudflare deploys the branch, re-run cases #2 / #3 against
`https://gaia.tiongson.co/...` and confirm the validating badge comes back. If
case #3 still serves the real SVG, the Worker isn't running ahead of the static
asset — see `docs/CLOUDFLARE-SETUP.md` § "Production verification".
