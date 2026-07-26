---
title: "Yggdrasil II: Two Types, One Trust Gate, and a Branch Axis That Is Never Declared"
author: "Marcus Rafael Tiongson, Founder"
summary: The Yggdrasil I to II meta shift collapses three node types to two, derives the branch axis at read-time instead of storing it, and retires the Evidence Floor so Trust Magnitude is the sole promotion gate.
abstract: |
  Yggdrasil II is the second meta generation of the GAIA registry, ratified 2026-07-07. It makes three structural cuts, each measurable against the live registry. First, the starless node `type` axis collapses from four values to two — 243 nodes now resolve as 113 `basic` and 130 `fusion`, and the legacy `extra` / `ultimate` / `unique` types are retired. Second, the named-skill **branch** axis is no longer a stored field: it is derived at read-time as a function of `suiteComponents` presence and rank, retiring a stored field that appeared on every one of the 249 named skills. Third, the Evidence Floor — the Yggdrasil I promotion gate — is retired and **Trust Magnitude** replaces it as the sole gate on both branches, with a single numeric ladder (S ≥ 250, A ≥ 100, B ≥ 50, C ≥ 20) standing in for the arbitrary ≥ 10k-stars hard requirement. This report documents each cut against the numbers, works a live classification, shows a real skill whose stored branch would have drifted and a real skill the retired popularity gate would have blocked, and states why the derived-not-declared discipline is the load-bearing change.
label: Meta Shift
---

## Abstract

Yggdrasil II is the second meta generation of the GAIA registry. It does not add machinery; it removes it — and the body below pays that claim off against the live catalog. Three structural simplifications land together — the node `type` axis collapses from four values to two, the named-skill **branch** axis stops being a stored field and becomes a read-time derivation, and the Evidence Floor requirement is retired in favour of **Trust Magnitude** as the sole promotion gate. Each change is stated here against the live registry: 243 starless nodes splitting as 113 `basic` + 130 `fusion`; a branch function `f(suiteComponents present?, rank)` evaluated in that order; and a Trust Magnitude ladder of S ≥ 250 / A ≥ 100 / B ≥ 50 / C ≥ 20 against a live distribution of S = 4 / A = 42 / B = 56 / C = 76. The unifying principle is *derived, not declared*: the registry now computes standing that Yggdrasil I forced a curator to assert and maintain by hand.

## Executive Summary

Contributors who curated under Yggdrasil I maintained state the registry could have computed. A node's `type` was one of four hand-chosen values; a named skill's progression **branch** was a stored decision on every named skill; and promotion to the upper ranks was gated by an Evidence Floor that, at the top pathway, encoded an arbitrary popularity threshold. Every one of those was a place two curators could disagree, and a place the registry could drift out of internal agreement — a claim the §Why It Matters before/after table below shows on a real skill.

Yggdrasil II removes all three:

| Axis | Yggdrasil I | Yggdrasil II |
|---|---|---|
| Node `type` | `basic`, `extra`, `ultimate`, `unique` (4 values, declared) | `basic`, `fusion` (2 values, structural) |
| Named branch | stored field, curator-maintained on every named skill | derived at read-time: `f(suiteComponents present?, rank)` |
| Promotion gate | Evidence Floor (per-star, curator-asserted) | Trust Magnitude (sole gate): S ≥ 250 for the top pathway |
| Top-pathway hard requirement | ≥ 10k repository stars | none — TM is the sole numeric gate |

None of these deletes information a reader needs. They delete information a reader can recompute — and by deleting it, they delete the states in which the stored copy disagreed with reality.

## The Type Collapse

Under Yggdrasil I the `type` field on a starless (generic) node carried four values, and curators used three of them (`extra`, `ultimate`, `unique`) to imply where a skill sat on a progression it did not actually govern. Yggdrasil II retires those three. Per META.md §1.2, *"Legacy values `extra`, `ultimate`, and `unique` are retired; all non-basic nodes are `fusion`."* The field now answers exactly one structural question — does the node have prerequisites? — and nothing else:

- `basic` — 0 prerequisites.
- `fusion` — ≥ 1 prerequisite.

`type` lives on starless nodes only. Named skills carry no `type` field at all; they inherit structure via the `genericSkillRef` walk (§1.2). The field is **pure structure**: it does *not* determine a named skill's branch, and curation must never consult it to decide one.

Against the live `registry/gaia.json` (`skills` key), the collapse resolves as:

| `type` | Prerequisites | Count | Share |
|---|---|---|---|
| `basic` | 0 | 113 | 46.5% |
| `fusion` | ≥ 1 | 130 | 53.5% |
| **Total (all starless)** | | **243** | **100%** |

Every one of the 243 nodes is starless, and every node lands in exactly one of the two buckets: `113 + 130 = 243`. The residue check is literal — nodes carrying a `type` in `{extra, ultimate, unique}`: **0**. The migration left nothing in a legacy value.

## The Branch Axis Is Derived, Never Declared

The change with the longest reach retires a stored field that appeared on **all 249 named skills** — more rows of hand-maintained state than either other cut touches (the type collapse re-labels 243 starless nodes; the Trust Magnitude consolidation removes one gate column). It is the one cut with no column of its own in the schema going forward. Under Yggdrasil I the named-skill **branch** — the progression path a skill walks — was stored and maintained by a curator on every named skill. Under Yggdrasil II it is *derived at read-time and never declared* (§1.2). The derivation is a two-argument function evaluated in a fixed order:

```
branch = f(suiteComponents present?, rank)   // suiteComponents-presence evaluated FIRST
```

**Type and branch are fully orthogonal.** Per §1.2, *"A `fusion` node without `suiteComponents` yields Unique-branch named skills; a `basic` node with `suiteComponents` yields Suite-branch named skills. Never consult `type` to determine branch."* The two axes answer different questions — `type` is about the generic node's prerequisites; `branch` is about a named skill's progression — and reading one to guess the other is the exact error Yggdrasil II makes structurally impossible.

The resulting three branches:

| Branch | Predicate (evaluated in order) | Ladder |
|---|---|---|
| `suite` | `suiteComponents` present — at **any** rank from the 2★ push floor | 4★ Extra → 5★ Ultimate → 6★ Apex |
| `standard` | no `suiteComponents` **and** rank 1–3 | 1★ Awakened → 2★ Named → 3★ Evolved |
| `unique` | no `suiteComponents` **and** rank ≥ 4 | 4★ Unique → 5★ Unique Ultimate → 6★ Unique Impossible |

Two subtleties matter to curators who lived through Yggdrasil I:

1. **`suiteComponents` is a Named-Skill-only list.** It never appears on the generic parent. Its mere presence puts a skill on the `suite` branch at any rank from the 2★ push floor — membership is *structural*. The 4★ fork (where the ladder words "Extra / Ultimate / Apex" first appear) is only a **decoration gate**: a 2★ or 3★ suite skill still shows the shared word (Named / Evolved) with a plain glyph, and the ladder words surface only at 4★+ (§1.2).
2. **The branch forks at 4★, not before.** Ranks 1–3 without `suiteComponents` share one `standard` ladder (1★ Awakened → 2★ Named → 3★ Evolved). The Suite-versus-Unique split appears only at the 4★ row, which §1.1 records as *"Extra (Suite) / Unique (Unique) — branch forks here."*

### Worked Example: classifying a skill under Yggdrasil II

Take `obra/writing-plans` — a live named skill at rank 4★ whose generic parent is a `fusion` node, and which carries **no** `suiteComponents` list. Yggdrasil I would have asked a curator to store a branch and, tempted by the `fusion`-adjacent legacy `ultimate` type, to store the wrong one. Yggdrasil II computes it:

1. **`suiteComponents` present?** No. (First argument, evaluated first — and note we did **not** look at `type`.)
2. **Rank?** 4★, i.e. ≥ 4.
3. ⇒ Branch = `unique`. The skill sits at **4★ Unique** on the ladder 4★ Unique → 5★ Unique Ultimate → 6★ Unique Impossible.

The parent being `fusion` is irrelevant to the answer — a `fusion` node without `suiteComponents` yields Unique-branch skills, exactly as a `basic` node *with* `suiteComponents` would yield Suite-branch ones. The classification is a pure function of two inputs, so two curators cannot disagree and the stored copy cannot drift.

### Stars live on named skills; starless refs inherit

The star axis is likewise not stored where a reader might expect. Per the §1 intro, *"Stars live on named skills only. Generic skill references are starless — rank-less taxonomy nodes."* A starless ref's **effective rank is the top star among its named-skill children**, and it renders as generic — italic, greyed-out. The full named ladder spans 0★–6★ with fixed rank labels:

| Stars | Rank label | Note |
|---|---|---|
| 0★ | Basic | — |
| 1★ | Awakened | ≤ 1★ handles redacted (see below) |
| 2★ | Named | minimum for a named implementation / push floor |
| 3★ | Evolved | — |
| 4★ | Extra (Suite) / Unique (Unique) | branch forks here |
| 5★ | Ultimate / Unique Ultimate | — |
| 6★ | Apex / Unique Impossible | gate-guarded (§4.3 / §4.4) |

Because stars live on named skills only, a ≤ 1★ handle (0★ Basic or 1★ Awakened, including a demoted skill) is *pre-named* and **redacted** on all public surfaces until it earns 2★ Named standing (§1.3): it renders as `████████` in monospace or `@[anonymous]` in proportional type — never the honor-red Origin handle — enforced by `scripts/validate_redaction.py`.

## Trust Magnitude Is the Sole Gate

Yggdrasil I gated promotion on an **Evidence Floor** — a per-star minimum a curator asserted against each skill. Yggdrasil II retires the Floor and replaces it with a single gate. Per META.md §4.4, *"The Evidence Floor requirement has been retired: Trust Magnitude is the sole promotion gate on both branches"* — Suite and Unique alike.

Trust Magnitude (TM) is an accumulation, not a cap. Each evidence row produces an **artifact score** = `magnitude × weight × freshness`, and a skill's TM is the **sum** of artifact scores across all its rows (§2.1c) — unbounded and set-bonus-driven, over a fixed taxonomy of ten evidence types. Type weights tilt the sum toward corroborated provenance: `verifier-attestation` and `fusion-recipe` at 1.5×, `benchmark-result` at 1.4×, `repo-own` discounted to 0.6×, most others 1.0×. The Overall Trust Grade is then keyed off accumulated TM:

| Grade | Trust Magnitude |
|---|---|
| S | ≥ 250 |
| A | ≥ 100 |
| B | ≥ 50 |
| C | ≥ 20 |

The migration regrade has run across all **249** named skills. The live distribution (post-I11 source-curation pass, §2.1c) is:

| Grade | TM threshold | Count | Share |
|---|---|---|---|
| S | ≥ 250 | 4 | 1.6% |
| A | ≥ 100 | 42 | 16.9% |
| B | ≥ 50 | 56 | 22.5% |
| C | ≥ 20 | 76 | 30.5% |
| Ungraded | below C gate † | 71 | 28.5% |
| **Total** | | **249** | **100%** |

† The skill-level *ungraded* bucket collects skills whose accumulated Trust Magnitude falls below the C gate (TM < 20). This is an inference from the grade ladder, distinct from the per-row rule in §2.1b, where an *evidence row* whose `trustNumber` < 40 is itself ungraded and counts toward no gate. The two are different objects — a skill-level TM floor versus a per-row Evidence Grade cut — and are not the same threshold.

The counts sum exactly: `4 + 42 + 56 + 76 + 71 = 249`. S is deliberately scarce — four skills — because reaching TM ≥ 250 is arithmetically out of reach for mechanical backfill. The **diversity gate** (§2.1c) requires S to carry ≥ 3 distinct Evidence Types including at least one non-self-producible type, so a contributor cannot reach S by stacking self-minted `repo-own` rows (weighted 0.6×). The rows that move the sum fastest are `verifier-attestation` and `fusion-recipe` at 1.5×, and a `verifier-attestation` row can only be written by a 4★+ Verifier. The floor is therefore human-gated at the top: no automated pass can mint its way to Platinum.

### The retired 10k-stars requirement

The Suite 5★ Ultimate pathway once carried a *"≥ 10k repository stars"* hard requirement. Per §4.2, that gate *"is retired under Yggdrasil II; TM is the sole numeric gate"* — the pathway now requires **Trust Magnitude ≥ 250 (S-grade)** and nothing else. The change does real work, and the live catalog shows it: `obra/writing-plans` reaches **A-grade (TM 110.2)** on peer-review and social-signal evidence while carrying **no `github-stars` evidence row at all** — its standing is built entirely from demonstration, not fame. `obra/subagent-driven-development` (A-grade, TM 117.7) and `stanfordnlp/dspy` (A-grade, TM 100.0, arxiv-sourced) are the same story: genuinely-evidenced skills whose repositories the retired gate would have measured on star count rather than on the evidence they actually carry. The old requirement rewarded a repository's fame; TM rewards a skill's demonstrated trust.

## Why It Matters

The three cuts share one rationale: **derived, not declared.**

A stored field is a promise a curator makes and must keep. Yggdrasil I stored the branch axis on every named skill, so every rank change, every added `suiteComponents` list, every promotion was a chance for the stored branch to fall out of agreement with the facts — and reconciling it was hand-maintained state, checked (imperfectly) by review. Consider `obra/writing-plans` again: a 4★ skill with no `suiteComponents`, whose parent is a `fusion` node. Under Yggdrasil I a curator storing its branch by hand, cued by the `fusion` parent and the legacy `ultimate` type, could plausibly have stored it as Suite:

| Skill | Ygg-I stored branch (drift risk) | Ygg-II derived branch |
|---|---|---|
| `obra/writing-plans` (4★, no `suiteComponents`, `fusion` parent) | `suite` (mis-cued by the `fusion`/`ultimate` adjacency) | `unique` — computed from (no `suiteComponents`, rank ≥ 4) |

Deriving `branch = f(suiteComponents present?, rank)` at read-time deletes not just the field but the entire class of drift the row above illustrates: there is no stored copy to disagree with, because the branch is recomputed from inputs that already have to be correct for other reasons. The orthogonality rule — *never consult `type` to determine branch* — is what makes the derivation total and unambiguous.

The type collapse is the same discipline applied to structure. Three of the four legacy `type` values encoded a *guess* at progression that the branch axis actually owns. Retiring them leaves `type` answering the one question it can answer from the graph alone — prerequisites present or not — and stops it from being a second, contradictory source of truth about a skill's path.

The Trust Magnitude consolidation removes an *arbitrary* declaration. A ≥ 10k-stars floor is a number no evidence justifies; it rewards fame over demonstration and blocks genuinely-evidenced skills that happen to live in quieter repositories — `obra/writing-plans`, `obra/subagent-driven-development`, and `stanfordnlp/dspy` above are three live A-grade skills carrying no star evidence at all. Collapsing to a single TM gate (S ≥ 250) means the one hurdle is *earned from evidence*, weighted toward the provenance that corroborates rather than the provenance that is merely popular. The live S = 4 distribution shows the gate holding its line: hard to clear, and — because of the diversity gate and the human-only `verifier-attestation` weight — clearable only on real, corroborated evidence.

## What It Means Going Forward

For contributors and curators, the practical rules of Yggdrasil II are short:

- **Never store a branch.** Do not add a branch field to a node; do not consult `type` to infer one. Read `suiteComponents` presence first, then rank, and let the derivation answer.
- **Use only `basic` or `fusion`** when adding a starless node — `basic` for 0 prerequisites, `fusion` for ≥ 1. The three legacy types are gone; do not reintroduce them.
- **`suiteComponents` is a named-skill list**, never on the generic parent, and its presence makes a skill Suite from the 2★ push floor upward. Do not wait for 4★ to treat a skill as Suite — 4★ is only where the ladder *words* appear.
- **Promote on Trust Magnitude alone.** There is no Evidence Floor to satisfy and no stars-count to clear. TM ≥ 250 is the S-grade / top-pathway bar; build it from weighted, corroborated evidence.
- **Redaction still binds.** ≤ 1★ handles stay anonymised until 2★ Named; `scripts/validate_redaction.py` enforces it.

Every mutation reaching these states must still route through the `gaia dev` CLI verbs — the registry computes standing, and the CLI is the only sanctioned writer of the inputs that standing is derived from. Yggdrasil II did not change that discipline; it extended it, by turning three more things a human used to declare into things the registry now derives.

## References

[1] GAIA Registry. (2026). *Yggdrasil II — node type collapse, derived branch axis, and orthogonality rule* (META.md §1.1–§1.2, ratified 2026-07-07).
[2] GAIA Registry. (2026). *Star ladder, rank labels, and the 4★ branch fork* (META.md §1.1).
[3] GAIA Registry. (2026). *Starless references and ≤1★ redaction* (META.md §1, §1.3; `scripts/validate_redaction.py`).
[4] GAIA Registry. (2026). *Trust Magnitude formula, type weights, diversity gate, and Overall Trust Grade thresholds* (META.md §2.1b–§2.1c).
[5] GAIA Registry. (2026). *Evidence Floor retirement — Trust Magnitude as sole promotion gate* (META.md §4.4, L213).
[6] GAIA Registry. (2026). *Suite 5★ Ultimate gate — retirement of the ≥ 10k-stars hard requirement* (META.md §4.2, L174).
[7] GAIA Registry. (2026). *Migration regrade distribution across 249 named skills, post-I11 source-curation pass* (META.md §2.1c, L123).
[8] GAIA Registry. *CONTEXT.md* — vocabulary source of truth for type, branch, stars, rank labels, Trust Magnitude, and the starless layer.
