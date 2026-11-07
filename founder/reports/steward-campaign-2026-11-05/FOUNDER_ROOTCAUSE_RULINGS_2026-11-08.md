# Founder root-cause rulings F1–F10, 2026-11-08 (verbatim)

Received by the Steward lead (Opus, herdr w2H) in the #2283 session on 2026-11-08, as JSON copied from the local review page built from `ROOTCAUSE-PLAN.md` §9. Recorded verbatim below before any action was taken on them. The questions as presented (context, the agent's labelled recommendation and the options) follow the verbatim block, so each choice can be read against exactly what it approved.

## Founder choices (verbatim JSON)

```json
{
  "F1": {
    "choice": "target",
    "label": "Target: below-ceiling is debt; a Verifier runs gaia dev calibrate per skill, preflights apply",
    "note": "Normally once a skill gets in the tree, this is now debt. A steward run will be canon if it detects below ceiling, and should calibrate automatically. Other ways to do this is through me, the verifier, or through a full monthly meta audit/closeout. So yes, it is technically a ceiling, but steward is now allowed to do this fully."
  },
  "F2": {
    "choice": "rfc",
    "label": "Refer to RFC #2148; hold promotions and demotions on cap-only evidence until it decides",
    "note": "No, \"Suite\" is a term for 3 star above for distinction since there is a \"unique\" vs \"suite\" fork, so its intended. But being a \"suite\" kind of skill with suitecomponents can be ANY ranking. I would call this semantic confusion. There should be no auto-3star for a \"suite\" candidate. In the schema, \"suite\" can be any star. Refer to META.md."
  },
  "F3": {
    "choice": "propose",
    "label": "Yes: keep proposing; the curator decides each time",
    "note": "As LONG as evidence points correctly and gives the correct trust magnitude, proposals are valid. The reason for demotion should be checked since usually it just means that there is no evidence."
  },
  "F4": {
    "choice": "ack",
    "label": "Approve: one decision record acknowledges these 4 historical events; no skill files touched",
    "note": ""
  },
  "F5": {
    "choice": "closed",
    "label": "Fail closed on unreadable or malformed index; empty registry keeps bootstrap; override still works",
    "note": ""
  },
  "F6": {
    "choice": "exception",
    "label": "Record a scoped exception for benchmark use only",
    "note": ""
  },
  "F7": {
    "choice": "source",
    "label": "Fix the gh-aw source and recompile the lock files",
    "note": ""
  },
  "F8": {
    "choice": "add",
    "label": "Add challenge to MUTATING_DEV_COMMANDS",
    "note": ""
  },
  "F9": {
    "choice": "keep",
    "label": "Keep them; fix their sinks through the lane",
    "note": "leave them as is"
  },
  "F10": {
    "choice": "regen",
    "label": "Regenerate after the generator fix, in one gated PR with rendered before/after",
    "note": ""
  }
}
```

## The questions as presented

Each card's text is reproduced from the review page source. HTML tags are stripped; wording is unchanged.

### F1. Is a stored level below its Trust Grade ceiling debt, or a promotion candidate?
*Trust calibration (120 open findings) — 116 of 120 trust_calibration_drift findings*

The sensor flags any skill whose level differs from the level its grade maps to (sensors.py:1855). META §4.1 calls the grade a ceiling ("stored level capped by the Trust Grade ceiling"), and the site already clamps displayed stars to it, so nothing public is overstated. 116 findings are skills below their ceiling; 4 are above it (already clamped on display).

Agent recommendation: Ceiling. Below-ceiling skills become a promotion-candidate queue on the desk, still listed and counted, not Class B debt. The 4 above-ceiling findings stay as debt. This follows META §4.1 and the challenge-driven governance of Yggdrasil IV.

Options:
- `ceiling`: Ceiling: below-ceiling skills are promotion candidates (desk queue, still reported); the 4 above-ceiling stay debt
- `target`: Target: below-ceiling is debt; a Verifier runs gaia dev calibrate per skill, preflights apply
- `defer`: Defer: leave all 120 open as they are

**Founder choice:** `target` — note: "Normally once a skill gets in the tree, this is now debt. A steward run will be canon if it detects below ceiling, and should calibrate automatically. Other ways to do this is through me, the verifier, or through a full monthly meta audit/closeout. So yes, it is technically a ceiling, but steward is now allowed to do this fully."

### F2. Suite component cap equals the B floor. Is cap-only evidence meant to earn grade B?
*Trust calibration (120 open findings) — 140 suite components (59 at 3★, 81 at 2★); 85 findings sit at TM exactly 50.0*

SUITE_COMPONENT_REPOSITORY_CAP = 50.0 carries the comment "cannot by itself promote every component", but grade B is >= 50.0, so suite-repo evidence alone grants B and a 3★ ceiling. The registry is inconsistent either way: 59 such components are already 3★, 81 are 2★. META freezes weights and thresholds pending RFC #2148.

Agent recommendation: Send it through RFC #2148 rather than changing a threshold here. Until it is decided, no promotions on cap-only evidence and no demotions of the 59.

Options:
- `intended`: Intended: cap-only evidence earns B; the 81 at 2★ become promotion candidates
- `unintended`: Unintended: the cap should sit below the floor; change it through the RFC #2148 gate
- `rfc`: Refer to RFC #2148; hold promotions and demotions on cap-only evidence until it decides

**Founder choice:** `rfc` — note: "No, "Suite" is a term for 3 star above for distinction since there is a "unique" vs "suite" fork, so its intended. But being a "suite" kind of skill with suitecomponents can be ANY ranking. I would call this semantic confusion. There should be no auto-3star for a "suite" candidate. In the schema, "suite" can be any star. Refer to META.md."

### F3. May drift re-propose a promotion over a recorded curator demotion?
*Trust calibration (120 open findings) — 15 findings*

15 promotion targets reverse a recorded governed demotion. Example: k-dense-ai/deepchem was demoted to 1★ on 2026-09-04 ("retitled as prompt wrapper") and is now targeted at 4★. At least 4 other targets would be refused by calibrate's own preflights.

Agent recommendation: No. A governed demotion holds until new evidence dated after it arrives. The finding stays visible, annotated as held by that demotion.

Options:
- `hold`: No: a governed demotion holds until newer evidence; finding stays visible and annotated
- `propose`: Yes: keep proposing; the curator decides each time

**Founder choice:** `propose` — note: "As LONG as evidence points correctly and gives the correct trust magnitude, proposals are valid. The reason for demotion should be checked since usually it just means that there is no evidence."

### F4. Acknowledge the 4 historical post-freeze events by decision record?
*Frozen skills — 4 frozen_skill_drift findings (mattpocock, 3★)*

The current level matches the frozen level. The findings are rank_up/demote events dated after the freeze (2026-09-02 and 09-11) that already corrected history. The sensor proposes gaia dev calibrate, which the frozen-skill preflight refuses, so they can never resolve. No skill files would be touched.

Agent recommendation: Approve a structured acknowledgment record. Pair it with the sensor fix that separates a real level mismatch (still flagged) from acknowledged history.

Options:
- `ack`: Approve: one decision record acknowledges these 4 historical events; no skill files touched
- `investigate`: Investigate each event before any acknowledgment

**Founder choice:** `ack`

### F5. Should authorization fail closed when the named-skill index is unreadable?
*Security and execution boundaries — authz.py:55; canonical mutation authority (R4)*

If named-skills.json cannot be read or parsed, the error is swallowed and every actor is allowed through as "bootstrap", the mode meant for a genuinely empty registry. A corrupted index therefore opens all mutating gaia dev verbs.

Agent recommendation: Fail closed with a clear error. A genuinely empty registry (zero Verifiers) still gets bootstrap, and GAIA_OPERATOR_OVERRIDE keeps working for CI.

Options:
- `closed`: Fail closed on unreadable or malformed index; empty registry keeps bootstrap; override still works
- `open`: Keep current behavior

**Founder choice:** `closed`

### F6. HumanEval runs model output with in-process exec. Isolate it, or record an exception?
*Security and execution boundaries — humaneval/run.py:157 (unsafe_execution)*

The code comment says it is "sandboxed by fixture design", but in-process exec is not a sandbox: model-generated code runs with the harness's full permissions.

Agent recommendation: Require isolation: a subprocess with a timeout, resource limits and no inherited secrets.

Options:
- `isolate`: Require isolation (subprocess, timeout, resource limits, no inherited secrets)
- `exception`: Record a scoped exception for benchmark use only

**Founder choice:** `exception`

### F7. gh-aw compiled workflows lack timeouts. Fix the source, or record an upstream exception?
*Security and execution boundaries — 8 .lock.yml workflow_hygiene findings*

Batch 9 repairs the 31 hand-written workflows. The other 8 are compiler output from gh-aw markdown sources, so editing the lock file directly would be overwritten on the next compile.

Agent recommendation: Fix the markdown source and recompile, so the timeout survives regeneration.

Options:
- `source`: Fix the gh-aw source and recompile the lock files
- `exception`: Record an upstream exception; leave the lock files as generated

**Founder choice:** `source`

### F8. Add challenge to the canonical list of gated dev commands?
*Security and execution boundaries — impl.py:256 MUTATING_DEV_COMMANDS (ungated_mutation)*

gaia dev challenge already calls require_operator at its entry, so it is gated in practice. It is missing from the canonical list that documents and checks gated verbs.

Agent recommendation: Yes. It changes no behavior and makes the canonical list true.

Options:
- `add`: Add challenge to MUTATING_DEV_COMMANDS
- `leave`: Leave the list as it is

**Founder choice:** `add`

### F9. docs/samples design prototypes: keep and fix, or retire?
*Public pages (frontend gate) — 8 files, 42 browser-sink sites*

docs/samples/ holds design prototypes (explorer, flowchart, ranks, nav, mobile and others). They are published under docs/ but are not linked from the site navigation.

Agent recommendation: No recommendation. This is a product call about whether the prototypes still serve a purpose.

Options:
- `keep`: Keep them; fix their sinks through the lane
- `retire`: Retire them in a gated PR

**Founder choice:** `keep` — note: "leave them as is"

### F10. Regenerate the changelog in the 26 published meta reports?
*Public pages (frontend gate) — 26 browser_sink_risk findings; public pages*

scripts/add_post.py writes registry text into each report's changelog without escaping. The generator fix is in progress, but the 26 published reports keep the old output until they are regenerated.

Agent recommendation: Yes, after the generator fix lands. One gated PR with a rendered before/after; benign text stays byte-identical.

Options:
- `regen`: Regenerate after the generator fix, in one gated PR with rendered before/after
- `leave`: Leave published reports as they are

**Founder choice:** `regen`


## Addendum: F2 follow-up (verbatim, 2026-11-08)

The founder replied directly to the engineering partner about F1 and F2 overlapping on the 81 cap-pinned suite components:

> Ratify the RFC now based on my comments. They do not get automatic 3 star--they get the cap 50 WHICH THEN gives them the grade right? so its fine

Lead's operational reading, applied until the founder says otherwise:
1. No trust-engine change: `SUITE_COMPONENT_REPOSITORY_CAP` stays 50.0 and the inclusive B floor stays 50.0, so a cap-only suite component legitimately holds grade B.
2. Cap-only suite components get no automatic 3★: they are excluded from F1's automatic calibration. A 3★ for one of them stays a governed per-skill calibration.
3. The 59 suite components already at 3★ with TM 50.0 are untouched (B allows 3★).
4. "Ratify the RFC" is recorded as the founder's ratification of this cap-and-grade reading under RFC #2148; the lead does not edit the RFC issue itself without a further instruction.
