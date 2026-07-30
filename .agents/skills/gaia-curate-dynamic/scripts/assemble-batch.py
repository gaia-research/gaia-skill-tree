#!/usr/bin/env python3
"""assemble-batch.py — Assemble 16 review-ready discovery packets into a batch intake JSON.

Reads review-ready packets from registry-for-review/discovery-packets/ and produces
the batch JSON at registry-for-review/skill-batches/.
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone

PACKETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "registry-for-review", "discovery-packets"
)
BATCH_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "registry-for-review", "skill-batches"
)

def is_review_ready(packet):
    lifecycle = packet.get("lifecycle", [])
    return lifecycle and lifecycle[-1] == "review-ready"

def extract_proposed_skill(packet):
    normalized = packet.get("normalized", {})
    evidence = packet.get("evidence", [])

    skill = {
        "id": normalized.get("id", packet.get("candidateId", "unknown")),
        "name": normalized.get("name", "Untitled"),
        "type": normalized.get("type", "basic"),
        "prerequisites": normalized.get("prerequisites", []),
        "description": normalized.get("description", ""),
        "attribution": normalized.get("attribution", {}),
        "evidence": evidence,
        "sourceRepo": "gaia-research/gaia-skill-tree",
        "lifecycle": "pending"
    }
    return skill

def compute_similarity(packets):
    """Compute pairwise similarity based on shared exactDedupe path/URL prefixes."""
    similarities = []
    paths = []
    for path, packet in packets:
        dedupe = packet.get("exactDedupe", {})
        paths.append({
            "candidateId": packet.get("candidateId", "unknown"),
            "repo": dedupe.get("normalizedRepoPath", ""),
            "url": dedupe.get("canonicalUrl", "")
        })

    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            repo_similarity = 0
            url_similarity = 0

            # Shared repo path prefix similarity
            repo_a = paths[i]["repo"]
            repo_b = paths[j]["repo"]
            if repo_a and repo_b:
                common = os.path.commonprefix([repo_a, repo_b])
                repo_similarity = len(common) / max(len(repo_a), len(repo_b), 1)

            # Shared URL prefix similarity
            url_a = paths[i]["url"]
            url_b = paths[j]["url"]
            if url_a and url_b:
                common = os.path.commonprefix([url_a, url_b])
                url_similarity = len(common) / max(len(url_a), len(url_b), 1)

            score = round((repo_similarity + url_similarity) / 2, 2)
            if score > 0:
                similarities.append({
                    "sourceSkillId": paths[i]["candidateId"],
                    "targetSkillId": paths[j]["candidateId"],
                    "score": score,
                    "reason": "shared path/URL prefix"
                })

    return similarities

def main():
    # Allow overriding directories via CLI args
    packets_dir = PACKETS_DIR
    batch_dir = BATCH_DIR
    run_id = "trending-16-seeds-001"

    args = sys.argv[1:]
    if "--packets-dir" in args:
        idx = args.index("--packets-dir")
        if idx + 1 < len(args):
            packets_dir = args[idx + 1]
    if "--output-dir" in args:
        idx = args.index("--output-dir")
        if idx + 1 < len(args):
            batch_dir = args[idx + 1]
    if "--run-id" in args:
        idx = args.index("--run-id")
        if idx + 1 < len(args):
            run_id = args[idx + 1]

    os.makedirs(batch_dir, exist_ok=True)

    pattern = os.path.join(packets_dir, "discovery-packet-*.json")
    files = sorted(glob.glob(pattern))

    review_ready = []
    for path in files:
        with open(path, "r") as f:
            packet = json.load(f)
        if is_review_ready(packet):
            review_ready.append((path, packet))

    print(f"Found {len(review_ready)} review-ready packet(s) in {packets_dir}")

    # Build proposedSkills array
    proposed_skills = []
    for path, packet in review_ready:
        skill = extract_proposed_skill(packet)
        proposed_skills.append(skill)

    # Compute similarity
    similarity = compute_similarity(review_ready)

    # Build batch ID
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    batch_id = f"{timestamp}-{run_id}"

    batch = {
        "batchId": batch_id,
        "userId": "gaia-curate-dynamic",
        "sourceRepo": "gaia-research/gaia-skill-tree",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "fromFile": True,
        "proposedSkills": proposed_skills,
        "similarity": similarity
    }

    output_path = os.path.join(batch_dir, f"{batch_id}.json")
    with open(output_path, "w") as f:
        json.dump(batch, f, indent=2, sort_keys=True)

    print()
    print("=" * 60)
    print("BATCH ASSEMBLY COMPLETE")
    print("=" * 60)
    print(f"  Batch ID:        {batch_id}")
    print(f"  Skills in batch: {len(proposed_skills)}")
    print(f"  Output file:     {output_path}")
    print(f"  Similarity pairs: {len(similarity)}")
    print()

    # Print summary of each skill
    for i, skill in enumerate(proposed_skills, 1):
        print(f"  [{i}] {skill['id']} ({skill['type']}) — {skill['name']}")
        print(f"      evidence: {len(skill['evidence'])} entries, grade {max((e['grade'] for e in skill['evidence']), default='N/A')}")

if __name__ == "__main__":
    main()
