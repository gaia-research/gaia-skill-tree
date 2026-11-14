# Founder ruling — leonxlnx/cook topology (recorded verbatim)

Context: L4 decision card `L4-REVIEW.md` (options A/B/C/D) presented in-session 2026-11-14.

Reply received in the session, verbatim: `A`

Reading: option A — NEW_GENERIC `reference-guided-visual-iteration` (fusion; prerequisites `code-generation`, `vision-qa`, `evaluate-output`). The reply did not choose the `skill-file-url` variant; the packet default (commit-pinned blob) stands unless the reviewer says otherwise.

## What this ruling does NOT yet do
It is a chat reply, not a trusted authorization envelope. `src/gaia_cli/curation/authorization.py::_verifyTrustedEnvelope` is deliberately disabled ("independent protected human authorization is not configured; L4 remains pending"), so `gaia dev ratify` and a trusted `gaia push --from-file <packet>` fail closed for every actor. Verified 2026-11-14: `gaia push --from-file <packet> --dry-run` refuses with "explicit l4Resolution.status=approved is required". No bypass was attempted.

## Open question for the reviewer
How to proceed given the trusted route is not wired — see HANDOFF.md § Routes.
