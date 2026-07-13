---
id: favorchurch/ticket-transfer
name: Ticket Transfer
contributor: favorchurch
origin: false
genericSkillRef: event-ticket-transfer
status: named
level: 1★
description: End-to-end workflow for processing ticket transfer requests, updates,
  and confirmation emails.
createdAt: '2026-07-14'
updatedAt: '2026-07-14'
title: Ticket Transfer
links:
  github: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/ticket-transfer/SKILL.md
timeline:
- timestamp: '2026-07-13T16:26:04Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill favorchurch/ticket-transfer
- timestamp: '2026-07-13T16:34:48Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/ticket-transfer/SKILL.md
    (type: self-attestation)'
- timestamp: '2026-07-13T16:48:04Z'
  action: demote
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 1★
evidence:
- source: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/ticket-transfer/SKILL.md
  evaluator: favorchurch
  date: '2026-07-14'
  type: self-attestation
  trustNumber: 10.0
  notes: Self-attestation of ticket-transfer skill implementation
  grade: C
verification:
  firstEvidenceAt: '2026-07-13T16:34:48Z'
---

# Ticket Transfer Workflow

Full pipeline for processing MNL ticket transfer requests.

## Prerequisites

Each requirement below is a **capability bucket** — any one of the listed tools satisfies it. Run this preflight before processing transfers. If a **Required** bucket has no connected tool, explain what it is, why this skill needs it, and how to connect one of the options, then **stop and ask the user to set it up** before continuing — never perform a partial transfer or fake a draft.

| Capability | Type | Satisfied by (any one) | If missing |
|---|---|---|---|
| **Fluro Access** (`kanban`, `events`, `item`) | Required | Fluro for Favor Church MCP | The transfer requests live on the `mnlTicketTransfers` kanban; without it there is nothing to process. Ask the user to connect/authenticate Fluro, then wait. |
| **Event Tickets Access** (`attendees`) | Required | Favor Event Tickets MCP | Needed to look up the transferer/transferee records and perform the actual attendee update. Ask the user to connect it (e.g. `mcp oauth login favor-event-tickets`), then wait. |
| **Gmail Draft Access** (send-as `conferences@favor.church`) | Required for Step 7 | Gmail MCP (`create_draft`) · Composio Gmail (`GMAIL_CREATE_EMAIL_DRAFT`) · `gws` CLI · any send-as-capable Gmail CLI/MCP | Needed to draft completion/inquiry emails. You may still complete Steps 1–6 without it — if no tool is connected, do the transfers, then tell the user the email-draft step is blocked and hand them ready-to-paste subject/body text instead. |
| `speak-like-favor` skill | Recommended | the `speak-like-favor` skill | Keeps email drafts in Favor voice. If absent, still apply the HTML/voice rules inlined in Step 7. |

---

## Step 1 — Fetch New & Pending Kanban Cards

Call the Fluro kanban tool:

```
Fluro for Favor Church:kanban
  action: "boards"
  search: "mnlTicketTransfers"
```

This returns the board definition including all cards. Filter cards where `stateKey` is **`newRequests`** or **`pending`** only. Ignore `completed` and `noTransfer`.

If no cards match, report: "No new or pending ticket transfer requests."

---

## Step 2 — Pull Submission Details

The kanban process card holds state/history only. The actual form data is in the linked `interaction` record (`mnlTicketTransferRequest`).

Fetch submissions via:

```
Fluro for Favor Church:events
  action: "formSubmissions"
  definition: "mnlTicketTransferRequest"
  limit: 100
```

Or query directly with a date filter:

```
Fluro for Favor Church:item
  batch: [{ action: "query", body: { "definition": "mnlTicketTransferRequest", "created": { "$gte": "<earliest card created date>" } }, simple: false }]
```

Match each submission to its kanban card via the `item._id` field on the process card == `_id` on the submission.

### For each request, extract and display:

| Field | Source path |
|---|---|
| Event | `data.event` |
| Transferer name | `data.transferer.fullName` |
| Transferer email | `data.transferer.email` |
| Ticket type | `data.transferer.ticketType[Event]` |
| Requester | `data.requester.fullName` + `data.requester.email` (if different from transferer) |
| Requester relationship | `data.requester.relationship` |
| Transferee name | `data.transferee.[eventKey].firstName` + `lastName` |
| Transferee email | `data.transferee.[eventKey].email` |
| Transferee phone | `data.transferee.[eventKey].phoneNumber` |
| Transferee ticket type | `data.transferee.[eventKey].ticketType` |
| Proof of payment | `https://api.fluro.io/get/{data.requester.originalTicketUpload}` |

> ⚠️ Proof of payment links require the user to be logged into Fluro in their browser to view.

Present each request clearly, grouped by card state (New Requests first, then Pending).

---

## Step 3 — Look Up Tickets in Favor Event Tickets

For each request, search the relevant event using **email** for the transferer (more reliable than name), and **full name** for the transferee.

```
Favor Event Tickets:attendees
  action: "query"
  event_query: "<event name>"
  search: "<transferer email>"
  columns: ["id", "title", "email", "ticket_type", "status"]

Favor Event Tickets:attendees
  action: "query"
  event_query: "<event name>"
  search: "<transferee full name>"
  columns: ["id", "title", "email", "ticket_type", "status"]
```

### Interpret results:

| Scenario | Meaning | Action |
|---|---|---|
| Transferer found, transferee not found | Normal — ready to transfer | Proceed |
| Transferer found, transferee already exists | Transferee has a ticket | ⚠️ Flag — do not transfer, see Edge Cases |
| Transferer not found by email | May have been renamed by prior transfer | Search by name as fallback |
| Neither found | Unusual — flag for manual review | |

Present a **summary table** covering all requests:

| # | Event | Transferer | Transferer Record | Transferee | Transferee Pre-exists? | Action |
|---|---|---|---|---|---|---|
| 1 | ... | ... | ✅ #ID / ❌ Not found | ... | ✅ Already registered / ❌ None | Transfer / ⚠️ Investigate |

---

## Step 4 — Await Go-Signal

**Do not perform any writes until Rico explicitly confirms.**

Present the action plan clearly:
- Which attendee IDs will be updated
- From name/email → to name/email
- Which cards will move to which state

Wait for "go", "proceed", "yes do it", or equivalent.

---

## Step 5 — Perform Ticket Transfers

For each approved transfer, call:

```
Favor Event Tickets:attendees
  action: "update"
  attendee_id: <id>
  full_name: "<transferee full name>"
  email: "<transferee email>"
  information: {
    "first-name": "...",
    "last-name": "...",
    "gender": "...",
    "birthdate": "YYYY-MM-DD",
    "age": <int>,
    "mobile-number": "...",
    "which-country-are-you-from": "...",
    "whats-your-church-involvement": "...",
    "do-you-want-to-be-connected-to-our-new-people-team-to-meet-new-friends-during-the-conference": "...",
    "do-you-need-special-assistance-during-the-conference": "..."
    // Student tickets also include: "what-is-your-school-university"
  }
```

**Verify success**: Check that `attendee_after.title` matches the transferee's name. If `attendee_before` == `attendee_after`, the update may not have applied — verify via:

```
Favor Event Tickets:attendees
  action: "get"
  attendee_id: <id>
  include_ticket_fields: true
```

---

## Step 6 — Move Kanban Cards

After confirmed successful transfers:

```
Fluro for Favor Church:kanban
  action: "move"
  cardIds: ["<process card _id>", ...]
  toStateKey: "completed"
```

For blocked/pending cases (e.g. transferee already has a ticket):
```
Fluro for Favor Church:kanban
  action: "move"
  cardIds: ["<process card _id>"]
  toStateKey: "pending"
```

Use the process card `_id` (from the kanban board data), **not** the submission item `_id`.

---

## Step 7 — Draft Emails via Gmail

All emails are from **conferences@favor.church** (Gmail **user 4**).

**Formatting (apply `speak-like-favor` Email Rendering):** draft every email as **HTML** (`is_html: true`), never plain text with markdown. Use `<strong>`/`<ul><li>`/`<p>` (no `**` or `-` bullets), and make any link clickable with `<a href="https://full-url">visible text</a>` (clean lowercase visible text, full URL in the href).

**Tooling note:** Composio `GMAIL_CREATE_EMAIL_DRAFT` works for drafting (`recipient_email`, `extra_recipients`/`cc`, `subject`, `body`, `is_html`). `GMAIL_UPDATE_DRAFT` often fails on thread-reply drafts ("Message not a draft") and `GMAIL_LIST_DRAFTS` under-reports due to indexing lag — verify with `GMAIL_GET_DRAFT` by id, and to fix a draft, delete and recreate it.

Draft link format: `https://mail.google.com/mail/u/4/#drafts?compose={messageId}`

### ✅ Transfer Complete Email

**To**: requester email (or transferer if they submitted themselves)
**CC**: transferee email, and transferer email if a third party submitted
**Subject**: `[Event] | Ticket Transfer Complete — [Transferer Name] → [Transferee Full Name]`

Body should confirm:
- Transfer has been completed
- Transferee's name and email now on the ticket
- Note that the transferee should receive ticket confirmation shortly

Sign off:
```
Much love,
[Event] Team
```

### ⚠️ Inquiry Email (Transferee already has a ticket)

**To**: requester email
**Subject**: `[Event] | Ticket Transfer Request — [Transferer Name]`

Body should:
- Thank them for submitting
- Explain that the intended transferee already appears to be registered
- Offer two options:
  1. Continue the transfer anyway (reply to confirm)
  2. Transfer to a different person (submit new form at **favor.church/tickettransfer**)

Sign off:
```
Much love,
[Event] Team
```

After creating all drafts, present the links to Rico for review before sending.

---

## Edge Cases

### Transferee already has a ticket
- Do **not** perform the attendee update
- Move card to `pending`
- Draft an inquiry email to the requester (see Step 7)
- Flag clearly in the summary

### Third-party requester (Jared-type scenario)
- Note when `requester.areyoutheoriginalticketholder == "No"` and a different person submitted
- The same requester submitting multiple transfers in one batch is normal — handle each independently

### Transferer not found in Event Tickets
- Try searching by name as fallback
- If still not found, note that the ticket may have already been transferred previously or registered under a different email
- Flag for manual review, do not proceed with that request

### kanban move returns 404
- This is an intermittent API issue — retry once before giving up
- The tool uses the process card `_id` (not the interaction item `_id`)

### Gmail delete draft
- The Gmail MCP does not support draft deletion — instruct Rico to delete manually via the draft link
