# Gaia Control Plane: Founder Product Direction

**Date:** 2026-11-08<br>
**Status:** Founder-selected product direction; **documentation only / implementation not authorized**<br>
**Scope:** Gaia App as a prospective cross-ecosystem interface. This is not a release plan, architectural ratification, implementation ticket, or authorization to merge/deploy.

## 1. North star

Read [ENDGAME.md](./ENDGAME.md) first. Gaia is a multidimensional capability graph: **one capability universe, many independently governed Trees**. The next developer-experience question is how people and agents can *understand, operate, and govern* that ecosystem without repeatedly reconstructing state across CLIs, websites, workflows, and repositories.

**Gaia App is proposed as a future control plane, not a graphical rewrite of Gaia CLI.** It should expose existing domain behavior through contracts, preserve offline/terminal workflows, and reduce maintainer attention rather than adding a new inbox or source of truth.

**Founder selection:** Option **B = Gaia Control Room first**, a maintainer-oriented integrated workbench for projects, agents, Steward findings, receipts, and decisions. The broadly accessible **My Tree / Gaia Workbench** remains important, but is not the first workflow proposed for validation.

**Terminology collision:** The letter **B here refers to the *Control Room-first product strategy*** discussed on 2026-11-08. It is **not** the older **B: Living Tree** release level under [Gaia Research #286](https://github.com/gaia-research/gaia-research/issues/286). That existing Living Tree B / Cockpit C program keeps its own scope, host acceptance gates, and issue owners. Neither initiative is superseded or authorized to ship by this document.

## 2. Product jobs and audiences

| Experience | User job | Proposed emphasis |
| --- | --- | --- |
| **Gaia Control Room** | As an authorized maintainer, identify the few decisions requiring judgment, understand agent work and evidence, and route approved actions | **First workflow to validate, not implement yet** |
| **Gaia Workbench / My Tree** | As a contributor, inspect personal and canonical skills, provenance, structure, projections, and skill development | Complementary; reuse [Tree #2046](https://github.com/gaia-research/gaia-skill-tree/issues/2046) |
| **Gaia Everyday** | As a non-developer, install and understand Skill Heaven and view meaningful capability/session information without Git or policy complexity | Progressive disclosure; no maintainer controls by default |
| **Gaia Organization** | As an organization, govern agents, skill policies, audit and team access | Long-horizon option; no cloud/enterprise implementation approval |

The app must earn its maintenance cost by reducing meaningful operations, avoiding duplicated logic, and remaining optional. If the CLI is faster or a web page already suffices, do not build a second surface for its own sake.

## 3. First-class domains and ownership boundaries

| Domain | Owns truth or action | Proposed app role |
| --- | --- | --- |
| **Skill Tree** | Canonical capability identity, independently defined Tree structures, indices, observations, governed promotions, frontend projections | Explore multiple lenses, inspect evidence, propose or review governed changes; never manufacture canon |
| **Skill Heaven / Skill Zero** | Harness execution, skill selection/summons, installation profiles, session receipts and per-host observability | Configure supported local profiles with preview/rollback; display *actual* session evidence; no second router or telemetry engine |
| **Steward** | Maintenance debt, classification, authority classes, dispatch, verification, receipts and founder decisions | Condensed decision queue and bounded action requests; never expand Class A/B/C permissions because a GUI exists |
| **Research** | Discovery, research material, benchmarks, reproducible evidence intake and publication boundaries | Curated reading, inspect and eventually propose benchmark submissions through existing validation/governance |
| **Gaia Security** | Central security policy, scanner profiles, vulnerability normalization, evidence-bound validation and remediation requirements | Inspect authorized security posture, private findings and approved review/repair state through narrow adapters; **not** a new scanner or repair authority |

**Security status at drafting:** [gaia-security PR #1](https://github.com/gaia-research/gaia-security/pull/1) is merged; [Skill Heaven PR #251](https://github.com/gaia-research/gaia-skill-heaven/pull/251) is merged; [Skill Tree PR #2422](https://github.com/gaia-research/gaia-skill-tree/pull/2422) remains open. These are status snapshots, not new approvals.

**Security constraint:** [Gaia Security's Steward contract](https://github.com/gaia-research/gaia-security/blob/main/governance/STEWARD_INTEGRATION.md) preserves *finding → restricted evidence → reviewed validation → authorized repair → independent verification*. Scanner output is advisory, private evidence must not leak into public UI, and no finding self-authorizes dispatch, repair, acceptance, or merge. Security is a **governance/assurance domain**, not automatically a new capability Tree or a numerical security-prestige score. A future security lens would be independently governed and derived only from appropriate observations.

## 4. Proposed architecture, not a stack ratification

The proposed shape is a **headless, contract-driven control plane with thin clients**:

```text
Desktop GUI (potentially Tauri/Rust + JS/TS)    gaia CLI/TUI
Existing public sites                           Agent/MCP clients
                      │
            versioned domain contracts
                      │
          local bridge / approved adapters
                      │
     ┌──────────┬───────────┬──────────┬────────────┬──────────┐
     │ Tree     │ Heaven    │ Steward  │ Research   │ Security │
     └──────────┴───────────┴──────────┴────────────┴──────────┘
                      │
          existing authoritative systems
           Git / local state / receipts
```

This is a **logical** diagram, not a mandate to create five microservices, run a local HTTP daemon, move all logic into Rust, or create a new `gaia-core` repository.

- **CLI preservation:** PyPI `gaia-cli`, its Python logic, Skill Heaven's TypeScript runtime and existing websites continue to work independently. Build adapters rather than rewrite domain rules in Rust.
- **Contracts first:** Stable skill identity, typed Tree relations, observation/evidence classes, revision/provenance, action policy, errors, and receipts belong to owners with versioning/conformance tests. Different transports may be used: desktop IPC, local agent MCP, and optional authenticated remote API.
- **Local-first:** A desktop shell must not require the GUI or a hosted service for existing agent/CLI correctness. No default uploads of skill bodies, workspace files, session transcripts, or private scan evidence.
- **No second source of truth:** A rendered Tree is a projection. A personal graph is not Gaia canon. A displayed Skill Heaven event is not execution authority. Steward and Security keep their own policy.
- **Third-party Trees:** Future independent maintainers should be able to define namespace, graph semantics, evidence/index rules and projection contracts without forking Gaia canon. Specific plugin/schema design remains open.
- **Scale:** Separate graph/data scale from multi-user operational scale. Enterprise identity, tenancy, hosted agents, remote pairing, team policies, and audit storage are future design questions, not preapproved infrastructure.

Tauri 2 + Rust and modular JS/TS UI are promising candidates for a standalone desktop shell, **not a committed implementation stack**. Reuse the existing web graph projections where practical rather than creating parallel layout semantics.

## 5. Permission and provenance invariants

1. **Authority lives in the domain policy and authenticated operation**, not in the selected UI, agent model, or a clickable button. Read-only observation must never mutate canon or local configuration.
2. Skill stages remain distinguishable: discovered ≠ installed ≠ previewed ≠ materialized ≠ body-read ≠ proven effective use. Render observed / reported / inferred / unknown honestly.
3. Yggdrasil prestige/TrustMagnitude, Arbor behavioral claims, and any future cost/security interpretation are independent; do not collapse them into a universal capability score.
4. Agent integrations receive bounded, permission-checked operations with explicit scope, stop conditions, proof contracts, and receipts. Stronger models do not gain wider authority.
5. Configuration changes preview the exact local diff; installation or removal is opt-in and supports recovery/rollback. Reuse Skill Heaven's **Core** versus **Core + Console** semantics and do not silently install hooks or desktop Mods.
6. GitHub is a natural contributor identity/PR interface, not a default storage bucket for private telemetry or local settings. Remote desktop pairing, synchronized settings and organization auth require separate consent and security decisions.
7. Security finding details stay in restricted channels; the UI may show appropriately sanitized counts/status only when authorized. Native repository security controls stay authoritative.
8. Offline/degraded/unsupported status is explicit. GUI failure never silently falls back to unauthorized commands, bogus observations, or fake telemetry.

## 6. Product stories to validate in a future discovery phase

| Priority | Story and acceptance signal |
| --- | --- |
| First | **Maintainer decision inbox:** one deduplicated, evidence-linked view of actionable Steward Class C decisions; no fabricated work when nothing is due |
| First | **Agent and session receipts:** inspect genuine observed summons, read evidence and scope across supported harnesses, with honest unknown states |
| First | **Safe configuration preview:** an existing Skill Heaven install/profile can be inspected and a proposed change previewed without applying it |
| Next | **Personal Tree inspection:** scoped local/repo/plugin skills mapped to canon when verifiable, unmapped otherwise, without rank contamination |
| Next | **Contribution/benchmark path:** validate existing skill or research submission contracts and prepare a GitHub proposal without bypassing review |
| Later | **Security review adapter:** inspect sanitized security posture and appropriately access-controlled findings, with no scanner-to-repair bypass |
| Later | **Team controls / remote pairing / custom Trees:** explore only after local contracts and permission boundaries have been validated |

Do **not** convert this table into implementation issues or a sprint backlog at this stage.

## 7. Decision gates, not dates

**Now: founder direction only.** Capture the intended experience, cross-repo ownership, architecture questions, and non-goals in this document and cross-reference the existing canonical issues. No product code, repo creation, migration, UI prototype, cloud service, new issue cloud, automatic scan, or deployment follows from this note.

**Future gate 0: contract and reuse audit (requires a separate go decision).** Check what exists in `gaia_cli`, the Skill Tree API clients, the Living Desktop plan, Skill Heaven status model, Steward policy, Research validation and Gaia Security. Demonstrate no competing authority or double-event tracking.

**Future gate 1: narrow pilot (requires a separate go decision).** Test one useful maintainer workflow end to end while preserving all CLI outcomes, policy gates, reproducible receipts, privacy and offline semantics. Build only if measured operator friction improves.

**Future gate 2: scope expansion (requires a separate go decision).** Consider broader My Tree/Workbench, benchmark authoring, private pairing and enterprise operations only when usability evidence and maintenance cost justify them.

**Stop/park criteria:** duplicated domain engines, reliance on unverifiable host hooks, ambiguous authority, accidental security data exposure, fragile cross-platform packaging, or a UI that adds more work than it saves.

## 8. Canonical issue relationships

- [Gaia Research #286](https://github.com/gaia-research/gaia-research/issues/286): cross-product desktop umbrella and existing Living Tree B/C planning; reference this future standalone control plane without rewriting its approved milestone vocabulary.
- [Skill Tree #2046](https://github.com/gaia-research/gaia-skill-tree/issues/2046): personal Tree semantics, discovery, identity, provenance and visual projection.
- [Skill Heaven #161](https://github.com/gaia-research/gaia-skill-heaven/issues/161): host-native desktop Mod/cockpit, separate from standalone Gaia App and from Core + Console.
- [Skill Heaven #192](https://github.com/gaia-research/gaia-skill-heaven/issues/192): existing portable status/event/receipt contract (closed issue; reuse rather than reopen by assumption).
- [Skill Tree #1477](https://github.com/gaia-research/gaia-skill-tree/issues/1477): Steward tracking; maintain governance and authorized dispatch boundaries.
- [Gaia Security PR #1](https://github.com/gaia-research/gaia-security/pull/1): merged policy/scanner foundation; no automatic control-plane execution authority.

## 9. Explicitly undecided

The application name, final UX hierarchy, local bridge packaging, shared contract ownership, standalone desktop versus browser-hosted fallback, deployment targets, authentication/session model, remote-pairing protocol, persistent personal-Tree policy, third-party Tree schema, cloud tenancy, and release timing all remain open.

**Founder decision locked for product exploration:** start from **Gaia Control Room**, not a general dashboard or a CLI skin. **Implementation remains parked until separately authorized.**
