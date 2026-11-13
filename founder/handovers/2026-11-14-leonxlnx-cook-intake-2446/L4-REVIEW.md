# L4 review card — leonxlnx/cook (tracking #2446)

**Gate:** Phase 2 human L4 topology. Nothing has been ratified, submitted or mutated. No intake issue/batch exists.
**Candidate:** `leonxlnx/cook` — Leonxlnx/cook @ `b23cac6fd9439dfddcab61b14808e7bf72549b46`, SKILL.md sha256 `110a9fe3…9585`, MIT, name+description frontmatter valid. Attribution: `upstream_author: leonxlnx`, type `attributed`, `named.contributor: leonxlnx`.
**What it is:** reference-driven visual build loop — intake once, numeric bar per dimension, render stills, side-by-side vs references, zero-context critics, fixes, persistent `cook/` state, user approval before final render.

## Machine signal (recall hint only, not authority)
Prefill top-3: video-composition 0.478, video-preview 0.465, video-rendering 0.454 — all **weak**, 0 strong, and thematically off (they match "film/video" wording, not the capability). No exact duplicate (`exactDedupe.matched=false`). Flag: nearest named neighbor `garrytan/design-shotgun` 0.466. Advisory principles receipt: every principle `unknown` by design (`--jev off`). Mechanical precedence for weak-only = DEFER for adjudication, i.e. this decision is yours.

## Options
| | Option | Topology | For | Against |
|---|---|---|---|---|
| **A — recommended** | NEW_GENERIC `reference-guided-visual-iteration` | fusion; prereqs `code-generation`, `vision-qa`, `evaluate-output` (all exist) | Falsifiable behaviors absent from neighbors: (1) references as minimum bar, (2) numeric per-dimension bar with calibration offset, (3) paired reference/render comparison scored by independent zero-context critics, (4) no-stop-on-first-working loop with approval gate. Spans 3D/video/games/UI, so wider than `design-generation`. | Adds a node; material-distinction vs `design-generation` must satisfy you. Novelty is judged by me, not by retrieval. |
| B | MAP `design-generation` (fusion: code-generation, ui-audit, vision-qa) | existing | Same contributor already maps `taste-skill` there; no new node. | `design-generation` is "from design intent"; cook is reference-matching and covers non-UI work; loop/critic behavior would be absorbed unlabeled. |
| C | MAP `vision-qa` (basic) | existing | `leonxlnx/image-to-code-skill` maps there. | vision-qa = answering questions about an image; poor fit for a build loop. Not recommended. |
| D | Reject / defer | — | If you judge it a workflow wrapper over existing generics. | Loses a distinct, MIT, attributed skill. |

Rejected neighbors (compared, not matched): `automated-testing` (pass-rate on tests), `recursive-self-improvement` (self-refines prompts/tools), `self-critique`/`multi-agent-debate` (text reasoning), `prototype` (throwaway), `unlazy`/`task-depth-enforcement` (cook only *optionally* pairs with it; not a prerequisite).

## If A is approved — exact payload
- generic id `reference-guided-visual-iteration`; name "Reference-Guided Visual Iteration"; type fusion; prerequisites `code-generation,vision-qa,evaluate-output`
- description: "Builds code-rendered visual work (3D scenes, video, games, UI) by repeatedly rendering stills, comparing them side by side with supplied reference images or video against a numeric per-dimension quality bar, scoring with independent fresh-context critics, and fixing the weakest dimension until the bar is met."
- named: contributor `leonxlnx`, skill-name `cook`, skill-file-url: packet default is the commit-pinned blob; installer-friendly alternative `https://github.com/Leonxlnx/cook/blob/main/SKILL.md` (your call — pin stays recorded in evidence either way).
- Origin: automatic by merit — do not set.

## Evidence honesty (carry to Phase 4)
Verified 2026-11-13 via API: 386★, 30 forks, created/pushed 2026-10-31, 1 contributor, 0 releases, 0 open issues. Fork burst on 2026-11-13 has unknown cause — **not adoption evidence**. Performance claims (Athenaion run etc.) are author-reported only. Upstream broken ref: `references/target-and-bar.md` cites `color_check.py`, which is absent from the repo (only `scripts/side-by-side.mjs` ships). Literature leads in the scout packet are search-snippet level, unverified; Design2Code snippet suggests self-revision helps little for some models — counterevidence. No TM/stars/rank proposed.

## Decision wanted (verbatim reply is enough)
`A` / `B` / `C` / `D` (+ skill-file-url choice). Then a human must supply the trusted authorization envelope for `gaia dev ratify` — an agent cannot mint it.
