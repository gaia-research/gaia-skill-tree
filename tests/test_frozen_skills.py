"""Frozen named skills must stay frozen, and keep the stars they were frozen at.

"Frozen" has one definition, ``gaia_cli.frozen.frozenIds`` (founder ruling
2026-10-30). Founder ruling 2026-11-03: a frozen skill keeps its stars, evidence
and calibration; only its computed Trust Magnitude may move. The rules below
apply to every frozen skill, including the older (August 2026) freezes.

After its own freeze event a frozen skill must not gain a rank, demote, trust
recalibration or evidence event. Two ledgers itemize the only events that exist
anyway. Each entry is checked against the registry in both directions, so a
ledger can neither hide a new change nor go stale:

* ``PRE_RULING``: events logged between the August 2026 freezes and the
  2026-10-30 ruling. Each skill ended at the stars it was frozen at and had no
  evidence change, so only the computed Trust Magnitude moved. The test
  verifies that, it is not taken on trust.
* ``WAIVED``: the 2026-11-03 restoration of ``leonxlnx/output-skill``, whose
  evidence row was removed at its freeze. No ``gaia dev`` verb can write a
  frozen record, so the founder waived the Programmatic-First rule for it.

The October 2026 freezes are also pinned so an accidental un-freeze fails here
instead of passing silently.
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from gaia_cli.frozen import frozenIds, frozenLock  # noqa: E402

OCTOBER_2026_FREEZES = {
    "leonxlnx/output-skill",
    "heygen-com/general-video",
    "heygen-com/embedded-captions",
    "heygen-com/faceless-explainer",
    "heygen-com/hyperframes-animation",
    "heygen-com/hyperframes-audio",
    "heygen-com/hyperframes-core",
    "heygen-com/hyperframes-creative",
    "heygen-com/hyperframes-keyframes",
    "heygen-com/motion-graphics",
    "heygen-com/music-to-video",
    "heygen-com/pr-to-video",
    "heygen-com/product-launch-video",
    "heygen-com/talking-head-recut",
}

LOCKED_EVENTS = {
    "rank_up", "demote", "recalibrate_trust_magnitude", "evidence_added",
    "evidence_removed", "evidence_graded", "evidence_updated",
}

# skill id -> (stars at freeze, post-freeze events as (action, timestamp)).
PRE_RULING = {
    "Manavarya09/design-extract": ("2★", (
        ("recalibrate_trust_magnitude", "2026-08-29T17:15:42Z"),
    )),
    "mattpocock/diagnose": ("3★", (
        ("recalibrate_trust_magnitude", "2026-08-29T17:15:52Z"),
        ("rank_up", "2026-09-02T15:11:39Z"),
        ("recalibrate_trust_magnitude", "2026-09-04T10:58:44Z"),
        ("demote", "2026-09-11T17:46:26Z"),
    )),
    "mattpocock/edit-article": ("3★", (
        ("recalibrate_trust_magnitude", "2026-08-29T17:15:52Z"),
        ("rank_up", "2026-09-02T15:11:39Z"),
        ("demote", "2026-09-04T00:00:00Z"),
        ("recalibrate_trust_magnitude", "2026-09-04T10:58:45Z"),
        ("rank_up", "2026-09-11T17:25:03Z"),
    )),
    "mattpocock/obsidian-vault": ("3★", (
        ("recalibrate_trust_magnitude", "2026-08-29T17:15:53Z"),
        ("rank_up", "2026-09-02T15:11:40Z"),
        ("demote", "2026-09-04T00:00:00Z"),
        ("recalibrate_trust_magnitude", "2026-09-04T10:58:45Z"),
        ("rank_up", "2026-09-11T17:25:05Z"),
    )),
    "mattpocock/personal": ("3★", (
        ("recalibrate_trust_magnitude", "2026-08-29T17:15:53Z"),
    )),
    "mattpocock/ubiquitous-language": ("3★", (
        ("recalibrate_trust_magnitude", "2026-08-29T17:15:54Z"),
        ("rank_up", "2026-09-02T15:11:40Z"),
        ("demote", "2026-09-04T00:00:00Z"),
        ("recalibrate_trust_magnitude", "2026-09-04T10:58:45Z"),
        ("rank_up", "2026-09-11T17:24:57Z"),
    )),
    "mattpocock/write-a-skill": ("2★", (
        ("recalibrate_trust_magnitude", "2026-08-29T17:15:54Z"),
        ("recalibrate_trust_magnitude", "2026-09-04T10:58:45Z"),
    )),
    "mattpocock/zoom-out": ("1★", (
        ("recalibrate_trust_magnitude", "2026-08-29T17:15:54Z"),
        ("recalibrate_trust_magnitude", "2026-09-04T10:58:45Z"),
    )),
}

# skill id -> events written under the founder's explicit 2026-11-03 waiver.
WAIVED = {
    "leonxlnx/output-skill": (
        ("evidence_added", "2026-11-03T11:30:32Z"),
        ("recalibrate_trust_magnitude", "2026-11-03T11:30:33Z"),
    ),
}


def loadAll():
    """Every named record's frontmatter, keyed by id."""
    out = {}
    for path in sorted((ROOT / "registry" / "named").glob("*/*.md")):
        match = re.match(r"---\n(.*?)\n---", path.read_text(encoding="utf-8"), re.S)
        if not match:
            continue
        data = yaml.safe_load(match.group(1)) or {}
        out[data["id"]] = data
    return out


def loadFrozen():
    """Frozen records by id (the engine's definition) mapped to (data, events, freezeAt)."""
    everything = loadAll()
    out = {}
    for skillId in frozenIds(everything.values()):
        data = everything[skillId]
        events = data.get("timeline") or []
        freezes = [str(e.get("timestamp", "")) for e in events if e.get("action") == "upstream_deprecated"]
        out[skillId] = (data, events, max(freezes) if freezes else None)
    return out


def lateEvents(events, freezeAt):
    """The locked events a record logged after its own freeze."""
    return {
        (e.get("action"), str(e.get("timestamp", "")))
        for e in events
        if e.get("action") in LOCKED_EVENTS and str(e.get("timestamp", "")) > freezeAt
    }


def test_october_2026_freezes_are_still_frozen():
    missing = sorted(OCTOBER_2026_FREEZES - set(loadFrozen()))
    assert not missing, f"October 2026 freezes were un-frozen or lost their freeze event: {missing}"


def test_frozen_skills_keep_their_install_link():
    # A suite capstone needs no links.github of its own; each component carries one.
    bad = [
        skillId for skillId, (data, _, _) in loadFrozen().items()
        if not data.get("suiteComponents") and not (data.get("links") or {}).get("github")
    ]
    assert not bad, f"frozen skills must keep links.github: {bad}"


def test_frozen_skills_have_no_calibration_or_evidence_change_after_freeze():
    """Every locked event after a freeze is itemized in PRE_RULING or WAIVED, and vice versa."""
    unexpected, stale = [], []
    for skillId, (_, events, freezeAt) in loadFrozen().items():
        if freezeAt is None:
            continue
        allowed = set(PRE_RULING.get(skillId, (None, ()))[1]) | set(WAIVED.get(skillId, ()))
        actual = lateEvents(events, freezeAt)
        unexpected += [(skillId, *item) for item in sorted(actual - allowed)]
        stale += [(skillId, *item) for item in sorted(allowed - actual)]
    assert not unexpected, f"frozen skills must not be recalibrated or have evidence changed: {unexpected}"
    assert not stale, f"ledger entries with no matching event (remove them): {stale}"


def test_pre_ruling_events_moved_only_the_computed_score():
    """The grandfathered August events never changed stars or evidence."""
    frozen = loadFrozen()
    bad = []
    for skillId, (starsAtFreeze, events) in PRE_RULING.items():
        assert skillId in frozen, f"{skillId} is in PRE_RULING but is no longer frozen"
        if frozen[skillId][0].get("level") != starsAtFreeze:
            bad.append((skillId, "stars", starsAtFreeze, frozen[skillId][0].get("level")))
        bad += [(skillId, "evidence", action) for action, _ in events if action.startswith("evidence_")]
    assert not bad, f"PRE_RULING must only cover net-zero star changes and no evidence changes: {bad}"


def test_output_skill_keeps_its_restored_evidence_and_lock():
    """The waived restoration: the github-stars-own row is back and the lock is the pre-freeze one."""
    data = loadFrozen()["leonxlnx/output-skill"][0]
    types = {row.get("type") for row in data.get("evidence") or []}
    assert {"github-stars-own", "repo-own"} <= types, f"restored evidence row is missing: {sorted(types)}"
    assert frozenLock(data) == (50.0, "B")
    assert data.get("level") == "3★"


def test_frozen_skills_display_their_stored_stars():
    """The grade ceiling never lowers a frozen skill's stars; only the computed score may move."""
    ledger = json.loads((ROOT / "docs" / "graph" / "ledger" / "data.json").read_text(encoding="utf-8"))
    rows = {r["skillId"]: r for r in ledger["rows"]}
    bad = [
        (skillId, rows[skillId]["storedStars"], rows[skillId]["currentStars"])
        for skillId in loadFrozen()
        if skillId in rows and rows[skillId].get("storedStars") != rows[skillId].get("currentStars")
    ]
    assert not bad, f"frozen skills must display their stored (frozen) stars: {bad}"


def test_freeze_set_is_not_empty():
    assert loadFrozen(), "expected at least one frozen skill in the registry"
