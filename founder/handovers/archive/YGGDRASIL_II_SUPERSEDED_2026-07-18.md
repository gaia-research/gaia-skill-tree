# Yggdrasil II — Superseded Ratification Claims (archived 2026-07-18)

**Status:** ARCHIVE / audit record. Nothing in this file is live guidance.
**Supersedes source:** claims that conflict with the **v3 Amendment (2026-07-18)** at the top of
`founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md`, confirmed against the landed
implementation (PR chain **#1232 → #1233 → #1234**) and the live named-skill data.

## Why this file exists

The v3 Amendment plus the #1232–1234 PR chain locked the **final shape** of the Yggdrasil II
taxonomy model. Two earlier framings in the ratification lineage are now WRONG and were archived
here so the live docs carry only the correct shape. Each superseded passage is quoted verbatim
below (with its source file + line reference at the time of archiving), followed by the correction
and the reason.

### The final shape (what is TRUE as of 2026-07-18)

1. **Membership is `suiteComponents`-first, from ANY rank.** A skill with `suiteComponents`
   is `suite` at any rank (verified: suites exist at 3★ in the landed data; the membership
   floor is the 2★ push floor, not 4★). No `suiteComponents` + rank 1–3 → `standard`;
   no `suiteComponents` + rank 4–6 → `unique`. Membership holds from low ranks up — it is
   NOT gated at 4★.
2. **Only the DECORATION forks at 4★+.** The ladder words
   (Extra / Ultimate / Apex on the suite branch · Unique / Unique Ultimate / Unique Impossible
   on the unique branch) and the prestige glyph / medallion / color render ONLY at 4★+.
   A 2★/3★ suite shows the shared word (Named / Evolved) + the plain glyph. (This decoration
   statement — including v2's decision to DROP the deprecated Ygg-I 5★ rank word in favor of
   Ultimate / Unique Ultimate — was CORRECT in v2
   and remains live; only the *membership-floor* framing around it was wrong.)
3. **Named-entry axes are emitted at BUILD time.** `branch` / `rank` / `rankWord` / `medallion` /
   `contractVersion` are resolved at build time by `src/gaia_cli/taxonomy.py` and written onto
   every named entry; consumers READ them. The earlier "derived / computed at read-time"
   framing is superseded (except for the starless graph — see §5).

---

## 1. v2 Amendment — membership-floor claims (the "fork begins only at 4★" framing)

**Source:** `founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md`

### 1a. L65 — "recognised ONLY at 4★+"

> Original (verbatim):
> "**The unique↔suite fork is recognised ONLY at 4★+.** At 1★–3★ there is NO branch distinction — all skills share the ladder: 1★ Awakened, 2★ Named, 3★ Evolved."

**Correction:** Membership (`standard` / `suite` / `unique`) is `suiteComponents`-first and holds
from any rank. What is recognised only at 4★+ is the **decoration** (ladder word + glyph/medallion/
color), NOT the membership. A 2★ or 3★ skill with `suiteComponents` already **belongs** to the
suite branch; it simply renders the shared word (Named / Evolved) and the plain glyph until 4★.

**Why:** suites exist at 3★ in the landed data (#1232–1234) — a 4★ gate on membership would
mis-bucket them. Membership is decided by `suiteComponents` presence, not star level.

### 1b. L74–76 — the rank≥4 GATE on suite/unique membership

> Original (verbatim):
> "- rank 1–3 → shared ladder (Awakened / Named / Evolved), no branch
> - rank ≥ 4 AND suiteComponents present → Suite ladder (Extra / Ultimate / Apex)
> - rank ≥ 4 AND no suiteComponents → Unique ladder (Unique / Unique Ultimate / Unique Impossible)"

**Correction:** The `rank ≥ 4 AND` conjunct is wrong for **membership**. Membership derivation is:
`suiteComponents present → suite` (at any rank); else `rank ≥ 4 → unique`; else `standard`.
The rank≥4 threshold applies only to (a) the `unique` fallback for non-suite skills and
(b) which *decoration/ladder word* renders — never to whether a suite-component skill is a
member of the suite branch.

**Why:** the formula as written makes a 2★/3★ suite-component skill fall to "shared ladder, no
branch," contradicting the landed data where those skills are already `suite`. The membership
axis and the decoration axis were conflated; v3 separates them.

### 1c. L80–87 — the "Rank ladder" table (MEMBERSHIP framing only)

> Original (verbatim):
> "| Stars | Shared (no branch) | Suite branch | Unique branch |
> |---|---|---|---|
> | 1★ | **Awakened** | — | — |
> | 2★ | **Named** | — | — |
> | 3★ | **Evolved** | — | — |
> | 4★ | — | **Extra** | **Unique** |
> | 5★ | — | **Ultimate** | **Unique Ultimate** |
> | 6★ | — | **Apex** | **Unique Impossible** |"

**Correction:** The table is CORRECT as a **decoration / rank-word** ladder — those are exactly the
words rendered per branch per star. It is WRONG only if read as a **membership** map (the "—" in
the 1★–3★ suite/unique columns implying a suite/unique skill has "no branch" below 4★). Under the
final shape a suite-component skill is `suite` at 1★–3★ too; it merely renders the shared word.
Keep the table as a decoration ladder; do not read the blanks as "no membership."

**Why:** same membership/decoration conflation as 1a/1b. The DECORATION facts in this table are
live; the implied membership floor is not.

> **Preserved-correct (NOT superseded):** the v2 decision to drop the deprecated Ygg-I 5★ rank
> word, and the two
> 4★+ ladder-word sets (Extra/Ultimate/Apex · Unique/Unique Ultimate/Unique Impossible) are the
> final decoration words and remain live. Only the "membership starts at 4★" framing is archived.

---

## 2. v1 / Q2 / glossary — "read-time derivation" claims

**Source:** `founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md`

### 2a. L172 — "derived at read-time"

> Original (verbatim):
> "**Branch axis** (named only, progression): `{standard, unique, suite}`, derived at read-time from `(generic.type, generic.suiteComponents present?, named.level)`. Never declared; always computed."

**Correction:** Branch is resolved at **build time** by `src/gaia_cli/taxonomy.py` and emitted onto
every named entry (alongside `rank` / `rankWord` / `medallion` / `contractVersion`). Consumers read
the emitted field; they do not compute it at read-time. (The v2 Amendment already superseded the
`generic.type` input; v3 additionally supersedes the *read-time* framing.)

**Why:** the landed pipeline (#1232–1234) writes `branch` into `named/index.json` so consumers read
a stable value; build-time emit is now the contract.

### 2b. L183 — "Always derived, never declared" (Branch axis glossary)

> Original (verbatim):
> "**Branch axis** — progression, on named skills only. Values: `standard` (1★–3★), `unique` (4★–6★ non-suite), `suite` (4★–6★ suite-based). Always derived, never declared."

**Correction:** Two errors. (1) Read-time-vs-build-time: branch is **emitted at build time** by
`taxonomy.py`, not derived at read-time by each consumer. (2) The parenthetical membership map
(`standard` = 1★–3★, `suite`/`unique` = 4★–6★) repeats the 4★-gate error — membership is
`suiteComponents`-first from any rank, so a 2★/3★ suite-component skill is `suite`, not `standard`.

**Why:** build-time emit is the contract; and suites exist below 4★ in the landed data.

### 2c. L208 — Q2 "always computed at read-time"

> Original (verbatim):
> "| Q2 | Branch declaration | Branch is completely derived from `(generic.type, generic.suiteComponents present?, named.level)`. Never declared on nodes; always computed at read-time. …"

**Correction:** Branch is computed at **build time** and emitted onto named entries. "Never declared
on the source nodes" is still true (the source `registry/nodes/` do not carry `branch`); what
changed is WHERE the derivation runs — build-time emit in `taxonomy.py`, not per-consumer at
read-time. (The inline `[SUPERSEDED by v2]` marker on this row already retired the `generic.type`
input; this archives the read-time claim on top of it.)

**Why:** consumers now READ an emitted `branch`; only the starless graph still derives client-side
(see §5).

---

## 3. DESIGN_ALIGNMENT — BRANCH axis "derived at read-time, never declared"

**Source:** `founder/handovers/YGGDRASIL_II_DESIGN_ALIGNMENT.md` L55

> Original (verbatim):
> "**BRANCH axis** (named skills only, *derived at read-time, never declared*): `branch = f(the Named Skill's suiteComponents present?, rank)`."

**Correction:** Branch is **emitted at build time** by `src/gaia_cli/taxonomy.py` onto every named
entry; consumers read it. "Never declared on the source node" remains true, but "derived at
read-time" is superseded by build-time emit.

**Why:** #1232–1234 moved branch resolution into the build (`named/index.json` carries `branch`);
the design surface should read the emitted field, not recompute per consumer. (Exception: the
starless graph — see §5.)

---

## 4. DESIGN_ALIGNMENT — rank≥4 suite/unique GATE (membership-floor error)

**Source:** `founder/handovers/YGGDRASIL_II_DESIGN_ALIGNMENT.md` L56–58

> Original (verbatim):
> "  - rank 1–3 → **standard** (no branch fork)
>   - rank ≥ 4 AND the Named Skill has `suiteComponents` → **suite**
>   - rank ≥ 4 AND the Named Skill has **no** `suiteComponents` → **unique**"

**Correction:** Same membership-floor error as §1b. Membership is `suiteComponents`-first from any
rank: `suiteComponents present → suite` (at any rank); else `rank ≥ 4 → unique`; else `standard`.
The `rank ≥ 4 AND suiteComponents` conjunct wrongly demotes a 2★/3★ suite-component skill to
`standard`. Only the *decoration/ladder word* forks at 4★+.

**Why:** suites exist at 3★ in the landed data (#1232–1234); membership is not 4★-gated.

---

## 5. DESIGN_ALIGNMENT — Scout #1 "browser data carries NO branch field"

**Source:** `founder/handovers/YGGDRASIL_II_DESIGN_ALIGNMENT.md` L127

> Original (verbatim):
> "**Scout #1 (JS enum readers) — RETURNED 2026-07-17. VERDICT: browser data carries NO `branch` field.** `docs/graph/gaia.json` + `named/index.json` ship `type: "basic"|"fusion"` and `suiteComponents`/`level` only. JS MUST derive branch client-side."

**Correction — STALE EXCEPT FOR THE STARLESS GRAPH:** The verdict is now TRUE ONLY for
`docs/graph/gaia.json` (the starless graph, which has no per-named-skill branch and where JS still
derives client-side). It is FALSE for `named/index.json`, which now carries the **emitted `branch`**
field written at build time by `taxonomy.py` (#1232–1234). Consumers of `named/index.json` read the
emitted branch; only the starless graph still derives branch client-side.

**Why:** the build-time emit landed after Scout #1 ran; the scout's "no branch field anywhere"
snapshot predates it. The client-side `computeBranch` helper remains correct for the starless graph
only.

---

## Cross-reference

- Authoritative live shape: **v3 Amendment (2026-07-18)** at the top of
  `founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md`.
- Landed implementation: PR chain **#1232 → #1233 → #1234**.
- Build-time emitter: `src/gaia_cli/taxonomy.py` (emits `branch` / `rank` / `rankWord` /
  `medallion` / `contractVersion` onto named entries).
