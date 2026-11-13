# ev-scout packet: Leonxlnx/cook (skill "cook")

Status: pre-curation research only. No grading, no Trust Magnitude, no star level. All leads are UNVERIFIED candidates.

## Target & pin

- Repo: https://github.com/Leonxlnx/cook
- Pinned commit (from task): b23cac6fd9439dfddcab61b14808e7bf72549b46
- Pin check: NOT verified. The API metadata below describes the default branch at retrieval time; I did not confirm that HEAD equals the pin. Verifier must run `gh api repos/Leonxlnx/cook/commits/b23cac6fd9439dfddcab61b14808e7bf72549b46`.
- Local upstream copy (untrusted, not executed): `/private/tmp/claude-501/-Users-marcotiongson-gaia-skill-tree/8cc04514-eae1-5520-96bf-0acb1b13d105/scratchpad/cook-src/` (SKILL.md, README.md, LICENSE, references/ x5, scripts/side-by-side.mjs, templates/ x2).
- Retrieval date: 2026-11-13T21:14:52Z (UTC, from `date -u` in the sandbox; the system date is 2026-11-14).

## Tools used / unavailable

- Used: `gh api` (read-only REST calls for repo, releases, contributors, commits header, issues, forks); local `grep`/`ls`/`wc` on the cook-src copy; WebSearch (standard mode) x2.
- Not used: WebFetch (not needed for the leads found; no leads were fetched and read in full, so every lead below is search-snippet level only).
- Unavailable / not attempted: Firecrawl and ev-discovery; no PDF was downloaded or read; no arXiv listing was checked for dates beyond what the search snippet showed.
- Did NOT run any gaia command, did not write to the repo, did not execute anything from cook-src.

## Source verification table (GitHub API, read-only)

| field | value | how obtained |
|---|---|---|
| full_name | Leonxlnx/cook | `gh api repos/Leonxlnx/cook` |
| license (SPDX) | MIT (LICENSE file also present locally) | repo metadata `.license.spdx_id`; local LICENSE |
| stargazers_count | 386 | repo metadata, 2026-11-13 |
| forks_count | 30 | repo metadata, 2026-11-13 |
| subscribers_count (watchers) | 2 | repo metadata |
| created_at | 2026-10-31T21:48:38Z | repo metadata |
| pushed_at | 2026-10-31T21:48:44Z | repo metadata |
| updated_at | 2026-11-13T20:55:59Z | repo metadata (updated_at moves on non-code activity; not a code change signal) |
| open_issues_count | 0 | repo metadata; `issues?state=open` returned an empty list |
| archived | false | repo metadata |
| default_branch | main | repo metadata |
| releases | 0 | `gh api repos/Leonxlnx/cook/releases` returned length 0 |
| contributors | 1 listed: Leonxlnx, 1 contribution | `gh api .../contributors` |
| commit count | unknown | the commits Link header was internally inconsistent (next=page 2, last=page 1) on per_page=1; not reliably obtained |
| description | "Give your agent a target, a bar and time, then let it cook. An agent skill for visual builds that have to match reference images or videos." | repo metadata |

Fork observations (from `repos/Leonxlnx/cook/forks?per_page=10`, first 10 of 30 only):
- Ten forks listed, created 2026-11-13 (between 10:03Z and 20:47Z UTC) under many different accounts.
- Eight of the ten show pushed_at = 2026-10-31T21:48:44Z, identical to upstream, which suggests no commits pushed beyond upstream at snapshot time. This does not prove the forks are unmodified (local-only changes are invisible).
- Two forks show later pushes: Mitternacht/cook (pushed 2026-11-13T15:45:56Z) and jpeek01/recook (pushed 2026-11-13T18:17:53Z). Their contents were NOT inspected.
- Interpretation: the burst of forks on one day is an observable fact. Its cause is unknown. Do not read it as adoption or endorsement. Possible explanations include a social share, a listing, or a template effect; unknown.

Independent review, mention, or adoption: NOT FOUND in this pass. I searched only the GitHub API endpoints above. I did not search social platforms, Hacker News, blogs, or skill directories. Treat as "unknown", not "none".

## Leads (generic, UNVERIFIED)

Only items for which a URL appeared in search results are listed. Dates are as shown in the snippet or URL id; "unknown" where not shown. Snippet-level only: none was opened.

| URL | title / publisher | date | possible Gaia evidence type | scope | what a verifier must confirm |
|---|---|---|---|---|---|
| https://arxiv.org/pdf/2403.03163 | Design2Code (benchmark for screenshot-to-code; the search snippet cites this id as the foundational benchmark) | arXiv id 2403 (March 2024) | arxiv / benchmark-source candidate | generic | Read the paper. Snippet claims self-revision prompting gave limited benefit for several MLLMs. Confirm the exact result table and conditions before using it. |
| https://arxiv.org/pdf/2602.18548 (also abs/2602.18548) | 1D-Bench, design-to-code benchmark with multi-round component edits and execution feedback (Taobao & Tmall group, per snippet) | arXiv id 2602 (Feb 2026, per snippet) | arxiv / benchmark-source candidate | generic | Snippet says iterative editing generally improves rendering success and often visual similarity. Confirm metrics, models, and whether results are reproducible. |
| https://arxiv.org/pdf/2602.05998 | VisRefiner (RL stage comparing render to target and editing code; Institute of Software, CAS, per snippet) | arXiv id 2602 (Feb 2026, per snippet) | arxiv | generic | Snippet claims gains in single-step quality and self-refinement. Check whether the self-refinement claim uses an independent judge or the same model. |
| https://icml.cc/virtual/2026/poster/66252 | UI2Code^N: UI-to-Code Generation as Interactive Visual Optimization (ICML 2026 poster page) | ICML 2026 (poster page; exact date unknown) | peer-review candidate (verify acceptance) | generic | Confirm acceptance status and venue on the ICML page. Snippet says a 9B open model with preference-based RL reports SOTA on drafting, polishing, editing benchmarks. Check whether it is an accepted paper or only a poster listing. |
| https://arxiv.org/pdf/2511.08195v2 | "Interactive UI-to-Code" paradigm paper (argues single-turn approaches under-use visual feedback; notes font, DPI and browser-default confounds) | arXiv id 2511 (Nov 2025, per id) | arxiv | generic | Confirm the claim about runtime factors making pixel fidelity unverifiable without real rendering. This is a useful caveat for cook's "measured vs eyeballed" split. |
| https://arxiv.org/pdf/2410.21819 | Self-Preference Bias in LLM-as-a-Judge (text-only LLM judges) | arXiv id 2410 (Oct 2024, per id) | arxiv | generic | Text-only. Confirms self-preference exists for LLM judges, including when the judge is not told the text is its own. Does NOT show this for VLM judges. |
| https://arxiv.org/abs/2508.20655v2 (also html/2508.20655v1) | Improving Alignment in LVLMs with Debiased Self-Judgment | arXiv id 2508 (Aug 2025, per id) | arxiv | generic | Related to LVLM self-judgment. Snippet says it targets self-rewarding training, not measuring VLM judge self-preference. Confirm before citing. |
| https://www.alphaxiv.org/abs/2604.24346.md | SycoPhantasy: sycophancy and hallucination in small open VLM evaluators (Bluffing Coefficient) | arXiv-style id 2604 (Apr 2026, per id) | arxiv | generic | Snippet claims a mismatch measure between VLM score and cited evidence. Directly relevant to critic reliability. Confirm the coefficient definition and sample. |

Searches that found no VLM-specific self-preference study: the second search returned mostly text-only LLM-judge papers (e.g. an April 2026 rubric-based paper reporting a 31.5% average reduction in self-preference bias for a structured multi-dimensional evaluation; URL https://arxiv.org/pdf/2604.06996.pdf, id-based date Apr 2026; scope generic, text-only, unverified). Suggested follow-up query: "vision language model evaluator self-preference".

## Counterevidence & competing approaches

- Counterevidence (on iteration): Design2Code snippet says self-revision gave limited benefit for several MLLMs (see lead 1). 1D-Bench and VisRefiner snippets report gains, so the evidence is mixed by snippet. Plateau or reward-hacking evidence for render-compare loops was NOT located in this pass.
- Counterevidence (on critics): text-only work shows self-preference and sycophancy-type bias in LLM judges (leads 6 and 8). The VLM case is weaker and less studied in what was found.
- Competing approaches (names only; not examined): visual regression testing tools (pixel and perceptual diff in CI), screenshot-diff agent loops, Self-Refine style generate-feedback-refine loops, and other UI-to-code agents. None was searched or verified in this pass. Treat as an open gap.
- Cook's own design choices that differ from the benchmark literature: it uses fresh zero-context critics (not the author model's own score) and a user calibration offset. Whether that reduces the bias above is UNVERIFIED.

## Safety observations (from files, quoted)

Source: local cook-src copy. All quotes are from those files. Line numbers are from grep.

- SKILL.md:10 "It is made for runs of 10 to 40 hours or more." Long unattended runs are the design target.
- SKILL.md:3 description: "especially runs of many hours or days while the user is away."
- SKILL.md:70 "Demos get a floor: at least 8h, and done after 2h means something is wrong. Big builds can take days. Small jobs get a hard cap." A minimum duration is imposed on stopping.
- SKILL.md:72 and references/loop-and-critics.md:96-101: usage pacing "about 20% of a 5h window per hour, about 99% per window, never 100%." The reference says usage is checked "if you can read usage (a status command, a usage tool, or numbers the user gave you)". Unknown whether the agent can read usage in practice.
- SKILL.md:81 "Split independent parts across parallel subagents." references/loop-and-critics.md:28: "The Athenaion run used 55 subagents, up to 12 in parallel." Subagent spawning is encouraged at scale; cost and rate-limit impact is not bounded in the files.
- references/loop-and-critics.md:36-39: at least two critics per round, three or more for big builds; fallback "a fresh session" or "score it yourself and mark it 'self-scored'."
- SKILL.md:96 and references/intake.md: the final render is gated on user approval: "Never start the final render, or any other long and costly export, before the user approves the stills in chat." Good gate. But the intake asks the user for limits, not a hard cap.
- references/intake.md:27 "May I download audio, push to a public repo or publish anything?" The default answer the intake proposes is "Download free licensed audio only and credit it. Prepare the repo locally, do not push or publish." Permissions are per-run in BRIEF.md (intake.md:63).
- references/ship.md:33 "Only if BRIEF.md allows pushing. Otherwise prepare everything locally and say it is ready." Push is conditional on BRIEF.md.
- references/rules.md:7 "Zero external assets by default". Reduces downloads, but references/target-and-bar.md:36-39 uses ffmpeg to extract frames from user videos (local, from user-supplied refs).
- Shell use: scripts/side-by-side.mjs uses `spawnSync('ffmpeg', ...)` (lines 11, 45-46, 73-74) with args built from CLI args, no shell string. Header comment line 9: "Needs ffmpeg on PATH." Also SKILL.md:77 instructs running `node <skill>/scripts/side-by-side.mjs` on user paths. The script itself makes no network call (grep for fetch/http returned nothing).
- references/ship.md:39 and SKILL.md:119: "Publish it only if the user wants to, and never with third-party references." and "Put API keys, tokens or private information in anything you publish." Both are prohibitions, not enforcement.
- Permission file scope: intake.md:67 says `cook/` is local working state and "is not published unless the user wants it to be."
- Not found in files: any explicit sandbox, network allowlist, or spend cap. Budget is by time and usage window only.
- Not found: an explicit instruction to install packages from npm or pip. references/target-and-bar.md:82 mentions `python color_check.py` but no install step was read; the script itself was not in the cook-src copy (only side-by-side.mjs is present), so the color_check reference points to a file that is absent from the copy. Note this as a broken reference.

## Benchmark-source candidates (candidates only, NOT verified results)

- 1D-Bench (arXiv 2602.18548): design-to-code, multi-round editing with execution feedback. Missing: exact metric definitions, model list, seeds or sample size, whether the rendering harness is released, and whether results are reproducible from the paper.
- Design2Code (arXiv 2403.03163): screenshot-to-code benchmark. Missing: which self-revision variant was measured, and whether the critic was the same model.
- UI2Code^N (ICML 2026 poster): UI drafting, polishing, editing benchmarks. Missing: benchmark names, scores, the 9B model ID, and whether the code and data are public.
- SycoPhantasy (id 2604.24346): VLM evaluator sycophancy. Missing: the evaluator set, the Bluffing Coefficient formula in full, and the sample.

No numeric scores are reported here. Any score must come from a verifier reading the source.

## Synthesis

- Architecture (what the files describe): a loop of intake, build, render, side-by-side comparison, zero-context critic scoring with median and calibration offset, prioritised fixes, and user approval before the final render. The structure is coherent and the bias controls (fresh critics, calibration against the user's estimate, measured vs eyeballed split) map onto documented concerns in the literature.
- Demonstrated performance: NOT established by anything in this packet. The only performance figures are the author's own (9 reference images, 55 subagents, Athenaion 4K render in about 13h on an integrated GPU). These are self-reported in the author's README or ship notes (references/ship.md:42-48) and are not independently checked. Upstream repo has 1 contributor, 0 releases, 0 open issues.
- Evidence about the loop class: benchmark-side snippets (1D-Bench, VisRefiner, UI2Code^N) suggest iterative visual feedback can help. Design2Code suggests it can help little for some models. The critic-reliability question for VLMs is under-studied in what was found.
- Uncertainty: high. Popularity (386 stars) and a fork burst on 2026-11-13 are observed facts with unknown cause. They are not evidence of quality or adoption.

## Suggested verification priorities

1. Verify the pin: confirm commit b23cac6fd9439dfddcab61b14808e7bf72549b46 matches the file contents used here, and that cook-src matches that commit.
2. Confirm the missing `color_check.py` reference (references/target-and-bar.md:82) is absent upstream, not just from the local copy.
3. Read the Design2Code and 1D-Bench papers in full for the iteration-effect claims. Use the paper, not the snippet.
4. Check acceptance status and venue for UI2Code^N (ICML 2026 poster page) before counting it as peer-reviewed.
5. Find VLM-specific self-preference or critic-reliability studies (the current search only found text-only LLM judges and one sycophancy paper).
6. Inspect the two forks with 2026-11-13 pushes (Mitternacht/cook, jpeek01/recook) and check whether any independent write-up or mention exists outside GitHub. Do not count forks as adoption without content evidence.
7. Recount commits and contributors via a working commit-count method (the Link header here was inconsistent).
8. Confirm the usage-window pacing instruction is operable (SKILL.md:72): what usage signal an agent can actually read.
