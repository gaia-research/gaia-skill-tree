---
title: "Skill Tree Report: A Registry Correction on caveman, and Two Install Fixes"
author: "Gaia Research"
summary: "mattpocock/caveman removed and replaced by its true original, juliusbrussee/caveman, at an honest 1★. Two skills got clearer install slugs, and several previously silent install failures now surface an honest error."
abstract: |
  This report covers three user-facing registry changes: the removal of mattpocock/caveman
  and the ingestion of its true original, juliusbrussee/caveman, at a conservative 1★; two
  contributor skills renamed to the slugs their upstream repos actually use for install;
  and a correction that makes several previously misleading install successes fail honestly
  instead.
label: Registry Correction
---

## Abstract

This report covers three user-facing changes to the skill tree this cycle. The most
significant is a registry correction: `mattpocock/caveman` was removed after its author
deleted it upstream and confirmed it was never meant to be public, and the skill it was a
private copy of — `juliusbrussee/caveman`, the real original — was ingested in its place at
a conservative, evidence-checked 1★. Two skills also picked up clearer install slugs that
match what their upstream repositories actually ship. And a batch of `gaia skills install`
targets that used to silently report success while installing nothing now correctly report
that they can't be installed.

## caveman: a registry correction, not just a removal

`mattpocock/caveman` sat in the registry at 2★. Its upstream repository deleted the skill
on 2026-05-31, and its author confirmed directly that it was a private duplicate of another
skill he was testing — never meant to be public, with no replacement. That much was a
straightforward removal.

The more interesting part is what it was a duplicate *of*. Tracing the skill's actual
history turned up **[`JuliusBrussee/caveman`](https://github.com/JuliusBrussee/caveman)** —
MIT licensed, over 96,000 stars, actively maintained, homepage at caveman.so. The evidence
that this is the true original, not the other way around:

- Julius Brussee's `caveman` has a first commit dated 2026-04-04. The copy that appeared in
  `mattpocock/skills` doesn't show up until 2026-04-17 — thirteen days later.
- Both `SKILL.md` files share the same "~65-75% token reduction" framing, the same rule
  structure, and at least one verbatim example line.
- When `mattpocock/skills` deprecates a skill for a real reason, its changeset names a
  replacement — it did exactly that for four other removed skills around the same time.
  Caveman's removal named none, consistent with it being a private test copy rather than
  original work with a designated successor.

`juliusbrussee/caveman` is now the registry's `caveman` entry, and the honest story is worth
telling in full because it's not simply "verified, ship it." The skill's own marketing
claims a ~65-75% reduction in agent context/token usage. Independent measurement tells a
different story: one measured source puts the real reduction closer to **31%**, and another
closer to **9%**. That gap between the claim and the independently measured result is
exactly why the skill landed at a conservative **1★** rather than higher — a real, popular,
well-maintained skill, whose central performance claim doesn't hold up to outside scrutiny
at the strength advertised. Readers evaluating whether to install it should weigh the
skill's genuine popularity and maintenance against that specific, checkable gap.

`caveman` is installable from
[`JuliusBrussee/caveman`](https://github.com/JuliusBrussee/caveman) via the usual
`gaia skills install juliusbrussee/caveman`.

## Two skills got install-accurate slugs

Two named skills were renamed so the slug you install by matches the name the upstream
project actually ships under:

| Old install command | New install command |
|---|---|
| `gaia skills install browserbase/stagehand` | `gaia skills install browserbase/browse` |
| `gaia skills install bradautomates/claude-video` | `gaia skills install bradautomates/watch` |

`browserbase/stagehand` had been flagged as possibly having no installable skill manifest at
all. That turned out to be wrong — the manifest exists upstream, just under a different
skill name (`browse`), and the registry now points at it correctly. `bradautomates/watch`
picks up the name its own `SKILL.md` uses rather than the older working title. Anyone with
either skill already installed keeps working; anyone installing fresh should use the new
slug.

## Install failures that used to lie now tell the truth

A number of named skills in the registry pointed `links.github` at a location that doesn't
actually contain an installable skill — an issue thread, a general framework repository with
no skill manifest, or a directory that never had one. Previously, running
`gaia skills install` against one of these could report success while installing nothing
usable. That's now fixed: these skills are correctly marked as not installable, so
`gaia skills install` gives you an honest failure instead of a false "done."

This is a trust fix, not a data-tidying exercise — the old behavior meant you could believe
you'd installed a skill you didn't actually have. A related cleanup pass is still in
progress for a further set of skills where the right call needs a maintainer's judgment call
(for example, whether a skill grouped under a component suite should be held to the same
individual-installability bar as a standalone skill); those are being worked through
deliberately rather than rushed.

## Reading the data

The key facts are:

- `mattpocock/caveman` removed; `juliusbrussee/caveman` — the verified true original —
  ingested at 1★, with the token-reduction discrepancy disclosed rather than smoothed over.
- `browserbase/browse` (was `stagehand`) and `bradautomates/watch` (was `claude-video`) are
  the current install slugs for those two skills.
- Several previously silently-broken install targets now fail honestly instead of falsely
  succeeding.
- The registry currently tracks 180 named skills across 38 contributors.

## Sources and References

[1] JuliusBrussee/caveman — https://github.com/JuliusBrussee/caveman — the verified true
original source now backing the registry's `caveman` entry.

[2] mattpocock/skills deprecation commit — https://github.com/mattpocock/skills/commit/7d3ada9716a9ee08d6c6f775d8a78ef889e1798f
— upstream deletion of the duplicate copy, authored by Matt Pocock.

[3] Browserbase — https://github.com/browserbase — upstream source for the `browse` skill
now installed as `browserbase/browse`.

[4] Brad Automates — https://github.com/bradautomates — upstream source for the `watch`
skill now installed as `bradautomates/watch`.
