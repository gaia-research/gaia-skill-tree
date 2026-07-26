# --tier-unique* Consumer Classification (workflow wf_af31db4f-2c3, 2026-07-25)

**127 hits / 19 files. Adversarially verified.** All 11 verifier disagreements + the 4 ambiguous resolved to Role-A (rank). **Corrected Role-A rename set = 37 hits across 6 files.**

## Role A — RANK ladder → RENAME to --rank-*-unique (37 hits)
| file:line | token | → target | context |
|---|---|---|---|
| docs/css/styles.css:3459 | --tier-unique | --rank-4-unique | .tree-glyph-uni--iv { color: var(--tier-unique) !important } |
| docs/css/styles.css:3464 | --tier-unique-5 | --rank-5-unique | .tree-glyph-uni--v { color: var(--tier-unique-5) !important } |
| docs/css/styles.css:3470 | --tier-unique-6 | --rank-6-unique | .tree-glyph-uni--vi { color: var(--tier-unique-6) !important } |
| docs/css/styles.css:3619 | --tier-unique | --rank-4-unique | .tree-unique-skillname--iv,.tree-unique-id--iv { color: var(--tier-uni |
| docs/css/styles.css:3626 | --tier-unique-5 | --rank-5-unique | .tree-unique-skillname--v,.tree-unique-id--v { color: var(--tier-uniqu |
| docs/css/styles.css:3633 | --tier-unique-6 | --rank-6-unique | .tree-unique-skillname--vi,.tree-unique-id--vi { color: var(--tier-uni |
| docs/css/ascension-overdrive-v2.css:701 | --tier-unique | --rank-4-unique | .aov-ucard__num { color: var(--tier-unique); } with L704/705 overridin |
| docs/css/ascension-overdrive-v2.css:1090 | --tier-unique | --rank-4-unique | Colour ladder comment: 'Rung 5 (Unique) : --tier-unique -> --muted' |
| docs/css/ascension-overdrive-v2.css:1240 | --tier-unique | --rank-4-unique | /* Unique: solid tier-unique, weight 500. */ above .aov-order-rung[dat |
| docs/css/ascension-overdrive-v2.css:1242 | --tier-unique | --rank-4-unique | .aov-order-rung[data-tier="unique"] { color: var(--tier-unique); } â€” |
| docs/js/skill-graph.js:1217 | --tier-unique-6-rgb | --rank-6-unique-rgb | if (n >= 6) return _rgbOnly(_readVar('--tier-unique-6-rgb')) // tok.ti |
| docs/js/skill-graph.js:1218 | --tier-unique-5-rgb | --rank-5-unique-rgb | if (n >= 5) return _rgbOnly(_readVar('--tier-unique-5-rgb')) // tok.ti |
| docs/js/skill-graph.js:1312 | --tier-unique-6-ink | --rank-6-unique-ink | const ink = _readVar('--tier-unique-6-ink'); â€” 6-star placeholder le |
| docs/js/skill-graph.js:1206 | --tier-unique | --rank-4-unique | //   4â˜… (--tier-unique, violet): the base singularity, toned DOWN fr |
| docs/js/skill-graph.js:1208 | --tier-unique-5 | --rank-5-unique | //   5â˜… (--tier-unique-5, copper): smaller radius, tighter/denser di |
| docs/js/skill-graph.js:1210 | --tier-unique-6 | --rank-6-unique | //   6â˜… (--tier-unique-6 copper + -ink): PLACEHOLDER â€” near-still  |
| docs/trust/leaderboard/leaderboard.js:121 | --tier-unique-rgb | --rank-4-unique-rgb | uniqueColors(level) 4-star stop; feeds typeColors -> bar gradient. Ran |
| docs/trust/leaderboard/leaderboard.js:122 | --tier-unique-5-rgb | --rank-5-unique-rgb | uniqueColors(level) 5-star stop (rawMap[5]). |
| docs/trust/leaderboard/leaderboard.js:123 | --tier-unique-6-rgb | --rank-6-unique-rgb | uniqueColors(level) 6-star stop (rawMap[6]). |
| docs/trust/leaderboard/leaderboard.js:198 | --tier-unique-rgb | --rank-4-unique-rgb | Comment documenting 4-star rank->token mapping above uniqueColors(). |
| docs/trust/leaderboard/leaderboard.js:199 | --tier-unique-5-rgb / --tier-unique-6-rgb | --rank-5-unique-rgb / --rank-6-unique-rgb | Comment documenting 5-star and 6-star rank->token mapping. |
| docs/badges/index.html:1157 | --tier-unique | --rank-4-unique | <span style="color:var(--tier-unique,#7c3aed);font-weight:600;">â—‰ Un |
| docs/badges/index.html:1161 | --tier-unique | --rank-4-unique | <span class="bd-rank-swatch" style="background:var(--tier-unique,#7c3a |
| docs/badges/index.html:1174 | --tier-unique-5 | --rank-5-unique | <span class="bd-rank-swatch" style="background:var(--tier-unique-5,#b2 |
| docs/badges/index.html:1183 | --tier-unique-6 | --rank-6-unique | <span style="color:var(--tier-unique-6);font-weight:700;...">â—‰ Uniqu |
| docs/badges/index.html:1187 | --tier-unique-6 | --rank-6-unique | <span class="bd-rank-swatch" style="background:var(--tier-unique-6,#e0 |

### + overturned by verifier (were mis-called Role-B; ARE rank):
- docs/css/styles.css:161 — Line 161 lives inside the selector `.rank-badge[data-tier="unique"] .rank-badge__chip` (opens L157) and its comment reads "Unique tier rank badge." Th
- docs/css/styles.css:161 — Line 161 uses var(--tier-unique-rgb) inside `.rank-badge[data-tier="unique"] .rank-badge__chip` (a RANK badge chip). --tier-unique-rgb is the RGB chan
- docs/css/styles.css:1971 — Line 1971 is `.btn-unique:hover { border-color: var(--tier-unique); }`. The block's own comment (L1960-1962) declares it a "Tier-4 (Unique) button" th
- docs/css/styles.css:1972 — Line 1972 sits inside `.btn-unique:hover` and references `--tier-unique-rgb`. This is the rank-4 base token of the Unique-branch RANK ladder (4=--tier
- docs/css/styles.css:4171 — Line 4171 (`var(--tier-unique-edge) 33%`) is the live use inside the `.graph-scatter-strip` four-stop gradient; line 4157 is only the comment describi
- docs/css/styles.css:4171 — The classifier's "ambiguous" is wrong; this is Role A (rank). The .graph-scatter-strip gradient (styles.css:4159-4173) is an explicit descending rank 
- docs/css/styles.css:7301 — The classifier's own sibling evidence refutes it. The .se-node-orb--* family is a single numbered orb ladder: --extra uses var(--rank-4) (L7291), --ul
- docs/css/ascension-overdrive-v2.css:626 — The base `.aov-ucard` border at L626 is NOT branch identity â€” it is the rank-4 tint. Although `.aov-ucard` is the base selector nominally covering "
- docs/js/skill-graph.js:17 — Re-reading the consumers, the base --tier-unique token is NOT merely a branch accent â€” it is the 4â˜… rung of the Unique-branch RANK ladder. In draw
- docs/js/named-skills.js:252 — The classifier's premise is factually wrong. emitDagLayer does NOT paint one flat token across the whole Unique branch. The caller loop (L340-353) ite
- docs/js/named-skills.js:699 — DISAGREE â€” this is Role A (rank), not branch-identity. The `--tier-unique` at L699 sits in the `groupHeader(rankNum, id, branch)` colorVar ternary w

### + ambiguous (verifier leaned rank; confirm on impl):
- docs/css/styles.css:4157 --tier-unique-edge — Inside a comment describing the scatter-strip gradient ('--tier-unique-edge â†’ --rank-3-edge'). Documentation for the live use at line 4171; classifi
- docs/css/styles.css:4171 --tier-unique-edge — .graph-scatter-strip gradient stop sitting BETWEEN --rank-5-edge (top) and --rank-3-edge (below), comment says strip 'maps onto the rank hierarchy fro
- docs/css/ascension-overdrive-v2.css:955 --tier-unique — .aov-pred[data-state="locked"] .aov-pred__id â€” faint 15%-into-muted tint on LOCKED prerequisite IDs. Not keyed to a 4/5/6 rank; on unlock the ID shi
- docs/js/skill-graph.js:17 --tier-unique / -rgb / -edge — Comment in the <canvas-tokens> contract block documenting the base --tier-unique token family (no numeric suffix). The base --tier-unique doubles as (

## Role B — BRANCH IDENTITY → KEEP as --tier-unique (or correct). ~90 hits.
The glyph ◉ (--tier-unique-symbol), plaque orbs (--tier-unique-bg/-border), generic Unique-branch accents NOT keyed to a specific 4/5/6 rank. NOTE: .tier-glyph[data-type="fusion"] reusing --tier-unique is a known MISUSE (correct, do not rename to rank).