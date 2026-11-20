# Redesign prototype: source snapshot

This is the source of the Claude Design canvas the founder approved on 20 Nov 2026 (canvas version 16). It is the visual and behavioural reference for the redesign. **It is not production code. Do not copy it into `docs/`.** Wiring waits until the founder has seen the final product with stamped assets.

**Canvas (private to the founder until shared):** https://claude.ai/artifact/8LmXZkYNH2HggishnaDwow. Start with the board "Gaia Skill Tree (play this)": it is the whole site, connected, with the Yggdrasil and Arbor lens in the header.

## Layout

| Path | What it is |
|---|---|
| `project/*.dc.html` | One board per file. Markup with `{{holes}}`, `<sc-if>`, `<sc-for>` and `<dc-import>`, plus a `class Component extends DCLogic` script per board. |
| `project/atlas.css` | Shared tokens and classes: the shell, the two worlds, the Arbor weather layer, components. |
| `project/canvas.json` | Board positions, titles and pages on the canvas. |
| [`BLOBS.md`](BLOBS.md) | Every `/_blob/<id>` the boards load: its role and its source in the repo. |
| `tools/` | The scripts that built the prototype's data snapshots from repository data. |

## Boards

| File | Title | Canvas page |
|---|---|---|
| `Main.dc.html` | Gaia Skill Tree (play this) | The site (connected prototype) |
| `Home.dc.html` | Home: Yggdrasil and Arbor compositions | Page families |
| `Atlas.dc.html` | Tree Explorer (the file name is internal; the page is "Tree Explorer") | Page families |
| `Explorer3D.dc.html` | Yggdrasil in 3D: live layout, Uniques as fruit | Page families |
| `Explorer3DHero.dc.html` | Yggdrasil in 3D: hero tree shape (review alternative) | Page families |
| `Skills.dc.html` | Skills: Ledger, Specimens, By capability, Flow | Page families |
| `Dossier.dc.html` | Skill dossier | Page families |
| `Leaderboard.dc.html` | Leaderboard: every graded skill by Trust Magnitude | Page families |
| `Evidence.dc.html` | Evidence and trust | Page families |
| `Benchmarks.dc.html` | Benchmarks and Hell-Heaven stamps | Page families |
| `Contributors.dc.html` | Contributors: profile, spotlight, directory | Page families |
| `Heroes.dc.html` | Hall of Heroes (restored, people first) | Page families |
| `Share.dc.html` | Share plaque view | Page families |
| `Docs.dc.html` | Docs (/en) | Page families |
| `Observatory.dc.html` | The Observatory (ecosystem) | Page families |
| `About.dc.html` | About: the founder story | Page families |
| `Reports.dc.html` | Reports (meta, weekly, trending template) | Page families |
| `Changelog.dc.html` | Changelog: every skill change, newest first | Page families |
| `System.dc.html` | Design system: three token layers | System and specimens |
| `NavCompare.dc.html` | Navigation: current vs proposed | System and specimens |
| `Weather.dc.html` | Arbor runtime weather | System and specimens |
| `Mobile.dc.html` | Phone compositions (390 px) | System and specimens |
| `States.dc.html` | Utility states: loading, empty, error, unknown | System and specimens |
| `Scene.dc.html` | Tree scene component | System and specimens |
| `Brief.dc.html` | Design brief, coverage matrix, boundary notes, round three | Brief and handoffs |
| `Handoff.dc.html` | Asset and Rive handoffs | Brief and handoffs |

## What is not here, and why

- **The canvas runtime.** The boards run on the Claude Design runtime, which belongs to the artifact type and is not redistributed here. To see the boards running, open the canvas.
- **Blob files.** These are images and data snapshots. The images already live in `docs/assets/` or come from GitHub avatars, and the data can be rebuilt with `tools/`. `BLOBS.md` maps each one.

## Data snapshot

All figures in the prototype come from the registry as of **17 Nov 2026**. They are read from:

- `docs/graph/gaia.json`
- `docs/graph/named/index.json`
- `docs/api/v1/*.json`
- `docs/graph/ledger/data.json`
- `docs/graph/arbor/`
- `docs/js/world-tree-layout.js`, for the 3D field pose

The scripts in `tools/` show exactly how. They were run in a scratch workspace, so set the path constants at the top of each before re-running.

| Script | Builds |
|---|---|
| `tools/fixtures_v2.py` | The shared registry fixture and the Tree scene data |
| `tools/export.cjs`, then `tools/augment.cjs` | The 3D explorer's field data, both shapes and the Unique fruit placement |
| `tools/build-local-flow.py` | Skills · Flow |
| `tools/changelog_data.py` | Changelog |
| `tools/lb-data.py` | Leaderboard (inlined in the board) |
| `tools/hall_data.py` | Hall of Heroes and Share data |
| `tools/serve.py` | The local static server used for screenshots |

## Known prototype shortcuts

The wiring work should not copy these:

- Data is inlined or loaded as snapshot JSON; production reads the live generated files.
- Some boards use `DCLogic` state where the site would use its own modules.
- Leaderboard bars are labelled by slug, and the Yggdrasil IV contested marks are not shown.
- The Changelog sorts timeline actions into families with its own mapping (documented in the board).
- The About page leaves out the email link on purpose.
- The Hell-Heaven stamp artwork is a placeholder.
