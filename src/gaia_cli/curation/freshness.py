"""Trusted-boundary freshness checks for discovery-packet-v2 packets.

This module deliberately treats packet snapshots as claims, not trust anchors.
Every unavailable live check is returned as a blocking error.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def _canonical_digest(value):
    from gaia_cli.intakeAdapter import _canonicalDigest
    return _canonicalDigest(value)


def _live_catalog_paths(registry_path):
    """Return available full catalog projections; malformed inputs fail closed."""
    root = Path(registry_path)
    registry = root / "registry"
    paths = []
    nodes = registry / "nodes"
    import json
    if nodes.is_dir():
        rows = []
        try:
            for path in sorted(nodes.rglob("*.json")):
                row = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                    raise ValueError("malformed node")
                rows.append(row)
        except (OSError, ValueError, json.JSONDecodeError):
            paths.append(("registry/nodes", None))
        else:
            paths.append(("registry/nodes", rows))
    for label, path in (("registry/gaia.json", registry / "gaia.json"), ("docs/graph/gaia.json", root / "docs/graph/gaia.json")):
        if path.is_file():
            try:
                graph = json.loads(path.read_text(encoding="utf-8"))
                rows = graph.get("skills")
                if not isinstance(rows, list):
                    raise ValueError("malformed catalog")
                paths.append((label, rows))
            except (OSError, ValueError, json.JSONDecodeError):
                paths.append((label, None))
    return paths


def sameGenericSnapshot(left, right) -> bool:
    """Compare catalog substance, not capture timestamps or retrieval metadata."""
    return isinstance(left, dict) and isinstance(right, dict) and all(
        left.get(key) == right.get(key)
        for key in ("command", "generics", "contentSha256", "semanticGenerics", "semanticCatalogSha256")
    )


def verifyPacketFreshness(packet, registryPath='.', fetcher=None) -> list[str]:
    """Independently verify live generic catalog and source freshness."""
    import json
    errors = []
    if not isinstance(packet, dict):
        return ["packet is not an object"]
    snapshot = packet.get("genericSnapshot")
    if not isinstance(snapshot, dict):
        errors.append("generic snapshot unavailable")
    else:
        try:
            from gaia_cli.curation.assessment import loadGenericSemantics
            semantics = loadGenericSemantics(registryPath)
        except (OSError, ValueError, json.JSONDecodeError):
            semantics = None
            errors.append("live generic catalog unavailable or malformed")
        catalogs = _live_catalog_paths(registryPath)
        if not catalogs or not any(rows is not None for _, rows in catalogs):
            if semantics is None:
                errors.append("live generic catalog unavailable")
        for name, rows in catalogs:
            if rows is None:
                errors.append(f"live generic catalog unreadable: {name}")
        generics = snapshot.get("generics")
        if not isinstance(generics, list):
            generics = []
            errors.append("generic snapshot is malformed")
        if snapshot.get("contentSha256") != _canonical_digest(generics):
            errors.append("generic snapshot digest mismatch")
        if semantics is not None:
            ids = {row["id"] for row in generics if isinstance(row, dict) and isinstance(row.get("id"), str)}
            live_ids = {key for key, row in semantics.items() if "/" not in key}
            expected_generics = [{"id": key, "name": semantics[key].get("name"), "kind": "generic"} for key in sorted(live_ids)]
            # Compare exact canonical projection, not only identity membership.
            if generics != expected_generics:
                errors.append("generic snapshot is stale")
            selected = {str(item.get("genericId")) for item in packet.get("mappingOptions", []) if isinstance(item, dict)}
            semantic_snapshot = snapshot.get("semanticGenerics")
            if not isinstance(semantic_snapshot, dict):
                errors.append("generic semantic snapshot unavailable")
            else:
                expected_selected = {key: semantics[key] for key in sorted(selected) if key in semantics}
                if set(selected) != set(expected_selected) or any(semantic_snapshot.get(key) != value for key, value in expected_selected.items()):
                    errors.append("selected generic semantic definition is stale")
            if snapshot.get("semanticCatalogSha256") != _canonical_digest(semantics):
                errors.append("generic semantic catalog is stale")
            # Generated catalogs, when present, must agree on canonical definitions.
            for name, rows in catalogs:
                if rows is None:
                    continue
                projected = {}
                for row in rows:
                    rid = row.get("id")
                    if isinstance(rid, str) and "/" not in rid:
                        projected[rid] = {k: row.get(k) for k in ("id", "name", "description", "type")}
                        projected[rid]["prerequisites"] = sorted(row.get("prerequisites", []))
                canonical = {key: semantics[key] for key in semantics if "/" not in key}
                if projected != canonical:
                    errors.append(f"live generic catalogs disagree: {name}")

    source = packet.get("source")
    source = source if isinstance(source, dict) else {}
    url, expected = source.get("canonicalUrl"), source.get("contentSha256")
    if not isinstance(url, str) or not isinstance(expected, str) or not expected:
        errors.append("source URL or content digest unavailable")
    else:
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
            pieces = url.split("/blob/", 1)
            if len(pieces) != 2:
                errors.append("source revision cannot be bound to canonical URL")
            else:
                url_revision = pieces[1].split("/", 1)[0]
                if len(revision) >= 7 and all(c in "0123456789abcdefABCDEF" for c in revision) and url_revision != revision:
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
        proof = _proveExactNamedDuplicate(registryPath, packet.get("candidateId"), source.get("canonicalUrl"), source.get("hostRepository"), source.get("contentSha256"), fetcher=fetcher)
        if proof.get("checked") is not True:
            errors.append("exact-dedupe verification unavailable")
        if isinstance(dedupe, dict) and (dedupe.get("matched") != proof.get("matched") or dedupe.get("namedIdentity") != proof.get("namedIdentity")):
            errors.append("exact-dedupe proof is stale against canonical named identities")
    if isinstance(dedupe, dict) and dedupe.get("matched"):
        if not all(dedupe.get(key) == source.get(src_key) for key, src_key in (("canonicalUrl", "canonicalUrl"), ("contentSha256", "contentSha256"), ("hostRepository", "hostRepository"))):
            errors.append("exact-dedupe proof does not match packet source")
        if not isinstance(dedupe.get("namedIdentity"), str) or "/" not in dedupe["namedIdentity"]:
            errors.append("exact-dedupe proof lacks canonical named identity")
    return errors
