"""Steward sensor for GitHub issue hygiene (#2130, contract section 3.6).

The sensor never touches the network and never writes. It reads the driver census
(``steward-github-census-v1``), judges it, and runs the real reconciliation
(``reconcile.reconcile``) over the census, the local registry and the local workflow
files. The manifest is folded into three debt kinds:

- ``issue_closure_ready`` (Class A): one debt per enabled closure rule, carrying the
  closure plans that ``closure.planClosures`` derives from proven items. The runner
  turns these into ``forge.close_issue`` actions under its own gates.
- ``issue_suite_review`` (Class B): one debt per suite batch (or ``unbatched``).
- ``issue_founder_decision`` (Class C): one debt per founder question.

Anything the census or manifest cannot prove fails closed: a missing census is
``SensorNotEvaluated``; an incomplete, stale or unreconcilable census is
``SensorUnavailable`` (coverage unknown, Class A blocked for the run); a manifest
that reports unknown coverage is ``SensorUnavailable``; a manifest scope it could
not evaluate is a skipped subject, so nothing is swept there.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from gaia_cli.steward.issuehygiene.census import Census, loadCensus
from gaia_cli.steward.issuehygiene.closure import planClosures
from gaia_cli.steward.issuehygiene.hygienepolicy import KNOWN_RULE_IDS, HygienePolicy
from gaia_cli.steward.issuehygiene.reconcile import SCHEMA_VERSION as MANIFEST_SCHEMA
from gaia_cli.steward.issuehygiene.reconcile import reconcile, workflowProbesFor
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from gaia_cli.steward.models import Observation, SensorScan, Subject, stable_json
from gaia_cli.steward.primitives import SensorNotEvaluated, SensorUnavailable, git_root
from gaia_cli.steward.primitives.inputs import parse_instant
from gaia_cli.steward.primitives.redact import scrub

CENSUS_INPUT = Path(".gaia/steward/inputs/github-issues.json")
CENSUS_SCHEMA = "steward-github-census-v1"
UNBATCHED = "unbatched"
UNQUESTIONED = "unquestioned"
AUTHORITIES = ("A", "B", "C", "none")
# Bounded so one large suite cannot blow the observation budget or the ledger.
MAX_ITEMS_PER_DEBT = 200
# Plans are derived for every proven item; the runner applies the per-run cap, not the sensor.
PLAN_CEILING = 1_000_000
NOT_EVALUATED_LIMIT = 10
_TEXT_LIMIT = 400


def _text(value: Any, limit: int = _TEXT_LIMIT) -> str:
    """A string echoed on purpose: scrubbed and bounded. Anything else becomes empty."""

    return scrub(value)[:limit] if isinstance(value, str) else ""


def _digest(manifest: Mapping[str, Any]) -> str:
    """Content digest of the manifest with its fetch time removed.

    ``censusFetchedAt`` changes on every collection even when no issue did;
    leaving it out keeps an unchanged backlog from re-keying every debt.
    """

    stripped = {key: value for key, value in manifest.items() if key not in ("censusFetchedAt", "manifestSha256")}
    return hashlib.sha256(stable_json(stripped).encode("utf-8")).hexdigest()


def _hygienePolicy(root: Path) -> HygienePolicy:
    from gaia_cli.steward.policy import PolicyError, StewardPolicy

    try:
        return StewardPolicy.load(root).issue_hygiene
    except PolicyError as exc:
        raise SensorUnavailable(f"steward policy is unreadable for issue hygiene: {exc}") from exc


def reconcileCensus(census: Census, root: Path, hygiene: HygienePolicy, now: Any) -> Mapping[str, Any]:
    """Run the real reconciliation: registry index, workflow probes, then the manifest.

    Reads local files only. Any failure is coverage unknown with the exception type
    named, never a crash and never the exception text (which may echo a body).
    """

    try:
        index = buildRegistryIndex(root)
        probes = workflowProbesFor(root, census, hygiene)
        manifest = reconcile(census, index, hygiene, now, workflowDisabled=probes)
    except Exception as exc:  # noqa: BLE001 - any reconciliation failure is coverage unknown
        raise SensorUnavailable(f"issue reconciliation failed: {type(exc).__name__}") from exc
    if not isinstance(manifest, Mapping):
        raise SensorUnavailable("issue reconciliation returned no manifest object")
    return manifest


def _validateManifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schemaVersion") != MANIFEST_SCHEMA:
        raise SensorUnavailable(f"reconciliation manifest does not declare {MANIFEST_SCHEMA}")
    coverage = manifest.get("coverage")
    if not isinstance(coverage, Mapping):
        raise SensorUnavailable("reconciliation manifest has no coverage object")
    unknown = coverage.get("unknown") or []
    if unknown:
        listed = ", ".join(_text(str(item), 80) for item in list(unknown)[:5])
        raise SensorUnavailable(f"reconciliation coverage is unknown for {listed}")
    items = manifest.get("items")
    if not isinstance(items, list):
        raise SensorUnavailable("reconciliation manifest items must be a list")
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise SensorUnavailable(f"reconciliation item {index} is not an object")
        if not isinstance(item.get("key"), str) or not item["key"]:
            raise SensorUnavailable(f"reconciliation item {index} has no semantic key")
        if item.get("authority") not in AUTHORITIES:
            raise SensorUnavailable(f"reconciliation item {index} has an unknown authority")
        number = item.get("issue")
        if isinstance(number, bool) or not isinstance(number, int):
            raise SensorUnavailable(f"reconciliation item {index} has no issue number")


def _provableClosure(item: Mapping[str, Any], hygiene: HygienePolicy) -> bool:
    """A plan counts only when the contract's proof conditions hold (contract 3.3)."""

    rule = item.get("ruleId")
    return (
        item.get("authority") == "A"
        and item.get("confidence") == "proven"
        and not item.get("unknowns")
        and isinstance(rule, str)
        and rule in KNOWN_RULE_IDS
        and hygiene.ruleEnabled(rule)
    )


def _observedPlan(plan: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """A closure plan as debt state: without its closing comment, which the emitter rebuilds.

    The comment is roughly as large as the original payload it quotes, and every debt row keeps
    its plans, so it is dropped here. ``reconciliationSha256`` keeps the rebuild byte-identical.
    """

    observed = {key: value for key, value in plan.items() if key != "comment"}
    observed["reconciliationSha256"] = manifest["manifestSha256"]
    return observed


def _closurePlans(manifest: Mapping[str, Any], hygiene: HygienePolicy) -> list[dict]:
    """Closure plans from lane B's planner, restricted to items whose proof still holds."""

    everything = replace(hygiene, writesEnabled=True, maxClosuresPerRun=PLAN_CEILING)
    items = {item["issue"]: item for item in manifest["items"]}
    plans = []
    for plan in planClosures(dict(manifest), everything):
        item = items.get(plan["issue"])
        if item is not None and _provableClosure(item, hygiene):
            plans.append(_observedPlan(plan, manifest))
    return sorted(plans, key=lambda plan: plan["issue"])


def _observation(
    kind: str, subject: Subject, observed_at: str, provenance: Mapping[str, Any], *,
    status: str, observed: Mapping[str, Any],
) -> Observation:
    return Observation(
        kind=kind, subject=subject, observed_at=observed_at, source=IssueHygieneSensor.id,
        status=status, current_state={"count": 0}, observed_state=dict(observed), provenance=dict(provenance),
    )


def _suiteRow(item: Mapping[str, Any]) -> dict[str, Any]:
    notProven = item.get("notProven") if isinstance(item.get("notProven"), list) else []
    return {
        "issue": item["issue"], "key": _text(item["key"], 200), "kind": _text(item.get("kind"), 32),
        "state": _text(item.get("state"), 32), "ruleId": _text(item.get("ruleId"), 64),
        "authority": item.get("authority"),
        "notProven": [_text(reason, 120) for reason in notProven[:3] if isinstance(reason, str)],
    }


class IssueHygieneSensor:
    """Class A/B/C debt from the reconciled GitHub issue census. Exhaustive when it observes."""

    id = "issue-hygiene"
    debt_kinds = ("issue_closure_ready", "issue_suite_review", "issue_founder_decision")
    routine_ids = (18,)
    resolution_scope = "exhaustive"
    driver_inputs = (CENSUS_INPUT.as_posix(),)

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return list(self.scan_detailed(repo_root, observed_at).observations)

    def scan_detailed(self, repo_root: Path, observed_at: str) -> SensorScan:
        root = git_root(repo_root)
        path = root / CENSUS_INPUT
        if not path.exists() and not path.is_symlink():
            raise SensorNotEvaluated(
                f"no {CENSUS_INPUT.name} supplied; a driver must collect the GitHub issue census",
                input_absent=True,
            )
        now = parse_instant(observed_at, "observed_at")
        hygiene = _hygienePolicy(root)
        census = loadCensus(path, now=now, maxAgeSeconds=hygiene.maxCensusAgeSeconds)
        if not census.status.complete:
            reasons = ", ".join(_text(reason, 80) for reason in census.status.reasons[:3]) or "no reason recorded"
            raise SensorUnavailable(f"issue census is {census.status.status}: {reasons}")
        manifest = reconcileCensus(census, root, hygiene, now)
        _validateManifest(manifest)
        return self._observations(manifest, hygiene, observed_at)

    def _observations(self, manifest: Mapping[str, Any], hygiene: HygienePolicy, observed_at: str) -> SensorScan:
        digest = _digest(manifest)
        stats = manifest.get("stats") if isinstance(manifest.get("stats"), Mapping) else {}
        # Provenance carries the backlog counts so a receipt can show before and after.
        provenance = {
            "input": CENSUS_INPUT.as_posix(),
            "schemaVersion": CENSUS_SCHEMA,
            "manifestSchemaVersion": MANIFEST_SCHEMA,
            "manifestDigest": digest,
            "censusStatus": _text(manifest.get("censusStatus"), 32),
            "censusFetchedAt": _text(manifest.get("censusFetchedAt"), 40),
            "stats": {key: value for key, value in stats.items() if isinstance(value, int) and not isinstance(value, bool)},
        }
        plans = _closurePlans(manifest, hygiene)
        planned = {plan["issue"] for plan in plans}
        suite_rows: dict[str, list[dict[str, Any]]] = {}
        founder_items: list[Mapping[str, Any]] = []
        for item in manifest["items"]:
            if item.get("authority") == "none" or item["issue"] in planned:
                continue
            if item.get("authority") == "C":
                founder_items.append(item)
                continue
            # Class B, and any A that the planner did not plan: never upgraded, so it is batch review.
            suite = item.get("suite") if isinstance(item.get("suite"), str) and item.get("suite") else UNBATCHED
            suite_rows.setdefault(suite, []).append(_suiteRow(item))

        observations: list[Observation] = []
        for rule in sorted(rule for rule in KNOWN_RULE_IDS if hygiene.ruleEnabled(rule)):
            rows = [plan for plan in plans if plan["ruleId"] == rule]
            observations.append(_observation(
                kind="issue_closure_ready", subject=Subject(type="issue-rule", id=rule),
                observed_at=observed_at, provenance=provenance,
                status="drift" if rows else "healthy",
                observed={"ruleId": rule, "count": len(rows), "plans": rows[:MAX_ITEMS_PER_DEBT],
                          "truncated": len(rows) > MAX_ITEMS_PER_DEBT, "manifestDigest": digest},
            ))
        for suite in sorted(suite_rows):
            rows = sorted(suite_rows[suite], key=lambda row: row["issue"])
            umbrella = next((batch.get("umbrella") for batch in manifest.get("batches") or []
                             if isinstance(batch, Mapping) and batch.get("suite") == suite), None)
            observations.append(_observation(
                kind="issue_suite_review", subject=Subject(type="issue-suite", id=suite),
                observed_at=observed_at, provenance=provenance, status="drift",
                observed={"suite": suite, "umbrella": umbrella if isinstance(umbrella, int) else None,
                          "count": len(rows), "items": rows[:MAX_ITEMS_PER_DEBT],
                          "truncated": len(rows) > MAX_ITEMS_PER_DEBT, "manifestDigest": digest},
            ))
        observations.extend(self._founder(manifest, founder_items, observed_at, provenance, digest))
        skipped = self._notEvaluated(manifest)
        return SensorScan(observations=tuple(observations), skipped=skipped)

    @staticmethod
    def _notEvaluated(manifest: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
        """Issues the reconciliation could not evaluate: one partial-coverage subject, never a sweep."""

        numbers = [n for n in (manifest["coverage"].get("notEvaluated") or [])
                   if isinstance(n, int) and not isinstance(n, bool)]
        if not numbers:
            return ()
        named = ", ".join(f"#{number}" for number in numbers[:NOT_EVALUATED_LIMIT])
        return ({
            "subjectType": "issue-scope",
            "subjectId": "unevaluated-issues",
            "reason": f"{len(numbers)} issue(s) not evaluated by issue reconciliation: {named}",
        },)

    @staticmethod
    def _founder(
        manifest: Mapping[str, Any], founder_items: list[Mapping[str, Any]],
        observed_at: str, provenance: Mapping[str, Any], digest: str,
    ) -> list[Observation]:
        observations: list[Observation] = []
        questions = [q for q in manifest.get("founderQuestions") or [] if isinstance(q, Mapping)]
        known = {_text(q.get("id"), 40) for q in questions}
        for question in sorted(questions, key=lambda q: _text(q.get("id"), 40)):
            qid = _text(question.get("id"), 40)
            if not qid:
                continue
            affected = sorted({n for n in question.get("affected") or []
                               if isinstance(n, int) and not isinstance(n, bool)})
            observations.append(_observation(
                kind="issue_founder_decision", subject=Subject(type="issue-question", id=qid),
                observed_at=observed_at, provenance=provenance, status="drift",
                observed={
                    # The founder queue groups by this exact target: one decision per question.
                    "decisionTarget": f"issue-question/{qid}".lower(),
                    "question": _text(question.get("question")),
                    "affected": affected[:MAX_ITEMS_PER_DEBT],
                    "affectedCount": len(affected),
                    "options": [_text(option, 60) for option in (question.get("options") or [])[:8]
                                if isinstance(option, str)],
                    "recommendation": _text(question.get("recommendation"), 60) or None,
                    "basis": _text(question.get("basis")),
                    "manifestDigest": digest,
                },
            ))
        orphans = sorted(
            item["issue"] for item in founder_items
            if not (set(item.get("questions") or []) & known)
        )
        if orphans:
            observations.append(_observation(
                kind="issue_founder_decision", subject=Subject(type="issue-question", id=UNQUESTIONED),
                observed_at=observed_at, provenance=provenance, status="drift",
                observed={"decisionTarget": "issue-question/unquestioned",
                          "question": "Issues await a founder decision that no founder question names.",
                          "affected": orphans[:MAX_ITEMS_PER_DEBT], "affectedCount": len(orphans),
                          "options": [], "recommendation": None, "basis": "", "manifestDigest": digest},
            ))
        return observations
