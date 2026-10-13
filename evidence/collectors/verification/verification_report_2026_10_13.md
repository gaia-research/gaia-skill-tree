# EV Verification Report — Emil Kowalski Skills

- **Date:** 2026-10-13 UTC
- **Upstream:** `emilkowalski/skills` at `2d228630ba1446365f614a108cb8252f1feda202`
- **Gaia base:** `f00b3606b355a5c86de6d08190995dbd9ac8aab5`
- **Status:** L4 approved; Phase 1 candidate collection and source audit complete; no evidence ingested, no Trust Magnitude/grade/rank calculated.

## 1. Founder-approved L4 map

| Named skill | Approved primary |
|---|---|
| `animate` | `animation-design` (new basic generic) |
| `animate-expo` | `animation-design` |
| `animation-performance` | `animation-design` |
| `find-animation-opportunities` | `animation-design` |
| `improve-animations` | `animation-design` |
| `review-animations` | `animation-design` |
| `emil-design-eng` | `ui-audit` |
| `apple-design` | `ui-audit` |
| `mobile-native` | `web-best-practices` |
| `break-ui` | `ui-audit` |
| `prototype` | existing `prototype` |
| `write-swift` | `swift-development` (new basic generic) |

`pick-ui-library` remains deferred pending `tool-select` review; `ask-sonner` remains excluded. `animation-vocabulary` remains support-only and was not included in the candidate manifest, named-skill EV, or scoring. The suite is provenance/packaging, not an installation dependency.

For this EV candidate manifest, `genericSkillRef`, `suiteRef`, `level`, and rank fields are deliberately omitted. This prevents generic evidence inheritance and suite-level evidence leakage; the approved map is recorded above, not fed into Phase 1 as an evidence-sharing mechanism.

## 2. Source provenance

The local upstream checkout HEAD and `git ls-remote` main both matched the founder pin. The 12 eligible `SKILL.md` files were SHA-256 checked against the pinned checkout; each link below points to the exact pinned blob:

| Skill | Pinned source | SHA-256 of pinned `SKILL.md` |
|---|---|---|
| `animate` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/animate/SKILL.md) | `b8ede161270458e6ae2e45e8a1985373515d4c63de5568ddb0f9012d7634356c` |
| `animate-expo` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/animate-expo/SKILL.md) | `9a01a91701e6563c67677dde6b66ab30f066a5341d42c21a90ba51d99679274a` |
| `animation-performance` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/animation-performance/SKILL.md) | `ceb9dd3fe912615830f725a0120ccf8d012d15a6218001a5cd6c15d38e39a957` |
| `apple-design` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/apple-design/SKILL.md) | `77bb63b7043bb93aca2ff4ab040c249484eef35682bb6ff7163433c31d30adc7` |
| `break-ui` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/break-ui/SKILL.md) | `e7eec1d70ac56a04255e9c0dbe98084ea3d544cc04aaad34f32c95d6fa9dff5e` |
| `emil-design-eng` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/emil-design-eng/SKILL.md) | `ffbe68e6007fb42cb8149f089b400a1ca007d59ba23e8948e2be4476f3175939` |
| `find-animation-opportunities` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/find-animation-opportunities/SKILL.md) | `d52a377819b84a71930f0c822cfe2849f40301605a2d5c7eccbfa3b257700df2` |
| `improve-animations` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/improve-animations/SKILL.md) | `73962447464433476343e2c12cd08ab39cc99a9e5f3c118c5fb54ed897574ef6` |
| `mobile-native` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/mobile-native/SKILL.md) | `888b7651d66d66dbac4e72b7c554638eb19bd971d686d6cbdf030a5ef3788f55` |
| `prototype` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/prototype/SKILL.md) | `bba39c955eb1871c5a02733976ceec5d0324198e0812e667604756489c89f7b9` |
| `review-animations` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/review-animations/SKILL.md) | `6ff590d29e436766135aa3d137be1fac2a867165c7257fc315b189361f1873af` |
| `write-swift` | [SKILL.md](https://github.com/emilkowalski/skills/blob/2d228630ba1446365f614a108cb8252f1feda202/skills/write-swift/SKILL.md) | `16a4b6adb74e338e55e704ce5753ad54d825438b8a63930eeaede9f3c04c9447` |

`animation-vocabulary` remains support-only; its source blob and SHA-256 from L4 are preserved separately (`40d2b27adfdfeb0570a9f20e7d0255109d9233c50603878bcd0dcd04c923fd94`). It is not an EV candidate or evidence row.

The upstream README credits Emil Kowalski (`emilkowalski`) and the repository is MIT-licensed. Candidate attribution uses the upstream author, not `self-made`; closed intake #1094 is not prior acceptance and its attribution error was not reused. GitHub's **45,919 stars / 2,616 forks** at the 2026-10-13 API check, are suite-level provenance/popularity only. No such values were copied into any named candidate. The video below itself says the parent repo had about 34,000 stars when published; neither figure is per-skill adoption evidence.

### Standalone dependency audit

No named `SKILL.md` declares another sibling skill as a prerequisite for its core task. Cross-skill references are scope routing/optional hand-offs, not suite installation dependencies. Relative companion files are part of the same upstream skill directory and must remain with that skill when distributed.

| Skill | Pinned companion / external dependency or exception |
|---|---|
| `animate` | `RECIPES.md` is loaded for matching component recipes. For component selection it routes to `pick-ui-library`; that branch is unavailable while the skill remains deferred, but ordinary animation construction is standalone. |
| `animate-expo` | `RECIPES.md`; execution targets an Expo/RN app. Core packages named by the source: `react-native-reanimated` + `react-native-worklets`, `react-native-gesture-handler`, and feature-specific `expo-router` / `expo-haptics`; keyboard controller, Lottie, and Skia are conditional. No sibling skill is required. |
| `animation-performance` | No companion file or package requirement; explicitly routes animation construction/review/native-thread work to sibling skills when the user requests those different tasks. |
| `apple-design` | No companion or mandatory package dependency in the pinned source. |
| `break-ui` | `CATALOG.md`; browser/screenshot tooling is conditional, not a hard dependency. |
| `emil-design-eng` | No companion or mandatory package dependency. |
| `find-animation-opportunities` | No companion or mandatory package dependency; read-only follow-on routes to review/plan skills. |
| `improve-animations` | `AUDIT.md` and `PLAN-TEMPLATE.md`; optional `execute <plan>` requires an executor subagent and then the `review-animations` bar. Audit and plan mode is standalone. |
| `mobile-native` | No companion or required package. It is explicitly for mobile **web apps**, may reuse existing `animate` tokens, and routes React Native work to `animate-expo`; real-device verification is required for device-dependent claims. |
| `prototype` | `PICKER.md` is required for the picker harness; browser testing is conditional. Dependency selection is outside its scope and routed to deferred `pick-ui-library`. |
| `review-animations` | `STANDARDS.md` is required for the review criteria; no runtime package dependency. |
| `write-swift` | No companion package; the guide assumes current Swift toolchains (Swift 6.3 baseline in the pinned text). Compiling/executing generated Swift requires a Swift toolchain, but reading the guidance does not. |
| `ask-sonner` (excluded) | `API.md`; using examples requires a React app with the `sonner` library. |
| `pick-ui-library` (deferred) | No companion file; it selects from a curated library list. |
| `animation-vocabulary` (support-only) | No runtime/sibling dependency. Provenance remains at the pinned source; **no EV receipt or scoring row** was made. |

## 3. Independent investigation and worker receipts

Five `worker-lite` lanes were run in isolated worktrees with read-only web search, one lane per the founder's assignment. Receipts in launch order: A `3d6fe510` (done), B `b5a6bcb5` (done), C `bf2e314d` (partial), D `ecbc36c2` (partial), E `5ed985a8` (done). Outputs were treated as leads, not evidence rows, and checked centrally:

| Lane | Assignment | Central disposition |
|---|---|---|
| A | `animate`, `animate-expo` | Upstream descriptions were not counted as independent evidence. The video below was independently fetched and its captions checked. |
| B | `review-animations`, `improve-animations` | Worker catalog pages mostly mirrored source text. Central GitHub follow-up verified a HivemindOS packaged `review-animations` copy, but it is an older adapted version in a 12-star project (below the proxy floor), so no proxy row was accepted. The direct video demo for `review-animations` was verified centrally. |
| C | `find-animation-opportunities`, `animation-performance` | Generic animation-performance discussions and upstream descriptions were rejected as skill-specific evidence. No independent row. |
| D | `emil-design-eng`, `apple-design`, `mobile-native` | Worker claims about native-agent infrastructure for `mobile-native` were rejected: the pinned source is specifically mobile-web CSS/meta guidance. External GitHub references were inspected separately below. |
| E | `break-ui`, `prototype`, `write-swift` | Worker attribution of the Gaia prototype framework and `twostraws/Swift-Agent-Skills` was false/unrelated and discarded. Only the direct video demo for `prototype` survived independent verification. |

The workers did not write evidence files. Relevant direct external leads inspected through GitHub's API:

- [Oort issue #3580](https://github.com/yeomyeonggeori/oort/issues/3580) (2026-10-06) and [merged PR #3585](https://github.com/yeomyeonggeori/oort/pull/3585) (merged 2026-10-06) describe a real Expo mobile UI implementation whose design brief cites `animate-expo` and `apple-design` among several sources. The PR documents an intentional exception to the cited `animate-expo` no-tab-slide rule (minimal fade/capsule motion requested by the user); it does not attribute an outcome to one skill or report per-skill metrics. It also lists `mobile-native`, but the pinned skill is mobile **web**, so that reference is not counted for `mobile-native`. This is an adoption/context lead only, not a typed scoring row.
- [Symphony Forge issue #227](https://github.com/knacklabs/symphony-forge/issues/227) (2026-09-15) explicitly lists `emil-design-eng` and `review-animations` as required in a consumer harness and `apple-design` as advisory. It describes pack installation/configuration, not evaluated results or a bundled artifact; therefore it is recorded as adoption context, not `proxy-containment` or a per-skill outcome row.
- [HivemindOS `skills-lock.json`](https://github.com/LiamVisionary/hivemindos/blob/main/skills-lock.json) and its [packaged `review-animations` file](https://github.com/LiamVisionary/hivemindos/blob/main/packaged-skills/optional/design/emilkowalski/review-animations/SKILL.md) verify a third-party package containing an earlier `review-animations` copy. The lock pins upstream ref `f76beceb7d3fc8c43309cefad5a095a206103a4e` (2026-07-09); the packaged file hashes to `c134999d294cbd631b1e332f072909faa51fb926d5eed49484dbc9e7f75088f3`, versus the upstream file at that ref (`da7ffae44f21bc8c5104567256f6c66e5dac69fd7118db639ee3d30e0f9d6ba9`) and the current pinned file (`6ff590d29e436766135aa3d137be1fac2a867165c7257fc315b189361f1873af`). The package copy adds `license: MIT` frontmatter and removes a blank line relative to the July source. HivemindOS has 12 stars / 4 forks at the 2026-10-13 API check; this is a verified packaging/adoption lead, not an effectiveness evaluation, and is below Gaia's 10,000 `proxy-containment` external-star floor, so no proxy row was created.
- The [rsc-harness README](https://github.com/ericrisco/rsc-harness) lists Emil skills and a source commit, but the current GitHub `skills/` directory contains no matching `animate`, `review-animations`, or other listed skill directories (only an unrelated `swift-ios` name matched). Treat that README catalog entry as unverified packaging, not containment evidence.
- [Dictus issue #201](https://github.com/getdictus/dictus-ios/issues/201) (2026-07-09) proposes a future `apple-design` review and was triaged as human-led on 2026-07-23; it remains open and contains no completed review, so it is not evidence.
- [TheSkillDrop short](https://www.youtube.com/watch?v=JuAKYR7jwTo) (2026-10-04) mentions `emil-design-eng`, `find-animation-opportunities`, and `review-animations`. A direct `yt-dlp` extraction returned 926 views; a later Firecrawl page scrape returned 934 views, 12 likes, 3 comments (counts were changing). Its description explicitly says its terminal lines and before/after animations are creator-made illustrations, not actual skill executions. It remains below Gaia's 1,000-view `social-signal` floor and was excluded.

Google/Firecrawl exact-name searches across blogs, catalogs, Reddit/HN, GitHub, arXiv and benchmark terms found many mirrors/indexes, but those repeat upstream descriptions or merely mention the pack. Examples inspected include [UiChemy](https://uichemy.com/design-skills/animate-expo/), [MCP Servers](https://mcpservers.org/agent-skills/emilkowalski/animate), [AgenticSkills](https://agenticskills.io/skills/emilkowalski-skills), and [Skill Vault](https://skillvault.md/emilkowalski/skills); they were treated as syndication/catalogs, not independent reviews or usage. [Hassam Ali's roundup](https://www.hassamali.com/posts/links-to-improve-llm-experience/) (published 2026-08-25, updated 2026-09-05) lists the collection and summarizes its scope, but contains no run log or result attributable to an individual skill, so it was not a row. Searches found no directly relevant arXiv paper, reproducible benchmark, or structured independent peer review for these 12 skills. No vendor benchmark was promoted to a `benchmark-result` row.

## 4. Per-skill EV receipts

Exactly one YouTube source qualified for a canonical skill-specific row. It is **one shared video** with distinct attributed sections—not a suite-wide row copied to siblings.

**Source:** [AISeeKing — “Emil Kowalski Skills: This is CRAZY GOOD SKILL (you need to have it)!”](https://www.youtube.com/watch?v=huWl2J4A6FE), published 2026-09-02. Direct `yt-dlp` metadata fetched 2026-10-13 UTC: **8,026 views, 84 likes, 3 comments**; a separate Firecrawl page scrape returned 8,023 views with the same likes. An earlier cached search snippet said 6,506 views / 74 likes. View counts were changing; the candidate manifest preserves the direct `yt-dlp` snapshot (8,026), not a stable lifetime total. The creator is external AISeeKing and the title is promotional. Auto-captions and the page transcript—not frame-by-frame visual inspection—were used to verify the narrated invocations. A low-resolution video segment fetch was attempted but yt-dlp reported no matching format, so no frames were downloaded or inspected; visual output remains unverified. Do not treat view count as quality or efficacy.

The video predates the current pin. The latest upstream commit available by its publication date was `d23d7f88a2e21c9e4b1418c7abe420f5c1052ba7` (2026-08-21). Comparing the three demonstrated `SKILL.md` files (`animate`, `review-animations`, `prototype`) from that commit to the pin shows only an eight-line initial-response block added to each; the demonstrated workflows/rules did not change. The video is still an earlier revision, not a test of the exact pinned bytes.

| Skill | Independently attributable observation | Canonical EV row / readiness |
|---|---|---|
| `animate` | Auto-caption transcript records invocation and standalone HTML animation implementation, 00:06:38–00:07:55. | One `social-signal` candidate; Phase 1 and link validation. Exposure/demo only, not efficacy. |
| `animate-expo` | Video describes the skill but does not invoke it. Oort PR is a shared implementation lead, not isolatable per-skill outcome. | No row; further independent evidence needed. |
| `animation-performance` | No direct run, review, or skill-specific outcome found. Generic performance rules are not evidence for this named implementation. | No row; evidence gap retained. |
| `apple-design` | Video describes it but does not invoke it. Oort PR cites it in a multi-source design brief; no isolated skill outcome or typed engagement metric. | No row; adoption lead only. |
| `break-ui` | No direct demo, independent review, adoption result, or benchmark found. | No row; evidence gap retained. |
| `emil-design-eng` | Consumer-harness issue #227 names it as required; no result/effectiveness report. TheSkillDrop's short mentions it but labels its demo illustrative and is below the view floor. | No row; adoption/config lead only. |
| `find-animation-opportunities` | Both videos only describe it; TheSkillDrop labels its examples illustrative and is below the view floor. No independent invocation or evaluation found. | No row; evidence gap retained. |
| `improve-animations` | Video describes it but does not invoke it; no independent execution or evaluation found. | No row; evidence gap retained. |
| `mobile-native` | No valid skill-specific demo found. The Oort reference is a React Native app, whereas the pinned skill addresses mobile web; excluded as mismatched scope. | No row; evidence gap retained. |
| `prototype` | Auto-caption transcript records invocation and three distinct toast variants behind a visual picker, 00:07:59–00:09:15. | One `social-signal` candidate; Phase 1 and link validation. Exposure/demo only, not efficacy. |
| `review-animations` | AISeeKing's auto-caption transcript records invocation on a deliberately flawed UI file and its findings/verdict, 00:04:50–00:06:38. TheSkillDrop's separate short is illustrative only and below the view floor. HivemindOS also packages an older copy, but its project is below the proxy floor. | One `social-signal` candidate; Phase 1 and link validation. Exposure/demo only, not independent efficacy. Packaging is a non-scoring adoption lead. |
| `write-swift` | Video only describes Swift guidance; no direct invocation, external review, or skill-specific result found. | No row; evidence gap retained. |

The direct 8,026-view snapshot is above Gaia's `social-signal` view floor of 1,000; that only makes these raw candidate rows eligible for review, not a quality grade or TM result. Creator multiplier/authority was not assigned. No row was created for `animation-vocabulary` (support-only), `pick-ui-library` (deferred), or `ask-sonner` (excluded). The video mentions other members, but mentions are not demonstrations.

## 5. Canonical EV processing and validation

- Candidate input: `evidence/collectors/emilkowalski-ev-candidates.json` (12 individually scoped candidate IDs; exactly 3 `social-signal` rows). It intentionally contains no `genericSkillRef`, `suiteRef`, level, grade, or score fields. The video was not appended to the shared author-level YouTube collector; explicit candidate IDs keep its three direct invocations from flowing to mention-only siblings.
- Phase 1: `generate_source_dump.py` loaded 12 candidates; `repo-own=0`, `github-stars-own=0`, `social-signal=3`, and all other canonical types=0. It ran with an empty named directory, `--skip-live-stars`, and `--no-legacy-tiers` so this scoped run did not read/copy other intakes or assign suite popularity. `compile_data_lake.py` compiled the candidate-only type-first lake successfully.

  Reproduce the scoped collection (candidate-only outputs stay under ignored `generated-output/`):
  ```bash
  mkdir -p generated-output/curation/emil-ev-2026-10-13/empty-named
  python evidence/scripts/generate_source_dump.py \\
    --named-skills-json registry/named-skills.json --gaia-json registry/gaia.json \\
    --named-dir generated-output/curation/emil-ev-2026-10-13/empty-named \\
    --output-dir generated-output/curation/emil-ev-2026-10-13 \\
    --by-type-dir generated-output/curation/emil-ev-2026-10-13/by-type \\
    --report-path generated-output/curation/emil-ev-2026-10-13/source_report_2026_10_13.md \\
    --candidate-manifest evidence/collectors/emilkowalski-ev-candidates.json \\
    --skip-live-stars --no-legacy-tiers --report-date 2026-10-13
  python evidence/scripts/compile_data_lake.py \\
    --sources generated-output/curation/emil-ev-2026-10-13/by-type \\
    --lake generated-output/curation/emil-ev-2026-10-13
  ```
- Phase 2: no per-skill `github-stars-own` rows existed, so Phase 2 did not fetch or assign per-skill star values. Parent repository stats were gathered separately and remain suite-level context only.
- Phase 2B: no `benchmark-result` rows or benchmark-source candidates; not applicable.
- Phase 3 manual adversarial audit: no type mismatch, duplicate within a target skill, subjective claim, or score field in the three rows. One source URL is shared across exactly three skills because the transcript records three distinct invocations. Cached view counts were replaced; promotional framing and non-efficacy limits are explicitly noted. Mirror/catalog search hits and uncompleted external plans were rejected.
- Phase 4 Firecrawl URL validation: `validate_sources.py --manifest` checked the candidate evidence URLs. The three skill-specific rows share one video URL, deduplicated to **1 unique URL: HTTP 200; 0 broken links; 0 validation errors** (receipt: `firecrawl_validation_report_2026_10_13.md`). The 12 pinned upstream blobs were separately checked against the local commit and SHA-256 list above; external GitHub leads were fetched directly through the GitHub API.

Generated candidate-only type partitions and the unified lake are kept locally under `generated-output/curation/emil-ev-2026-10-13/`; they are not mixed into the existing shared `evidence/by-type/social-signal.md`, which already contains another scoped candidate and cannot be safely replaced by this candidate-only run. The PR carries the canonical candidate-manifest input and its verification receipts instead. No registry/named/generic files or support schema/install code changed.

## 6. Trust and next-stage boundary

The three rows are unscored evidence candidates. No creator multiplier/authority tier was assigned, no TM or grade was calculated, and nothing was ingested. The other nine eligible skills retain zero skill-specific rows rather than borrowing a sibling's video or suite stars. The next gate is human review of these source candidates; additional evidence discovery is justified only for skills where a stronger independent signal is desired. Support-component representation/install requirements remain tracked under #2084 and outside this EV change.
