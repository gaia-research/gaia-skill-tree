# Handover — Fix role-stripping regression in `buildMergedSkillMap()` (#1643)

Status: PLAN — NOT IMPLEMENTED (captured per founder instruction: "keep in handover, dont implement yet")
Date: 2026-08-25
Tracking issue: gaia-research/gaia-skill-tree#1643 (sub-issue of Wayfinder map #1636)
Diagnosis source: #1638 (`ruvnet/ruflo-v3` TM overcount investigation)

---

## 1. Problem

`src/gaia_cli/registryMaps.py::buildMergedSkillMap()` (added by commit `4ba12db`
/ #1600, 2026-08-20) strips the `role` key from every named-skill entry before
returning the merged map:

```python
# src/gaia_cli/registryMaps.py, line 74
fm = {k: v for k, v in fm.items() if k != "role"}
```

This copies a stripping pattern from commit `59a87e45d` (2026-08-18), which
removed `role` to fix a *display-only* bug (a UI "champion vs variant" role
was incorrectly zeroing non-champion suite components' fusion contribution).
That commit's own message flagged the RFC-field collision as "a follow-up,
out of scope" — the follow-up never landed.

`role` is overloaded:
- **UI role** — champion/variant display distinction within a bucket. Should
  stay stripped from the shared map; not an RFC-graded input.
- **RFC §C-2 `role: variant` field** — a genuine frontmatter marker that
  excludes a suite component from the graded-origin count in fusion-recipe
  TM scoring. Stripping it silently makes every `role: variant` component
  count as a full graded origin.

`buildMergedSkillMap()` is the shared resolver consumed by `trustMagnitude.py`,
`trust_appraise.py`, and `gaia dev calibrate-trust-magnitude` — so the bug is
live in the canonical TM pipeline. `scripts/inspectTrustMagnitude.py` never
adopted this shared resolver (it has its own forked `buildGenericSkillMap`/
`buildNamedSkillMap`) and still respects `role` correctly, which is how the
divergence was caught: it alone produces the RFC-correct number for
`ruvnet/ruflo-v3`.

## 2. Confirmed impact

- `ruvnet/ruflo-v3`: stamped `trustMagnitude: 216.00` (written 2026-08-20 by
  `gaia dev calibrate-trust-magnitude`, commit `4ba12db`, #1600) vs RFC-correct
  `186.00` — a +30.00 overcount. Its `v3-ddd-architecture` component
  (`role: variant`) is wrongly counted as a 6th graded origin instead of
  excluded.
- **8 named skills registry-wide** carry a genuine `role: variant` marker.
  Only `ruflo-v3` is confirmed currently wrong; the other 7 need auditing
  once the fix lands (they may not currently trip the bug if their suite has
  no graded variant-adjacent component, but the resolver bug affects all 8
  equally at the code level).

## 3. Fix plan (in order — NOT executed)

1. **Separate UI role from RFC role** in `registryMaps.py::buildMergedSkillMap()`
   and in `trustMagnitude.py`'s consumers. The merged map should stop
   unconditionally deleting `role`; instead, keep the RFC-relevant value and
   only strip/ignore it at display-rendering call sites that need the
   champion/variant UI distinction suppressed. Concretely: stop the blanket
   `fm = {k: v for k, v in fm.items() if k != "role"}` at registryMaps.py:74;
   let `role` pass through the merged map, and audit every consumer of
   `buildMergedSkillMap()` for whether it needs the UI role hidden (rendering
   paths) vs the RFC role visible (TM/grading paths) — these may need to
   diverge into two accessors rather than one map with one meaning of `role`.
2. **Migrate `scripts/inspectTrustMagnitude.py`** onto the fixed shared
   `buildMergedSkillMap()` resolver, retiring its forked
   `buildGenericSkillMap`/`buildNamedSkillMap`. Do this only after step 1 —
   right now the script is correct only by accident of never having adopted
   the buggy shared path; migrating it before the fix would import the bug
   into the one place that's currently right.
3. **Audit all 8 `role: variant` skills** for TM impact once the fix ships.
   Do NOT recalibrate `ruflo-v3` (or any of the 8) before this fix lands —
   `gaia dev calibrate-trust-magnitude` would just re-stamp the buggy 216.00.
   Recalibrating `ruflo-v3`'s frontmatter is an explicit mechanical follow-up
   ticket *after* this one, not part of it.
4. **Regression test**: a suite with a `role: variant` component must exclude
   it from the graded-origin count in TM scoring; a suite with only a
   display/UI role difference (non-champion, no RFC `variant` marker) must
   NOT lose fusion contribution. Add this to whatever test module covers
   `trustMagnitude.py` / `registryMaps.py` today (needs locating — not yet
   identified in this pass).

## 4. Open question for founder — routing

Per the map issue's own "Not yet specified" note: this is a genuine code fix
touching `src/gaia_cli/registryMaps.py`, `trustMagnitude.py`, and
`scripts/inspectTrustMagnitude.py`, with an 8-skill blast radius on canonical
TM scores. Unlike #1637/#1641 (pure mechanical re-stamps), this needs a design
call on the UI-role/RFC-role split before any line is touched — the "two
accessors instead of one overloaded map" question in step 1 is a real API
shape decision, not a mechanical fix.

Two routing options once founder gives the go-ahead:
- **(a)** Dispatch a coding subagent directly with this handover as the spec
  (fast, but the API-shape call gets made implicitly by whoever implements).
- **(b)** Run a planning pass first (e.g. `/fp-plan`-style or a `Plan` agent)
  to nail down the exact two-accessor (or other) shape before implementation,
  given the blast radius touches the canonical TM pipeline directly.

No implementation work has been started on this ticket. This handover exists
so the plan isn't lost, not as a go-ahead to build.
