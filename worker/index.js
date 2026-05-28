/**
 * Gaia site Worker — static assets + repo-bound badge validation.
 *
 * Deploy model: this project is a Cloudflare **Worker with Static Assets**
 * (`wrangler deploy`, `[assets] directory = "docs"`). A Cloudflare *Pages*
 * Function (the old `functions/badges/[handle]/[file].js`) is NOT deployed by
 * `wrangler deploy` — the `functions/` convention is Pages-only — and even
 * under `wrangler pages dev` a Function cannot intercept a request that
 * resolves to an existing static asset. Every badge is committed as a static
 * SVG at `docs/badges/<handle>/<file>.svg`, so static-asset serving always
 * won and the `?repo=` gate never ran.
 *
 * The fix: `[assets] run_worker_first = ["/badges/*"]` in wrangler.toml makes
 * THIS worker run *before* static-asset serving for `/badges/*`, so we can
 * inspect `?repo=` and decide what to serve. Everything outside `/badges/*`
 * is served straight from static assets (the worker isn't even invoked).
 *
 * Route handled: /badges/<handle>/<file>.svg
 *
 *   - No `?repo=`            → serve the real SVG (back-compat for READMEs that
 *                              haven't migrated to the validated form yet).
 *   - `?repo=` matches one   → serve the real SVG.
 *     of contributors[handle].repos in /badges/registry.json
 *   - `?repo=` doesn't match → serve /badges/not-found.svg (the "validating…"
 *     badge) at THIS url, HTTP 200, so GitHub's camo proxy caches a stable
 *     image. (A 404 would make camo render a broken-image placeholder.)
 *
 * Cache: 24h on both valid and invalid responses, matching GitHub camo's own
 * ~24h window. The edge cache key includes the query string, so each
 * (handle, file, repo) triple caches independently.
 *
 * Pass-through (never validated): /badges/powered-by-gaia.svg,
 * /badges/not-found.svg, /badges/samples/*, /badges/registry.json,
 * /badges/index.html, and anything that isn't a two-segment *.svg.
 */

const ONE_DAY = 60 * 60 * 24;
const CACHE_HEADERS = `public, max-age=${ONE_DAY}, s-maxage=${ONE_DAY}`;

// Matches /badges/<handle>/<file>.svg exactly (two segments, .svg file).
const BADGE_RE = /^\/badges\/([^/]+)\/([^/]+\.svg)$/;

// Files that are NEVER repo-gated even when nested under a handle directory.
const PASSTHROUGH_FILES = new Set([
  "powered-by-gaia.svg",
  "not-found.svg",
]);

// Pseudo-"handles" that are really directories under /badges/ (e.g.
// /badges/samples/rank-1.svg). Hitting one means pass through to the asset.
const PASSTHROUGH_HANDLES = new Set([
  "samples",
]);

/**
 * Structured log line — one JSON object per badge decision. Cloudflare Workers
 * Logs picks these up automatically. Tail with `wrangler tail` or query in the
 * dashboard → Workers & Pages → <project> → Logs.
 *
 * Schema (kept stable so jq queries don't break):
 *   evt           "badge_request"
 *   handle        the @handle in the URL
 *   file          the requested SVG filename
 *   repo_claimed  the ?repo= value, or null if absent
 *   state         "valid" | "validating" | "passthrough_no_repo" | "passthrough_static"
 */
function logEvent(handle, file, repo, state) {
  console.log(JSON.stringify({
    evt: "badge_request",
    handle,
    file,
    repo_claimed: repo || null,
    state,
  }));
}

export default {
  async fetch(request, env) {
    // run_worker_first only scopes to /badges/*, but guard anyway: anything
    // that isn't a GET or isn't a per-handle badge SVG is served as-is.
    if (request.method !== "GET") return env.ASSETS.fetch(request);

    const url = new URL(request.url);
    const match = url.pathname.match(BADGE_RE);
    if (!match) return env.ASSETS.fetch(request);

    const handle = match[1];
    const file = match[2];

    // Pass-through directories (samples/) and pass-through files
    // (powered-by-gaia.svg, not-found.svg) skip validation entirely.
    if (PASSTHROUGH_HANDLES.has(handle) || PASSTHROUGH_FILES.has(file)) {
      logEvent(handle, file, null, "passthrough_static");
      return env.ASSETS.fetch(request);
    }

    const repo = url.searchParams.get("repo");

    // Back-compat: badges in existing READMEs may not include `?repo=` yet.
    if (!repo) {
      logEvent(handle, file, null, "passthrough_no_repo");
      return passThrough(request, env);
    }

    // Look up the contributor's approved repos (cached in module scope).
    const approved = await getApprovedRepos(handle, env, url);

    if (approved && approved.includes(repo)) {
      logEvent(handle, file, repo, "valid");
      return passThrough(request, env);
    }

    // Repo doesn't match (or unknown handle) — serve the validating badge at
    // this URL so camo caches a stable image per (handle, file, repo) tuple.
    logEvent(handle, file, repo, "validating");
    const notFoundUrl = new URL("/badges/not-found.svg", url.origin);
    const notFoundResp = await env.ASSETS.fetch(new Request(notFoundUrl, request));
    if (!notFoundResp.ok) {
      // not-found.svg missing — better to render a real badge than a broken image.
      return passThrough(request, env);
    }
    const body = await notFoundResp.arrayBuffer();
    return new Response(body, {
      status: 200,
      headers: {
        "content-type": "image/svg+xml; charset=utf-8",
        "cache-control": CACHE_HEADERS,
        "x-gaia-badge-state": "validating",
        "x-gaia-badge-handle": handle,
        "x-gaia-badge-repo-claimed": repo,
      },
    });
  },
};

/**
 * Serve the originally-requested asset with a 24h cache header and a
 * `x-gaia-badge-state: valid` marker. `env.ASSETS.fetch` serves the static
 * file directly (it does not re-enter this worker), so there's no loop.
 */
async function passThrough(request, env) {
  const resp = await env.ASSETS.fetch(request);
  if (!resp.ok) return resp;
  const body = await resp.arrayBuffer();
  const headers = new Headers(resp.headers);
  headers.set("cache-control", CACHE_HEADERS);
  headers.set("x-gaia-badge-state", "valid");
  return new Response(body, {
    status: resp.status,
    statusText: resp.statusText,
    headers,
  });
}

// ── registry.json caching ────────────────────────────────────────────────────
// Cache the parsed contributor list in module scope. A worker instance is
// reused across requests on the same edge node, so this saves a fetch + JSON
// parse on the hot path. The 24h TTL matches the badge cache; a redeploy
// resets it (fresh bundle), so newly-registered repos go live within 24h.
let _cache = { at: 0, data: null };

async function getApprovedRepos(handle, env, url) {
  const now = Date.now();
  if (_cache.data && now - _cache.at < ONE_DAY * 1000) {
    return (_cache.data[handle] && _cache.data[handle].repos) || [];
  }
  try {
    const registryUrl = new URL("/badges/registry.json", url.origin);
    const r = await env.ASSETS.fetch(new Request(registryUrl, { cf: { cacheTtl: ONE_DAY } }));
    if (!r.ok) return [];
    const json = await r.json();
    _cache = { at: now, data: json.contributors || {} };
    return (_cache.data[handle] && _cache.data[handle].repos) || [];
  } catch {
    return [];
  }
}
