# Website plan (EPIC #2189 outcome 5)

Opus planner, read-only at `43797a441`, 2026-10-28.

## Gaps beyond the brief
- `docs/api/v1/health.json` 8.26.10 vs pyproject 8.28.1 (`_STRIP_TOP` hides it from --check).
- 65 `docs/u/<handle>/index.html` load `?v=8.26.10` (not in `build_html_cache_busting()`).
- `trust-lifecycle.js` loaded only by `index.html` + `named/index.html`; other skill-explorer pages render empty `#se-tm`.
- III messaging in five places: `docs/js/site-nav.js:54-60` era stamp, `docs/index.html:463` and `:564` banners (outside hero-post markers), `docs/heroes/index.html:62` pill, hero post → Sept-25 note.
- `leaderboard.json` lacks `generatedAt` read by `leaderboard.js:543`.
- Denominators: leaderboard/ledger 268 rows vs `skills/index.json` totalSkills 229 (1★ redaction) — must be explained + tested.
- Report skill registered as `gaia-post` (`.claude/skills/meta-post/SKILL.md`, `scripts/add_post.py`).

## Surfaces (IV state now)
Homepage hero/news/era (none) · named profiles (none) · Skill Explorer `#se-tm` (partial, no provider) · generic nodes (none) · leaderboard 4 sections + filters + embed (none) · historical rank/ledger (partial) · Origin standings/heroes/wreath (none) · contested badges (none) · challenge detail/history (partial) · evidence provenance (partial) · public API (none) · Meta reports (none) · version consistency (broken).

## Data contract
One artifact: `docs/graph/challenges/index.json` mirrored to `docs/api/v1/challenges/index.json` (contract `gaia-challenge-projection/v1`), `sourceStatus: unavailable | verified-empty | verified`; `unavailable` ⇒ empty collections and UI renders nothing; fail-closed whole-file. Consequence only `current-baseline | approved-decision`; proposals only as `pendingProposal` pointer into the adjudication ledger — no proposed numeric fields anywhere public. Synthetic fixtures only under `tests/fixtures/` with a no-synthetic guard over `docs/`.

Reconciliation with the challenger plan: admission-held reviews project separately as `gaia-challenge-review/v1` (never "contested"); `gaia-challenge-projection/v1` stays `unavailable` until issuer + admission exist.

## Parity tests
`tests/test_public_projection_parity.py` (leaderboard↔ledger, skills index pages, named index↔API↔ledger, prestige, evidence, Origin uniqueness, versions/`?v=`, Meta links) · `tests/test_challenge_projection.py` · node: contested rendering keeps bar widths byte-identical; page co-load test.

## Slices
W0 `dev/yggiv-web-consistency` (cache-bust, health, generatedAt, parity) · W1 `dev/yggiv-challenge-projection` · W2 `design/yggiv-lifecycle-everywhere` · W3 `design/yggiv-leaderboard-contested` (W1) · W4 `design/yggiv-ledger-history` (W1) · W5 `design/yggiv-challenge-detail` (W1) · W6 `design/yggiv-origin-surfaces` (W1) · W6b badge SVG contested (founder decision, held) · W7 `design/yggiv-evidence-provenance` · W8 `design/yggiv-era-messaging` (needs truthful IV report + founder) · W9 `verify/yggiv-web-acceptance` (screenshot matrix, one preview at a time).
Every visual PR: 1440/390/320 native screenshots, no 320 overflow, focus ring, Escape closes toggletips, nav clearance, reduced motion, tokens only, `build_docs.py --check` green; founder visual approval final.
