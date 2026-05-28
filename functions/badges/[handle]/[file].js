/**
 * Cloudflare Pages Function — repo-bound badge validation
 *
 * Route: /badges/<handle>/<file>.svg
 *
 * Behaviour:
 *   - No `?repo=` query     → serve the asset as-is (back-compat for READMEs
 *                             that haven't migrated to the validated form yet).
 *   - `?repo=` matches one  → serve the asset as-is.
 *     of contributors[handle].repos in registry.json.
 *   - `?repo=` doesn't match → serve docs/badges/not-found.svg (the
 *     "validating…" badge) as the same path so GitHub's camo proxy caches
 *     a stable image at this URL. HTTP 200 (not 404) — a 404 would make camo
 *     fall back to a broken-image placeholder, defeating the visual signal.
 *
 * Cache strategy:
 *   - 24h TTL on both valid and invalid responses. GitHub's camo proxy caches
 *     for ~24h regardless, so we match that — no point shortening it. When a
 *     contributor registers a new repo the badge will go live within 24h via
 *     normal cache expiry; users can hard-refresh their own README on
 *     github.com to see it sooner.
 *   - Edge cache uses the request URL (handle + file + repo) as key, so each
 *     (handle, file, repo) triple is cached independently.
 *
 * Pass-through paths (never validated):
 *   - /badges/powered-by-gaia.svg
 *   - /badges/not-found.svg
 *   - /badges/samples/*
 *   - /badges/registry.json
 */

const ONE_DAY = 60 * 60 * 24;
const CACHE_HEADERS_VALID = `public, max-age=${ONE_DAY}, s-maxage=${ONE_DAY}`;
const CACHE_HEADERS_INVALID = `public, max-age=${ONE_DAY}, s-maxage=${ONE_DAY}`;

// Files that are NEVER repo-gated. Any other *.svg under /badges/<handle>/
// goes through the validator.
const PASSTHROUGH_FILES = new Set([
  "powered-by-gaia.svg",
  "not-found.svg",
]);

// Pseudo-"handles" that are actually directory names sitting under /badges/.
// Hitting one of these means the routed path is e.g. /badges/samples/rank-1.svg
// and we should pass through to the static asset.
const PASSTHROUGH_HANDLES = new Set([
  "samples",
]);

/**
 * Structured log line — one JSON object per badge decision. Cloudflare Workers
 * Logs picks these up automatically (no binding required, free up to ~5M
 * events/day). Tail with `wrangler pages deployment tail` or query in the
 * Cloudflare dashboard → Workers & Pages → <project> → Logs.
 *
 * Schema (kept stable so jq queries don't break):
 *   evt           "badge_request"
 *   handle        the @handle in the URL
 *   file          the requested SVG filename
 *   repo_claimed  the ?repo= value, or null if absent
 *   state         "valid" | "validating" | "passthrough_no_repo" | "passthrough_static"
 *
 * Path B (Workers Analytics Engine for queryable time-series) is tracked in
 * a separate enhancement issue — wire it here when that lands.
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

export async function onRequestGet({ request, env, params }) {
  const url = new URL(request.url);
  const handle = params.handle;
  const file = params.file;

  // Pass-through directories (samples/) and pass-through files
  // (powered-by-gaia.svg, not-found.svg) skip validation entirely.
  if (PASSTHROUGH_HANDLES.has(handle) || PASSTHROUGH_FILES.has(file)) {
    logEvent(handle, file, null, "passthrough_static");
    return env.ASSETS.fetch(request);
  }

  const repo = url.searchParams.get("repo");

  // Back-compat: badges in existing READMEs may not include `?repo=` yet.
  // Serve the real SVG; the page UI hands out the validated form going
  // forward, so this branch shrinks naturally over time.
  if (!repo) {
    logEvent(handle, file, null, "passthrough_no_repo");
    return passThrough(request, env);
  }

  // Look up the contributor's approved repos. Cached at the edge so we don't
  // re-fetch registry.json for every badge hit.
  const approved = await getApprovedRepos(handle, env, request);

  if (approved && approved.includes(repo)) {
    logEvent(handle, file, repo, "valid");
    return passThrough(request, env);
  }

  // Repo doesn't match (or unknown handle) — serve the validating badge.
  // Fetch the raw SVG bytes from the static assets and return them at THIS
  // URL so camo caches a stable image per (handle, file, repo) tuple.
  logEvent(handle, file, repo, "validating");
  const notFoundUrl = new URL("/badges/not-found.svg", url.origin);
  const notFoundResp = await env.ASSETS.fetch(new Request(notFoundUrl, request));
  if (!notFoundResp.ok) {
    // If for some reason not-found.svg is missing, fall through to the real
    // asset — better to render a real badge than a broken image.
    return passThrough(request, env);
  }

  const body = await notFoundResp.arrayBuffer();
  return new Response(body, {
    status: 200,
    headers: {
      "content-type": "image/svg+xml; charset=utf-8",
      "cache-control": CACHE_HEADERS_INVALID,
      "x-gaia-badge-state": "validating",
      "x-gaia-badge-handle": handle,
      "x-gaia-badge-repo-claimed": repo,
    },
  });
}

/**
 * Serve the originally-requested asset with a 24h cache header. We re-issue
 * the response so we own the cache-control rather than inheriting whatever
 * the static asset server set.
 */
async function passThrough(request, env) {
  const resp = await env.ASSETS.fetch(request);
  if (!resp.ok) return resp;
  const body = await resp.arrayBuffer();
  const headers = new Headers(resp.headers);
  headers.set("cache-control", CACHE_HEADERS_VALID);
  headers.set("x-gaia-badge-state", "valid");
  return new Response(body, {
    status: resp.status,
    statusText: resp.statusText,
    headers,
  });
}

// ── registry.json caching ────────────────────────────────────────────────────
// Cache the parsed contributor list in module scope. A Pages Function instance
// is reused across requests on the same edge node, so this saves a fetch +
// JSON parse on the hot path. The 24h TTL matches the badge cache — when a
// new contributor is added we accept up to 24h of staleness in exchange for
// the speed.

let _cache = { at: 0, data: null };

async function getApprovedRepos(handle, env, request) {
  const now = Date.now();
  if (_cache.data && now - _cache.at < ONE_DAY * 1000) {
    return (_cache.data[handle] && _cache.data[handle].repos) || [];
  }
  try {
    const registryUrl = new URL("/badges/registry.json", new URL(request.url).origin);
    const r = await env.ASSETS.fetch(new Request(registryUrl, { cf: { cacheTtl: ONE_DAY } }));
    if (!r.ok) return [];
    const json = await r.json();
    _cache = { at: now, data: json.contributors || {} };
    return (_cache.data[handle] && _cache.data[handle].repos) || [];
  } catch {
    return [];
  }
}
