"""The executable Class B trust-calibration route (founder ruling F1, #2283).

Founder ruling F1 (2026-11-08, verbatim note): "Normally once a skill gets in
the tree, this is now debt. A steward run will be canon if it detects below
ceiling, and should calibrate automatically. Other ways to do this is through
me, the verifier, or through a full monthly meta audit/closeout. So yes, it is
technically a ceiling, but steward is now allowed to do this fully."

Founder ruling F3 (verbatim note): "As LONG as evidence points correctly and
gives the correct trust magnitude, proposals are valid. The reason for demotion
should be checked since usually it just means that there is no evidence."

This module is the one definition of what the route may carry and how its
result is proven. It is used in three places, so they cannot drift apart:

* the sensor marks every ``trust_calibration_drift`` finding the route may never
  carry ``laneEligible: false`` with a reason (it stays open and visible);
* routing refuses such a packet, from the lane or an explicit ``--debt``;
* verification re-derives eligibility and the target live, and proves the diff
  is exactly what ``gaia dev calibrate <id> <target> --no-build`` writes.

A packet is one skill, one promotion to its grade target. Never a demotion
(``ceiling-exceeded``), never a frozen skill, never a skill whose last rank
event is a recorded demotion (F3: those stay proposals for the curator, with
the demotion reason shown), never a cap-only suite component to 3★ or higher
(F2), and never a calibration a canonical preflight refuses.

Class S artifacts (``docs/**``) are not written by a packet: parallel per-skill
builders would conflict on the same generated files. The lead regenerates the
deterministic Class S set once per integrated wave (``gaia dev docs``), and
Guard E holds on the integration-to-main delivery; see the routine guide.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

CALIBRATION_ROUTE_DEBT_KIND = "trust_calibration_drift"
CALIBRATION_ROUTE_RULE_ID = "trust-calibration-drift"
CALIBRATION_ROUTE_ALLOWED = ("registry/named/**",)
NAMED_ROOT = "registry/named"

_LEVEL_ORDER = {"1★": 1, "2★": 2, "3★": 3, "4★": 4, "5★": 5, "6★": 6}
# Frontmatter keys the calibrate verb may change; everything else must be equal.
_WRITABLE_KEYS = frozenset({"level", "updatedAt", "timeline"})


def subjectPath(skill_id: str) -> str:
    """The registry source a calibration of ``skill_id`` writes."""

    return f"{NAMED_ROOT}/{skill_id}.md"


def ineligibilityReason(observed_state: Mapping[str, Any], current_level: Any) -> str | None:
    """Why the route may not carry this finding, or None when it may.

    Reads only the sensor's own annotations, so the sensor, routing and
    verification apply one rule. A missing annotation is a refusal, never a pass.
    """

    target = observed_state.get("targetLevel")
    if target not in _LEVEL_ORDER or current_level not in _LEVEL_ORDER:
        return "the finding carries no comparable stored and target level"
    direction = observed_state.get("direction")
    if direction is None:
        return "the finding carries no direction annotation; refusing rather than guessing"
    if direction != "promotion-candidate" or _LEVEL_ORDER[target] <= _LEVEL_ORDER[current_level]:
        return (
            "ceiling-exceeded: founder ruling F1 covers below-ceiling promotions only; a demotion keeps its "
            "governed authority (Yggdrasil IV)"
        )
    if observed_state.get("frozen") is not False:
        return "the skill is frozen (or its frozen status is unknown); frozen records are never calibrated"
    demotion = observed_state.get("priorGovernedDemotion")
    if demotion is not None:
        when = demotion.get("timestamp", "?") if isinstance(demotion, Mapping) else "?"
        why = demotion.get("details", "") if isinstance(demotion, Mapping) else ""
        return (
            f"F3 proposal only: the last rank event is a recorded demotion ({when}: {why or 'no reason recorded'}); "
            "check the reason (usually missing evidence) and let the curator decide"
        )
    if observed_state.get("capOnlySuiteComponent") is not False and _LEVEL_ORDER[target] >= 3:
        if observed_state.get("capOnlySuiteComponent") is None:
            return "the finding carries no capOnlySuiteComponent annotation; refusing rather than guessing"
        return (
            "F2: a suite component whose Trust Magnitude comes only from the inherited suite-repository cap "
            "never receives an automatic 3★ or higher"
        )
    refused = observed_state.get("commandWouldBeRefused")
    if refused is True:
        gates = [str(item.get("gate")) for item in observed_state.get("gatesUnmet") or [] if isinstance(item, Mapping)]
        return "a canonical calibrate preflight refuses this calibration: " + ", ".join(gates)
    if refused is not False:
        return "a canonical calibrate preflight could not be evaluated; refusing rather than guessing"
    return None


def liveObservation(repo_root: Path, skill_id: str) -> tuple[Any, dict[str, Any] | None]:
    """Re-derive this one skill's drift finding from the registry at ``repo_root``.

    Returns ``(stored level, observed state)``; the state is None when the skill
    shows no ``trust_calibration_drift`` now. The computation is the sensor's own
    (one evidence context, the same annotations), run for a single record.
    """

    from gaia_cli.steward.sensors import TrustCalibrationDriftSensor

    return TrustCalibrationDriftSensor.observeOne(repo_root, skill_id)


def liveIneligibility(
    repo_root: Path, skill_id: str, *, expected_current: Any, expected_target: Any
) -> str | None:
    """Why a packet for ``skill_id`` may not run or be accepted now, from live state."""

    try:
        current, state = liveObservation(repo_root, skill_id)
    except Exception as exc:  # noqa: BLE001 - any failure to re-derive is a refusal, reported with its type
        return f"the finding could not be re-derived live ({type(exc).__name__}); refusing"
    if state is None:
        return "the skill no longer shows trust_calibration_drift on the current registry"
    if current != expected_current or state.get("targetLevel") != expected_target:
        return (
            f"the packet is stale: it was cut for {expected_current} -> {expected_target}, the registry now "
            f"shows {current} -> {state.get('targetLevel')}"
        )
    return ineligibilityReason(state, current)


def _splitRecord(text: str) -> tuple[dict[str, Any] | None, str | None, str | None]:
    import yaml

    from gaia_cli.frontmatter import split_frontmatter

    fence, raw, body = split_frontmatter(text)
    if not fence:
        return None, None, "no closed frontmatter fence"
    try:
        meta = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, None, f"frontmatter is not valid YAML ({type(exc).__name__})"
    if not isinstance(meta, dict):
        return None, None, "frontmatter is not a mapping"
    return meta, body, None


def proveCalibrationEdit(
    *,
    skill_id: str,
    current_level: str,
    target_level: str,
    base_text: str | None,
    post_text: str | None,
) -> list[str]:
    """Structural proof that ``post_text`` is exactly one calibrate write.

    The registry record may be re-serialized by the verb, so the comparison is
    semantic (parsed frontmatter and the byte-exact body), never line by line:
    every key other than ``level``, ``updatedAt`` and ``timeline`` is equal;
    ``level`` moves from the packet's stored level to its target; ``timeline``
    is the base timeline plus exactly one appended ``rank_up`` event whose
    details are the verb's own ``Calibrated level from X to Y``; the body is
    unchanged.
    """

    if base_text is None:
        return ["the subject record's base content could not be read"]
    if post_text is None:
        return ["the subject record's post-diff content could not be reconstructed"]
    base, base_body, problem = _splitRecord(base_text)
    if problem:
        return [f"base record: {problem}"]
    post, post_body, problem = _splitRecord(post_text)
    if problem:
        return [f"post-diff record: {problem}"]
    assert base is not None and post is not None
    problems: list[str] = []
    if base.get("id") != skill_id or post.get("id") != skill_id:
        problems.append(f"the record does not belong to {skill_id}")
    if post_body != base_body:
        problems.append("the record body changed; calibrate writes frontmatter only")
    changed = sorted(key for key in set(base) | set(post) if key not in _WRITABLE_KEYS and base.get(key) != post.get(key))
    if changed:
        problems.append("frontmatter keys other than level/updatedAt/timeline changed: " + ", ".join(changed))
    if base.get("level") != current_level:
        problems.append(f"base level is {base.get('level')!r}, the packet was cut for {current_level!r}")
    if post.get("level") != target_level:
        problems.append(f"post level is {post.get('level')!r}, the packet target is {target_level!r}")
    if not isinstance(post.get("updatedAt"), str) and post.get("updatedAt") is not None:
        problems.append("updatedAt is not a date string")
    base_timeline = base.get("timeline") if isinstance(base.get("timeline"), list) else []
    post_timeline = post.get("timeline") if isinstance(post.get("timeline"), list) else []
    if len(post_timeline) != len(base_timeline) + 1 or post_timeline[: len(base_timeline)] != base_timeline:
        problems.append("the timeline must equal the base timeline plus exactly one appended event")
    else:
        event = post_timeline[-1]
        expected = f"Calibrated level from {current_level} to {target_level}"
        if not isinstance(event, dict):
            problems.append("the appended timeline event is not a mapping")
        else:
            if event.get("action") != "rank_up":
                problems.append(f"the appended event action is {event.get('action')!r}, not 'rank_up'")
            if event.get("details") != expected:
                problems.append(f"the appended event details are not the verb's own {expected!r}")
            if not event.get("timestamp"):
                problems.append("the appended event has no timestamp")
            extra = sorted(set(event) - {"timestamp", "action", "contributor", "details"})
            if extra:
                problems.append("the appended event carries unexpected keys: " + ", ".join(extra))
    return problems


def calibrationViolations(
    repo_root: Path,
    *,
    packet_debt: Mapping[str, Any],
    change_paths: tuple[str, ...],
    created_or_deleted: tuple[str, ...],
    base_text: str | None,
    post_text: str | None,
) -> list[str]:
    """Every reason a calibration candidate must be rejected (empty when proven).

    Mechanical, in order: one file, exactly the subject's registry source; the
    edit is one calibrate write; eligibility and the target re-derived live
    (Trust Magnitude and grade recomputed by the verifier, preflights re-run).
    """

    subject = packet_debt.get("subject") if isinstance(packet_debt.get("subject"), Mapping) else {}
    skill_id = str(subject.get("id") or "")
    current = (packet_debt.get("currentState") or {}).get("level")
    target = (packet_debt.get("observedState") or {}).get("targetLevel")
    expected_path = subjectPath(skill_id)
    if change_paths != (expected_path,):
        return [
            f"a calibration diff must touch exactly {expected_path}; it touches "
            + (", ".join(change_paths) or "nothing")
        ]
    if created_or_deleted:
        return ["a calibration diff may not create or delete the record"]
    problems = proveCalibrationEdit(
        skill_id=skill_id,
        current_level=str(current),
        target_level=str(target),
        base_text=base_text,
        post_text=post_text,
    )
    reason = ineligibilityReason(packet_debt.get("observedState") or {}, current)
    if reason:
        problems.append("the dispatched finding was not eligible: " + reason)
    live = liveIneligibility(repo_root, skill_id, expected_current=current, expected_target=target)
    if live:
        problems.append("live re-derivation refuses: " + live)
    return problems
