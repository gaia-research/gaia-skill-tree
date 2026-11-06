## M1 — first protected-main delivery verified

PR #2297 merged normally at **2026-11-05T20:05:51Z**, main merge **3cd5504e00ac00e4708503f484a05e04e5775dcc**. Tree **9b29681b44be112306f8502961f4e67787492d97** exactly matches the independently accepted frozen candidate; parents preserve both prior main31b407db… and candidate2d9599c11…. Exact-head applicable PR CI passed before merge. Post-merge CI will be collected in the next batch.

Founder choices were recorded verbatim and pushed in **324e0ab97** before acting. The only ruleset configuration change was Main Ruleset18124772 `conditions.ref_name.include: [] -> ["refs/heads/main"]`. Existing checks/rules/strictness and zero bypass actors were preserved; main protected:true and three effective rules were verified. The shown ledger warning was approved. Normal merge, no admin override or required-check bypass. Existing `[skip-gen]` source-only guard avoids unapproved artifact regeneration/release/deploy.

**Correction:** the PR's pre-existing GitHub closing relationship automatically closed this tracker at20:05:54Z. It is reopened because M1 is not whole-campaign completion; no debt adjudication or routine18 issue-closure action is claimed.

Seven principal engineering packages are now on main, **not seven debt closures**. Canonical B repair closures remain **one**. Roster patch97cc7863… is committed and its build recorded (165package tests passed), but no independent acceptance or closure is claimed: the resumed run stopped on unknown pr-maintenance coverage. Refresh/diagnose current census through the authorized path before any further dispatch; do not override coverage or reset attempts.

Current Routine19 owner remains untouched; archive remains parked. New LLM work uses native subagent with28-minute batched cost/cache guards. Going forward non-Steward engineering uses Terra through **openai**, not openai-codex; canonical Steward retains its shared Codex roster. No current worker is restarted merely to change routing.
