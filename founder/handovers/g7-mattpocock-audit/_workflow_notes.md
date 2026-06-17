# wf_afe9b5c8-053 — Author notes

## issueCommentDeltaNotes

Comment body generated from the five amendments, the amended 6-predicate gate, and the 3/6 verdict for mattpocock/skills. Cross-links use the relative tree path format from the prior issue comment. Kept under 4kb prose (excluding the tables). Q1-Q5 section recaps implications without re-explaining the prior analysis. I7 pointer added as instructed.

---

## handoverDeltaNotes

The delta is authored from the full text of G7_IMPLEMENTATION_HANDOVER.md. Key decisions made: (1) Section C cleanly separates sourceStartedAt (amendment-driven) from role=variant enforcement (audit-graft) and notes the graft provenance. (2) Section D Decision (D) text is written to be dropped verbatim into §1 after Decision C. (3) Section F replaces the visual flow block entirely (the cleanest integration point). (4) Section G replaces the §8 table entirely. (5) I7 cost is $1.20 as specified; the token counts (45k in / 6k out) are reverse-engineered to land at that price at Sonnet 4.6 rates. (6) The dispatch checklist amendment notes in Section G are advisory — the orchestrator who integrates this delta should apply them to §9 of the handover directly.

---

## codexPageNotes

Key design choices:

1. Layout pattern: follows docs/codex.html exactly — body.process-page, #site-nav, main, #site-footer-mount, #scrollToTop, same JS bundle (atlas-helpers, ui, page-ia). The back link goes to ../codex.html with the history.back() pattern.

2. CSS reuse: uses all existing tokens — --surface, --border, --text, --muted, --tier-basic/extra/unique/ultimate, --tier-*-bg/border, --honor-red, --apex-gold, --font-display/body/mono. The new classes (.tm-formula-block, .tm-table, .grade-pill, .tm-predicate-list, .tm-closure-list, .tm-callout, .tm-example-header, .tm-back-row) are minimal additions on top of the existing design system. .process-section, .process-hero, .process-kicker, .process-lede, .process-actions, .section-sub, .codex-toc, .review-grid, .review-card, .btn, .btn-ghost are all consumed from styles.css as-is.

3. Vocabulary compliance: uses "Trust Magnitude" not "trust score", "Overall Trust Grade" not "trust rating", "Evidence Type" / "Evidence Grade" not "class", "Origin Contributor", "Named Skill", "fusion" / "fuse", "Suite Components", "role='origin'" / "role='variant'". No rarity references. No banned synonyms. Apex is used only for 6★ Transcendent ★. Uses "rank up" / "promote" verbs correctly.

4. The grade pills use four distinct visual treatments: S = white shimmer, A = tier-ultimate amber, B = tier-extra purple, C = tier-basic sky, ungraded = muted grey. These derive from tier tokens, not hardcoded hex.

5. The Apex Gate predicate list uses .pred-pass / .pred-fail with left-border color semantics to distinguish passing vs failing predicates in the worked example section.

6. The worked example shows mattpocock/skills at TM 1187, grade S, Apex Gate 3/6 — with aGradedOriginsGte5 (4/5 fail), depth2OnlyReachableGte1 (0 fail), and apexPromotionPrSigned (intentional, no PR submitted) all marked failing, and the other three passing.

7. The Suite vs Fusion section uses the existing .review-grid + .review-card pattern for the side-by-side comparison, then a .tm-callout for the variant-padding attack closure note.

8. Page length is ~700 lines, within the 600-1000 target budget.

9. The ../css/styles.css rel path assumes the file lives at docs/codex/trust-methodology.html.

10. Cross-links footer section links to /codex/, /evidence/, /named/, /badges/, GitHub repo, and RFC G7 issue #715 as specified.

---

