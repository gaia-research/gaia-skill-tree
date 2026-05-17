# Hero Stats Variations

Three layout options for the hero stats bar. All use DESIGN.md colors:
- Total skills → `#e2e8f0` (primary text)  
- Named count → `#ef4444` (contributor red)  
- Legendary count → `#fbbf24` (Level VI amber)

Data: **133 skills · 32 named · 1 ★ legendary**

---

![Mockup variations](C:\Users\mrttr\.gemini\antigravity\brain\0ce2d80a-fd71-4630-9e9b-c7f140aa2347\hero_stats_variations_1778427695106.png)

---

## Variation A — Pill badges

Three pill-shaped badges in a horizontal row, each with a subtle colored border and dark `--surface` background. Visually prominent but adds a "dashboard" feel.

```html
<div class="hero-stats">
  <span class="hs-pill"><strong>133</strong> skills</span>
  <span class="hs-pill hs-named"><strong>32</strong> named</span>
  <span class="hs-pill hs-legendary"><strong>1</strong> ★ legendary</span>
</div>
```

**Pros:** Eye-catching, each stat feels like a card  
**Cons:** Heaviest visually — could compete with the CTA buttons

---

## Variation B — Large numbers with labels

Three bold numbers separated by thin vertical dividers, with small labels underneath. Clean stat-counter style.

```html
<div class="hero-stats">
  <div class="hs-stat"><div class="hs-num">133</div><div class="hs-label">skills</div></div>
  <div class="hs-divider"></div>
  <div class="hs-stat"><div class="hs-num hs-named">32</div><div class="hs-label">named</div></div>
  <div class="hs-divider"></div>
  <div class="hs-stat"><div class="hs-num hs-legendary">1</div><div class="hs-label">★ legendary</div></div>
</div>
```

**Pros:** Premium feel, very scannable  
**Cons:** Takes vertical space, might need responsive breakpoints

---

## Variation C — Compact inline ← recommended

A single line of text with colored numbers and gray labels. Lightest touch — fits naturally under the hero subtitle without adding visual weight.

```html
<p class="hero-stats">
  <strong>133</strong> skills · <strong class="hs-named">32</strong> named · <strong class="hs-legendary">1</strong> ★ legendary
</p>
```

**Pros:** Minimal, doesn't compete with existing hero elements, easy to make scripted  
**Cons:** Less dramatic than A/B

---

> [!TIP]
> **Recommendation:** Variation **C** (compact inline) fits best with the existing hero layout — it slots cleanly below the subtitle paragraph without adding visual clutter. The "1 ★ legendary" in amber is the hook.

Pick A, B, or C and I'll implement it.
