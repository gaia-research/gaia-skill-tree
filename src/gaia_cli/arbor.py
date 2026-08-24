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
}
SOURCE_DIRECTORIES = {
    DECLARATION_SCHEMA: "declarations",
    RECEIPT_SCHEMA: "receipts",
    INTERPRETATION_SCHEMA: "interpretations",
}


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
        if schemaId == DECLARATION_SCHEMA and not destination.is_file():
            # The moving canonical file is an admission oracle only. Once stored,
            # the declaration digest and pinned hash are immutable history.
            validateSkillIdentity(record["skill"], registryRoot)
        if schemaId == RECEIPT_SCHEMA:
            validateReceiptTarget(record, root, registryRoot)
        if schemaId == INTERPRETATION_SCHEMA:
            validateInterpretationTarget(record, root, registryRoot)

        declarations, receipts, interpretations = sourceRecords(registryRoot)
        if schemaId == DECLARATION_SCHEMA:
            declarations[digest] = record
        elif schemaId == RECEIPT_SCHEMA:
            receipts[digest] = record
        else:
            interpretations[digest] = record
        buildProfiles(declarations, receipts, interpretations, registryRoot)

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
    root = arborRoot(registryRoot) / "sources"
    declarations = loadSources(root / "declarations", DECLARATION_SCHEMA, registryRoot)
    receipts = loadSources(root / "receipts", RECEIPT_SCHEMA, registryRoot)
    interpretations = loadSources(
        root / "interpretations", INTERPRETATION_SCHEMA, registryRoot
    )
    return declarations, receipts, interpretations


def loadSources(directory: Path, expectedSchema: str, registryRoot: str | Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    if not directory.exists():
        return records
    for path in sorted(directory.glob("*.json")):
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


def replay(registryRoot: str | Path) -> list[Path]:
    """Stage, validate, then reconcile every generated profile under one lock."""

    with storeLock(registryRoot):
        declarations, receipts, interpretations = sourceRecords(registryRoot)
        profiles = buildProfiles(declarations, receipts, interpretations, registryRoot)
        staged = {
            path: json.dumps(profile, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
            + b"\n"
            for path, profile in profiles.items()
        }
        profileRoot = arborRoot(registryRoot) / "profiles"
        existing = set(profileRoot.glob("**/*.json")) if profileRoot.exists() else set()
        for path, content in staged.items():
            writeAtomic(path, content)
        for stale in sorted(existing - set(staged)):
            stale.unlink()
        if profileRoot.exists():
            for directory in sorted(
                (path for path in profileRoot.glob("**/*") if path.is_dir()),
                key=lambda path: len(path.parts),
                reverse=True,
            ):
                try:
                    directory.rmdir()
                except OSError:
                    pass
        return list(staged)


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
            if schemaId == DECLARATION_SCHEMA:
                digest = contentDigest(record)
                stored = root / "sources" / "declarations" / f"{digest}.json"
                expectedBytes = canonicalBytes(record) + b"\n"
                if stored.is_file():
                    if stored.read_bytes() != expectedBytes:
                        raise ArborError(f"immutable Arbor source collision at {stored}")
                else:
                    validateSkillIdentity(record["skill"], registryRoot)
            elif schemaId == RECEIPT_SCHEMA:
                validateReceiptTarget(record, root, registryRoot)
            elif schemaId == INTERPRETATION_SCHEMA:
                validateInterpretationTarget(record, root, registryRoot)
            return 1

        declarations, receipts, interpretations = sourceRecords(registryRoot)
        expected = buildProfiles(declarations, receipts, interpretations, registryRoot)
        profileRoot = arborRoot(registryRoot) / "profiles"
        existing = set(profileRoot.glob("**/*.json")) if profileRoot.exists() else set()
        if existing != set(expected):
            raise ArborError("generated Arbor profile set is stale; run `gaia dev arbor replay`")
        for path, profile in expected.items():
            stored = readJson(path)
            validateRecord(stored, registryRoot)
            if stored != profile:
                raise ArborError(f"generated Arbor profile is stale: {path}")
        return len(declarations) + len(receipts) + len(interpretations) + len(expected)
