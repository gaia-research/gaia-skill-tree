# RUN: c1-graphify-vs-graft

Outcome: **contradicted** by the pre-registered rule (tie: the two tools returned identical caller sets). Untrusted experiment record; admission not attempted.

## Pre-registration (committed before the request and the scored run)
- `lead.json`: challenger Graphify 0.8.13 (PyPI `graphifyy`, installed at that version, no substitution) vs incumbent `trailhq/graft` (graft CLI 0.25.0; 0.28.0 available, not applied).
- `protocol.json` (frontier-protocol-v1) holds the exact decision rule: SUPPORTED iff Graphify recall >= Graft recall + 0.2 on >=3 of 5 targets AND Graphify micro precision >= Graft micro precision - 0.05; CONTRADICTED iff Graft recall >= Graphify recall on all 5 targets AND Graft micro precision >= Graphify micro precision; else INCONCLUSIVE. Caller identity = (path relative to src/gaia_cli, bare enclosing function name, `<module>` for module level).
- `fixture/ground-truth.json`: 5 targets chosen mechanically (rule in the fixture: sha256(name+revision) ordering over unique-named public functions with 3-15 callers across >=2 files, stdlib-name collisions excluded): spec_by_id, computeTrustMagnitude, suiteComponentIds, rankWord, embeddings_path; 27 ground-truth callers from Python `ast`, each call site reviewed by reading the line. Pinned revision d237c0839c9c9197fc861ecec839ed323a9748a4.
- `runner/run-c1.py` sha256 96df20b503314043d5634dea3d9ed8c9d8c7c68a8d9410c447e30eaa56a67e2a (recorded in the protocol text). Its parsers were exercised beforehand only on three non-target functions (formatTime, load_lane, rankLabel) in a scratch dir; the decision logic was not changed after any scored output.
- `gaia dev frontier match`: Graphify is already registered as `safishamsi/graphify` (knowledge-graph-build), so this is a cross-bucket comparison; declared target ranked 1 at 0.1215. `dedupe`: not a duplicate (2 prior ledger leads).

## Run
`python3 build_verification_request.py` -> `request.json` (requestId `sha256:19a1c7ab29fd5e86a0e8c1aab7d446e16b9191f02c903eb923fa031eda507be1`); then the fixed runner extracted src/gaia_cli (excluding data/) from the pinned commit via `git archive` into a temp dir, ran `graphify update` (graph.json `calls` edges) and `graft build --only-dir tree --no-gitignore --no-ignore` + `graft callers <name>` per target on separate copies of identical bytes, scored, and wrote `artifacts/native.json` (Graphify), `artifacts/graft.target.json` (Graft), `artifacts/scoring.json`. Receipt via `gaia_cli.frontier.build_experiment_receipt` + `validate_experiment_receipt` (no errors).

## Result
Recall per target (both tools identical): computeTrustMagnitude 8/11 = 0.727, embeddings_path 5/5, rankWord 3/4 = 0.75, spec_by_id 4/4, suiteComponentIds 2/3 = 0.667. Micro precision 22/22 = 1.0 for both. Recall wins for Graphify (>= +0.2): 0 of 5, so not supported. Graft >= Graphify on all 5 and precision equal: contradicted by the rule.

## Honest notes
- The result is a tie, not a Graft advantage. "Contradicted" here means no demonstrated Graphify advantage on these targets under the rule; it does not show Graft is better.
- Both tools missed the same callers (computeTrustMagnitude via shadowEvaluation.py evaluateShadow/_assessOne/evaluateShadowRegistry; the cardRenderer.py module-level comprehension; trustMagnitude.py _fusionAndSuiteOriginIds), which suggests a shared static-resolution limit (attribute-call or module-alias calls), not a tool-specific gap.
- Five targets, one repository, one Python package; graph tools were not given an LLM pass. Caller identity normalised to bare names, so same-named methods in one file would be conflated.
- Runner session also authored protocol and ground truth; not independent, not authenticated. A separate Meta verification session is expected to re-execute.
