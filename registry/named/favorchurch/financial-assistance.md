---
id: favorchurch/financial-assistance
name: Financial Assistance
contributor: favorchurch
origin: false
genericSkillRef: grant-application-processing
status: named
level: 1★
description: Process financial assistance applications - coupon assignment, request
  tracking, and updates.
createdAt: '2026-07-14'
updatedAt: '2026-07-14'
title: Financial Assistance
links:
  github: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/financial-assistance/SKILL.md
timeline:
- timestamp: '2026-07-13T16:26:04Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill favorchurch/financial-assistance
- timestamp: '2026-07-13T16:34:45Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/financial-assistance/SKILL.md
    (type: self-attestation)'
- timestamp: '2026-07-13T16:48:01Z'
  action: demote
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 1★
evidence:
- source: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/financial-assistance/SKILL.md
  evaluator: favorchurch
  date: '2026-07-14'
  type: self-attestation
  trustNumber: 10.0
  notes: Self-attestation of financial-assistance skill implementation
  grade: C
verification:
  firstEvidenceAt: '2026-07-13T16:34:45Z'
---

# Financial Assistance

## Overview

Process Favor Church conference financial assistance requests end to end: read the Fluro kanban, calculate exact discounts from live ticket prices and applicant pay amounts, update the tracker Sheet, assign coupon codes, draft emails from the correct sender, then send and close kanban cards only after user gives the go-signal.

Core rule: never guess the applicant, event, ticket price, sender, coupon tier, or sent status. Verify each live system before writing.

## Prerequisites

Each requirement below is a **capability bucket** — any one of the listed tools satisfies it. Run this preflight before any phase. If a **Required** bucket has no connected tool, explain what it is, why this skill needs it, and how to connect one of the options, then **stop and ask the user to set it up** before continuing — never guess a price, coupon, or sender to work around a missing tool.

| Capability | Type | Satisfied by (any one) | If missing |
|---|---|---|---|
| **Fluro Access** (`kanban`, `item`, `update`) | Required | Fluro for Favor Church MCP | The requests live on the `mnlFinancialAssistanceRequests` board; without it there is nothing to intake or close. Ask the user to connect Fluro, then wait. |
| **Google Sheets Access** | Required | Composio (`GOOGLESHEETS_*`) · `gws` CLI · Google Sheets MCP | The tracker (`REQUESTS`) and coupon tabs live in Sheets. Ask the user to connect a Sheets-capable tool, then wait. |
| **Gmail Draft Access** (send-as `conferences@favor.church`) | Required for Phases 5 & 7 | Gmail MCP/CLI with send-as · Composio Gmail with verified send-as · `gws` CLI | Drafts/sends must come from the correct sender. If no connected tool can enforce the `From` address, **do not create wrong-sender drafts** — give the user install/auth instructions plus ready-to-send text instead (see Sender Enforcement). |
| **Event Tickets Access** | Required for live prices (has fallback) | Favor Event Tickets MCP · *fallback:* the official event page (e.g. `favor.church/conference`) | Used to read live ticket prices for the discount math. If missing, fall back to the official event page and tell the user; only use user-provided prices if they explicitly confirm. |
| `speak-like-favor` skill | Recommended | the `speak-like-favor` skill | Keeps coupon emails in Favor voice + the standout coupon block. If absent, apply the HTML rules inlined in Phase 5. |

## Fixed Systems

| System | Value |
| --- | --- |
| Fluro board | `64afa26a6a4b2c0033c9bccf` / `mnlFinancialAssistanceRequests` |
| Board title | `MNL | Financial Assistance Requests` |
| Spreadsheet | `1gWT7fB-TWRQwIHrlxpAjBo7scHBbIqlAcxSyUdmt9So` |
| Tracker tab | `REQUESTS` unless user specifies otherwise |
| Default sender | `conferences@favor.church` |
| No-browser rule | Do not use Chrome, browser automation, or manual web UI control |

Use Fluro MCP first, Google Sheets MCP or `gws`/Composio for Sheets, Gmail MCP or a CLI/MCP that can enforce send-as for email, and Event Tickets MCP or the official event page for live ticket prices.

Default to a dry-run summary if the user asks to “check,” “review,” or “process” without explicitly authorizing writes. Proceed with writes when the user asks to update, draft, assign, move, send, or otherwise complete a phase.

## Resolve Event And Tabs

1. Read the Fluro board with `kanban.boards` using search text such as `Financial Assistance`; verify the returned `_id` is `64afa26a6a4b2c0033c9bccf`.
2. Determine the event from the process criteria and linked submission `rawData.event`.
3. If multiple events or tabs could apply, ask user which event/tab before writing.
4. Map event to tabs by convention and Sheet metadata. Examples:
   - Favor Conference 2026 → `REQUESTS`, `FC26-COUPONS`, `FC26-EmailTemplate`
   - If no obvious match, ask or suggest.

## Email-Approved Requests (Gmail exception)

When a financial assistance request is **approved directly over email** (e.g. handed off from the `triage-conference` workflow as a follow-up) and there is **no matching card on the Fluro board**, do NOT block on Fluro:

- Skip Fluro intake and Fluro close entirely for that applicant. A missing board card is expected and fine here.
- Assign the coupon **directly** from the coupon tab (Phase 4) and **add the full row to the tracker Sheet** (Phase 3), including the coupon code, so the code is drawn and recorded exactly once.
- Draft/send the coupon email (Phases 5 & 7) as usual, in the applicant's email thread.
- Determine the discount from the applicant's stated pay amount. If the amount is not in the email, use the tier already issued for the **same requester's group / their prior coupons** (check the tracker for their email), or ask for the exact amount. Never round to a nearby tier.

This is an explicit exception to the board-first flow: email-approved requests are legitimate without a Fluro card. Everything else (exact-discount math, one coupon per applicant, tracker recording, sender enforcement) still applies.

## Phase 1: Intake New Cards

1. From the board, select only cards with `stateKey: "new"`.
2. For each card, fetch the process record, then fetch its linked interaction from the process `item` field.
3. Extract from `interaction.rawData.contact`:
   - first name, last name, email, phone, church, ticket type, amount able to pay, reason
   - event from `rawData.event`
   - process card id and interaction id
4. Match by actual submission details, not by card title. The card title is generic.
5. Save all inspected New items to a CSV in the current project directory or as an artifact before writing Sheets. Name it like `FC26_financial_assistance_new.csv` or `<event-code>_financial_assistance_new_<YYYYMMDD>.csv`.

Do not move cards in this phase.

## Clarification Rules

Move a card to `step_4` / “Clarification Needed” and report the reason when any of these are true:

| Issue | Why |
| --- | --- |
| Missing or invalid email | Cannot draft/send safely |
| Missing ticket type | Cannot determine ticket cost |
| Missing, non-numeric, or ambiguous pay amount | User said the amount they put is exactly honored |
| Pay amount is greater than live ticket cost | Discount would be negative |
| Event is missing or mismatched | Wrong template/coupon risk |
| No matching template tab | Email cannot be generated faithfully |
| No available coupon for computed discount | Cannot honor the exact approved discount |
| Duplicate applicant/card ambiguity | Risk of assigning the wrong coupon |

For clarification cards: do not add to the live tracker, do not allocate a coupon, and do not draft an email unless Rico explicitly decides the missing value.

## Phase 2: Live Ticket Prices

Calculate discounts from live ticket prices.

Preferred order:
1. Event Tickets MCP for the event and ticket types.
2. Official event page, such as `favor.church/conference`, when MCP is unavailable.
3. User-provided prices only if user explicitly confirms.

Formula:

```text
amount_to_pay = exact numeric value from the applicant
discount = live_ticket_cost(ticket_type) - amount_to_pay
```

Examples:

| Ticket Cost | Applicant Can Pay | Discount |
| --- | ---: | ---: |
| Adult `1000` | `100` | `900` |
| Student `250` | `100` | `150` |
| Adult `1000` | `0` | `1000` / full discount |

Do not round to a nearby coupon tier. If the exact discount tier does not exist, treat it as clarification/no available coupon.

## Phase 3: Update REQUESTS

1. Read Sheet metadata and the target tab headers first.
2. Infer columns by header names, not fixed column letters.
3. Append or fill rows only for non-clarification applicants.
4. Include the raw applicant data, event, ticket type, amount to pay, calculated discount, coupon code once assigned, process card id, and email fields where matching headers exist.
5. Leave the `Sent` checkbox unchecked until the email is actually sent.

After writing, re-read the inserted rows and confirm:
- row count matches processed applicants
- names, emails, ticket types, pay amounts, discounts, and coupon codes are correct
- `Sent` remains unchecked before go-signal

## Phase 4: Assign Coupons

1. Read the coupon tab headers and enough rows to find coupon blocks.
2. Identify coupon blocks by header text:
   - `FULL DISCOUNT` means full discount
   - `P900 off`, `P150 off`, etc. map to numeric discounts
3. For each applicant, find the block matching the exact discount amount.
4. In that block, find the first row where:
   - coupon code exists
   - `Used?` cell is `FALSE` or unticked
   - `Gave To` cell is blank
5. Write:
   - `Used?` = `TRUE`
   - `Gave To` = full name
6. Record the coupon code back into the tracker row.

Use one coherent Sheets batch when practical, but avoid a huge mixed batch. Re-read the edited coupon cells after writing.

Do not delete old coupon columns unless user specifically asks. If old event columns interfere with the active coupon generator, report them first and ask.

## Phase 5: Draft Emails

1. Read the event email template tab, such as `FC26-EmailTemplate`.
2. Use the template’s own `FROM`, `SUBJECT`, `BODY`, `CC`, and `BCC` fields.
3. Replace placeholders with:
   - name
   - ticket type
   - coupon code
   - discount amount with `₱`
   - amount to pay with `₱`
4. Draft as **HTML** (`is_html: true`), never plain text with markdown. Apply `speak-like-favor` Email Rendering:
   - **Render the coupon code in a large, bold standout block** (not inline plain text), regardless of whether the template emphasizes it. Example:
     ```html
     <div style="font-size:34px;font-weight:bold;letter-spacing:3px;color:#E8740C;background:#FFF4E8;border:2px dashed #E8740C;border-radius:10px;padding:18px;text-align:center;margin:18px 0;font-family:monospace;">FC26-XXXX-900</div>
     ```
   - **Make every link clickable:** `<a href="https://favor.church/conference#tickets">favor.church/conference#tickets</a>` (clean visible text, full URL in href).
   - Bold names and amounts with `<strong>`; use `<ol>`/`<ul>` for steps, never `-`/`*` or `**`.
   - Keep the footer/signature if the sender account applies it.
5. Footer must include gmail sender's default signature.
   - If this cannot be done, try checking recent emails from sender for signatures and copy that. Confirm with user noting this approach.
6. Create drafts only unless user gave an explicit go-signal to send.

### Sender Enforcement

Sender must be the template `FROM` value, normally `conferences@favor.church`.

Preferred order:
1. Gmail MCP/CLI method that supports send-as/from.
2. `gws` or Composio Gmail action with a raw MIME `From:` header and verified send-as support.
3. If available tools cannot enforce `From`, do not create wrong-sender drafts. Give user:
   - exact install/auth instructions for a CLI/MCP that can set Gmail send-as
   - ready-to-send subject/body/recipient drafts as text

Never use browser automation or the user’s Chrome/Gmail UI to fix sender. Browser use is forbidden for this workflow.

After drafting, verify every draft:
- `From` is the required sender
- `To`, `CC`, and `BCC` match the template
- subject contains the applicant name
- body contains the correct coupon, discount, and amount to pay

## Phase 6: Review Checkpoint

Before sending, report:
- applicants processed
- clarification cards moved, with reasons
- CSV path
- tracker row numbers
- coupon codes assigned
- draft ids or draft status
- verification results

Do not send email, mark `Sent`, or move processed cards to `couponSent` until user gives a go-signal.

## Phase 7: Go-Signal Send And Close

After user explicitly says to send/proceed:

1. Send the verified drafts from the required sender.
2. Search/list sent messages and verify:
   - count equals processed applicants
   - `from` is the required sender
   - each recipient received the expected subject/coupon
3. Move only successfully sent cards to `couponSent` / “Email & Coupon Sent”.
4. In `REQUESTS`, tick the `Sent` checkbox for those rows.
5. Add a Google Sheets note to each `Sent` cell, using the cell `note` field, with the sent date and sender, for example:

```text
Sent via conferences@favor.church on Tuesday, May 26, 2026, 12:02PM
```

Use Manila time for sent notes unless Rico requests another timezone.

If any email fails to send, do not move that card or mark it sent. Report the failed applicant and reason.

## Verification Checklist

| Area | Verify |
| --- | --- |
| Fluro intake | Board id, state keys, linked interaction ids, event |
| Clarifications | Moved to `step_4`, no coupon/draft allocated |
| CSV | File exists, row count matches New items inspected |
| Prices | Source and ticket costs recorded |
| REQUESTS | Rows inserted, values correct, `Sent` unchecked before send |
| Coupons | Exact tier, `Used?=TRUE`, `Gave To` full name, coupon copied to tracker |
| Drafts | Required sender, recipients, CC/BCC, subject, placeholders, formatting |
| Sending | Sent search confirms exact count and required sender |
| Closing | Only sent cards moved to `couponSent`; `Sent` checkbox ticked with date note |

## Common Mistakes

| Mistake | Correct Behavior |
| --- | --- |
| Moving all New cards | Move only cards matched to processed/sent applicants |
| Treating generic card titles as people | Fetch linked interactions for real data |
| Interpreting `YES`, `.`, blank, or text as `0` | Clarification needed |
| Using stale ticket prices | Verify live prices first |
| Rounding to nearest coupon tier | Exact discount only |
| Creating drafts from `rico@favor.church` | Stop and install/auth sender-capable tooling |
| Marking `Sent` after draft creation | Mark only after actual sent-message verification |
| Using browser UI to fix Gmail sender | Forbidden; use MCP/CLI or provide manual drafts |
| Deleting old coupon columns automatically | Ask before cleanup |

## Quick Fluro Reference

Board states:

| Key | Title | Use |
| --- | --- | --- |
| `new` | New Requests | Intake source |
| `step_4` | Clarification Needed | Invalid/missing data |
| `couponSent` | Email & Coupon Sent | Only after email sent |
| `noCoupon` | No Coupon | Only if Rico decides no coupon |
| `eventFinished` | Event Finished | Not part of normal processing |

Kanban move shape:

```json
{
  "action": "move",
  "cardIds": ["<process-card-id>"],
  "toStateKey": "couponSent"
}
```

Use the process card `_id`, not the linked interaction `_id`, when moving kanban cards.
