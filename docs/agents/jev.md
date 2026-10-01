# Budgeted Jev advisory lane

Implementation scope for the Jev integration:

- Inventory existing usage before adding infrastructure.
- Prioritize generic mapping and curation, upstream-change review, and issue routing.
- Keep deterministic checks free; use Jev only for bounded semantic judgments.
- Treat the monthly $5 allowance as a ceiling, with conservative request limits,
  caching, and explicit opt-in for CI.
- Return an actionable Luna fallback on uncertainty, unavailable credentials,
  exhausted limits, or service failures. Never make paid calls just to test setup.
- Preserve all curator, evidence-verification, registry-mutation, and merge gates.

This document will include the implemented command contract and GitHub secret setup
when the advisory lane lands. No registry data changes are part of this work.
