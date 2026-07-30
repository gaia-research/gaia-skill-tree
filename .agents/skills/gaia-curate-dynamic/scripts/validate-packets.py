#!/usr/bin/env python3
"""validate-packets.py — Validate discovery packets against discovery-packet-v2 schema.

Validates that each discovery packet in registry-for-review/discovery-packets/
conforms to the discovery-packet-v2 schema and that exactly 16 packets are
in review-ready state.
"""

import glob
import json
import os
import re
import sys

PACKETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "registry-for-review", "discovery-packets"
)
REQUIRED_KEYS = [
    "contractVersion", "candidateId", "lifecycle", "source",
    "normalized", "exactDedupe", "mappingOptions", "decision", "evidence", "flags"
]
LIFECYCLE_TERMINAL = "review-ready"
MIN_DESC_LENGTH = 10

def validate_packet(path):
    errors = []
    basename = os.path.basename(path)

    with open(path, "r") as f:
        try:
            packet = json.load(f)
        except json.JSONDecodeError as e:
            return [f"{basename}: invalid JSON — {e}"]

    # contractVersion check
    if packet.get("contractVersion") != "discovery-packet-v2":
        errors.append(f"{basename}: contractVersion is '{packet.get('contractVersion')}', expected 'discovery-packet-v2'")

    # lifecycle check — must end with review-ready
    lifecycle = packet.get("lifecycle", [])
    if not lifecycle or lifecycle[-1] != LIFECYCLE_TERMINAL:
        errors.append(f"{basename}: lifecycle does not end with '{LIFECYCLE_TERMINAL}' (got {lifecycle[-1] if lifecycle else 'empty'})")

    # evidence check — at least 1 entry with grade B or higher
    evidence = packet.get("evidence", [])
    if not evidence:
        errors.append(f"{basename}: evidence array is empty")
    else:
        valid_grades = {"A", "B", "C"}
        grade_order = {"A": 3, "B": 2, "C": 1}
        has_b_or_higher = any(
            e.get("grade", "C") in valid_grades and grade_order.get(e.get("grade", "C"), 0) >= grade_order["B"]
            for e in evidence
        )
        if not has_b_or_higher:
            errors.append(f"{basename}: evidence has no entry at grade B or higher")

    # normalized.description length
    normalized = packet.get("normalized", {})
    desc = normalized.get("description", "")
    if len(desc) < MIN_DESC_LENGTH:
        errors.append(f"{basename}: normalized.description is {len(desc)} chars, minimum is {MIN_DESC_LENGTH}")

    # normalized.attribution.type
    attribution = normalized.get("attribution", {})
    attr_type = attribution.get("type", "")
    if attr_type != "attributed":
        errors.append(f"{basename}: normalized.attribution.type is '{attr_type}', expected 'attributed'")

    # normalized.id kebab-case
    cid = normalized.get("id", "")
    if cid and not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", cid):
        errors.append(f"{basename}: normalized.id '{cid}' is not valid kebab-case")

    # exactDedupe fields
    dedupe = packet.get("exactDedupe", {})
    for field in ["normalizedRepoPath", "canonicalUrl", "contentHash"]:
        if not dedupe.get(field):
            errors.append(f"{basename}: exactDedupe.{field} is missing or empty")

    return errors

def check_cross_packet_duplicates(packets):
    errors = []
    seen_paths = {}
    seen_urls = {}
    for path, packet in packets:
        basename = os.path.basename(path)
        dedupe = packet.get("exactDedupe", {})
        repo_path = dedupe.get("normalizedRepoPath")
        canonical_url = dedupe.get("canonicalUrl")

        if repo_path:
            if repo_path in seen_paths:
                errors.append(f"{basename}: duplicate normalizedRepoPath '{repo_path}' (also in {seen_paths[repo_path]})")
            else:
                seen_paths[repo_path] = basename

        if canonical_url:
            if canonical_url in seen_urls:
                errors.append(f"{basename}: duplicate canonicalUrl '{canonical_url}' (also in {seen_urls[canonical_url]})")
            else:
                seen_urls[canonical_url] = basename

    return errors

def main():
    # Allow overriding packets directory via CLI arg
    if len(sys.argv) > 1 and "--packets-dir" in sys.argv:
        idx = sys.argv.index("--packets-dir")
        if idx + 1 < len(sys.argv):
            PACKETS_DIR = sys.argv[idx + 1]

    pattern = os.path.join(PACKETS_DIR, "discovery-packet-*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"ERROR: No discovery packets found in {PACKETS_DIR}")
        sys.exit(1)

    print(f"Found {len(files)} discovery packet(s) in {PACKETS_DIR}")
    print()

    all_errors = []
    review_ready_count = 0
    packets_data = []

    for path in files:
        basename = os.path.basename(path)
        with open(path, "r") as f:
            packet = json.load(f)

        lifecycle = packet.get("lifecycle", [])
        is_review_ready = lifecycle and lifecycle[-1] == LIFECYCLE_TERMINAL
        if is_review_ready:
            review_ready_count += 1

        packets_data.append((path, packet))

        packet_errors = validate_packet(path)
        if packet_errors:
            all_errors.extend(packet_errors)
        else:
            print(f"  PASS: {basename}")

    # Cross-packet duplicate check
    dup_errors = check_cross_packet_duplicates(packets_data)
    all_errors.extend(dup_errors)

    print()
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  Total packets:    {len(files)}")
    print(f"  Review-ready:     {review_ready_count}")
    print(f"  Expected:         16")
    print(f"  Packet errors:    {len(all_errors)}")
    print()

    if all_errors:
        print("ERRORS:")
        for err in all_errors:
            print(f"  - {err}")
        print()
        print("RESULT: FAIL")
        sys.exit(1)

    if review_ready_count != 16:
        print(f"WARNING: Expected 16 review-ready packets, found {review_ready_count}")
        print("RESULT: PARTIAL")
        sys.exit(1)

    print("All checks passed.")
    print("RESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
