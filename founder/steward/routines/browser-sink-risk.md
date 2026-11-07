# Routine — Browser Sink Risk (Report-Only / Founder Desk)

| | |
|---|---|
| **Policy classification** | Report-Only / Founder Desk |
| **Sensor** | `browser-sink` / Routine 16 |
| **Debt kind** | `browser_sink_risk` |
| **Authority** | Ineligible for autonomous write dispatch (Class C escalation) |
| **Cadence** | Worth looking on a normal scan |
| **Routine catalog** | #16 — Browser, Privacy, and External Trust Auditor |
| **Decision** | `steward-browser-sink-route` (founder ruling 2026-11-08, #2283) |

---

## What it is for

Sensor #16 audits browser DOM sinks for reverse-tabnabbing (`target="_blank"` without `rel="noopener noreferrer"`) and XSS risks in frontend surfaces (`docs/**`) and publishing scripts (`scripts/add_post.py`).

## Governance & Human-Gating Policy (CLAUDE.md)

Under repository policy in `CLAUDE.md` § Frontend changes are HUMAN-GATED:
- All frontend changes require founder/human review.
- The Founder Directive (2026-11-08) explicitly mandates:
  > *"FRONTEND IS HUMAN-GATED: the route may only do changes with NO rendered diff (e.g. innerHTML of plain text -> textContent where the value is never markup), must carry a no-rendered-diff proof, and must route anything else to the founder desk instead of dispatching. If no-rendered-diff cannot be made mechanically provable, design it as report-only and say so."*

## Technical Disposition: Report-Only

Root-cause investigation and census analysis revealed:
1. Over 150 sink sites across `docs/` are dynamic HTML templates (e.g. `innerHTML` assignments interpolating template literals and markup).
2. 26 meta-report pages interpolate unescaped JSON changelog strings via `scripts/add_post.py:638`.
3. Transforming dynamic markup templates cannot be mechanically proven in Python to have zero rendered visual diff without an interactive browser render pass and human design review.

In accordance with the Founder Directive's explicit condition, `browser_sink_risk` is formally designated as **Report-Only**:
- Autonomous write dispatch is declined.
- Findings are surfaced as advisory reports on the Founder Desk.
- Human contributors resolve findings with interactive design verification per `CLAUDE.md`.
