# SEED-MAPPING.md — R1 seed skills → predicted Arbor stamp cells

**Status: PREDICTIONS ONLY, pending R2.** Every mapping below is a hand-label
*prediction* to be tested by the R2 worksheet procedure. None of it is a
benchmark result (B4/B2/B3). No numbers appear here by design — the language is
N repeats plus confidence intervals once labeling lands.

Source: `gaia-research` branch `dev/r1-hh-benchmark`,
`docs/skill-heaven/r1-seed-set.md` §2–§3 (read verbatim). Stamps are
multiplicative with exactly one declared PRIMARY per skill (T9); the T8
publish-class deny-list is rung-independent.

| # | Seed skill (identity) | Band | Predicted stamps (secondary) | PRIMARY prediction | Tension cells |
|---|------------------------|------|------------------------------|--------------------|---------------|
| 1 | Adversarial-critique/grilling playbook (`mattpocock/grilling`) | Heaven | heaven-native | heaven-native | T2, T9 |
| 2 | Design-systems/visual style guide (`garrytan/design-consultation`) — **clean control (Heaven)** | Heaven | heaven-native | heaven-native | control |
| 3 | Systematic-debugging playbook (`obra/systematic-debugging`) — dual-stamp anchor | Heaven | heaven-native (+ultra-ready) | heaven-native | T9 |
| 4 | House-style/brand-voice reference (`anthropics/brand-guidelines`) | Heaven | heaven-native (standing-dose economics) | heaven-native | T7-lite, T11 |
| 5 | IaC-plan review checklist (**TBD**, review-only shape required) | Heaven | heaven-native; explicitly NOT hell-safe | heaven-native | T1 |
| 6 | Language-onboarding cheatsheet+tutor (`mattpocock/teach`) | Heaven | heaven-native (+ultra-ready?) | heaven-native | T6, T9 |
| 7 | Decision-framework/tradeoff matrix (**TBD**, text-only shape required) | Heaven | heaven-native (+ultra-ready) | heaven-native | T9 |
| 8 | Read-only security-audit checklist (`garrytan/cso`) | Hell | hell-safe@high | hell-safe@high | T1 contrast |
| 9 | Auto-patch w/ RED→GREEN gate (**TBD**, gate must verify in-skill) | Hell | hell-safe@max only if gate verified | hell-safe@max (conditional) | T1, T8, T10-open |
| 10 | Codemod/org-migration playbook (`laravel/upgrade-laravel-v13`) | Hell | hell-safe@xhigh + ultra-ready | hell-safe@xhigh | T1, T8, T11 |
| 11 | Bulk test-gen/coverage sweep (`upsonic/unittest-generator`) — **clean control (Hell)** | Hell | hell-safe@high | hell-safe@high | control |
| 12 | Chaos-injection playbook (**TBD**, env-gate precondition required) | Hell | hell-safe@mid conditional on env gate | hell-safe@mid (conditional) | T4 |
| 13 | Corpus map-reduce summarizer (`huggingface/huggingface-datasets`) | Hell | hell-safe@high + ultra-ready | hell-safe@high | privacy/egress open question |
| 14 | Web-recon/deep-research playbook (`mvanhorn/last30days`) | Hell | hell-safe@tier w/ network qualifier | hell-safe (tiered, network qualifier) | network axis |
| 15 | Image/batch media-generation skill (`remotion-dev/remotion-multimedia`) | Hell | hell-safe@high w/ cost ceiling | hell-safe@high (cost ceiling) | S5 cost containment |
| 16 | Env-repro/get-it-running skill (`firecrawl/firecrawl-build-onboarding`) | Hell | hell-safe@ceiling (tier cap, not blanket) | hell-safe@ceiling | T3 |
| 17 | Checkpoint/canonization protocol (`garrytan/context-save`) | Governor | ultra-ready | ultra-ready | U2/U3 pilot |
| 18 | Guardrail/destructive-action gate (`garrytan/guard`) | Governor | ultra-ready + composition-load-bearing | ultra-ready | S3 probe |
| 19 | Grounding/citation-integrity discipline (`caioribeiroclw-pixel/evidence-attestation`) | Governor | ultra-ready + hell-safe candidate | ultra-ready | T5 |
| 20 | Heavy normative reference WCAG-class (`supabase/supabase-postgres-best-practices`) | Summon-floor | none-auto / summon-floor | none-auto | T7 |

Notes:

- Slots #5, #7, #9, #12 are identity-TBD in the seed set (required shapes given
  there); predictions attach to the shape until identities land.
- Known divergences from filled worksheets (review cycle 3, recorded in
  r1-seed-set.md §7): #03 ultra-ready withheld; #10 ultra-ready withheld;
  #13 derives none-auto/deny-list-adjacent conservatively; #14 tier caps to
  med; #20 none-auto held with all-S-pass presentation question. All pending D9.
- Coverage: every tension cell T1–T11 lands at least once across these 20.
- These are inputs to R2 labeling. Nothing here becomes an `arbor/v0` entry in
  `stamps.jsonl` until benchmark receipts exist and `evidence.ledgerRefs` can be
  non-empty per entry.
