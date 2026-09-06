"""Declaration-first Arbor sidecar contracts, storage, and interpretation.

Canonical skill records are never edited here. Authored declarations and observed
benchmark receipts are canonicalized, digest-addressed, and published immutably;
Arbor profiles are reproducible interpretations of those source records.
"""

from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable

from jsonschema import Draft7Validator, FormatChecker

DECLARATION_SCHEMA = "gaia.arbor-expert-declaration/v1"
RECEIPT_SCHEMA = "gaia.arbor-benchmark-receipt/v1"
INTERPRETATION_SCHEMA = "gaia.arbor-interpretation/v1"
PROFILE_SCHEMA = "gaia.arbor-profile/v1"
EDGE_DECLARATION_SCHEMA = "gaia.arbor-edge-declaration/v1"
EDGE_OBSERVATION_SCHEMA = "gaia.arbor-edge-observation/v1"
EDGE_INTERPRETATION_SCHEMA = "gaia.arbor-edge-interpretation/v1"
EDGE_SCHEMA = "gaia.arbor-edge/v1"
EDGE_INDEX_SCHEMA = "gaia.arbor-edge-index/v1"
HH_OBSERVATION_REF_SCHEMA = "gaia.hh-observation-ref/v1"
HH_ACCEPTANCE_SCHEMA = "gaia.hh-acceptance/v1"
RUNTIME_SCHEMA = "gaia.arbor-runtime/v1"
RUNTIME_INDEX_SCHEMA = "gaia.arbor-runtime-index/v1"

PRESTIGE_KEYS = {
    "grade",
    "grades",
    "level",
    "levels",
    "prestige",
    "rank",
    "ranks",
    "star",
    "stars",
    "tm",
    "trust",
    "trustgrade",
    "trustmagnitude",
}
SOURCE_INTERPRETATION_KEYS = {
    "assessment",
    "assessments",
    "conclusion",
    "conclusions",
    "decision",
    "decisions",
    "finding",
    "findings",
    "interpretation",
    "interpretations",
    "outcome",
    "outcomes",
    "recommendation",
    "recommendations",
    "result",
    "results",
    "support",
    "supportlabel",
    "verdict",
    "verdicts",
}
# Structural Yggdrasil relations are never an Arbor observation or claim.
STRUCTURAL_KEYS = {
    "prerequisite",
    "prerequisites",
    "prereqs",
    "fusion",
    "suitecomponents",
}
SKILL_ID_PART = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
SKILL_ID_PATTERN = re.compile(rf"^{SKILL_ID_PART}(?:/{SKILL_ID_PART})?$")
DATE_TIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time", raises=(TypeError, ValueError))
def isDateTime(value: object) -> bool:
    """Check RFC 3339 date-times even when jsonschema's optional extra is absent."""

    return isinstance(value, str) and bool(DATE_TIME_PATTERN.fullmatch(value)) and bool(
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    )


SCHEMA_FILES = {
    DECLARATION_SCHEMA: "expert-declaration.schema.json",
    RECEIPT_SCHEMA: "benchmark-receipt.schema.json",
    INTERPRETATION_SCHEMA: "interpretation.schema.json",
    PROFILE_SCHEMA: "profile.schema.json",
    EDGE_DECLARATION_SCHEMA: "edge-declaration.schema.json",
    EDGE_OBSERVATION_SCHEMA: "edge-observation.schema.json",
    EDGE_INTERPRETATION_SCHEMA: "edge-interpretation.schema.json",
    EDGE_SCHEMA: "edge.schema.json",
    EDGE_INDEX_SCHEMA: "edge-index.schema.json",
    HH_OBSERVATION_REF_SCHEMA: "hh-observation-ref.schema.json",
    HH_ACCEPTANCE_SCHEMA: "hh-acceptance.schema.json",
    RUNTIME_SCHEMA: "runtime.schema.json",
}
SOURCE_DIRECTORIES = {
    DECLARATION_SCHEMA: "declarations",
    RECEIPT_SCHEMA: "receipts",
    INTERPRETATION_SCHEMA: "interpretations",
    EDGE_DECLARATION_SCHEMA: "edge-declarations",
    EDGE_OBSERVATION_SCHEMA: "edge-observations",
    EDGE_INTERPRETATION_SCHEMA: "edge-interpretations",
    HH_OBSERVATION_REF_SCHEMA: "hh-observation-refs",
    HH_ACCEPTANCE_SCHEMA: "hh-acceptances",
}
EDGE_SOURCE_SCHEMAS = {
    EDGE_DECLARATION_SCHEMA,
    EDGE_OBSERVATION_SCHEMA,
    EDGE_INTERPRETATION_SCHEMA,
}
HH_SOURCE_SCHEMAS = {HH_OBSERVATION_REF_SCHEMA, HH_ACCEPTANCE_SCHEMA}
SOURCE_RECORD_SCHEMAS = set(SOURCE_DIRECTORIES)


class ArborError(RuntimeError):
    """Raised when an Arbor record or store violates its contract."""


def canonicalBytes(value: object) -> bytes:
    """Return the stable UTF-8 representation used for every Arbor digest."""

    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def contentDigest(value: object) -> str:
    return hashlib.sha256(canonicalBytes(value)).hexdigest()


def readJson(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArborError(f"cannot read JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArborError(f"Arbor record must be a JSON object: {path}")
    return value


def arborRoot(registryRoot: str | Path) -> Path:
    return Path(registryRoot) / "registry" / "arbor"


def canonicalSkillPath(skillId: str, registryRoot: str | Path) -> Path:
    """Resolve the one canonical source file whose exact bytes identify a skill."""

    if not isinstance(skillId, str) or not SKILL_ID_PATTERN.fullmatch(skillId):
        raise ArborError(f"unsafe Arbor skill id: {skillId!r}")
    registry = Path(registryRoot) / "registry"
    if "/" in skillId:
        contributor, slug = skillId.split("/")
        candidates = [registry / "named" / contributor / f"{slug}.md"]
    else:
        candidates = [
            registry / "nodes" / nodeType / f"{skillId}.json"
            for nodeType in ("basic", "fusion")
        ]
    existing = [path for path in candidates if path.is_file()]
    if not existing:
        raise ArborError(f"canonical skill id does not exist: {skillId}")
    if len(existing) != 1:
        raise ArborError(f"canonical skill id is ambiguous: {skillId}")
    return existing[0]


def validateSkillIdentity(skill: dict, registryRoot: str | Path) -> None:
    path = canonicalSkillPath(skill["id"], registryRoot)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if skill["contentSha256"] != actual:
        raise ArborError(
            f"canonical skill hash mismatch for {skill['id']}: expected {actual} from {path}"
        )


def validateRecord(record: dict, registryRoot: str | Path) -> str:
    """Validate one Arbor contract without consulting moving canonical skill bytes."""

    schemaId = record.get("schema")
    if schemaId not in SCHEMA_FILES:
        raise ArborError(f"unsupported Arbor schema: {schemaId!r}")
    if schemaId in SOURCE_DIRECTORIES:
        rejectKeys(record, PRESTIGE_KEYS, "prestige")
    if schemaId in {DECLARATION_SCHEMA, RECEIPT_SCHEMA}:
        rejectKeys(record, SOURCE_INTERPRETATION_KEYS, "source interpretation")
    # HH observation refs are deliberately conclusion-free. HH acceptance is a
    # governed envelope, so its resultDigest is legitimate and only prestige is
    # rejected. Edge observations receive the same two rejection sets; edge
    # declarations and interpretations carry their governed relation/support.
    if schemaId in {EDGE_OBSERVATION_SCHEMA, HH_OBSERVATION_REF_SCHEMA}:
        rejectKeys(record, SOURCE_INTERPRETATION_KEYS, "source interpretation")
    if schemaId in EDGE_SOURCE_SCHEMAS:
        rejectKeys(record, STRUCTURAL_KEYS, "structural Arbor")

    schemaPath = arborRoot(registryRoot) / "contracts" / SCHEMA_FILES[schemaId]
    schema = readJson(schemaPath)
    validator = Draft7Validator(schema, format_checker=FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(record), key=lambda item: list(item.path))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "$"
            details.append(f"{location}: {error.message}")
        raise ArborError("invalid Arbor record: " + "; ".join(details))
    rejectNonFinite(record)
    if schemaId == DECLARATION_SCHEMA:
        claimIds = [claim["id"] for claim in record["claims"]]
        if len(claimIds) != len(set(claimIds)):
            raise ArborError("expert declaration claim ids must be unique")
    if schemaId == RECEIPT_SCHEMA:
        metrics = [measurement["metric"] for measurement in record["measurements"]]
        if len(metrics) != len(set(metrics)):
            raise ArborError("benchmark receipt measurement metrics must be unique")
        if record["control"]["environment"] != record["treatment"]["environment"]:
            raise ArborError("benchmark receipt control and treatment environments must be equivalent")
    if schemaId == EDGE_OBSERVATION_SCHEMA:
        metrics = [measurement["metric"] for measurement in record["measurements"]]
        if len(metrics) != len(set(metrics)):
            raise ArborError("edge observation measurement metrics must be unique")
        if record["control"]["environment"] != record["treatment"]["environment"]:
            raise ArborError("edge observation control and treatment environments must be equivalent")
    if schemaId == EDGE_DECLARATION_SCHEMA:
        claimIds = [claim["id"] for claim in record["claims"]]
        if len(claimIds) != len(set(claimIds)):
            raise ArborError("edge declaration claim ids must be unique")
        validatePair(record["pair"])
    return schemaId


def rejectNonFinite(value: object, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ArborError(f"non-finite number is forbidden at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            rejectNonFinite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rejectNonFinite(child, f"{path}[{index}]")


def rejectKeys(value: object, forbidden: set[str], label: str, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized in forbidden:
                raise ArborError(f"{label} field is forbidden at {path}.{key}")
            rejectKeys(child, forbidden, label, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rejectKeys(child, forbidden, label, f"{path}[{index}]")


@contextmanager
def storeLock(registryRoot: str | Path):
    """Hold the portable, store-wide Arbor publication lock."""

    root = arborRoot(registryRoot)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".store-lock"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ArborError(f"Arbor store is locked: {lock}") from exc
    try:
        yield
    finally:
        lock.rmdir()


def importSource(inputPath: str | Path, registryRoot: str | Path) -> tuple[Path, str, bool]:
    """Validate, preflight, and atomically publish one immutable source."""

    record = readJson(Path(inputPath))
    with storeLock(registryRoot):
        schemaId = validateRecord(record, registryRoot)
        if schemaId not in SOURCE_DIRECTORIES:
            raise ArborError("generated Arbor profiles cannot be imported as source records")

        root = arborRoot(registryRoot)
        digest = contentDigest(record)
        destination = root / "sources" / SOURCE_DIRECTORIES[schemaId] / f"{digest}.json"
        if not destination.is_file():
            # Moving canonical files are admission oracles only. Once stored,
            # every declaration/edge/acceptance pin is immutable history.
            if schemaId == DECLARATION_SCHEMA:
                validateSkillIdentity(record["skill"], registryRoot)
            elif schemaId == EDGE_DECLARATION_SCHEMA:
                validatePairAdmission(record["pair"], registryRoot)
            elif schemaId == HH_ACCEPTANCE_SCHEMA:
                validateSkillIdentity(record["subject"], registryRoot)

        sources = allSourceRecords(registryRoot)
        addSourceRecord(sources, schemaId, digest, record)
        validateSourceSet(sources, registryRoot)
        buildProfiles(
            sources[DECLARATION_SCHEMA],
            sources[RECEIPT_SCHEMA],
            sources[INTERPRETATION_SCHEMA],
            registryRoot,
        )
        buildEdgeEntries(sources, registryRoot)
        buildRuntime(registryRoot, sources)

        created = publishImmutable(destination, canonicalBytes(record) + b"\n")
        return destination, digest, created


def publishImmutable(path: Path, content: bytes) -> bool:
    """Atomically create a digest-addressed file without permitting replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporaryName = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporaryName)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != content:
                raise ArborError(f"immutable Arbor source collision at {path}")
            return False
        except (AttributeError, NotImplementedError, OSError) as exc:
            if isinstance(exc, OSError) and exc.errno not in {
                errno.EPERM, errno.EOPNOTSUPP, errno.ENOSYS, errno.EXDEV
            }:
                raise
            claim = path.with_name(f".{path.name}.publish-lock")
            try:
                claim.mkdir()
            except FileExistsError as claimExc:
                if path.exists() and path.read_bytes() == content:
                    return False
                raise ArborError(f"immutable Arbor publication is already active at {path}") from claimExc
            try:
                if path.exists():
                    if path.read_bytes() != content:
                        raise ArborError(f"immutable Arbor source collision at {path}")
                    return False
                os.replace(temporary, path)
            finally:
                claim.rmdir()
        return True
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def writeAtomic(path: Path, content: bytes) -> bool:
    """Atomically replace a generated interpretation, skipping identical bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_bytes() == content:
        return False
    descriptor, temporaryName = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporaryName)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return True


def sourceRecords(
    registryRoot: str | Path,
) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    """Return the original three source classes for compatibility."""

    sources = allSourceRecords(registryRoot)
    return (
        sources[DECLARATION_SCHEMA],
        sources[RECEIPT_SCHEMA],
        sources[INTERPRETATION_SCHEMA],
    )


def allSourceRecords(registryRoot: str | Path) -> dict[str, dict[str, dict]]:
    root = arborRoot(registryRoot) / "sources"
    return {
        schemaId: loadSources(
            root / directory, schemaId, registryRoot
        )
        for schemaId, directory in SOURCE_DIRECTORIES.items()
    }


def addSourceRecord(
    sources: dict[str, dict[str, dict]], schemaId: str, digest: str, record: dict
) -> None:
    sources.setdefault(schemaId, {})[digest] = record


def loadSources(directory: Path, expectedSchema: str, registryRoot: str | Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    if not directory.exists():
        return records
    for path in sorted(directory.glob("*.json")):
        if path.is_symlink():
            raise ArborError(f"Arbor source must not be a symlink: {path}")
        record = readJson(path)
        schemaId = validateRecord(record, registryRoot)
        if schemaId != expectedSchema:
            raise ArborError(f"wrong Arbor source type in {path}")
        digest = contentDigest(record)
        if path.stem != digest:
            raise ArborError(f"Arbor source filename does not match its digest: {path}")
        if path.read_bytes() != canonicalBytes(record) + b"\n":
            raise ArborError(f"Arbor source is not canonically serialized: {path}")
        records[digest] = record
    return records


def validateReceiptTarget(receipt: dict, root: Path, registryRoot: str | Path) -> None:
    digest = receipt["target"]["declarationSha256"]
    declarationPath = root / "sources" / "declarations" / f"{digest}.json"
    if not declarationPath.is_file():
        raise ArborError(f"benchmark receipt references missing declaration {digest}")
    declaration = readJson(declarationPath)
    validateRecord(declaration, registryRoot)
    if contentDigest(declaration) != digest:
        raise ArborError(f"benchmark receipt references altered declaration {digest}")
    claim = next(
        (item for item in declaration["claims"] if item["id"] == receipt["target"]["claimId"]),
        None,
    )
    if claim is None:
        raise ArborError("benchmark receipt target claim does not exist in its declaration")
    if receipt["skill"] != declaration["skill"]:
        raise ArborError("benchmark receipt skill identity/hash differs from its declaration")


def validateInterpretationTarget(
    interpretation: dict, root: Path, registryRoot: str | Path
) -> None:
    target = interpretation["target"]
    declarationDigest = target["declarationSha256"]
    declarationPath = root / "sources" / "declarations" / f"{declarationDigest}.json"
    if not declarationPath.is_file():
        raise ArborError(
            f"Arbor interpretation references missing declaration {declarationDigest}"
        )
    declaration = readJson(declarationPath)
    validateRecord(declaration, registryRoot)
    if contentDigest(declaration) != declarationDigest:
        raise ArborError(
            f"Arbor interpretation references altered declaration {declarationDigest}"
        )
    if not any(claim["id"] == target["claimId"] for claim in declaration["claims"]):
        raise ArborError("Arbor interpretation target claim does not exist")
    if interpretation["skill"] != declaration["skill"]:
        raise ArborError("Arbor interpretation skill identity/hash differs from its declaration")

    for receiptDigest in interpretation["receiptSources"]:
        receiptPath = root / "sources" / "receipts" / f"{receiptDigest}.json"
        if not receiptPath.is_file():
            raise ArborError(
                f"Arbor interpretation references missing receipt {receiptDigest}"
            )
        receipt = readJson(receiptPath)
        validateRecord(receipt, registryRoot)
        if contentDigest(receipt) != receiptDigest:
            raise ArborError(
                f"Arbor interpretation references altered receipt {receiptDigest}"
            )
        if receipt["target"] != target:
            raise ArborError("Arbor interpretation receipt targets a different claim")

    supersedes = interpretation.get("supersedesSha256")
    if supersedes is not None:
        priorPath = root / "sources" / "interpretations" / f"{supersedes}.json"
        if not priorPath.is_file():
            raise ArborError(
                f"Arbor interpretation supersedes missing interpretation {supersedes}"
            )
        prior = readJson(priorPath)
        validateRecord(prior, registryRoot)
        if contentDigest(prior) != supersedes:
            raise ArborError(
                f"Arbor interpretation supersedes altered interpretation {supersedes}"
            )
        if prior["target"] != target or prior["skill"] != interpretation["skill"]:
            raise ArborError("Arbor interpretation may only supersede the same claim")


def validatePair(pair: dict) -> None:
    """Validate ordered pair identity without normalizing its direction."""

    if pair["from"] == pair["to"]:
        raise ArborError("Arbor edge pair cannot be a self-edge")


def pairKey(pair: dict) -> str:
    return canonicalBytes(pair).decode("utf-8")


def targetKey(pair: dict, target: dict) -> str:
    return canonicalBytes([pair, target]).decode("utf-8")


def sourcePath(root: Path, schemaId: str, digest: str) -> Path:
    return root / "sources" / SOURCE_DIRECTORIES[schemaId] / f"{digest}.json"


def validatePairAdmission(pair: dict, registryRoot: str | Path) -> None:
    """Admit both pinned endpoints against current canonical bytes exactly once."""

    validatePair(pair)
    validateSkillIdentity(pair["from"], registryRoot)
    validateSkillIdentity(pair["to"], registryRoot)


def activeTips(
    records: dict[str, dict], keyFunction, supersedesField: str
) -> dict[object, tuple[str, dict]]:
    """Return one active source per target, rejecting forks and bad chains."""

    grouped: dict[object, list[tuple[str, dict]]] = {}
    for digest, record in records.items():
        grouped.setdefault(keyFunction(record), []).append((digest, record))
    active: dict[object, tuple[str, dict]] = {}
    for key, items in grouped.items():
        digests = {digest for digest, _ in items}
        superseded: set[str] = set()
        for digest, record in items:
            prior = record.get(supersedesField)
            if prior is None:
                continue
            seen: set[str] = {digest}
            while prior is not None:
                if prior in seen:
                    raise ArborError("Arbor supersession cycle is forbidden")
                seen.add(prior)
                if prior not in digests:
                    raise ArborError(
                        f"{record['schema']} supersedes missing source {prior}"
                    )
                superseded.add(prior)
                priorRecord = records[prior]
                if keyFunction(priorRecord) != key:
                    raise ArborError("supersession may only target the same Arbor record")
                prior = priorRecord.get(supersedesField)
        tips = sorted(digests - superseded)
        if len(tips) > 1:
            raise ArborError("multiple active Arbor interpretations for one target")
        if tips:
            active[key] = (tips[0], records[tips[0]])
    return active


def validateSourceSet(
    sources: dict[str, dict[str, dict]], registryRoot: str | Path
) -> None:
    """Validate cross-record links from immutable in-memory source maps."""

    edgeDeclarations = sources[EDGE_DECLARATION_SCHEMA]
    edgeObservations = sources[EDGE_OBSERVATION_SCHEMA]
    edgeInterpretations = sources[EDGE_INTERPRETATION_SCHEMA]
    hhRefs = sources[HH_OBSERVATION_REF_SCHEMA]
    hhAcceptances = sources[HH_ACCEPTANCE_SCHEMA]

    declarationKeys: dict[str, set[str]] = {}
    for digest, declaration in edgeDeclarations.items():
        validatePair(declaration["pair"])
        key = pairKey(declaration["pair"])
        declarationIds = declarationKeys.setdefault(key, set())
        if declaration["declarationId"] in declarationIds:
            raise ArborError(
                f"duplicate Arbor edge declaration id: {declaration['declarationId']}"
            )
        declarationIds.add(declaration["declarationId"])
        if contentDigest(declaration) != digest:
            raise ArborError("Arbor edge declaration digest does not match its content")

    for digest, observation in edgeObservations.items():
        target = observation["target"]
        declaration = edgeDeclarations.get(target["declarationSha256"])
        if declaration is None:
            raise ArborError(
                f"edge observation references missing declaration {target['declarationSha256']}"
            )
        if observation["pair"] != declaration["pair"]:
            raise ArborError("edge observation pair differs from its declaration")
        if not any(claim["id"] == target["claimId"] for claim in declaration["claims"]):
            raise ArborError("edge observation target claim does not exist")
        if contentDigest(observation) != digest:
            raise ArborError("Arbor edge observation digest does not match its content")

    for digest, interpretation in edgeInterpretations.items():
        target = interpretation["target"]
        declaration = edgeDeclarations.get(target["declarationSha256"])
        if declaration is None:
            raise ArborError(
                f"edge interpretation references missing declaration {target['declarationSha256']}"
            )
        if interpretation["pair"] != declaration["pair"]:
            raise ArborError("edge interpretation pair differs from its declaration")
        if not any(claim["id"] == target["claimId"] for claim in declaration["claims"]):
            raise ArborError("edge interpretation target claim does not exist")
        for observationDigest in interpretation["observationSources"]:
            observation = edgeObservations.get(observationDigest)
            if observation is None:
                raise ArborError(
                    f"edge interpretation references missing observation {observationDigest}"
                )
            if (
                observation["pair"] != interpretation["pair"]
                or observation["target"] != target
            ):
                raise ArborError(
                    "edge interpretation observation has a different pair or target"
                )
        supersedes = interpretation.get("supersedesSha256")
        if supersedes is not None:
            prior = edgeInterpretations.get(supersedes)
            if prior is None:
                raise ArborError(
                    f"edge interpretation supersedes missing interpretation {supersedes}"
                )
            if prior["pair"] != interpretation["pair"] or prior["target"] != target:
                raise ArborError(
                    "edge interpretation may only supersede the same pair and target"
                )
        if contentDigest(interpretation) != digest:
            raise ArborError("Arbor edge interpretation digest does not match its content")

    activeTips(
        edgeInterpretations,
        lambda record: targetKey(record["pair"], record["target"]),
        "supersedesSha256",
    )

    for digest, reference in hhRefs.items():
        if contentDigest(reference) != digest:
            raise ArborError("HH observation reference digest does not match its content")

    for digest, acceptance in hhAcceptances.items():
        for referenceDigest in acceptance["observationRefs"]:
            if referenceDigest not in hhRefs:
                raise ArborError(
                    f"HH acceptance references missing observation {referenceDigest}"
                )
        supersedes = acceptance.get("supersedes")
        if supersedes is not None:
            prior = hhAcceptances.get(supersedes)
            if prior is None:
                raise ArborError(f"HH acceptance supersedes missing acceptance {supersedes}")
            if (
                prior["subject"] != acceptance["subject"]
                or prior["indexId"] != acceptance["indexId"]
            ):
                raise ArborError(
                    "HH acceptance may only supersede the same subject and index"
                )
        if contentDigest(acceptance) != digest:
            raise ArborError("HH acceptance digest does not match its content")

    activeTips(
        hhAcceptances,
        lambda record: (
            record["subject"]["id"],
            record["subject"]["contentSha256"],
            record["indexId"],
        ),
        "supersedes",
    )


def digestSourceSet(digests: Iterable[str]) -> str:
    """Digest a sorted source set, not a presentation-order concatenation."""

    return contentDigest(sorted(set(digests)))


def edgeKey(pair: dict, target: dict, relation: str) -> str:
    """Derive a collision-safe ordered key, including declaration identity.

    The reviewed packet's abbreviated formula omitted declarationSha256. The
    target is part of the identity, so retaining it here prevents two
    declarations with the same claim id from overwriting one another.
    """

    return contentDigest(
        [
            pair["from"]["id"],
            pair["from"]["contentSha256"],
            pair["to"]["id"],
            pair["to"]["contentSha256"],
            relation,
            target["declarationSha256"],
            target["claimId"],
        ]
    )


def currentEndpointMatches(endpoint: dict, registryRoot: str | Path) -> bool:
    try:
        path = canonicalSkillPath(endpoint["id"], registryRoot)
    except ArborError:
        return False
    return hashlib.sha256(path.read_bytes()).hexdigest() == endpoint["contentSha256"]


def buildProfiles(
    declarations: dict[str, dict],
    receipts: dict[str, dict],
    interpretations: dict[str, dict],
    registryRoot: str | Path,
) -> dict[Path, dict]:
    """Build and validate a complete profile generation without publishing it."""

    root = arborRoot(registryRoot)
    for receipt in receipts.values():
        validateReceiptTarget(receipt, root, registryRoot)
    for interpretation in interpretations.values():
        validateInterpretationTarget(interpretation, root, registryRoot)
    grouped: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    declarationIds: dict[tuple[str, str], set[str]] = {}
    for digest, declaration in declarations.items():
        skill = declaration["skill"]
        key = (skill["id"], skill["contentSha256"])
        ids = declarationIds.setdefault(key, set())
        if declaration["declarationId"] in ids:
            raise ArborError(
                f"duplicate Arbor declaration id for one skill hash: {declaration['declarationId']}"
            )
        ids.add(declaration["declarationId"])
        grouped.setdefault(key, []).append((digest, declaration))

    profiles = {}
    for (skillId, skillHash), items in sorted(grouped.items()):
        profile = interpretProfile(items, receipts, interpretations)
        validateRecord(profile, registryRoot)
        profiles[profilePath(root, skillId, skillHash)] = profile
    return profiles


def buildEdgeEntries(
    sources: dict[str, dict[str, dict]], registryRoot: str | Path
) -> list[dict]:
    """Project governed edge claims without reading structural registry relations."""

    validateSourceSet(sources, registryRoot)
    declarations = sources[EDGE_DECLARATION_SCHEMA]
    observations = sources[EDGE_OBSERVATION_SCHEMA]
    interpretations = sources[EDGE_INTERPRETATION_SCHEMA]
    active = activeTips(
        interpretations,
        lambda record: targetKey(record["pair"], record["target"]),
        "supersedesSha256",
    )
    entries: list[dict] = []
    for declarationDigest, declaration in sorted(declarations.items()):
        for claim in declaration["claims"]:
            target = {"declarationSha256": declarationDigest, "claimId": claim["id"]}
            observationSources = sorted(
                digest
                for digest, observation in observations.items()
                if observation["target"] == target
            )
            interpretationDigest, interpretation = active.get(
                targetKey(declaration["pair"], target), (None, None)
            )
            if interpretation is None:
                support = "expert-declared"
                authority = claim["authority"]
                interpretationDigest = None
            else:
                support = interpretation["support"]
                authority = interpretation["authority"]
                observationSources = sorted(interpretation["observationSources"])
            entry = {
                "schema": EDGE_SCHEMA,
                "edgeKey": edgeKey(declaration["pair"], target, claim["relation"]),
                "pair": declaration["pair"],
                "target": target,
                "relation": claim["relation"],
                "conditions": claim["conditions"],
                "authority": authority,
                "support": support,
                "declarationSource": declarationDigest,
                "observationSources": observationSources,
                "interpretationSource": interpretationDigest,
                "structuralOverlap": "not-evaluated",
                "pairApplicable": all(
                    currentEndpointMatches(endpoint, registryRoot)
                    for endpoint in (
                        declaration["pair"]["from"],
                        declaration["pair"]["to"],
                    )
                ),
            }
            validateRecord(entry, registryRoot)
            entries.append(entry)
    return sorted(entries, key=lambda entry: entry["edgeKey"])


def buildEdgeIndex(
    registryRoot: str | Path,
    sources: dict[str, dict[str, dict]] | None = None,
) -> dict:
    sources = sources or allSourceRecords(registryRoot)
    entries = buildEdgeEntries(sources, registryRoot)
    pairs = {pairKey(entry["pair"]) for entry in entries}
    index = {
        "schema": EDGE_INDEX_SCHEMA,
        "edgeSetVersion": EDGE_SCHEMA,
        "coverage": {
            "pairsEvaluated": len(pairs),
            "absenceMeaning": "not-evaluated",
        },
        "edges": entries,
    }
    schema = readJson(
        arborRoot(registryRoot) / "contracts" / SCHEMA_FILES[EDGE_INDEX_SCHEMA]
    )
    errors = sorted(
        Draft7Validator(schema, format_checker=FORMAT_CHECKER).iter_errors(index),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ArborError(f"invalid Arbor edge index: {errors[0].message}")
    return index


def runtimePath(root: Path, skillId: str, skillHash: str) -> Path:
    if not SKILL_ID_PATTERN.fullmatch(skillId):
        raise ArborError(f"unsafe Arbor skill id: {skillId!r}")
    return root / "runtime" / Path(*skillId.split("/")) / f"{skillHash}.json"


def buildRuntime(
    registryRoot: str | Path,
    sources: dict[str, dict[str, dict]] | None = None,
) -> dict[Path, dict]:
    """Build one aggregate per pinned subject, with HH deliberately absent."""

    sources = sources or allSourceRecords(registryRoot)
    validateSourceSet(sources, registryRoot)
    profiles = buildProfiles(
        sources[DECLARATION_SCHEMA],
        sources[RECEIPT_SCHEMA],
        sources[INTERPRETATION_SCHEMA],
        registryRoot,
    )
    profileBySubject = {
        (profile["skill"]["id"], profile["skill"]["contentSha256"]): profile
        for profile in profiles.values()
    }
    edgeEntries = buildEdgeEntries(sources, registryRoot)
    activeAcceptances = activeTips(
        sources[HH_ACCEPTANCE_SCHEMA],
        lambda record: (
            record["subject"]["id"],
            record["subject"]["contentSha256"],
            record["indexId"],
        ),
        "supersedes",
    )

    subjects = set(profileBySubject)
    for entry in edgeEntries:
        subjects.add((entry["pair"]["from"]["id"], entry["pair"]["from"]["contentSha256"]))
        subjects.add((entry["pair"]["to"]["id"], entry["pair"]["to"]["contentSha256"]))
    for acceptance in sources[HH_ACCEPTANCE_SCHEMA].values():
        subject = acceptance["subject"]
        subjects.add((subject["id"], subject["contentSha256"]))

    root = arborRoot(registryRoot)
    runtimes: dict[Path, dict] = {}
    for subjectId, subjectHash in sorted(subjects):
        subject = {"id": subjectId, "contentSha256": subjectHash}
        subjectMatches = currentEndpointMatches(subject, registryRoot)
        profile = profileBySubject.get((subjectId, subjectHash))
        if profile is None:
            claimsLens = {
                "status": "absent-no-accepted-record",
                "sourceDigest": None,
                "profile": None,
            }
        else:
            profileSources = [
                digest
                for digestList in profile["sources"].values()
                for digest in digestList
            ]
            claimsLens = {
                "status": "present",
                "sourceDigest": digestSourceSet(profileSources),
                # The closed profile document is embedded byte-for-byte. A
                # reader still checks the subject pin before using this lens.
                "profile": profile,
            }

        subjectSourceDigests: set[str] = set()
        if profile is not None:
            subjectSourceDigests.update(
                digest
                for digestList in profile["sources"].values()
                for digest in digestList
            )

        acceptanceKey = (subjectId, subjectHash, "hell-heaven")
        acceptanceItem = activeAcceptances.get(acceptanceKey)
        if acceptanceItem is None:
            hhLens = {
                "status": "absent-no-accepted-record",
                "sourceDigest": None,
                "result": None,
            }
        else:
            acceptanceDigest, acceptance = acceptanceItem
            subjectSourceDigests.update(
                [acceptanceDigest, *acceptance["observationRefs"]]
            )
            acceptanceSources = digestSourceSet(
                [acceptanceDigest, *acceptance["observationRefs"]]
            )
            if not subjectMatches:
                hhLens = {
                    "status": "absent-subject-version-mismatch",
                    "sourceDigest": acceptanceSources,
                    "result": None,
                }
            else:
                # The accepted HH result contract is still research-owned. Do
                # not pass through a resultDigest as if it were a known payload.
                hhLens = {
                    "status": "unavailable-unsupported-payload",
                    "sourceDigest": acceptanceSources,
                    "result": None,
                }

        relatedEdges = [
            entry
            for entry in edgeEntries
            if entry["pair"]["from"] == subject or entry["pair"]["to"] == subject
        ]
        ownMatches = subjectMatches
        for edge in relatedEdges:
            subjectSourceDigests.add(edge["declarationSource"])
            subjectSourceDigests.update(edge["observationSources"])
            if edge["interpretationSource"]:
                subjectSourceDigests.add(edge["interpretationSource"])
        if relatedEdges and not ownMatches:
            interactionsLens = {
                "status": "absent-subject-version-mismatch",
                "sourceDigest": digestSourceSet(
                    digest
                    for edge in relatedEdges
                    for digest in (
                        [edge["declarationSource"]]
                        + edge["observationSources"]
                        + ([edge["interpretationSource"]] if edge["interpretationSource"] else [])
                    )
                ),
                "edges": [],
            }
        else:
            interactionEdges = [
                dict(edge)
                for edge in relatedEdges
                if ownMatches
            ]
            interactionsLens = {
                "status": "present" if interactionEdges else "absent-no-accepted-record",
                "sourceDigest": (
                    digestSourceSet(
                        digest
                        for edge in interactionEdges
                        for digest in (
                            [edge["declarationSource"]]
                            + edge["observationSources"]
                            + ([edge["interpretationSource"]] if edge["interpretationSource"] else [])
                        )
                    )
                    if interactionEdges
                    else None
                ),
                "edges": interactionEdges,
            }

        runtime = {
            "schema": RUNTIME_SCHEMA,
            "subject": subject,
            "inputDigest": digestSourceSet(subjectSourceDigests),
            "lenses": {
                "claims": claimsLens,
                "hellHeaven": hhLens,
                "interactions": interactionsLens,
            },
        }
        validateRecord(runtime, registryRoot)
        runtimes[runtimePath(root, subjectId, subjectHash)] = runtime
    return runtimes


def buildArborArtifacts(
    registryRoot: str | Path,
    sources: dict[str, dict[str, dict]] | None = None,
) -> tuple[dict, dict[Path, dict]]:
    sources = sources or allSourceRecords(registryRoot)
    return buildEdgeIndex(registryRoot, sources), buildRuntime(registryRoot, sources)


def buildArborProjection(registryRoot: str | Path) -> dict[str, dict]:
    """Return the deterministic Class S files owned by the Arbor publisher."""

    edgeIndex, runtimes = buildArborArtifacts(registryRoot)
    runtimeRecords = {
        str(path.relative_to(arborRoot(registryRoot) / "runtime")): runtime
        for path, runtime in runtimes.items()
    }
    subjects = [
        runtime["subject"]
        for _path, runtime in sorted(runtimeRecords.items())
    ]
    projection = {
        "edges.json": edgeIndex,
        "runtime/index.json": {
            "schema": RUNTIME_INDEX_SCHEMA,
            "runtimeVersion": RUNTIME_SCHEMA,
            "subjects": subjects,
        },
    }
    projection.update(
        {
            f"runtime/{relativePath}": runtime
            for relativePath, runtime in runtimeRecords.items()
        }
    )
    return projection


def serializeRecord(record: dict) -> bytes:
    return json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def reconcileGenerated(root: Path, staged: dict[Path, bytes]) -> None:
    existing = set(root.glob("**/*.json")) if root.exists() else set()
    for path, content in staged.items():
        writeAtomic(path, content)
    for stale in sorted(existing - set(staged)):
        stale.unlink()
    if root.exists():
        for directory in sorted(
            (path for path in root.glob("**/*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass


def replay(registryRoot: str | Path) -> list[Path]:
    """Stage, validate, then reconcile profiles and runtime projections."""

    with storeLock(registryRoot):
        sources = allSourceRecords(registryRoot)
        profiles = buildProfiles(
            sources[DECLARATION_SCHEMA],
            sources[RECEIPT_SCHEMA],
            sources[INTERPRETATION_SCHEMA],
            registryRoot,
        )
        edgeIndex, runtimes = buildArborArtifacts(registryRoot, sources)
        profileRoot = arborRoot(registryRoot) / "profiles"
        reconcileGenerated(
            profileRoot,
            {path: serializeRecord(profile) for path, profile in profiles.items()},
        )
        reconcileGenerated(
            arborRoot(registryRoot) / "runtime",
            {path: serializeRecord(runtime) for path, runtime in runtimes.items()},
        )
        writeAtomic(arborRoot(registryRoot) / "edges.json", serializeRecord(edgeIndex))
        return list(profiles)


def interpretProfile(
    declarations: Iterable[tuple[str, dict]],
    receipts: dict[str, dict],
    interpretations: dict[str, dict],
) -> dict:
    declarationItems = sorted(declarations, key=lambda item: item[0])
    firstSkill = declarationItems[0][1]["skill"]
    claims = []
    seen = set()
    usedReceipts = set()
    usedInterpretations = set()
    for declarationDigest, declaration in declarationItems:
        if declaration["skill"] != firstSkill:
            raise ArborError("cannot combine declarations for different skill identities or hashes")
        for claim in declaration["claims"]:
            if claim["id"] in seen:
                raise ArborError(f"duplicate Arbor claim id for one skill hash: {claim['id']}")
            seen.add(claim["id"])
            target = {
                "declarationSha256": declarationDigest,
                "claimId": claim["id"],
            }
            receiptDigests = sorted(
                digest for digest, receipt in receipts.items() if receipt["target"] == target
            )
            targetedInterpretations = {
                digest: interpretation
                for digest, interpretation in interpretations.items()
                if interpretation["target"] == target
            }
            superseded = {
                interpretation["supersedesSha256"]
                for interpretation in targetedInterpretations.values()
                if "supersedesSha256" in interpretation
            }
            tips = sorted(set(targetedInterpretations) - superseded)
            if len(tips) > 1:
                raise ArborError(
                    f"multiple active Arbor interpretations for claim {claim['id']}; "
                    "a new interpretation must supersede the active source"
                )
            interpretationDigest = tips[0] if tips else None
            support = (
                targetedInterpretations[interpretationDigest]["support"]
                if interpretationDigest is not None
                else "expert-declared"
            )
            usedReceipts.update(receiptDigests)
            usedInterpretations.update(targetedInterpretations)
            claims.append(
                {
                    "id": claim["id"],
                    "facet": claim["facet"],
                    "conditions": claim["conditions"],
                    "rationale": claim["rationale"],
                    "authority": claim["authority"],
                    "support": support,
                    "declarationId": declaration["declarationId"],
                    "declaredAt": declaration["declaredAt"],
                    "declarationSource": declarationDigest,
                    "benchmarkSources": receiptDigests,
                    "interpretationSource": interpretationDigest,
                }
            )

    declarationDigests = [digest for digest, _ in declarationItems]
    sourceDigests = (
        declarationDigests + sorted(usedReceipts) + sorted(usedInterpretations)
    )
    return {
        "schema": PROFILE_SCHEMA,
        "skill": firstSkill,
        "inputDigest": hashlib.sha256("\n".join(sourceDigests).encode("ascii")).hexdigest(),
        "sources": {
            "declarations": declarationDigests,
            "benchmarkReceipts": sorted(usedReceipts),
            "interpretations": sorted(usedInterpretations),
        },
        "claims": sorted(claims, key=lambda item: item["id"]),
    }


def profilePath(root: Path, skillId: str, skillHash: str) -> Path:
    if not SKILL_ID_PATTERN.fullmatch(skillId):
        raise ArborError(f"unsafe Arbor skill id: {skillId!r}")
    return root / "profiles" / Path(*skillId.split("/")) / f"{skillHash}.json"


def checkStore(registryRoot: str | Path, inputPath: str | Path | None = None) -> int:
    """Validate one input or immutable store integrity; returns checked file count.

    A standalone declaration not already stored also receives the current
    canonical admission check. Receipts validate their immutable target; profiles
    receive contract validation. Stored history never consults moving skill bytes.
    """

    with storeLock(registryRoot):
        if inputPath is not None:
            record = readJson(Path(inputPath))
            schemaId = validateRecord(record, registryRoot)
            root = arborRoot(registryRoot)
            digest = contentDigest(record)
            stored = sourcePath(root, schemaId, digest) if schemaId in SOURCE_DIRECTORIES else None
            expectedBytes = canonicalBytes(record) + b"\n"
            if stored is not None and stored.is_file():
                if stored.read_bytes() != expectedBytes:
                    raise ArborError(f"immutable Arbor source collision at {stored}")
            elif schemaId == DECLARATION_SCHEMA:
                validateSkillIdentity(record["skill"], registryRoot)
            elif schemaId == EDGE_DECLARATION_SCHEMA:
                validatePairAdmission(record["pair"], registryRoot)
            elif schemaId == HH_ACCEPTANCE_SCHEMA:
                validateSkillIdentity(record["subject"], registryRoot)

            sources = allSourceRecords(registryRoot)
            if schemaId in SOURCE_DIRECTORIES:
                addSourceRecord(sources, schemaId, digest, record)
                validateSourceSet(sources, registryRoot)
                buildProfiles(
                    sources[DECLARATION_SCHEMA],
                    sources[RECEIPT_SCHEMA],
                    sources[INTERPRETATION_SCHEMA],
                    registryRoot,
                )
                buildArborArtifacts(registryRoot, sources)
            return 1

        sources = allSourceRecords(registryRoot)
        validateSourceSet(sources, registryRoot)
        expectedProfiles = buildProfiles(
            sources[DECLARATION_SCHEMA],
            sources[RECEIPT_SCHEMA],
            sources[INTERPRETATION_SCHEMA],
            registryRoot,
        )
        expectedEdges, expectedRuntimes = buildArborArtifacts(registryRoot, sources)
        profileRoot = arborRoot(registryRoot) / "profiles"
        existing = set(profileRoot.glob("**/*.json")) if profileRoot.exists() else set()
        if existing != set(expectedProfiles):
            raise ArborError("generated Arbor profile set is stale; run `gaia dev arbor replay`")
        for path, profile in expectedProfiles.items():
            stored = readJson(path)
            validateRecord(stored, registryRoot)
            if stored != profile:
                raise ArborError(f"generated Arbor profile is stale: {path}")

        edgePath = arborRoot(registryRoot) / "edges.json"
        runtimeRoot = arborRoot(registryRoot) / "runtime"
        generatedExists = edgePath.exists() or runtimeRoot.exists()
        if generatedExists or any(sources.values()):
            if not edgePath.is_file() or readJson(edgePath) != expectedEdges:
                raise ArborError("generated Arbor edge index is stale; run `gaia dev arbor replay`")
            runtimeExisting = set(runtimeRoot.glob("**/*.json")) if runtimeRoot.exists() else set()
            if runtimeExisting != set(expectedRuntimes):
                raise ArborError("generated Arbor runtime set is stale; run `gaia dev arbor replay`")
            for path, runtime in expectedRuntimes.items():
                stored = readJson(path)
                validateRecord(stored, registryRoot)
                if stored != runtime:
                    raise ArborError(f"generated Arbor runtime is stale: {path}")
        return (
            sum(len(records) for records in sources.values())
            + len(expectedProfiles)
        )
