# Gaia

Gaia is an open, evidence-backed skill registry for AI agents. Capabilities are catalogued in a graph, awakened by real usage, and named to the contributor who first demonstrates them.

_See also: `PRODUCT.md` for audience, product purpose, and the design-principle / anti-reference / accessibility baseline. `DESIGN.md` for visual tokens and motion specs._

## Language

### Skill taxonomy (the categories)

**Basic Skill (○)**:
A primitive, indivisible capability — the genome of every agent. In catalog section headers, write **Basics** verbatim.
_Avoid_: primitive, atomic skill, Atomic Basics, Unwired Basics, Pure / Undeveloped (as a section label — conflates the tier and stars axes).

**Extra Skill (◇)**:
A capability that emerges when two or more lower-tier skills fuse; can itself fuse with other **Extra Skills** to produce more complex Extras. In catalog section headers, write **Extras** verbatim.
_Avoid_: composite skill, compound skill.

**Unique Skill (◉)**:
A graph-isolated **Basic Skill** that reached elite mastery through depth alone, with no fusion path forward. In catalog section headers, write **Uniques** verbatim.
_Avoid_: standalone skill, solo skill, graph-isolated singularities.

**Ultimate Skill (◆)**:
A high-complexity emergent capability found in fewer than 1% of agents — the apex tier. In catalog section headers, write **Ultimates** verbatim.
_Avoid_: legendary skill, top-tier skill, mythic.

**Fusion**:
The act of combining two or more skills into a single higher-complexity skill, formalised in the registry via `gaia fuse`. Basics can fuse into Extras or Ultimates; Extras can fuse with other Extras.
_Avoid_: combination, merge, composition.

### Maturity (the level)

**Stars**:
A skill's verified maturity on a 0★ to 6★ axis, derived from evidence — never declared. Use "stars" for the axis itself.
_Avoid_: rank (the axis), level (the axis), tier (tier means the taxonomy above).

**Rank**:
The named label for a specific star value, valid only when paired with the name. Examples: "the Hardened rank", "Transcendent rank". Never used as the axis name.
_Avoid_: using "rank" alone to mean stars; using "rank" as a verb (the verb is rank up).

The rank names, in order: **Unawakened** (0★), **Awakened** (1★), **Named** (2★), **Evolved** (3★), **Hardened** (4★), **Transcendent** (5★), **Transcendent ★** (6★ apex).

**Apex**:
Brand-voice shorthand for the **Transcendent ★** rank (6★). Pair with the rank symbol on first mention on a surface (e.g. `6★ Apex`); the bare word is reserved for hero / ceremonial copy and section endpoints (e.g. the Ascension Cycle terminus). Long-form documentation uses **Transcendent ★** in full; compact CLI plaques and home-page affordances may use **Apex** alone.
_Avoid_: using "Apex" for any rank below 6★; using "apex tier" as a synonym for "Ultimate tier" (Apex is a stars-axis word, Ultimate is a taxonomy-axis word).

**Pure**:
Alternative descriptor for the Unawakened (0★) rank — used as a per-skill pill (e.g. `[0★ · Pure]` in tree renders) where a 0★ skill needs a one-word label distinct from "Unawakened." Strictly a stars-axis term; never used as a section header or as a tier synonym.
_Avoid_: "Pure skill" to mean a Basic-tier skill; "Pure / Undeveloped" as a section header (conflates the tier and stars axes).

**Rank up / Level up**:
Equivalent verbs for ascending one or more stars; both valid in copy and the CLI surface (`gaia promote`).
_Avoid_: upgrade, promote-up.

**Demote**:
The verb for dropping a skill back one or more stars when a demerit lands or evidence is retracted.
_Avoid_: downgrade, demote-down.

**Evidence Class** _(deprecated — see Evidence Type + Evidence Grade)_:
The legacy single axis that conflated *provenance* and *quality* into one letter: Class C (first sighting), Class B (reproducible, documented), Class A (battle-tested, peer-reviewed). Superseded under the #646 trust model by **Evidence Type** (where a demonstration came from) plus **Evidence Grade** (how strong it is). The field stays valid in the schema until the next major release, then is removed; new evidence should carry a Type and a Grade instead. **Warning:** Class A/B are *not* Grade A/B — never read one axis as the other.
_Avoid_: proof level, evidence tier; using Class for new evidence; equating Class letters with Grade letters.

### Evidence and trust (the trust model)

The #646 trust model splits the old single `class` letter into two orthogonal axes — **Evidence Type** (provenance) and **Evidence Grade** (quality) — and adds the skill-level **Overall Trust Grade**. These materialise in generated catalogs; they are computed by the build pipeline, never declared.

**Evidence Type**:
The provenance of one demonstration — *where* it comes from, not how good it is. Values are kebab-case and list-driven from `meta.json` `evidence.types` (initially `arxiv`, `repo`, `github-stars`), so new sources extend the list without a schema change. Always write the full phrase "Evidence Type"; never the bare word "type", which names the Basic/Extra/Unique/Ultimate taxonomy field.
_Avoid_: reusing **Evidence Class** for provenance; "source class"; the bare "type" for provenance.

**Evidence Grade**:
The quality of one demonstration on an **S / A / B / C** axis — Platinum (S), Gold (A), Silver (B), Bronze (C) — derived from its **trust number**. A demonstration whose trust number falls below the C threshold is **ungraded**: on the record but counting toward no gate. The grade letters are deliberately distinct from the deprecated **Evidence Class** letters — Grade A ≠ Class A.
_Avoid_: equating Grade A/B with Class A/B; "evidence tier"; "proof grade".

**trust number**:
The internal 0–100 score an **Evidence Grade** derives from, via `meta.json` `evidence.gradeThresholds` (S ≥ 90, A ≥ 80, B ≥ 60, C ≥ 40, ungraded < 40). An input to grading, **not user-facing** — surfaces show the grade it yields, never the raw number.
_Avoid_: showing the trust number in copy; "trust score" (the term is "trust number").

**Overall Trust Grade**:
A skill's *aggregate* standing — the accumulation of its individual **Evidence Grades** that establishes the capability "beyond reasonable doubt." Computed from the evidence inventory at build time and **never stored in a node** (Programmatic-First); it materialises only in generated catalogs (`named-skills.json`, `docs/graph/gaia.json`). Distinct from a single demonstration's **Evidence Grade**.
_Avoid_: storing it on a node; conflating it with one entry's Evidence Grade; "trust rating".

**rank tenure**:
How long a skill has held its current stars, derived from its timeline `rank_up` / `demote` events and rendered as "held the *[rank name]* rank since *[date]*." Computed, never stored. In copy always pair the word "rank" with the rank name (e.g. "the Hardened rank since 2026-03-01"); never write "rank" alone to mean the stars axis.
_Avoid_: "rank since" with no rank name; storing tenure on a node; "rank age".

**Verification levels**:
The states an evidence entry passes through, orthogonal to its grade: **unverified** (default), **verified** (confirmed by a 4★+ **Verifier**; `evidence.verified: true`), and **disputed** (`evidence.disputed: true`). Verification attests that a demonstration is *real*; grading measures how *strong* it is — the two never substitute for each other.
_Avoid_: treating "verified" as a grade; "verification stars" (verification is not on the stars axis).

### Rarity (the third axis — REMOVED)

**Rarity** was a legacy schema-defined axis on a scale of **common → uncommon → rare → epic → legendary**. It was originally intended as a third orthogonal axis alongside **tier** (Basic / Extra / Unique / Ultimate) and **stars** (0★–6★), but in practice it duplicated signal already carried by the other two axes and was never surfaced to users.

**Status: removed.** The field is gone from the schemas (`skill.schema.json`, `skillTree.schema.json`, `meta.json`), from every registry node and skill tree, from the generated mirrors, and from all CLI/MCP code paths (issue #356). Historical references survive only in `docs/archive/`, dated meta reports, and this notice. CI (`docs-cohesion.yml` Guard B) fails any new code-level rarity reference.

_Avoid_: introducing **any** new reference to rarity — in CLI output, docs, agent skills, review tables, or curation workflows. If you find yourself reaching for the word, you almost certainly want **tier** or **stars** instead.

### Contribution

**Named Skill**:
A canonical skill that has been claimed by a real contributor with Class C evidence or better; reaches 2★ at the moment of naming. Contributor names render in **honor red**.
_Avoid_: claimed skill, owned skill.

**Origin Contributor**:
The first contributor to successfully promote a skill into the canonical graph — their name attaches permanently.
_Avoid_: owner, author, creator.

**Named Contributors**:
The collective noun for contributors who hold one or more Named Skills — used as a page-level heading (e.g. on the Hunter's Atlas) and in product copy when referring to the cohort. Per-skill attribution remains **Origin Contributor**; one Origin Contributor per skill, many Named Contributors across the registry.
_Avoid_: claimers, owners list, top namers, leaderboard.

**Promote**:
The CLI action (`gaia promote`) that ranks up a skill, gated by evidence. In the brand voice, **rank up** or **level up** are the visitor-facing verbs.
_Avoid_: lift, advance.

**Propose**:
The CLI action (`gaia propose`) that claims an unclaimed Ultimate skill by submitting an implementation for review.
_Avoid_: submit, request.

### Registry mechanics

**Starless**:
The collective term for generic skill references — rank-less taxonomy nodes that carry no stars of their own. Stars belong only to a starless ref's named-skill implementations (its "children"); a starless ref's *effective rank* is the top star among its named variants. A starless ref also holds the shared, capability-level (Class A / academic) evidence pool that every named child inherits; named skills add their own implementation-specific evidence on top. Whenever a starless reference is shown in UI or copy it renders as *generic* in italic, greyed-out styling — "generic" is retained as the technical descriptor, "starless" is the brand / collective noun.
_Avoid_: giving a generic skill reference its own stars, level, or tier; "leveled generic", "ranked reference".

**Registry**:
The canonical, maintainer-reviewed graph of all skills (`registry/gaia.json`). Public, versioned, evidence-backed.
_Avoid_: database, catalog, index.

**Intake**:
Draft skill batches submitted by `gaia push` and held in `registry-for-review/` until reviewed.
_Avoid_: queue, draft pool.

**Skill Tree**:
A user's personal projection of the registry, showing which skills they have demonstrated, at what stars, in which repository.
_Avoid_: profile, dashboard, scorecard.

### Registry Management

**Programmatic-First Policy**:
The Gaia registry is programmatically managed. Manual edits to JSON files in `registry/nodes/` are deprecated for all meta-shifts. AI agents and human contributors must use the Gaia CLI to ensure timeline logging, timestamping, and schema integrity.

- **Merge**: Use `gaia dev merge` to fuse canonical nodes.
- **Split**: Use `gaia dev split` to divide capabilities.
- **Add**: Use `gaia dev add` to create new canonical or named skills.
- **Evidence**: Use `gaia dev evidence` to support rank-up claims.
- **Assemble**: The `registry/gaia.json` file is a generated artifact; never edit it.

_Avoid_: manual JSON patching, direct `gaia.json` edits, untracked schema shifts.

**Transparency Mandate** (the other half of Programmatic-First):
**Every event is on the record.** No rank change — demotion, promotion, fusion,
or evidence update — may be untracked; each must leave an auditable **timeline
event** so a skill's history tells the whole truth. A demotion that silently
lowers a star without a `demote` event is a transparency failure, not a cosmetic
one. This is a *mindset*, not just a rule: prefer the CLI precisely because it
logs the event for you, and never hand-lower a level without recording why. The
**Transparency Gate** (`scripts/validate_timelines.py`, run in `gaia validate`
and release CI) enforces it — every user-tree timeline must explain its skill's
current rank, or the build fails.

## Relationships

- A **Basic Skill** fuses with other **Basic Skills** to produce an **Extra Skill**.
- An **Extra Skill** can fuse with other **Extra Skills** to produce a more complex **Extra Skill**, or chain into an **Ultimate Skill**.
- A **Unique Skill** is a **Basic Skill** that ranked up without ever fusing.
- A skill becomes a **Named Skill** at 2★, attaching it to its **Origin Contributor**.
- Every star above 1★ requires graded evidence — an **Evidence Grade** (the **Evidence Class** axis it replaces is deprecated); ranking up across stars gates on it.
- The **Registry** is the canonical graph; a **Skill Tree** is one user's view of that graph.

## Example dialogue

> **Dev:** "Karpathy demonstrated `/autoresearch` — does that make it a Named Skill?"
> **Maintainer:** "It does, but only after `gaia propose` lands with Class C evidence or stronger. Until then it sits in **Intake**. Once accepted, Karpathy becomes the **Origin Contributor** and the skill ranks up to **Named** (2★)."
> **Dev:** "And if `/autoresearch` is an Ultimate, the same contributor stays attached as it climbs?"
> **Maintainer:** "Yes — Origin sticks for the life of the skill, even at 6★."
> **Dev:** "Can two Extra Skills fuse into a new Extra?"
> **Maintainer:** "They can. Fusion isn't restricted to Basics-only; an Extra can compose with another Extra and still land as an Extra if it doesn't cross the Ultimate complexity bar."

## Flagged ambiguities

- "Rank" was used loosely as both the axis name and the label name. Resolved: **stars** is the axis (0★–6★); **rank** is only valid as a noun paired with the rank name (e.g. "the Hardened rank").
- "Level" was used loosely for both stars and the taxonomic categories (Basic/Extra/Unique/Ultimate). Resolved: stars is the maturity axis; **tier** or the specific category name (Basic/Extra/Unique/Ultimate) is the taxonomy axis. "Level up" as a verb is fine and is synonymous with **rank up**.
- "Claim" is the brand-voice verb a visitor sees; **Propose** is the canonical CLI command beneath it. The two refer to the same action against an unclaimed Ultimate.

---

## Brand voice

> _Evidence. Permanence. Craft._

These terms govern public surface copy and visual nomenclature on the Hunter's Atlas redesign. They sit on top of the domain glossary above — never replacing canonical terms, only adding fantasy-register synonyms where they carry voice.

### Lane and stance

**Hunter's Atlas**:
The working name for the Gaia visual design lane — a sacred-atlas × Solo-Leveling guild-registry stance. Carries ledger-faithful seriousness in typography and ceremoniousness in motion; carries main-character-energy through verbs around honors.
_Avoid_: Pokédex, RPG site, game UI, anime UI.

**Half-Merged Voice**:
The brand-voice register chosen for Hunter's Atlas — truthful primary labels (Registry, Skill Tree, Contributors) carry the page; fantasy verbs (claim, ascend, name, fuse, bond) and ornamental section titles (Hall of Heroes, Initiate's Rite, Ascension Cycle, The Codex) carry the swagger.
_Avoid_: Overt guild voice (over-commits to fantasy), Atlas-mostly voice (under-commits).

### Brand-color roles (sit on top of DESIGN.md tier/rank tokens)

**Honor Red**:
The role token for contributor handles wherever they appear (`#ef4444`). The single most load-bearing brand-accent color besides apex gold. Never used decoratively.
_Avoid_: contributor red, name red.

**Apex Gold**:
The role token for the 6★ Transcendent ★ tier, Ultimate accent moments, the Diamond Seal mark, and other apex affordances (`#fbbf24`, deepening to `hsl(45,100%,45%)` at fringes per `drawNodeVI`). Never used as a decorative accent on lower tiers.
_Avoid_: Ultimate gold, accent gold.

### Nomenclature decisions

**Registry vs. HUD**:
"Registry" is the canonical user-facing label for the public skill graph and any view of it (nav anchor, dialog title, copy). "HUD" is **internal-only** — retained as a synonym in code (`hud-toggle.js`, `hud-trigger` CSS class, internal docs) but never surfaced in UI copy. When the visitor flips the hero into the immersive constellation/canvas mode, the toggle is labelled **Field view** (chip: `⇄ Field view`), not "HUD". The two terms are interchangeable in commit messages and source comments; only "Registry" / "Field view" appear in user-visible copy.
_Avoid_: "View as HUD", "HUD mode", "Heads-up display" in user-facing text.

### Surfaces

**The Diamond Seal**:
The brand mark — a diamond outline framing a serif "G". Used in nav, favicon, OG cards, and at the centre of every plaque. Distinct from the apex tier glyph ◆ (the seal is rotated to square-on-point and contains a letterform).
_Avoid_: the logo, the icon (use "the mark" or "the Diamond Seal").

**Hall of Heroes**:
The public-facing section showcasing the top contributors and their named skills. Ranks contributors by stars then origin date. Renders one plaque per featured contributor.
_Avoid_: Top contributors, Named contributors section.

**The Initiate's Rite**:
The three-command setup flow (`pip install gaia-cli` → `gaia init` → `gaia scan`) styled as a ceremonial inscription rather than a how-to. Lives in Path A of the Two Doors home.
_Avoid_: Get started, Quickstart, Onboarding.

**Bond your agent**:
The brand-voice label for the MCP-install moment, where a contributor's AI agent links to the Gaia registry.
_Avoid_: Connect MCP, Add Gaia to your agent.

**Available Ultimates**:
The list of unclaimed Ultimate skills shown in Path B of the Two Doors home. Each row carries the tier glow on hover and a `Claim →` action.
_Avoid_: Open Ultimates, Unclaimed Ultimates (acceptable; less preferred), Ultimate marketplace.

**Ascension Cycle**:
The lifecycle diagram showing how a contributor's skill travels from Register → Scan → Rank up → Name → Fuse → Apex. Replaces the old "Skill Lifecycle" arrow flow.
_Avoid_: Skill lifecycle, Progression flow, Workflow.

**The Codex**:
The renamed `how-we-do-things.html` companion page — long-form documentation of governance, evidence policy, and contribution rules. Reskinned in Scholar's Plate.
_Avoid_: How We Work, How we do things, Documentation.

**Your Tree**:
The visitor's personal skill-tree projection (canonical term **Skill Tree**; "Your Tree" is its second-person label in nav and dialogs).
_Avoid_: My Tree, Profile, Dashboard.

### Render-artifact names (exact spelling and capitalisation)

These are the user-facing names for every render output. Copy must match verbatim; the `## Banned synonyms` section below lists every drift to avoid.

| Artifact | Canonical name | Definition |
|---|---|---|
| Public registry surface as a whole | **Hunter's Atlas** | The whole site experience. Short form "Atlas" only in nav / subheaders. |
| Canonical 3D view (button + data) | **Registry** | The button label that opens the 3D canvas, and the data layer (`registry/gaia.json`). Not a synonym for Atlas. |
| Full-viewport overlay of the Registry | **Field view** | The toggle label (`⇄ Field view` / `⇄ Exit field`). "HUD" is internal-only (code class names like `.hud-trigger`, files like `hud-toggle.js`) and never surfaces in copy. |
| Markdown projection of the graph | **Tree** | The downloadable `tree.md` and per-user `skill-tree.md`. The DAG view inside the Named Skills Explorer is qualified as **"Tree view"** to avoid collision. |
| Home-page top-contributor track | **Hall of Heroes** | Horizontal scroller of plaques. |
| Home-page 0★→6★ journey diagram | **Ascension Cycle** | The one catalog-shaped surface that intentionally reads ascending (low-to-high). Carries `data-pattern="journey"` so future linters don't auto-flip its direction. |
| Long-form reference page | **The Codex** | `/codex.html`. |
| Browse-all named-skills section | **Named Skills Explorer** | Filterable surface on the home page with three view modes: **Tile / List / Tree**. |
| Card-shaped skill render | **Plaque** | Variants: `--mini` (HoH track), `--tile` (explorer grid), `--row` (explorer list), `--detail` (modal hero), `--settled` (profile trophy), `--og` (1200×630 social card). |
| Personal projection of the Registry | **Skill Tree** (or **Your Tree** in second-person copy) | Already defined above; cross-listed here for completeness. |

### Artifacts

**The Plaque**:
The evidence-based visual artifact a contributor earns when a skill is named. Renders in three priority modes — **Priority D** the animated naming reveal (plays once when a skill is named, settles into a static plate), **Priority B** the contributor profile page surface, **Priority C** the OG share card. All three are one design language at different resolutions and motion states.
_Avoid_: badge (specifically misleading — README badges were dropped from scope), card, trophy.

**The Naming Reveal**:
Priority D of the plaque — the moment of being named, rendered as a Solo-Leveling-style ascension cinematic: graph zooms to the node, gold ink pours into engraving, contributor handle resolves in honor red, stars ignite one at a time, settles into a static plate.
_Avoid_: Award animation, Level-up animation.

**Two Doors**:
The home-page IA pattern — a forked CTA pair ("Register your repo →" / "Claim an Ultimate ◆") that splits the page into two parallel path columns reconverging at Hall of Heroes. The visitor picks a door within 10 seconds; both lead to the canonical registry.
_Avoid_: Dual CTA, A/B paths.

### Verbs (use in copy)

| Verb | Brand-voice gloss | CLI equivalent |
|---|---|---|
| **Rank up · Level up** | Ascend one or more stars on the verified-maturity axis | `gaia promote` |
| **Demote** | Drop a skill back one or more stars (demerit or retracted evidence) | (no CLI verb yet) |
| **Name · Be named** | The 2★ moment a skill claims its Origin Contributor; uses honor red | `gaia push` (when accepted) |
| **Fuse** | Combine two or more skills into a higher-complexity skill | `gaia fuse` |
| **Claim · Propose** | Take an unclaimed Ultimate (Claim = brand voice; Propose = CLI) | `gaia propose` |
| **Ascend** | Reach Apex (6★ Transcendent ★) | (no CLI verb — emerges from `gaia promote` reaching 6★) |
| **Bond** | Link an AI agent to Gaia via MCP | `gaia mcp` install flow |
| **Register** | First connect a repo to Gaia | `gaia init` |
| **Scan** | Detect demonstrated skills in a repo | `gaia scan` |
| **Install** | Add a Named Skill to a local skills directory | `gaia install` / `gaia skills install` |
| **Open** | Reveal an artifact (the Registry, the Tree, a Plaque) | (UI-only verb; no CLI equivalent) |

## Codebase Architecture

The codebase is structured as a polyglot monorepo containing multiple key contexts, separating core database operations (Registry and Python CLI) from client integrations (npm CLI wrapper and the stdio Model Context Protocol server).

For a detailed folder-by-folder mapping of components, boundaries, and scopes, refer to the [CONTEXT-MAP.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/CONTEXT-MAP.md) at the root of the project.

### Core CLI Design
The Python core CLI (`gaia`) leverages a dynamic command discovery system. Instead of maintaining a monolithic dispatch file, individual subcommands (like `init`, `scan`, `install`, and `dev`) are isolated modules inheriting from a shared `Command` contract.

Mutating registry operations are grouped within the developer subpackage `gaia_cli.commands.dev/` (`evidence`, `verify`, `merge`, `rename`, `calibrate`, `list`, `build`, `audit`, `timeline`, `named`).

### Generated Artifacts (Class P / Class S)

The codebase produces two categorically different classes of generated files; the distinction governs storage policy.

**Class P (pipeline-internal artifacts):**
Regenerated from `registry/nodes/` + `registry/named/` by `gaia dev docs`. Consumed by Python tooling and the wheel-build pipeline; never served to a browser at runtime. Members: `registry/gaia.json`, `registry/named-skills.json`, `registry/gaia.gexf`, `registry/gaia.svg`, `registry/layouts_3d.json`, `registry/real-skills.{json,md}`, `base_gaia.json`, and the bundled snapshot under `src/gaia_cli/data/registry/`. Storage: **gitignored**. Bundled into PyPI wheels at vX.Y.0 minor releases via the "Bundle fresh registry snapshot" step in `publish-pypi.yml`.

_Avoid_: tracking Class P in git (manufactures merge conflicts on every PR touching source); editing Class P by hand (always derived).

**Class S (site-served artifacts):**
Files inside `docs/` that browsers fetch at runtime or that GitHub Pages serves as downloads. Members include the four graph mirrors under `docs/graph/` (`gaia.json`, `named/index.json`, `gaia.gexf`, `gaia.svg`) alongside the regular content files (`docs/**/*.html`, `docs/css/*`, `docs/js/*`, `docs/og/*`). Storage: **tracked in git.** The deploy substrate is git → GitHub Pages → `gaia.tiongson.co` from `main:/docs`; whatever lives there at any moment IS the live website.

_Avoid_: gitignoring Class S (deletes the live site at next Pages publish); editing the graph mirrors by hand (regenerated; hand-edits get overwritten on next `gaia dev docs`).

**Rule of thumb:** if browsers fetch the file at runtime, it's Class S. If only `gaia` tooling reads it, it's Class P.

### MCP Server Management
The Model Context Protocol (MCP) server enables AI agents (such as Claude Code and Cursor) to interact with the registry. It supports:
- **Daemonization:** Running in the background detached via a lightweight Node.js daemon process manager (`daemon.ts`) controlled via `~/.gaia/mcp.pid`.
- **Configuration Merger:** Gracefully merging system-wide configuration (`~/.mcp.json`) and local directory config (`./.mcp.json`) with local overrides.

---

## Release Channels

Gaia ships on three channels, derived automatically from the Conventional-Commit
type of each merge to `main`. The version bump determines the channel:

| Channel | Bump | Trigger (merge commit) | Where it lands |
|---|---|---|---|
| **Production** | major | `feat!:` / `fix!:` / `BREAKING CHANGE` | GitHub Release (marked **latest**) **and published to PyPI** |
| **Beta** | minor | `feat:` | GitHub **pre-release** only |
| **Canary** | patch | anything else (`fix:`, `chore:`, `docs:`, …) | GitHub **pre-release** only |

- **PyPI is production-only.** `pip install gaia-cli` always resolves to the
  latest **Production** (major) release. Beta and canary are installable from
  their git tag/source but never reach PyPI by default.
- The channel is decided in `.github/workflows/sync-artifacts.yml` (every merge
  to `main` bumps, tags, and creates a channel-labelled GitHub Release). Production
  merges additionally dispatch `publish-pypi.yml`.
- **Manual publish:** Actions → *Publish gaia-cli to PyPI* → Run workflow, picking
  the branch **or tag** to build from (publishes whatever version is in
  `pyproject.toml` at that ref; idempotent via `skip-existing`).
- Because the channel keys off the **merge commit message**, only a breaking-change
  commit (`!:` or `BREAKING CHANGE`) cuts a Production/PyPI release. Use `feat:` for
  Beta and ordinary types for Canary.

Copy rules: write the channel names capitalised — **Production**, **Beta**,
**Canary**. Do not coin synonyms (`stable`, `nightly`, `edge`, `RC`).

---

## Banned synonyms

Single source of truth for CI grep. Any term below appearing in user-facing copy (`docs/**.html`, `docs/js/`, `docs/css/`, generated artifacts under `docs/`, `scripts/generate*.py`, `src/gaia_cli/`) fails the lint. Alphabetised.

- `apex tier` (as Ultimate-tier synonym) — Apex is a stars-axis word; use **Ultimate** for the taxonomy or **Apex** only when meaning 6★ Transcendent ★
- `Atomic Basics` — section label; use **Basics**
- `Atomic skill` / `atomic skill` — tier synonym; use **Basic Skill**
- `card` — for plaque; use **Plaque**
- `claimers` — collective noun for contributors; use **Named Contributors**
- `claimed skill` — use **Named Skill**
- `common` — never a **tier** or **rank** name (it was a rarity-axis value; see Rarity section above — never surfaced in user-facing copy)
- `composite skill` / `compound skill` — for Extra; use **Extra Skill**
- `Connect MCP` / `Add Gaia to your agent` — MCP install copy; use **Bond your agent**
- `dashboard` / `profile` (as skill-tree synonym) — use **Skill Tree** or **Your Tree**
- `database` / `catalog` / `index` — for Registry; use **Registry**
- `Documentation` / `How we do things` / `How We Work` — page name; use **The Codex**
- `Field view` is the **only** user-facing label for the immersive canvas toggle — banned alternatives: `View as HUD`, `HUD mode`, `Heads-up display`, `Open HUD`, `Constellation view`
- `Get started` / `Quickstart` / `Onboarding` — setup copy; use **The Initiate's Rite**
- `graph-isolated singularities` — for Unique section; use **Uniques**
- `Highest Tier: common` — broken stat label; emit the rank name or `—`
- `legendary` / `legendary skill` — banned synonym for **Ultimate** tier (it was a rarity-axis value; the axis is removed)
- `leaderboard` (as Hall-of-Heroes synonym) — use **Hall of Heroes**
- `Level lifecycle` / `Progression flow` / `Workflow` — diagram name; use **Ascension Cycle**
- `mythic` — banned synonym for Ultimate
- `owners list` — collective; use **Named Contributors**
- `owner` / `author` / `creator` — for Origin Contributor; use **Origin Contributor**
- `Pokédex` / `RPG site` / `game UI` / `anime UI` — brand-stance violations
- `primitive` — for Basic Skill; use **Basic Skill**
- `Pure / Undeveloped` — section label that conflates tier and stars axes; section header is **Basics**, and a 0★ skill can carry the **Pure** pill inline
- `Pure skill` — as tier synonym; "Pure" is only a 0★ stars-axis descriptor
- `rank` / `level` / `tier` — when used alone to mean the **stars axis** (these are reserved for the rank-name label, the verbs, and the tier taxonomy respectively)
- `rarity` / `Rarity` / `rare` / `epic` / `uncommon` — the rarity axis is removed (see Rarity section above). Do not introduce new references in CLI copy, docs, agent skills, or curation workflows.
- `Skill lifecycle` — diagram name; use **Ascension Cycle**
- `standalone skill` / `solo skill` — for Unique; use **Unique Skill**
- `Top contributors` / `Named contributors section` — section; use **Hall of Heroes**
- `top namers` — collective; use **Named Contributors**
- `top-tier skill` — banned synonym for Ultimate
- `trophy` (as plaque synonym in copy) — use **Plaque**
- `Undeveloped` — pejorative; not in vocabulary
- `Unwired Basics` — section label; use **Basics**
- `upgrade` / `promote-up` — for rank-up verb; use **Rank up** or **Level up**
