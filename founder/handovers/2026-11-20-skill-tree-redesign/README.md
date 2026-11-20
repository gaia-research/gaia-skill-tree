# Skill Tree website redesign: handoff packet (20 Nov 2026)

The founder approved the redesign prototype on 20 Nov 2026. This folder holds a source snapshot of that prototype and three team handoffs. Tracking: epic [#2481](https://github.com/gaia-research/gaia-skill-tree/issues/2481).

**No wiring yet.** None of this work changes `docs/` or the live site. The founder decides on wiring after seeing the final product, which is the prototype with the stamped assets in place. Wiring gets its own handoff after that.

## What is here

| Path | What it is |
|---|---|
| [`image-assets-codex-sol.md`](image-assets-codex-sol.md) | Image assets A1 to A5 for the Codex team. Issue [#2482](https://github.com/gaia-research/gaia-skill-tree/issues/2482). |
| [`rive-claude-local.md`](rive-claude-local.md) | Rive requests R1 to R3 for the local Claude team. Issue [#2483](https://github.com/gaia-research/gaia-skill-tree/issues/2483). |
| [`design-docs-agy.md`](design-docs-agy.md) | Design-intent documentation for the Agy team. Issue [#2484](https://github.com/gaia-research/gaia-skill-tree/issues/2484). |
| [`prototype/`](prototype/) | Source snapshot of the approved prototype (Claude Design canvas, version 16). Read [`prototype/README.md`](prototype/README.md) first. |

## Teams

| Team | Harness | Roster | Delivers |
|---|---|---|---|
| Images | Codex | Sol, Xhigh, solo | A1 to A5 (A3 optional, A4 conditional) |
| Asset review | Terra's own harness | Terra, independent reviewer | Verification of every image and Rive deliverable |
| Rive | Local Claude with the Rive MCP | Opus (medium) lead; Sonnet and Opus implementers | R1 to R3 |
| Documentation | Agy (Antigravity) | Neon orchestrator; Hydrogen implementers | New design-intent Markdown under `founder/website-design/` |

The three teams work in parallel. None of them depends on another to start.

## The stamp rule (founder, 20 Nov 2026)

Every asset, image or Rive, passes the same gate:

1. **Deliver.** The producing team delivers the exact files, with SHA-256 hashes.
2. **Verify.** Terra checks them independently against the canon and the handoff's acceptance criteria. A verification covers those bytes only; any later change needs a new verification.
3. **Stamp.** Claude, the cloud design lead of this redesign, stamps the verified asset. For images, that means setting the gaia-research asset ledger entry to `approved` with a stamp note. For Rive, it means a stamp line in the delivery receipt.
4. **Veto.** The founder may veto any stamp. A vetoed asset is marked `deprecated` (images) or rejected (Rive) and goes back to its team.

An asset counts only once it is stamped and not vetoed. Producing teams never stamp their own work, and Terra does not stamp.

## Order of work

1. Codex Sol produces the images and Terra verifies them. The local Claude team does the same for Rive, with Terra verifying. In parallel, Agy writes the docs.
2. Claude audits each team's PR, stamps the verified assets and places them in the prototype.
3. The founder reviews the final product and may veto.
4. Only after that does the wiring handoff get written.

**PRs.** Every team opens PRs and marks them ready for review. **No team merges its own PR.** Claude runs the final audit, merges, and closes the issues.

## Decisions recorded in this packet

| Decision | Source |
|---|---|
| Images: Sol solo at Xhigh in Codex, not Pi; no Hydrogen on images | Founder, 20 Nov 2026 |
| Codex image generation defaults to `gpt-image-2.6`, so there is no model preflight; the ledger `credit` records it | Founder attestation, 20 Nov 2026 |
| The canonical image skill is `gaia-research/.agents/skills/gaia-image-production/SKILL.md`; the Skill Tree copy's model rule is out of date ([#2485](https://github.com/gaia-research/gaia-skill-tree/issues/2485)) | Founder, 20 Nov 2026 |
| Stamp rule as above | Founder, 20 Nov 2026 |
| Rive stays with the local Claude team | Founder, 19 and 20 Nov 2026 |
| New documentation team in Agy: Neon orchestrator, Hydrogen implementers | Founder, 20 Nov 2026 |
| No wiring until the founder has seen the final product | Founder, 20 Nov 2026 |
| 3D explorer: keep the live layout's positions and colours, grow links as the hero shape's curved wood, draw every tree node round (Fusion gets an inner ring); text glyphs ○ ◇ ◆ ◉ stay in chips and legends | Founder comments and answers, 20 Nov 2026 |
| A Unique hangs as fruit from a skill it needs (a prerequisite) | Founder answer, 20 Nov 2026 |
| The Trust Ledger sits beside the Evidence Library, under the Yggdrasil lens only; the vertical-bar Leaderboard is a page and a homepage section | Founder comment, 20 Nov 2026 |
| The Hell-Heaven stamp artwork is a placeholder: placement approved, artwork not ratified, so it is not requested | Founder comment, 20 Nov 2026 |
| The A5 keystone follows the canonical Diamond Seal (`docs/assets/marks/diamond-seal.svg`). The prototype's extra inner square is not part of the brand and is not requested. | Claude, from `founder/GAIA_MULTI_TREE_WEB_ENDGAME_2026-11-14.md` §2 (the seal is shell identity) |

## Precedence

This packet describes an approved prototype; it decides nothing beyond the table above. Where it touches existing law, the owner wins: `META.md` and `GOVERNANCE.md` for standing; `founder/ENDGAME.md` and `founder/GAIA_MULTI_TREE_WEB_ENDGAME_2026-11-14.md` for the adaptive website; `DESIGN.md` for tokens and components; `founder/ARBOR-DESIGN.md` for Arbor.

## The prototype link

The canvas is https://claude.ai/artifact/8LmXZkYNH2HggishnaDwow. It is private to the founder: teams can open it only after the founder shares it. Every team can work from the snapshot in `prototype/` either way.
