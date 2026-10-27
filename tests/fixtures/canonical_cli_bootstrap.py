"""TEST-ONLY interpreter bootstrap. Not a production issuer or CLI option.

Runs the real native CLI in an isolated subprocess after replacing trusted Python
resolver seams. A separately authored fixture grant binds the entire plan. Schema
extensions below are synthetic test contracts, NOT adoption of held schemas.
"""
import contextlib
import json
import os
import sys
from pathlib import Path

from gaia_cli import canonicalTransaction as tx
from gaia_cli import canonicalWorkflow as workflow

mode, grantPath = sys.argv[1:3]
sys.argv = [sys.argv[0]] + sys.argv[3:]
grant = json.loads(Path(grantPath).read_bytes())
root = Path(grant["root"])
if not (root / "DISPOSABLE_CANONICAL_FIXTURE").is_file():
    raise RuntimeError("fixture bootstrap requires an explicitly disposable fixture repository")
originalSchemas = workflow.schemaPolicy


def fixtureSchemas(selected):
    assert selected == root
    schemas = originalSchemas(selected)
    for schema in schemas.values():
        timeline = schema["definitions"]["timelineEvent"]
        timeline["properties"]["action"]["enum"] += [s.replace("-", "_") for s in workflow.OPERATIONS]
        timeline["properties"].update(decisionRef={"type": "string"}, eventId={"type": "string"})
    evidence = schemas["namedSkill.schema.json"]["definitions"]["evidenceEntry"]
    evidence["properties"].update({key: {} for key in (
        "evidenceId", "revision", "assertionState", "supersedes", "decisionRef", "decisionHistory",
        "reviewedOldDigest", "reviewedNewDigest", "metricMethod", "observationState", "lastObservedAt",
        "contentDigest", "sourceRevision", "measurementScope")})
    return schemas


class FixtureIssuer:
    def __init__(self, plan, operation):
        self.plan, self.operation = plan, operation

    def verify(self, request):
        expected = workflow.transactionPlan(self.plan)
        return (self.plan["planDigest"] == grant.get("planDigest")
                and self.plan["context"] == grant.get("context")
                and self.plan["request"] == grant.get("request")
                and self.operation in grant.get("operations", [])
                and request.operation == self.operation
                and request.root == str(root)
                and request.plan_digest == expected.digest
                and request.context_digest == tx._context(expected, self.operation))


workflow.schemaPolicy = fixtureSchemas
if mode != "schema-only":
    def fixtureResolver(selected, plan, operation):
        assert selected == root
        return FixtureIssuer(plan, operation)
    workflow.resolveApproval = fixtureResolver
if mode in {"interrupt", "interrupt-rollback"}:
    originalAtomic = tx._atomic
    def interruptCanonical(path, data, permissions):
        originalAtomic(path, data, permissions)
        if path.is_relative_to(root / "registry/named"):
            os._exit(73 if mode == "interrupt" else 74)  # real abrupt fixture-process death
    tx._atomic = interruptCanonical

if mode == "observe-lock":
    originalLock = tx._lock
    @contextlib.contextmanager
    def observedLock(selected):
        (root / "writer-lock-attempt").touch()
        with originalLock(selected) as state:
            yield state
    tx._lock = observedLock

from gaia_cli.main import main
sys.exit(main() or 0)
