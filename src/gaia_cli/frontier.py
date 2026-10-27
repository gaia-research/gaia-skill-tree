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
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from jsonschema import Draft202012Validator, FormatChecker

DATA = Path(__file__).parent / "data" / "frontier"
SCHEMA = DATA / "challenger-lead-v1.1.schema.json"
REQUEST_SCHEMA = DATA / "frontier-verification-request-v1.schema.json"
EXPERIMENT_SCHEMA = DATA / "experiment-receipt-v1.schema.json"
EXPERIMENT_SCHEMA_V11 = DATA / "experiment-receipt-v1.1.schema.json"
VERSION_MISMATCH_RESULTS = {"inconclusive", "execution_failed"}
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


def validate_experiment_receipt(receipt: dict[str, Any], request: dict[str, Any], *, repo_root: str | Path | None = None) -> list[str]:
    """Check binding and output-file integrity; result remains untrusted and never means admission."""
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
        for item in outputs:
            try:
                path, raw = _validated_file(root, item["path"])
                if not path.is_relative_to((root / "generated-output/frontier").resolve()):
                    errors.append("output artifact is outside generated-output/frontier")
                if _sha(raw) != item.get("contentDigest"):
                    errors.append(f"output artifact digest mismatch: {item.get('label')}")
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"invalid output artifact: {exc}")
    return sorted(set(errors))


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
