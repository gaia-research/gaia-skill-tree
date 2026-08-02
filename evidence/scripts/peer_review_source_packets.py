from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from typing import Any, Iterable
from urllib.parse import urlparse

from evidence_type_partitions import normalizeEvidenceType, typeOutputPath

PACKET_CONTRACT_VERSION = "ev-peer-review-source-packet-v1"
MANIFEST_CONTRACT_VERSION = "ev-peer-review-source-manifest-v1"
FORBIDDEN_STRENGTH_FIELDS = {
    "trustNumber",
    "grade",
    "class",
    "tier",
    "level",
    "stars",
    "rank",
}
SKILL_ID_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")


def loadManifest(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    contractVersion = data.get("contractVersion")
    if contractVersion not in {PACKET_CONTRACT_VERSION, MANIFEST_CONTRACT_VERSION}:
        raise ValueError(
            "contractVersion must be "
            f"{PACKET_CONTRACT_VERSION!r} or {MANIFEST_CONTRACT_VERSION!r}"
        )
    return data


def iterPackets(manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
    contractVersion = manifest.get("contractVersion")
    if contractVersion == PACKET_CONTRACT_VERSION:
        yield manifest
        return
    if contractVersion != MANIFEST_CONTRACT_VERSION:
        raise ValueError(f"unsupported contractVersion: {contractVersion!r}")
    packets = manifest.get("packets")
    if not isinstance(packets, list):
        raise ValueError("manifest packets must be a list")
    for index, packet in enumerate(packets, start=1):
        if not isinstance(packet, dict):
            raise ValueError(f"packets[{index}] must be an object")
        yield packet


def _findForbiddenFields(node: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            childPath = f"{path}.{key}"
            if key in FORBIDDEN_STRENGTH_FIELDS:
                hits.append(childPath)
            hits.extend(_findForbiddenFields(value, childPath))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            hits.extend(_findForbiddenFields(value, f"{path}[{index}]"))
    return hits


def _isAbsoluteHttpUrl(raw: Any) -> bool:
    if not isinstance(raw, str) or not raw.strip():
        return False
    parsed = urlparse(raw)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _validateSkillId(raw: Any) -> str:
    if not isinstance(raw, str) or not SKILL_ID_RE.fullmatch(raw.strip()):
        raise ValueError("target skillId must use contributor/skill format")
    return raw.strip()


def validatePacket(packet: dict[str, Any]) -> None:
    forbiddenHits = _findForbiddenFields(packet)
    if forbiddenHits:
        joined = ", ".join(sorted(forbiddenHits))
        raise ValueError(f"packet contains forbidden strength fields: {joined}")

    if packet.get("contractVersion") != PACKET_CONTRACT_VERSION:
        raise ValueError(f"packet contractVersion must be {PACKET_CONTRACT_VERSION!r}")

    evidenceType = packet.get("evidenceType")
    if evidenceType != "peer-review":
        raise ValueError("packet evidenceType must be exactly 'peer-review'")
    normalizeEvidenceType(evidenceType)

    source = packet.get("source")
    if not isinstance(source, dict):
        raise ValueError("packet source must be an object")
    if not _isAbsoluteHttpUrl(source.get("url")):
        raise ValueError("source.url must be an absolute http(s) URL")

    reviewers = source.get("reviewers")
    if not isinstance(reviewers, int) or isinstance(reviewers, bool) or reviewers < 1:
        raise ValueError("source.reviewers must be an integer >= 1")

    targets = packet.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("packet targets must be a non-empty list")

    seen: set[tuple[str, str, str]] = set()
    sourceUrl = source["url"].strip()
    for index, target in enumerate(targets, start=1):
        if not isinstance(target, dict):
            raise ValueError(f"targets[{index}] must be an object")
        skillId = _validateSkillId(target.get("skillId"))
        key = (sourceUrl, skillId, evidenceType)
        if key in seen:
            raise ValueError(
                "packet must contain at most one row per "
                "(source.url, skillId, evidenceType)"
            )
        seen.add(key)


def expandPacket(packet: dict[str, Any]) -> list[dict[str, Any]]:
    validatePacket(packet)
    source = dict(packet["source"])
    sourceUrl = source["url"].strip()
    packetId = packet.get("id")
    rows: list[dict[str, Any]] = []
    for target in packet["targets"]:
        skillId = target["skillId"].strip()
        contributor, _, skillSlug = skillId.partition("/")
        rows.append(
            {
                "skillId": skillId,
                "name": target.get("name") or skillSlug,
                "contributor": contributor,
                "primaryRepo": target.get("primaryRepo"),
                "packetId": packetId,
                "evidenceType": "peer-review",
                "source": sourceUrl,
                "date": source.get("date", "unknown"),
                "title": source.get("title"),
                "author": source.get("author"),
                "reviewers": source.get("reviewers"),
                "independence": source.get("independence"),
                "genericSkillRef": target.get("genericSkillRef"),
                "attributionScope": target.get("attributionScope"),
                "confidence": target.get("confidence"),
                "notes": target.get("notes"),
            }
        )
    return rows


def _formatOptionalLine(label: str, value: Any, *, code: bool = False) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    wrapped = f"`{text}`" if code else text
    return f"- **{label}:** {wrapped}\n"


def writePeerReviewPartition(byTypeDir: str, rows: list[dict[str, Any]]) -> str:
    outputPath = typeOutputPath(byTypeDir, "peer-review")
    os.makedirs(os.path.dirname(outputPath), exist_ok=True)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["skillId"]].append(row)

    with open(outputPath, "w", encoding="utf-8") as f:
        f.write("# Evidence Sources: peer-review\n\n")
        f.write(
            "This scratch type-first partition materializes peer-review source "
            "packets for temporary ev-pipeline work. A legitimate review URL may "
            "appear once per named skill when the same source independently "
            "reviews each target.\n\n"
        )
        for skillId in sorted(grouped):
            skillRows = sorted(
                grouped[skillId],
                key=lambda row: (
                    str(row.get("source") or ""),
                    str(row.get("packetId") or ""),
                    str(row.get("genericSkillRef") or ""),
                ),
            )
            first = skillRows[0]
            f.write(f"## Skill: `{skillId}`\n")
            f.write(f"- **Name:** {first.get('name', 'N/A')}\n")
            f.write(f"- **Contributor:** `{first.get('contributor', 'N/A')}`\n")
            primaryRepo = first.get("primaryRepo")
            if primaryRepo:
                f.write(f"- **Primary GitHub Repository:** [{primaryRepo}]({primaryRepo})\n")
            f.write("\n### Evidence Rows:\n\n")
            for index, row in enumerate(skillRows, start=1):
                f.write(f"#### E{index}: `peer-review`\n")
                f.write(f"- **Source:** [{row['source']}]({row['source']})\n")
                f.write(f"- **Date:** {row.get('date', 'unknown')}\n")
                f.write(_formatOptionalLine("Title", row.get("title")))
                f.write(_formatOptionalLine("Author", row.get("author")))
                f.write(f"- **Reviewers:** {row['reviewers']}\n")
                f.write(_formatOptionalLine("Independence", row.get("independence")))
                f.write(_formatOptionalLine("Packet ID", row.get("packetId"), code=True))
                f.write(
                    _formatOptionalLine(
                        "Generic Skill Ref", row.get("genericSkillRef"), code=True
                    )
                )
                if row.get("attributionScope"):
                    f.write(f"- **Scope:** {row['attributionScope']}\n")
                f.write(_formatOptionalLine("Confidence", row.get("confidence")))
                f.write(
                    f"- **Description:** {row.get('notes') or 'No notes.'}\n\n"
                )
            f.write("---\n\n")
    return outputPath


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize a scratch peer-review by-type partition from a packet manifest."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to a peer-review packet or manifest JSON file",
    )
    parser.add_argument(
        "--by-type-dir",
        required=True,
        help="Output by-type directory for the scratch peer-review.md partition",
    )
    args = parser.parse_args()

    manifest = loadManifest(args.manifest)
    rows: list[dict[str, Any]] = []
    for packet in iterPackets(manifest):
        rows.extend(expandPacket(packet))
    outputPath = writePeerReviewPartition(args.by_type_dir, rows)
    print(f"Wrote {outputPath} with {len(rows)} peer-review row(s).")


if __name__ == "__main__":
    main()
