# Adversarial audit: leonxlnx/cook (Phase 3, ev-adversarial-audit)

Status: audit only. No grades, tiers, stars or Trust Magnitude are assigned here.
Read-only: no repo edits, no `gaia dev` commands, no commits. Upstream files were read and hashed, never executed.
Audit date: 2026-11-14. Live GitHub checks were made with read-only `gh api` calls at audit time.

## Scope and method

- Stage-1 rows: `scratchpad/ev1/stage1-candidates.json` (repo-own, github-stars-own, self-attestation), with the cook entries from `scratchpad/ev1/by-type/{repo-own,github-stars-own,self-attestation}.md`. `link-report.md` and `urls.txt` checked.
- Discovery rows: `generated-output/ev-discovery/leonxlnx-cook/candidates.json` (3 social-signal rows), checked against the raw scrapes in the same directory.
- Upstream: `scratchpad/cook-src/` compared with `Leonxlnx/cook` at the pinned commit by git blob hash for SKILL.md, README.md and scripts/side-by-side.mjs (all three match). Upstream tree listed with `git/trees/main?recursive=1`.
- Guideline checks: `docs/agents/curation-guidelines.md` §5 (canonical URL per type) and §6 (same-source dedup, social-signal view floor, self-attestation).
- Not run: Firecrawl, WebFetch, a browser. The GitHub UI was not loaded, so UI-only figures are unverified.

## Live verification results (GitHub API, 2026-11-14)

| Field | Live value | Row or packet value | Result |
|---|---|---|---|
| Pinned commit `b23cac6fd9439dfddcab61b14808e7bf72549b46` | Exists; it is the only commit on `main` (commits list, per_page=100) | scout: pin not verified | Verified now |
| Commits on default branch | 1 (b23cac6, 2026-10-31T21:48:26Z) | 1 | Agrees |
| Contributors (API) | 1 (Leonxlnx, 1 contribution) | 1 | Agrees |
| Contributors (UI) | not loaded | row/scout: UI shows 2 | Unverified |
| Co-Authored-By trailer | Present in commit message: `Claude Opus 5.5 <noreply@anthropic.com>` | scout: explains UI 2 | Trailer confirmed. The UI-count explanation is plausible (a co-author that is not a GitHub account would not create a login in the API), but it is not confirmed |
| Stars | 410 (2026-11-14, later in the day than the row's 409) | 409 (row), 386 (2026-11-13, scout) | Agrees within same-day drift |
| Forks | 33 | 33 row, 30 scout (11-13) | Agrees |
| Watchers (subscribers) | 2 | not in rows | Observation only |
| License | MIT (SPDX) | MIT | Agrees |
| Releases | 0 | 0 | Agrees |
| Open issues | 0 | 0 | Agrees |
| Archived / fork | false / false | n/a | Agrees |
| Created / pushed | 2026-10-31T21:48:38Z / 2026-10-31T21:48:44Z | scout | Agrees |
| `stargazers` endpoint | HTTP 404 (re-confirmed) | 404 | Star velocity still unverifiable |
| `subscribers` endpoint | HTTP 404 | not listed | Not usable |

Fork creation dates, all 33 forks (`repos/Leonxlnx/cook/forks`):
- 5 forks created 2026-11-01 to 11-07.
- 28 forks created 2026-11-12 to 11-14 (9 on 11-12, 17 on 11-13, 2 on 11-14).
- 31 of 33 forks show `pushed_at` equal to upstream's 2026-10-31T21:48:44Z, meaning no commits after the fork.
- Two forks have later pushes: `Mitternacht/cook` (2026-11-13T15:45:56Z) and `jpeek01/recook` (2026-11-13T18:17:53Z). Contents not inspected.

Interpretation: the burst is an observed fact. It is not evidence of quality, adoption or endorsement, and its cause is unknown. Forks do not add stars, but they are a burst indicator alongside the star growth. The fork burst is about 2 weeks after the repo was created.

Upstream content checks:
- `SKILL.md`, `README.md`, `scripts/side-by-side.mjs`: git blob hashes match the pinned commit.
- Local copy lacks `.gitignore`, which exists upstream. Not used by any row; noted as copy incompleteness.
- `references/target-and-bar.md:82` cites `python color_check.py`. No such file exists upstream (full tree listed). This is a dangling reference in the upstream skill, not a defect in any evidence row.
- Upstream README says "MIT. Made by Leon Lin (@LexnLin)". This ties the repo owner to the X account that authored the discovery post.
- Upstream README performance table (~45h, 55 subagents, ~45k lines, ~11M tokens, ~$1.8k–2.3k API-equivalent) is author-reported. Nothing in the audit verified it, and no row cites it as a verified number.

## Per-row verdicts

| # | Row | Type | URL | Shape (§5) | Verdict | Reasons |
|---|---|---|---|---|---|---|
| A1 | repo-own | repo-own | `https://github.com/Leonxlnx/cook` | Correct (repo root) | **PASS** | MIT, 1 commit, 1 API contributor, 0 releases, 0 open issues all verified live. The row does not claim the UI count of 2, so no conflict. Optional note edit: record the verified pin. |
| A2 | github-stars-own | github-stars-own | `https://github.com/Leonxlnx/cook/blob/main/SKILL.md` | Correct (`blob/branch/path`) | **FLAG** (ingest with note edit) | Shape is canonical and no `tree/` is used. Numbers are accurate for their dated snapshot (409 at 11-14 when row was written, 410 now). Concerns: (1) the star count is repository-level, not specific to SKILL.md; the blob URL does not make it skill-level. (2) Growth 386 to 409 in about one day, followed by the fork burst, is a burst indicator. Star authenticity cannot be checked because the stargazer timeline returns 404. (3) The row's note already discloses the 404; the note should also say the stars are unverified in origin, so the number is not read as adoption. |
| A3 | self-attestation | self-attestation | `https://github.com/Leonxlnx/cook` | Correct (skill's own repo) | **PASS** with wording edit | Only one `self-attestation` row for cook (max 1 per skill satisfied). The note reads "performance claims are author-reported", which implies the row carries performance claims. It does not; that wording suggests the attestation endorses performance. Edit to: "Author-published skill; repository owner self-declared; no independent endorsement." |
| B1 | social-signal, X post | social-signal | `https://x.com/LexnLin/status/2116662591363690999` | Correct (specific post) | **REJECT** | Author-originated. The scrape text says "I turned this into a skill: /cook" and "npx skills add Leonxlnx/cook". The upstream README names "@LexnLin" as the maintainer. The row itself concedes author origin. Author self-promotion is not third-party attention. No view or impression count in the scrape (only like 634, repost 44, reply 27), so the view floor cannot be assessed, and that alone blocks any scoring. Date 2026-10-31 matches created_at 22:44Z. The "about 45h / 45k lines" figures match the post text, but they are author-reported. |
| B2 | social-signal, skillsllm | social-signal | `https://skillsllm.com/skill/cook` | **Wrong type shape**: a directory profile page, not a video/post | **REJECT** | (1) Type mismatch: §5 requires the specific video or post; this is a listing page for the skill. (2) No view counts, so the floor is not assessable. (3) Not independent attention: the page says "It has 396 GitHub stars" (derived from GitHub data), and the directory sells placement ("Promote this skill, from $49"). (4) "Verified" is an automated security scan that the page itself says "is not a certification". Row facts checked and correct: Added 11/12/2026, Last scanned 11/13/2026, 396 stars, 31 forks. |
| B3 | social-signal, skills.sh | social-signal | `https://www.skills.sh/leonxlnx/cook/cook` | **Wrong type shape**: skill directory page | **REJECT** | (1) Same type mismatch as B2. (2) Row note is wrong: it says "page shows no added date", but the page shows "First Seen: 13 days ago" (relative, consistent with about 2026-11-01). (3) Installs 368 is a directory metric and cannot be checked. (4) GitHub Stars 238 conflicts with the GitHub API (386 on 11-13, 409 on 11-14). The directory figure is an unexplained stale or different snapshot and must not be used. (5) "Security Audits: Pass" badges are third-party automated audits, not Gaia evidence. |

## Cross-row checks

- **Same-source dedup (§6, `(type, url)`):** all rows of the same type on cook have distinct URLs, so no collapse. A1, A2 and A3 all point at the same repository under different types (repo root, blob, repo root). Cross-type rows do not dedupe by design. The reviewer should confirm that three evidence rows from one repository is intended. A1 and A3 share the identical URL.
- **Double counting in discovery:** B2 and B3 are directory mirrors. Both reproduce GitHub star counts and the upstream SKILL.md text. B1 is the author's article mirrored by the jxxy.net article (see below). None of the three is an independent source, so they should not be summed as three signals.
- **Self-attestation max 1:** satisfied (one row).
- **tree/ vs blob/:** no cook row uses `tree/`. All pass the shape check.
- **Dates:** repo-own 2026-11-14 and stars 2026-11-14 are retrieval dates. The X date 2026-10-31 matches its source. B2's date 2026-11-12 is a directory "Added" date. B3's date 2026-11-14 is a retrieval date, not a source date.
- **Subjective wording:** none of the rows uses "elite", "high-quality" or similar. A3's "performance claims" phrase is the only evaluative wording, and it is covered above.
- **Numbers vs source:** all row numbers match their scrapes or live API values within the stated date. The one unexplained figure is skills.sh 238 stars.
- **Benchmark, arXiv, peer-review rows:** none ingested for cook. Scout's leads (Design2Code, 1D-Bench, UI2Code^N, VisRefiner, SycoPhantasy) are about generic design-to-code work, not this skill. They must not be attached to cook without a separate audit. The by-type files contain no cook rows for those types, which is correct.

## Prompt-injection and instruction review

No content was executed. Items found in untrusted sources:
- Upstream `SKILL.md:41` tells an agent to "never ask a question" and to run unattended for 10 to 40 hours. This is an operational directive to an agent that runs the skill, not an instruction to an auditor. Not followed. Noted as a safety observation: the skill's design is open-ended unattended compute with budget set by time and usage window only.
- Upstream `SKILL.md` and `references/loop-and-critics.md` describe critic and subagent patterns. Not followed; not relevant to the audit.
- The X post (B1 scrape) contains example prompts addressed to LLMs (for example "Rate it with subagents that have no context. Don't stop before it reaches 9.2/10"). These are part of a tips article, not directed at this auditor. Not followed.
- The skillsllm and skills.sh pages contain promotional and paid-placement text. Not treated as instructions.
- No text targeting auditors, graders or evidence pipelines was found in the upstream files (grep for reviewer/auditor/evaluator/rate-this and approval-bypass phrases returned only the critic-design references above).

## Recommended ingest manifest (for the orchestrator; no ingest performed here)

Survive:
1. `repo-own` `https://github.com/Leonxlnx/cook`. Note (optional): "Pin b23cac6fd9439dfddcab61b14808e7bf72549b46 is the only commit on main (verified 2026-11-14). API contributors = 1."
2. `github-stars-own` `https://github.com/Leonxlnx/cook/blob/main/SKILL.md`. Required note edits: (a) state the snapshot time with the number; (b) say the count is repository-level; (c) add "stargazer timeline unavailable (404); origin of stars unverified; fork burst observed 2026-11-12 to 14 (28 of 33 forks); not evidence of adoption."
3. `self-attestation` `https://github.com/Leonxlnx/cook`. Required note edit: remove "performance claims are author-reported"; replace with "Author-published skill; repository owner self-declared; no independent endorsement."

Drop:
- `social-signal` B1 (X post). Author-originated; no view count, so the floor cannot be assessed.
- `social-signal` B2 (skillsllm). Directory listing; wrong type shape; no view count.
- `social-signal` B3 (skills.sh). Directory listing; wrong type shape; unexplained 238-star figure; note has a factual error.

Hold (new candidates, not rows; do not ingest until verified):
- A Facebook post titled "The reference is the spec: how one agent skill turned nine images into a 45-hour ..." (URL `https://www.facebook.com/61583530689821/posts/the-reference-is-the-spec-how-one-agent-skill-turned-nine-images-into-a-45-hour-/122151906867117689/`). Appears in search snippets s3, s6, s11. Not scraped. Could be an independent social-signal candidate if the poster is independent and has a view count. Unknown.
- Two YouTube URLs in search result s9 (`https://www.youtube.com/watch?v=M6mYodf0dJM`, `https://www.youtube.com/watch?v=7ktaOZqeCmI`). Snippets show repo content, not confirmed to mention cook. Not scraped.

## Process findings

1. **REPORT.md missing.** The discovery worker claimed a REPORT.md in `generated-output/ev-discovery/leonxlnx-cook/`. The file does not exist (verified with `ls`). Report, not fixed here.
2. **Misfiled raw scrape.** `generated-output/ev-discovery/leonxlnx-cook/escapement.json` has sourceURL `https://github.com/Leonxlnx/escapement`, a different repository. It must not be used as cook evidence. Recommend moving it out of the cook directory.
3. **Unreferenced raw scrapes.** `jxxy.json` (a jxxy.net article at `https://www.jxxy.net/ai/articles/lexnlin-2116662591363690999/`, 200 OK) and `cook_readme.json` (GitHub README, 200 OK) are present but not used by any candidate. The jxxy article appears to be a repost of the author's X article (slug matches the post ID). Its body was not read in full; treat it as author-originated unless shown otherwise. Not a candidate.
4. **Discovery coverage gap.** Search results s3, s6, s9 and s11 surfaced a Facebook post, YouTube videos and X posts by the same author (for example status 2119558997162287560 and 2099104768584974721) that were not scraped or triaged. Not all were checked for cook content.
5. **Scout packet status.** The scout said the pin was not verified. It is now verified (see table). The scout's "Firecrawl and ev-discovery not used" note is accurate for the scout, but the discovery run used Firecrawl afterwards (scrapes at 10:04–10:09 on 11-14).
6. **Local copy incomplete.** `scratchpad/cook-src/` is missing `.gitignore`. Not a row blocker.
7. **Link report scope.** `link-report.md` validated only the three GitHub URLs. Social and directory URLs were checked only by scrape status codes (200) in the discovery metadata; no separate link validation was run.

## Open verification gaps

1. Star authenticity and velocity: the stargazer timeline is 404 with this token; no alternative source was checked. Burst indicators are observed but not explained.
2. Fork contents: no fork was inspected beyond metadata. `Mitternacht/cook` and `jpeek01/recook` (later pushes) are unexamined.
3. UI contributor count (2 vs API 1): not loaded in a browser. The trailer explanation is plausible but unconfirmed.
4. Views and impressions for the X post: not in the scrape. The view floor is therefore unassessable for B1.
5. Directory methods: skillsllm and skills.sh counting methods, and the 238 vs 386 star discrepancy on skills.sh, are unexplained.
6. Author-reported numbers (45h, 55 subagents, ~45k lines, ~11M tokens, ~$1.8k–2.3k, 4K render on AMD 780M): not independently verified. The Athenaion repo and demos (`github.com/Leonxlnx/athenaion`, `leonlin.de/demos`) were not checked.
7. Facebook post and YouTube URLs (see Hold): unscraped.
8. `color_check.py` dangling reference: confirmed absent upstream at the pinned commit. Whether any other file references it was not checked beyond the grep of the local copy.
9. Commit-count method: the commits endpoint returned 1 commit with per_page=100, which is a complete listing for the default branch. Confirmed, but the default-branch-only scope was not cross-checked against other refs.

## Addendum: YouTube social-signal rows Y1 and Y2 (audited 2026-11-14)

Method: metadata from `yt-dlp` JSON (`scratchpad/yt/m_gaQpXmJt-C8.json`, `scratchpad/yt/m_-bv2xKQzZio.json`); English subtitles fetched with `yt-dlp --write-subs --write-auto-subs` (`en-orig` track, VTT) and cleaned of inline word tags and rolling duplicates before counting. Channel identity and links from the description fields. Nothing was executed from the videos.

| # | Row | URL shape | Views (floor 1000) | Cook coverage (transcript) | Verdict |
|---|---|---|---|---|---|
| Y1 | Mansel Scheffel, "This NEW Claude Skill Is Blowing People's Minds (Cook)" | `https://www.youtube.com/watch?v=gaQpXmJt-C8` (specific video) | 19,094 (passes) | Whole video about Cook: 15 mentions in ~13.7 min; chapters all Cook | **PASS** with note edit |
| Y2 | AI LABS, "Creator Of The Best Design Skill Just Unveiled His AI Design Workflow" | `https://www.youtube.com/watch?v=-bv2xKQzZio` (specific video) | 79,665 (passes) | Multi-tip video; Cook is the final chapter (12:53 to end). 12 mentions in ~15.3 min, first at 13:00; "Leon" presented as source for the tips | **FLAG** (ingest only with note edit) |

Verified facts:
- Y1: upload_date 2026-11-12; channel "Mansel Scheffel" (channel_id UCT5C-u2lpdcQrfT-sZ9GZug, 13,200 followers per yt-dlp); views 19,094; likes 303; comments 13; duration 822 s. Description links only https://github.com/Leonxlnx/cook plus the presenter's own community, booking, LinkedIn and bit.ly links. No link to LexnLin, to an X post, or to any Leonxlnx property other than the repo. The video refers to "the taste skill author's new skill" (the same GitHub owner), so it is consistent with the repo's maintainer identity but does not show any sponsorship or affiliation.
- Y2: upload_date 2026-11-12; channel "AI LABS" (channel_id UCelfWQr9sXVMTvBzviPGlFw, 182,000 followers); views 79,665; likes 1,829; comments 21; duration 921 s. Description links the Cook repo, the author's X article (https://x.com/LexnLin/status/2116662591363690999), and the channel's own community, newsletter and an Autometa promotion. A sponsor segment is chaptered at 6:39 to 7:31; the sponsor's identity was not confirmed from the transcript. No affiliate link to Leonxlnx or LexnLin was found.
- Repo creation 2026-10-31T21:48:38Z, so both uploads (2026-11-12) post-date the repo. Consistent with the rejected DesignCode video (2026-08-14) being out of scope.

Y1 PASS reasons: specific video URL; views pass the 1000 floor; independent channel with no author link; Cook is the video's whole subject, so the coverage is meaningful; content is the presenter's own walkthrough and tests (chapters "What one hour got me", "One round: helpers and judges" indicate his own use, not a copy of the author's text).
Required note wording (Y1): "Third-party video by Mansel Scheffel (channel not affiliated with the author per description and links), uploaded 2026-11-12, 19,094 views at retrieval 2026-11-14 (yt-dlp). Video is about Cook; presenter describes his own run. Not evidence of cook's performance." Do not quote the title's "Blowing People's Minds".

Y2 FLAG reasons: specific video URL and views (79,665) pass the floor, and the channel is third-party with no affiliate link. But (1) Cook is one segment, roughly 2 minutes of a 15-minute multi-tip video; (2) the segment and the tips largely paraphrase the author's published X article ("Leon gives...", "Leon says..."), so this is amplification of author content, not an independent evaluation; (3) the sponsor segment is not identified; (4) the title's "Best Design Skill" is the video's subjective claim and must not be used in any note. Required note wording (Y2, if ingested): "Third-party multi-tip video by AI LABS, uploaded 2026-11-12, 79,665 views at retrieval 2026-11-14 (yt-dlp). Cook is covered in the final segment (about 13:00 to end of a 15:21 video) and summarizes the author's published article. Not an independent evaluation of cook's results."

Cluster consistency:
- Both videos were uploaded 2026-11-12. Directory listing skillsllm "Added 11/12/2026" is the same day. 9 forks were created on 11-12, 17 on 11-13, 2 on 11-14 (28 of 33 forks in 11-12 to 11-14).
- A public-coverage explanation for the fork burst is now plausible (videos on 11-12, fork peak 11-13), but it is a timing correlation. Fork creation records do not show referrers, so the cause remains unverified.
- Y1 and Y2 are separate channels, but both are coverage of the same release, and Y2 paraphrases the author's article. They must not be summed as two independent confirmations, and neither counts toward the same-day burst as proof of adoption.

Relationship and double-counting checks:
- Y2 links the author's own X post (B1, already rejected). Linking the author's post does not make Y2 author-originated, but B1's rejection is unaffected.
- Y1 and Y2 share the repo URL with A1, A2 and A3 (cross-type, no dedup). That is consistent with the earlier cross-type note and does not change it.

Gaps (new):
- Y2 sponsor identity not confirmed; I did not check the sponsor segment's content beyond the chapter title.
- Transcripts are auto-generated (en-orig); cue timings are approximate.
- Likes, comments and the comment text were not read; no comment-based claims are made.
- yt-dlp returned HTTP 429 once during the Y2 subtitle request; the retry succeeded after a pause.
