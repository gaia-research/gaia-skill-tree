---
id: favorchurch/attendees
name: Attendees
contributor: favorchurch
origin: false
genericSkillRef: event-attendance-metrics
status: named
level: 2★
description: Count attendees for any event by checking Favor Event Tickets first,
  then Fluro as a fallback.
createdAt: '2026-07-14'
updatedAt: '2026-07-14'
title: Attendees
links:
  github: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/attendees/SKILL.md
timeline:
- timestamp: '2026-07-13T16:26:02Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill favorchurch/attendees
- timestamp: '2026-07-13T16:34:22Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/attendees/SKILL.md
    (type: self-attestation)'
evidence:
- source: https://github.com/favorchurch/favor-skills/blob/main/CONFERENCE-2026/attendees/SKILL.md
  evaluator: favorchurch
  date: '2026-07-14'
  type: self-attestation
  trustNumber: 10.0
  notes: Self-attestation of Attendees skill implementation
  grade: C
verification:
  firstEvidenceAt: '2026-07-13T16:34:22Z'
---

# Attendees Skill

Count attendees for any event by checking Favor Event Tickets (WordPress/WooCommerce) first, then Fluro as a fallback.

## Prerequisites

Each requirement below is a **capability bucket** — any one of the listed tools satisfies it. Run this preflight before counting. If a **Required** bucket has no connected tool, explain what it is, why this skill needs it, and how to connect one of the options, then **stop and ask the user to set it up** — never fake or guess a count. For **Optional** buckets, note the gap and proceed with reduced coverage.

| Capability | Type | Satisfied by (any one) | If missing |
|---|---|---|---|
| **Event Tickets Access** | Required | Favor Event Tickets MCP | Authoritative source for ticketed events. If not connected/authenticated, tell the user and ask them to run `mcp oauth login favor-event-tickets`, then wait. Do not proceed to Fluro until this is connected. |
| **Fluro Access** | Optional (fallback) | Fluro for Favor Church MCP | Used only for non-ticketed/internal events (RSVP forms, check-ins). If missing, warn that small-group, prayer, or internal events can't be checked, then report what Event Tickets returns. Prompt `mcp oauth login fluro-mcp` only if a fallback is actually needed. |

See **Error Handling** below for full auth-error recovery once a connection drops mid-run.

## Workflow

### Step 1 — Authenticate Favor Event Tickets first

- If the Favor Event Tickets MCP session is not authenticated, stop and prompt the user to run `mcp oauth login favor-event-tickets`.
- Do not continue to Fluro until Favor Event Tickets has been authenticated.

### Step 2 — Check Favor Event Tickets (WordPress)

Use `mcp_favor-event-tickets_event_attendee_count` with the event name or partial title as `event_query`.

- If the event is found and returns a count → **report it and stop**.
- If an authentication error occurs at this stage, stop and prompt the user to run `mcp oauth login favor-event-tickets`. Re-authorization must be done via the CLI's built-in OAuth flow, not another skill.
- If the result is 0 or the event is not found (and no auth error) → proceed to Step 3.

```
mcp_favor-event-tickets_event_attendee_count
  event_query: "<user's event name>"
```

### Step 3 — Check Fluro (fallback)

Try `mcp_fluro-mcp_attendee_rsvp` first (it checks forms, guestlists, and mailing lists):

```
mcp_fluro-mcp_attendee_rsvp
  search: "<user's event name>"
```

- If `attendee_rsvp` returns a count → **report it and stop**.
- If `attendee_rsvp` returns 0 or no match, and you have a Fluro event ID, fall back to `mcp_fluro-mcp_event_checkins` for physical check-in counts.

### Step 4 — Reporting

Present results clearly:

- State the event name as resolved/matched.
- Show the attendee count with the source (e.g., "via ticket registrations" or "via RSVP form" or "via check-ins").
- If counts came from multiple sources, show each separately and note any differences.
- If nothing is found in either system, say so clearly and suggest the user double-check the event name.

## Notes

- **Prioritize RSVP/registration counts over check-in counts** — check-ins only reflect who physically attended, not total registered.
- If the user asks specifically about check-ins or physical attendance, use `event_checkins` directly.
- For ticket-based events (paid or free tickets via WooCommerce), Favor Event Tickets is the authoritative source.
- For small groups, prayer events, or internal church events, Fluro is more likely to have the data.

## Error Handling

### Authentication Errors

If you encounter an authentication error (e.g., `401 Unauthorized`, `Invalid token`, or `Authentication failed`) from any MCP tool:

- **For Fluro (`fluro-mcp`):** 
  - If the error occurs, prompt the user to run `mcp oauth login fluro-mcp`. 
  - **Do not** attempt to fix this via another skill (like `fluro-auth`); the underlying MCP session must be re-authorized via the CLI's built-in OAuth flow.
- **For Favor Event Tickets:**
  - Prompt the user to run `mcp oauth login favor-event-tickets` to refresh the session.
  - This is the required first step before falling back to Fluro.
- **General:**
  - If an MCP tool returns an auth error, do not silently fail. Report the error to the user and explain that re-authorization is required to continue.
