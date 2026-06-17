"""Quick audit helper. Not committed long-term."""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

DIR = os.path.dirname(os.path.abspath(__file__))


def loadProposal(stance):
    with open(os.path.join(DIR, stance + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


for stance in ["P1-strict-S", "P2-attainable-S", "P3-fusion-heavy", "P4-community-heavy"]:
    p = loadProposal(stance)
    print("=== " + stance + " ===")
    print(f"  thresholds: {p.get('thresholds')}")
    print(f"  formulaTuning keys: {list((p.get('formulaTuning') or {}).keys())}")
    cal = p.get("calibrationTable", [])
    apexSkills = [
        c for c in cal
        if "6" in str(c.get("currentRank", ""))
        or "apex" in str(c.get("currentRank", "")).lower()
        or "mattpocock" in str(c.get("skillId", ""))
        or "ruflo" in str(c.get("skillId", ""))
    ]
    print(f"  apex/6-star calibration rows ({len(apexSkills)}):")
    for c in apexSkills[:6]:
        print(
            f"    {c.get('skillId')} | {c.get('currentRank')} -> TM {c.get('proposedTrustMagnitude')} "
            f"{c.get('proposedOverallGrade')} drift={c.get('driftDirection')}"
        )
        rat = c.get("rationale", "")
        if rat:
            print(f"      rationale: {rat[:280]}")
    closedVecs = p.get("gameabilityClosed") or []
    openedVecs = p.get("gameabilityOpened") or []
    print(f"  gameabilityClosed ({len(closedVecs)}):")
    for g in closedVecs[:5]:
        print(f"    - {g[:200]}")
    print(f"  gameabilityOpened ({len(openedVecs)}):")
    for g in openedVecs[:5]:
        print(f"    - {g[:200]}")
    print()
