# Evidence Manifest — Intake #1733

**Status:** Human topology-approved (`intake:topology-approved`). Evidence verification completed across Phases 1–4.  
**Intake Issue:** [#1733](https://github.com/gaia-research/gaia-skill-tree/issues/1733)  
**Batch ID:** `20260905191407-mbtiongson1-from-file`  
**Candidate:** `heygen-com/hyperframes` (Suite Capstone → `genericSkillRef: video-composition`)  
**Upstream Repository:** `https://github.com/heygen-com/hyperframes`  
**Pinned Commit SHA:** `7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd`  

---

## 1. Stage-1 Primary Evidence Rows

| Skill | Evidence Type | Scope | Source URL | Verified Metric | Audit Status |
|---|---|---|---|---|---|
| `heygen-com/hyperframes` | `github-stars-own` | `suite-wide` | `https://github.com/heygen-com/hyperframes/blob/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/skills/hyperframes/SKILL.md` | 44,308 stars | `200 OK` · Verified live via GitHub REST API |
| `heygen-com/hyperframes` | `repo-own` | `suite-wide` | `https://github.com/heygen-com/hyperframes` | 4,199 commits, 57 contributors, Apache-2.0 | `200 OK` · Verified live via GitHub REST API |
| `heygen-com/hyperframes` | `self-attestation` | `standalone` | `https://github.com/heygen-com/hyperframes/blob/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/skills/hyperframes/SKILL.md` | Upstream orchestrator & router entry point | `200 OK` · Exact blob URL |

---

## 2. Adversarial Component Installability Audit (Phase 3 & 4)

All candidate suite components were audited to verify they are **real, independent, installable Agent Skills**, not passive documentation or code modules.

### Installability Verification Matrix

| Component Candidate | Relative Skill Path | HTTP Status | YAML Frontmatter | Declared Skill Name | Install Mechanism |
|---|---|---|---|---|---|
| `heygen-com/hyperframes` (Capstone) | `skills/hyperframes/SKILL.md` | `200 OK` | Valid (`---`) | `hyperframes` | `npx hyperframes init` / `npx skills add` |
| `heygen-com/hyperframes-core` | `skills/hyperframes-core/SKILL.md` | `200 OK` | Valid (`---`) | `hyperframes-core` | `npx hyperframes skills update hyperframes-core` |
| `heygen-com/hyperframes-cli` | `skills/hyperframes-cli/SKILL.md` | `200 OK` | Valid (`---`) | `hyperframes-cli` | `npx hyperframes skills update hyperframes-cli` |
| `heygen-com/hyperframes-animation` | `skills/hyperframes-animation/SKILL.md` | `200 OK` | Valid (`---`) | `hyperframes-animation` | `npx hyperframes skills update hyperframes-animation` |
| `heygen-com/hyperframes-keyframes` | `skills/hyperframes-keyframes/SKILL.md` | `200 OK` | Valid (`---`) | `hyperframes-keyframes` | `npx hyperframes skills update hyperframes-keyframes` |
| `heygen-com/hyperframes-creative` | `skills/hyperframes-creative/SKILL.md` | `200 OK` | Valid (`---`) | `hyperframes-creative` | `npx hyperframes skills update hyperframes-creative` |
| `heygen-com/hyperframes-audio` | `skills/hyperframes-audio/SKILL.md` | `200 OK` | Valid (`---`) | `hyperframes-audio` | `npx hyperframes skills update hyperframes-audio` |
| `heygen-com/hyperframes-registry` | `skills/hyperframes-registry/SKILL.md` | `200 OK` | Valid (`---`) | `hyperframes-registry` | `npx hyperframes skills update hyperframes-registry` |
| `heygen-com/media-use` | `skills/media-use/SKILL.md` | `200 OK` | Valid (`---`) | `media-use` | `npx hyperframes skills update media-use` |
| `heygen-com/motion-graphics` | `skills/motion-graphics/SKILL.md` | `200 OK` | Valid (`---`) | `motion-graphics` | `npx hyperframes skills update motion-graphics` |
| `heygen-com/music-to-video` | `skills/music-to-video/SKILL.md` | `200 OK` | Valid (`---`) | `music-to-video` | `npx hyperframes skills update music-to-video` |
| `heygen-com/pr-to-video` | `skills/pr-to-video/SKILL.md` | `200 OK` | Valid (`---`) | `pr-to-video` | `npx hyperframes skills update pr-to-video` |
| `heygen-com/product-launch-video` | `skills/product-launch-video/SKILL.md` | `200 OK` | Valid (`---`) | `product-launch-video` | `npx hyperframes skills update product-launch-video` |
| `heygen-com/remotion-to-hyperframes` | `skills/remotion-to-hyperframes/SKILL.md` | `200 OK` | Valid (`---`) | `remotion-to-hyperframes` | `npx hyperframes skills update remotion-to-hyperframes` |
| `heygen-com/slideshow` | `skills/slideshow/SKILL.md` | `200 OK` | Valid (`---`) | `slideshow` | `npx hyperframes skills update slideshow` |
| `heygen-com/talking-head-recut` | `skills/talking-head-recut/SKILL.md` | `200 OK` | Valid (`---`) | `talking-head-recut` | `npx hyperframes skills update talking-head-recut` |
| `heygen-com/embedded-captions` | `skills/embedded-captions/SKILL.md` | `200 OK` | Valid (`---`) | `embedded-captions` | `npx hyperframes skills update embedded-captions` |
| `heygen-com/faceless-explainer` | `skills/faceless-explainer/SKILL.md` | `200 OK` | Valid (`---`) | `faceless-explainer` | `npx hyperframes skills update faceless-explainer` |
| `heygen-com/figma` | `skills/figma/SKILL.md` | `200 OK` | Valid (`---`) | `figma` | `npx hyperframes skills update figma` |
| `heygen-com/general-video` | `skills/general-video/SKILL.md` | `200 OK` | Valid (`---`) | `general-video` | `npx hyperframes skills update general-video` |

---

## 3. Adversarial Installability Checks
1. **Automated Upstream Linter:** Upstream runs `scripts/lint-skills.ts` in CI (`bun run lint:skills`) to enforce strict conformance with the Agent Skills standard:
   - Validates that frontmatter parses with the `yaml` package.
   - Requires non-empty string `name` and `description`.
   - Restricts top-level keys to `{name, description, license, allowed-tools, metadata}`.
   - Guards against unquoted inline patterns (`!`, `>`) that break Claude Code / Codex bash checkers.
2. **Dual-Tier Lifecycle:** Documented in `skills/hyperframes/references/skill-lifecycle.md`:
   - Eager core set: `/hyperframes`, domain skills, `/media-use`.
   - Lazy workflow set: installed on demand via `npx hyperframes skills update <workflow>`.
   - General harness fallback: compatible with `npx skills add heygen-com/hyperframes --skill <name>` and native subagent directory discovery.
3. **No Phantom Skills:** Zero directories in the suite lack a runnable `SKILL.md`. Every component is an independent, functional skill unit.
