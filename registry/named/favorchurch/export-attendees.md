---
id: favorchurch/export-attendees
name: Export Attendees
contributor: favorchurch
origin: false
genericSkillRef: event-attendee-management
status: named
level: 1★
description: Sync and export attendee data from Favor Event Tickets into a Google
  Sheets masterlist.
createdAt: '2026-07-14'
updatedAt: '2026-07-14'
title: Export Attendees
links:
  github: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/export-attendees/SKILL.md
timeline:
- timestamp: '2026-07-13T16:26:02Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill favorchurch/export-attendees
- timestamp: '2026-07-13T16:34:35Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/export-attendees/SKILL.md
    (type: self-attestation)'
- timestamp: '2026-07-13T16:47:52Z'
  action: demote
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 1★
evidence:
- source: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/export-attendees/SKILL.md
  evaluator: favorchurch
  date: '2026-07-14'
  type: self-attestation
  trustNumber: 10.0
  notes: Self-attestation of export-attendees skill implementation
  grade: C
verification:
  firstEvidenceAt: '2026-07-13T16:34:35Z'
---

# Export Attendees Skill

Exports the full attendee CSV from Favor Event Tickets and pastes it (values only) into the matching Google Sheets masterlist, then updates the "Last Updated" timestamp.

---

## Prerequisites

Each requirement below is a **capability bucket** — any one of the listed tools satisfies it. Run this preflight before exporting. If a **Required** bucket has no connected tool, explain what it is, why this skill needs it, and how to connect one of the options, then **stop and ask the user to set it up** before continuing — never paste partial or fabricated rows.

| Capability | Type | Satisfied by (any one) | If missing |
|---|---|---|---|
| **Event Tickets Access** (`attendees` with `action: "csv"`) | Required | Favor Event Tickets MCP | Source of the attendee CSV. Ask the user to connect it (e.g. `mcp oauth login favor-event-tickets`), then wait. |
| **Google Sheets Access** (+ Composio Remote Workbench for the paste) | Required | Composio `GOOGLESHEETS_*` (this skill's flow assumes the Composio workbench) | Needed to locate the masterlist and paste values in chunks. Ask the user to connect the `googlesheets` toolkit in Composio, then wait. |
| **Shell & Python** (bash + `curl` with a browser User-Agent) | Required | a terminal with `bash`, `curl`, and Python 3 | The signed CSV URL returns HTTP 403 to default User-Agents and expires in ~15 min. Without a shell, the CSV can't be downloaded. |

---

## Workflow

### Step 0 — Resolve the target event

Decide which event to export **before** anything else. Never assume a specific conference.

1. **If the user named an event** (this message or earlier in the conversation), use that as the `event_query` and skip to Step 1.

2. **If no event was named** (e.g. "sync the sheet", "update attendees", "do it again" with no prior event in context), auto-resolve the default to **the current conference** from the live event list — do NOT hardcode one:

   ```
   Favor Event Tickets:events
     action: "search"
     query: "conference"
     per_page: 50
   ```

   From the results, pick the **soonest upcoming conference**: the event with "conference" in its title whose `end_date` has **not yet passed** (`end_date` >= today, Asia/Manila UTC+8), choosing the one with the earliest `start_date`. That becomes the `event_query`.

   Worked example (today = 2026-06-30):
   - Favor Conference 2026 ends 2026-07-04 → not passed → **selected default**.
   - Worship Conference 2026 (ended 2026-04-18) and High School Conference 2026 (ended 2026-03-07) → past → skipped.
   - On/after 2026-07-05, Favor Conference 2026 is past, so the default rolls forward to the next conference whose end date hasn't passed (whatever it is — Worship/High School/Favor, soonest wins).

Announce the resolved event in your first reply (e.g. "No event specified — defaulting to the current conference: **Favor Conference 2026** (ends Jul 4, 2026)"), then continue **end-to-end without a confirmation prompt** — the only thing that pauses for confirmation is a missing sheet (Step 3).

### Step 1 — Get the CSV download URL

Use `Favor Event Tickets:attendees` with the event name. This returns a temporary download URL (expires in 15 minutes, per the response's `expires_in: 900` — still download promptly) and the total attendee count.

```
Favor Event Tickets:attendees
  action: "csv"
  event_query: "<resolved event from Step 0>"
```

Note the `total_attendees` from the response — this is the completed-tickets count for the final report.

### Step 2 — Peek at the CSV header only (bash)

This step is **only** to learn the header + row count. The full data is downloaded and processed **inside the Remote Workbench** in Step 6 — never here.

```bash
curl -s -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" "<download_url>" -o /tmp/attendees.csv
head -1 /tmp/attendees.csv   # header row only
wc -l /tmp/attendees.csv     # total row count
```

Read **only** the header row here — do NOT load all rows into context. Keep the `<download_url>` handy: the Remote Workbench will re-download it (still valid within the 15-min window) so the row data never enters Claude's context.

### Step 3 — Find the Google Sheet

Use `GOOGLESHEETS_SEARCH_SPREADSHEETS` (via Composio) to locate the sheet by the **resolved event name** (e.g. "Favor Conference 2026"). Capture the `spreadsheet_id`.

Then use `GOOGLESHEETS_GET_SHEET_NAMES` to list all tabs — identify the one that looks like a masterlist (usually named "MASTERLIST" or similar).

- **Sheet found** → continue to Step 4 end-to-end, no confirmation needed.
- **No sheet matches the event name** → do NOT fall back to another conference's sheet or guess. Stop and ask the user to confirm creating a fresh masterlist (Step 3b). Proceed only after they say yes.

### Step 3b — Create the masterlist (only if none exists)

Run this **only** when Step 3 finds no sheet for the resolved event, and **only after the user confirms**.

Create a new spreadsheet titled `<Event Name> Attendees` (e.g. "Favor Conference 2026 Attendees") with a `MASTERLIST` tab, modeled on the most recent prior conference masterlist (see the cache table at the bottom) so downstream formulas/filters line up:

- **Header row at row 4:** the CSV column names, in CSV order
- **Data starts at row 5**
- A **timestamp cell** in the top rows (rows 1–3), updated in Step 7

Use `GOOGLESHEETS_CREATE_SPREADSHEET` (then write the row-4 headers and a timestamp cell). Capture the new `spreadsheet_id` and continue to Step 4. Note: a freshly created sheet has no SUMMARY dashboard or count formulas — tell the user those still need to be built; this skill only fills the MASTERLIST.

### Step 4 — Read sheet headers & locate the timestamp cell (detect, never hardcode)

Fetch the top rows of the masterlist tab with `GOOGLESHEETS_BATCH_GET`, range `MASTERLIST!A1:Z6`, then detect:

1. **Header row** — the row whose values match the CSV header (contains "Ticket", "First Name", etc.). Do not assume row 4 — confirm it from the data.
2. **First data row** — header row + 1.
3. **Timestamp cell** — find it dynamically, in this priority order. **Never hardcode `B1`.**
   - **(a)** If a text label like `Last Updated` / `Updated` / `Last Refreshed` / `Timestamp` appears in the top rows → the timestamp cell is the cell **immediately to its right**.
   - **(b)** Else, if this event has a row in the cache table (bottom of this file) with a known timestamp cell → use that.
   - **(c)** Else, scan the rows above the header for the cell holding the **most recent date-time value** and update that cell in place (e.g. if `A2` holds an older date and `B2` a newer one, the live timestamp cell is `B2`).
   - Many of these sheets feed a **SUMMARY dashboard** whose "live count" time reads from this exact cell — so update the existing cell, do not invent a new one.

Report to the user: the header row, the first data row, and **which exact cell** you will write the timestamp to (e.g. "Headers at row 4, data from row 5, timestamp cell = B2").

### Steps 5–6 — Parse + paste, ENTIRELY inside the Remote Workbench

> 🚫 **HARD RULE — the row data must NEVER pass through Claude's context or a tool call's arguments.**
> All CSV downloading, parsing, column mapping, and the chunked write happen as Python **inside one `COMPOSIO_REMOTE_WORKBENCH` session**. Read these anti-patterns first — they are exactly how past runs failed:
> - ❌ Do NOT build `values` arrays in your own context and pass them to `GOOGLESHEETS_UPDATE_VALUES_BATCH` (via `COMPOSIO_MULTI_EXECUTE_TOOL` or otherwise). The payload (~0.25 MB/chunk) blows the token budget and the run dies or fabricates.
> - ❌ Do NOT write **empty `values` arrays** "to test" — that silently blanks rows.
> - ❌ Do NOT claim the paste succeeded without the read-back in Step 7.5.
> - ✅ The workbench `curl`s the signed URL itself, parses the file on disk, and calls the Sheets API from inside the sandbox. Claude only ever sees the header + counts + a success log.

**Step 5 — column mapping (in the workbench):** parse the CSV header, compare to the sheet header row, and build `{csv_col_index: sheet_col_index}`:
- Match by column name (case-insensitive, trimmed).
- Columns in **both** → keep the sheet's existing column index (never shift positions).
- Columns **only in CSV** → append to the right of the last sheet column.
- Columns **only in the sheet** → leave untouched (do not overwrite).

**Step 6 — chunked write (in the workbench):** download the full CSV inside the workbench, write all rows (including cancelled) in 300-row chunks, `RAW` input, 1.2 s between chunks.

```python
# Runs INSIDE COMPOSIO_REMOTE_WORKBENCH. SIGNED_URL / SPREADSHEET_ID / HEADER_ROW
# / SHEET_LAST_COL passed in as small strings. Row data stays in the sandbox.
import csv, io, time, subprocess
raw = subprocess.run(["curl","-s","-A","Mozilla/5.0","-L",SIGNED_URL],
                     capture_output=True, text=True).stdout
rows = list(csv.reader(io.StringIO(raw)))
header, data_rows = rows[0], rows[1:]          # data_rows = ALL statuses
assert data_rows, "CSV had no data rows — abort, do NOT write empty arrays"
# ... apply the Step-5 column mapping to reorder each row into sheet columns ...
CHUNK, data_start = 300, HEADER_ROW + 1
for i in range(0, len(data_rows), CHUNK):
    chunk = mapped[i:i+CHUNK]
    start = data_start + i
    rng = f"'MASTERLIST'!A{start}:{SHEET_LAST_COL}{start+len(chunk)-1}"
    run_composio_tool("GOOGLESHEETS_UPDATE_VALUES_BATCH", {
        "spreadsheet_id": SPREADSHEET_ID, "valueInputOption": "RAW",
        "data": [{"range": rng, "values": chunk}]})
    time.sleep(1.2)
print(f"wrote {len(data_rows)} rows, {data_start}..{data_start+len(data_rows)-1}")
```

### Step 7 — Update the timestamp (the exact cell detected in Step 4)

Write the current Manila time (UTC+8) to the **timestamp cell located in Step 4** — the cell to the right of the "Last Updated" label, or the detected/cached live-timestamp cell (e.g. `B2`). **Never default to `B1`.** Update only *after* the paste succeeds, so the timestamp doesn't claim a refresh that didn't finish.

Format: `M/D/YYYY HH:MM:SS` — use `USER_ENTERED` so Sheets parses it as a date. Do not touch the SUMMARY tab or any segment tab; they recompute from MASTERLIST automatically.

### Step 7.5 — Verify before reporting (mandatory — do NOT skip)

A paste is not "done" until read back. Fetch from the live sheet and confirm all of:

1. **Last data row** — `GOOGLESHEETS_BATCH_GET` for the first column from `data_start` downward; the last populated row must equal `data_start + (CSV data rows) − 1`. A short fall-off means the paste truncated → re-run Step 6, do not report success.
2. **Column alignment** — spot-check a mid-sheet row (e.g. row 100): a known column (First Name / Order Status) is populated and in the right place.
3. **SUMMARY count** — read the SUMMARY tab's headline totals (and/or the MASTERLIST top-area count cells). They must be **non-zero** and consistent with `total_attendees` from Step 1 (allow small drift — registrations are live). Zeros or wildly-off numbers mean the **MASTERLIST data/paste is wrong → fix THAT and re-paste.**
4. **Timestamp** — the cell from Step 4 now shows the time you wrote.

> ⛔ **INTEGRITY GUARDRAIL — never edit SUMMARY (or the count cells) to hit the target.** The SUMMARY tab and the MASTERLIST top-area count cells are formula-driven, **read-only indicators** — they are how you *check* the result, never something you *write* to in order to pass. You must NEVER replace a formula with a literal value, hardcode a number, or alter a formula so it outputs the expected total. The count is correct **only** as a side effect of a complete, correctly-aligned MASTERLIST paste — never by touching the summary. If a count is wrong, the fault is in the MASTERLIST data; fix the paste, not the summary. **Doctoring the summary to fit the target is data falsification and a FAILED run, even if the numbers then look right.**
>
> **One narrow exception:** if your paste genuinely **shifted MASTERLIST column positions** (e.g. a new column landed mid-table), a SUMMARY formula that points at specific MASTERLIST columns may now read the wrong column. You MAY update that formula's **range/column references** so it reads the correct, shifted columns again — that repairs the formula to compute *honestly*. You still may NOT change what it computes or force a value. Better: avoid shifting existing columns at all — append new CSV columns to the right (Step 5 merge rule) so SUMMARY formulas keep working untouched and this exception never applies.

If any check fails, **say so plainly and fix the underlying paste** — never fabricate a count or a spreadsheet ID, never edit SUMMARY to fake a pass, never report "success" on an unverified or partial paste.

### Step 8 — Report

Summarize with **real, read-back values only**:
- Total rows in CSV (all statuses) · completed · cancelled
- Rows actually written + the verified last row
- Any new columns added
- SUMMARY headline count (post-paste) vs `total_attendees`
- Timestamp value + the exact cell it was written to

---

## Default event & per-event sheet cache

**The default event is resolved at runtime in Step 0** — the soonest conference whose end date hasn't passed. No conference below is a permanent default; the cache is only a shortcut for repeat exports.

Sheet coordinates are discovered dynamically in Steps 3–4. Add a row here once you confirm a new event's layout. The most recent filled row also serves as the template when creating a new masterlist (Step 3b).

Timestamp cells differ per sheet — Step 4 **detects** it; the column below is a recorded reference, not a thing to hardcode in code.

| Event | Spreadsheet ID | Tab | Header row | Data starts | Timestamp cell | Columns |
|---|---|---|---|---|---|---|
| Favor Conference 2026 *(current default)* | `1WDJTxOHaGLiBgJa5Jc5oYQETYPZmoA9nM7f_ct2947Y` | MASTERLIST | Row 4 | Row 5 | **B2** (feeds SUMMARY `C2`; `A2` = prior "as of" baseline) | A–BG (59) |
| Worship Conference 2026 *(past — layout reference)* | `1XtIpt-mRAvDbTQ5Q7EqlmkCXNh0REAfaZGv-FiuZDZU` | MASTERLIST | Row 4 | Row 5 | B1 | A–V (22); CSV adds `Purchase Date` as col W |

Links: [Favor Conference 2026 Attendees](https://docs.google.com/spreadsheets/d/1WDJTxOHaGLiBgJa5Jc5oYQETYPZmoA9nM7f_ct2947Y/edit) · [Worship Conference 2026 Attendees](https://docs.google.com/spreadsheets/d/1XtIpt-mRAvDbTQ5Q7EqlmkCXNh0REAfaZGv-FiuZDZU/edit)

The Favor Conference 2026 sheet has extra tabs that this skill must **not** write to: a **SUMMARY** dashboard (formula-driven "CONFERENCE LIVE COUNT" — recomputes from MASTERLIST), segment tabs (GENLUNCH, YOUTH, OPEN ACCESS, NEW PEOPLE, …), and a reserved **`Claude Cache`** tab (used by `=CLAUDE` sheet functions — never edit it). Only MASTERLIST + its timestamp cell are written.

---

## Notes & Gotchas

- **CSV token expires in 15 minutes** (`expires_in: 900`) — still download promptly after fetching the URL. Don't read the headers first and then re-fetch.
- **Programmatic download needs a browser User-Agent** — the signed URL returns HTTP 403 to default UAs (Cloudflare/WAF). Fetch with `curl -A "Mozilla/5.0 ..."` or equivalent.
- **Cancelled rows are included intentionally** — do not filter them out.
- **"Tickets are non-refundable" column** is mostly blank in the CSV — this is a known server-side data issue, not a paste error.
- **Rate limits:** Google Sheets allows ~60 writes/min. The 300-row chunk + 1.2s delay keeps writes safe.
- **Process the full CSV only in the Remote Workbench** — never in Claude's context window. Row data must never be passed as tool-call arguments. (This is the #1 past failure mode: agents either fabricated a result or died on token limits trying to inline the payload.)
- **Never write empty `values` arrays** — not even "to test." It silently blanks rows. If the parsed CSV has zero data rows, abort and report.
- **Column merge rule:** Never shift existing column positions. New CSV columns go to the right of the last sheet column.
- **Never fabricate** spreadsheet IDs, counts, or "success." Every value reported comes from a real read-back (Step 7.5).
- **Don't touch SUMMARY / segment / `Claude Cache` tabs.** SUMMARY and segment tabs are formula-driven and recompute from MASTERLIST. `Claude Cache` is reserved for `=CLAUDE` functions — editing it breaks them. **Never write into SUMMARY (or the count cells) to force a total to "match"** — that's data falsification (see the integrity guardrail in Step 7.5). The lone exception is re-pointing a formula's column references after a genuine column shift — never changing the value it computes.
- **Success criterion:** the paste is only complete when the **SUMMARY tab shows correct, non-zero counts** consistent with the live attendee total, MASTERLIST is fully populated (verified last row), and the timestamp cell is updated.
