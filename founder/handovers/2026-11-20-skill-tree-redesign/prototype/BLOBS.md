# Prototype blobs

The boards load their images and data from the artifact's asset store as `/_blob/<id>`. The files themselves are not in this snapshot: images come from `docs/assets/` or GitHub, and every data file can be rebuilt from repository data with the scripts in `tools/`. This table maps each id to its role and source.

| Blob id | Role | Source | Used by |
|---|---|---|---|
| `00f360793a1b19d3eefe8877075c5d3a` | Capture of the live 3D explorer, for the Brief | Screenshot of `/?tree=1` on 19 Nov 2026 | Brief |
| `0d2eb07f0432c1cefb75dd02485bfb39` | Origin wreath | `docs/assets/origin-wreath-gold.svg` | Contributors, Dossier, Explorer3D, Heroes, Home, Leaderboard, Share, Skills |
| `344138fe2966bd3daea583bc3b98afa2` | Hall of Heroes astrolabe substrate, 1920 px | `docs/assets/ascension-overdrive/aov4-astrolabe-substrate.webp`, resized | Heroes |
| `42c70ced95d3d825de36f2ef46d51ca5` | Share plaque badge data (JSON) | `tools/hall_data.py` from `docs/api/v1` and the badges data | Share |
| `759fe54d3c8d6fc4b0f4b817c52cd7f9` | Avatar sprite, 8 columns of 64 px cells, for the 42 Origin holders | GitHub avatars (`avatars.githubusercontent.com/<handle>?s=96`), packed; order in `tools/holders.txt` | Explorer3D, Leaderboard |
| `86f35239f6827d7638f172937dcbe2b6` | Changelog data (JSON): 5,306 timeline events | `tools/changelog_data.py` from the same two graph files, as `docs/js/page-ia.js` does | Changelog |
| `8b66798fc1cd342f5d6247214f6263ae` | Skills Flow view data (JSON): 317 generic skills, 501 links, 482 named skills | `tools/build-local-flow.py` from `docs/graph/gaia.json` and `docs/graph/named/index.json` | Skills |
| `b5829cd5ed954bed364b2ca99692d4dd` | Registry snapshot fixture (JSON): counts, skills, dossiers, ledger, reports, hall, plates, avatar map | `tools/fixtures_v2.py` from `docs/graph/*.json`, `docs/api/v1/*` | About, Atlas, Benchmarks, Changelog, Contributors, Dossier, Evidence, Heroes, Home, Leaderboard, Reports, Skills |
| `c5e5787bf089816408111cba8e7fbef7` | 3D explorer field data v3 (JSON): nodes, edges, routes, ghosts, holders, both shapes, Unique fruit placement | `tools/export.cjs` then `tools/augment.cjs`, run over `docs/graph/gaia.json` with `docs/js/world-tree-layout.js` | Explorer3D |
| `c71612db03dd0c08b5c962bfeb5fd65b` | Tree scene data (JSON): Yggdrasil and Arbor positions, the 22 pinned subjects and 3 relations | `tools/fixtures_v2.py` from `docs/graph/gaia.json` and `docs/graph/arbor/` | Scene |
| `f3c4a78f650495709742b34c13ba9ba9` | About page portrait | `docs/assets/mbtiongson1-avatar.jpg` | About |
| `067317f281dd6808e896e3baa06d8a89` | Rank medallion c5-suite-ultimate | Medallion art from `docs/assets/ascension-overdrive/`, resized | Contributors, Dossier, Heroes, Home, Skills |
| `245265bcf720c3554a92d4deebdf13ca` | Rank medallion c2-suite-named | Medallion art from `docs/assets/ascension-overdrive/`, resized | Contributors, Dossier, Home, Skills |
| `25a22d936d7985205d6d77f23460d572` | Rank medallion d6-unique-impossible | Medallion art from `docs/assets/ascension-overdrive/`, resized | Contributors, Dossier, Heroes, Home, Skills |
| `4ef143c437116175bb61ebf5456688ed` | Ascension Overdrive capture, phone | Screenshot of the live homepage | Home |
| `5a4f089a79116491433e15afa4296e82` | Rank medallion d5-unique-ultimate | Medallion art from `docs/assets/ascension-overdrive/`, resized | Contributors, Dossier, Heroes, Home, Share, Skills |
| `670ae5fd0ba207ea8ec029f130247610` | Rank medallion c6-suite-apex | Medallion art from `docs/assets/ascension-overdrive/`, resized | Contributors, Dossier, Heroes, Home, Skills |
| `6a2d8698de517f2560e94464141478fb` | Yggdrasil hero backdrop | `docs/assets/world-tree/yggdrasil-backdrop-941.webp` | Observatory, Scene, Share |
| `745d7120f4048829967270ed0745c143` | GitHub avatar, @safishamsi | `avatars.githubusercontent.com/safishamsi?s=480` | Share |
| `7601aadaeb67b8b9616c4f70239a5f5a` | Rank medallion d4-unique | Medallion art from `docs/assets/ascension-overdrive/`, resized | Contributors, Dossier, Heroes, Home, Skills |
| `7ecf86e4708fc19c0b59821d6c743613` | Rank medallion c4-suite-extra | Medallion art from `docs/assets/ascension-overdrive/`, resized | Contributors, Dossier, Heroes, Home, Skills |
| `a683094ec451ed1421d6e3c772818798` | Rank medallion c1-suite-awakened | Medallion art from `docs/assets/ascension-overdrive/`, resized | Contributors, Dossier, Home, Skills, States |
| `ac2cc5993d8a4b999aefcac268fcfe49` | Ascension Overdrive capture, desktop (the locked section is shown, not rebuilt) | Screenshot of the live homepage | Home |
| `addaa4effaafea78fe4b3a07bbc383bb` | Milim poster for the Observatory Research aperture | Poster of the approved `milim.riv` (gaia-research `public/milim`) | Observatory |
| `d762e0fb037e3eff0ed7123da1031186` | Rank medallion c3-suite-evolved | Medallion art from `docs/assets/ascension-overdrive/`, resized | Contributors, Dossier, Home, Skills |
| `d8f31bcadb5931e0f57b0f6a21876e73` | Lucy, Zero state, for the Skill Heaven aperture | gaia-skill-heaven Lucy v5 Zero delivery | Observatory |
| `ef18f7fbd43f0eaebfd86d10a774593a` | Departure Mono font | Departure Mono, OFL | atlas.css |
