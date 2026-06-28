# Worker: badges validator — manual test checklist

The site Worker at `worker/index.js` gates badge serving on a `?repo=` query
matching the contributor's approved repos in `docs/badges/registry.json`.

It needs **both** `run_worker_first = true` (so the Worker runs at all in this
deploy) **and** the real SVGs relocated to `docs/badges/_assets/<handle>/` (so
the public `/badges/<handle>/<file>.svg` path has no static asset shadowing the
Worker). The Worker serves the real SVG from `_assets` (or `not-found.svg` on a
mismatch). Worker fetch handlers don't run under pytest, so this is a manual
smoke-test list — run it locally (`wrangler dev`) and against the PR preview
deploy before merging changes to the Worker or to `generateBadges.py`'s layout.

## Setup

```bash
npm install -g wrangler
wrangler dev          # reads ./wrangler.toml (Worker + [assets]); serves on :8787
```

## Cases

`H` = registered handle (e.g. `mbtiongson1`), `F` = a real SVG (e.g.
`handle.svg`), `R` = a repo from `registry.json.contributors[H].repos`.

| # | Request | Expected |
|---|---------|----------|
| 1 | `GET /badges/H/F.svg` | 200, real SVG, `x-gaia-badge-state: valid` (back-compat, no `?repo=`) |
| 2 | `GET /badges/H/F.svg?repo=R` | 200, real SVG, `x-gaia-badge-state: valid` |
| 3 | `GET /badges/H/F.svg?repo=evil/repo` | 200, validating SVG, `x-gaia-badge-state: validating`, `x-gaia-badge-repo-claimed: evil/repo` |
| 4 | `GET /badges/unknown-handle/handle.svg?repo=any/thing` | 200, validating SVG (handle not in registry) |
| 5 | `GET /badges/powered-by-gaia.svg` | 200, real SVG (1 segment — static, never the worker) |
| 8 | `GET /badges/samples/rank-1.svg?repo=evil/repo` | 200, real SVG (static; samples never validated) |
| 10 | `GET /badges/H/F-seal.svg?repo=R` | 200, real seal-only SVG, `valid` |
| 11 | `GET /badges/H/F-seal.svg?repo=evil/repo` | 200, validating SVG |
| 12 | `GET /` and other non-`/badges/` paths | 200, static — **no** `x-gaia-badge-state` header (worker not invoked) |
| 13 | `GET /badges/registry.json` | 200, static JSON |
| 14 | `GET /badges/_assets/H/F.svg` | 200, real SVG (internal source, served static; not validated) |

Byte checks worth running:
- case 2 served bytes `md5sum` == `docs/badges/_assets/H/F.svg`
- case 3 served bytes `md5sum` == `docs/badges/not-found.svg`

## Per-repo correctness (cache sanity)

Because the Worker generates these responses (they are not static assets),
Cloudflare does not edge-cache them and each `?repo=` is evaluated fresh.
Confirm in production that two different repos on the **same** badge path return
**different** images:

```bash
H=https://gaia-skill-tree.marco-tngsn.workers.dev
curl -s "$H/badges/mbtiongson1/handle.svg?repo=gaia-research/gaia-skill-tree" | md5sum  # real
curl -s "$H/badges/mbtiongson1/handle.svg?repo=evil/repo"                  | md5sum  # not-found
# the two md5s MUST differ
```

## Structured log lines

Every badge decision emits one JSON line via `console.log`. In `wrangler dev`
they print to stdout; in production use `wrangler tail` or **Cloudflare →
Workers & Pages → gaia-skill-tree → Logs**.

```json
{"evt":"badge_request","handle":"...","file":"...","repo_claimed":"...|null","state":"valid|validating|passthrough_no_repo|passthrough_static"}
```

```bash
# Top spoof attempts (claimed-but-wrong repos)
wrangler tail | jq -r 'select(.message|fromjson|.state=="validating")|.message|fromjson|.repo_claimed' | sort | uniq -c | sort -rn | head
# Most-embedded contributors (valid hits)
wrangler tail | jq -r 'select(.message|fromjson|.state=="valid")|.message|fromjson|.handle' | sort | uniq -c | sort -rn | head
```

## Production smoke after deploy

Re-run cases #2 / #3 against the Worker URL
(`https://gaia-skill-tree.<account>.workers.dev`). If case #3 serves the real
SVG, the Worker isn't handling the route — confirm `docs/badges/<handle>/` has
no static SVGs (they belong under `docs/badges/_assets/<handle>/`).
