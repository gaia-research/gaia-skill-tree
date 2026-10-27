"""Read-only validation and handoff helpers for Frontier challenger leads.

A lead is untrusted discovery input. This module deliberately has no verifier,
approval, registry mutation, trust, rank, or challenge-admission API.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from jsonschema import Draft202012Validator, FormatChecker

DATA = Path(__file__).parent / "data" / "frontier"
SCHEMA = DATA / "challenger-lead-v1.1.schema.json"
REQUEST_SCHEMA = DATA / "frontier-verification-request-v1.schema.json"
EXPERIMENT_SCHEMA = DATA / "experiment-receipt-v1.schema.json"
EXPERIMENT_SCHEMA_V11 = DATA / "experiment-receipt-v1.1.schema.json"
PROTOCOL_SCHEMA = DATA / "frontier-protocol-v1.schema.json"
DEFAULT_ARTIFACT_ROOT = "generated-output/frontier"
COMMITTED_ARTIFACT_ROOT = re.compile(r"evidence/frontier-challenges/[A-Za-z0-9][A-Za-z0-9._-]*/artifacts")
EXPERIMENT_RESULTS = ("supported", "contradicted", "inconclusive", "execution_failed")
UNIVERSAL_ARTIFACT_KEYS = ("experiment", "executionCheck", "requestId", "fixtureDigest", "protocolDigest")
VERSION_MISMATCH_RESULTS = {"inconclusive", "execution_failed"}
# Declaration for the pre-generic git-log-L protocol file, which stays byte-identical
# (its digest is bound into existing requests/receipts) and so declares nothing itself.
LEGACY_EXPERIMENTS = {
    "git-log-L-vs-graft-v1": {
        "id": "git-log-L-vs-graft-v1", "toolName": "Git", "runnerLabel": "Fixed Git fixture runner",
        "expectedArtifactKeys": list(UNIVERSAL_ARTIFACT_KEYS) + ["gitVersion", "output", "outputDigest"],
        "outputField": "output", "outputDigestField": "outputDigest",
        "versionProbe": {"field": "gitVersion", "pattern": r"git version (\S+)(?: .*)?", "label": "git --version", "crossCheckField": "executedVersion"},
        "resultRule": {"statement": "Legacy git-log-L rule: comparative results need native and target artifacts; a version mismatch permits only inconclusive or execution_failed.", "allowedResults": list(EXPERIMENT_RESULTS)},
    }
}
FORBIDDEN_AUTHORITY_FIELDS = {"verified", "verifiedBy", "approvedBy", "verificationReceipt", "confidence", "publicChallengeId", "challengeStatus", "verifierId", "actor", "signature", "admission"}


def canonical_source_url(value: str) -> str:
    """Normalize only safe HTTPS source URLs; reject credentials and fragments."""
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("source URL must be credential-free HTTPS")
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/")
    return urlunsplit(("https", parts.netloc.lower(), path, parts.query, ""))


def validate_lead(data: dict[str, Any]) -> list[str]:
    """Return schema errors and reject caller-supplied authority assertions."""
    if not isinstance(data, dict):
        return ["lead must be a JSON object"]
    forged = sorted(FORBIDDEN_AUTHORITY_FIELDS.intersection(data))
    errors = [f"forbidden authority field: {key}" for key in forged]
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")), format_checker=FormatChecker())
    errors.extend(f"{'.'.join(map(str, error.absolute_path)) or '$'}: {error.message}" for error in validator.iter_errors(data))
    if isinstance(data.get("source"), dict):
        try:
            canonical_source_url(data["source"].get("url", ""))
        except (TypeError, ValueError) as exc:
            errors.append(f"source.url: {exc}")
    return sorted(errors)


def dedupe_key(data: dict[str, Any]) -> str:
    """Stable semantic key; observation timestamps do not make repeats unique."""
    identity = data["identity"]["name"].strip().casefold()
    version = str(data["identity"]["version"]).casefold()
    url = canonical_source_url(data["source"]["url"])
    task = " ".join(data["capability"]["task"].casefold().split())
    target = data["target"]["skillId"].casefold()
    target_revision = data["target"]["revision"].lower()
    return hashlib.sha256("\0".join((identity, version, url, task, target, target_revision, data["target"]["contentDigest"])).encode()).hexdigest()


def _canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _validated_file(root: Path, relative: str) -> tuple[Path, bytes]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"required pinned file missing or outside checkout: {relative}")
    return path, path.read_bytes()


def create_verification_request(data: dict[str, Any], *, repo_root: str | Path, lead_path: str, protocol_path: str, fixture_path: str) -> dict[str, Any]:
    """Bind lead, captured source, actual canonical target, reviewed protocol and fixture."""
    errors = validate_lead(data)
    if errors:
        raise ValueError("invalid challenger lead: " + "; ".join(errors))
    root = Path(repo_root).resolve()
    target = data["target"]
    ref = target["skillId"]
    if target["kind"] == "named":
        parts = ref.split("/")
        if len(parts) != 2 or any(part in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", part) for part in parts):
            raise ValueError("named target identity is not a safe owner/slug")
        owner, slug = parts
        relative = f"registry/named/{owner}/{slug}.md"
        generic_id = _read_named_generic(root / relative)
        if generic_id != target.get("genericSkillId"):
            raise ValueError("target genericSkillId does not match named skill frontmatter")
        paths = [relative]
        generic_path = _find_generic(root, generic_id)
        paths.append(generic_path)
    else:
        paths = [_find_generic(root, ref)]
        generic_id = ref
    protocol_revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    revision = target["revision"]
    try:
        resolved = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--verify", f"{revision}^{{commit}}"], text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        raise ValueError("lead target revision does not resolve to a commit in this repository") from None
    if resolved != revision:
        raise ValueError("lead target revision must be the full immutable commit id it resolves to")
    target_bytes = []
    for path in paths:
        _validated_file(root, path)
        pinned = subprocess.check_output(["git", "-C", str(root), "show", f"{revision}:{path}"])
        target_bytes.append(pinned)
    if target["kind"] == "named" and _read_named_generic_bytes(target_bytes[0], paths[0]) != generic_id:
        raise ValueError("pinned named target genericSkillRef does not match its lead")
    target_digest = _sha(_canonical({"paths": paths, "digests": [_sha(b) for b in target_bytes]}))
    if target.get("contentDigest") != _sha(target_bytes[0]):
        raise ValueError("lead target content digest does not match exact repository bytes")
    source_path, source_bytes = _validated_file(root, data["source"]["capturedBytesPath"])
    if _sha(source_bytes) != data["source"]["contentDigest"]:
        raise ValueError("captured source bytes digest mismatch")
    protocol, protocol_bytes = _validated_file(root, protocol_path)
    fixture, fixture_bytes = _validated_file(root, fixture_path)
    for relative, current in ((protocol_path, protocol_bytes), (fixture_path, fixture_bytes)):
        pinned = subprocess.check_output(["git", "-C", str(root), "show", f"{protocol_revision}:{relative}"])
        if current != pinned: raise ValueError(f"working experiment input differs from pinned revision: {relative}")
    lead_file, lead_bytes = _validated_file(root, lead_path)
    if json.loads(lead_bytes) != data:
        raise ValueError("lead file content does not match request input")
    claim_digest = _sha(_canonical({"claimId": data["claimId"], "claim": data["capability"], "comparison": data["comparison"]}))
    binding = {
        "schemaVersion": "frontier-verification-request-v1", "campaignId": data["campaignId"], "leadId": data["leadId"],
        "leadDigest": _sha(_canonical(data)), "claimId": data["claimId"], "claimDigest": claim_digest,
        "native": {"name": data["identity"]["name"], "version": data["identity"]["version"], "provider": data["source"]["provider"]},
        "source": {"url": data["source"]["url"], "contentDigest": _sha(source_bytes), "capturedBytesPath": data["source"]["capturedBytesPath"]},
        "target": {"kind": target["kind"], "skillId": ref, "genericSkillId": generic_id, "revision": revision, "contentDigest": target_digest, "path": paths[0]},
        "historyRef": f"git:{revision}",
        "protocol": {"path": protocol_path, "revision": protocol_revision, "contentDigest": _sha(protocol_bytes)},
        "fixture": {"path": fixture_path, "contentDigest": _sha(fixture_bytes)},
        "conditions": data["capability"]["conditions"],
    }
    request_id = _sha(_canonical(binding))
    result = {"schemaVersion": binding["schemaVersion"], "requestId": request_id, **{k:v for k,v in binding.items() if k != "schemaVersion"}, "createdAtUTC": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    errors = _validate_schema(result, REQUEST_SCHEMA)
    if errors: raise ValueError("invalid verification request: " + "; ".join(errors))
    return result


def _read_named_generic(path: Path) -> str:
    return _read_named_generic_bytes(path.read_bytes(), f"{path.parent.name}/{path.stem}")


def _read_named_generic_bytes(raw: bytes, identity_path: str) -> str:
    import yaml
    text = raw.decode("utf-8")
    if not text.startswith("---\n"): raise ValueError("named target has no frontmatter")
    meta = yaml.safe_load(text.split("---", 2)[1])
    expected_id = identity_path.removeprefix("registry/named/").removesuffix(".md")
    if not isinstance(meta, dict) or not meta.get("id") or not meta.get("genericSkillRef"):
        raise ValueError("named target lacks canonical identity/reference")
    if meta["id"] != expected_id: raise ValueError("named target identity mismatch")
    return meta["genericSkillRef"]


def _find_generic(root: Path, skill_id: str) -> str:
    for path in (root / "registry/nodes").rglob("*.json"):
        try: node = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError): continue
        if node.get("id") == skill_id: return path.relative_to(root).as_posix()
    raise ValueError(f"target generic skill does not exist: {skill_id}")


def _validate_schema(data: dict[str, Any], schema_path: Path) -> list[str]:
    validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")), format_checker=FormatChecker())
    return sorted(f"{'.'.join(map(str,e.absolute_path)) or '$'}: {e.message}" for e in validator.iter_errors(data))


def validate_request(request: dict[str, Any]) -> list[str]:
    errors = _validate_schema(request, REQUEST_SCHEMA)
    if errors: return errors
    binding = {k:v for k,v in request.items() if k not in {"requestId", "createdAtUTC"}}
    if request["requestId"] != _sha(_canonical(binding)):
        errors.append("requestId does not match immutable request content")
    return errors


def validate_experiment_receipt(receipt: dict[str, Any], request: dict[str, Any], *, repo_root: str | Path | None = None, artifact_root: str = DEFAULT_ARTIFACT_ROOT) -> list[str]:
    """Check binding and output-file integrity; result remains untrusted and never means admission.

    `artifact_root` names the repo-relative directory every output must live under:
    `generated-output/frontier` (default) or a committed bundle's
    `evidence/frontier-challenges/<id>/artifacts`, so archived bundles re-validate.
    """
    is_v11 = isinstance(receipt, dict) and receipt.get("schemaVersion") == "frontier-experiment-receipt-v1.1"
    errors = _validate_schema(receipt, EXPERIMENT_SCHEMA_V11 if is_v11 else EXPERIMENT_SCHEMA)
    request_errors = validate_request(request)
    errors.extend(f"request: {error}" for error in request_errors)
    if not isinstance(receipt, dict) or request_errors:
        return sorted(set(errors))
    links = {"campaignId": request["campaignId"], "nativeVersion": request["native"]["version"], "requestId": request["requestId"], "leadDigest": request["leadDigest"], "claimDigest": request["claimDigest"], "sourceDigest": request["source"]["contentDigest"], "targetDigest": request["target"]["contentDigest"], "targetRevision": request["target"]["revision"], "historyRef": request["historyRef"], "protocolDigest": request["protocol"]["contentDigest"], "fixtureDigest": request["fixture"]["contentDigest"]}
    if is_v11:
        # nativeVersion reports what actually ran; the request's version is claim provenance only.
        links["nativeVersion"] = receipt.get("executedVersion")
        links["documentedVersion"] = request["native"]["version"]
    errors.extend(f"cross-binding mismatch: {key}" for key, value in links.items() if receipt.get(key) != value)
    if is_v11 and receipt.get("documentedVersion") != receipt.get("executedVersion"):
        if receipt.get("result") not in VERSION_MISMATCH_RESULTS:
            errors.append("documented and executed versions differ: only inconclusive or execution_failed is permitted")
        if not any(isinstance(x, str) and "differs from documented version" in x for x in receipt.get("limitations", [])):
            errors.append("documented and executed versions differ: limitation entry required")
    outputs = receipt.get("outputs", [])
    labels = {item.get("label") for item in outputs if isinstance(item, dict)}
    if receipt.get("result") in {"supported", "contradicted"}:
        if not {"native", "target"}.issubset(labels):
            errors.append("comparative outcome requires actual native and target output artifacts")
        if repo_root is None:
            errors.append("comparative outcome requires local output integrity verification")
    if outputs and repo_root is None:
        errors.append("output artifacts require local integrity verification")
    if repo_root is not None:
        root = Path(repo_root).resolve()
        resolved_outputs = []
        for item in outputs:
            try:
                relative = item["path"]
                if Path(relative).as_posix() != relative:
                    errors.append(f"output artifact path is not normalized: {relative}")
                path = resolve_artifact(root, relative, artifact_root)
                _, raw = _validated_file(root, relative)
                resolved_outputs.append(path)
                if _sha(raw) != item.get("contentDigest"):
                    errors.append(f"output artifact digest mismatch: {item.get('label')}")
            except (KeyError, TypeError, ValueError) as exc:
                if "descendant" in str(exc):
                    errors.append(f"output artifact is outside {artifact_root}")
                else:
                    errors.append(f"invalid output artifact: {exc}")
        if len(set(resolved_outputs)) != len(resolved_outputs):
            errors.append("output artifacts alias each other")
        try:
            pinned = pinned_declaration(root, request)
            if receipt.get("result") not in pinned["resultRule"]["allowedResults"]:
                errors.append("result is not permitted by the pinned protocol result rule")
            if "experimentId" in receipt and receipt["experimentId"] != pinned["id"]:
                errors.append("experimentId does not match the pinned protocol")
        except ValueError:
            if "experimentId" in receipt:
                errors.append("experimentId cannot be checked: pinned protocol declares no experiment contract")
    return sorted(set(errors))


def _artifact_base(root: Path, artifact_root: str) -> Path:
    """Resolve a permitted artifact root; refuse unknown roots and symlinked components."""
    if artifact_root != DEFAULT_ARTIFACT_ROOT and not COMMITTED_ARTIFACT_ROOT.fullmatch(str(artifact_root)):
        raise ValueError("artifact_root must be generated-output/frontier or evidence/frontier-challenges/<id>/artifacts")
    current = root
    for part in Path(artifact_root).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("artifact_root must not contain symlinks")
    resolved = current.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("artifact_root is outside checkout")
    return resolved


def resolve_artifact(root: str | Path, relative: str, artifact_root: str = DEFAULT_ARTIFACT_ROOT) -> Path:
    """Confine reads/writes to real descendants of the artifact root; never follow symlinks."""
    root = Path(root).resolve()
    _artifact_base(root, artifact_root)
    rel, prefix = Path(relative), Path(artifact_root).parts
    if rel.is_absolute() or ".." in rel.parts or rel.parts[:len(prefix)] != prefix or len(rel.parts) <= len(prefix):
        raise ValueError(f"artifact must be a relative {artifact_root} descendant")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("artifact paths must not contain symlinks")
    if not current.resolve().is_relative_to(root):
        raise ValueError("artifact is outside checkout")
    return current


def validate_protocol(protocol: Any) -> list[str]:
    """Schema-check a `frontier-protocol-v1` document, including its version-probe regex."""
    if not isinstance(protocol, dict):
        return ["protocol must be a JSON object"]
    errors = _validate_schema(protocol, PROTOCOL_SCHEMA)
    if not errors:
        try:
            probe = protocol["experiment"]["versionProbe"]["pattern"]
            if re.compile(probe).groups != 1:
                errors.append("experiment.versionProbe.pattern: must have exactly one capture group (the executed version)")
        except re.error as exc:
            errors.append(f"experiment.versionProbe.pattern: invalid regex: {exc}")
    return errors


def experiment_declaration(protocol: Any) -> dict[str, Any]:
    """Return the experiment contract a protocol declares (explicitly, or the legacy git-log-L one)."""
    if isinstance(protocol, dict) and protocol.get("schemaVersion") == "frontier-protocol-v1":
        errors = validate_protocol(protocol)
        if errors:
            raise ValueError("invalid protocol: " + "; ".join(errors))
        return protocol["experiment"]
    if isinstance(protocol, dict) and protocol.get("protocolId") in LEGACY_EXPERIMENTS:
        return LEGACY_EXPERIMENTS[protocol["protocolId"]]
    raise ValueError("protocol declares no experiment contract (expected schemaVersion frontier-protocol-v1)")


def pinned_declaration(root: Path, request: dict[str, Any], protocol: str | None = None) -> dict[str, Any]:
    """Experiment contract declared by the protocol file the request pins; digest-checked, never caller-supplied."""
    pinned = request["protocol"]["path"]
    if protocol is not None and str(protocol) != pinned:
        raise ValueError("protocol path does not match the request's pinned protocol")
    _, raw = _validated_file(root, pinned)
    if _sha(raw) != request["protocol"]["contentDigest"]:
        raise ValueError("checkout protocol bytes differ from the request")
    try:
        document = json.loads(raw)
    except ValueError as exc:
        raise ValueError(f"protocol is not valid JSON: {exc}") from None
    return experiment_declaration(document)


def build_experiment_receipt(*, root: str | Path, request: dict[str, Any], execution_path: str, protocol: str | None = None,
                             target_path: str | None = None, result: str = "inconclusive",
                             artifact_root: str = DEFAULT_ARTIFACT_ROOT, run_id: str | None = None,
                             recorded_at: str | None = None) -> dict[str, Any]:
    """Bind a runner artifact to a request under the contract its pinned protocol declares.

    The experiment contract is always read from the protocol file the request pins (checked
    against the request's digest); `protocol`, if given, must name that same path. The result
    is an untrusted experiment record, never a verifier authentication or admission.
    """
    root = Path(root).resolve()
    if result not in EXPERIMENT_RESULTS:
        raise ValueError("invalid experimental result")
    request_errors = validate_request(request)
    if request_errors:
        raise ValueError("request integrity check failed")
    declaration = pinned_declaration(root, request, protocol)
    if result not in declaration["resultRule"]["allowedResults"]:
        raise ValueError(f"result {result} is not permitted by the protocol result rule")
    native_file = resolve_artifact(root, execution_path, artifact_root)
    native_raw = native_file.read_bytes()
    execution = json.loads(native_raw)
    if not isinstance(execution, dict) or execution.get("experiment") != declaration["id"] or execution.get("executionCheck") != "passed":
        raise ValueError("fixed runner output did not match expected reviewed protocol")
    probe = declaration["versionProbe"]
    required = list(dict.fromkeys([*declaration["expectedArtifactKeys"], *UNIVERSAL_ARTIFACT_KEYS, probe["field"], declaration["outputField"], declaration["outputDigestField"]]))
    missing = [key for key in required if key not in execution]
    if missing:
        raise ValueError("native artifact is missing expected keys: " + ", ".join(missing))
    probed = str(execution.get(probe["field"], "")).strip()
    match = re.fullmatch(probe["pattern"], probed) if len(probed) <= 200 else None
    if not match or not match.group(1):
        raise ValueError(f"native artifact lacks a recognizable {probe['label']} string")
    executed = match.group(1)
    cross = probe.get("crossCheckField")
    if cross and cross in execution and execution[cross] != executed:
        raise ValueError(f"native artifact {cross} does not match its recorded {probe['label']}")
    documented = request["native"]["version"]
    if executed != documented and result not in VERSION_MISMATCH_RESULTS:
        raise ValueError(f"executed {declaration['toolName']} {executed} differs from documented {documented}: only inconclusive or execution_failed may be recorded")
    recorded = execution.get("result")
    if recorded is not None and recorded != result and not (recorded == "inconclusive" and target_path is not None):
        raise ValueError(f"result {result} contradicts the runner artifact's recorded result {recorded}; only a paired target artifact may move an inconclusive runner result")
    for key, expected in (("requestId", request["requestId"]), ("fixtureDigest", request["fixture"]["contentDigest"]), ("protocolDigest", request["protocol"]["contentDigest"])):
        if execution.get(key) != expected:
            raise ValueError(f"native artifact {key} does not match the request")
    # Also bind to the fixture bytes this checkout holds, not only the request's claim.
    _, fixture_raw = _validated_file(root, request["fixture"]["path"])
    if _sha(fixture_raw) != request["fixture"]["contentDigest"]:
        raise ValueError("checkout fixture bytes differ from the request")
    output = execution.get(declaration["outputField"])
    if not isinstance(output, str) or execution.get(declaration["outputDigestField"]) != _sha(output.encode("utf-8")):
        raise ValueError("native recorded output digest mismatch")
    outputs = [{"label": "native", "contentDigest": _sha(native_raw), "path": execution_path}]
    limitations = ["This is an untrusted experiment record, not verifier authentication or public challenge admission."]
    if executed != documented:
        limitations.append(f"Executed {declaration['toolName']} version {executed} differs from documented version {documented}; the documented tag is claim provenance only, so only inconclusive or execution_failed is permitted.")
    if target_path is not None:
        target_file = resolve_artifact(root, target_path, artifact_root)
        target_raw = target_file.read_bytes()
        if not target_raw.strip():
            raise ValueError("target output artifact is empty")
        if native_file == target_file:
            raise ValueError("native and target outputs must be distinct artifacts")
        if hashlib.sha256(target_raw).digest() == hashlib.sha256(native_raw).digest():
            raise ValueError("native and target outputs must have distinct content")
        outputs.append({"label": "target", "contentDigest": _sha(target_raw), "path": target_path})
        limitations.append("Paired artifacts alone establish neither comparable performance, superiority nor independent verification; Meta must assess protocol execution and counterevidence.")
    else:
        limitations.append(f"{declaration['runnerLabel']} executed; no target comparison output is attached.")
    receipt = {
        "schemaVersion": "frontier-experiment-receipt-v1.1", "experimentRunId": run_id or "run-" + uuid.uuid4().hex,
        "campaignId": request["campaignId"], "nativeVersion": executed,
        "documentedVersion": documented, "executedVersion": executed,
        "requestId": request["requestId"], "leadDigest": request["leadDigest"], "claimDigest": request["claimDigest"],
        "sourceDigest": request["source"]["contentDigest"], "targetDigest": request["target"]["contentDigest"],
        "targetRevision": request["target"]["revision"], "historyRef": request["historyRef"],
        "protocolDigest": request["protocol"]["contentDigest"], "fixtureDigest": request["fixture"]["contentDigest"],
        "result": result, "outputs": outputs, "limitations": limitations,
        "recordedAtUTC": recorded_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if declaration is not LEGACY_EXPERIMENTS.get(declaration["id"]):
        receipt["experimentId"] = declaration["id"]
    errors = validate_experiment_receipt(receipt, request, repo_root=root, artifact_root=artifact_root)
    if errors:
        raise ValueError("receipt invalid: " + "; ".join(errors))
    return receipt


def read_only_handoff(data: dict[str, Any], *, packet_path: str, request: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a work request for existing Meta/audit workflows, never an admission."""
    errors = validate_lead(data)
    if errors:
        raise ValueError("invalid challenger lead: " + "; ".join(errors))
    if request is not None and (not isinstance(request, dict) or request.get("leadId") != data["leadId"] or request.get("leadDigest") != _sha(_canonical(data)) or validate_request(request)):
        raise ValueError("request does not bind the supplied lead or failed request integrity validation")
    matched = request is not None and request.get("target", {}).get("skillId") == data["target"]["skillId"]
    return {
        "schemaVersion": "frontier-meta-handoff-v1",
        "leadId": data["leadId"],
        "packetPath": packet_path,
        "leadDisposition": data["disposition"]["status"] if matched else "deferred",
        "targetSkillId": data["target"]["skillId"],
        "verificationRequestId": request["requestId"] if matched else None,
        "advisoryMatch": "matched-actionable-request" if matched else "unmatched-advisory-deferred",
        "requestedWork": ["gaia-meta-audit triage", "gaia-audit focused independent verification"],
        "verification": "unverified-lead",
        "experimentalResult": "not-executed",
        "publicChallengeAdmission": "not-requested-until-independent-verification",
        "trustedReceiptIssuer": "unavailable-in-this-lane; fail closed",
        "canonicalMutation": "prohibited",
        "createdAtUTC": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
