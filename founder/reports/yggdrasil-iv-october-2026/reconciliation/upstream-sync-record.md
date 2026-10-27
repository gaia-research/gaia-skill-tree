# October 2026 upstream sync record (Yggdrasil IV launch lane, EPIC #2189 outcome 2)

Resolved live via `gh api repos/<repo>/releases/latest` on 2026-10-27T21:3xZ. Applied by `upstream-sync-commands.sh` (now carried by PR #2199 at `founder/reports/yggdrasil-iv-october-2026/reconciliation/upstream-sync-commands.sh`, since `review/meta/` branches may not carry `founder/**/*.sh`) (CLI verb `gaia dev sync-upstream`, `--user mbtiongson1`). Upstream may move again before the 2026-10-31 cutoff: re-run the script from #2199.

| skill | old tag | new tag | releasedAt | source URL | mode |
|---|---|---|---|---|---|
| `addy-osmani/agent-skills` | 0.6.10 | 0.6.13 | 2026-10-13T20:21:58Z | https://github.com/addyosmani/agent-skills/releases/tag/0.6.13 | components |
| `garrytan/garrytan` | (none, bootstrap) | v1.91.242.0 | 2026-10-26T12:01:30Z | https://github.com/garrytan/gstack/releases/tag/v1.91.242.0 | components |
| `garrytan/gbrain` | v0.51.6.0 | v0.60.474.0 | 2026-10-27T21:20:11Z | https://github.com/garrytan/gbrain/releases/tag/v0.60.474.0 | components |
| `garrytan/gstack` | (none, bootstrap) | v1.91.242.0 | 2026-10-26T12:01:30Z | https://github.com/garrytan/gstack/releases/tag/v1.91.242.0 | components |
| `heygen-com/hyperframes` | v0.8.60 | v0.8.209 | 2026-10-27T15:10:55Z | https://github.com/heygen-com/hyperframes/releases/tag/v0.8.209 | components |
| `leonxlnx/taste-skill` | (none, bootstrap) | v2.1.5 | 2026-10-24T23:44:17Z | https://github.com/Leonxlnx/taste-skill/releases/tag/v2.1.5 | components |
| `mattpocock/skills` | v1.2.3 | v1.3.1 | 2026-10-04T12:48:18Z | https://github.com/mattpocock/skills/releases/tag/v1.3.1 | components |
| `obra/superpowers` | v6.4.1 | v7.0.1 | 2026-10-21T21:05:11Z | https://github.com/obra/superpowers/releases/tag/v7.0.1 | components |
| `ruvnet/agentdb` | v3.42.4 | v3.63.5 | 2026-10-27T19:12:42Z | https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 | components |
| `ruvnet/dual-mode` | v3.41.2 | v3.63.5 | 2026-10-27T19:12:42Z | https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 | components |
| `ruvnet/flow-nexus` | v3.41.2 | v3.63.5 | 2026-10-27T19:12:42Z | https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 | components |
| `ruvnet/github-suite` | v3.41.2 | v3.63.5 | 2026-10-27T19:12:42Z | https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 | components |
| `ruvnet/reasoningbank` | v3.41.2 | v3.63.5 | 2026-10-27T19:12:42Z | https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 | components |
| `ruvnet/ruflo-v3` | v3.41.2 | v3.63.5 | 2026-10-27T19:12:42Z | https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 | components |
| `ruvnet/ruflo` | v3.41.2 | v3.63.5 | 2026-10-27T19:12:42Z | https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 | components |

## Not applied (needs a human decision)

- heygen-com/hyperframes: upstream v0.8.209 `skills/` no longer contains 12 components (embedded-captions, faceless-explainer, hyperframes-animation, hyperframes-audio, hyperframes-core, hyperframes-creative, hyperframes-keyframes, motion-graphics, music-to-video, pr-to-video, product-launch-video, talking-head-recut). Umbrella #1823 says to freeze them (`gaia dev freeze`, installable:false). Not done here: all 12 are 3★, their `links.github` are SHA-pinned blobs that still resolve, and `freeze` on 3★+ may trip the META.md §2.4 Star Bar. Decision for a human; the version sync itself is applied.
- mattpocock/skills: watcher payload (#2040) auto-derived `mode: version-only`; the registry block was `components` and was preserved.
- Component adds (garrytan/gbrain 72, addy-osmani/agent-skills 17, obra/superpowers 4, heygen hyperframes 1) are intake children, handled in the intake-triage PR, not here.

## Relation to PRs #2170 / #2171 (targeting main, left open)

This PR writes the identical baseline (`garrytan/garrytan` and `garrytan/gstack` at v1.91.242.0, source https://github.com/garrytan/gstack/releases/tag/v1.91.242.0, releasedAt 2026-10-26T12:01:30Z) in one regeneration of Class S, so it supersedes both and avoids their Class S conflict with each other (#2170 reports CONFLICTING). They were not closed. If #2170/#2171 land on main first, `syncedAt` differs and the dev<-main sync will conflict on those two files; close them or take this branch's content.
