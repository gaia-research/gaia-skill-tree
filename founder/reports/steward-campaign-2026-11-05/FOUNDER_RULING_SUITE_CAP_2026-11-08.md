# Founder ruling: suite-component repository cap (2026-11-08, verbatim)

The founder sent this directly to the Opus engineering partner in the #2283 session on 2026-11-08. It is recorded verbatim below, in the same change that implements it. It answers decision **F2** of the root-cause review ("is cap-only evidence giving Grade B and a 3★ ceiling intended?"), the RFC #2148 gate on Yggdrasil III weights and thresholds.

## Messages, in order

1. Reply to a side-agent note that F1 ("target") and F2 overlapped on about 81 cap-pinned suite components:

   > Ratify the RFC now based on my comments. They do not get automatic 3 star--they get the cap 50 WHICH THEN gives them the grade right? so its fine

2. After the engineering partner explained that a 50.0 cap equals the inclusive Grade B floor, so the cap alone grades B and allows 3★, and that F1 would then promote those components automatically:

   > Interesting. Ok cap it at 49.9. Thats the final RFC. They need one more thing to get them 3star.

3. On coordination:

   > mention to coordinator of course. I'm just messaging you directly cause i can ;)

## The ruling

- `SUITE_COMPONENT_REPOSITORY_CAP` changes from **50.0** to **49.9** TM. That is just below the inclusive Grade B floor (`GRADE_B_FLOOR = 50.0`, unchanged).
- A suite component whose Trust Magnitude comes only from the inherited suite-repository baseline therefore grades **C** (2★ ceiling).
- It needs at least one more scoring evidence row of its own, worth ≥ 0.1 TM, to reach Grade B and become eligible for 3★.
- No other weight, threshold or grade changes.

## Measured consequences (read-only simulation on campaign `1a264cdd5`, 473 named records)

| Effect | Count |
|---|---|
| Named records whose computed TM moves | 158 (17 frozen) |
| Grade changes, all B → C | 140 |
| — at 2★ (the open promotion candidates) | 81 |
| — at 3★, not frozen | 46 |
| — at 3★, frozen | 13 |
| Displayed stars dropping 3★ → 2★ through the existing grade clamp (`clampLevelToGrade`; frozen records are exempt) | 46 |
| `trust_calibration_drift` subjects resolved (the 81 promotion candidates) | 81 |
| New `trust_calibration_drift` subjects (all ceiling-exceeded, stored 3★ above the new 2★ ceiling) | 46 |
| Stored TM stamps that become stale | up to 158 (17 frozen, whose locked stamps are never rewritten) |

## Still open, for the founder or the coordinator

- **The 46 non-frozen 3★ components.** Their *displayed* stars drop to 2★ automatically on the next `gaia dev docs` because of the grade ceiling. Their *stored* level stays 3★, and no demotion is written without a governed calibration (Yggdrasil IV). The founder's message says cap-only components "need one more thing to get them 3star". Whether these already-3★ components should be grandfathered was not addressed.
- **Same-sprint landing steps** (part of this ruling's change, not follow-ups):
  1. Restamp the non-frozen stale stamps through the governed `gaia dev calibrate-trust-magnitude`. The grade changes B → C, so `--recomputation-only` holds them.
  2. Run `gaia dev docs` and commit the Class S artifacts.
  3. Schedule the merge between Steward batches, because it re-keys debt (−81 / +46 drift ids, plus stale stamps).
