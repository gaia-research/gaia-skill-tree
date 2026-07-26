---
target: docs/index.html mobile hero
total_score: 29
p0_count: 0
p1_count: 2
timestamp: 2026-07-12T19-15-00Z
slug: docs-index-html-mobile-hero
---
# Mobile Hero Critique — docs/index.html

## Score: 29/40 (Good). Weak axis: Aesthetic/Minimalist = 2/4 (visual noise).

## Priority Issues
- [P1] Visual noise floor: full-bleed tree at scale(1.5) has no luminance hierarchy; midfield tangle + starfield + gold glow + copy all at same tonal band. Fix: depth-of-field vignette/blur over tree, drop starfield opacity, push bright root-burst above headline not behind. (adapt/layout)
- [P1] Three button languages in one fold: top pills (Explore/Trust Ledger), floating Curation chip, three stacked action rows. Fix: remove Trust Ledger pill; convert floating chip to latest-report notification.
- [P2] Glyph-only semantics: ◆ ◇ ↑ repeat with different meanings. (clarify)
- [P2] Muted .hero-sub contrast over fading tree base; verify 4.5:1. (audit)

## Detector (whole file): 4 warnings, none in hero. broken-image x2 (lazy src="" false positives), flat-type-hierarchy (page ramp), em-dash-overuse (26 in body elsewhere). Hero markup clean.

## Working: tree-as-identity full-bleed; headline typography; install-CLI card w/ platform toggle.
