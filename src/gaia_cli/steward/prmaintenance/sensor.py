"""Steward sensor for routine PR maintenance (routine 19). Observes only; an observation is never permission.

It reads the driver census (``steward-pr-census-v1``), the producer registry and local git objects, and emits one
debt per registered-producer pull request. Authority comes from POLICY.yaml by debt kind: the seven routine kinds
are Class B and ``routine_pr_founder_decision`` is Class C. A missing census is ``SensorNotEvaluated``; an incomplete,
stale or unevaluable census is ``SensorUnavailable`` (coverage unknown). Deferred repositories are reported in the
provenance and are never counted healthy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gaia_cli.steward.models import Observation, SensorScan, Subject
from gaia_cli.steward.prmaintenance import advice
from gaia_cli.steward.prmaintenance.census import CENSUS_INPUT, SCHEMA_VERSION, loadPrCensus
from gaia_cli.steward.prmaintenance.evaluate import KIND_FOUNDER, KINDS, Evaluation, evaluateCensus
from gaia_cli.steward.prmaintenance.producers import RegistryError, loadRegistry
from gaia_cli.steward.primitives import SensorNotEvaluated, SensorUnavailable, git_root
from gaia_cli.steward.primitives.inputs import parse_instant
from gaia_cli.steward.primitives.redact import scrub


def _observation(kind: str, e: Evaluation, observedAt: str, provenance: dict[str, Any]) -> Observation:
    """One observation. The kind is a literal at every call site so the coverage checker can prove ownership."""

    state = {**e.asState(), **(founderState(e) if e.kind == KIND_FOUNDER else {}), "evaluationSha256": e.digest()}
    return Observation(kind=kind, subject=Subject(type="pull-request", id=e.subjectId), observed_at=observedAt,
                       source=PrMaintenanceSensor.id, status="drift", current_state={"count": 0}, observed_state=state,
                       provenance=provenance)


def founderState(e: Evaluation) -> dict[str, Any]:
    """The Class C question shape the founder desk groups by ``decisionTarget``: one decision per pull request."""

    held = "; ".join(e.reasons)[:300] or "founder decision required"
    procedural, substantive = advice.pair(g.name for g in e.gates)
    return {
        "decisionTarget": f"routine-pr/{e.repo}/{e.number}".lower(),
        "question": f"Steward will not merge or close this routine pull request ({held}). Merge, hold or close it?",
        "options": ["hold", "mark-ready-and-let-steward-verify", "close-without-merge"],
        # "hold" is a procedural recommendation about Steward's own action. It says nothing about whether the change should land.
        "recommendation": "hold",
        "recommendationKind": "procedural",
        "procedural": procedural,
        "substantive": substantive,
        "basis": f"producer {e.producerId}; head {e.headSha[:12]}; gates: "
                 + ", ".join(f"{g.name}={g.state}" for g in e.gates if g.state != "pass")[:300],
        "affected": [e.number],
    }


class PrMaintenanceSensor:
    """Class B/C debt from the reconciled pull-request census. Exhaustive over the enabled repositories."""

    id = "pr-maintenance"
    debt_kinds = KINDS
    routine_ids = (19,)
    resolution_scope = "exhaustive"
    driver_inputs = (CENSUS_INPUT.as_posix(),)

    @staticmethod
    def observationFor(e: Evaluation, observedAt: str, provenance: dict[str, Any]) -> Observation:
        if e.kind == "routine_pr_merge_ready":
            return _observation("routine_pr_merge_ready", e, observedAt, provenance)
        if e.kind == "routine_pr_blocked":
            return _observation("routine_pr_blocked", e, observedAt, provenance)
        if e.kind == "routine_pr_superseded":
            return _observation("routine_pr_superseded", e, observedAt, provenance)
        if e.kind == "routine_pr_conflict":
            return _observation("routine_pr_conflict", e, observedAt, provenance)
        if e.kind == "routine_pr_verification_failed":
            return _observation("routine_pr_verification_failed", e, observedAt, provenance)
        if e.kind == "routine_pr_provenance_unknown":
            return _observation("routine_pr_provenance_unknown", e, observedAt, provenance)
        if e.kind == "routine_pr_closure_ready":
            return _observation("routine_pr_closure_ready", e, observedAt, provenance)
        if e.kind == "routine_pr_founder_decision":
            return _observation("routine_pr_founder_decision", e, observedAt, provenance)
        raise ValueError(f"unregistered PR-maintenance disposition {e.kind!r}")

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return list(self.scan_detailed(repo_root, observed_at).observations)

    def scan_detailed(self, repo_root: Path, observed_at: str) -> SensorScan:
        from gaia_cli.steward.policy import PolicyError, StewardPolicy

        root = git_root(repo_root)
        path = root / CENSUS_INPUT
        if not path.exists() and not path.is_symlink():
            raise SensorNotEvaluated(
                f"no {CENSUS_INPUT.name} supplied; a driver must collect the GitHub pull-request census", input_absent=True)
        now = parse_instant(observed_at, "observed_at")
        try:
            policy = StewardPolicy.load(root)
        except PolicyError as exc:
            raise SensorUnavailable(f"steward policy is unreadable for PR maintenance: {exc}") from exc
        if policy.pr_maintenance_error:
            raise SensorUnavailable(f"steward policy is unreadable for PR maintenance: {policy.pr_maintenance_error}")
        try:
            registry = loadRegistry(root)
        except RegistryError as exc:
            raise SensorUnavailable(f"producer registry is unusable: {scrub(str(exc))[:200]}") from exc
        census = loadPrCensus(path, now=now, maxAgeSeconds=policy.pr_maintenance.maxCensusAgeSeconds)
        if not census.status.complete:
            reasons = ", ".join(scrub(reason)[:80] for reason in census.status.reasons[:3]) or "no reason recorded"
            raise SensorUnavailable(f"pull-request census is {census.status.status}: {reasons}")
        document: dict[str, Any] = census.document or {}
        if document.get("repo") not in registry.enabledRepos:
            raise SensorUnavailable(f"census repository {scrub(str(document.get('repo')))[:80]} is not an enabled repository")
        try:
            evaluations = evaluateCensus(root, registry, document)
        except Exception as exc:  # noqa: BLE001 - any evaluation failure is coverage unknown, never a crash
            raise SensorUnavailable(f"pull-request evaluation failed: {type(exc).__name__}") from exc
        provenance = {
            "input": CENSUS_INPUT.as_posix(), "schemaVersion": SCHEMA_VERSION, "censusFetchedAt": document.get("fetchedAt"),
            "repo": document.get("repo"), "openPulls": len(document.get("pulls") or []), "routinePulls": len(evaluations),
            "producerRegistryRevision": registry.revision, "producerRegistrySha256": registry.sha256,
            "deferredRepos": [{"repo": d.repo, "coverage": d.coverage} for d in registry.deferred],
            "organisationWideDiscovery": "deferred",
        }
        observations = [self.observationFor(e, observed_at, provenance) for e in evaluations]
        return SensorScan(observations=tuple(observations))
