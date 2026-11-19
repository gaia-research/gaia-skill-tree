"""Repository-envelope wire protocol. Source-local, not a registry/trust schema.

Envelope v2 uses payloadVersion=3 to distinguish the old single-named batch v2.
There is deliberately no migration executor and no approval field in this format.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from urllib.parse import quote, urlsplit

from scripts.upstream_watcher.approval import PayloadError, canonical_hash, extract_payload
from scripts.upstream_watcher.finder import resolve_suite_source

FORMAT = "gaia-upstream-repository"
VERSION = 2
MAX_FINDINGS = 256
MAX_ROWS = 4096
MAX_BODY = 60_000
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")


def repository(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise PayloadError("invalid repository identity")
    return value.lower()


def release_repository(source, version):
    """Exact GitHub release source, never a prefix/host/query/path injection."""
    if not isinstance(source, str) or not isinstance(version, str) or not version:
        raise PayloadError("release source/version missing")
    if any(ord(c) < 32 or ord(c) == 127 for c in source + version):
        raise PayloadError("control characters in release identity")
    parts = urlsplit(source)
    segments = parts.path.split("/")
    if (parts.scheme != "https" or parts.netloc.lower() != "github.com"
            or parts.query or parts.fragment or len(segments) != 6
            or segments[3:5] != ["releases", "tag"]
            or segments[5] != quote(version, safe="")):
        raise PayloadError("release source must name the exact approved tag")
    return repository("/".join(segments[1:3]))


def authority_repository(identifier, authority):
    # Canonical named IDs are case-sensitive. Repository comparison alone folds case.
    if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
        raise PayloadError("invalid canonical named identity")
    meta = authority.get(identifier)
    if not isinstance(meta, dict) or meta.get("id") != identifier:
        raise PayloadError("named identity is not in registry authority")
    try:
        resolved = resolve_suite_source(meta)
    except Exception as exc:
        raise PayloadError("registry release authority cannot be resolved") from exc
    if resolved is None:
        raise PayloadError("registry has no release authority")
    return repository("/".join(resolved[:2]))


def validate_named(payload, repo, authority, *, digest=True, mutation_scope=True):
    if not isinstance(payload, dict):
        raise PayloadError("named finding is not an object")
    identifier = payload.get("skillId")
    if authority_repository(identifier, authority) != repo:
        raise PayloadError("named finding belongs to a different release repository")
    if release_repository(payload.get("sourceUrl"), payload.get("newVersion")) != repo:
        raise PayloadError("named source disagrees with envelope repository")
    modes = {"components", "version-only"} if digest else {"components", "version-only", "bootstrap"}
    if not isinstance(payload.get("mode"), str) or payload["mode"] not in modes:
        raise PayloadError("invalid named finding mode")
    if digest and (type(payload.get("payloadVersion")) is not int or payload["payloadVersion"] != 2):
        raise PayloadError("invalid named finding wire version")
    for key in ("releasedAt", "newVersion"):
        value = payload.get(key)
        if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 for c in value):
            raise PayloadError(f"invalid {key}")
    for key in ("componentAdds", "componentRemoves", "linkLiveness", "nameDrift", "candidates"):
        if not isinstance(payload.get(key, []), list):
            raise PayloadError(f"invalid {key}")
    for key in ("componentAdds", "componentRemoves"):
        values = payload.get(key, [])
        if (not all(isinstance(v, str) and v and not any(c.isspace() or ord(c) < 32 for c in v) for v in values)
                or len(values) != len(set(values))):
            raise PayloadError(f"duplicate or malformed {key}")
    components = set(authority[identifier].get("suiteComponents") or [])
    if mutation_scope and not set(payload.get("componentRemoves", [])) <= components:
        raise PayloadError("component removal is outside the selected named scope")
    if mutation_scope and any((authority.get(identifier) or {}).get("suiteComponents")
                              for identifier in payload.get("componentRemoves", [])):
        raise PayloadError("a selected finding cannot mutate another named suite root")
    if payload.get("findingType") not in (None, "update", "bootstrap"):
        raise PayloadError("unknown named finding type")
    rows = payload.get("candidates", [])
    if len(rows) > MAX_ROWS or "candidateRecords" in payload or "rowStorage" in payload:
        raise PayloadError("named finding must contain full bounded rows when validated")
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or "namedSkillId" in row or "candidateId" in row):
            raise PayloadError("malformed named candidate identity")
        row_repo, separator, slug = row["id"].partition(":")
        key = (row_repo.lower(), slug)
        if not separator or not slug or key in seen:
            raise PayloadError("duplicate named candidate identity")
        seen.add(key)
        if row_repo.lower() != repo:
            raise PayloadError("candidate belongs to another repository")
        if (row.get("slug") != slug or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", slug)
                or not isinstance(row.get("suggestedId"), str) or not IDENTIFIER.fullmatch(row["suggestedId"])
                or not isinstance(row.get("status"), str)
                or row["status"] not in {"new", "tracked", "present", "rejected", "escalated"}
                or not all(isinstance(row.get(k), str) and row[k] and not any(c.isspace() for c in row[k])
                           for k in ("firstSeenVersion", "lastSeenVersion"))):
            raise PayloadError("malformed candidate record fields")
        if mutation_scope:
            first = row.get("firstSeenVersion")
            url = row.get("evidenceUrl")
            if not isinstance(first, str) or not first or not isinstance(url, str):
                raise PayloadError("candidate has no pinned release evidence")
            parts = urlsplit(url)
            path = parts.path.split("/")
            if (parts.scheme != "https" or parts.netloc.lower() != "github.com" or parts.query or parts.fragment
                    or len(path) < 7 or "/".join(path[1:3]).lower() != repo
                    or path[3:5] != ["blob", quote(first, safe="")] or path[-1] != "SKILL.md"):
                raise PayloadError("candidate evidence is not pinned to its own first-seen release source")
        if row.get("child") is not None and (type(row["child"]) is not int or row["child"] < 1):
            raise PayloadError("invalid child identity")
    if digest and payload.get("payloadSha256") != canonical_hash(payload):
        raise PayloadError("named finding digest mismatch")
    return payload


def is_envelope(payload):
    return isinstance(payload, dict) and (payload.get("format") == FORMAT or "envelopeVersion" in payload)


def seal(payload):
    result = copy.deepcopy(payload)
    result["payloadSha256"] = canonical_hash(result)
    return result


def build(repo, findings, authority):
    repo = repository(repo)
    unique = {}
    for finding in findings:
        validate_named(finding, repo, authority)
        identifier = finding["skillId"]
        if identifier in unique and unique[identifier] != finding:
            raise PayloadError("conflicting duplicate named findings")
        unique[identifier] = copy.deepcopy(finding)
    payload = seal({"format": FORMAT, "envelopeVersion": VERSION, "payloadVersion": 3,
                    "repository": repo, "findings": [unique[k] for k in sorted(unique)]})
    validate(payload, authority)
    return payload


def validate(payload, authority, title=None):
    if (not isinstance(payload, dict) or set(payload) != {
            "format", "envelopeVersion", "payloadVersion", "repository", "findings", "payloadSha256"}
            or payload.get("format") != FORMAT or type(payload.get("envelopeVersion")) is not int
            or payload.get("envelopeVersion") != VERSION or type(payload.get("payloadVersion")) is not int
            or payload.get("payloadVersion") != 3):
        raise PayloadError("unknown repository-envelope wire format")
    repo = repository(payload.get("repository"))
    if repo != payload["repository"]:
        raise PayloadError("envelope repository must be normalized")
    findings = payload.get("findings")
    if not isinstance(findings, list) or not 1 <= len(findings) <= MAX_FINDINGS:
        raise PayloadError("invalid envelope findings count")
    identifiers = []
    for finding in findings:
        validate_named(finding, repo, authority)
        identifiers.append(finding["skillId"])
    if identifiers != sorted(set(identifiers)):
        raise PayloadError("duplicate or unordered canonical named identities")
    if payload.get("payloadSha256") != canonical_hash(payload):
        raise PayloadError("repository-envelope digest mismatch")
    if title is not None:
        from scripts.upstream_watcher.evidence import title_suite_and_version
        parsed = title_suite_and_version(title, "release")
        if parsed != (repo, title_version(payload)):
            raise PayloadError("title/repository/envelope disagreement")
    return payload


def title_version(payload):
    # Common release tag is displayed only when every named finding has that tag.
    versions = {f["newVersion"] for f in payload["findings"]}
    return next(iter(versions)) if len(versions) == 1 else "repository-envelope-v2"


def title(payload):
    return f"[upstream] {payload['repository']} → {title_version(payload)}"


def render(payload):
    from scripts.upstream_watcher.batch import payload_block
    body = ("## Upstream repository release findings\n\n" + payload_block(payload)
            + "\n\nApproval is per exact named ID, finding digest and release source. "
            "A repository label alone approves no named finding.\n\n")
    for finding in payload["findings"]:
        body += (f"- `{finding['skillId']}` → `{finding['newVersion']}`; "
                 f"finding SHA-256 `{finding['payloadSha256']}`; {finding['sourceUrl']}\n")
    if len(body) > MAX_BODY:
        raise PayloadError("repository envelope exceeds body budget; no rows may be omitted")
    return body


def layout(payload):
    """Reuse the existing two-phase record generation, with source-local scoped IDs.

    Individual finding digests always cover their FULL rows, independently of a
    sibling's storage generation. The root wire digest covers the compact index
    and the generation. Readers must hydrate and verify before selecting a member.
    """
    from scripts.upstream_watcher import records
    try:
        return payload, render(payload), None
    except PayloadError:
        pass
    compact = copy.deepcopy(payload)
    scoped = []
    for finding in compact["findings"]:
        rows = finding["candidates"]
        for row in rows:
            scoped.append({**row, "id": scope_key(finding["skillId"], row["id"]),
                           "namedSkillId": finding["skillId"], "candidateId": row["id"]})
        finding["candidates"] = [{"id": r["id"], "status": r.get("status"), "child": r.get("child")} for r in rows]
        finding["rowStorage"] = "repository-records-v1"
    if not scoped:
        raise PayloadError("repository envelope exceeds body budget without externalizable rows")
    compact["candidateRecords"] = {"chunks": len(records.chunk_rows(scoped)), "rows": len(scoped),
                                   "sha256": records.rows_digest(scoped)}
    compact = seal(compact)
    # Render every chunk BEFORE the first write, preserving existing comment limits.
    for index, chunk in enumerate(records.chunk_rows(scoped), 1):
        records.render_chunk(compact["candidateRecords"]["sha256"], index,
                             compact["candidateRecords"]["chunks"], chunk)
    return compact, render(compact), scoped


def read(body, authority, *, title_text=None, comments=None):
    """Validate inline or hydrate a compact generation; never trust an index alone."""
    from scripts.upstream_watcher import records
    payload, _ = extract_payload(body)
    if "candidateRecords" not in payload:
        return validate(payload, authority, title_text)
    expected = {"format", "envelopeVersion", "payloadVersion", "repository", "findings", "payloadSha256", "candidateRecords"}
    if (set(payload) != expected or payload.get("format") != FORMAT
            or type(payload.get("envelopeVersion")) is not int or payload.get("envelopeVersion") != VERSION
            or type(payload.get("payloadVersion")) is not int or payload.get("payloadVersion") != 3
            or payload.get("payloadSha256") != canonical_hash(payload)):
        raise PayloadError("malformed compact repository envelope")
    ref = payload["candidateRecords"]
    if (not isinstance(ref, dict) or set(ref) != {"chunks", "rows", "sha256"}
            or type(ref.get("chunks")) is not int or type(ref.get("rows")) is not int
            or not 1 <= ref["rows"] <= MAX_ROWS * MAX_FINDINGS
            or ref["chunks"] != (ref["rows"] + records.ROWS_PER_CHUNK - 1) // records.ROWS_PER_CHUNK
            or not isinstance(ref.get("sha256"), str) or not SHA.fullmatch(ref["sha256"])):
        raise PayloadError("malformed repository record reference")
    if comments is None:
        raise PayloadError("repository records must be read before named selection")
    rows = records.read_rows(comments, ref)
    by_name = {}
    for row in rows:
        identifier, candidate = row.get("namedSkillId"), row.get("candidateId")
        if (not isinstance(identifier, str) or not isinstance(candidate, str)
                or row.get("id") != scope_key(identifier, candidate)):
            raise PayloadError("record row does not bind an exact named candidate")
        full = {k: v for k, v in row.items() if k not in {"namedSkillId", "candidateId"}}
        full["id"] = candidate
        by_name.setdefault(identifier, []).append(full)
    expanded = copy.deepcopy(payload)
    expanded.pop("candidateRecords")
    if not isinstance(expanded.get("findings"), list) or not 1 <= len(expanded["findings"]) <= MAX_FINDINGS:
        raise PayloadError("compact findings must be a bounded list")
    for finding in expanded["findings"]:
        if (not isinstance(finding, dict) or not isinstance(finding.get("skillId"), str)
                or finding.pop("rowStorage", None) != "repository-records-v1"):
            raise PayloadError("compact named finding has no recognized row storage")
        full_rows = by_name.pop(finding.get("skillId"), [])
        index = [{"id": r["id"], "status": r.get("status"), "child": r.get("child")} for r in full_rows]
        if finding.get("candidates") != index:
            raise PayloadError("named candidate index does not match scoped record rows")
        finding["candidates"] = full_rows
    if by_name:
        raise PayloadError("record generation contains an unclaimed named identity")
    expanded = seal(expanded)
    return validate(expanded, authority, title_text)


def scope_key(identifier, candidate):
    """Unambiguous composite identity for receipts/journals, not string concatenation."""
    return json.dumps([identifier, candidate], separators=(",", ":"), ensure_ascii=False)


def select(body, authority, *, identifier, digest, source, title_text=None, comments=None):
    payload = read(body, authority, title_text=title_text, comments=comments)
    if not isinstance(digest, str) or not SHA.fullmatch(digest):
        raise PayloadError("an explicit named finding digest is required")
    selected = [f for f in payload["findings"] if f["skillId"] == identifier]
    if len(selected) != 1 or selected[0]["payloadSha256"] != digest or selected[0]["sourceUrl"] != source:
        raise PayloadError("missing, stale or conflicting named approval selector")
    return copy.deepcopy(selected[0]), digest


def migration_plan(issue, payload, current_authority, historical_authority, policy):
    """Lossless reference-only plan. Never returns execution or approval authority.

    Legacy facts are validated against current OR independently pinned historical
    authority. Every new plan binds exact raw API body bytes. Neither historical
    validation nor the policy record grants migration execution authority.
    """
    from scripts.upstream_watcher.evidence import title_suite_and_version
    body = issue.get("body")
    if not isinstance(body, str) or not isinstance(payload, dict) or is_envelope(payload):
        raise PayloadError("legacy payload is missing or malformed")
    labels = {v.get("name") if isinstance(v, dict) else v for v in issue.get("labels", [])}
    kind = "bootstrap" if "upstream:bootstrap" in labels else "release"
    parsed = title_suite_and_version(issue.get("title", ""), kind)
    if not parsed:
        raise PayloadError("legacy title is malformed")
    repo = release_repository(payload.get("sourceUrl"), payload.get("newVersion"))
    expected_title_identity = str(payload.get("skillId", "")).lower() if kind == "bootstrap" else repo
    if parsed != (expected_title_identity, payload["newVersion"]):
        raise PayloadError("legacy source/title disagreement")
    if payload.get("payloadVersion") is not None and (
            type(payload["payloadVersion"]) is not int or payload["payloadVersion"] not in (1, 2)):
        raise PayloadError("unknown legacy payload version")
    if "payloadSha256" in payload and payload["payloadSha256"] != canonical_hash(payload):
        raise PayloadError("legacy digest mismatch")
    identifier = payload.get("skillId")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    try:
        current_repo = authority_repository(identifier, current_authority)
    except PayloadError:
        current_repo = None
    validation_authority = current_authority
    if current_repo != repo:
        # No foreign-ID allowlist and no hash normalization: prove the named
        # association against a pinned historical registry snapshot. A fresh
        # reference plan is not an approval to change this historical record.
        if authority_repository(identifier, historical_authority) != repo:
            raise PayloadError("unverifiable legacy claimed target")
        validation_authority = historical_authority
    # Full inline legacy facts must be well shaped too. A valid compact records
    # index is retained by reference; its historical generation is never rewritten.
    inline = {k: v for k, v in payload.items() if k != "candidateRecords"}
    if "candidateRecords" in payload:
        ref = payload["candidateRecords"]
        if (not isinstance(ref, dict) or not isinstance(ref.get("sha256"), str)
                or not SHA.fullmatch(ref["sha256"]) or type(ref.get("chunks")) is not int
                or type(ref.get("rows")) is not int or ref["chunks"] < 1 or ref["rows"] < 1):
            raise PayloadError("malformed legacy record reference")
        inline["candidates"] = []
    validate_named(inline, repo, validation_authority, digest=False, mutation_scope=False)
    for key in ("componentAdds", "componentRemoves", "linkLiveness", "nameDrift", "candidates"):
        if not isinstance(payload.get(key, []), list):
            raise PayloadError("malformed legacy finding facts")
    plan = {"planVersion": 1, "kind": "preserve-legacy-reference", "repository": repo,
            "issue": issue["number"], "bodySha256": digest, "bodyHashScheme": "raw_api_utf8",
            "originalPayload": copy.deepcopy(payload), "originalTitle": issue["title"],
            "legacyNamedId": identifier, "legacyKind": kind, "currentReleaseRepository": current_repo,
            "policySha256": canonical_hash(policy), "writeReadiness": False,
            "hold": "separate-migration-approval-required",
            "deploymentOrder": ["deploy envelope-aware readers with legacy writes held",
                                "independently review lossless body/records/journal migration plan",
                                "obtain separate issue/scope/hash-bound migration approval",
                                "execute separately authorized migration; revalidate all readers"]}
    # The complete immutable original body is referenced by hash, not echoed into
    # reports. originalPayload preserves processed/carry-forward facts exactly.
    return seal(plan)


def verify_migration_reference(plan, issue):
    """Revalidate a saved reference without authorizing any operation.

    No alternate framing, newline normalization or policy receipt can satisfy a
    raw-body binding. A changed body requires a NEW independently reviewed plan.
    """
    if (not isinstance(plan, dict) or plan.get("planVersion") != 1
            or plan.get("bodyHashScheme") != "raw_api_utf8"
            or plan.get("writeReadiness") is not False
            or plan.get("payloadSha256") != canonical_hash(plan)
            or issue.get("number") != plan.get("issue")
            or not isinstance(issue.get("body"), str)
            or hashlib.sha256(issue["body"].encode("utf-8")).hexdigest() != plan.get("bodySha256")):
        raise PayloadError("legacy migration reference is stale or unverifiable")
    return True
