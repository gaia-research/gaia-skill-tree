"""Durable evidence custody for ephemeral cloud Steward runs (issue #2448).

Daily Steward maintenance runs on short-lived cloud subagents. A subagent's
`.gaia/steward/` directory is destroyed with its container, so the original scan
receipt, the content-addressed dispatch receipt, the candidate diff and the
`steward-proof-transcript-v1` it produced vanish with it. A later host then has
no envelope to verify against, and `gaia steward verify` correctly refuses.

This module makes those artifacts durable *before* the agent that made them can
disappear, and lets a different clean checkout retrieve and authenticate them.

Design (and why)
----------------
* **A second Git ref, `steward/evidence`, not the hot ledger.** The shared
  `steward/ledger` document is read and rewritten by every run; large diffs and
  proof transcripts would inflate every load. The ledger may *index* a bundle by
  id (the full-run driver does); the bytes live here.
* **Append-only, content-addressed, no force.** Raw bytes sit at
  `objects/<sha256>`; one manifest per bundle sits at
  `bundles/<debt key>/<bundle id>.json`. Writes reuse the ledger's
  fast-forward-only CAS tail (`GitRefLedgerStore.publishTree`), so Git itself
  refuses a stale writer. Nothing is ever overwritten or deleted by this module.
* **Original bytes, original authority.** Receipts are stored and restored
  byte-for-byte. Restoration never re-renders a dispatch from today's policy and
  never writes a receipt that was not issued; a restored dispatch must still
  attest to its own content hash.
* **Write is not done until read-back.** Every publish re-fetches the remote ref
  and re-verifies every object it just wrote. Only then does it report success.
* **Fail closed.** Every failure is a `CustodyError` carrying the actionable
  reason; callers surface `BLOCKED: provenance unavailable`. There is no local
  fallback and no "best effort" success.

Bundle kinds form a chain: `dispatch` -> `build` -> `verdict`. A build bundle
names its parent dispatch bundle, so the verifier is always handed the exact
receipt that authorized the work, never "the latest one for that debt".
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from gaia_cli.steward.ledger import (
    GitRefLedgerStore,
    LedgerConflict,
    LedgerUnavailable,
    validateRef,
)
from gaia_cli.steward.receipts import ensure_local_state_path, run_id_matches


EVIDENCE_REF = "steward/evidence"
BUNDLE_SCHEMA = "steward-evidence-bundle-v1"
HANDOFF_SCHEMA = "steward-evidence-handoff-v1"
BUNDLE_KINDS = ("dispatch", "build", "verdict")
OBJECTS_DIRECTORY = "objects"
BUNDLES_DIRECTORY = "bundles"
ENVIRONMENT_VARIABLE = "GAIA_STEWARD_EVIDENCE"
REF_VARIABLE = "GAIA_STEWARD_EVIDENCE_REF"  # rehearsals and tests only; production uses EVIDENCE_REF
BLOCKED_PREFIX = "BLOCKED: provenance unavailable"

# Safety bounds. A diff or proof beyond these is refused, never truncated.
MAX_OBJECT_BYTES = 8 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
PUBLISH_ATTEMPTS = 6

SHA256 = re.compile(r"^[0-9a-f]{64}$")
FULL_COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class CustodyError(RuntimeError):
    """Evidence could not be persisted, retrieved or authenticated."""

    def blocked(self) -> str:
        return f"{BLOCKED_PREFIX}: {self}"


class CustodyUnavailable(CustodyError):
    """The shared transport failed. Nothing was proven either way."""


class CustodyRefused(CustodyError):
    """The evidence is missing, altered, stale or malformed."""


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def canonicalJson(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256Hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def debtKey(debtId: str) -> str:
    """Path-safe stable key for a debt id (debt ids contain `:` and arbitrary slugs)."""

    return sha256Hex(debtId.encode("utf-8"))[:16]


def objectPath(digest: str) -> str:
    return f"{OBJECTS_DIRECTORY}/{digest}"


def bundlePath(debtId: str, bundleId: str) -> str:
    return f"{BUNDLES_DIRECTORY}/{debtKey(debtId)}/{bundleId}.json"


def nowUtc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def requestedMode(flag: str | None = None, environ: Mapping[str, str] | None = None) -> str | None:
    """Resolve the custody mode: an explicit flag wins over the environment.

    Returns `None` (custody not requested) or `"git"`. Any other value is an
    error rather than a silent downgrade to "off".
    """

    env = os.environ if environ is None else environ
    value = flag if flag is not None else env.get(ENVIRONMENT_VARIABLE)
    if value is None or value in ("", "off"):
        return None
    if value != "git":
        raise CustodyRefused(f"unknown evidence custody mode {value!r}; use 'git' or 'off'")
    return "git"


@dataclass(frozen=True)
class Artifact:
    role: str
    sha256: str
    size: int
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {"sha256": self.sha256, "size": self.size, "name": self.name}


@dataclass(frozen=True)
class Bundle:
    """One verified manifest. `identity` is hashed into `bundleId`; `meta` is not."""

    bundleId: str
    identity: Mapping[str, Any]
    meta: Mapping[str, Any]
    raw: bytes

    @property
    def kind(self) -> str:
        return str(self.identity["kind"])

    @property
    def debtId(self) -> str:
        return str(self.identity["debtId"])

    @property
    def parent(self) -> str | None:
        parent = self.identity.get("parent")
        return str(parent) if parent else None

    @property
    def artifacts(self) -> Mapping[str, Mapping[str, Any]]:
        return self.identity.get("artifacts", {})  # type: ignore[return-value]


@dataclass(frozen=True)
class PublishResult:
    bundleId: str
    kind: str
    commit: str
    published: bool  # False when an identical bundle was already durable (idempotent resume)
    readBack: bool
    objects: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundleId": self.bundleId, "kind": self.kind, "evidenceCommit": self.commit,
            "published": self.published, "readBack": self.readBack, "objects": dict(self.objects),
        }


def makeBundle(identity: Mapping[str, Any], meta: Mapping[str, Any]) -> Bundle:
    body = dict(identity)
    bundleId = sha256Hex(canonicalJson(body))
    document = {
        "schemaVersion": BUNDLE_SCHEMA, "bundleId": bundleId, "identity": body, "meta": dict(meta),
    }
    raw = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    return Bundle(bundleId=bundleId, identity=body, meta=dict(meta), raw=raw)


def parseBundle(raw: bytes, *, expectedId: str | None = None) -> Bundle:
    """Parse a stored manifest and prove its id is the hash of its identity."""

    if len(raw) > MAX_MANIFEST_BYTES:
        raise CustodyRefused("evidence manifest exceeds its safety limit")
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CustodyRefused(f"evidence manifest is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schemaVersion") != BUNDLE_SCHEMA:
        raise CustodyRefused(f"evidence manifest must declare schemaVersion {BUNDLE_SCHEMA}")
    identity = data.get("identity")
    meta = data.get("meta", {})
    bundleId = data.get("bundleId")
    if not isinstance(identity, dict) or not isinstance(meta, dict) or not isinstance(bundleId, str):
        raise CustodyRefused("evidence manifest is malformed")
    if not SHA256.match(bundleId) or sha256Hex(canonicalJson(identity)) != bundleId:
        raise CustodyRefused(
            "evidence manifest no longer matches its own bundle id; it was altered after publication"
        )
    if expectedId is not None and bundleId != expectedId:
        raise CustodyRefused(f"evidence manifest {bundleId} was stored under id {expectedId}")
    if identity.get("kind") not in BUNDLE_KINDS:
        raise CustodyRefused(f"unknown evidence bundle kind {identity.get('kind')!r}")
    if not isinstance(identity.get("debtId"), str) or not identity["debtId"]:
        raise CustodyRefused("evidence manifest names no debt")
    artifacts = identity.get("artifacts")
    if not isinstance(artifacts, dict):
        raise CustodyRefused("evidence manifest lists no artifacts object")
    for role, item in artifacts.items():
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("sha256"), str)
            or not SHA256.match(item["sha256"])
            or isinstance(item.get("size"), bool)
            or not isinstance(item.get("size"), int)
            or not isinstance(item.get("name"), str)
            or "/" in item["name"]
            or item["name"] in ("", ".", "..")
        ):
            raise CustodyRefused(f"evidence artifact {role!r} is malformed")
    return Bundle(bundleId=bundleId, identity=identity, meta=meta, raw=raw)


# ---------------------------------------------------------------------------
# Transport: a Git ref carrying a tree of immutable files
# ---------------------------------------------------------------------------


class GitEvidenceStore(GitRefLedgerStore):
    """`steward/evidence` on a git remote. Append-only; CAS by fast-forward push."""

    transport = "git-ref-evidence"
    shared = True

    def __init__(self, repoRoot: Path | str, remote: str = "origin", ref: str = EVIDENCE_REF, **kwargs: Any) -> None:
        super().__init__(repoRoot, remote, ref, **kwargs)
        # The ledger ref and the evidence ref must never alias each other.
        if validateRef(ref) == "steward/ledger":
            raise CustodyRefused("the evidence ref must not be the ledger ref")

    # -- reads ---------------------------------------------------------------

    def snapshot(self) -> str | None:
        """Fetch the remote tip afresh. `None` means the ref does not exist yet."""

        try:
            return self.fetchRemote()
        except LedgerUnavailable as exc:
            raise CustodyUnavailable(f"evidence ref could not be fetched: {exc}") from exc

    def readFile(self, commit: str, path: str, *, limit: int) -> bytes | None:
        spec = f"{commit}:{path}"
        probe = self.git(["cat-file", "-e", spec], timeout=self.localTimeout)
        if probe.returncode != 0:
            return None
        try:
            size = int(self.plumb(["cat-file", "-s", spec]))
        except (ValueError, LedgerUnavailable) as exc:
            raise CustodyUnavailable(f"could not size {path}: {exc}") from exc
        if size > limit:
            raise CustodyRefused(f"{path} is {size} bytes, over the {limit} byte bound")
        result = self.git(["cat-file", "-p", spec], timeout=self.localTimeout)
        if result.returncode != 0:
            raise CustodyUnavailable(f"could not read {path}: {self.outputText(result).strip()[:300]}")
        return bytes(result.stdout)

    def listBundleIds(self, commit: str | None, debtId: str) -> list[str]:
        if commit is None:
            return []
        prefix = f"{BUNDLES_DIRECTORY}/{debtKey(debtId)}"
        result = self.git(["ls-tree", "--name-only", f"{commit}:{prefix}"], timeout=self.localTimeout)
        if result.returncode != 0:
            return []  # no directory means no bundles for this debt
        names = result.stdout.decode("utf-8", "replace").split()
        return sorted(name[:-5] for name in names if name.endswith(".json") and SHA256.match(name[:-5]))

    def isAncestor(self, ancestor: str, descendant: str) -> bool:
        result = self.git(["merge-base", "--is-ancestor", ancestor, descendant], timeout=self.localTimeout)
        return result.returncode == 0

    # -- write ---------------------------------------------------------------

    def commitFiles(self, expected: str | None, files: Mapping[str, bytes], message: str) -> str:
        """Add `files` to the tree at `expected` and CAS-push. Existing paths are never replaced."""

        indexDirectory = tempfile.mkdtemp(prefix="steward-evidence-index-")
        indexFile = str(Path(indexDirectory) / "index")
        env = {"GIT_INDEX_FILE": indexFile}
        try:
            if expected is not None:
                result = self.git(["read-tree", expected], timeout=self.localTimeout, env=env)
                if result.returncode != 0:
                    raise CustodyUnavailable(f"read-tree failed: {self.outputText(result).strip()[:300]}")
            for path, data in sorted(files.items()):
                if expected is not None:
                    existing = self.git(["cat-file", "-e", f"{expected}:{path}"], timeout=self.localTimeout)
                    if existing.returncode == 0:
                        stored = self.readFile(expected, path, limit=MAX_OBJECT_BYTES)
                        if stored != data:
                            raise CustodyRefused(f"immutable evidence path {path} already holds different bytes")
                        continue
                blob = self.plumb(["hash-object", "-w", "--stdin"], stdin=data)
                result = self.git(
                    ["update-index", "--add", "--cacheinfo", f"100644,{blob},{path}"],
                    timeout=self.localTimeout, env=env,
                )
                if result.returncode != 0:
                    raise CustodyUnavailable(f"update-index failed: {self.outputText(result).strip()[:300]}")
            result = self.git(["write-tree"], timeout=self.localTimeout, env=env)
            if result.returncode != 0:
                raise CustodyUnavailable(f"write-tree failed: {self.outputText(result).strip()[:300]}")
            tree = result.stdout.decode("utf-8", "replace").strip()
        finally:
            for name in (indexFile, indexFile + ".lock"):
                try:
                    os.unlink(name)
                except OSError:
                    pass
            try:
                os.rmdir(indexDirectory)
            except OSError:
                pass
        try:
            return self.publishTree(expected, tree, message)
        except LedgerConflict:
            raise
        except LedgerUnavailable as exc:
            raise CustodyUnavailable(f"evidence push failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Custody operations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Loaded:
    """A bundle whose manifest and every artifact byte were re-verified."""

    bundle: Bundle
    commit: str
    files: Mapping[str, bytes]  # role -> exact bytes


class Custody:
    """Publish, read back and restore evidence bundles through one store."""

    def __init__(self, store: GitEvidenceStore) -> None:
        self.store = store

    @classmethod
    def open(cls, repoRoot: Path | str, remote: str = "origin", ref: str | None = None) -> "Custody":
        try:
            return cls(GitEvidenceStore(repoRoot, remote, ref or os.environ.get(REF_VARIABLE) or EVIDENCE_REF))
        except (ValueError, LedgerUnavailable) as exc:
            raise CustodyUnavailable(f"evidence store is not usable: {exc}") from exc

    # -- publishing -----------------------------------------------------------

    def publish(self, bundle: Bundle, objects: Mapping[str, bytes]) -> PublishResult:
        """Durably store `bundle`, then prove it by reading it back from the remote.

        `objects` maps sha256 -> bytes for every artifact the manifest lists, and
        nothing else. A publish whose bundle is already durable is a no-op that
        still re-verifies, so resumed runs neither duplicate nor trust blindly.
        """

        listed = {item["sha256"] for item in bundle.artifacts.values()}
        if set(objects) != listed:
            raise CustodyRefused("published objects do not match the bundle's artifact list")
        for digest, data in objects.items():
            if sha256Hex(data) != digest:
                raise CustodyRefused("an artifact's bytes do not hash to its manifest entry")
            if len(data) > MAX_OBJECT_BYTES:
                raise CustodyRefused(f"an artifact exceeds the {MAX_OBJECT_BYTES} byte bound")
        path = bundlePath(bundle.debtId, bundle.bundleId)
        files = {objectPath(digest): data for digest, data in objects.items()}
        files[path] = bundle.raw

        lastConflict: Exception | None = None
        for attempt in range(PUBLISH_ATTEMPTS):
            expected = self.store.snapshot()
            existing = (
                self.store.readFile(expected, path, limit=MAX_MANIFEST_BYTES) if expected is not None else None
            )
            if existing is not None:
                stored = parseBundle(existing, expectedId=bundle.bundleId)
                if stored.identity != bundle.identity:
                    raise CustodyRefused("a different bundle already holds this id")
                self.loadAt(expected, bundle.bundleId, bundle.debtId)  # re-verify, never trust
                return PublishResult(bundle.bundleId, bundle.kind, str(expected), False, True,
                                     {role: item["sha256"] for role, item in bundle.artifacts.items()})
            try:
                commit = self.store.commitFiles(
                    expected, files,
                    f"steward evidence {bundle.kind} {bundle.bundleId[:12]}",
                )
            except LedgerConflict as exc:
                lastConflict = exc
                continue  # another writer advanced the ref; re-read and retry on the new tip
            readBack = self.readBack(bundle, commit)
            return PublishResult(bundle.bundleId, bundle.kind, readBack, True, True,
                                 {role: item["sha256"] for role, item in bundle.artifacts.items()})
        raise CustodyUnavailable(
            f"evidence ref kept moving under {PUBLISH_ATTEMPTS} attempts; nothing was confirmed ({lastConflict})"
        )

    def readBack(self, bundle: Bundle, pushedCommit: str) -> str:
        """Re-fetch the remote and re-verify what was written. Returns the tip verified."""

        tip = self.store.snapshot()
        if tip is None:
            raise CustodyUnavailable("read-back found no evidence ref on the remote after the push")
        if tip != pushedCommit and not self.store.isAncestor(pushedCommit, tip):
            raise CustodyUnavailable("read-back tip does not contain the commit that was pushed")
        self.loadAt(tip, bundle.bundleId, bundle.debtId)
        return tip

    # -- loading --------------------------------------------------------------

    def loadAt(self, commit: str | None, bundleId: str, debtId: str) -> Loaded:
        if commit is None:
            raise CustodyRefused("no evidence has been published (the evidence ref does not exist)")
        raw = self.store.readFile(commit, bundlePath(debtId, bundleId), limit=MAX_MANIFEST_BYTES)
        if raw is None:
            raise CustodyRefused(f"evidence bundle {bundleId} for this debt is missing from custody")
        bundle = parseBundle(raw, expectedId=bundleId)
        if bundle.debtId != debtId:
            raise CustodyRefused("evidence bundle is stored under a different debt")
        files: dict[str, bytes] = {}
        for role, item in sorted(bundle.artifacts.items()):
            data = self.store.readFile(commit, objectPath(item["sha256"]), limit=MAX_OBJECT_BYTES)
            if data is None:
                raise CustodyRefused(f"evidence artifact {role!r} ({item['sha256'][:12]}) is missing from custody")
            if len(data) != item["size"] or sha256Hex(data) != item["sha256"]:
                raise CustodyRefused(f"evidence artifact {role!r} does not match its recorded hash; it was altered")
            files[role] = data
        return Loaded(bundle=bundle, commit=commit, files=files)

    def bundles(self, commit: str | None, debtId: str) -> list[Bundle]:
        result: list[Bundle] = []
        for bundleId in self.store.listBundleIds(commit, debtId):
            raw = self.store.readFile(str(commit), bundlePath(debtId, bundleId), limit=MAX_MANIFEST_BYTES)
            if raw is not None:
                result.append(parseBundle(raw, expectedId=bundleId))
        return result

    def select(
        self, debtId: str, kind: str, *, bundleId: str | None = None, parent: str | None = None,
        dispatchId: str | None = None,
    ) -> tuple[str, Bundle]:
        """Pick exactly one bundle. Ambiguity is refused: the caller must name it."""

        commit = self.store.snapshot()
        found = [b for b in self.bundles(commit, debtId) if b.kind == kind]
        if bundleId is not None:
            found = [b for b in found if b.bundleId == bundleId or b.bundleId.startswith(bundleId)]
        if parent is not None:
            found = [b for b in found if b.parent == parent]
        if dispatchId is not None:
            found = [b for b in found if b.identity.get("dispatchId") == dispatchId]
        if not found:
            raise CustodyRefused(f"no {kind} evidence bundle exists in custody for debt {debtId}")
        if len(found) > 1:
            raise CustodyRefused(
                f"{len(found)} {kind} bundles match debt {debtId} ({', '.join(b.bundleId[:12] for b in found)}); "
                "name the intended one with --bundle"
            )
        return str(commit), found[0]

    def chain(self, debtId: str, bundleId: str | None = None) -> list[Loaded]:
        """Load and authenticate dispatch -> build -> verdict for one debt, newest tip.

        `bundleId` may name the build or verdict at the end of the chain. Every
        link's parent must exist and be of the right kind.
        """

        commit = self.store.snapshot()
        every = self.bundles(commit, debtId)
        byId = {b.bundleId: b for b in every}
        tails = [b for b in every if b.kind in ("build", "verdict")]
        if bundleId is not None:
            tails = [b for b in tails if b.bundleId.startswith(bundleId)]
        else:
            childless = {b.parent for b in every if b.parent}
            tails = [b for b in tails if b.bundleId not in childless]
        if not tails:
            dispatches = [b for b in every if b.kind == "dispatch"]
            if bundleId is None and dispatches:
                tails = dispatches
            else:
                raise CustodyRefused(f"no evidence chain exists in custody for debt {debtId}")
        if len(tails) > 1:
            raise CustodyRefused(
                f"{len(tails)} evidence chains end for debt {debtId} "
                f"({', '.join(b.bundleId[:12] for b in tails)}); name one with --bundle"
            )
        links: list[Loaded] = []
        cursor: Bundle | None = tails[0]
        expected = {"verdict": "build", "build": "dispatch"}
        while cursor is not None:
            links.append(self.loadAt(commit, cursor.bundleId, debtId))
            if cursor.kind == "dispatch":
                break
            parentId = cursor.parent
            parent = byId.get(parentId or "")
            if parent is None or parent.kind != expected[cursor.kind]:
                raise CustodyRefused(
                    f"{cursor.kind} bundle {cursor.bundleId[:12]} has no valid {expected[cursor.kind]} parent in custody"
                )
            cursor = parent
        links.reverse()
        return links


# ---------------------------------------------------------------------------
# Authenticating the Steward artifacts inside a bundle
# ---------------------------------------------------------------------------


def parseJsonObject(raw: bytes, label: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CustodyRefused(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CustodyRefused(f"{label} must be a JSON object")
    return data


def authenticateDispatch(scanRaw: bytes, dispatchRaw: bytes, *, debtId: str) -> dict[str, Any]:
    """Check a dispatch receipt and its scan the way `_dispatch_receipt_for` will, before storing or trusting them.

    Returns facts for the manifest. This never writes, never re-renders and
    never consults today's policy: it only asks whether these exact bytes still
    attest to themselves and to each other.
    """

    dispatch = parseJsonObject(dispatchRaw, "dispatch receipt")
    scan = parseJsonObject(scanRaw, "scan receipt")
    if dispatch.get("action") != "dispatch":
        raise CustodyRefused("the receipt is not a dispatch receipt")
    artifact = dispatch.get("artifact")
    if not isinstance(artifact, dict):
        raise CustodyRefused("the dispatch receipt carries no artifact")
    debt = artifact.get("debt")
    if not isinstance(debt, dict) or debt.get("id") != debtId:
        raise CustodyRefused(f"the dispatch receipt does not authorize debt {debtId}")
    runId = str(dispatch.get("runId", ""))
    if not run_id_matches(runId, {"action": "dispatch", "scanReceiptId": dispatch.get("scanReceiptId"), "artifact": artifact}):
        raise CustodyRefused(
            "the dispatch receipt no longer matches its own content hash; it is not evidence of what was authorized"
        )
    scanId = str(dispatch.get("scanReceiptId", ""))
    if not scanId or scan.get("runId") != scanId:
        raise CustodyRefused("the scan receipt is not the scan this dispatch was issued against")
    if not isinstance(scan.get("openDebt"), list):
        raise CustodyRefused("the scan receipt records no open debt set")
    for field in ("headCommit", "gitHead"):
        if field in dispatch:
            raise CustodyRefused(f"the dispatch receipt carries an unauthenticated top-level {field}")
    head = artifact.get("headCommit")
    if head is not None and (not isinstance(head, str) or not FULL_COMMIT.match(head)):
        raise CustodyRefused("the dispatch receipt records a headCommit that is not a full commit id")
    proof = artifact.get("proof")
    return {
        "dispatchReceiptId": runId,
        "scanReceiptId": scanId,
        "dispatchId": str(artifact.get("dispatchId") or artifact.get("dispatch_id") or ""),
        "sourceCommit": head,
        "proofContractLength": len(proof) if isinstance(proof, list) else 0,
    }


def dispatchBundle(
    *, debtId: str, scanRaw: bytes, dispatchRaw: bytes, writer: Mapping[str, Any]
) -> tuple[Bundle, dict[str, bytes]]:
    facts = authenticateDispatch(scanRaw, dispatchRaw, debtId=debtId)
    if not facts["dispatchId"]:
        raise CustodyRefused("the dispatch receipt names no dispatch id")
    artifacts = {
        "scan-receipt": Artifact("scan-receipt", sha256Hex(scanRaw), len(scanRaw), f"{facts['scanReceiptId']}.json"),
        "dispatch-receipt": Artifact("dispatch-receipt", sha256Hex(dispatchRaw), len(dispatchRaw), f"{facts['dispatchReceiptId']}.json"),
    }
    identity = {
        "kind": "dispatch", "debtId": debtId, "dispatchId": facts["dispatchId"],
        "dispatchReceiptId": facts["dispatchReceiptId"], "scanReceiptId": facts["scanReceiptId"],
        "sourceCommit": facts["sourceCommit"], "parent": None,
        "artifacts": {role: art.to_dict() for role, art in artifacts.items()},
    }
    objects = {artifacts["scan-receipt"].sha256: scanRaw, artifacts["dispatch-receipt"].sha256: dispatchRaw}
    return makeBundle(identity, {"createdAt": nowUtc(), "writer": dict(writer)}), objects


def buildBundle(
    *, dispatch: Loaded, diffRaw: bytes | None, proofRaw: bytes | None, noChange: bool,
    summary: str, writer: Mapping[str, Any],
) -> tuple[Bundle, dict[str, bytes]]:
    """A builder's output, tied to the exact dispatch bundle that authorized it."""

    from gaia_cli.steward.verification import VerificationError, parse_proof_transcript

    if dispatch.bundle.kind != "dispatch":
        raise CustodyRefused("a build bundle must descend from a dispatch bundle")
    facts = authenticateDispatch(
        dispatch.files["scan-receipt"], dispatch.files["dispatch-receipt"], debtId=dispatch.bundle.debtId
    )
    artifacts: dict[str, Artifact] = {}
    objects: dict[str, bytes] = {}
    if noChange:
        if diffRaw or proofRaw:
            raise CustodyRefused("a no-change build must not carry a diff or proof")
    else:
        if not diffRaw or not diffRaw.strip():
            raise CustodyRefused("the candidate diff is missing or empty; a build that changed nothing must say no-change")
        if b"@@" not in diffRaw:
            raise CustodyRefused("the candidate diff holds no hunks; it is not a unified diff")
        if not proofRaw or not proofRaw.strip():
            raise CustodyRefused("the proof transcript is missing or empty; /dev/null is not proof")
        try:
            parse_proof_transcript(proofRaw.decode("utf-8"), proof_contract_length=facts["proofContractLength"])
        except (VerificationError, UnicodeDecodeError) as exc:
            raise CustodyRefused(f"the proof transcript is not a valid steward-proof-transcript-v1: {exc}") from exc
        artifacts["candidate-diff"] = Artifact("candidate-diff", sha256Hex(diffRaw), len(diffRaw), "candidate.diff")
        artifacts["proof-transcript"] = Artifact("proof-transcript", sha256Hex(proofRaw), len(proofRaw), "proof.json")
        objects = {artifacts["candidate-diff"].sha256: diffRaw, artifacts["proof-transcript"].sha256: proofRaw}
    identity = {
        "kind": "build", "debtId": dispatch.bundle.debtId, "dispatchId": facts["dispatchId"],
        "dispatchReceiptId": facts["dispatchReceiptId"], "scanReceiptId": facts["scanReceiptId"],
        "sourceCommit": facts["sourceCommit"], "parent": dispatch.bundle.bundleId, "noChange": noChange,
        "artifacts": {role: art.to_dict() for role, art in artifacts.items()},
    }
    meta = {"createdAt": nowUtc(), "writer": dict(writer), "summary": summary}
    return makeBundle(identity, meta), objects


def verdictBundle(
    *, build: Loaded, receiptRaw: bytes, writer: Mapping[str, Any]
) -> tuple[Bundle, dict[str, bytes]]:
    """The recorded outcome of mechanical verification, tied to the build it judged."""

    if build.bundle.kind != "build":
        raise CustodyRefused("a verdict bundle must descend from a build bundle")
    receipt = parseJsonObject(receiptRaw, "verification receipt")
    artifact = receipt.get("artifact")
    if receipt.get("action") != "verify" or not isinstance(artifact, dict):
        raise CustodyRefused("the receipt is not a verification receipt")
    if artifact.get("dispatch_id", artifact.get("dispatchId")) != build.bundle.identity.get("dispatchId"):
        raise CustodyRefused("the verification receipt judged a different dispatch than this build")
    receiptId = str(receipt.get("runId", ""))
    if not run_id_matches(receiptId, {"action": "verify", "scanReceiptId": receipt.get("scanReceiptId"), "artifact": artifact}):
        raise CustodyRefused("the verification receipt no longer matches its own content hash")
    verdict = str(artifact.get("verdict", ""))
    art = Artifact("verification-receipt", sha256Hex(receiptRaw), len(receiptRaw), f"{receiptId}.json")
    identity = {
        "kind": "verdict", "debtId": build.bundle.debtId,
        "dispatchId": build.bundle.identity.get("dispatchId"),
        "dispatchReceiptId": build.bundle.identity.get("dispatchReceiptId"),
        "scanReceiptId": build.bundle.identity.get("scanReceiptId"),
        "sourceCommit": build.bundle.identity.get("sourceCommit"), "parent": build.bundle.bundleId,
        "verdict": verdict, "artifacts": {"verification-receipt": art.to_dict()},
    }
    meta = {"createdAt": nowUtc(), "writer": dict(writer), "verificationReceiptId": receiptId}
    return makeBundle(identity, meta), {art.sha256: receiptRaw}


# ---------------------------------------------------------------------------
# Restoring into a clean checkout
# ---------------------------------------------------------------------------


def writeExclusive(path: Path, data: bytes, *, repoRoot: Path, stateRoot: Path) -> bool:
    """Write exact bytes without clobbering. Existing identical bytes are fine; different bytes are tampering."""

    ensure_local_state_path(repoRoot, stateRoot, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_local_state_path(repoRoot, stateRoot, path)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    except FileExistsError:
        if path.read_bytes() != data:
            raise CustodyRefused(
                f"{path.name} already exists locally with different bytes than custody holds; refusing to overwrite"
            )
        return False
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("restore write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        try:
            path.unlink()
        except OSError:
            pass
        raise
    os.close(descriptor)
    return True


@dataclass(frozen=True)
class Restored:
    dispatch: Loaded
    build: Loaded | None
    receiptPaths: tuple[Path, ...]
    diffPath: Path | None
    proofPath: Path | None
    evidenceDirectory: Path


def restoreChain(
    custody: Custody, repoRoot: Path, debtId: str, *, bundleId: str | None, receiptsDirectory: Path, stateRoot: Path,
) -> Restored:
    """Retrieve and authenticate a chain, then lay the original bytes into this checkout.

    The baseline commit must exist here: a checkout that cannot resolve the
    authorized baseline cannot verify against it.
    """

    links = custody.chain(debtId, bundleId)
    dispatch = links[0]
    if dispatch.bundle.kind != "dispatch":
        raise CustodyRefused("the evidence chain does not begin with a dispatch bundle")
    facts = authenticateDispatch(dispatch.files["scan-receipt"], dispatch.files["dispatch-receipt"], debtId=debtId)
    source = facts["sourceCommit"]
    if source is not None:
        probe = custody.store.git(["cat-file", "-e", f"{source}^{{commit}}"], timeout=custody.store.localTimeout)
        if probe.returncode != 0:
            raise CustodyRefused(
                f"the authorized baseline commit {source[:12]} is not present in this checkout; "
                "fetch it before verifying (an unrelated baseline cannot stand in)"
            )
    build = next((link for link in links if link.bundle.kind == "build"), None)
    written: list[Path] = []
    for role in ("scan-receipt", "dispatch-receipt"):
        item = dispatch.bundle.artifacts[role]
        path = receiptsDirectory / item["name"]
        writeExclusive(path, dispatch.files[role], repoRoot=repoRoot, stateRoot=stateRoot)
        written.append(path)
    evidenceDirectory = stateRoot / "evidence" / (build or dispatch).bundle.bundleId[:16]
    diffPath = proofPath = None
    if build is not None and not build.bundle.identity.get("noChange"):
        diffPath = evidenceDirectory / "candidate.diff"
        proofPath = evidenceDirectory / "proof.json"
        writeExclusive(diffPath, build.files["candidate-diff"], repoRoot=repoRoot, stateRoot=stateRoot)
        writeExclusive(proofPath, build.files["proof-transcript"], repoRoot=repoRoot, stateRoot=stateRoot)
    return Restored(dispatch, build, tuple(written), diffPath, proofPath, evidenceDirectory)


def handoffRecord(links: list[Loaded], ref: str = EVIDENCE_REF) -> dict[str, Any]:
    """The PR-safe summary of a complete chain: ids and hashes, never payloads."""

    return {
        "schemaVersion": HANDOFF_SCHEMA,
        "debtId": links[0].bundle.debtId,
        "evidenceRef": ref,
        "evidenceCommit": links[-1].commit,
        "sourceCommit": links[0].bundle.identity.get("sourceCommit"),
        "dispatchId": links[0].bundle.identity.get("dispatchId"),
        "bundles": [
            {
                "kind": link.bundle.kind,
                "bundleId": link.bundle.bundleId,
                "artifacts": {role: item["sha256"] for role, item in sorted(link.bundle.artifacts.items())},
            }
            for link in links
        ],
    }


def newRunToken() -> str:
    return uuid.uuid4().hex[:12]
