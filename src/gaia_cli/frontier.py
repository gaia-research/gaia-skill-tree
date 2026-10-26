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
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = Path(__file__).parent / "data" / "frontier" / "challenger-lead-v1.schema.json"
FORBIDDEN_AUTHORITY_FIELDS = {"verified", "verifiedBy", "approvedBy", "verificationReceipt", "confidence", "publicChallengeId", "challengeStatus"}


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
    url = canonical_source_url(data["source"]["url"])
    task = " ".join(data["capability"]["task"].casefold().split())
    target = data["target"]["skillId"].casefold()
    return hashlib.sha256("\0".join((identity, url, task, target)).encode()).hexdigest()


def read_only_handoff(data: dict[str, Any], *, packet_path: str) -> dict[str, Any]:
    """Create a work request for existing Meta/audit workflows, never an admission."""
    errors = validate_lead(data)
    if errors:
        raise ValueError("invalid challenger lead: " + "; ".join(errors))
    return {
        "schemaVersion": "frontier-meta-handoff-v1",
        "leadId": data["leadId"],
        "packetPath": packet_path,
        "leadDisposition": data["disposition"]["status"],
        "targetSkillId": data["target"]["skillId"],
        "requestedWork": ["gaia-meta-audit triage", "gaia-audit focused independent verification"],
        "verification": "unverified-lead",
        "publicChallengeAdmission": "not-requested-until-independent-verification",
        "trustedReceiptIssuer": "unavailable-in-this-lane; fail closed",
        "canonicalMutation": "prohibited",
        "createdAtUTC": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
