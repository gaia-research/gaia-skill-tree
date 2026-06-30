#!/usr/bin/env python3
"""Generate docs/api/v1/trending/ — snapshot-based trending engine.

Usage:
    python scripts/buildTrendingProjection.py --out-dir <path>

Input sources:
    docs/api/v1/skills/index.json               — current skills with TM values
    docs/api/v1/skills/<contributor>/<skill>.json — individual skill details
    <out-dir>/trending/snapshot.json            — prior run state (may not exist)
    <out-dir>/trending/history/<YYYY-MM-DD>.json — daily archive

Output files (all under <out-dir>/trending/):
    snapshot.json      — current state dict {skill_id: {tm, grade, level, updatedAt}}
    history/<date>.json — copy of today's snapshot
    7d.json            — 7-day trending list
    30d.json           — 30-day trending list
    ascended.json      — skills with rank_up/calibrate events in last 30 days
    contested.json     — genericSkillRef buckets with >=2 named implementations

Constraint: No new scoring. TM values are read from existing API projection as-is.
"""

from __future__ import annotations

import argparse
import email.utils
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gaia_cli.redaction import is_redacted  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_version() -> str:
    """Extract version string from pyproject.toml via regex (no tomllib dep)."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _slug_from_id(skill_id: str) -> tuple[str, str]:
    """Split 'contributor/skill-name' into (contributor, skill_slug)."""
    parts = skill_id.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return skill_id, skill_id


def _utcnow() -> datetime:
    """Return current UTC time as a naive datetime (for consistent arithmetic)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso_now() -> str:
    return _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_str() -> str:
    return _utcnow().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Snapshot I/O
# ---------------------------------------------------------------------------


def _load_snapshot(snapshot_path: Path) -> dict:
    """Load prior snapshot. Returns empty dict on missing/corrupt file."""
    if not snapshot_path.exists():
        return {}
    try:
        return json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_snapshot(snapshot_path: Path, state: dict, generated_at: str) -> None:
    """Write current state as snapshot.json."""
    _write_json(snapshot_path, {
        "generatedAt": generated_at,
        "skills": state,
    })


def _archive_history(history_dir: Path, state: dict, generated_at: str) -> None:
    """Write today's snapshot to history/ and prune to 30 days."""
    today = _today_str()
    _write_json(history_dir / f"{today}.json", {
        "date": today,
        "generatedAt": generated_at,
        "skills": state,
    })

    # Prune history files older than 30 days
    cutoff = _utcnow() - timedelta(days=30)
    for f in sorted(history_dir.glob("*.json")):
        try:
            file_date = datetime.strptime(f.stem, "%Y-%m-%d")
            if file_date < cutoff:
                f.unlink()
        except ValueError:
            pass  # skip files that don't match date pattern


def _find_history_snapshot(
    history_dir: Path, target_date: datetime, tolerance_days: int = 2
) -> dict:
    """Find the history snapshot nearest to target_date within ±tolerance_days."""
    best: dict = {}
    best_delta = timedelta(days=tolerance_days + 1)

    for f in history_dir.glob("*.json"):
        try:
            file_date = datetime.strptime(f.stem, "%Y-%m-%d")
            delta = abs(file_date - target_date)
            if delta <= timedelta(days=tolerance_days) and delta < best_delta:
                data = json.loads(f.read_text(encoding="utf-8"))
                best = data.get("skills", {})
                best_delta = delta
        except (ValueError, json.JSONDecodeError, OSError):
            pass

    return best


# ---------------------------------------------------------------------------
# Skill data loading
# ---------------------------------------------------------------------------


def _load_skills_index(api_dir: Path) -> list[dict]:
    """Load all skills from docs/api/v1/skills/index.json and paginated pages."""
    index_path = api_dir / "skills" / "index.json"
    if not index_path.exists():
        return []

    index = json.loads(index_path.read_text(encoding="utf-8"))
    all_skills = list(index.get("skills", []))

    # Load additional pages if present
    total_pages = index.get("totalPages", 1)
    for page_num in range(2, total_pages + 1):
        page_path = api_dir / "skills" / f"page-{page_num}.json"
        if page_path.exists():
            try:
                page_data = json.loads(page_path.read_text(encoding="utf-8"))
                all_skills.extend(page_data.get("skills", []))
            except (json.JSONDecodeError, OSError):
                pass

    return all_skills


def _load_skill_detail(api_dir: Path, skill_id: str) -> dict:
    """Load full skill detail JSON for a given skill_id."""
    contributor, slug = _slug_from_id(skill_id)
    path = api_dir / "skills" / contributor / f"{slug}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Trending score formula (read-only — no TM recomputation)
# ---------------------------------------------------------------------------


def _trending_score(
    cur_tm: float,
    prior_tm: float,
    timeline: list[dict],
    window_days: int,
) -> float:
    """Compute trending score from TM delta and timeline signals."""
    cutoff = (_utcnow() - timedelta(days=window_days)).isoformat()

    tm_delta = cur_tm - prior_tm
    tm_delta_pct = tm_delta / max(prior_tm, 1.0)

    rank_changed = any(
        e.get("action") in ("rank_up", "demote", "calibrate")
        and e.get("timestamp", "") >= cutoff
        for e in timeline
    )

    evidence_added = sum(
        1 for e in timeline
        if e.get("action") == "evidence_added"
        and e.get("timestamp", "") >= cutoff
    )
    evidence_signal = min(evidence_added, 5)

    score = (
        tm_delta * 1.0
        + tm_delta_pct * 20.0
        + (50.0 if rank_changed else 0.0)
        + evidence_signal * 10.0
    )
    return round(score, 2)


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------


def build_trending_window(
    out_dir: Path,
    window: str,
    window_days: int,
    current_skills: list[dict],
    api_dir: Path,
    prior_snapshot: dict,
    first_run: bool,
    generated_at: str,
) -> None:
    """Build 7d.json or 30d.json trending list."""
    entries = []

    for skill in current_skills:
        skill_id = skill.get("id", "")
        cur_tm = skill.get("trustMagnitude", 0) or 0

        # Skip redacted skills
        if is_redacted(skill.get("level", "")):
            continue

        detail = _load_skill_detail(api_dir, skill_id)
        timeline = detail.get("timeline", [])

        is_new = skill_id not in prior_snapshot
        prior_entry = prior_snapshot.get(skill_id, {})
        prior_tm = prior_entry.get("tm", 0) if prior_entry else 0

        if first_run:
            # Cold start: sort by TM descending, no trending scores
            score = 0.0
            tm_delta = 0.0
        elif is_new:
            score = round(cur_tm * 0.5, 2)
            tm_delta = cur_tm
        else:
            prior_tm_val = float(prior_tm)
            tm_delta = round(cur_tm - prior_tm_val, 4)
            score = _trending_score(cur_tm, prior_tm_val, timeline, window_days)

        if not first_run and score <= 0:
            continue

        contributor, slug = _slug_from_id(skill_id)
        entry = {
            "id": skill_id,
            "name": skill.get("name", ""),
            "level": skill.get("level", ""),
            "contributor": skill.get("contributor", contributor),
            "trustMagnitude": cur_tm,
            "overallTrustGrade": skill.get("overallTrustGrade"),
            "trendingScore": score,
            "tmDelta": round(tm_delta, 4) if not first_run else 0.0,
            "new": is_new and not first_run,
            "_links": {"self": f"/api/v1/skills/{contributor}/{slug}.json"},
        }
        entries.append(entry)

    # Sort: cold start → TM descending; normal → trending score descending
    if first_run:
        entries.sort(key=lambda e: -e["trustMagnitude"])
    else:
        entries.sort(key=lambda e: -e["trendingScore"])

    _write_json(out_dir / f"{window}.json", {
        "window": window,
        "generatedAt": generated_at,
        "firstRun": first_run,
        "skills": entries,
        "totalTrending": len(entries),
        "_links": {"self": f"/api/v1/trending/{window}.json"},
    })


def build_ascended(
    out_dir: Path,
    current_skills: list[dict],
    api_dir: Path,
    generated_at: str,
    window_days: int = 30,
) -> None:
    """Build ascended.json — skills with rank_up/calibrate events in last 30 days."""
    cutoff = (_utcnow() - timedelta(days=window_days)).isoformat()
    entries = []

    for skill in current_skills:
        skill_id = skill.get("id", "")

        if is_redacted(skill.get("level", "")):
            continue

        detail = _load_skill_detail(api_dir, skill_id)
        timeline = detail.get("timeline", [])

        # Find the most recent rank_up/calibrate event within window
        ascend_events = [
            e for e in timeline
            if e.get("action") in ("rank_up", "calibrate")
            and e.get("timestamp", "") >= cutoff
        ]

        if not ascend_events:
            continue

        # Most recent event timestamp and event
        ascended_at = max(e.get("timestamp", "") for e in ascend_events)
        latest_event = max(ascend_events, key=lambda e: e.get("timestamp", ""))

        # Extract previousLevel from event details text
        # e.g. "Level updated from 1★ to 4★ …"
        previous_level: str | None = None
        details = latest_event.get("details", "")
        m_prev = re.search(r"from\s+(\S+)\s+to\s+", details)
        if m_prev:
            previous_level = m_prev.group(1).strip()

        contributor, slug = _slug_from_id(skill_id)
        entry: dict = {
            "id": skill_id,
            "name": skill.get("name", ""),
            "level": skill.get("level", ""),
            "contributor": skill.get("contributor", contributor),
            "trustMagnitude": skill.get("trustMagnitude", 0),
            "overallTrustGrade": skill.get("overallTrustGrade"),
            "ascendedAt": ascended_at,
            "_links": {"self": f"/api/v1/skills/{contributor}/{slug}.json"},
        }
        if previous_level:
            entry["previousLevel"] = previous_level
        entries.append(entry)

    # Sort by most recent ascendedAt descending
    entries.sort(key=lambda e: e.get("ascendedAt", ""), reverse=True)
    entries = entries[:30]

    _write_json(out_dir / "ascended.json", {
        "generatedAt": generated_at,
        "skills": entries,
        "_links": {"self": "/api/v1/trending/ascended.json"},
    })


def _write_rss(out_dir: Path, trending_7d: list[dict], generated_at: str) -> None:
    """Write valid RSS 2.0 feed.xml for the top 20 trending skills."""
    # Parse generated_at (ISO 8601 UTC) into RFC 2822 for <lastBuildDate>
    try:
        gen_dt = datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        gen_dt = datetime.now(timezone.utc)

    last_build = email.utils.format_datetime(gen_dt)
    top20 = trending_7d[:20]

    items_xml: list[str] = []
    for skill in top20:
        skill_id = skill.get("id", "")
        name = skill.get("name") or skill_id
        tm = skill.get("trustMagnitude")
        grade = skill.get("overallTrustGrade") or ""
        delta = skill.get("tmDelta")

        # Title: "Skill Name (+5.2 TM)" or just "Skill Name"
        if delta is not None and delta != 0.0:
            sign = "+" if delta > 0 else ""
            title = f"{name} ({sign}{delta:.1f} TM)"
        else:
            title = name

        link = f"https://gaia.tiongson.co/named/#explorer/{skill_id}"

        # Description: TM + grade
        tm_str = f"{tm:.1f}" if isinstance(tm, (int, float)) else "—"
        grade_str = f" · Grade {grade}" if grade else ""
        description = f"Trust Magnitude: {tm_str}{grade_str}"

        # pubDate — use generated_at as RFC 2822
        pub_date = last_build

        # Date part of generated_at for guid suffix (YYYY-MM-DD)
        date_part = generated_at[:10]

        guid = f"gaia-trending-{skill_id}-{date_part}"

        def _xml(s: str) -> str:
            """Escape XML special characters."""
            return (
                str(s)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        items_xml.append(
            f"    <item>\n"
            f"      <title>{_xml(title)}</title>\n"
            f"      <link>{_xml(link)}</link>\n"
            f"      <description>{_xml(description)}</description>\n"
            f"      <pubDate>{pub_date}</pubDate>\n"
            f"      <guid isPermaLink=\"false\">{_xml(guid)}</guid>\n"
            f"    </item>"
        )

    items_block = "\n".join(items_xml)
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '  <channel>\n'
        '    <title>Gaia Trending Skills</title>\n'
        '    <link>https://gaia.tiongson.co/trending/</link>\n'
        '    <description>Skills gaining trust this week — ranked by evidence velocity, not hype.</description>\n'
        '    <language>en-us</language>\n'
        f'    <lastBuildDate>{last_build}</lastBuildDate>\n'
        '    <atom:link href="https://gaia.tiongson.co/api/v1/trending/feed.xml"'
        ' rel="self" type="application/rss+xml"/>\n'
        f'{items_block}\n'
        '  </channel>\n'
        '</rss>\n'
    )

    feed_path = out_dir / "feed.xml"
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_text(rss, encoding="utf-8")


def build_contested(
    out_dir: Path,
    current_skills: list[dict],
    api_dir: Path,
    generated_at: str,
) -> None:
    """Build contested.json — genericSkillRef buckets with >=2 named implementations."""
    # Build buckets keyed by genericSkillRef
    buckets: dict[str, list[dict]] = {}

    for skill in current_skills:
        if is_redacted(skill.get("level", "")):
            continue

        skill_id = skill.get("id", "")
        detail = _load_skill_detail(api_dir, skill_id)
        generic_ref = detail.get("genericSkillRef") or ""

        if not generic_ref:
            continue

        contributor, slug = _slug_from_id(skill_id)
        entry = {
            "id": skill_id,
            "trustMagnitude": skill.get("trustMagnitude", 0),
            "level": skill.get("level", ""),
            "overallTrustGrade": skill.get("overallTrustGrade"),
        }
        buckets.setdefault(generic_ref, []).append(entry)

    # Filter to buckets with >= 2 implementations
    contested = {ref: skills for ref, skills in buckets.items() if len(skills) >= 2}

    # Build output — sort each bucket by TM descending; mark origin (highest TM)
    bucket_list = []
    for ref, skills in contested.items():
        skills.sort(key=lambda s: -(s.get("trustMagnitude") or 0))
        # Mark the top skill as origin (highest TM = most established impl)
        for i, s in enumerate(skills):
            s["origin"] = i == 0
        top_tm = skills[0].get("trustMagnitude", 0) if skills else 0
        bucket_list.append({
            "genericSkillRef": ref,
            "implementations": len(skills),
            "topTM": top_tm,
            "skills": skills,
        })

    # Sort buckets by topTM descending
    bucket_list.sort(key=lambda b: -(b.get("topTM") or 0))
    bucket_list = bucket_list[:20]

    _write_json(out_dir / "contested.json", {
        "generatedAt": generated_at,
        "buckets": bucket_list,
        "_links": {"self": "/api/v1/trending/contested.json"},
    })


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def run(out_dir: Path) -> int:
    """Execute the full trending projection. Returns 0 on success, 1 on error."""
    api_dir = ROOT / "docs" / "api" / "v1"
    trending_dir = out_dir / "trending"
    snapshot_path = trending_dir / "snapshot.json"
    history_dir = trending_dir / "history"

    # Load the committed API projection (NOT registry/named-skills.json)
    current_skills = _load_skills_index(api_dir)

    if not current_skills:
        print(
            "FATAL: No skills found in docs/api/v1/skills/index.json. "
            "Run `python scripts/buildApiProjection.py` first.",
            file=sys.stderr,
        )
        return 1

    # Filter redacted skills
    current_skills = [
        s for s in current_skills if not is_redacted(s.get("level", ""))
    ]

    generated_at = _iso_now()
    today = _today_str()

    # Load prior snapshot
    snapshot_data = _load_snapshot(snapshot_path)
    prior_skills_state: dict = snapshot_data.get("skills", {}) if snapshot_data else {}

    first_run = not bool(prior_skills_state)

    # Build current state dict for snapshot
    current_state: dict = {}
    for skill in current_skills:
        skill_id = skill.get("id", "")
        current_state[skill_id] = {
            "tm": skill.get("trustMagnitude", 0),
            "grade": skill.get("overallTrustGrade"),
            "level": skill.get("level", ""),
            "updatedAt": generated_at,
        }

    # Resolve prior snapshots for 7d and 30d windows
    now_dt = _utcnow()
    history_dir.mkdir(parents=True, exist_ok=True)

    target_7d = now_dt - timedelta(days=7)
    target_30d = now_dt - timedelta(days=30)

    prior_7d = _find_history_snapshot(history_dir, target_7d)
    prior_30d = _find_history_snapshot(history_dir, target_30d)

    # On first run, use current state as the prior (delta = 0)
    if first_run:
        prior_7d = current_state
        prior_30d = current_state

    # Save snapshot and archive history BEFORE building trending files
    _save_snapshot(snapshot_path, current_state, generated_at)
    _archive_history(history_dir, current_state, generated_at)

    # Build output files
    build_trending_window(
        trending_dir, "7d", 7, current_skills, api_dir,
        prior_7d, first_run, generated_at,
    )
    build_trending_window(
        trending_dir, "30d", 30, current_skills, api_dir,
        prior_30d, first_run, generated_at,
    )
    build_ascended(trending_dir, current_skills, api_dir, generated_at)
    build_contested(trending_dir, current_skills, api_dir, generated_at)

    # Build RSS feed from 7d trending list
    trending_7d_data = json.loads((trending_dir / "7d.json").read_text(encoding="utf-8"))
    _write_rss(trending_dir, trending_7d_data.get("skills", []), generated_at)

    print(f"Trending projection written to {trending_dir}/")
    print(f"  snapshot.json, history/{today}.json")
    print(f"  7d.json, 30d.json, ascended.json, contested.json, feed.xml")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate docs/api/v1/trending/ static JSON trending projection."
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Output directory root (trending/ subdir is written here)",
    )
    args = parser.parse_args(argv)
    rc = run(Path(args.out_dir))
    sys.exit(rc)


if __name__ == "__main__":
    main()
