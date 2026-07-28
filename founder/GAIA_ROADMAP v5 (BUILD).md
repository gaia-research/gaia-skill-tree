GAIA — Open Capability Control System for AI Agents

Version: 5.0

Status: **DRAFT — awaiting founder ratification**

Supersedes: `GAIA_ROADMAP v4 (BUILD).md` (to be archived on ratification)

Author: Orchestrator + Marcus Tiongson

Drafted: 2026-07-28 (post-Yggdrasil II, v7.1.5)

Ratified: —

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

2. **Skill Heaven enters the roadmap as the flagship program**, not as a satellite. It is the runtime layer: it decides which capabilities enter a session, at what dose, under what trust posture. The Tree answers *what exists and why trust it*; Skill Heaven answers *what should enter this context, right now*.

3. **Alphabetical sprints are replaced by permanent concurrent programs.** v4's B→D→C→E→F→G chain assumed one product and one work-front. There are now five products moving at once. Programs run continuously; **arcs** sequence the milestones that cut across them.

4. **The lexicon becomes load-bearing infrastructure, not documentation garnish.** With five repos and agent-authored change, semantic entropy is the primary failure mode. A federated lexicon with per-namespace ownership is a v5 deliverable, tracked at #1302.

5. **Enterprise, Prestige Index, and the Skill Groups ML program are deferred** — not killed. None of them currently pull demand, and two of them (Prestige, Skill Groups) are better informed by runtime evidence that does not exist yet.

6. **Every v5 claim is bound to a reproducible record.** v4's Migration Invariants block is replaced by **Federation Invariants**, which enforce contract versioning and evidence-before-claim across repo boundaries.

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

### Ownership, stated so it stops being re-litigated

**Gaia Research owns** the HH benchmark methodology, context-dose research, the harness capability matrix, negative findings, thought leadership, blog and SEO surfaces, experimental labs, benchmark ledgers, and the deliberately playful frontier of the brand. It is the organization, the laboratory, and the public intellectual voice. It is **not** a future destination for the Skill Tree website.

**Gaia Skill Tree owns** skill identity, content hashes, generic and Named records, attribution, Trust Magnitude, evidence, relationships and prerequisites, promotion and rank, public projections, and — after Arc IV — benchmark-earned HH stamps.

**Skill Heaven owns** the live session: launch posture, standing dose, which hand-curated skills enter, what can be summoned, how much can be admitted, whether a requested loadout exceeds the selected rung, and how one outcome maps onto different harness mechanics.

**Gaia MCP owns** transport compatibility, agent-oriented results, recommendation composition, approvals, and client diagnostics. It owns neither Registry truth nor benchmark truth — it consumes both.

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
| `@gaia-research/mcp` | **v0.1.0**, read-only Registry mode, implementation under review, **not yet published to npm** |
| Gaia MCP live tools | `gaia_search`, `gaia_inspect`, `gaia_status` |
| Legacy `packages/mcp` | Still in Skill Tree; extraction RFC open at **#1191** |
| Lexicon of record | Live in `gaia-research/founder/lexicon.json` (51 terms, namespace `core`, states `canonical`/`parked`/`banned`/`frozen`). Port RFC to Skill Tree open at **#1302** |
| HH ledger | `hh-ledger/v1` emitting; validator + append-only ledger of record in `gaia-research` |
| R0 dose census | Published (`content/reports/hh-benchmark/r0-census.md`) |

### 4.2 Divergences the founder analysis should absorb

**(a) PR #4 cites a retired decision — confirmed.** `RATIFICATION.md`'s header lists **D13** among "Retired ids — never reused," deleted 2026-07-24. PR #4's body binds itself to "D12, **D13**, P2, P3, D6." The PR is authority-stale. It must be re-bound before merge. This is exactly the failure D9 exists to prevent (*ratification and implementation land in the same PR*), which makes it a governance finding, not a code finding.

**(b) Product floor vs. benchmark floor is already ratified as OPEN, with the founder's proposal on the table.** Ledger OPEN item 4 reads: *"Suppressing slash commands at the deepest floor leaves it with no controls at all. Proposal: keep the doorless floor as the benchmark's placebo-of-record and ship a doorful product floor, priced as a separate arm."* v5 therefore does **not** invent this split — it **mandates closing it** and names the closure a gate on Arc I. PR #4's probe F7 already prices the door at **+515 tokens** (20,176 vs T9b's 19,661; still −28.9% off native's 28,379).

**(c) The `/skill-heaven` scope gap is already OPEN item 10.** The ledger records N8 as **CURRENT — INCOMPLETE**, covering "the moment of reach only," and names the four scenarios that surfaced in skill-heaven#4: posture adjustment, capability discovery, clean-room access, refusal transparency. v5 makes completing N8 a deliverable, not a discovery.

**(d) The two-MCP-profile problem is worse than a profile split — it is a name collision.** D4 ratifies a ≤2-tool summon surface spelled `search_skills` and `summon`. The shipped Registry surface is spelled `gaia_search` / `gaia_inspect` / `gaia_status`. Two different spellings for the same act of searching now exist across two ratified sources. **This is precisely the entropy the lexicon exists to prevent, and it has already happened.** v5 treats it as the first live test of the federated lexicon.

**(e) `VISION.md` and `MISSION.md` do not exist.** `skill-heaven/README.md` ships two public badges linking to `gaia-research/blob/main/VISION.md` and `MISSION.md`. Both return 404. The About/North-Star gap is not a nice-to-have — it is already a broken public surface.

**(f) v4's sprint ledger, honestly.** Sprint D (Content Engine + Benchmark MVP) closed 13 issues and is substantially landed. Sprints C and E were never opened as milestones. Sprint F is now cancelled. Sprint G is deferred. v5 does not inherit their numbering.

**(g) Two shipped surfaces are currently unreachable from the homepage.** #1130 records that the *Latest Weekly Report* and *Benchmarks Leaderboard* links in `docs/index.html` were temporarily disabled "until Epic 1002 is completed." **EPIC #1002 is now closed.** Both surfaces exist and render (`docs/reports/2026-28/`, `docs/benchmarks/{humaneval,mmlu}/`) — they simply have no way in. Under this repo's Design Entrypoints invariant, *shipping a section with no way to reach it from the homepage is a broken feature*. Re-enabling them is unblocked work, not future work, and it is the cheapest credibility win available to v5: the megaphone v4 built is currently muted.

---

## 5. The six programs

Programs are **permanent and concurrent**. Each has an owner plane, a standing goal, and kill criteria that can be checked on any given day.

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

**Federated namespaces** — one mega-file is explicitly rejected:

`gaia.registry` · `gaia.trust` · `gaia.heaven` · `gaia.mcp` · `gaia.research` · `gaia.brand`

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
- KC2: A CI gate rejects a PR that introduces a `banned` term or redefines a term it does not own
- KC3: The `search_skills`/`gaia_search` collision is closed by lexicon ruling, with the losing spelling marked `banned`
- KC4: An agent can determine, from the lexicon alone, whether a concept is ratified law or a point-in-time report

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

### Program 4 — MCP & Summoning

**Plane:** Transport · **Priority: resolve one architectural contradiction** · **Repo:** `gaia-mcp` (+ #1191 in Skill Tree)

**Standing goal:** a rich agent interface for deliberate Gaia interaction, without making every Skill Heaven session pay for all of it.

**The contradiction, precisely.** D4 caps the summon-side surface at ≤2 tools to protect the runtime context footprint. The standalone architecture defines a broader deliberate-interaction surface. **Neither is wrong — they serve different moments.** v5 resolves this by defining **two profiles over one package**:

| Profile | Tools | Purpose |
|---|---|---|
| **Registry / Bond** | search · inspect · workspace status · analyze project · plan path · (later) guarded install + Intake | Deliberate Gaia interaction |
| **Heaven / Summon** | search · summon | Low-overhead runtime admission |

Skill Heaven launches the **minimal** profile and **measures its schema dose** — D4's subtraction discipline applies to the profile actually loaded, not to the package's total surface.

**Skill Tree's half of the work is #1191** and is unchanged by this roadmap except in one respect: v5 explicitly ratifies the standalone MCP workstream that #1191 asks for. Extraction stays **parity-gated** — `packages/mcp` is not deleted until the standalone is published, clean-installable, contract-documented, link-migrated, and covered by a client-config migration test. The truthful-bridge obligation holds meanwhile: **no active surface may present an unpublished package as installable** (#1328 tracks 14 stale refs).

**Kill criteria**

- KC1: Both profiles are named in the lexicon and implemented by one package
- KC2: The Heaven profile's schema dose is measured and subtracted in every Heaven claim
- KC3: `@gaia-research/mcp` is published and installs clean from a fresh MCP client
- KC4: Every summon is content-hash pinned
- KC5: No public Skill Tree surface claims an unpublished package is installable
- KC6: `packages/mcp` is removed **only** after all #1191 migration gates pass

**Budget:** ~$26

---

### Program 5 — Gaia Skill Tree Core

**Plane:** Trust · **Priority: stability and routing-quality projections** · **Repo:** `gaia-skill-tree`

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
| #1202 | Built `gaia.json` is invalid against its own schema (`additionalProperties:false`) |
| #1201 | Live graph JSON `$schema` points at a dead path (404) |
| #1001 | Branch-aware TM formula rebuild (G8) — unblocked now that Ygg II has landed |

**5.3 Standing platform debt** — carried, not deferred: #1147 (DOM-XSS / `innerHTML` risks on static pages) · #1268 (frontend performance: DAG, Skill Explorer, page latency) · #1258 (branding: "Gaia Registry" is not the product name) · #1307 (`gaia install` conformance to the Agent Skills standard) · #1178 (RFC: extract `skill-trees/` — a **federation** move, not a migration).

**5.4 Deliberately *not* in Program 5:** the website does not move. There is no monorepo destination. `docs/` remains the Skill Tree's own served surface.

**Kill criteria**

- KC1: Every skill exposes a stable SkillRef + content hash that Skill Heaven can pin against
- KC2: A version handshake exists between Tree projections and both consumers (Heaven, MCP)
- KC3: Taxonomy logic has exactly one implementation, not three (#1231 closed)
- KC4: `gaia.json` validates against its own schema (#1202 closed)
- KC5: TM v-next is branch-aware and published with a reproducibility fingerprint (#1001)
- KC6: `gaia dev docs` output and the served Class S artifacts remain byte-consistent

**Budget:** ~$40

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

**Two immediate defects, both cheap and both currently costing credibility:**

- **The About / North Star gap.** `VISION.md` and `MISSION.md` are linked from `skill-heaven/README.md` and **do not exist** (§4.2e). The ecosystem now has five planes and no public page explaining how they relate. This is Program 6's opening deliverable.
- **The muted megaphone (#1130).** The *Latest Weekly Report* and *Benchmarks Leaderboard* homepage links were disabled pending EPIC #1002, which has now closed (§4.2g). v4's entire Sprint D thesis — *megaphone before medals* — is built and unreachable. Re-enable, verify the entrypoints render, and close #1130.

**Kill criteria**

- KC1: A public About / North Star surface explains the five planes and the compounding loop; `VISION.md` and `MISSION.md` resolve
- KC2: The weekly report and benchmark leaderboard are reachable from the homepage again; #1130 closed
- KC3: Every shipped Skill Heaven or HH result has a permanent, citable URL within one week of landing
- KC4: At least one published negative finding per arc
- KC5: The cadence is sustainable without orchestrator intervention on the mechanical steps

**Budget:** ~$22

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
- Stand up the About / North Star surface; fix the 404 badges
- Re-enable the weekly report + benchmark leaderboard entrypoints (#1130) — unblocked by EPIC #1002 closing

**Arc gate:** Skill Heaven v0.1 kill criteria KC1–KC9 pass, and no shipped Gaia surface is unreachable from its own homepage.

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
| 4 — MCP & Summoning | ~260k | ~$26 |
| 5 — Gaia Skill Tree Core | ~400k | ~$40 |
| 6 — Research, SEO & Thought Leadership | ~220k | ~$22 |
| **Total (Arcs I–IV horizon)** | **~1.70M** | **~$170** |

Arc V is unbudgeted by design — it opens only after the Claude prototype sings, and its scope depends on what Arcs I–IV learn.

Cushions: each program carries ~25–35% orchestration, review, and rework overhead. Unspent budget rolls into the next arc's cushion, **not** into scope expansion.

**Model routing:** splurge domains (contract schemas, HH methodology, routing determinism, floor-vs-floor ratification) → Opus at max effort. Balanced (lexicon porting, projection work, MCP profiles) → Opus high. Satisfice (docs, link migrations, test additions, CI YAML) → Sonnet. Auto-batchable (dependency bumps, mechanical renames) → Haiku with schema.

---

## 10. Decision log — v5 ratification

Entries marked **⚠ needs founder ruling** are drafted, not decided.

| # | Decision | Status |
|---|---|---|
| V5-1 | v4 Sprint F (migration + monorepo move) is **retired, not completed**. Gaia Research remains the laboratory and organizational centre. | ⚠ needs founder ruling |
| V5-2 | Skill Heaven is the **flagship program** of v5 and takes the centre. | ⚠ needs founder ruling |
| V5-3 | Alphabetical sprints are replaced by **six permanent concurrent programs** sequenced by **five arcs**. | ⚠ needs founder ruling |
| V5-4 | The ecosystem is **five planes with contract federation**; no plane imports another's source. | ⚠ needs founder ruling |
| V5-5 | The **benchmark floor stays doorless** (placebo-of-record); a **doorful product floor** ships and is priced as a separate arm. Closes ledger OPEN 4. | ⚠ needs founder ruling — *upstream ledger owns final wording* |
| V5-6 | PR #4 does **not** merge as framed; it is re-bound to live decisions with **D13 removed**, and its ratification delta lands in the same PR cycle (D9). | ⚠ needs founder ruling |
| V5-7 | Gaia MCP defines **two profiles over one package** — Registry/Bond and Heaven/Summon. Skill Heaven launches the minimal profile and measures its schema dose. | ⚠ needs founder ruling |
| V5-8 | The **federated lexicon** (six namespaces, one owner per term) is a v5 deliverable, and the `search_skills` ↔ `gaia_search` collision is its first ruling. | ⚠ needs founder ruling |
| V5-9 | **Enterprise, Prestige Index, Skill Groups + Named Badges** are deferred, not killed. | ⚠ needs founder ruling |
| V5-10 | **Federation Invariants** replace Migration Invariants as the mandatory PR body section. | ⚠ needs founder ruling |
| V5-11 | The **About / North Star surface** is Program 6's opening deliverable; `VISION.md` and `MISSION.md` must resolve. | ⚠ needs founder ruling |
| V5-13 | The weekly report and benchmark leaderboard entrypoints are **re-enabled in Arc I** (#1130) — their blocking condition (EPIC #1002) has closed. | ⚠ needs founder ruling |
| V5-12 | Post-Ygg-II remainder (#1230/#1231/#1264/#1174/#1202/#1201/#1001) is **Program 5's opening work**, per the sprint-completeness rule — closed, not re-filed. | ⚠ needs founder ruling |

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
| `@gaia-research/mcp` v0.1.0 Registry mode | 🔶 Implementation under review; **unpublished** |
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

## 12. Open questions for the founder

1. **Arc I scope.** Does the About / North Star surface belong in Arc I (it fixes a live 404 and explains a five-plane ecosystem nobody can currently read), or does it wait for Arc II so Arc I stays purely the Skill Heaven door?
2. **The name collision (§4.2d).** Which spelling wins — `search_skills` (D4, ratified) or `gaia_search` (shipped in v0.1)? The ratified name and the shipped name disagree, and the shipped one is already in agents' hands.
3. **Lexicon seat of authority.** Does the Skill Tree get its own `founder/lexicon.json` extending `gaia-research`'s `core` namespace, or does one lexicon live in `gaia-research` with the Skill Tree importing it? #1302 leaves this open.
4. **`hh-stamp/v1` acceptance threshold.** How repeatable must a result be before the Tree records it? "Sufficiently repeatable" needs a number before Arc IV.
5. **Skill Tree milestone mapping.** v5's programs do not map onto the existing milestones (Phase 2 — Product Moat, Phase 3 — Growth Engine). New milestones per program, or re-point the existing two?
6. **Budget shape.** ~$170 across Arcs I–IV vs. v4's ~$208 across six sprints. Comfortable, or should Program 5 (largest at ~$40) be trimmed in favour of Program 1?

---

*Drafted 2026-07-28, post-Yggdrasil II, at v7.1.5. Ratification pending. On ratification, `GAIA_ROADMAP v4 (BUILD).md` archives to `founder/handovers/archive/roadmaps/` and `founder/CLAUDE.md`'s Key References table updates to point here.*
