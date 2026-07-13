---
id: favorchurch/update-unique-churches
name: Update Unique Churches
contributor: favorchurch
origin: false
genericSkillRef: crm-data-cleanup
status: named
level: 2★
description: Recount and update the unique churches represented in the conference
  attendance Google Sheet.
createdAt: '2026-07-14'
updatedAt: '2026-07-14'
title: Update Unique Churches
links:
  github: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/update-unique-churches/SKILL.md
timeline:
- timestamp: '2026-07-13T16:26:02Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill favorchurch/update-unique-churches
- timestamp: '2026-07-13T16:34:32Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/update-unique-churches/SKILL.md
    (type: self-attestation)'
evidence:
- source: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/update-unique-churches/SKILL.md
  evaluator: favorchurch
  date: '2026-07-14'
  type: self-attestation
  trustNumber: 10.0
  notes: Self-attestation of update-unique-churches skill implementation
  grade: C
verification:
  firstEvidenceAt: '2026-07-13T16:34:32Z'
---

# Update Unique Churches (Composio, incremental)

Keeps the **"Church Count (Normalized)"** tab current by folding **new signups** into the existing
normalized list — not a full rebuild. The agent supplies judgment (classify new raw church
strings, confirm merges, decide pruning); `church_recount.py` does the deterministic extraction,
matching, recount, transforms, and write-payload assembly.

**Core principle — incremental, not rebuild:** every raw string already folded into the table is
recorded in its **Merged variants** column. New signups = strings *not yet* captured there; only
those need judgment. Counts are then recomputed for the whole table, so cancellations (counts go
DOWN) and additions both register.

> A sibling skill `unique-churches` exists but is **stale** (uses the `gws` CLI, the pre-drift
> column letters, and the old "add parentheses for campuses" convention). Prefer THIS skill.

## Prerequisites

Each requirement below is a **capability bucket** — any one of the listed tools satisfies it. Run this preflight before reading or writing the Sheet. If a **Required** bucket has no connected tool, explain what it is, why this skill needs it, and how to connect one of the options, then **stop and ask the user to set it up** before continuing — never write a recount you couldn't verify.

| Capability | Type | Satisfied by (any one) | If missing |
|---|---|---|---|
| **Google Sheets Access** (as `rico@favor.church`) | Required | Composio CLI with the `googlesheets` toolkit (this skill's commands assume Composio `GOOGLESHEETS_*`) | All reads/writes go through `GOOGLESHEETS_*`. Confirm with `composio whoami`; if not connected, ask the user to authenticate the googlesheets toolkit, then wait. |
| **Shell & Python** (Python 3 + the bundled `church_recount.py`) | Required | a terminal with Python 3 | The deterministic extraction, matching, recount, and payload assembly run in the script. Without it, do not hand-recount. |
| **Web search / fetch** | Optional | any web search or fetch tool | Used to verify ambiguous or higher-count new churches. If unavailable, mark them `Unverified` and note which rows still need verification. |

## Fixed facts

- **Sheet ID:** `1PT2e_9nk9gmlPKcGQloXmTLgZZt88MLzyt0kL249oFE`
- **Tabs:** `MASTERLIST` (source) · `Church Count (Normalized)` (target) · `Churches with 30+ attendees` ·
  `Cities` · `Update Log` (dated log) · `AGENTS` (methodology §5, change log §9).
- **Normalized table layout:** rows 1–3 = banner/note/headers; data from **row 4**;
  `A=Normalized Church · B=City · C=Status · D=Attendees · E=Merged variants`.
  `H1` (`=COUNTA(A4:A…)`) and `E1` are **live formulas** — recount automatically; **never write them**.
- **Auth/write:** Composio CLI as `rico@favor.church` (`composio whoami`). The `googlesheets` toolkit
  is connected. Read = `GOOGLESHEETS_VALUES_GET`; write = `GOOGLESHEETS_VALUES_UPDATE`;
  clear = `GOOGLESHEETS_SPREADSHEETS_VALUES_BATCH_CLEAR`. Big reads spill to `outputFilePath` — parse that file.
- **Column drift is expected.** The MASTERLIST export reshuffles columns (Order Status has moved
  AW→BA; church fields are N/S/T/AH/AI). The script detects columns **by header text**, so don't
  hardcode letters. If `analyze` errors on header detection, inspect row 1 and update `detect_cols()`.
- **Inclusion filter** (encoded in the script): Order Status = `completed`, ticket ≠ `Kids`, and the
  person stated a non-Favor church in one of the church fields (Favor-location-only people are excluded).

## Workflow

Work in a scratch dir. Script: `~/.claude/skills/update-unique-churches/church_recount.py`.

### 1. Fetch source + current table (Composio)
```bash
SID=1PT2e_9nk9gmlPKcGQloXmTLgZZt88MLzyt0kL249oFE
# Full MASTERLIST incl. header (bump 6000 if it grew). Output spills to a file:
composio execute GOOGLESHEETS_VALUES_GET -d "{\"spreadsheet_id\":\"$SID\",\"range\":\"MASTERLIST!A1:BA6000\"}" > ml_resp.json
# Current normalized table from A1:
composio execute GOOGLESHEETS_VALUES_GET -d "{\"spreadsheet_id\":\"$SID\",\"range\":\"Church Count (Normalized)!A1:E997\"}" > tbl_resp.json
```
Extract the `values` array from each response (follow `outputFilePath` when `storedInFile`) into
`ml.json` and `table.json` (plain 2-D arrays). A small Python helper that walks the JSON for the
first `values` key does this reliably.

### 2. Analyze
```bash
python3 ~/.claude/skills/update-unique-churches/church_recount.py analyze ml.json table.json
```
Prints stated/matched/uncaptured/zero-row stats and saves `stated.json`, `matched.json`,
`unmatched.json` (uncaptured string → head-count), `zerorows.json` (fragment-dup vs standalone).

### 3. Classify uncaptured strings → `curation.json` (judgment)
For **every** string in `unmatched.json`, one of:
- `{"action":"existing","name":"<exact existing row name>","city":"<row city>"}` — a spelling/variant of a church already in the table.
- `{"action":"new","name":"…","city":"…","status":"Verified|Unverified"}` — a genuinely new church.
- `{"action":"drop"}` — not a church (personal name, bare city like "Pasig City", a sentence, a business, junk like "L"/"N/Q"/"VGH").

Normalization rules (mirror AGENTS §5):
- Identity = **brand/denomination + the church's own campus city** (not the attendee's residence).
  Same brand + same city → merge; same brand + **different** city → separate.
- Expand acronyms (CCF, JIL, JIA, IPC, GOP, UPCI, VICCF…); fuzzy-match typos/spacing/diacritics.
- Resolve barangay→city (Sta. Mesa→Manila, Mambog→Bacoor); **web-verify** ambiguous or higher-count new churches.
- City unknown but church looks real → `status:"Unverified"` (still counts as 1), city `"—"`.
- **Name new rows in FINAL form** — current convention is **bare brand, city in the City column**
  (e.g. `Victory` + city `Makati`, not `Victory (Makati)`). Keep deliberate acronyms like
  `International Churches of Christ (ICOC)`.
- **Never alter `Manually Verified` rows.**

### 4. Decide transforms → `transforms.json` (optional)
```json
{ "strip_parens": true,
  "apostrophe_fixes": {"Christ Commission Fellowship":"Christ’s Commission Fellowship"},
  "renames": [{"match":"Old Name|City","name":"New Name","city":"City","status":"Verified"}],
  "merges":  [{"into":"Name|City","absorb":["Frag|—","Other Spelling|City"]}],
  "prune_zeros": "fragments" }
```
- `strip_parens` removes trailing campus parentheticals from **pre-existing** rows only (legacy
  `The Feast (Alabang)`→`The Feast`); new rows are left as you named them.
- `prune_zeros`: `"fragments"` (drop only duplicate fragments, default) · `"all"` (also drop
  standalone churches whose regs all cancelled) · `"none"` (retain for audit). Rows whose status is
  `Not a Church` are always dropped. Review `zerorows.json` first.
- The script auto-merges any two rows that share name+city after transforms (e.g. two Victory
  campuses both in Manila) — expected when stripping parens; note it in the report.

### 5. Build → payload
```bash
python3 ~/.claude/skills/update-unique-churches/church_recount.py build table.json curation.json transforms.json
```
Re-run until it reports **no UNMAPPED** (any unmapped string must be added to `curation.json`).
Writes `new_table.json` (full A4:E matrix) and `summary.json` (`unique`, `verified`, `unverified`,
`placed`, `data_range`, `banner`, `plus30`, `pruned`).

### 6. Write back (Composio)
```bash
# A) data region — use summary.json data_range, e.g. A4:E283. USER_ENTERED so counts are numeric.
python3 -c "import json;t=json.load(open('new_table.json'));json.dump({'spreadsheet_id':'$SID','range':'Church Count (Normalized)!A4:E283','value_input_option':'USER_ENTERED','values':t},open('pl.json','w'),ensure_ascii=False)"
composio execute GOOGLESHEETS_VALUES_UPDATE -d @pl.json
# B) if the table SHRANK, clear the now-empty trailing rows:
composio execute GOOGLESHEETS_SPREADSHEETS_VALUES_BATCH_CLEAR -d "{\"spreadsheet_id\":\"$SID\",\"ranges\":[\"Church Count (Normalized)!A284:E997\"]}"
# C) banner A1 (summary.json "banner"; append the running "dropped (cumulative)" tally)
# D) Churches with 30+ tab: header A1 count + rows A4:C{n} from summary.json plus30 + C{n+1}==SUM; clear extras
# E) Cities tab: append any NEW city (City | Country | =SUMIF formula) not already in column A (rows from A93+)
```
Then **append a dated `Update Log` row** (Date/Time PHT · Action · Unique Churches · Attendees Placed ·
People Stated · Raw Strings Dropped · New Churches · Notes) and **update AGENTS**: refresh §5's
"Latest (date): …" line and §5c acronym text if needed. PHT time: `TZ='Asia/Manila' date '+%Y-%m-%d %H:%M PHT'`.

### 7. Report
New unique-church count + net change, new churches, merges, prunes, and judgment calls worth auditing.

## Gotchas
- **`H1`/`E1` are live** — only write `A4:E<last>`, `A1`, and the other tabs. Never write H1.
- **Counts go DOWN too** — cancellations are real; a row dropping to 0 is usually a cancellation, not a bug. Probe the MASTERLIST for that church's strings before assuming error.
- **Fragment-duplicate zeros**: brand already has a populated sibling row; their variants are folded into the sibling on prune so the audit trail survives.
- **`USER_ENTERED`, not RAW**, for the data write — otherwise the Attendees column stores as text and the Cities `SUMIF`/30+ `SUM` break.
- **`Cities` counts auto-update** via SUMIF, but only for cities already listed — append genuinely new cities or they're untallied (and `Cities!B2` undercounts).
- **Some `Merged variants` cells are truncated with a literal `…`** — older spellings re-surface as uncaptured; just re-classify them to the right row.

## Verification
After writing: re-read `H1` (must equal `summary.json` `unique`) and confirm `=SUM(D4:D<last>)` equals
`placed`. Spot-check 2–3 changed rows and the 30+ `SUM`.
