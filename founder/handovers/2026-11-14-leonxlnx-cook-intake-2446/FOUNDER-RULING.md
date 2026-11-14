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

---
## Ruling 4 — L4 philosophy (2026-11-14, verbatim)
`read as well CONTRIBUTING.md. The idea is anyone can truly L4 approve a curation step. Then everything in the pipeline is required, including evidence seed, etc to increase its score. The gate in the repo is awakening the skill at 2 star up, not a strict L4 environment`

Effect: the envelope/ratify ceremony is NOT the L4 route (the Opus verifier build was stopped; no PR). L4 = a recorded human topology decision; the substantive gate is the evidence pipeline that earns 2★+. CONTRIBUTING.md:71 ("L4 is independent human authority … verified authorization") and CURATION-CORE steps 4–5 contradict this and are stale.

---
## Rulings 5–6 — methodology and calibration (2026-11-14, verbatim)
`how does 410 stars get 56? check the /trust-methodology-consult . Youtube is fine, this is trust signal. Get the most honest result, tm grade is rarely the deciding factor. Going through the pipeline correctly is . Tm is the result`

`merge the playbook as is, then continue the ingest til the end`

Reading: (1) the TM result stands as computed (126.75, Grade A); YouTube rows are valid trust signal. (2) PR #2456 merged as is (merge commit 69697dc). (3) "continue the ingest til the end" follows the lead's explicit proposal "apply 4★ … say 4★ and I'll proceed", so the lead reads it as approval of the recommended calibration (the G7 mapping of Grade A = 4★), subject to the CLI's own Star Bar / Origin pre-flight. If the founder meant otherwise, the level can be changed through `gaia dev calibrate` before merge.
