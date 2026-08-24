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
from pathlib import Path
from typing import Iterable

from jsonschema import Draft7Validator

DECLARATION_SCHEMA = "gaia.arbor-expert-declaration/v1"
RECEIPT_SCHEMA = "gaia.arbor-benchmark-receipt/v1"
PROFILE_SCHEMA = "gaia.arbor-profile/v1"
SUPPORT_VALUES = {
    "expert-declared",
    "benchmark-confirmed",
    "benchmark-qualified",
    "benchmark-revised",
    "inconclusive",
}

PRESTIGE_KEYS = {
    "level",
    "levels",
    "prestige",
    "rank",
    "ranks",
    "star",
    "stars",
    "tm",
    "trustgrade",
    "trustmagnitude",
}
RECEIPT_CONCLUSION_KEYS = {
    "conclusion",
    "conclusions",
    "support",
    "supportlabel",
    "verdict",
    "verdicts",
}
SCHEMA_FILES = {
    DECLARATION_SCHEMA: "expert-declaration.schema.json",
    RECEIPT_SCHEMA: "benchmark-receipt.schema.json",
    PROFILE_SCHEMA: "profile.schema.json",
}
SOURCE_DIRECTORIES = {
    DECLARATION_SCHEMA: "declarations",
    RECEIPT_SCHEMA: "receipts",
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


def validateRecord(record: dict, registryRoot: str | Path) -> str:
    """Validate one of the three Arbor contracts and return its schema id."""

    schemaId = record.get("schema")
    if schemaId not in SCHEMA_FILES:
        raise ArborError(f"unsupported Arbor schema: {schemaId!r}")
    rejectKeys(record, PRESTIGE_KEYS, "prestige")
    if schemaId == RECEIPT_SCHEMA:
        rejectKeys(record, RECEIPT_CONCLUSION_KEYS, "benchmark conclusion")

    schemaPath = arborRoot(registryRoot) / "contracts" / SCHEMA_FILES[schemaId]
    schema = readJson(schemaPath)
    errors = sorted(Draft7Validator(schema).iter_errors(record), key=lambda item: list(item.path))
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
        for measurement in record["measurements"]:
            interval = measurement["difference"]["confidenceInterval"]
            if interval["lower"] > interval["upper"]:
                raise ArborError(
                    f"benchmark receipt confidence interval is reversed for {measurement['metric']}"
                )
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


def importSource(inputPath: str | Path, registryRoot: str | Path) -> tuple[Path, str, bool]:
    """Validate and atomically publish one immutable declaration or receipt."""

    record = readJson(Path(inputPath))
    schemaId = validateRecord(record, registryRoot)
    if schemaId not in SOURCE_DIRECTORIES:
        raise ArborError("generated Arbor profiles cannot be imported as source records")

    root = arborRoot(registryRoot)
    if schemaId == RECEIPT_SCHEMA:
        validateReceiptTarget(record, root, registryRoot)

    digest = contentDigest(record)
    destination = root / "sources" / SOURCE_DIRECTORIES[schemaId] / f"{digest}.json"
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


def sourceRecords(registryRoot: str | Path) -> tuple[dict[str, dict], dict[str, dict]]:
    root = arborRoot(registryRoot) / "sources"
    declarations = loadSources(root / "declarations", DECLARATION_SCHEMA, registryRoot)
    receipts = loadSources(root / "receipts", RECEIPT_SCHEMA, registryRoot)
    return declarations, receipts


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


def replay(registryRoot: str | Path) -> list[Path]:
    """Recompute every Arbor profile solely from immutable source records."""

    declarations, receipts = sourceRecords(registryRoot)
    for receipt in receipts.values():
        validateReceiptTarget(receipt, arborRoot(registryRoot), registryRoot)

    grouped: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for digest, declaration in declarations.items():
        skill = declaration["skill"]
        key = (skill["id"], skill["contentSha256"])
        grouped.setdefault(key, []).append((digest, declaration))

    written = []
    for (skillId, skillHash), items in sorted(grouped.items()):
        profile = interpretProfile(items, receipts)
        validateRecord(profile, registryRoot)
        path = profilePath(arborRoot(registryRoot), skillId, skillHash)
        writeAtomic(path, json.dumps(profile, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
        written.append(path)
    return written


def interpretProfile(
    declarations: Iterable[tuple[str, dict]], receipts: dict[str, dict]
) -> dict:
    declarationItems = sorted(declarations, key=lambda item: item[0])
    firstSkill = declarationItems[0][1]["skill"]
    claims = []
    seen = set()
    usedReceipts = set()
    for declarationDigest, declaration in declarationItems:
        if declaration["skill"] != firstSkill:
            raise ArborError("cannot combine declarations for different skill identities or hashes")
        for claim in declaration["claims"]:
            if claim["id"] in seen:
                raise ArborError(f"duplicate Arbor claim id for one skill hash: {claim['id']}")
            seen.add(claim["id"])
            targeted = [
                (digest, receipt)
                for digest, receipt in receipts.items()
                if receipt["target"] == {
                    "declarationSha256": declarationDigest,
                    "claimId": claim["id"],
                }
            ]
            outcomes = [interpretReceipt(claim, receipt) for _, receipt in targeted]
            support = combineOutcomes(outcomes)
            receiptDigests = sorted(digest for digest, _ in targeted)
            usedReceipts.update(receiptDigests)
            claims.append(
                {
                    "id": claim["id"],
                    "facet": claim["facet"],
                    "conditions": claim["conditions"],
                    "rationale": claim["rationale"],
                    "authority": claim["authority"],
                    "support": support,
                    "declarationSource": declarationDigest,
                    "benchmarkSources": receiptDigests,
                }
            )

    declarationDigests = [digest for digest, _ in declarationItems]
    sourceDigests = declarationDigests + sorted(usedReceipts)
    return {
        "schema": PROFILE_SCHEMA,
        "skill": firstSkill,
        "inputDigest": hashlib.sha256("\n".join(sourceDigests).encode("ascii")).hexdigest(),
        "sources": {
            "declarations": declarationDigests,
            "benchmarkReceipts": sorted(usedReceipts),
        },
        "claims": sorted(claims, key=lambda item: item["id"]),
    }


def interpretReceipt(claim: dict, receipt: dict) -> str:
    expectation = claim["expectation"]
    observation = next(
        (item for item in receipt["measurements"] if item["metric"] == expectation["metric"]),
        None,
    )
    if observation is None:
        return "inconclusive"
    difference = observation["difference"]
    estimate = difference["estimate"]
    lower = difference["confidenceInterval"]["lower"]
    upper = difference["confidenceInterval"]["upper"]
    minimum = expectation["minimumEffect"]
    if expectation["direction"] == "increase":
        if lower >= minimum:
            return "benchmark-confirmed"
        if estimate >= minimum:
            return "benchmark-qualified"
        if upper < 0:
            return "benchmark-revised"
    else:
        threshold = -minimum
        if upper <= threshold:
            return "benchmark-confirmed"
        if estimate <= threshold:
            return "benchmark-qualified"
        if lower > 0:
            return "benchmark-revised"
    return "inconclusive"


def combineOutcomes(outcomes: list[str]) -> str:
    if not outcomes:
        return "expert-declared"
    distinct = set(outcomes)
    positive = distinct & {"benchmark-confirmed", "benchmark-qualified"}
    if "benchmark-revised" in distinct and positive:
        return "inconclusive"
    if "benchmark-revised" in distinct:
        return "benchmark-revised"
    if "benchmark-confirmed" in distinct:
        return "benchmark-confirmed"
    if "benchmark-qualified" in distinct:
        return "benchmark-qualified"
    return "inconclusive"


def profilePath(root: Path, skillId: str, skillHash: str) -> Path:
    parts = skillId.split("/")
    if not parts or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", part) for part in parts):
        raise ArborError(f"unsafe Arbor skill id: {skillId!r}")
    return root / "profiles" / Path(*parts) / f"{skillHash}.json"


def checkStore(registryRoot: str | Path, inputPath: str | Path | None = None) -> int:
    """Validate one input or the complete store; returns checked file count."""

    if inputPath is not None:
        record = readJson(Path(inputPath))
        schemaId = validateRecord(record, registryRoot)
        if schemaId == RECEIPT_SCHEMA:
            validateReceiptTarget(record, arborRoot(registryRoot), registryRoot)
        return 1

    declarations, receipts = sourceRecords(registryRoot)
    for receipt in receipts.values():
        validateReceiptTarget(receipt, arborRoot(registryRoot), registryRoot)
    expected = {}
    grouped: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for digest, declaration in declarations.items():
        skill = declaration["skill"]
        grouped.setdefault((skill["id"], skill["contentSha256"]), []).append((digest, declaration))
    for (skillId, skillHash), items in grouped.items():
        profile = interpretProfile(items, receipts)
        expected[profilePath(arborRoot(registryRoot), skillId, skillHash)] = profile
    existing = set((arborRoot(registryRoot) / "profiles").glob("**/*.json"))
    if existing != set(expected):
        raise ArborError("generated Arbor profile set is stale; run `gaia dev arbor replay`")
    for path, profile in expected.items():
        stored = readJson(path)
        validateRecord(stored, registryRoot)
        if stored != profile:
            raise ArborError(f"generated Arbor profile is stale: {path}")
    return len(declarations) + len(receipts) + len(expected)
