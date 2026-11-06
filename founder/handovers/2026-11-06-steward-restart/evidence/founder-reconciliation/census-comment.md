## Canonical live census verified — counts reconciled, no closure authority inferred

Canonical REST collector exited **0**, fetched at **2026-11-04T20:15:21Z**, with issues and pulls completeness independently marked `complete: true` (six fetched pages / three confirmation pages for each cohort).

| Measured cohort | Count |
|---|---:|
| Open REST issue items, **including pull requests** | **223** |
| Actual open issues, excluding PRs | **218** |
| Open pull requests | **5** |
| GitHub Actions-authored open issues | **83** |
| `upstream:child` open issues | **72** |
| GitHub Actions-authored children | **72** |

Thus the founder hygiene receipt's **218 / 83 / 72** is corroborated by the canonical collector at this snapshot. **223 was an item count, not 223 actual issues**; the five PRs are #2290, #2289, #2287, #2281 and #2235. Repository `open_issues_count` and REST `/issues` count issues and PRs together; do not compare those to an issue-only listing. This does not yet prove the historical watcher's specific failure mechanism; the isolated #2278 lane is investigating it and preserving fail-closed completeness checks.

C1 #1833, C2 #2002 and C3 #1835 remain open with `upstream:needs-info`; their corrected holds are preserved. #2126/#2127 and P1 #2278 remain open. No metadata writes were made by this census.

Canonical census SHA-256: `ce11107af1030b42ac74887d89fb61ce785c614fb8ff5cb20747a7075e274d24`. Full exact snapshots, completeness receipt and cohort derivation are retained under `.gaia/steward/campaigns/2026-11-05/founder-reconciliation/`.

**Routine 18 read-only dry-run is now running against this separate census path**, without `--apply-closures`, without overwriting active campaign inputs or advancing its lease. Individual closure eligibility, child/L4 preservation and founder decision consumption are not yet claimed verified. `writesEnabled=false` and open closure-authority decision remain unchanged.
