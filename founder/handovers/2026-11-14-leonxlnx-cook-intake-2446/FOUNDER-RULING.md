# Founder ruling — leonxlnx/cook topology (recorded verbatim)

Context: L4 decision card `L4-REVIEW.md` (options A/B/C/D) presented in-session 2026-11-14.

Reply received in the session, verbatim: `A`

Reading: option A — NEW_GENERIC `reference-guided-visual-iteration` (fusion; prerequisites `code-generation`, `vision-qa`, `evaluate-output`). The reply did not choose the `skill-file-url` variant; the packet default (commit-pinned blob) stands unless the reviewer says otherwise.

## What this ruling does NOT yet do
It is a chat reply, not a trusted authorization envelope. `src/gaia_cli/curation/authorization.py::_verifyTrustedEnvelope` is deliberately disabled ("independent protected human authorization is not configured; L4 remains pending"), so `gaia dev ratify` and a trusted `gaia push --from-file <packet>` fail closed for every actor. Verified 2026-11-14: `gaia push --from-file <packet> --dry-run` refuses with "explicit l4Resolution.status=approved is required". No bypass was attempted.

## Open question for the reviewer
How to proceed given the trusted route is not wired — see HANDOFF.md § Routes.

---
## Ruling 2 — reaffirmation and route (2026-11-14, verbatim)
`I approved L4. Its A`

## Ruling 3 — route decision (2026-11-14, verbatim)
`2. Have Opus wire it. Merge after a code-review, thats my founder gate for today. Then fontinue with gaia full pipeline on cook.`

Reading: route 2 (wire the protected authorization workflow). Opus is explicitly authorized for this task only (overrides the roster's "no Opus"). Founder gate for the verifier PR = independent code review passes, then lead merges. After merge, resume cook at HANDOFF Resume step 3. Reviewer must still perform the ceremony (trigger workflow + approve in the protected environment) — a chat approval is not the envelope. Admin setup of the `l4-human-review` environment is out of band.
