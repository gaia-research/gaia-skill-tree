# RUN: c4-ripgrep-vs-graft-callers

Outcome: **rejected at triage**. No experiment, no protocol, no request, no receipt.

- Lead: `lead.json` (challenger ripgrep 15.1.0 vs target `trailhq/graft` @ d237c0839c9c9197fc861ecec839ed323a9748a4). Source README captured at tag 15.1.0 (`sources/`).
- `gaia dev frontier match` (`artifacts/match.json`): declared target `trailhq/graft` ranked 1 with lexical score 0.0878; next generic `codebase-graph-retrieval` 0.067. Matching terms (graft, symbol, where, find) largely come from the lead's own comparator wording, and the absolute score is low. Not a strong-similarity signal.
- `gaia dev frontier dedupe` (`artifacts/dedupe.json`): not a duplicate; ledger had 0 prior leads at run time.
- Rationale: ripgrep is a general regex text search tool. It makes no symbol, call-graph or caller-resolution claim, so it is not a challenger to codebase-graph-retrieval. Pre-registered expectation (plan C4) was triage rejection; the match output is consistent with that and does not contradict it.
- Commands run: 2 gaia frontier (match, dedupe), 0 experiment commands.
