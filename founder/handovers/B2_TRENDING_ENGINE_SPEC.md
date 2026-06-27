# B2 Trending Engine — Implementation Spec
**Status:** Planning  
**Sprint:** B2  
**Issues:** #651, #697, #698, #760, #852, #853  
**Author:** Opus planning agent, 2026-06-28  
**Constraint:** No new scoring — TM/grade values are READ from registry, never recomputed here.

---

## Architecture Decision: Delta Source

**Recommendation: Option A — Snapshot-based delta.**

### Why snapshot-based wins

| Option | Pros | Cons |
|--------|------|------|
| A. Snapshot | Simple, self-contained, no git dependency at runtime, works in CI and locally, explicit JSON diff | Cold-start requires a seed run; snapshot file is Class S (tracked) |
| B. Timeline-based | Data already exists in frontmatter | Timeline entries are noisy (many `migrate_trust_magnitude` artifacts from G7 cutover); action labels inconsistent; no guarantee all TM changes produce a timeline event |
| C. Git-log-based | Perfect historical accuracy | Requires git at runtime; slow on 249 files; impossible in Cloudflare Workers; breaks offline/stateless pipelines |

**Decision:** Option A with timeline-event enrichment. The snapshot stores `{skillId: {tm, grade, level, evidenceCount, updatedAt}}` per skill. Delta = current minus prior snapshot. Timeline events (`rank_up`, `demote`, `evidence_added`) are used ONLY as qualitative signals for the "Recently Ascended" and "activity recency" views — never as TM recalculation triggers.

### Snapshot lifecycle

```
1. `gaia dev docs` → calls buildTrendingProjection.py
2. Script reads registry/named-skills.json (current state)
3. Script reads docs/api/v1/trending/snapshot.json (prior state)
4. Script computes deltas, writes 7d.json / 30d.json / ascended.json / contested.json / feed.xml
5. Script writes NEW snapshot.json (overwrites prior)
6. On first run (no prior snapshot): all deltas = 0; snapshot seeded; trending lists show "New" badge
```

The snapshot is **Class S** (tracked in git) because:
- It must survive across merges (each merge to main triggers sync-artifacts → gaia dev docs → new snapshot).
- It's tiny (~15KB for 249 skills).
- Git diff on it is meaningless (always changes) → add to `.gitattributes` as `linguist-generated=true`.

### Window detection (no 24h)

The roadmap mentions 24h / 7d / 30d. However:
- Regen happens on every merge to main (typically 1–5× per day).
- A single snapshot has ONE timestamp. True 24h granularity would require storing multiple historical snapshots.
- **Decision:** Ship 7d and 30d. The "7d" window uses a rolling snapshot archive (last 7 snapshots, max 1 per day). The "30d" window uses the 30th-oldest snapshot.

**Snapshot archive format:**
```
docs/api/v1/trending/
  snapshot.json          ← current (latest)
  history/
    2026-06-28.json      ← one per calendar day, max 30 retained
    2026-06-27.json
    ...
```

On each run:
1. Copy current `snapshot.json` → `history/<today>.json` (if not already written today).
2. Prune history/ entries older than 30 days.
3. For 7d delta: compare current vs `history/<today-7>.json` (or nearest available).
4. For 30d delta: compare current vs `history/<today-30>.json` (or nearest available).

---

## Trending Score Formula

**Constraint:** NEVER recomputes Trust Magnitude. Reads `trustMagnitude` and `overallTrustGrade` as-is.

```python
def trendingScore(skill, currentTM, priorTM, timelineEvents, window):
    """
    Pure ranking function. Higher = more trending.
    All inputs are READ from existing registry data.
    """
    # 1. TM delta (absolute change in Trust Magnitude over window)
    tmDelta = currentTM - priorTM  # can be negative (falling)

    # 2. TM delta percentage (guards against large-TM skills dominating)
    tmDeltaPct = tmDelta / max(priorTM, 1.0)  # avoid div-by-zero

    # 3. Rank change signal (binary: did the star rank change in window?)
    rankChanged = 1.0 if hasRankChangeInWindow(timelineEvents, window) else 0.0

    # 4. Evidence recency signal (count of evidence_added events in window)
    evidenceAdded = countEventsInWindow(timelineEvents, 'evidence_added', window)
    evidenceSignal = min(evidenceAdded, 5)  # cap at 5 to prevent spam

    # 5. Grade jump signal (e.g. C→B or B→A in window)
    gradeJump = gradeJumpScore(skill.priorGrade, skill.currentGrade)

    # Composite score — weighted linear combination
    score = (
        tmDelta * 1.0            # raw TM gain (absolute)
      + tmDeltaPct * 20.0        # percentage gain (rewards small-but-fast movers)
      + rankChanged * 50.0       # rank change is a major event
      + evidenceSignal * 10.0    # new evidence = active curation
      + gradeJump * 30.0         # grade promotion = quality signal
    )

    return round(score, 2)


def gradeJumpScore(prior, current):
    """Returns 0-3 based on grade improvement."""
    ORDER = {'ungraded': 0, 'C': 1, 'B': 2, 'A': 3, 'S': 4}
    return max(0, ORDER.get(current, 0) - ORDER.get(prior, 0))


def hasRankChangeInWindow(timeline, window):
    """Check timeline for rank_up or demote events within the window."""
    cutoff = now() - window
    for event in timeline:
        if event.get('action') in ('rank_up', 'demote', 'calibrate'):
            if event.get('timestamp', '') >= cutoff.isoformat():
                return True
    return False


def countEventsInWindow(timeline, action, window):
    cutoff = now() - window
    return sum(1 for e in timeline
               if e.get('action') == action
               and e.get('timestamp', '') >= cutoff.isoformat())
```

### "New" skills (no prior snapshot entry)

Skills that appear in the current registry but NOT in the prior snapshot get a special `"new": true` flag and a trending score of `currentTM * 0.5` (half their absolute TM, so they appear on the list but don't dominate).

### Negative trending (falling)

Skills with negative trending scores are excluded from trending lists. They could be surfaced in a future "Falling" view but are out of scope for B2.

---

## Implementation Plan

### Day 1–2: Snapshot infrastructure + buildTrendingProjection.py skeleton

| Task | Size | Blocker |
|------|------|---------|
| Create `scripts/buildTrendingProjection.py` with CLI args, snapshot read/write | M | None |
| Implement snapshot history archive (daily rotation, 30-day prune) | S | None |
| Wire into `scripts/build_docs.py` as `build_trending_projection` step | S | None |
| Add `.gitattributes` entry for snapshot files | XS | None |

### Day 3–4: Trending computation + API JSON output

| Task | Size | Blocker |
|------|------|---------|
| Implement `trendingScore()` formula | M | Snapshot infra |
| Build `7d.json` and `30d.json` endpoint writers | M | Formula |
| Build `ascended.json` (rank_up events in window) | S | Snapshot infra |
| Build `contested.json` (genericSkillRef bucket analysis) | M | None |
| Build `feed.xml` RSS writer | S | 7d.json |

### Day 5–6: Frontend page

| Task | Size | Blocker |
|------|------|---------|
| Create `docs/trending/index.html` shell (nav, mounts, structure) | M | None |
| Create `docs/trending/trending.js` (fetch + render) | M | API JSON shape |
| Create `docs/trending/trending.css` (design tokens only) | S | None |
| Update `docs/js/mounts.js` with `'trending'` | XS | None |
| Register in `build_html_cache_busting()` | XS | None |

### Day 7: Stargazer heartbeat workflow

| Task | Size | Blocker |
|------|------|---------|
| Create `.github/workflows/stargazer-heartbeat.yml` | M | None |
| Create `scripts/stargazerHeartbeat.py` (star pull + frontmatter update) | M | None |
| Test idempotency + GITHUB_TOKEN permissions | S | Both above |

### Day 8: Integration testing + edge cases

| Task | Size | Blocker |
|------|------|---------|
| Add pytest tests for buildTrendingProjection.py | M | Script |
| Verify cold-start (no snapshot) | S | Script |
| Verify `gaia dev docs` includes trending step | S | Wire |
| PR review + merge | S | All above |

**Total estimate: 8 working days, ~240k tokens across all agents.**

---

## Script: buildTrendingProjection.py

### CLI Signature

```bash
python scripts/buildTrendingProjection.py --out-dir <path>
```

### Input Sources

| Source | Path | Class | Purpose |
|--------|------|-------|---------|
| Named skills index | `registry/named-skills.json` | P (gitignored) | Current TM, grade, level, evidence array, timeline |
| Prior snapshot | `docs/api/v1/trending/snapshot.json` | S (tracked) | Previous TM/grade/level per skill |
| Snapshot history | `docs/api/v1/trending/history/*.json` | S (tracked) | Historical daily snapshots for 7d/30d windows |

### Output Files

| File | Purpose | Size est. |
|------|---------|-----------|
| `<out>/trending/7d.json` | 7-day trending list | ~8KB |
| `<out>/trending/30d.json` | 30-day trending list | ~10KB |
| `<out>/trending/ascended.json` | Recently ascended skills | ~3KB |
| `<out>/trending/contested.json` | Most contested buckets | ~5KB |
| `<out>/trending/snapshot.json` | Current state (for next run) | ~15KB |
| `<out>/trending/history/<date>.json` | Daily archive | ~15KB |
| `<out>/trending/feed.xml` | RSS 2.0 feed | ~5KB |

### Algorithm (pseudocode)

```python
def run(out_dir):
    # 1. Load current state
    named_skills = load("registry/named-skills.json")
    current = {skill.id: extract_fields(skill) for skill in flatten(named_skills)}

    # 2. Load prior snapshots
    snapshot_dir = out_dir / "trending"
    prior_7d = load_snapshot_for_window(snapshot_dir, days=7)
    prior_30d = load_snapshot_for_window(snapshot_dir, days=30)

    # 3. Compute 7d trending
    scores_7d = []
    for skill_id, cur in current.items():
        prior = prior_7d.get(skill_id)
        if prior is None:
            # New skill
            scores_7d.append({**cur, "new": True, "trendingScore": cur.tm * 0.5, "tmDelta": cur.tm})
        else:
            score = trendingScore(cur, cur.tm, prior.tm, cur.timeline, days=7)
            if score > 0:
                scores_7d.append({**cur, "trendingScore": score, "tmDelta": cur.tm - prior.tm, "priorGrade": prior.grade})

    scores_7d.sort(key=lambda x: -x["trendingScore"])
    write_json(out_dir / "trending/7d.json", {"window": "7d", "skills": scores_7d[:50], "generatedAt": now()})

    # 4. Same for 30d (analogous)

    # 5. Ascended: skills with rank_up/demote in last 7d timeline
    ascended = [s for s in current.values() if has_rank_change_in_window(s.timeline, 7)]
    ascended.sort(key=lambda x: latest_rank_event_timestamp(x.timeline), reverse=True)
    write_json(out_dir / "trending/ascended.json", {"skills": ascended[:30], "generatedAt": now()})

    # 6. Contested: genericSkillRef buckets with >= 2 named implementations + recent activity
    buckets = group_by_generic_ref(current)
    contested = [b for b in buckets if len(b.skills) >= 2 and any_activity_in_window(b, 30)]
    contested.sort(key=lambda b: max_trending_score_in_bucket(b), reverse=True)
    write_json(out_dir / "trending/contested.json", {"buckets": contested[:20], "generatedAt": now()})

    # 7. Write new snapshot
    write_snapshot(out_dir / "trending/snapshot.json", current)
    archive_snapshot(out_dir / "trending/history", current)
    prune_history(out_dir / "trending/history", max_days=30)

    # 8. RSS feed
    write_rss(out_dir / "trending/feed.xml", scores_7d[:20])
```

### Edge Cases

1. **First run (no snapshot.json):** Seed with current state. All deltas = 0. Trending lists show skills sorted by absolute TM with `"firstRun": true` flag.
2. **Skill removed from registry:** Present in prior snapshot but not current. Silently dropped (no negative entries).
3. **Skill renamed/moved:** Tracked by `id` field (stable `contributor/slug`). ID changes are rare and would appear as "new" + "removed" (acceptable).
4. **Redacted skills (1★):** Excluded via `is_redacted()` — same filter as `buildApiProjection.py`.
5. **Snapshot history gap (missed days):** Use nearest available snapshot. E.g., if no snapshot for day-7, use day-8 or day-6 (whichever exists).

---

## Frontend: docs/trending/index.html

### Page Structure

```
hero (title + lede)
├── window toggle: [7d] [30d]
├── trending list (cards, populated by trending.js)
├── recently ascended section
└── most contested section
```

- Load `../js/mounts.js` BEFORE `../js/site-nav.js`
- `trending` must be added to `window.GAIA_MOUNTS` in `docs/js/mounts.js`
- Design tokens only — zero hex color values
- Include `<link rel="alternate" type="application/rss+xml" href="feed.xml">`
- Cache-bust: register in `build_html_cache_busting()` in `scripts/build_docs.py` (~line 316)

### Token usage examples

```css
.trending-card { border-color: var(--rank-3-border); }
.trending-delta-up { color: var(--rank-5); }
.trending-delta-new { color: var(--rank-2); }
.trending-grade { color: var(--grade-A); }
```

---

## Infra: Stargazer Heartbeat (#760)

### Purpose

Monthly GitHub Action that:
1. Reads all named skills with `links.github` containing a valid repo URL.
2. Queries GitHub API for current star counts.
3. If any star count has changed significantly (>5% or >100 stars delta), updates frontmatter evidence rows.
4. Commits changes and triggers a `gaia dev docs` regen which produces updated TM values + trending snapshot.

### Workflow YAML Sketch

```yaml
name: Stargazer Heartbeat

on:
  schedule:
    - cron: '0 6 1 * *'  # 06:00 UTC on 1st of each month
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  heartbeat:
    runs-on: ubuntu-latest
    if: github.ref_name == 'main'
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -e ".[dev]"
      - name: Configure git
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
      - name: Run stargazer pull
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GAIA_OPERATOR_OVERRIDE: "1"
        run: python scripts/stargazerHeartbeat.py --apply
      - name: Check for changes
        id: changes
        run: |
          if [[ -n "$(git status --porcelain registry/named/)" ]]; then
            echo "changed=true" >> $GITHUB_OUTPUT
          else
            echo "changed=false" >> $GITHUB_OUTPUT
          fi
      - name: Commit + regen
        if: steps.changes.outputs.changed == 'true'
        run: |
          git add registry/named/
          git commit -m "chore(heartbeat): monthly stargazer refresh [skip-gen]"
          gaia dev docs
          git add docs/
          git commit --amend --no-edit
          git push
```

### Idempotency Strategy

- Reads each skill's existing `evidence[type=github-stars-own].stars` value.
- Only writes if new value differs by >5% OR >100 absolute stars.
- Uses `trustMagnitudeInputHash` to avoid redundant TM recomputes (existing mechanism).
- `[skip-gen]` in commit message prevents `sync-artifacts.yml` from double-triggering.
- If run multiple times in the same day, subsequent runs are no-ops.

### Supporting script: scripts/stargazerHeartbeat.py

```
Input:  registry/named/<contributor>/<skill>.md (frontmatter)
Output: updates stars field in evidence rows in-place

Algorithm:
  for each skill with links.github:
    extract owner/repo from URL
    query GET /repos/{owner}/{repo} → stargazers_count
    if abs(new - old) / max(old, 1) > 0.05 or abs(new - old) > 100:
      update evidence[type=github-stars-own].stars = new
      update evidence[type=github-stars-own].updatedAt = today

Does NOT recompute TM — gaia dev docs does that downstream.
```

---

## API Endpoints

### `GET /api/v1/trending/7d.json`

```json
{
  "window": "7d",
  "generatedAt": "2026-06-28T12:00:00Z",
  "firstRun": false,
  "skills": [
    {
      "id": "browser-use/browser-harness",
      "name": "Browser Harness",
      "level": "3★",
      "contributor": "browser-use",
      "trustMagnitude": 73.59,
      "overallTrustGrade": "B",
      "trendingScore": 85.4,
      "tmDelta": 37.59,
      "priorGrade": "C",
      "new": false,
      "_links": { "self": "/api/v1/skills/browser-use/browser-harness.json" }
    }
  ],
  "totalTrending": 42,
  "_links": {
    "self": "/api/v1/trending/7d.json",
    "alternate": "/api/v1/trending/30d.json"
  }
}
```

### `GET /api/v1/trending/30d.json`

Same shape as 7d with `"window": "30d"`.

### `GET /api/v1/trending/ascended.json`

```json
{
  "generatedAt": "2026-06-28T12:00:00Z",
  "skills": [
    {
      "id": "browser-use/browser-harness",
      "name": "Browser Harness",
      "previousLevel": "2★",
      "currentLevel": "3★",
      "ascendedAt": "2026-06-20T06:31:20Z",
      "trustMagnitude": 73.59,
      "overallTrustGrade": "B",
      "_links": { "self": "/api/v1/skills/browser-use/browser-harness.json" }
    }
  ],
  "_links": { "self": "/api/v1/trending/ascended.json" }
}
```

### `GET /api/v1/trending/contested.json`

```json
{
  "generatedAt": "2026-06-28T12:00:00Z",
  "buckets": [
    {
      "genericSkillRef": "browser-control",
      "implementations": 3,
      "skills": [
        { "id": "browser-use/browser-harness", "trustMagnitude": 73.59, "level": "3★" },
        { "id": "garrytan/browse", "trustMagnitude": 145.0, "level": "4★" },
        { "id": "browserbase/stagehand", "trustMagnitude": 0.0, "level": "2★" }
      ],
      "topTM": 145.0,
      "recentActivity": true
    }
  ],
  "_links": { "self": "/api/v1/trending/contested.json" }
}
```

### `GET /trending/feed.xml`

RSS 2.0. Top 20 trending skills (7d window). Each item links to `/named/#explorer/<skill-id>`.

---

## pi-zerg-swarm Parallelization Plan

### Assessment: YES — 4 parallel work streams

B2 decomposes cleanly into independent subtasks:

| Agent | Task | Dependencies | Est. tokens |
|-------|------|--------------|-------------|
| Worker A | `scripts/buildTrendingProjection.py` (full script) | None — reads patterns from buildApiProjection.py | ~40k |
| Worker B | `docs/trending/` (HTML + CSS + JS) | Needs API shape (embed in prompt) | ~25k |
| Worker C | `.github/workflows/stargazer-heartbeat.yml` + `scripts/stargazerHeartbeat.py` | None | ~20k |
| Worker D | Integration wiring (`build_docs.py`, `mounts.js`, `.gitattributes`, tests) | Worker A output paths (provide in prompt) | ~20k |

### Sync points

- **T+0:** Workers A, B, C dispatch simultaneously.
- **T+1:** Worker D dispatches after Worker A confirms output file paths.
- **T+2:** Orchestrator runs `gaia dev docs --check` to validate cohesion.
- **Final:** Single merge PR with all four workers' commits rebased in sequence.

### pi-zerg-swarm usage

Use `zerg_control` to launch Workers A, B, C as parallel agents with `tasks` array. Wait for all three to complete, then launch Worker D as a `chain` step using `{previous}` from Worker A for the output paths. This cuts the B2 calendar time from 8 sequential days to approximately 3 (parallel day 1 + wiring day 2 + integration day 3).

---

## Dispatch Sequence (for the orchestrator)

### Wave 1 (parallel — all at T+0 via zerg_control tasks[])

**Worker A prompt outline:** Create `scripts/buildTrendingProjection.py`. Model after `scripts/buildApiProjection.py`. Reads `registry/named-skills.json`, computes trending scores using [embed formula from this spec], writes to `docs/api/v1/trending/`. Snapshot archive, 7d/30d windows, ascended, contested, feed.xml, cold-start handling. Use `is_redacted()` filter. CLI: `--out-dir <path>`.

**Worker B prompt outline:** Create `docs/trending/index.html`, `trending.css`, `trending.js`. Fetch from `../api/v1/trending/{7d,30d,ascended,contested}.json`. Use design tokens only. Follow `docs/trust/leaderboard/index.html` for page patterns. Include RSS alternate link. Sections: hero, window toggle, trending list, ascended, contested.

**Worker C prompt outline:** Create `.github/workflows/stargazer-heartbeat.yml` (monthly cron, `GAIA_OPERATOR_OVERRIDE=1`) and `scripts/stargazerHeartbeat.py`. Query GitHub API for star counts of all skills with `links.github`. Update `evidence[type=github-stars-own].stars` in frontmatter if delta >5% or >100. Idempotent.

### Wave 2 (after Worker A returns)

**Worker D prompt outline:** Wire `buildTrendingProjection.py` into `scripts/build_docs.py` as `build_trending_projection` step (same tempdir-diff pattern as `build_api_projection`). Add `'trending'` to `docs/js/mounts.js`. Add `"trending/index.html"` to `build_html_cache_busting()`. Add trending snapshot paths to `.gitattributes` as `linguist-generated=true`. Write `tests/test_trending.py`.

---

## Token Budget Estimate

| Dispatch | Model | Est. Input | Est. Output | Est. Cost |
|----------|-------|------------|-------------|-----------|
| Orchestrator planning (this doc) | Opus | ~80k | ~15k | ~$8 |
| Worker A — Python script | Sonnet | ~40k | ~12k | ~$3 |
| Worker B — Frontend | Sonnet | ~30k | ~10k | ~$2 |
| Worker C — Stargazer infra | Sonnet | ~25k | ~8k | ~$2 |
| Worker D — Wiring + tests | Sonnet | ~35k | ~10k | ~$3 |
| Integration review | Opus | ~30k | ~5k | ~$3 |
| **Total B2** | | **~240k** | **~60k** | **~$21** |

Within the Sprint B budget of ~250k tokens / ~$25.

---

## Files Changed/Created Summary

### New Files
- `scripts/buildTrendingProjection.py`
- `scripts/stargazerHeartbeat.py`
- `docs/trending/index.html`
- `docs/trending/trending.css`
- `docs/trending/trending.js`
- `docs/trending/feed.xml` (generated — Class S)
- `docs/api/v1/trending/7d.json` (generated — Class S)
- `docs/api/v1/trending/30d.json` (generated — Class S)
- `docs/api/v1/trending/ascended.json` (generated — Class S)
- `docs/api/v1/trending/contested.json` (generated — Class S)
- `docs/api/v1/trending/snapshot.json` (generated — Class S, linguist-generated)
- `docs/api/v1/trending/history/` (generated — Class S, linguist-generated)
- `.github/workflows/stargazer-heartbeat.yml`
- `tests/test_trending.py`

### Modified Files
- `scripts/build_docs.py` — add `build_trending_projection` step
- `docs/js/mounts.js` — add `'trending'`
- `.gitattributes` — trending snapshots as `linguist-generated=true`

### Classification
- `docs/api/v1/trending/*.json` — **Class S** (tracked, served by GitHub Pages)
- `docs/trending/feed.xml` — **Class S** (tracked, served)
- Snapshot history — **Class S** (tracked, generated, linguist-generated=true)
