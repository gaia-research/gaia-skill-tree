---
id: favorchurch/triage-conference
name: Triage Conference
contributor: favorchurch
origin: false
genericSkillRef: event-support-triage
status: named
level: 2★
description: Triage incoming emails, search registrations, match against knowledge
  base, and draft/send replies.
createdAt: '2026-07-14'
updatedAt: '2026-07-14'
title: Triage Conference
links:
  github: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/triage-conference/SKILL.md
timeline:
- timestamp: '2026-07-13T16:26:03Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill favorchurch/triage-conference
---

# triage-conference

Triage unread emails at conferences@favor.church, draft contextual replies that answer attendees' questions accurately, and surface next-step suggestions using Favor Event Tickets and Fluro data.

---

## Prerequisites

Each requirement below is a **capability bucket** — any one of the listed tools satisfies it. Run this preflight before triaging. If a **Required** bucket has no connected tool, explain what it is, why this skill needs it, and how to connect one of the options, then **stop and ask the user to set it up** before continuing — never invent inbox contents or event facts.

| Capability | Type | Satisfied by (any one) | If missing |
|---|---|---|---|
| **Gmail Draft Access** (on the `conferences@favor.church` mailbox) | Required | Gmail MCP (`search_threads`, `get_thread`, `create_draft`) · Composio Gmail (`GMAIL_*`) · `gws` CLI (if its OAuth has read scope) | Phases 1 (fetch unread) and 3 (draft replies) cannot run without it. Ask the user to connect the conferences Gmail, then wait. |
| **Conference KB** (`references/conference-kb.md`, bundled) | Required | the file shipped alongside this skill | Source of truth for event facts and FAQ answers. If not present, stop and ask — do not answer from memory. |
| **Event Tickets Access** (`attendees`, `orders`, `events`) | Required for Phase 4 actions | Favor Event Tickets MCP | Needed to resend tickets, check registrations, and fix wrong emails. If missing, you can still summarize and draft (Phases 1–3); warn that no ticket actions can be taken and ask to connect it for those. |
| **Fluro Access** (`item`, `update`) | Optional (conditional) | Fluro for Favor Church MCP | Only needed when an email requires tagging a contact (e.g. Favor DNA proof). If missing, draft the reply and note the tagging step is pending a Fluro connection. |
| `speak-like-favor` skill | Recommended | the `speak-like-favor` skill | Keeps every draft in Favor voice. If absent, apply the voice/HTML rules inlined in Phase 3. |

---

## Overview

This skill runs a 4-phase pipeline:

1. **Fetch & Summarize** — Search Gmail for unread messages to `conferences@favor.church`
2. **Classify & Answer** — Match each email to a known FAQ scenario and pull the correct answer from the knowledge base
3. **Draft Replies** — Create Gmail drafts in Favor voice for each email that warrants a reply
4. **Take/Suggest Actions** — Cross-reference Favor Event Tickets + Fluro to resend tickets, tag contacts, update records, and recommend follow-ups

**Always answer using the knowledge base in `references/conference-kb.md`. Never invent event facts.** If the KB does not cover something, say so and flag it for Rico rather than guessing.

---

## Phase 1: Fetch Unread Emails

Use the Gmail search tool with the query:

```
to:conferences@favor.church is:unread
```

- Set page size to 20–50 (paginate if more).
- For each result, fetch the full thread to get the body and any attachments.
- Extract: sender, subject, thread ID, body, date.
- Skip automated system mail (invoices, "Here's your ticket", "New ticket booking request", Fluro form-submission notices) unless they need action — note them as "no reply needed".

**Display a triage table:**

| # | From | Subject | Date | Scenario | Summary |
|---|------|---------|------|----------|---------|

---

## Phase 2: Classify & Answer from the Knowledge Base

Before drafting replies, search Gmail for recent successfully sent non-system emails (e.g., `from:me -subject:invoice -subject:booking -subject:"your qr"`) from the last 2–3 days. Reflect on these sent messages to identify the most up-to-date policies, templates, approval patterns, and links used by the team, and let them guide your responses to ensure they match recent actions.

Read `references/conference-kb.md` and match each email to a scenario in §3 of that file. Common recurring scenarios:

- Didn't receive ticket / QR → resend + "check inbox and spam".
- "Is my order confirmation my ticket?" → clarify order confirmation vs separate QR tickets.
- Wrong/bounced email → correct in Favor Event Tickets, resend.
- Ticket transfer request → apply the **Phase 2.5 auto-approval policy**. Auto-approve (proceed / ask for transferee details) for unforeseen circumstances or another-church-with-multiple-tickets; execute if info is complete and a prior thread approved it; otherwise summarize and ask Rico via `AskUserQuestion`. The window closed June 26, but never dismiss the sender, and never state the reason when approving.
- Financial assistance → `favor.church/financialaid`. New requests: point to the form; multi-ticket requests need Ps Dawn & Kim approval. **Follow-ups are auto-approved: run `/financial-assistance` to issue the coupon directly (email-approved exception), then send the code in-thread** (see Phase 2.5). Do not defer to Finance.
- Serving / Open Access volunteer → `favor.church/serveatconference`.
- Sponsorship → `sponsorships@favor.church`.
- Kids questions (helper/yaya, check-in, pickup times) → see KB §5.
- **Kids guardian update request → update the attendee record in FET + CC kids@favor.church (see Phase 4).**
- Open Access / BTS / pastors sessions → see KB §6.
- General FAQs (parking, venue, food, merch, baggage, accommodations, livestream, lost wristband, PWD/senior/deaf) → KB §7–9.
- **Favor DNA proof/screenshot → reply AND tag the Fluro contact (see Phase 4).**

> **Deadline note:** the Conference FAQs doc still says transfers close "June 2" — that is stale. The operative deadline is **June 26** (live ticket emails + Rico's replies). Use June 26.

---

## Phase 2.5: Auto-approval policy (act vs. draft-only)

**Do the FET check while triaging, before crafting any response.** Never write "we are checking / we will verify / we'll get back to you" for something you can resolve now. Look it up, take the action, then write the reply as a statement of what was done.

Decide per email whether to **act + send** (perform the FET action and send the reply, not just save a draft) or **draft-only** (save a Gmail draft for Rico to review):

**Auto-approve → act + SEND the reply:**
- **Resend / "didn't get my QR" / QR not showing** → resend the ticket(s), then send the reply.
- **"QR / ticket not found" but a valid registration exists** → resend, then send.
- **Cancelled or incomplete order WITH proof of payment attached** → re-complete the order (`orders status … completed, send_ticket_email:true`), resend if needed, then send.
- **Financial assistance follow-up** (chasing a coupon, "haven't received my code", "did my aid go through") → auto-approved. Run the `/financial-assistance` workflow to **issue the coupon directly** using its email-approved exception: assign the correct-tier coupon from the coupon tab, record the row in the tracker Sheet, then send the code in-thread. Do **not** defer to Finance and do **not** send a "we've asked Finance" holding reply. If the applicant's exact pay amount is unknown, use the tier already issued for the same requester's group / their prior coupons, or ask for the amount.

**Ticket transfers → case-by-case:**
- **Auto-approve** (proceed: reply asking for the transferee's full intake details — one complete set per ticket — or, if details + a prior approval already exist, process the transfer) when EITHER:
  - the reason is an **unforeseen circumstance** (accident, unapproved/last-minute leave, sudden illness, calamity such as flooding affecting them or their church), OR
  - the request is from **someone at another church holding multiple tickets** (they may be traveling in from the province).
- **Never state the reason for approving in the reply. Just approve** (ask for details / proceed). Do not write "because of your situation" or "as an exception."
- **Complete info + prior thread already approved** → execute the transfer now via the `/ticket-transfer` workflow (update the attendee, resend QR).
- **Not auto-approved** (no qualifying reason, single ticket, unclear) → do NOT send. Collect these into one summary and ask Rico via `AskUserQuestion` (one option set per person: Approve / Decline) whether to approve for this run. Only after his answer do you act or finalize drafts.

**Everything else not listed above → keep as a draft only** (policy answers, clarifications, informational replies, anything requiring Rico's judgment).

---

## Phase 3: Draft Replies (Favor voice)

For each email that needs a reply, draft a warm, accurate reply, then save it as a Gmail draft.

**Always apply the `speak-like-favor` skill** to every draft. Key rules:

- Open with `Hey, [Name]!`
- Warm, casual, clear, encouraging — no Christianese, no corporate stiffness.
- **No em dashes** (use commas, colons, parentheses). Don't start sentences with "And". Oxford commas.
- Dates/times in Favor format: `July 2`, `6PM`, `9:30PM` (no `:00`, no space before AM/PM).
- Currency with `₱`. Visible link text lowercase with no `https://`/`www`, e.g. `favor.church/tickettransfer`.
- **Draft as HTML, no markdown.** Use `<strong>`, `<ul><li>`, `<p>` — never `**` or `-` bullet characters. Bold key dates, deadlines, links, and action items.
- **Make links clickable:** wrap every link in `<a href="https://full-url">visible text</a>` (clean visible text, full URL in the href). See the `speak-like-favor` Email Rendering section.
- Keep it concise (3–5 sentences) unless clarification is needed.
- Close with:

  ```
  Much love,
  Favor Conference Team
  ```

  Use the specific event team name (e.g. "Business Breakfast Team") when triaging a different event — derive it from the event, never a generic fallback.

**Tooling:** create drafts with Composio `GMAIL_CREATE_EMAIL_DRAFT` on the conferences Gmail connection. Params: `recipient_email`, `extra_recipients`/`cc` (arrays), `subject` (with "Re: "), `thread_id` (threads correctly), `body`, and `is_html: true` for HTML. (`gws` can also create drafts, but its OAuth often lacks Gmail read scope, so it can't fetch the inbox.) Caveats learned in practice: `GMAIL_LIST_DRAFTS`/search lag on indexing and under-report — confirm a draft exists with `GMAIL_GET_DRAFT` by id, not the list. `GMAIL_UPDATE_DRAFT` often fails on thread-reply drafts ("Message not a draft"); to fix one, `GMAIL_DELETE_DRAFT` then recreate it.

**CC rules:**
- If the email was forwarded from another Favor inbox (e.g. `info@favor.church`), CC that inbox so they know it's handled. CC all Favor addresses already on the thread.
- **Kids guardian update emails: always CC `kids@favor.church`** so the Kids team is in the loop.

**Show each draft inline** for review before/after saving.

---

## Phase 4: Take & Suggest Actions (Favor Event Tickets + Fluro)

### Favor Event Tickets

| Email type | Action |
|------------|--------|
| Needs ticket resent | `attendees { action: "resend", attendee_id }` |
| Check if registered | `attendees { action: "query", event_query, search: "<email>" }` |
| Count for an event | `attendees { action: "count", event_query }` |
| Wrong email / update | `attendees { action: "update", attendee_id, ... }` then resend |
| Ticket transfer (past deadline) | Collect full intake details → `attendees { action: "update", attendee_id, full_name, email, information }` then resend (see below) |
| Order issue | `orders { action: "attendees", order_id }` |
| Re-complete a cancelled/incomplete order (verified payment) | `orders { action: "status", order_id, status: "completed", send_ticket_email: true }`; if it returns `email_triggered: false`, resend the attendee ticket explicitly |
| Unknown event name | `events { action: "search", search: "<name>" }` |

### Ticket transfer request → collect full details, then update the attendee

The self-service transfer form (`favor.church/tickettransfer`) **closed June 26**. Past-deadline transfers are now handled directly by the team. **Before processing any transfer, you must have the complete intake details below.** If the sender hasn't provided them, draft a reply (Phase 3) requesting them, asking for **one complete set per ticket**:

```
Transferring from:
- Full name
- Email
- Ticket type (Adult / Student)

Transferring to:
- First name
- Last name
- Email address
- Mobile number
- Gender
- Date of birth
- Country
- Which Favor location or church they're from
- Their church involvement (member, volunteer, leader, etc.)
- Would they like to be connected to our New People team? (yes or no)
- Any special assistance needed during the conference? (or none)
```

Once you have the details (and any required approval — **group/multi-ticket transfers go to Ps Dawn & leadership first**):

1. Find the "transferring from" attendee in FET: `attendees { action: "query", event_query, search: "<email or name>", include_ticket_fields: true }`.
2. Run the update once with `dry_run: true` to preview, then commit with `dry_run: false`:
   ```
   attendees { action: "update", attendee_id: <from_attendee_id>,
     full_name: "<First Last>", email: "<transferee email>",
     information: { "first-name", "last-name", "gender", "mobile-number", "birthdate",
       "which-country-are-you-from", "whats-your-church-involvement", ... },
     dry_run: false, send_ticket_email: true }
   ```
3. **Student tickets:** the transferee must also be a student — capture and set their school (`what-is-your-school-university`).
4. If the QR didn't auto-send, resend explicitly: `attendees { action: "resend", attendee_id, dry_run: false }`. Confirm completion in the reply.
5. **Caveat:** the update response may show `order_sync: false`. The TEC attendee name/email (which drive the QR ticket) update correctly, but the WooCommerce **order-level meta** (IAC name / billing) may still show the old holder — reconcile via postmeta (see `~/claude/CLAUDE.md`) if a clean order record is needed.

For complex or group transfers, route to the dedicated `/ticket-transfer` skill.

### Kids guardian update → update the attendee record

When someone emails requesting a guardian change for their child's ticket (e.g. "I can't attend, my mother will be bringing my kid"):

1. Query attendees by the sender's email with `include_ticket_fields: true` to find both the adult and kids attendees on the order. The kids attendee record will have fields like `parents-guardians-first-name`, `parents-guardians-last-name`, `parents-guardians-gender`, `parents-guardians-mobile`.
2. Update the kids attendee record with the new guardian's details:
   ```
   attendees { action: "update", attendee_id: <kids_attendee_id>, information: {
     "parents-guardians-first-name": "<new first name>",
     "parents-guardians-last-name": "<new last name>"
   }, dry_run: false }
   ```
3. If the sender didn't provide the new guardian's mobile number, note it in the reply and ask for it.
4. Draft the reply (Phase 3) — **CC `kids@favor.church`** — confirming the update, noting that the guardian will need the **Parent Code (Ticket ID)** from the ticket confirmation email at kids check-in.
5. **Note:** The guardian data lives entirely in Favor Event Tickets. There is no separate Fluro form submission for kids conference registrations — don't spend time searching Fluro for one.

### Favor DNA proof → tag the contact in Fluro

When someone sends proof/screenshot that they completed **Favor DNA**:

1. Draft the acknowledgement reply (Phase 3).
2. Find their Fluro contact by name/email (`item { action: "query", body: { _type: "contact", ... } }`).
3. Tag the contact with the graduate tag **🎓 Favor DNA**, Fluro tag `_id` **`6824574fea78c50036f1b7a4`** (definition `equipping`).
   - Do **not** use the plain "Favor DNA" tag `687641e7d93dae0036d7e48c` (that's the in-progress tag).
   - PATCH the contact via the Fluro `update` tool, adding the tag id to the existing `tags` array (preserve current tags).
4. Confirm the tag was applied before marking the email handled.

### Output format per email:

```
📌 Email #1 — [Subject]   (Scenario: missing ticket)
  Draft saved ✅
  Actions taken / suggested:
  • Resent QR ticket to [email] → attendees { action: "resend", attendee_id: ... }
  • [Favor DNA] Tagged contact with 🎓 Favor DNA in Fluro ✅
  • [Guardian update] Updated kids attendee #XXXXX: guardian → [New Guardian Name] ✅
```

---

## Full Output Summary

```
📬 Triage Complete
  - X unread emails found
  - Y drafts saved
  - Z actions taken (resends, tags, corrections, guardian updates)
  - W action items suggested
```

---

## Edge Cases

- **No unread emails:** "No unread emails at conferences@favor.church right now. 🎉"
- **No reply needed** (notification, bounce, auto-reply, system mail): skip drafting, note it.
- **ID/attachment with no context:** ask what it's in reference to before acting.
- **Multiple emails from same sender:** group and draft one consolidated reply.
- **KB doesn't cover the question:** don't guess. Draft a holding reply and flag it for Rico to confirm the answer.
- **FAQ doc vs live facts conflict:** trust live facts (e.g. transfer deadline June 26, not June 2).
- **Kids guardian update — mobile number missing:** update the name fields anyway, then ask for the mobile in the reply draft.

---

## Compatible Tools

- Gmail MCP — `search_threads`, `get_thread`, `create_draft`, `label_thread`
- Favor Event Tickets — `attendees` (`count`, `query`, `update`, `resend`), `orders` (`attendees`), `events` (`search`, `list`)
- Fluro — `item` (`query`, `get`), `update` (`update` for tagging contacts)

## References

- `references/conference-kb.md` — conference knowledge base (event facts, pricing, FAQs, scenario→answer map, Favor DNA tagging). Read it at the start of every triage run.
