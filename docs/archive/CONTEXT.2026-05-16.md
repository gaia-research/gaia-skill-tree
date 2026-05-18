# Gaia

Gaia is an open, evidence-backed skill registry for AI agents. Capabilities are catalogued in a graph, awakened by real usage, and named to the contributor who first demonstrates them.

## Language

### Skill taxonomy (the categories)

**Basic Skill (○)**:
A primitive, indivisible capability — the genome of every agent.
_Avoid_: primitive, atomic skill.

**Extra Skill (◇)**:
A capability that emerges when two or more lower-tier skills fuse; can itself fuse with other **Extra Skills** to produce more complex Extras.
_Avoid_: composite skill, compound skill.

**Unique Skill (◉)**:
A graph-isolated **Basic Skill** that reached elite mastery through depth alone, with no fusion path forward.
_Avoid_: standalone skill, solo skill.

**Ultimate Skill (◆)**:
A high-complexity emergent capability found in fewer than 1% of agents — the apex tier.
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

**Rank up / Level up**:
Equivalent verbs for ascending one or more stars; both valid in copy and the CLI surface (`gaia promote`).
_Avoid_: upgrade, promote-up.

**Demote**:
The verb for dropping a skill back one or more stars when a demerit lands or evidence is retracted.
_Avoid_: downgrade, demote-down.

**Evidence Class**:
The independently graded quality of a real-world demonstration: Class C (first sighting), Class B (reproducible, documented), Class A (battle-tested, peer-reviewed).
_Avoid_: proof level, evidence tier.

### Contribution

**Named Skill**:
A canonical skill that has been claimed by a real contributor with Class C evidence or better; reaches 2★ at the moment of naming. Contributor names render in **honor red**.
_Avoid_: claimed skill, owned skill.

**Origin Contributor**:
The first contributor to successfully promote a skill into the canonical graph — their name attaches permanently.
_Avoid_: owner, author, creator.

**Promote**:
The CLI action (`gaia promote`) that ranks up a skill, gated by evidence. In the brand voice, **rank up** or **level up** are the visitor-facing verbs.
_Avoid_: lift, advance.

**Propose**:
The CLI action (`gaia propose`) that claims an unclaimed Ultimate skill by submitting an implementation for review.
_Avoid_: submit, request.

### Registry mechanics

**Registry**:
The canonical, maintainer-reviewed graph of all skills (`registry/gaia.json`). Public, versioned, evidence-backed.
_Avoid_: database, catalog, index.

**Intake**:
Draft skill batches submitted by `gaia push` and held in `registry-for-review/` until reviewed.
_Avoid_: queue, draft pool.

**Skill Tree**:
A user's personal projection of the registry, showing which skills they have demonstrated, at what stars, in which repository.
_Avoid_: profile, dashboard, scorecard.

## Relationships

- A **Basic Skill** fuses with other **Basic Skills** to produce an **Extra Skill**.
- An **Extra Skill** can fuse with other **Extra Skills** to produce a more complex **Extra Skill**, or chain into an **Ultimate Skill**.
- A **Unique Skill** is a **Basic Skill** that ranked up without ever fusing.
- A skill becomes a **Named Skill** at 2★, attaching it to its **Origin Contributor**.
- Every star above 1★ requires an **Evidence Class**; ranking up across stars gates on it.
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

**Rank up · Level up · Demote** — verified maturity moves on the stars axis (see domain section above).
**Name · Be named** — the moment a skill claims a contributor at 2★; uses honor red.
**Fuse** — combining skills (canonical, see domain section).
**Claim · Propose** — taking an unclaimed Ultimate (Claim = brand voice; Propose = CLI).
**Ascend** — reaching Apex (6★ Transcendent ★).
**Bond** — linking an agent to Gaia via MCP.
**Register** — first connecting a repo to Gaia via `gaia init`.
