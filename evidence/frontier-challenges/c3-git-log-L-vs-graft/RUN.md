# RUN: c3-git-log-L-vs-graft

Outcome: **inconclusive** (receipt `receipts/experiment-receipt.json`, schema frontier-experiment-receipt-v1.1). Untrusted experiment record; admission not attempted.

## Pre-registration
Lead (`lead.json`), captured Git 2.56.0 `git-log.adoc` source, and the protocol `examples/frontier/protocols/git-log-L-vs-graft-v1.json` (byte-identical to dev, bound by digest) were fixed and committed (`review(frontier): C3 pre-registration`) before the request was built or anything was run. Decision rule as pre-registered in that protocol: git log -L and Graft are complementary, so superiority is inconclusive; documented/executed version mismatch permits only `inconclusive` or `execution_failed`. Expected outcome per plan: negative/at most inconclusive.

## What ran
- `gaia dev frontier match` / `dedupe`: outputs in `artifacts/`. Not a duplicate (ledger had C4 only). Registry match: generic `codebase-graph-retrieval` 0.1713, declared target `trailhq/graft` rank 2 at 0.0844.
- Request: `python3 examples/frontier/build_verification_request.py --lead ... --request-out request.json` (requestId `sha256:50a864e709d674403353090556d9342ce9e63a040cd782ebde7c228aae999929`).
- Native: `python3 examples/frontier/run_git_log_L_fixture.py --output artifacts/native.json --request request.json` on the host `/usr/bin/git`: **Apple Git 2.50.1**, documented tag **2.56.0**. No isolated 2.56.0 build was made (the version-binding rule permits recording the mismatch as inconclusive).
- Target: graft 0.25.0 (latest 0.28.0 not applied) built out-of-tree (`graft --dir <scratch> build --only-dir examples/frontier/fixtures --no-gitignore --no-ignore .`), then `ask "locate function score" --source`, `callers score`, `callers caller --direction out`, `ask "historical line evolution of score across commits"`, `grep "return value"`; combined output `artifacts/graft.target-output.txt`. Tracked `.gitignore` unchanged after build.
- Receipt: `gaia_cli.frontier.build_experiment_receipt` (result inconclusive); `validate_experiment_receipt` returned no errors with `artifact_root=evidence/frontier-challenges/c3-git-log-L-vs-graft/artifacts`.

## Observations
Git log -L traced `score` across both fixture commits. Graft located `score` (L1-L3) and `caller`, resolved `caller -> score`, and returned only the current body; the history question returned current-code nodes and no historical evolution. Complementary scope, not like-for-like.

## Limitations
One 7-line fixture. Run by the same agent lane that wrote the lead; not independent, not authenticated. Host Git version differs from documented 2.56.0 (stated as a receipt limitation). Commands run: 2 gaia frontier, 1 request builder, 1 runner (several git subcommands inside), 6 graft, 1 receipt build.
