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
import stat
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
PIN_SCHEMA = "gaia.arbor-pin/v1"
INSTRUCTION_OBSERVATION_SCHEMA = "gaia.arbor-instruction-observation/v1"
IDENTITY_VERSION = "gaia.arbor-behavioral-identity/v1"

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
    PIN_SCHEMA: "pin.schema.json",
    INSTRUCTION_OBSERVATION_SCHEMA: "instruction-observation.schema.json",
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


def repositoryRoot(registryRoot: str | Path) -> Path:
    """Anchor all managed Arbor paths at the caller's physical repository root."""

    try:
        return Path(registryRoot).expanduser().resolve(strict=False)
    except OSError as exc:
        raise ArborError(f"cannot resolve Arbor repository root {registryRoot}: {exc}") from exc


def _checkedPath(anchor: Path, parts: tuple[str | Path, ...]) -> Path:
    anchor = Path(anchor)
    candidate = anchor.joinpath(*parts)
    try:
        candidate.relative_to(anchor)
    except ValueError as exc:
        raise ArborError(f"Arbor managed path escapes repository root: {candidate}") from exc

    current = anchor
    for part in candidate.relative_to(anchor).parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            break
        except OSError as exc:
            raise ArborError(f"cannot inspect Arbor managed path {current}: {exc}") from exc
        if stat.S_ISLNK(mode):
            raise ArborError(f"Arbor managed path cannot contain a symlink: {current}")
        if current != candidate and not stat.S_ISDIR(mode):
            raise ArborError(f"Arbor managed parent is not a directory: {current}")

    try:
        physical = candidate.resolve(strict=False)
        physical.relative_to(anchor)
    except (OSError, ValueError) as exc:
        raise ArborError(f"Arbor managed path escapes repository root: {candidate}") from exc
    return candidate


def managedPath(registryRoot: str | Path, *parts: str | Path) -> Path:
    """Return a path confined to the canonical repository root.

    The input record path is intentionally not passed through this helper: users
    may import a JSON file from outside the repository. Only Arbor-owned
    destinations and readers are confined.
    """

    return _checkedPath(repositoryRoot(registryRoot), tuple(parts))


def managedChild(root: Path, *parts: str | Path) -> Path:
    """Validate a child of an already anchored managed directory."""

    return _checkedPath(Path(root), tuple(parts))


def assertManagedTree(root: Path) -> None:
    """Reject symlinked managed roots/leaves before any recursive operation."""

    root = Path(root)
    if root.is_symlink():
        raise ArborError(f"Arbor managed path cannot be a symlink: {root}")
    if not root.exists():
        return
    if not root.is_dir():
        raise ArborError(f"Arbor managed path is not a directory: {root}")
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            entries = list(os.scandir(current))
        except OSError as exc:
            raise ArborError(f"cannot inspect Arbor managed directory {current}: {exc}") from exc
        for entry in entries:
            entryPath = Path(entry.path)
            try:
                mode = entry.stat(follow_symlinks=False).st_mode
            except OSError as exc:
                raise ArborError(f"cannot inspect Arbor managed path {entryPath}: {exc}") from exc
            if stat.S_ISLNK(mode):
                raise ArborError(f"Arbor managed path cannot contain a symlink: {entryPath}")
            if stat.S_ISDIR(mode):
                pending.append(entryPath)


def managedFiles(root: Path) -> set[Path]:
    assertManagedTree(root)
    if not root.exists():
        return set()
    return {
        path
        for path in root.rglob("*")
        if path.is_file()
    }


def readJson(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArborError(f"cannot read JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArborError(f"Arbor record must be a JSON object: {path}")
    return value


def arborRoot(registryRoot: str | Path) -> Path:
    return managedPath(registryRoot, "registry", "arbor")


def canonicalSkillPath(skillId: str, registryRoot: str | Path) -> Path:
    """Resolve the one canonical source file whose exact bytes identify a skill."""

    if not isinstance(skillId, str) or not SKILL_ID_PATTERN.fullmatch(skillId):
        raise ArborError(f"unsafe Arbor skill id: {skillId!r}")
    registry = managedPath(registryRoot, "registry")
    if "/" in skillId:
        contributor, slug = skillId.split("/")
        candidates = [
            managedChild(registry, "named", contributor, f"{slug}.md")
        ]
    else:
        candidates = [
            managedChild(registry, "nodes", nodeType, f"{skillId}.json")
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

    schemaPath = managedChild(
        arborRoot(registryRoot), "contracts", SCHEMA_FILES[schemaId]
    )
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
    assertManagedTree(root)
    lock = managedChild(root, ".store-lock")
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
        destination = managedChild(
            root,
            "sources",
            SOURCE_DIRECTORIES[schemaId],
            f"{digest}.json",
        )
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

        if not destination.is_file():
            # Admission verified these bytes as current, so their pin is exact.
            for subject in admittedSubjects(schemaId, record):
                publishPin(
                    registryRoot,
                    subject["id"],
                    canonicalSkillPath(subject["id"], registryRoot).read_bytes(),
                )
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
    root = arborRoot(registryRoot)
    sourcesRoot = managedChild(root, "sources")
    assertManagedTree(sourcesRoot)
    return {
        schemaId: loadSources(
            managedChild(sourcesRoot, directory), schemaId, registryRoot
        )
        for schemaId, directory in SOURCE_DIRECTORIES.items()
    }


def addSourceRecord(
    sources: dict[str, dict[str, dict]], schemaId: str, digest: str, record: dict
) -> None:
    sources.setdefault(schemaId, {})[digest] = record


def loadSources(directory: Path, expectedSchema: str, registryRoot: str | Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    assertManagedTree(directory)
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
    declarationPath = sourcePath(root, DECLARATION_SCHEMA, digest)
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
    declarationPath = sourcePath(root, DECLARATION_SCHEMA, declarationDigest)
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
        receiptPath = sourcePath(root, RECEIPT_SCHEMA, receiptDigest)
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
        priorPath = sourcePath(root, INTERPRETATION_SCHEMA, supersedes)
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
    return managedChild(
        root,
        "sources",
        SOURCE_DIRECTORIES[schemaId],
        f"{digest}.json",
    )


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


# --- Behavioural identity, subject pins and instruction observations (#2441) ---
#
# A source record pins ``contentSha256`` of the whole canonical skill file. That
# file also carries prestige and history (evidence, timeline, level, trust), so
# exact-byte matching made Arbor knowledge go dark on every curation edit, while
# a change to upstream instructions behind a mutable link left it applicable.
#
# The pinned hash stays the immutable identity of every source record. What
# changes is how the *projection* decides applicability:
#
# * A pin (``registry/arbor/pins/<id>/<contentSha256>.json``) records, once, the
#   behavioural identity digest of the pinned bytes: the canonical record with
#   prestige/history fields removed. Unknown fields stay in the digest, so a new
#   field fails closed (invalidates) rather than being silently ignored.
# * The current canonical bytes are reduced the same way. Equal digests mean the
#   pinned knowledge still describes this skill; otherwise it is inapplicable.
# * Upstream instruction bytes behind a mutable link are tracked by immutable
#   instruction observations. A drift-check whose bytes differ from the baseline
#   (or that found the upstream unavailable) makes the subject inapplicable.
#
# Because the projection reads only the behavioural digest, a prestige-only edit
# no longer changes any generated Arbor file, and a behavioural edit changes it
# deterministically (and is caught by ``gaia dev arbor check``).

# Fields that describe standing, provenance-of-standing or history. Anything not
# listed here is treated as behavioural, so new or unknown fields fail closed.
NONBEHAVIORAL_NAMED_KEYS = frozenset(
    {
        "apexGateStatus",
        "attribution",
        "catalogRef",
        "createdAt",
        "evidence",
        "level",
        "name",
        "origin",
        "overallTrustGrade",
        "provisional",
        "provisionalUntil",
        "status",
        "tags",
        "timeline",
        "title",
        "trustMagnitude",
        "trustMagnitudeInputHash",
        "updatedAt",
        "verification",
    }
)
NONBEHAVIORAL_NODE_KEYS = frozenset(
    {
        "createdAt",
        "derivatives",
        "evidence",
        "knownAgents",
        "name",
        "status",
        "timeline",
        "title",
        "updatedAt",
        "verification",
    }
)
# Bookkeeping inside a behavioural block (the release identity stays).
NONBEHAVIORAL_UPSTREAM_KEYS = frozenset({"syncedAt"})
GITHUB_BLOB_PATTERN = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/blob/([^/]+)/(.+)$"
)
COMMIT_PATTERN = re.compile(r"^[a-f0-9]{40}$")


def _jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def splitFrontmatter(data: bytes) -> tuple[dict, str] | None:
    """Parse a named-skill markdown record; ``None`` when it has no frontmatter."""

    import yaml

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    try:
        frontmatter = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None
    if not isinstance(frontmatter, dict):
        return None
    closing = text.find("\n", end + 1)
    body = "" if closing < 0 else text[closing + 1:]
    return _jsonable(frontmatter), body


def behavioralView(skillId: str, data: bytes) -> object:
    """Return the behavioural part of one canonical record (fail closed).

    Unparseable bytes are returned whole, so any change to them still counts as
    a behavioural change.
    """

    if "/" in skillId:
        parsed = splitFrontmatter(data)
        if parsed is None:
            return {"raw": hashlib.sha256(data).hexdigest()}
        frontmatter, body = parsed
        kept = {
            key: value
            for key, value in frontmatter.items()
            if key not in NONBEHAVIORAL_NAMED_KEYS
        }
        if isinstance(kept.get("upstream"), dict):
            kept["upstream"] = {
                key: value
                for key, value in kept["upstream"].items()
                if key not in NONBEHAVIORAL_UPSTREAM_KEYS
            }
        return {"frontmatter": kept, "body": body}
    try:
        record = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw": hashlib.sha256(data).hexdigest()}
    if not isinstance(record, dict):
        return {"raw": hashlib.sha256(data).hexdigest()}
    return {
        key: value for key, value in record.items() if key not in NONBEHAVIORAL_NODE_KEYS
    }


def behavioralDigest(skillId: str, data: bytes) -> str:
    return contentDigest([IDENTITY_VERSION, skillId, behavioralView(skillId, data)])


def instructionLink(skillId: str, data: bytes) -> dict:
    """Describe the canonical instruction link (``links.github``) of these bytes."""

    url = None
    if "/" in skillId:
        parsed = splitFrontmatter(data)
        if parsed is not None:
            links = parsed[0].get("links")
            if isinstance(links, dict) and isinstance(links.get("github"), str):
                url = links["github"]
    match = GITHUB_BLOB_PATTERN.fullmatch(url) if url else None
    if match is None:
        # A link that exists but is not a GitHub blob URL (a tree/ link, another
        # host) cannot be observed, so it must not count as "no instructions".
        return {
            "url": url,
            "repository": None,
            "path": None,
            "ref": None,
            "refKind": "unobservable" if url else "none",
        }
    repository, ref, path = match.groups()
    return {
        "url": url,
        "repository": repository,
        "path": path,
        "ref": ref,
        "refKind": "commit" if COMMIT_PATTERN.fullmatch(ref) else "mutable",
    }


def buildPin(skillId: str, data: bytes) -> dict:
    return {
        "schema": PIN_SCHEMA,
        "skill": {"id": skillId, "contentSha256": hashlib.sha256(data).hexdigest()},
        "identity": {
            "version": IDENTITY_VERSION,
            "behavioralSha256": behavioralDigest(skillId, data),
        },
        "instruction": instructionLink(skillId, data),
    }


def pinPath(root: Path, skillId: str, skillHash: str) -> Path:
    if not SKILL_ID_PATTERN.fullmatch(skillId):
        raise ArborError(f"unsafe Arbor skill id: {skillId!r}")
    if not re.fullmatch(r"[a-f0-9]{64}", skillHash):
        raise ArborError(f"invalid Arbor skill hash: {skillHash!r}")
    return managedChild(root, "pins", *Path(*skillId.split("/")).parts, f"{skillHash}.json")


def observationPath(root: Path, record: dict) -> Path:
    skill = record["skill"]
    if not SKILL_ID_PATTERN.fullmatch(skill["id"]):
        raise ArborError(f"unsafe Arbor skill id: {skill['id']!r}")
    return managedChild(
        root,
        "instruction-observations",
        *Path(*skill["id"].split("/")).parts,
        skill["contentSha256"],
        f"{contentDigest(record)}.json",
    )


def currentCanonicalBytes(skillId: str, registryRoot: str | Path) -> bytes | None:
    try:
        return canonicalSkillPath(skillId, registryRoot).read_bytes()
    except ArborError:
        return None


def gitHistoryStatus(registryRoot: str | Path) -> str:
    """Return ``full``, ``shallow`` or ``none`` for the repository holding the store."""

    import subprocess

    repo = repositoryRoot(registryRoot)
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--is-shallow-repository"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not (repo / ".git").exists():
        return "none"
    return "shallow" if result.stdout.strip() == "true" else "full"


def historicalBlob(registryRoot: str | Path, skillId: str, contentSha256: str) -> bytes | None:
    """Find the canonical record bytes hashing to ``contentSha256`` in git history."""

    import subprocess

    repo = repositoryRoot(registryRoot)
    if "/" in skillId:
        contributor, slug = skillId.split("/")
        candidates = [f"registry/named/{contributor}/{slug}.md"]
    else:
        candidates = [f"registry/nodes/{kind}/{skillId}.json" for kind in ("basic", "fusion")]
    for relative in candidates:
        result = subprocess.run(
            ["git", "-C", str(repo), "log", "--all", "--full-history", "--format=%H", "--", relative],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            continue
        seen: set[str] = set()
        for commit in result.stdout.split():
            blob = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", f"{commit}:{relative}"],
                capture_output=True,
                text=True,
            )
            objectId = blob.stdout.strip()
            if blob.returncode != 0 or objectId in seen:
                continue
            seen.add(objectId)
            data = subprocess.run(
                ["git", "-C", str(repo), "cat-file", "blob", objectId], capture_output=True
            ).stdout
            if hashlib.sha256(data).hexdigest() == contentSha256:
                return data
    return None


def loadPins(
    registryRoot: str | Path, requireHistory: bool = False
) -> dict[tuple[str, str], dict]:
    """Load every pin, rejecting misplaced, non-canonical or forged records.

    Every pin is re-derived from the bytes it names: the current canonical
    file when it still hashes to the pin, otherwise the matching blob in git
    history. Without full history an older pin cannot be re-derived; that is
    an error when ``requireHistory`` is set (CI) and is skipped otherwise.
    """

    root = arborRoot(registryRoot)
    directory = managedChild(root, "pins")
    assertManagedTree(directory)
    pins: dict[tuple[str, str], dict] = {}
    history: str | None = None
    if not directory.exists():
        return pins
    for path in sorted(directory.rglob("*.json")):
        if path.is_symlink():
            raise ArborError(f"Arbor pin must not be a symlink: {path}")
        record = readJson(path)
        if validateRecord(record, registryRoot) != PIN_SCHEMA:
            raise ArborError(f"wrong Arbor record type in {path}")
        skill = record["skill"]
        if path != pinPath(root, skill["id"], skill["contentSha256"]):
            raise ArborError(f"Arbor pin is stored at the wrong path: {path}")
        if path.read_bytes() != canonicalBytes(record) + b"\n":
            raise ArborError(f"Arbor pin is not canonically serialized: {path}")
        current = currentCanonicalBytes(skill["id"], registryRoot)
        if current is not None and hashlib.sha256(current).hexdigest() == skill["contentSha256"]:
            pinned = current
        else:
            if history is None:
                history = gitHistoryStatus(registryRoot)
            if history != "full":
                if requireHistory:
                    raise ArborError(
                        f"cannot verify historical Arbor pin {path} without full git history "
                        f"(repository is {history}); fetch full history"
                    )
                pinned = None
            else:
                pinned = historicalBlob(registryRoot, skill["id"], skill["contentSha256"])
                if pinned is None:
                    raise ArborError(
                        f"Arbor pin names bytes that exist neither now nor in git history: {path}"
                    )
        if pinned is not None and buildPin(skill["id"], pinned) != record:
            raise ArborError(f"Arbor pin does not match its pinned canonical bytes: {path}")
        pins[(skill["id"], skill["contentSha256"])] = record
    return pins


def citedInstructions(sources: dict[str, dict[str, dict]]) -> dict[tuple[str, str], set[tuple[str, str]]]:
    """Map each subject to the (commit, sha256) pairs its immutable sources cite.

    Claims cite ``<repository>@<commit>:<path> (sha256 <hex>)`` in
    ``authority.basis``; only a citation of the subject's own pinned path
    counts.
    """

    pattern = re.compile(
        r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([a-f0-9]{40}):(\S+?) \(sha256 ([a-f0-9]{64})"
    )
    cited: dict[tuple[str, str], set[tuple[str, str, str, str]]] = {}
    for schemaId in (DECLARATION_SCHEMA, EDGE_DECLARATION_SCHEMA):
        for record in sources.get(schemaId, {}).values():
            subjects = admittedSubjects(schemaId, record)
            for claim in record["claims"]:
                for match in pattern.finditer(claim["authority"]["basis"]):
                    for subject in subjects:
                        cited.setdefault(
                            (subject["id"], subject["contentSha256"]), set()
                        ).add(match.groups())
    return cited


def loadObservations(
    registryRoot: str | Path,
    pins: dict[tuple[str, str], dict],
    sources: dict[str, dict[str, dict]] | None = None,
) -> dict[tuple[str, str], list[dict]]:
    root = arborRoot(registryRoot)
    directory = managedChild(root, "instruction-observations")
    assertManagedTree(directory)
    grouped: dict[tuple[str, str], list[dict]] = {}
    if not directory.exists():
        return grouped
    cited = citedInstructions(sources if sources is not None else allSourceRecords(registryRoot))
    for path in sorted(directory.rglob("*.json")):
        if path.is_symlink():
            raise ArborError(f"Arbor observation must not be a symlink: {path}")
        record = readJson(path)
        if validateRecord(record, registryRoot) != INSTRUCTION_OBSERVATION_SCHEMA:
            raise ArborError(f"wrong Arbor record type in {path}")
        if path != observationPath(root, record):
            raise ArborError(f"Arbor instruction observation is stored at the wrong path: {path}")
        if path.read_bytes() != canonicalBytes(record) + b"\n":
            raise ArborError(f"Arbor instruction observation is not canonically serialized: {path}")
        validateObservation(record, pins)
        key = (record["skill"]["id"], record["skill"]["contentSha256"])
        if record["purpose"] == "baseline":
            validateBaselineCitation(record, cited.get(key, set()))
        grouped.setdefault(key, []).append(record)
    for key, records in grouped.items():
        baselines = {
            item["observed"]["sha256"]
            for item in records
            if item["purpose"] == "baseline"
        }
        if len(baselines) > 1:
            raise ArborError(f"conflicting Arbor instruction baselines for {key[0]}")
    return grouped


def validateBaselineCitation(record: dict, cited: set[tuple[str, str, str, str]]) -> None:
    """A baseline must be the exact bytes an immutable source says it read."""

    expected = (
        record["instruction"]["repository"],
        record["observed"]["commit"],
        record["instruction"]["path"],
        record["observed"]["sha256"],
    )
    if expected not in cited:
        raise ArborError(
            f"baseline instruction observation for {record['skill']['id']} is not cited by any "
            "of its immutable declarations; a claim's authority.basis must contain "
            "`<owner>/<repo>@<40-hex commit>:<path> (sha256 <64-hex>)` for this exact link and bytes"
        )


def validateObservation(record: dict, pins: dict[tuple[str, str], dict]) -> None:
    skill = record["skill"]
    pin = pins.get((skill["id"], skill["contentSha256"]))
    if pin is None:
        raise ArborError(f"instruction observation names an unpinned subject: {skill['id']}")
    instruction = pin["instruction"]
    if instruction["refKind"] in {"none", "unobservable"}:
        raise ArborError(f"instruction observation for a subject with no observable instruction link: {skill['id']}")
    expected = {
        "repository": instruction["repository"],
        "path": instruction["path"],
        "ref": instruction["ref"],
    }
    if record["instruction"] != expected:
        raise ArborError(
            f"instruction observation does not match the pinned link of {skill['id']}"
        )
    observed = record["observed"]
    available = observed["status"] == "available"
    if available != (observed["sha256"] is not None and observed["commit"] is not None):
        raise ArborError("an available observation needs commit and sha256; an unavailable one has neither")
    if record["purpose"] == "baseline" and not available:
        raise ArborError("a baseline instruction observation must be available")


def identityState(
    registryRoot: str | Path,
    sources: dict[str, dict[str, dict]] | None = None,
    requireHistory: bool = False,
) -> dict:
    pins = loadPins(registryRoot, requireHistory)
    return {
        "pins": pins,
        "observations": loadObservations(registryRoot, pins, sources),
        "current": {},
    }


def subjectApplicability(subject: dict, state: dict, registryRoot: str | Path) -> dict:
    """Decide whether knowledge pinned to ``subject`` applies to the current skill."""

    skillId = subject["id"]
    pin = state["pins"].get((skillId, subject["contentSha256"]))
    if skillId not in state["current"]:
        data = currentCanonicalBytes(skillId, registryRoot)
        state["current"][skillId] = (
            None
            if data is None
            else (hashlib.sha256(data).hexdigest(), behavioralDigest(skillId, data))
        )
    current = state["current"][skillId]
    behavioral = pin["identity"]["behavioralSha256"] if pin else None
    refKind = pin["instruction"]["refKind"] if pin else "none"
    if current is None:
        canonical = "missing"
    elif pin is None:
        # Without a pin only exact bytes can be trusted; check() requires pins.
        canonical = "behavior-equivalent" if current[0] == subject["contentSha256"] else "unpinned"
    else:
        canonical = "behavior-equivalent" if current[1] == behavioral else "behavior-changed"

    observations = state["observations"].get((skillId, subject["contentSha256"]), [])
    baseline = next(
        (item["observed"]["sha256"] for item in observations if item["purpose"] == "baseline"),
        None,
    )
    if refKind == "none":
        instructionStatus = "no-instruction-link"
    elif refKind == "unobservable":
        instructionStatus = "instruction-unobservable"
    elif any(
        item["purpose"] == "drift-check" and item["observed"]["status"] == "unavailable"
        for item in observations
    ):
        instructionStatus = "instruction-unavailable"
    elif baseline is not None and any(
        item["purpose"] == "drift-check" and item["observed"]["sha256"] != baseline
        for item in observations
    ):
        instructionStatus = "instruction-changed"
    elif refKind == "commit":
        instructionStatus = "immutable-ref"
    elif baseline is not None:
        instructionStatus = "baseline-observed"
    else:
        instructionStatus = "mutable-ref-unobserved"
    return {
        # Applicable only when the instructions are known: no link, an immutable
        # commit link, or a mutable link with a verified baseline and no drift.
        "applicable": canonical == "behavior-equivalent"
        and instructionStatus in {"no-instruction-link", "immutable-ref", "baseline-observed"},
        "identityVersion": IDENTITY_VERSION,
        "behavioralSha256": behavioral,
        "canonical": canonical,
        "instruction": {
            "status": instructionStatus,
            "refKind": refKind,
            "baselineSha256": baseline,
        },
    }


def admittedSubjects(schemaId: str, record: dict) -> list[dict]:
    if schemaId == DECLARATION_SCHEMA:
        return [record["skill"]]
    if schemaId == EDGE_DECLARATION_SCHEMA:
        return [record["pair"]["from"], record["pair"]["to"]]
    if schemaId == HH_ACCEPTANCE_SCHEMA:
        return [record["subject"]]
    return []


def sourceSubjects(sources: dict[str, dict[str, dict]]) -> set[tuple[str, str]]:
    subjects: set[tuple[str, str]] = set()
    for schemaId in (DECLARATION_SCHEMA, EDGE_DECLARATION_SCHEMA, HH_ACCEPTANCE_SCHEMA):
        for record in sources.get(schemaId, {}).values():
            for subject in admittedSubjects(schemaId, record):
                subjects.add((subject["id"], subject["contentSha256"]))
    return subjects


def publishPin(registryRoot: str | Path, skillId: str, data: bytes) -> tuple[Path, bool]:
    record = buildPin(skillId, data)
    validateRecord(record, registryRoot)
    path = pinPath(arborRoot(registryRoot), skillId, record["skill"]["contentSha256"])
    return path, publishImmutable(path, canonicalBytes(record) + b"\n")


def gitBlob(registryRoot: str | Path, revision: str, path: Path) -> bytes:
    import subprocess

    repo = repositoryRoot(registryRoot)
    relative = path.relative_to(repo).as_posix()
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{revision}:{relative}"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise ArborError(
            f"cannot read {relative} at {revision}: {result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout


def pinSubject(
    skillId: str,
    registryRoot: str | Path,
    contentSha256: str | None = None,
    fromGit: str | None = None,
) -> tuple[Path, bool]:
    """Publish the pin for current bytes, or for a verified historical blob."""

    with storeLock(registryRoot):
        path = canonicalSkillPath(skillId, registryRoot)
        data = gitBlob(registryRoot, fromGit, path) if fromGit else path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if contentSha256 is not None and actual != contentSha256:
            raise ArborError(
                f"{skillId} bytes{' at ' + fromGit if fromGit else ''} hash to {actual}, not {contentSha256}"
            )
        return publishPin(registryRoot, skillId, data)


def fetchInstruction(repository: str, ref: str, path: str) -> bytes | None:
    """Fetch raw upstream bytes; ``None`` when the upstream says they do not exist."""

    import urllib.error
    import urllib.parse
    import urllib.request

    url = (
        f"https://raw.githubusercontent.com/{repository}/"
        f"{urllib.parse.quote(ref, safe='')}/{urllib.parse.quote(path)}"
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise ArborError(f"upstream fetch failed ({exc.code}) for {url}") from exc
    except urllib.error.URLError as exc:
        raise ArborError(f"upstream fetch failed for {url}: {exc.reason}") from exc


def resolveCommit(repository: str, ref: str) -> str:
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/commits/{ref}",
        headers={"Accept": "application/vnd.github.sha"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            sha = response.read().decode("ascii").strip()
    except (urllib.error.URLError, UnicodeDecodeError) as exc:
        raise ArborError(f"cannot resolve {repository}@{ref} to a commit") from exc
    if not COMMIT_PATTERN.fullmatch(sha):
        raise ArborError(f"cannot resolve {repository}@{ref} to a commit")
    return sha


def utcNow() -> str:
    from datetime import timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def recordObservation(
    registryRoot: str | Path,
    skillId: str,
    contentSha256: str,
    purpose: str,
    commit: str | None,
    fetch=fetchInstruction,
    resolve=resolveCommit,
    expectedSha256: str | None = None,
    observedAt: str | None = None,
    prefetched: tuple[bytes | None] | None = None,
) -> tuple[Path, dict, bool]:
    """Fetch, hash and immutably record one instruction observation.

    A baseline names the exact commit a declaration was read from; its bytes
    must hash to ``expectedSha256`` and that (commit, sha256) must be cited by
    one of the subject's immutable declarations. ``prefetched`` lets a drift
    check record exactly the bytes it compared.
    """

    pins = loadPins(registryRoot)
    pin = pins.get((skillId, contentSha256))
    if pin is None:
        raise ArborError(f"no Arbor pin for {skillId} at {contentSha256}; run `gaia dev arbor pin`")
    instruction = pin["instruction"]
    if instruction["refKind"] in {"none", "unobservable"}:
        raise ArborError(f"{skillId} has no GitHub blob instruction link to observe")
    if purpose == "baseline" and not (commit and COMMIT_PATTERN.fullmatch(commit)):
        raise ArborError("a baseline observation needs the exact 40-hex commit the declarations were read from")
    if purpose == "baseline" and not expectedSha256:
        raise ArborError("a baseline observation needs --expect-sha256 (the sha256 the claim cites)")
    target = commit or instruction["ref"]
    data = prefetched[0] if prefetched is not None else fetch(
        instruction["repository"], target, instruction["path"]
    )
    if data is None:
        if purpose == "baseline":
            raise ArborError(f"baseline instruction bytes are unavailable for {skillId} at {target}")
        observed = {"status": "unavailable", "commit": None, "sha256": None}
    else:
        digest = hashlib.sha256(data).hexdigest()
        if expectedSha256 is not None and digest != expectedSha256:
            raise ArborError(
                f"{skillId} instruction bytes at {target} hash to {digest}, not the cited {expectedSha256}"
            )
        resolved = commit if commit and COMMIT_PATTERN.fullmatch(commit) else resolve(
            instruction["repository"], target
        )
        observed = {"status": "available", "commit": resolved, "sha256": digest}
    record = {
        "schema": INSTRUCTION_OBSERVATION_SCHEMA,
        "skill": {"id": skillId, "contentSha256": contentSha256},
        "purpose": purpose,
        "instruction": {
            "repository": instruction["repository"],
            "path": instruction["path"],
            "ref": instruction["ref"],
        },
        "observed": {**observed, "observedAt": observedAt or utcNow(), "method": "raw-fetch-sha256"},
    }
    validateRecord(record, registryRoot)
    validateObservation(record, pins)
    if purpose == "baseline":
        cited = citedInstructions(allSourceRecords(registryRoot))
        validateBaselineCitation(record, cited.get((skillId, contentSha256), set()))
    with storeLock(registryRoot):
        path = observationPath(arborRoot(registryRoot), record)
        created = publishImmutable(path, canonicalBytes(record) + b"\n")
    return path, record, created


def upstreamCheck(
    registryRoot: str | Path,
    record: bool = False,
    fetch=fetchInstruction,
    resolve=resolveCommit,
) -> list[dict]:
    """Compare each observed baseline with what its mutable link serves now.

    Each subject is fetched once. Status is ``unchanged``, ``changed``,
    ``unavailable`` (the upstream says the file does not exist) or ``error``
    (the fetch itself failed; nothing is concluded or recorded). Report-only
    unless ``record``: then a changed or unavailable result is written as an
    immutable drift-check observation, unless an identical drift result is
    already recorded. Unchanged results write nothing.
    """

    state = identityState(registryRoot)
    report = []
    for key, observations in sorted(state["observations"].items()):
        baseline = next(
            (item for item in observations if item["purpose"] == "baseline"), None
        )
        pin = state["pins"][key]
        if baseline is None or pin["instruction"]["refKind"] != "mutable":
            continue
        instruction = pin["instruction"]
        entry = {"skill": key[0], "contentSha256": key[1]}
        try:
            data = fetch(instruction["repository"], instruction["ref"], instruction["path"])
        except ArborError as exc:
            report.append({**entry, "status": "error", "sha256": None, "error": str(exc)})
            continue
        digest = None if data is None else hashlib.sha256(data).hexdigest()
        status = (
            "unavailable"
            if data is None
            else "unchanged" if digest == baseline["observed"]["sha256"] else "changed"
        )
        entry.update({"status": status, "sha256": digest})
        already = any(
            item["purpose"] == "drift-check" and item["observed"]["sha256"] == digest
            for item in observations
        )
        if record and status in {"changed", "unavailable"} and not already:
            try:
                path, _record, _created = recordObservation(
                    registryRoot, key[0], key[1], "drift-check", None,
                    fetch=fetch, resolve=resolve, prefetched=(data,),
                )
            except ArborError as exc:
                entry.update({"status": "error", "error": str(exc)})
            else:
                entry["recorded"] = str(path)
        report.append(entry)
    return report

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
    sources: dict[str, dict[str, dict]],
    registryRoot: str | Path,
    state: dict | None = None,
) -> list[dict]:
    """Project governed edge claims without reading structural registry relations."""

    validateSourceSet(sources, registryRoot)
    state = state if state is not None else identityState(registryRoot, sources)
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
                    subjectApplicability(endpoint, state, registryRoot)["applicable"]
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
    state: dict | None = None,
) -> dict:
    sources = sources or allSourceRecords(registryRoot)
    entries = buildEdgeEntries(sources, registryRoot, state)
    # Coverage describes observed pairs, not the number of authored claims.
    pairs = {
        pairKey(observation["pair"])
        for observation in sources[EDGE_OBSERVATION_SCHEMA].values()
    }
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
        managedChild(
            arborRoot(registryRoot), "contracts", SCHEMA_FILES[EDGE_INDEX_SCHEMA]
        )
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
    return managedChild(
        root, "runtime", *Path(*skillId.split("/")).parts, f"{skillHash}.json"
    )


def buildRuntime(
    registryRoot: str | Path,
    sources: dict[str, dict[str, dict]] | None = None,
    state: dict | None = None,
) -> dict[Path, dict]:
    """Build one aggregate per pinned subject, with HH deliberately absent."""

    sources = sources or allSourceRecords(registryRoot)
    state = state if state is not None else identityState(registryRoot, sources)
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
    edgeEntries = buildEdgeEntries(sources, registryRoot, state)
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
        applicability = subjectApplicability(subject, state, registryRoot)
        subjectMatches = applicability["applicable"]
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
            "applicability": applicability,
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
    state = identityState(registryRoot, sources)
    return (
        buildEdgeIndex(registryRoot, sources, state),
        buildRuntime(registryRoot, sources, state),
    )


def buildArborProjection(registryRoot: str | Path) -> dict[str, dict]:
    """Return the deterministic Class S files owned by the Arbor publisher."""

    edgeIndex, runtimes = buildArborArtifacts(registryRoot)
    runtimeRecords = {
        str(path.relative_to(managedChild(arborRoot(registryRoot), "runtime"))): runtime
        for path, runtime in runtimes.items()
    }
    # Consumers join on skill id and read ``applicable``; they never need to
    # recompute the exact pinned hash of the current canonical file.
    subjects = [
        {
            **runtime["subject"],
            "applicable": runtime["applicability"]["applicable"],
            "behavioralSha256": runtime["applicability"]["behavioralSha256"],
        }
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
    """Reconcile one owned tree after rejecting all symlinked descendants."""

    root = Path(root)
    assertManagedTree(root)
    existing = managedFiles(root)
    safeStaged: dict[Path, bytes] = {}
    for path, content in staged.items():
        try:
            relative = Path(path).relative_to(root)
        except ValueError as exc:
            raise ArborError(f"generated Arbor path escapes its owner: {path}") from exc
        safePath = managedChild(root, *relative.parts)
        safeStaged[safePath] = content
        writeAtomic(safePath, content)
    for stale in sorted(existing - set(safeStaged)):
        stale.unlink()
    if root.exists():
        for directory in sorted(
            (path for path in root.rglob("*") if path.is_dir()),
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
        profileRoot = managedChild(arborRoot(registryRoot), "profiles")
        reconcileGenerated(
            profileRoot,
            {path: serializeRecord(profile) for path, profile in profiles.items()},
        )
        reconcileGenerated(
            managedChild(arborRoot(registryRoot), "runtime"),
            {path: serializeRecord(runtime) for path, runtime in runtimes.items()},
        )
        writeAtomic(
            managedChild(arborRoot(registryRoot), "edges.json"),
            serializeRecord(edgeIndex),
        )
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
    return managedChild(
        root, "profiles", *Path(*skillId.split("/")).parts, f"{skillHash}.json"
    )


def checkStore(
    registryRoot: str | Path,
    inputPath: str | Path | None = None,
    requireHistory: bool = False,
) -> int:
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
        state = identityState(registryRoot, sources, requireHistory)
        missingPins = sorted(sourceSubjects(sources) - set(state["pins"]))
        if missingPins:
            names = ", ".join(f"{skillId}@{skillHash[:12]}" for skillId, skillHash in missingPins)
            raise ArborError(
                f"Arbor subjects have no pin: {names}; run `gaia dev arbor pin`"
            )
        expectedProfiles = buildProfiles(
            sources[DECLARATION_SCHEMA],
            sources[RECEIPT_SCHEMA],
            sources[INTERPRETATION_SCHEMA],
            registryRoot,
        )
        expectedEdges, expectedRuntimes = buildArborArtifacts(registryRoot, sources)
        profileRoot = managedChild(arborRoot(registryRoot), "profiles")
        existing = managedFiles(profileRoot)
        if existing != set(expectedProfiles):
            raise ArborError("generated Arbor profile set is stale; run `gaia dev arbor replay`")
        for path, profile in expectedProfiles.items():
            stored = readJson(path)
            if stored != profile:
                raise ArborError(f"generated Arbor profile is stale: {path}")
            validateRecord(stored, registryRoot)

        edgePath = managedChild(arborRoot(registryRoot), "edges.json")
        runtimeRoot = managedChild(arborRoot(registryRoot), "runtime")
        generatedExists = edgePath.exists() or runtimeRoot.exists()
        if generatedExists or any(sources.values()):
            if not edgePath.is_file() or readJson(edgePath) != expectedEdges:
                raise ArborError("generated Arbor edge index is stale; run `gaia dev arbor replay`")
            runtimeExisting = managedFiles(runtimeRoot)
            if runtimeExisting != set(expectedRuntimes):
                raise ArborError("generated Arbor runtime set is stale; run `gaia dev arbor replay`")
            for path, runtime in expectedRuntimes.items():
                stored = readJson(path)
                if stored != runtime:
                    raise ArborError(f"generated Arbor runtime is stale: {path}")
                validateRecord(stored, registryRoot)
        return (
            sum(len(records) for records in sources.values())
            + len(expectedProfiles)
        )
