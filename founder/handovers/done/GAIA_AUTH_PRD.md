# PRD: GitHub Sign-In for GAIA (#155)

**Status:** Draft v1 for Marco's review — co-author via doc-coauthoring.
**Principles (Marco, 2026-06-10):** simple, clean auth that verifies you are the GitHub repo owner; read-only access; CLI depends on it (model after `gh auth login`); the site stays static and only ever shows canon; no hosting of local trees.

---

## 1. The tradeoffs, in plain terms

There are four ways to do "sign in with GitHub". What matters for GAIA: does it need a server, does it need a secret, and does it fit a CLI.

| Option | How it feels | Needs a secret? | Needs a server? | Verdict for GAIA |
|---|---|---|---|---|
| **Device flow** (what `gh auth login` does) | CLI prints a code like `A1B2-C3D4`, you open github.com/login/device, type it, done | No — client_id only | No | **MVP. This is the one.** |
| **Web flow + serverless exchange** | Click "Login", bounce to GitHub, bounce back | Yes — GitHub still requires the client secret at token exchange even with PKCE (confirmed against GitHub's July 2025 changelog; they don't distinguish public clients) | Yes — one tiny function (Cloudflare Worker/Pages Function) holding the secret; the site stays static otherwise | Shelved — leaning CLI-forever |
| **GitHub App** | Like OAuth but with installation + fine-grained repo permissions | Yes | Yes | Overkill — built for apps acting ON repos; we only need identity + read |
| **Paste a PAT** | User creates a token by hand and pastes it | No | No | Rejected — worst UX, trains bad security habits, no identity guarantee about how the token was scoped |

Key consequence of the static-site rule: **browser login cannot be fully static on GitHub today.** Either we accept one serverless function as the single non-static exception (it holds the secret, exchanges the code, and immediately hands the user a session — it stores nothing), or the site simply has no login and all authentication lives in the CLI.

## 2. Recommended architecture

### MVP — CLI device flow (`gaia login`)

1. `gaia login` → POST to GitHub's device endpoint with our OAuth app's client_id → user gets a short code + URL.
2. User authorizes in any browser; CLI polls until granted.
3. Scope: **none beyond identity** (an empty-scope token reads public data and proves who you are — sufficient for ownership checks against public repos). Read-only by construction.
4. Verification: token → `GET /user` → handle; ownership of a claimed repo verified via the repos API (owner/affiliation match). The verified handle becomes the canonical `gaiaUser` — you can only claim your own tree, rankings, badges.
5. Storage: **persistent** — OS keychain via keyring, chmod-600 file fallback (gh's pattern), so login survives across sessions. `gaia logout` deletes + revokes. Env vars still override per session for CI.
6. `gaia whoami` reports the verified handle alongside the existing Verifier status.
7. **Remote-repo read access**: login lets the user select remote repos to read; `.gaia` remains local and stores a worktree-style path to its repo. Offline mode remains first-class — login only adds capability, never gates existing local workflows.

### Phase 2 (parked in its own milestone until MVP is "working and stable" — Marco)

- **Web login: leaning CLI-forever** — the minimal-Worker option is documented for the record but shelved; revisit only if something forces a browser flow.
- **#494 signed badges** — design against CLI-issued proof, not a web session.
- **OAuth-bound share pages** (#128 option c) — explicitly parked per Marco.

## 3. The static page — what Login means there (design scope)

The page hosts **canon only**, forever. Within that:

- **MVP-adjacent (no auth needed!):** "check my rankings" — enter/auto-fill a GitHub handle, page highlights that contributor's named skills, ranks, tenure within the canon view. Reading canon is public; auth only matters when claiming/writing. This can ship before any web login exists.
- **Client-side previews:** paste or upload a JSON (primarily `gaia share` bundles) → rendered tree preview, entirely in-browser, nothing stored, nothing hosted. The bundle's pre-resolved metadata (PR #657) was designed exactly so this needs no registry calls.
- **Deferred, not MVP:** `gaia install` configurator/generator (compose a bundle/command interactively).
- **Never:** hosting local gaia trees, server-side user state, anything non-canon.

## 4. Open questions for Marco

- [x] **Offline process: REMAINS** (Marco, 2026-06-10) — offline is a first-class mode, not a fallback. Login adds capability on top: a logged-in user can **select remote repos for read access**. `.gaia` stays local and carries a **path to the repo, worktree-style** — the local folder points at its remote the way a git worktree points at its tree.
- [x] Web login: **leaning CLI-forever** (Marco, 2026-06-10). The serverless Worker idea stays on the shelf unless something forces a browser flow; #494 badge design should assume CLI-issued proof, not a web session.
- [x] Token storage: **persistent** (Marco, 2026-06-10 — revised same day from "none"). Users shouldn't re-login for a while: store in the OS keychain via keyring, falling back to a chmod-600 hosts-style file (gh's exact pattern). `gaia logout` deletes locally and revokes via the API. Decide at implementation: plain non-expiring OAuth token (simplest) vs opting the app into expiring tokens + refresh (safer, more moving parts) — default to non-expiring unless Marco says otherwise.

## 5. Rollout

1. **Marco:** register the GitHub OAuth app (Settings → Developer settings → OAuth Apps). For device-flow-only MVP: no callback URL matters (use a placeholder), enable Device Flow, note the client_id. The client_secret is generated but **unused in MVP — store it nowhere**, it only becomes relevant if Phase 2 web login happens.
2. **Coding agent** (`cli/` branch): `gaia login` / `gaia logout` / `whoami` extension (keyring-persistent token) + ownership check helper + remote-repo selection with worktree-style `.gaia` path. `Refs #155`.
3. **Design lane** (`design/` branch, independent): rankings-check + JSON preview on the static page — needs zero auth infrastructure.
4. #155 closes when CLI login verifies ownership end-to-end; Phase 2 items move to their own milestone.

## 6. CLI-issued proof — badges without a server (feeds #494 design)

Context: honesty-mode switch is currently ON (signed badges not tracked); the original Cloudflare Worker plan is dead because the site is not hosted in the wrangler deployment. Two serverless mechanisms, layerable:

**Layer 1 — canon-derived badges (MVP, zero crypto).** Badge JSONs are generated at build time by CI from canon (`skill-trees/<user>/` + registry) into `docs/badges/<user>/<skill>.json`, served by the static site, rendered via shields.io endpoint URLs. Impersonation-proof because canon is maintainer-gated: the only way to change your badge is a merged PR. No server, no keys, page stays canon-only. Honesty mode maps cleanly: badges carry `verified: canon` vs `honesty` provenance.

**Layer 2 — signature attestations (for off-canon claims: local trees, share bundles).** `gaia badge sign` uses the user's local SSH/GPG key (the same key they sign commits with) to sign a small attestation JSON (handle, skill, rank, timestamp, tree hash). Any verifier — CI, another user's CLI, a future page — fetches the signer's public keys from GitHub's public API (`/users/<u>/ssh_signing_keys`, `/users/<u>/gpg_keys`) and verifies. GitHub acts as the keyserver; no GAIA infrastructure. The device-flow login is what binds `gaiaUser` to the GitHub handle whose keys count.

Worker postscript: if a dynamic endpoint is ever truly needed, it doesn't have to be same-origin — a `badges.<domain>` DNS route or workers.dev URL works regardless of where the site is hosted. Parked; the layers above don't need it.

### docs/badges page — design updates (Layer 1 + 2 surfaced)

The existing page (`docs/badges/index.html` + `generateBadges.py` assets) keeps its role as the copy-paste configurator, with these changes:

1. **Snippets emit plain static URLs** — `/badges/_assets/<handle>/<file>.svg` directly. No `?repo=` query string; the "validating…" fallback SVG retires with the Worker.
2. **Provenance ladder legend** on the page: `canon` (listed in registry — true by construction) → `verified` (signed attestation, CI-checked) → `honesty` (unsigned claim). Badge variants may carry a small provenance mark; design tokens via `formatting.py`/tokens pipeline, vocabulary via CONTEXT.md.
3. **"Sign it" block**: shows the two commands (`gaia login`, `gaia badge sign`) and what the attestation file is, plus the `gaia badge verify <repo>` one-liner for consumers.
4. **registry.json survives** as the approved-repos source (schema v2 `fileSeal` variant included), consumed by CI/CLI verification instead of the Worker.
5. Samples gallery unchanged.

## Sources

- [GitHub Changelog — PKCE support for OAuth and GitHub App authentication (July 2025)](https://github.blog/changelog/2025-07-14-pkce-support-for-oauth-and-github-app-authentication/) — PKCE supported, but client secret still required at exchange.
- [GitHub Docs — Authorizing OAuth apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps) — device flow for headless/CLI apps.
- [Community discussion #15752](https://github.com/orgs/community/discussions/15752) — no public/confidential client distinction; SPAs must include the secret.
