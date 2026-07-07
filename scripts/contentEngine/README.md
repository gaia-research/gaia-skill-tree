# Content Engine (Sprint D · W1)

The Content Engine turns Gaia's live trending API surface into a weekly
markdown report — published on Monday 08:00 UTC to a permanent, indexed,
tweetable URL.

## Files

| Path | Role |
|---|---|
| `generate_weekly_report.py` | Data layer — reads `docs/api/v1/trending/{7d,ascended,contested}.json`, assembles a canonical report dict, renders markdown + HTML. |
| `synthesizer.py` | L1/L2/L3 salvage harness. L1 (Opus) + L2 (Sonnet) are LLM-gated by `GAIA_CONTENT_ENGINE_LLM=1`; L3 is a pure-Python mechanical fallback that can never fail on valid data. |
| `templates/report.md.j2` | Canonical markdown body. Embedded in both the DRAFT output and the HTML render. |
| `templates/report.html.j2` | Thin HTML wrapper for `/reports/YYYY-WW/` — loads `tokens.css`, `mounts.js`, `site-nav.js`. No custom CSS. |
| `templates/archive.html.j2` | `/reports/index.html` landing page. |
| `templates/_partials/{header,trending,ascended,contested}.md.j2` | Per-section fragments. |

## Publish gate

`GAIA_CONTENT_ENGINE_PUBLISH`:

- unset / `0` → writes `docs/reports/DRAFT/YYYY-WW.md` (gitignored — never leaves the runner)
- `1` → writes:
  - `docs/api/v1/reports/YYYY-WW.json` (canonical)
  - `docs/reports/YYYY-WW/index.html` (public)
  - rebuilds `docs/api/v1/reports/index.json`

The gate is flipped by Marco in the `content-engine-live` GitHub Environment.
Default: OFF for the first 4 weeks (per `founder/handovers/SPRINT_D_EPIC_PLAN.md` §4).

## Invariants — frozen for Sprint F

- URL structure `/reports/YYYY-WW/` **FROZEN** (SEO, tweetable URL).
- Canonical JSON shape at `docs/api/v1/reports/YYYY-WW.json` **FROZEN** (SDK contract).
- ISO week format `%G-%V` (ISO year + week; disagrees with `%Y-%W` at year boundaries) **FROZEN**.

## Sprint F portability boundaries

- **Portable (survives Sprint F unchanged):**
  `scripts/contentEngine/**/*.py`, `templates/**/*.j2`, `tests/contentEngine/`,
  `.github/workflows/weekly-content-engine.yml`.
- **Rewrites (Sprint F Next.js replaces the render layer):**
  `docs/reports/**/*.html` — the Next.js `<Report>` page will consume the
  canonical JSON unchanged.

## Local usage

```bash
# Dry-run into a tempdir (never touches docs/):
python scripts/contentEngine/generate_weekly_report.py --dry-run /tmp/gaia-report

# Write a DRAFT into docs/reports/DRAFT/YYYY-WW.md (gitignored):
python scripts/contentEngine/generate_weekly_report.py --out-dir docs --publish 0

# Publish to docs/reports/YYYY-WW/ (only the cron does this):
python scripts/contentEngine/generate_weekly_report.py --out-dir docs --publish 1
```
