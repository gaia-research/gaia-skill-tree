"""Trusted-boundary freshness checks for discovery-packet-v2 packets.

This module deliberately treats packet snapshots as claims, not trust anchors.
Every unavailable live check is returned as a blocking error.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _canonical_digest(value):
    from gaia_cli.intakeAdapter import _canonicalDigest
    return _canonicalDigest(value)


def _generic_ids(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if "skills" in data:
        rows = data.get("skills")
    else:
        rows = [row for bucket in (data.get("buckets") or {}).values() for row in bucket]
    if not isinstance(rows, list):
        return None
    return sorted({row["id"] for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"].strip()})


def _live_catalog_paths(registry_path):
    root = Path(registry_path)
    registry = root / "registry"
    paths = []
    nodes = registry / "nodes"
    if nodes.is_dir():
        ids = []
        readable = True
        for path in sorted(nodes.rglob("*.json")):
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                readable = False
                break
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                readable = False
                break
            ids.append(row["id"])
        paths.append(("registry/nodes", sorted(set(ids)) if readable else None))
    for label, path in (
        ("registry/gaia.json", registry / "gaia.json"),
        ("docs/graph/gaia.json", root / "docs" / "graph" / "gaia.json"),
    ):
        if path.is_file():
            ids = _generic_ids(path)
            if ids is None:
                paths.append((label, None))
            else:
                paths.append((label, ids))
    return paths


def verifyPacketFreshness(packet, registryPath='.', fetcher=None) -> list[str]:
    """Independently verify live generic catalog and source freshness.

    Returns blocking diagnostics. Missing snapshots, inaccessible sources,
    malformed timestamps, catalog drift, or source digest mismatch fail closed.
    ``fetcher`` has the same ``url -> bytes|str`` contract as prefill.
    """
    errors = []
    if not isinstance(packet, dict):
        return ["packet is not an object"]
    snapshot = packet.get("genericSnapshot")
    if not isinstance(snapshot, dict):
        errors.append("generic snapshot unavailable")
    else:
        paths = _live_catalog_paths(registryPath)
        known = [(name, ids) for name, ids in paths if ids is not None]
        if not known:
            errors.append("live generic catalog unavailable")
        else:
            baseline_name, baseline = known[0]
            for name, ids in paths:
                if ids is None:
                    errors.append(f"live generic catalog unreadable: {name}")
                elif ids != baseline:
                    errors.append(f"live generic catalogs disagree: {baseline_name} vs {name}")
            snapshot_ids = sorted({row.get("id") for row in snapshot.get("generics", []) if isinstance(row, dict) and isinstance(row.get("id"), str)})
            if snapshot_ids != baseline:
                errors.append("generic snapshot is stale")
            if snapshot.get("contentSha256") != _canonical_digest(snapshot.get("generics", [])):
                errors.append("generic snapshot digest mismatch")

    source = packet.get("source")
    source = source if isinstance(source, dict) else {}
    url = source.get("canonicalUrl")
    expected = source.get("contentSha256")
    if not isinstance(url, str) or not isinstance(expected, str) or not expected:
        errors.append("source URL or content digest unavailable")
    else:
        # Import lazily to avoid a module cycle; a fetch failure returns no bytes.
        from gaia_cli.prefill import fetchCandidateSource
        host, _raw_url, content, digest = fetchCandidateSource(url, fetcher=fetcher)
        if content is None or digest is None:
            errors.append("source freshness verification unavailable")
        elif digest != expected:
            errors.append("source content digest mismatch (stale snapshot)")
        elif isinstance(source.get("hostRepository"), str) and host != source.get("hostRepository"):
            errors.append("source origin mismatch")
        revision = source.get("revision") or source.get("commitSha")
        if revision:
            # Revision-bearing URLs are immutable inputs; confirm the claimed
            # revision appears as the URL's branch component when SHA-shaped.
            pieces = url.split("/blob/", 1)
            if len(pieces) != 2:
                errors.append("source revision cannot be bound to canonical URL")
            else:
                url_revision = pieces[1].split("/", 1)[0]
                if len(revision) >= 7 and all(c in "0123456789abcdefABCDEF" for c in revision):
                    if url_revision != revision:
                        errors.append("source revision is stale or does not match canonical URL")
    fetched_at = source.get("fetchedAt")
    if not isinstance(fetched_at, str):
        errors.append("source fetchedAt unavailable")
    else:
        try:
            timestamp = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError("timezone missing")
            if timestamp > datetime.now(timezone.utc):
                errors.append("source fetchedAt is in the future")
        except (ValueError, TypeError):
            errors.append("source fetchedAt is invalid")

    dedupe = packet.get("exactDedupe")
    if "deduped" in packet.get("lifecycle", []) and (not isinstance(dedupe, dict) or dedupe.get("checked") is not True):
        errors.append("deduped lifecycle lacks executed exact-dedupe check")
    if "deduped" in packet.get("lifecycle", []) and isinstance(source.get("contentSha256"), str):
        from gaia_cli.prefill import _proveExactNamedDuplicate
        live_proof = _proveExactNamedDuplicate(
            registryPath, packet.get("candidateId"), source.get("canonicalUrl"),
            source.get("hostRepository"), source.get("contentSha256"), fetcher=fetcher,
        )
        if isinstance(dedupe, dict) and (
            dedupe.get("matched") != live_proof.get("matched")
            or dedupe.get("namedIdentity") != live_proof.get("namedIdentity")
        ):
            errors.append("exact-dedupe proof is stale against canonical named identities")
    if isinstance(dedupe, dict) and dedupe.get("matched"):
        if not all(dedupe.get(key) == source.get(src_key) for key, src_key in (("canonicalUrl", "canonicalUrl"), ("contentSha256", "contentSha256"), ("hostRepository", "hostRepository"))):
            errors.append("exact-dedupe proof does not match packet source")
        if not isinstance(dedupe.get("namedIdentity"), str) or "/" not in dedupe["namedIdentity"]:
            errors.append("exact-dedupe proof lacks canonical named identity")
    return errors
