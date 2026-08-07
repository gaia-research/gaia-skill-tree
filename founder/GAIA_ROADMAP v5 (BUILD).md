GAIA — Open Capability Control System for AI Agents

Version: 5.0

Status: **RATIFIED**

Supersedes: `GAIA_ROADMAP v4 (BUILD).md` (archived to `founder/handovers/archive/roadmaps/`)

Author: Orchestrator + Marcus Tiongson

Drafted: 2026-07-28 (post-Yggdrasil II, v7.1.5)

Ratified: **2026-07-28** — Marcus Tiongson. Fourteen decisions ruled, three amended, one left deliberately open (V5-4). See §10.

Audience:

* Codex
* Claude Code
* Orchestrator Agents
* Gaia Research (planning + editorial)
* Human Maintainers

---

## 0. What changed from v4

v4 was a **single-product roadmap with a migration at the end of it**. v5 is an **ecosystem roadmap with contracts between products**. Six substantive corrections:

1. **Sprint F is retired, not completed.** v4 planned to migrate the Skill Tree website into a `gaia-research` monorepo and reduce Skill Tree to a headless toolkit. That is cancelled. Gaia Research stays the laboratory and the organizational centre; the Skill Tree stays the Atlas and keeps its own site. Replacement: **Ecosystem Separation + Contract Federation** — nothing consumes another product's source, everything talks through versioned contracts.

2. **Skill Heaven is where v5 puts its focus** — as one member of an ecosystem, not as a ranked flagship over the others. *(Amended at ratification, V5-2.)* The ecosystem is **Skill Tree + Skill Heaven + Skill Hell**, with Gaia Research as the laboratory around them. Skill Heaven is the runtime layer: it decides which capabilities enter a session, at what dose, under what trust posture. The Tree answers *what exists and why trust it*; Skill Heaven answers *what should enter this context, right now*. The Tree is **feature-complete for this cycle** — ops and refinements only, until Yggdrasil III. That is why v5's attention sits on Heaven: not because the Tree is subordinate, but because it is done.

3. **Alphabetical sprints are replaced by permanent concurrent programs.** v4's B→D→C→E→F→G chain assumed one product and one work-front. There are now five products moving at once. Programs run continuously; **arcs** sequence the milestones that cut across them.

4. **The lexicon becomes load-bearing infrastructure, not documentation garnish.** With five repos and agent-authored change, semantic entropy is the primary failure mode. A federated lexicon with per-namespace ownership is a v5 deliverable, tracked at #1302.

5. **Enterprise, Prestige Index, and the Skill Groups ML program are deferred** — not killed. None of them currently pull demand, and two of them (Prestige, Skill Groups) are better informed by runtime evidence that does not exist yet.

6. **Every v5 claim is bound to a reproducible record.** v4's Migration Invariants block is replaced by **Federation Invariants**, which enforce contract versioning and evidence-before-claim across repo boundaries.

7. **Gaia MCP is rebuilt, not extended.** The v0.1.0 package is a prototype. Program 4 restarts from a blank canvas keeping only the package name — which means, uniquely, that its vocabulary can be ruled by the lexicon *before* any of it ships.

8. **Adoption is a program, not a polish pass.** v5 introduces more genuinely new concepts than any roadmap before it — five planes, a runtime layer, a summon model, an index — and the About pages take Gaia's highest traffic. **Program 7 is locked into Arc I**, and carries the ecosystem explainer, the adoption paths, change management for concepts that *replace* what users already learned, and a consolidation pass over every user-facing surface. Concepts that are not explained are not adopted.

---

## 1. North Star (v5)

> **Gaia is an open capability control system for AI agents.**
>
> **Gaia Research** measures and publishes the frontier.
> **Gaia Skill Tree** records what capabilities exist and why they are trusted.
> **Skill Heaven** controls what enters a session and how much it costs.
> **Gaia MCP** lets agents discover and summon those capabilities through stable, evidence-backed contracts.

v1's north star — canonical naming, attribution, evidence, discoverability, provenance — is preserved intact. v5 adds the layer v1 could not yet see: **runtime admission, context authorship, cross-harness composition, deterministic routing, benchmark-derived skill economics, capability virtualization.**

The strategic bet, stated plainly: *marketplaces solve acquisition; Skill Heaven solves runtime composition.* As catalogs grow past a few hundred capabilities, "install everything useful" stops scaling — descriptions, triggers, schemas and MCP definitions all bill to standing context on every session. The durable moat is not the catalog. It is the accumulated cross-harness evidence, versioned compatibility history, benchmark corpus, trust graph, and routing outcomes. Code is copyable; that dataset is not.

---

## 2. The ecosystem — five planes

| Plane | Product | Repo | Primary responsibility |
|---|---|---|---|
| **Research** | Gaia Research | `gaia-research/gaia-research` | Measure, experiment, publish, explain, provoke |
| **Trust** | Gaia Skill Tree | `gaia-research/gaia-skill-tree` | Canonical capability graph, provenance, Trust Magnitude, identity, stamps |
| **Runtime** | Skill Heaven | `gaia-research/skill-heaven` | Compile session posture, meter context dose, admit and route capabilities |
| **Transport** | Gaia MCP | `gaia-research/gaia-mcp` | Expose trusted discovery and summoning to agents |
| **Execution** | Harness doors | `skill-heaven/packages/*-heaven` | Apply those controls correctly in Claude Code, pi, Codex, Cursor, and others |

This is an **ecosystem architecture**, not a monorepo architecture. The boundary rule is already ratified upstream as **D6** (cross-repo contract, thin): the product repo does not import research code — it vendors small pure pieces and proves parity by fixture. v5 generalizes D6 to every seam in the table.

> **⚠ V5-4 is OPEN by founder ruling (2026-07-28) — this table is provisional.**
>
> The five-plane table above is the *implementation* view. The founder leans toward a **four-name** model — **Tree · Heaven · Hell · Research** — in which **Skill Heaven is one package containing both the MCP transport and Skill Hell**, and the Tree eventually fans out (the Canon Tree is done; enterprise skill trees become a packaged product alongside an enterprise-ready Skill Heaven). The decision is deliberately kept flexible: the four-name model is easier to understand and is the likely public story, while the repo and package topology stays free to move.
>
> **What this does *not* block.** Program 7's ecosystem surface ships the **four-name public story** and never names a repo or an npm package. It owns the relationships between four named things; topology is an internal concern that can change without rewriting the page. Program 4's *destination* — standalone `gaia-mcp` package versus folded into the Heaven package — is a sub-decision of V5-4 and likewise open; V5-14's blank-canvas ruling holds either way.

### Ownership, stated so it stops being re-litigated

**Gaia Research owns** the HH benchmark methodology, context-dose research, the harness capability matrix, negative findings, thought leadership, blog and SEO surfaces, experimental labs, benchmark ledgers, and the deliberately playful frontier of the brand. It is the organization, the laboratory, and the public intellectual voice. It is **not** a future destination for the Skill Tree website.

**Gaia Skill Tree owns** skill identity, content hashes, generic and Named records, attribution, Trust Magnitude, evidence, relationships and prerequisites, promotion and rank, public projections, and — after Arc IV — benchmark-earned HH stamps.

**Skill Heaven owns** the live session: launch posture, standing dose, which hand-curated skills enter, what can be summoned, how much can be admitted, whether a requested loadout exceeds the selected rung, and how one outcome maps onto different harness mechanics.

**Gaia MCP owns** transport compatibility, agent-oriented results, recommendation composition, approvals, and client diagnostics. It owns neither Registry truth nor benchmark truth — it consumes both. As of the 2026-07-28 ruling its implementation is a **blank canvas** (Program 4).

**Nobody owns adoption by default — so v5 assigns it.** Five planes with clean boundaries is an architecture; it is also five things a newcomer must hold at once. Program 7 owns the surfaces that make the ecosystem legible: the explainer, the adoption paths, and the record of what changed. Without an assigned owner, adoption is what each plane assumes another plane is doing.

---

## 3. The compounding loop

```text
Gaia Research
    measures cost, quality, failures, and harness behavior
        ↓
Gaia Skill Tree
    records trusted capabilities, hashes, relationships, and earned stamps
        ↓
Skill Heaven
    compiles a task-specific session posture and admission policy
        ↓
Gaia MCP
    searches and summons hash-pinned capabilities
        ↓
Harness Door
    applies the plan safely inside Claude, pi, Codex, Cursor
        ↓
Run Ledger
    records dose, result, latency, failures, and trust provenance
        ↓
Gaia Research
```

Each rotation improves the benchmark dataset, the routing index, harness-compatibility knowledge, skill-level cost estimates, trust coverage, negative-result knowledge, public research, and the Tree's canonical projections.

**The loop is the moat.** v5's programs are organized to close it, not to maximize any single plane.

---

## 4. Ground truth at draft time (verified 2026-07-28)

Everything in this section was checked against live repos, not recalled. Where the founder's v5 analysis and live state diverge, the divergence is named.

### 4.1 Verified state

| Fact | State |
|---|---|
| Skill Tree version | **v7.1.5** on `main` |
| Yggdrasil II | **Shipped.** EPIC #1002 closed; aggregate PR #1185 merged |
| `claude-heaven` launcher slice | **Merged** (skill-heaven PR #3): native posture default, session-scoped statusline, standing-dose census, zero shared-state mutation, core↔door package boundary, **57/57 tests** |
| `/skill-heaven` posture slider | **Draft PR #4, open, not mergeable as framed** (see 4.2) |
| `@gaia-research/mcp` | **v0.1.0, PUBLISHED TO npm 2026-07-16** — read-only Registry mode, implementation under review. Binary `gaia-mcp`. Description: "Agent-native discovery and trust interface for the Gaia Skill Tree". ⚠️ **This row read "not yet published to npm" at ratification. That was factually wrong — corrected 2026-07-28 per V5-18.** The package name is the true name and is kept (V5-14); it is the *implementation* that is a blank canvas |
| Gaia MCP live tools | `gaia_search`, `gaia_inspect`, `gaia_status` |
| Legacy `packages/mcp` | Still in Skill Tree; extraction RFC open at **#1191** |
| Lexicon of record | Live in `gaia-research/founder/lexicon.json` on `main` — **51 terms** (29 `canonical`, 13 `parked`, 9 `banned`), schema 1, namespace `core`, updated 2026-07-24. Generated companion `founder/LEXICON.md` (hand-edit forbidden). Port RFC to Skill Tree open at **#1302** |
| Lexicon **CI gate** | **Already shipped and green** — `.github/workflows/lexicon-ci.yml` in `gaia-research` runs `scripts/lexicon/check-lexicon.ts` plus 19 self-test assertions and 8 fixtures. Path-scoped to the Skill Heaven line only. Does **not** exist in `gaia-skill-tree`, `skill-heaven`, or `gaia-mcp` |
| `search_skills` ↔ `gaia_search` | **Already ruled** — `summon` is `canonical` with oracle **D4** and its definition names `search_skills` as its partner tool. `search_skills` wins. The prototype's `gaia_search`/`gaia_inspect`/`gaia_status` are simply not yet recorded as `banned` with a replacement pointer |
| HH ledger | `hh-ledger/v1` emitting; validator + append-only ledger of record in `gaia-research` |
| R0 dose census | Published (`content/reports/hh-benchmark/r0-census.md`) |

### 4.2 Divergences the founder analysis should absorb

**(a) PR #4 cites a retired decision — confirmed.** `RATIFICATION.md`'s header lists **D13** among "Retired ids — never reused," deleted 2026-07-24. PR #4's body binds itself to "D12, **D13**, P2, P3, D6." The PR is authority-stale. It must be re-bound before merge. This is exactly the failure D9 exists to prevent (*ratification and implementation land in the same PR*), which makes it a governance finding, not a code finding.

**(b) Product floor vs. benchmark floor is already ratified as OPEN, with the founder's proposal on the table.** Ledger OPEN item 4 reads: *"Suppressing slash commands at the deepest floor leaves it with no controls at all. Proposal: keep the doorless floor as the benchmark's placebo-of-record and ship a doorful product floor, priced as a separate arm."* v5 therefore does **not** invent this split — it **mandates closing it** and names the closure a gate on Arc I. PR #4's probe F7 already prices the door at **+515 tokens** (20,176 vs T9b's 19,661; still −28.9% off native's 28,379).

**(c) The `/skill-heaven` scope gap is already OPEN item 10.** The ledger records N8 as **CURRENT — INCOMPLETE**, covering "the moment of reach only," and names the four scenarios that surfaced in skill-heaven#4: posture adjustment, capability discovery, clean-room access, refusal transparency. v5 makes completing N8 a deliverable, not a discovery.

**(d) Gaia MCP is a prototype, and is being rebuilt from scratch.** Founder ruling, 2026-07-28: `@gaia-research/mcp` v0.1.0 is treated as **a prototype, not a foundation**. The package name is kept; the implementation is a **blank canvas**. This resolves what looked like a name collision — D4 ratifies a ≤2-tool summon surface spelled `search_skills`/`summon`, while the prototype shipped `gaia_search`/`gaia_inspect`/`gaia_status` — into something better: **nothing is load-bearing yet, so the lexicon rules the names *before* the implementation exists rather than reconciling two shipped surfaces after the fact.** That is the correct order, and it is available exactly once. Program 2 owes Program 4 a ruling before Program 4 writes a tool definition.

**(e) The org-level North Star surface does not exist — the *line's* does.** `VISION.md` and `MISSION.md` have **moved** to `gaia-research/docs/skill-heaven/`, and their own headers are explicit about scope: *"This is a line doc, not an org doc: `gaia-research` is the lab, and this is one of the things the lab is building."* The Skill Heaven line therefore has a ratified north star — *"Gaia is a Mixture-of-Agents, but for skills"*, *"End install debt"* — and the **ecosystem has none**. Two consequences: `skill-heaven/README.md`'s badges still point at the old repo-root paths and 404, and there is no public page anywhere that explains how the five planes relate. The second is the real gap; the first is a link fix.

**(f) v4's sprint ledger, honestly.** Sprint D (Content Engine + Benchmark MVP) closed 13 issues and is substantially landed. Sprints C and E were never opened as milestones. Sprint F is now cancelled. Sprint G is deferred. v5 does not inherit their numbering.

**(g) Two shipped surfaces are currently unreachable from the homepage.** #1130 records that the *Latest Weekly Report* and *Benchmarks Leaderboard* links in `docs/index.html` were temporarily disabled "until Epic 1002 is completed." **EPIC #1002 is now closed.** Both surfaces exist and render (`docs/reports/2026-28/`, `docs/benchmarks/{humaneval,mmlu}/`) — they simply have no way in. Under this repo's Design Entrypoints invariant, *shipping a section with no way to reach it from the homepage is a broken feature*. Re-enabling them is unblocked work, not future work, and it is the cheapest credibility win available to v5: the megaphone v4 built is currently muted.

---

## 5. The seven programs

Programs are **permanent and concurrent**. Each has an owner plane, a standing goal, and kill criteria that can be checked on any given day.

Programs 1–6 are the build. **Program 7 is how anyone finds out** — and it is locked into Arc I, not deferred, because v5 introduces more genuinely new concepts than any roadmap before it.

---

### Program 1 — Skill Heaven Prototype

**Plane:** Runtime · **Priority: immediate flagship** · **Repo:** `skill-heaven`

**Standing goal:** one delightful, truthful Claude Code prototype that demonstrates capability control end to end. Not every harness. One undeniable magic trick.

The demonstration, in order:

1. Native session dose, honestly scoped
2. A visible session posture
3. A manually curated lower-dose launch
4. Trusted capability discovery
5. One safe summon path
6. A measured before/after result

**Immediate blocker — PR #4 reshaping.** The PR does not merge as framed. It must be re-cut around:

- Re-binding to live decisions; **D13 is retired and must not appear**
- The benchmark floor may remain completely doorless — it is the placebo-of-record (B2)
- The product floor retains the minimum control surface (F7's +515 tok route)
- The two floors are **measured and named separately**, and priced as separate arms (B1)
- `/skill-heaven` initially **explains posture and available transitions** — it never implies an in-session subtraction the harness cannot perform (D12)
- The ratification delta lands upstream **in the same PR cycle** as the implementation (D9)

This is not a setback. It is the product learning what physics permits, and the ledger is already structured to absorb it.

**Kill criteria — Skill Heaven v0.1**

- KC1: `claude-heaven` installs cleanly from the marketplace
- KC2: Native launch reports an honestly scoped standing dose (current scope: user + project; bundled and plugin-provided disclosed as excluded)
- KC3: Product floor produces a **measured** context reduction against its own same-harness placebo
- KC4: Curated mode loads only the selected skill set — zero listing residual
- KC5: No shared config or skill directory is mutated (P3), verified by before/after diff
- KC6: Unsupported levels fail explicitly and refuse honestly (P2) — no false sense of access
- KC7: `/skill-heaven` never claims a transition the harness cannot perform
- KC8: Every public claim links to a reproducible benchmark record (B4)
- KC9: A complete three-minute demo runs native → measured bloat → curated launch → successful task

**Budget:** ~$34

---

### Program 2 — Lexicon & Contract Spine

**Plane:** cross-cutting · **Priority: parallel with Program 1 — explicitly not a waterfall prerequisite** · **Repos:** all

**Standing goal:** an agent-built ecosystem that does not decay semantically. One term, one owner, one definition — imported or extended elsewhere, never redefined.

The reference implementation exists: `gaia-research/founder/lexicon.json` already distinguishes `canonical` / `parked` / `banned` / `frozen`, and already encodes the discipline that **a provisional concept does not become canonical merely because an old report described it confidently**. RFC #1302 is the port into the Skill Tree, and separates: founder rulings · standing invariants · point-in-time reports · generated artifacts · vocabulary authority · structural schema constants. It exists specifically to stop the failure mode where an agent blocks correct work because a stale report was mistaken for permanent law.

**Federated namespaces** — one mega-file is explicitly rejected. Ratified set (V5-8, 2026-07-28):

`gaia.skills` · `gaia.trust` · `gaia.heaven` · `gaia.mcp` · `gaia.research` · `gaia.brand`

> **`gaia.registry` is rejected** — renamed to **`gaia.skills`**. This is the same ruling as **#1258** ("Gaia Registry" is not the product name), arriving from the vocabulary side. The two close together.

**Two namespace HQs** (V5-8, 2026-07-28). Namespace files live in exactly two repos:

| Repo | Owns |
|---|---|
| `gaia-research` | `core` · `gaia.research` · `gaia.brand` · `gaia.heaven` · `gaia.mcp` |
| `gaia-skill-tree` | `gaia.skills` · `gaia.trust` |

`skill-heaven` and `gaia-mcp` hold **no** namespace files — they consume. The rationale: the Skill Tree's vocabulary is tight and skill-indexed, so it belongs proximate to the Tree; everything else converges on Research, because every line starts and ends there.

**Scope correction (verified at ratification).** The six-namespace migration is a restructure of a **working** system, not a greenfield build. `founder/lexicon.json` is live at 51 terms and **the CI gate already runs green in `gaia-research`** (§4.1). Program 2's Arc I work is therefore: (a) migrate flat `core` into the six ratified namespaces across the two HQs, (b) record `gaia_search`/`gaia_inspect`/`gaia_status` as `banned` → `search_skills`, which makes the existing D4 ruling *enforceable* and is the entire Program 2 → Program 4 unblock, (c) extend the gate's reach to the second HQ. The authority hierarchy (#1302) remains Arc II/III.

**Contracts to formalize.** The lexicon defines what the nouns mean; schemas define their shapes; ratification defines why they exist; tests verify the implementations agree.

| Contract | Owner plane | Status |
|---|---|---|
| `gaia-public/v1` | Trust | Partially live (`/api/v1/*`) — needs versioned freeze |
| `gaia-cli-machine/v1` | Trust | Draft — stable JSON for scan/status/installed/paths |
| `gaia-skill-ref/v1` | Trust | Draft — stable SkillRef + content hash |
| `hh-ledger/v1` | Research | **Emitting; freeze in Arc II** |
| `hh-stamp/v1` | Research → Trust | Draft in Arc II, accepted in Arc IV |
| `heaven-profile/v1` | Runtime | Draft |
| `heaven-census/v1` | Runtime | Emitting (chars4 tokenizer, sha256 SKILL.md refs) |
| `summon-index/v1` | Runtime | Arc III |
| `gaia-mcp-result/v1` | Transport | Draft |

**First live test.** Resolve the `search_skills` ↔ `gaia_search` collision (§4.2d) through the lexicon, not through a side conversation. Whichever spelling wins, the loser becomes `banned` with a pointer. If the lexicon cannot settle this, it is not yet load-bearing.

**Kill criteria**

- KC1: Every term in the table above resolves to exactly one namespace-owning definition
- KC2: A CI gate rejects a PR that introduces a `banned` term or redefines a term it does not own — **live in `gaia-research`; must reach the `gaia-skill-tree` HQ**
- KC3: The `search_skills`/`gaia_search` collision is closed by lexicon ruling, with the losing spelling marked `banned` — **ruled; needs the enforcing entries written**
- KC4: An agent can determine, from the lexicon alone, whether a concept is ratified law or a point-in-time report *(Arc II/III, #1302)*
- KC5: The six ratified namespaces exist across the two HQs, and no term is defined twice

**Budget:** ~$18

---

### Program 3 — Hell Heaven Index

**Plane:** Research · **Priority: research moat** · **Repo:** `gaia-research`

**Standing goal:** the HH Index becomes the bridge between the Tree and Skill Heaven — the evidence that makes routing eligibility a lookup rather than a guess.

The existing methodology is strong and is **carried forward unchanged**: standing / invocation / harness doses priced separately (B1) · own-placebo anchoring (B2) · repeats plus confidence intervals, no determinism assumed (B3) · clean sandboxed harness installs for benchmark-grade claims (B5) · negative findings first-class (B4) · stamps content-hash-bound · routing eligibility by discrete set membership, not vague arithmetic (G2) · security and provenance accompanying the stamp (G1).

**The Index must answer more than "good" or "bad."** Target question set:

- What does this skill cost while merely listed?
- What does it cost when invoked?
- Does it improve task completion?
- At what task complexity does it become useful?
- Under which models and harnesses?
- Does it net-save or net-cost tokens?
- Does it improve latency or degrade it?
- Does it survive compaction correctly? *(currently unmeasured — ledger OPEN 2)*
- Can it be safely summoned by content hash?
- Is it suitable for manual, curated, or routed admission?

**Tree integration is one-directional.** Research publishes the result; the Tree records the accepted result; Skill Heaven consumes it. The Tree never calculates it.

```yaml
hellHeaven:
  schema: hh-stamp/v1
  contentHash: sha256:...
  harness: claude-code
  tier: low
  result: heaven-safe
  benchmarkRun: ...
  confidence: ...
  measuredAt: ...
```

**Kill criteria**

- KC1: Clean-install benchmark arms run for both floors (benchmark floor and product floor), priced separately
- KC2: `hh-ledger/v1` is frozen and versioned; the validator is the hard gate on every record
- KC3: At least one **published negative finding** carries the same rigor as a positive one
- KC4: Compaction survival (OPEN 2) has a matrix gate before any load-bearing copy asserts it
- KC5: `hh-stamp/v1` is drafted with content-hash binding and a confidence field
- KC6: No public claim ships ahead of its benchmark record (B4), enforced by the claim-discipline table

**Budget:** ~$30

---

### Program 4 — MCP & Summoning · *blank canvas*

**Plane:** Transport · **Priority: rebuild, do not extend** · **Repo:** `gaia-mcp` (+ #1191 in Skill Tree)

**Founder ruling (2026-07-28):** `@gaia-research/mcp` v0.1.0 is **a prototype**. It is not the foundation of the transport plane. Program 4 **restarts from a blank canvas**, keeping the package name and discarding the implementation, the tool vocabulary, and the v0.1→v1.0 milestone ladder inherited from the prototype's `ROADMAP.md`.

This is a deliberate discard, and it buys three things the prototype cannot:

1. **Names get ruled before the *rebuild* ships.** Program 2 rules the vocabulary, and Program 4 implements the ruling. ⚠️ **Corrected 2026-07-28 (V5-18):** this originally read "available exactly once, and only because nothing is published." **The package IS published** (v0.1.0, npm, 2026-07-16), and its README documents `gaia_search`/`gaia_inspect`/`gaia_status`. The ordering advantage is real but **smaller than drafted** — it applies to the rebuilt implementation, not to a blank canvas. **Renaming the prototype's tools is a breaking change to a shipped public interface, not free pre-publication hygiene.**
2. **Profiles are a design input, not a retrofit.** The two-audience problem is known up front rather than discovered after a surface exists.
3. ~~**No migration debt.** Nothing is installed anywhere, so there is no deprecation window to honour and no client to break.~~ ⚠️ **STRUCK 2026-07-28 (V5-18) — this was false.** The package is on npm and installable, so there **is** a client surface to consider. At v0.1.0 with a single published version the debt is **small, but not zero**, and Program 4 owes an explicit migration story — deprecation window, aliases, or a clean break at 0.2.0 with a changelog entry. **The disposition is OPEN (see §12).**

**Standing goal:** a rich agent interface for deliberate Gaia interaction that never makes a Skill Heaven session pay for the parts it is not using.

**Two profiles over one package** — the architecture the rebuild targets:

| Profile | Surface | Purpose |
|---|---|---|
| **Registry / Bond** | discovery · inspection · workspace status · project analysis · progression planning · (later) guarded install + Intake | Deliberate Gaia interaction |
| **Heaven / Summon** | discovery · summon (≤2 tools, per D4) | Low-overhead runtime admission |

Skill Heaven launches the **minimal** profile and **measures its schema dose**. D4's subtraction discipline applies to the profile actually loaded, never to the package's total surface — a package may be rich as long as a session can be thin.

**Sequencing constraint.** Program 4 does not write a tool definition until Program 2 has ruled the `gaia.mcp` namespace. A blank canvas that starts by inventing vocabulary reproduces the defect it was reset to avoid.

**Skill Tree's half of the work is #1191**, and the rebuild *strengthens* its gating rather than relaxing it: `packages/mcp` is not deleted until the rebuilt standalone is published, clean-installable, contract-documented, link-migrated, and covered by a client-config migration test. Meanwhile the truthful-bridge obligation is absolute — **no active surface may present an unpublished package as installable** (#1328 tracks 14 stale refs in `docs/en/mcp-server.html` alone). A prototype being discarded makes this *more* urgent, not less: the surfaces currently advertise something that will never ship in that shape.

**Kill criteria**

- KC1: The `gaia.mcp` namespace is ruled in the lexicon **before** the first tool definition is written
- KC2: Both profiles are named in the lexicon and implemented by one package
- KC3: The Heaven profile's schema dose is measured and subtracted in every Heaven claim
- KC4: `@gaia-research/mcp` is published and installs clean from a fresh MCP client
- KC5: Every summon is content-hash pinned
- KC6: No public Skill Tree surface claims an unpublished package is installable
- KC7: `packages/mcp` is removed **only** after all #1191 migration gates pass
- KC8: The prototype's history is preserved in git; nothing is force-erased

**Budget:** ~$32 *(raised from $26 — a rebuild costs more than an extension)*

---

### Program 5 — Gaia Skill Tree Core

**Plane:** Trust · **Priority: maintenance lane — ops and refinements only** · **Repo:** `gaia-skill-tree`

> **Rescoped at ratification (V5-2, V5-12).** The Tree is **feature-complete for this cycle**. Program 5 is a **background maintenance program**, not a build program: ops, refinements, and correctness fixes until **Yggdrasil III**. It never competes with Arc I for founder attention. Budget drops from ~$40 to **~$20**; the difference rolls into the arc cushion, not into scope.
>
> **Execution model:** a nested orchestrator loaded with `founder/BACKLOG_ERADICATION_TRACKER.md`, driving chained auto-Sonnet workers, producing **one large resumable PR** with **a single founder review pass** at the end. Not a stream of small PRs — the founder reviews once.

**Standing goal:** the Tree does not absorb Skill Heaven — it becomes exceptionally good at **supplying** it. Skill Heaven is the Tree's most demanding consumer, and that is healthy pressure: *if Skill Heaven cannot safely route against the Tree, the Tree's machine contracts are not yet strong enough.*

**5.1 Substrate work (the routing dependency)**

- Canonical skill **content hashes** and stable **SkillRef** identifiers — the pin every summon depends on
- Trust and evidence projections consumable without reading repo internals
- Harness compatibility metadata
- Dose metadata
- HH stamp projections (Arc IV)
- Prerequisite and fusion relationships
- Freshness information + version handshakes
- Deterministic branch and rank resolution
- Lexicon enforcement in CI

**5.2 Post-Yggdrasil-II consolidation.** Ygg II shipped the type/branch axis split, the Ultimate rank rename, and the Evidence Floor → Trust Magnitude move. Its remainder is now Program 5's opening work — and per the repo's own sprint-completeness rule, this is the sprint's own remainder, tracked and closed, not re-filed as future work:

| Issue | Work |
|---|---|
| #1231 | Taxonomy logic triplicated across client / projection / CLI — the website pays the drift cost |
| #1230 | Dead type-enum reads (`ultimate`/`unique`/`extra`) + `stype='extra'` writes persist post-#997 |
| #1264 | `share.py` `_TYPE_SYMBOL` keyed on retired type literals |
| #1174 | Auto-derive `type` from prereq structure; deprecate `gaia dev reclassify` |
| #1202 | Built `gaia.json` is invalid against its own schema (`additionalProperties:false`) — **priority: a consumer will hit this** |
| #1201 | Live graph JSON `$schema` points at a dead path (404) — **priority: same** |
| ~~#1001~~ | ~~Branch-aware TM formula rebuild (G8)~~ — **DEFERRED at ratification (V5-12).** Does not ship in this cycle. Lands **August 2026 with TM Index v2**, alongside the meta audit. It is a new formula, not Yggdrasil II's remainder, and the founder is satisfied with Ygg II as shipped. |

**5.3 Standing platform debt** — carried, not deferred: #1147 (DOM-XSS / `innerHTML` risks on static pages) · #1268 (frontend performance: DAG, Skill Explorer, page latency) · #1258 (branding: "Gaia Registry" is not the product name) · #1307 (`gaia install` conformance to the Agent Skills standard) · #1178 (RFC: extract `skill-trees/` — a **federation** move, not a migration).

**5.4 Deliberately *not* in Program 5:** the website does not move. There is no monorepo destination. `docs/` remains the Skill Tree's own served surface.

**Kill criteria**

- KC1: Every skill exposes a stable SkillRef + content hash that Skill Heaven can pin against
- KC2: A version handshake exists between Tree projections and both consumers (Heaven, MCP)
- KC3: Taxonomy logic has exactly one implementation, not three (#1231 closed)
- KC4: `gaia.json` validates against its own schema (#1202 closed)
- ~~KC5: TM v-next is branch-aware and published with a reproducibility fingerprint (#1001)~~ — **moved out of this cycle** to TM Index v2, August 2026 (V5-12)
- KC6: `gaia dev docs` output and the served Class S artifacts remain byte-consistent
- KC7: The Ygg II remainder lands as **one resumable PR** with a single founder review pass — not a stream of small PRs

**Budget:** ~$20 *(reduced from $40 at ratification — maintenance lane, #1001 deferred)*

---

### Program 6 — Research, SEO & Thought Leadership

**Plane:** Research · **Priority: persistent, enjoyable cadence** · **Repo:** `gaia-research`

**Standing goal:** a laboratory notebook people look forward to opening. **Not a content mill.** This is where the keep-it-fun rule is load-bearing rather than decorative — for Gaia Research, joy is part of the operating model, not a distraction from the roadmap.

The ingredients already exist: the weekly report engine, permanent report URLs, benchmark pages, research blog infrastructure, sitemap integration, Infinite Skill Craft, Context Diet, the Yggdrasil II editorial material (published, every statistic verified against the live registry), and Skill Heaven's inherently provocative thesis.

**Editorial pillars**

1. **Agent Skill Economics** — standing cost, invocation cost, context tax, why "install everything" stops scaling
2. **Harness Field Notes** — Claude Code vs pi vs Codex vs Cursor; verified mechanisms; negative findings; version drift; clean-room experiments
3. **Capability Cartography** — what new skills are appearing, which fusions are emerging, what the Tree reveals about agent development
4. **Skill Heaven Build Log** — unexpected harness behavior, benchmark results, failed routing experiments, design decisions, demo videos
5. **Open Research** — can deterministic routing beat model-selected tool loading? when does a skill net-save tokens? how large can a trusted catalog grow? what belongs in standing vs summonable context?

**One experiment, six echoes:** a research artifact → a concise blog post → a permanent SEO page → a visual social card → a short demo → a Tree or HH dataset update. Pipeline tracked at #1309.

**Boundary with Program 7.** Program 6 owns the *cadence* — what gets published, how often, in what voice. Program 7 owns the *durable surfaces* — the ecosystem explainer, adoption paths, change management. The failure mode to avoid is a research cadence that publishes brilliantly into a site nobody can navigate, which is roughly where things stand today: **v4's entire Sprint D thesis — *megaphone before medals* — is built and currently unreachable** (#1130, §4.2g). Program 6 supplies the content; Program 7 makes sure there is a way in.

**Kill criteria**

- KC1: Every shipped Skill Heaven or HH result has a permanent, citable URL within one week of landing
- KC2: At least one published negative finding per arc
- KC3: The cadence is sustainable without orchestrator intervention on the mechanical steps
- KC4: No research artifact ships without an entrypoint from at least one navigable surface

**Budget:** ~$22

---

### Program 7 — Adoption & Surface Consolidation

**Plane:** cross-cutting, founder-locked · **Priority: Arc I — *locked in at the start*** · **Repos:** `gaia-skill-tree`, `gaia-research`, `skill-heaven`

**Founder ruling (2026-07-28):** **Adoption is the surface.** The About pages take the highest traffic of anything Gaia ships, and v5 introduces more genuinely new concepts than any previous roadmap — five planes, two products nobody has heard of, a runtime layer, a summon model, an index. **Concepts that are not explained are not adopted.** This program is locked into Arc I rather than deferred to a polish pass.

**The problem, stated plainly.** v5 asks a reader to hold five products and a new mental model. Right now:

- There is **no ecosystem-level North Star page anywhere.** `VISION.md`/`MISSION.md` are Skill Heaven *line* docs by their own declaration (§4.2e); `gaia-research/PRODUCT.md` is a brand and voice register, not an explainer; `gaia-skill-tree/docs/about.html` is a founder-story page. Each is correct for its job. None answers *"what is Gaia, and how do these five things relate?"*
- **Two shipped surfaces have no way in** (#1130, §4.2g).
- **A public README badge 404s** because a doc moved and nothing followed it.
- Skill Heaven, the HH Index, summoning, and capability control are **new nouns with no adoption path** — no page a curious reader lands on and leaves understanding.

These are the same defect at four sizes: **things ship, and the way in does not.** This repo already has the invariant that names it — *shipping a section with no way to reach it from the homepage is a broken feature.* Program 7 applies that invariant to the ecosystem instead of to a page.

**7.1 The Gaia Ecosystem / About surface (Arc I, locked)**

One canonical explainer of the five planes and the compounding loop, published where the traffic already is. It must answer, for a first-time reader:

- What is Gaia?
- What are these five things and why are they separate?
- Which one do I want *right now*?
- What changed, and what does it mean for what I already use?

It must **not** become a fifth competing north-star doc. The rule: the ecosystem page owns the *relationships*; each line doc keeps owning its own thesis and is linked, never restated. `VISION.md`/`MISSION.md` stay Skill Heaven's.

**7.2 Adoption paths**

An adoption path per plane, each ending in something a reader can actually do: install `claude-heaven` · browse the Tree · read a benchmark · contribute a skill · connect the MCP once it is real. Every path states its true state — shipped, prototype, or gated — because a false path costs more trust than a missing one (B4 applied to product surfaces, not just claims).

Note: this is not a revival of the retired `docs/archive/ADOPTION.html`. That page was deleted under Yggdrasil II precisely because **nothing linked to it** — which is the failure this program exists to prevent, and a useful reminder that an adoption surface with no entrypoint is not an adoption surface.

**7.3 Change management (conceptually new things)**

v5's concepts are new, and some of them **replace** things people already learned. Yggdrasil II changed the type and branch axes, the rank vocabulary, and the trust model. v5 retires the monorepo migration, rebuilds the MCP, and introduces runtime admission. A reader who learned Gaia six months ago is now partly wrong and has no way to find out.

Deliverable: a durable **What Changed** surface — versioned, dated, linked from the About page — that states what a returning user must relearn. The Ygg II meta-post is the proof this works; the gap is that it was an *event*, not a *standing surface*.

**7.4 Surface consolidation**

Audit every user-facing surface across the three public repos and resolve each to one of: **canonical** (this is where the concept lives) · **pointer** (links to canonical, restates nothing) · **retired** (removed, with redirects). Fix the stale ones found in drafting — `skill-heaven`'s 404 badges, #1328's 14 stale MCP refs, #1258's "Gaia Registry" branding violation, #1130's disabled entrypoints.

**Kill criteria**

- KC1: A single canonical Gaia Ecosystem / About surface explains the five planes and the compounding loop, and is reachable from the homepage of every public Gaia property
- KC2: Every plane has an adoption path ending in a concrete action, each labelled with its true state (shipped / prototype / gated)
- KC3: A standing, versioned **What Changed** surface exists and covers Yggdrasil II and v5
- KC4: Every user-facing surface is classified canonical / pointer / retired — no concept has two competing homes
- KC5: Zero 404s and zero unreachable shipped surfaces across the three public repos (closes #1130, the `skill-heaven` badges, #1328)
- KC6: No adoption path advertises an unshipped capability as available

**Budget:** ~$28

---

## 6. Sequencing — five arcs

Programs run continuously. Arcs are the checkpoints that cut across them.

### Arc I — The Door · *now*

- Reconcile PR #4 with the current ratification ledger (**drop D13**)
- Decide benchmark floor vs. product floor; close ledger OPEN 4
- Complete `/skill-heaven`; close ledger OPEN 10 (finish N8)
- Package `claude-heaven`
- Publish a repeatable native-vs-curated demonstration
- Keep Hell visibly locked (P2)

**Adoption, locked into Arc I (Program 7):**

- Ship the canonical **Gaia Ecosystem / About** surface — five planes, one page, highest-traffic placement
- Publish an **adoption path per plane**, each labelled with its true state
- Stand up the standing **What Changed** surface covering Yggdrasil II and v5
- Re-enable the weekly report + benchmark leaderboard entrypoints (#1130) — unblocked by EPIC #1002 closing
- Fix `skill-heaven`'s 404 `VISION`/`MISSION` badges (they moved to `docs/skill-heaven/`)
- Begin the canonical / pointer / retired classification of every user-facing surface

**Ruled before implementation (Program 2 → Program 4):** the `gaia.mcp` namespace, so the MCP rebuild does not start by inventing vocabulary.

**Arc gate:** Skill Heaven v0.1 kill criteria KC1–KC9 pass · no shipped Gaia surface is unreachable from its own homepage · a first-time reader can land on one page and correctly describe what the five planes are and which one they want.

### Arc II — The Measure · *next*

- Complete clean-install benchmark arms (B5)
- Publish the R0 dose census in its finished form
- Run paired Heaven experiments with own-placebo anchoring
- Publish negative **and** positive results
- Freeze `hh-ledger/v1`
- Draft `hh-stamp/v1`
- Probe compaction survival (OPEN 2)

**Arc gate:** no Skill Heaven claim in public copy lacks a reproducible record.

### Arc III — The Summon · *after Heaven is honest*

- Deterministic routing spike (D5: nearest-neighbour, frozen versioned index, no model call decides a loadout)
- Freeze the versioned retrieval index (`summon-index/v1`)
- Launch the minimal MCP summon profile; measure its schema dose
- Enforce content-hash pinning
- Add the session admission meter
- Keep Hell gated until its evidence clears

**Arc gate:** a summon is hash-pinned, dose-metered, and traceable to a Tree record.

### Arc IV — The Inscription · *after results exist*

- Accept HH stamps into the Skill Tree (G1: canon read-only; stamps land after the benchmark)
- Publish the stamped routing projection
- Render dose and summonability on skill dossiers
- Add Tree → Heaven launch actions
- Feed runtime findings back into Research — **the loop closes here**

**Arc gate:** one full rotation of §3's loop completes with an auditable trail at every hop.

### Arc V — The Expansion · *only after the Claude prototype sings*

- `pi-heaven` (note the verified `--no-skills` discovery race on 0.80.10 — floor runs must assert the listing probe and discard leak runs)
- Codex recipe or door
- Cursor recipe or door
- Compatibility matrix automation
- User-defined curated sets
- Shared loadout manifests
- Organization policies — much later

---

## 7. Cross-cutting: Federation Invariants

These **replace** v4's Migration Invariants. Every non-trivial PR in any Gaia repo carries:

```markdown
## Federation notes

- **Contracts touched:** [which versioned contracts this reads or writes]
- **Cross-repo effect:** [what another plane must do, or "none"]
- **Evidence:** [benchmark record / matrix cell / "no public claim made"]
```

**The standing rules:**

1. **No plane imports another plane's source.** Vendor small pure pieces and prove parity by fixture (D6).
2. **Every cross-plane read goes through a versioned contract.** No plane reads another's repository internals.
3. **No claim ships ahead of its benchmark** (B4). A "will not work" ledger is as first-class as a "will work" one.
4. **Ratification and implementation land in the same PR** (D9). A PR citing a retired decision id is a defect (§4.2a).
5. **Doses are priced separately, never as one number** (B1).
6. **Canon is read-only from outside** (G1). Schema changes route as reviewable proposals; stamps land after the benchmark.
7. **One term, one owner.** Redefining a term another namespace owns is a CI failure.
8. **Class P / Class S is unchanged.** If a browser fetches it at runtime it is Class S and belongs in git; if only tooling reads it, Class P and gitignored.

---

## 8. What moves off v5

| Item | Disposition | Reason |
|---|---|---|
| **Research migration / monorepo move** (v4 Sprint F) | **Retired** | Gaia Research stays the laboratory and organizational centre; the Skill Tree keeps its own site. Federation replaces migration. |
| **Enterprise + Auth API** (v4 Sprint G) | **Deferred** | Not for lack of potential — no external demand currently pulls it, and it does not energize the work. Returns when demand pulls it in. |
| **Prestige Index** | **Deferred** | Trust Magnitude, HH stamps, runtime results, and permanent attribution are more load-bearing now. Contributor prestige should emerge from observed behavior, not be designed ahead of it. |
| **Skill Groups ML program** (v4 Sprint E) | **Deferred** | Routing and admission evidence will reveal which groupings are actually useful. Do not force an ML taxonomy prematurely. |
| **Named badges** | **Deferred with Skill Groups** | Same reasoning: rewards need an audience and a basis. |
| **SEO + content engine** | **Retained, re-pointed** | Now amplifies Skill Heaven research, not only Registry trends. |
| **Stable consumer contracts** | **Retained, escalated** | More important than in v4 — there are now several independent products depending on them. |
| **Billing / marketplace / multi-tenancy** | **Out of scope** | Unchanged from v4. |

---

## 9. Budget

| Program | Token estimate | Cost estimate |
|---|---|---|
| 1 — Skill Heaven Prototype | ~340k | ~$34 |
| 2 — Lexicon & Contract Spine | ~180k | ~$18 |
| 3 — Hell Heaven Index | ~300k | ~$30 |
| 4 — MCP & Summoning *(blank-canvas rebuild)* | ~320k | ~$32 |
| 5 — Gaia Skill Tree Core *(maintenance lane)* | ~200k | ~$20 |
| 6 — Research, SEO & Thought Leadership | ~220k | ~$22 |
| 7 — Adoption & Surface Consolidation | ~280k | ~$28 |
| **Total (Arcs I–IV horizon)** | **~1.84M** | **~$184** |

*Program 5 reduced from ~$40/~400k at ratification (V5-2, V5-12): the Tree is feature-complete for this cycle and #1001 moves to TM Index v2 in August. The ~$20 difference rolls into the arc cushion, **not** into scope.*

Arc V is unbudgeted by design — it opens only after the Claude prototype sings, and its scope depends on what Arcs I–IV learn.

Cushions: each program carries ~25–35% orchestration, review, and rework overhead. Unspent budget rolls into the next arc's cushion, **not** into scope expansion.

**Model routing:** splurge domains (contract schemas, HH methodology, routing determinism, floor-vs-floor ratification) → Opus at max effort. Balanced (lexicon porting, projection work, MCP profiles) → Opus high. Satisfice (docs, link migrations, test additions, CI YAML) → Sonnet. Auto-batchable (dependency bumps, mechanical renames) → Haiku with schema.

---

## 10. Decision log — v5 ratification

**All entries ruled 2026-07-28 by Marcus Tiongson.** One entry (V5-4) is ruled **OPEN on purpose** and must stay that way until evidence closes it. Where a ruling **amended** the drafted text, the amendment is authoritative and the body of this document has been updated to match.

| # | Decision | Ruling |
|---|---|---|
| V5-1 | v4 Sprint F (migration + monorepo move) is **retired, not completed**. Gaia Research remains the laboratory and organizational centre. | ✅ **Ratified as written** |
| V5-2 | ~~Skill Heaven is the flagship program of v5 and takes the centre.~~ **AMENDED:** the ecosystem is **Skill Tree + Skill Heaven + Skill Hell**, with Research as the laboratory. v5's *focus* is Skill Heaven. The Tree is **feature-complete for this cycle** — ops and refinements only until **Yggdrasil III**. | ⚠️ **Amended** |
| V5-3 | Alphabetical sprints are replaced by **seven permanent concurrent programs** sequenced by **five arcs**. *(Drafted as "six" — corrected to seven at ratification.)* | ✅ **Ratified** |
| V5-4 | The ecosystem is **five planes with contract federation**; no plane imports another's source. | 🔓 **OPEN — deliberately.** Founder leans **four names: Tree · Heaven · Hell · Research**, with Skill Heaven as one package containing MCP + Skill Hell, and the Tree fanning out later (Canon Tree done; enterprise trees a packaged product). Kept flexible. See the note in §2. |
| V5-5 | The **benchmark floor stays doorless** (placebo-of-record); a **doorful product floor** ships and is priced as a separate arm. Closes ledger OPEN 4. | ✅ **Ratified as written.** Upstream ledger still owns final wording; the `floor` lexicon term splits in two. |
| V5-6 | PR #4 does **not** merge as framed; it is re-bound to live decisions with **D13 removed**, and its ratification delta lands in the same PR cycle (D9). | ✅ **Ratified as written** |
| V5-7 | Gaia MCP defines **two profiles over one package** — Registry/Bond and Heaven/Summon. Skill Heaven launches the minimal profile and measures its schema dose. | ✅ **Ratified as written.** Survives V5-4 either way. |
| V5-8 | The **federated lexicon** (six namespaces, one owner per term) is a v5 deliverable, and the `gaia.mcp` namespace is ruled **before** the MCP rebuild writes a tool definition. | ✅ **Ratified + escalated.** Full six-namespace migration lands in **Arc I**, not later. **`gaia.registry` REJECTED → renamed `gaia.skills`** (same ruling as #1258). **Two namespace HQs:** `gaia-research` holds `core` + `gaia.research` + `gaia.brand` + `gaia.heaven` + `gaia.mcp`; `gaia-skill-tree` holds `gaia.skills` + `gaia.trust`. No namespace files in `skill-heaven` or `gaia-mcp`. |
| V5-9 | **Enterprise, Prestige Index, Skill Groups + Named Badges** are deferred, not killed. | ✅ **Ratified as written.** Enterprise is **not discussed** in this public roadmap — no path, no mechanism, no motivation stated. Skill Hell is described only as a gated Heaven tier. |
| V5-10 | **Federation Invariants** replace Migration Invariants as the mandatory PR body section. | ✅ **Ratified + enforced.** A CI check makes the three-line block mandatory in every Gaia repo, the way branch-scope already is. Pairs with the lexicon gate install. |
| V5-11 | A **canonical ecosystem-level About / North Star surface** is created. It owns the *relationships*; `VISION.md`/`MISSION.md` remain Skill Heaven **line** docs, linked and never restated. | ✅ **Ratified.** **Canonical on Gaia Research**, mirrored as a prominent **pointer** from the Tree. It tells the **four-name** story (V5-4) and never names a repo or a package. |
| V5-12 | Post-Ygg-II remainder is **Program 5's opening work**, per the sprint-completeness rule — closed, not re-filed. | ✅ **Ratified as a background lane.** Nested orchestrator on `founder/BACKLOG_ERADICATION_TRACKER.md` → chained auto-Sonnet workers → **one large resumable PR** → **one founder review pass**. **#1001 (branch-aware TM rebuild) is excluded** — it ships August 2026 with **TM Index v2** and the meta audit. |
| V5-13 | The weekly report and benchmark leaderboard entrypoints are **re-enabled in Arc I** (#1130). | ✅ **Ratified as written** |
| V5-14 | **`@gaia-research/mcp` v0.1.0 is a prototype.** Program 4 is a **blank-canvas rebuild** — package name kept, implementation and tool vocabulary discarded. History preserved in git. | ✅ **Founder ruling, 2026-07-28** |
| V5-15 | **Adoption is a first-class surface**; Program 7 is **locked into Arc I**. | ✅ **Founder ruling, 2026-07-28** |
| V5-16 | **Change management is in scope** — a standing, versioned **What Changed** surface ships alongside the About surface. | ✅ **Founder ruling, 2026-07-28** |
| V5-17 | Every user-facing surface across the public repos is classified **canonical / pointer / retired**. | ✅ **Ratified, scoped.** **Arc I fixes only the four proven breaks** — #1130's disabled entrypoints, `skill-heaven`'s 404 VISION/MISSION badges, #1328's 14 stale MCP refs, #1258's "Gaia Registry" branding. The full classification audit is a **Program 7 background lane**, not an arc blocker. |
| V5-18 | **FACTUAL CORRECTION, not a new decision.** `@gaia-research/mcp` **v0.1.0 was published to npm on 2026-07-16**, twelve days before ratification. §4.1 recorded it as "not yet published"; that was wrong, and three downstream claims inherited the error. | ✅ **Founder correction, 2026-07-28** (caught by Marcus during Arc I dispatch). **V5-14 SURVIVES INTACT** — prototype status and the blank-canvas rebuild never depended on publication, and the **package name `@gaia-research/mcp` is the true name and is kept.** What breaks is only the *cost* reasoning: Program 4's "no migration debt / nothing installed anywhere" is **struck**, and "available exactly once because nothing is published" is **narrowed**. The `@gaia-registry/mcp-server` references in `docs/en/mcp-server.html` (#1328) were stale due to a **RENAME**, not non-publication — so #1328's suggested rename to `@gaia-research/mcp` was **correct**. Naming an already-published package in install documentation **does not close V5-4**; the no-package-names constraint governs the **About surface** (Program 7), not install docs for a shipped package. |
| V5-19 | **Final MCP tool names.** D4 ratified a ≤2-tool summon surface spelled `search_skills`/`summon`; the shipped prototype exposes `gaia_search`/`gaia_inspect`/`gaia_status` on a **published** package (V5-18). | ✅ **CLOSED — founder ruling, 2026-07-28. D4's direction stands: `search_skills`/`summon` is canonical. THE RENAME EXECUTES AT ARC III**, as part of Program 4's rebuild — **not before, and not as a side effect of lexicon work.** The `banned` entries landed in `gaia-research` PR #126 record **vocabulary intent**; they do **not** authorize changing the published surface. Until Arc III ships the rebuild, `@gaia-research/mcp` v0.1.0 keeps its shipped tool names and no Gaia surface may describe them as deprecated. **The migration story remains open** (§12) — deprecation window, aliases, or a clean break at 0.2.0 with a changelog entry. |
| V5-20 | **The Program 4 blank canvas is no longer blank.** V5-14 ruled Gaia MCP *rebuilt, not extended*, keeping only the package name — whose stated benefit was that "its vocabulary can be ruled by the lexicon *before* any of it ships." On 2026-08-07 a working summon engine landed on `gaia-mcp` `main`: install parity with `gaia install`, session-scoped GC with a liveness guard, a commit-addressed payload cache, tree-agnostic by construction, 27/27 tests. It is unpublished. | ✅ **Ruled 2026-08-07 by Marcus Tiongson.** **Today's engine is adopted as Program 4's starting canvas** rather than discarded. V5-14's rebuild-not-extend intent is *satisfied*, not overridden — the surface was rebuilt, just earlier than scheduled. **Consequence: V5-19's Arc III rename window opens NOW**, because the naming freeze existed only to protect a published interface and the new surface has not shipped. Every name on the summon surface is therefore in scope for the lexicon *before* 0.2.0 publishes, which is precisely the condition V5-14 was written to create. `@gaia-research/mcp` v0.1.0's three published tool names remain untouched until a deliberate migration ships. |

---

## 11. Carryover status from v4

| Deliverable | State |
|---|---|
| Trust Magnitude v1 | ✅ Live |
| Public Trust API v1 | ✅ Live |
| Trending engine + RSS | ✅ Live |
| Hall of Heroes | ✅ Live |
| Python + TS SDK | ✅ Live |
| OKF bundle | ✅ Live |
| Content Engine + weekly report | 🔶 Built (v4 Sprint D) — **homepage entrypoint disabled**, #1130 |
| Benchmark MVP + leaderboard | 🔶 Built (v4 Sprint D) — **homepage entrypoint disabled**, #1130 |
| Yggdrasil II (type/branch split, rank rename, Evidence Floor → TM) | ✅ Shipped — EPIC #1002 closed, #1185 merged, v7.1.5 |
| `claude-heaven` launcher slice | ✅ Merged (skill-heaven #3) |
| `@gaia-research/mcp` v0.1.0 Registry mode | ⛔ **Prototype — discarded.** Name kept, rebuilt blank-canvas (V5-14) |
| Gaia Ecosystem / About + adoption surface | ⏳ Program 7, Arc I (V5-15) |
| Standing **What Changed** surface | ⏳ Program 7, Arc I (V5-16) |
| `/skill-heaven` posture slider | 🔶 Draft PR #4 — reshaping required |
| HH ledger `v1` | 🔶 Emitting; freeze in Arc II |
| Trust Magnitude v-next (branch-aware) | ⏳ Program 5 (#1001) |
| Federated lexicon | ⏳ Program 2 (#1302) |
| MCP extraction from Skill Tree | ⏳ Program 4 (#1191) |
| `skill-trees/` extraction | ⏳ Program 5 (#1178) |
| Prestige Index | ⛔ Deferred |
| Skill Groups + Named Badges | ⛔ Deferred |
| React/Node monorepo migration | ⛔ **Retired** |
| Enterprise + Auth API | ⛔ Deferred |

---

## 12. Open questions

### Closed at ratification, 2026-07-28

1. ~~**Where does the ecosystem About surface physically live?**~~ → **Canonical on Gaia Research, mirrored as a prominent pointer from the Tree.** Research owns the org voice; the Tree keeps the traffic and links in. (V5-11)
2. ~~**Does `docs/about.html` stay the founder-story page?**~~ → **Yes, kept separate.** The ecosystem explainer goes at a new path. They serve different readers; merging dilutes both.
3. ~~**Lexicon seat of authority.**~~ → **Two HQs.** `gaia-research` holds `core` + `gaia.research` + `gaia.brand` + `gaia.heaven` + `gaia.mcp`; `gaia-skill-tree` holds `gaia.skills` + `gaia.trust`. Neither `skill-heaven` nor `gaia-mcp` holds namespace files. The extend-never-redefine mechanism already exists and has a working precedent. (V5-8)
4. ~~**How much of the MCP prototype is worth reading before discarding it?**~~ → **Harvest the 8 contract test files and `COMPATIBILITY.md`; discard the tool surface and the architecture.**
5. ~~**Skill Tree milestone mapping.**~~ → **New milestones, one per program.** Programs are permanent, so program-named milestones stay meaningful; arcs become a field on the org project board rather than a milestone.
6. ~~**Budget shape.**~~ → **Accepted at ~$184** after Program 5 was rescoped to a ~$20 maintenance lane (V5-2, V5-12). The freed ~$20 rolls into the arc cushion, not into scope.

### Still open

1. **V5-4 — how many planes, and what packages hold them.** Ruled open on purpose. The founder leans four names (Tree · Heaven · Hell · Research) with Skill Heaven as one package holding MCP and Skill Hell. **Nothing in Arc I depends on closing it** — Program 7 ships the four-name public story and never names a repo or package. Sub-decision, equally open: Program 4's destination (standalone `gaia-mcp` versus folded into the Heaven package).
2. **`hh-stamp/v1` acceptance threshold.** How repeatable must a result be before the Tree records it? "Sufficiently repeatable" needs a number **before Arc IV**. Not an Arc I blocker.
3. **Compaction survival (ledger OPEN 2).** Unmeasured. Needs a matrix gate before any load-bearing copy asserts it. Arc II.
4. **Migration story for the `@gaia-research/mcp` rebuild.** Follows from V5-18 and the now-closed V5-19: deprecation window, aliases, or a clean break at 0.2.0 with a changelog entry. Small at one published version — but it must be **chosen, not assumed away**. Needed **before Arc III executes the rename**; not an Arc I blocker.

---

*Drafted 2026-07-28, post-Yggdrasil II, at v7.1.5. **Ratified 2026-07-28** by Marcus Tiongson. `GAIA_ROADMAP v4 (BUILD).md` is archived to `founder/handovers/archive/roadmaps/`; `founder/CLAUDE.md`'s Key References table points here.*

*Arc I execution handover: [`founder/handovers/ARC_I.md`](handovers/ARC_I.md). Umbrella EPIC and per-repo sub-issues are tracked on the `gaia-research` org project board, filterable by **Program** and **Arc**.*
