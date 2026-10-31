#!/usr/bin/env python3
"""Reproducible, preparation-only compiler for the October L4 decisions.

This helper reads the founder's existing choices and original intake inventory,
then optionally invokes only canonical `gaia dev prefill` and `gaia dev assess`.
It never invokes ratify/add/evidence/calibrate/build/docs or writes registry data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "founder/reports/yggdrasil-iv-october-2026"
PREP = REPORT / "l4-preparation"
CHOICE_RE = re.compile(r"^\|\s*`?([^|]+?)`?\s*\|\s*(approve|other|new|decline)\s*\|\s*([^|]*?)\s*\|(?:\s*([^|]*?)\s*\|)?\s*$")
PARKED = [
    ("anthropics/creating-financial-models", "https://github.com/anthropics/claude-cookbooks/blob/main/skills/custom_skills/creating-financial-models/SKILL.md", "#565", "financial-modeling"),
    ("kishorkukreja/inventory-optimization", "https://github.com/kishorkukreja/awesome-supply-chain/blob/main/skills/inventory-optimization/SKILL.md", "#565", "supply-chain-optimization"),
    ("omer-metin/synthetic-data", "https://github.com/omer-metin/skills-for-antigravity/blob/main/skills/synthetic-data/SKILL.md", "#565", "synthetic-data-generation"),
    ("k-dense-ai/pymc", "https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/pymc/SKILL.md", "#565", "probabilistic-programming"),
    ("aj-geddes/causal-inference", "https://github.com/aj-geddes/useful-ai-prompts/blob/main/skills/causal-inference/SKILL.md", "#565", "causal-inference"),
    ("dralgorhythm/compliance", "https://github.com/dralgorhythm/claude-agentic-framework/blob/main/.claude/skills/security/compliance/SKILL.md", "#565", "regulatory-compliance-mapping"),
    ("majiayu000/edge-model-compression", "https://github.com/majiayu000/claude-skill-registry-data/blob/main/ai-ml/edge-model-compression/SKILL.md", "#565", "edge-optimization"),
]
# Topology choices that explicitly select an existing generic or a founder-described new shape.
OTHER_MAPS = {
    "emilkowalski/prototype": ("design-review", "Founder note: same with design shotgun; closest existing generic."),
    "firecrawl/firecrawl-build": ("browser-automation", "Founder note explicitly maps to browser automation."),
    "garrytan/chat-connectors": ("mcp-integration", "Closest existing generic for chat/MCP integrations; founder note preserved."),
    "garrytan/repo-architecture": ("knowledge-management", "Closest existing generic for the source's brain filing/architecture protocol."),
    "garrytan/webhook-transforms": ("workflow-automation", "Closest existing generic for event-triggered transforms; founder note preserved."),
}
NEW = {
    "cis2042/product-design-harness": {"id":"product-design-review", "name":"Product Design Review", "description":"Combines product-design work with structured design review to turn product goals into evaluated interface decisions.", "type":"fusion", "prerequisites":["product-design", "design-review"]},
    "emilkowalski/animation-performance": {"id":"animation-performance", "name":"Animation Performance", "description":"Diagnoses and improves runtime and rendering performance in interactive animations while preserving intended motion behavior.", "type":"fusion", "prerequisites":["performance-tuning", "timeline-animation"]},
    "emilkowalski/break-ui": {"id":"ui-red-teaming", "name":"UI Red Teaming", "description":"Adversarially probes user interfaces for exploitable interaction, accessibility, and resilience failures, combining red-team testing with UI audit.", "type":"fusion", "prerequisites":["red-teaming", "ui-audit"]},
    "garrytan/company-brainify": {"id":"company-knowledge-management", "name":"Company Knowledge Management", "description":"Builds and maintains an internal company knowledge system by combining knowledge management with organization-specific knowledge capture and retrieval.", "type":"fusion", "prerequisites":["knowledge-management", "internal-knowledge"]},
    "garrytan/enrich": {"id":"knowledge-enrichment", "name":"Knowledge Enrichment", "description":"Enriches existing knowledge records with structured context, relationships, and useful metadata while preserving their source meaning.", "type":"basic", "prerequisites":[]},
    "garrytan/frontmatter-guard": {"id":"knowledge-aware-frontend", "name":"Knowledge-Aware Frontend", "description":"Combines frontend implementation with knowledge-management practices so interface changes preserve and expose relevant product knowledge.", "type":"fusion", "prerequisites":["frontend-development", "knowledge-management"]},
    "garrytan/google-loops": {"id":"google-workspace-automation", "name":"Google Workspace Automation", "description":"Automates repeatable workflows across Google Workspace services using connected applications and their native data.", "type":"basic", "prerequisites":[]},
    "garrytan/publish": {"id":"brain-publishing", "name":"Brain Publishing", "description":"Publishes selected knowledge-base content as controlled, shareable pages while preserving access and privacy boundaries.", "type":"basic", "prerequisites":[]},
    "garrytan/query": {"id":"knowledge-query", "name":"Knowledge Query", "description":"Performs focused lookup and retrieval over a knowledge base, returning directly relevant information without broader synthesis or authoring.", "type":"basic", "prerequisites":[]},
    "garrytan/voice-note-ingest": {"id":"voice-knowledge-ingestion", "name":"Voice Knowledge Ingestion", "description":"Turns spoken notes into accurately captured and organized knowledge, combining voice processing with knowledge ingestion.", "type":"fusion", "prerequisites":["voice-agent", "knowledge-harvest"]},
}


def parse_choices():
    campaign = (REPORT / "CAMPAIGN.md").read_text(encoding="utf-8")
    section = campaign.split("## L4 topology choices", 1)[1].split("\n## Founder rulings", 1)[0]
    choices = []
    for line in section.splitlines():
        match = CHOICE_RE.match(line)
        if not match:
            continue
        skill, choice, generic, note = match.groups()
        choices.append({"choiceId": skill.strip(), "founderChoice": choice, "founderGeneric": generic.strip() or None, "founderNote": (note or "").strip() or None})
    if len(choices) != 76:
        raise SystemExit(f"Expected 76 human choice rows, found {len(choices)}")
    return choices


def read_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    try:
        import yaml
        return yaml.safe_load(text[4:end]) or {}
    except Exception:
        return {}


def inventory():
    triage_doc = json.loads((REPORT / "reconciliation/intake-triage.json").read_text(encoding="utf-8"))
    triage = {x.get("skill"): x for x in triage_doc["items"]}
    choices = parse_choices()
    rows = []
    for choice in choices:
        if choice["choiceId"] == "(7 parked drafts)":
            for skill_id, url, issue, generic_id in PARKED:
                rows.append({**choice, "skillId": skill_id, "sourceIssue": issue, "umbrellaIssue": "#564", "sourceUrl": url,
                             "existingGeneric": generic_id, "intakeIdentity": "original parked-draft inventory #565; no individual intake issue or batch id",
                             "oldPacket": None, "oldAssessment": None, "disposition": "skip-existing" if skill_id == "k-dense-ai/pymc" else "approved-source-preparation",
                             "sourceMetadataFrom": "#565 issue body; original evidence claims are not treated as current verification"})
            continue
        item = triage.get(choice["choiceId"])
        if not item:
            raise SystemExit(f"No original intake-triage record for {choice['choiceId']}")
        row = {**choice, "skillId": choice["choiceId"], "sourceIssue": item.get("ref"), "sourceUrl": item.get("source"),
               "description": item.get("description"), "name": item.get("name"), "license": item.get("license"),
               "oldPacket": item.get("receipts", {}).get("prefill"), "oldAssessment": item.get("receipts", {}).get("assessment"),
               "oldIntakeDisposition": item.get("disposition"), "existingPacketIdentity": item.get("receipts"),
               "intakeIdentity": (f"existing issue {item.get('ref')}" if item.get("ref") else "no individual intake issue found in source ledger")}
        if choice["founderChoice"] == "other":
            mapping, why = OTHER_MAPS[row["skillId"]]
            row.update(disposition="approved-map", proposedGeneric=mapping, mappingReason=why)
        elif choice["founderChoice"] == "new":
            row.update(disposition="approved-new-generic", proposal=NEW[row["skillId"]], proposedGeneric=NEW[row["skillId"]]["id"])
        elif choice["founderChoice"] == "decline":
            row.update(disposition="decline-support", declineReason=choice.get("founderNote") or "Founder choice: decline; preserve support-skill rationale from approval table.")
        else:
            row.update(disposition="approved-map", proposedGeneric=item.get("proposedGeneric"), mappingReason=item.get("proposedGenericNote"))
        existing = ROOT / "registry/named" / (row["skillId"].replace("/", "/") + ".md")
        if existing.exists():
            fm = read_frontmatter(existing)
            row["alreadyNamed"] = True
            row["existingNamedPath"] = str(existing.relative_to(ROOT))
            row["frozen"] = bool(fm.get("frozen") is True or fm.get("frozenAt") or fm.get("installable") is False or any(isinstance(e, dict) and e.get("action") == "upstream_deprecated" for e in fm.get("timeline", [])))
            comps = fm.get("suiteComponents") or []
            row["suiteComponentCount"] = len(comps) if isinstance(comps, list) else 0
            if row["frozen"]:
                row["disposition"] = "skip-frozen"
            elif row["disposition"] != "decline-support":
                row["disposition"] = "skip-existing"
        rows.append(row)
    return {"contract":"yggiv-l4-decision-inventory-v1", "sourceApproval":{"file":"founder/reports/yggdrasil-iv-october-2026/CAMPAIGN.md","sha256":hashlib.sha256((REPORT / "CAMPAIGN.md").read_bytes()).hexdigest(),"approvalRef":"CAMPAIGN.md § L4 topology choices"},
            "sourceTriage":{"file":"founder/reports/yggdrasil-iv-october-2026/reconciliation/intake-triage.json","sha256":hashlib.sha256((REPORT / "reconciliation/intake-triage.json").read_bytes()).hexdigest()},
            "choiceRows":len(choices), "concreteInventoryRows":len(rows), "countsByFounderChoice":{k:sum(x['founderChoice']==k for x in choices) for k in ('approve','other','new','decline')},
            "notes":"Parked-draft group expands to its seven named inventory records; existing k-dense-ai/pymc is represented and skipped, not re-submitted. Existing issue/batch references are preserved and no gaia push is performed.", "items":rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--prepare", action="store_true", help="Invoke canonical prefill/assess for eligible approval candidates")
    args = parser.parse_args()
    inv = inventory()
    PREP.mkdir(parents=True, exist_ok=True)
    inventory_path = PREP / "decision-inventory.json"
    inventory_path.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.prepare:
        print(f"Wrote {inventory_path.relative_to(ROOT)}: {inv['choiceRows']} choices / {inv['concreteInventoryRows']} concrete inventory rows")
        return
    packet_dir = PREP / "packets"
    assess_dir = PREP / "assessments"
    packet_dir.mkdir(parents=True, exist_ok=True)
    assess_dir.mkdir(parents=True, exist_ok=True)
    for item in inv["items"]:
        if item.get("founderChoice") == "decline" or item.get("disposition") in ("skip-existing", "skip-frozen"):
            continue
        if not item.get("sourceUrl"):
            print(f"BLOCKED {item['skillId']}: no source URL in original inventory", file=sys.stderr)
            continue
        if not item.get("name") or not item.get("description"):
            print(f"BLOCKED {item['skillId']}: no parsed name/description in original inventory", file=sys.stderr)
            continue
        slug = re.sub(r"[^a-zA-Z0-9_.-]", "_", item["skillId"])
        packet_path = packet_dir / f"{slug}.json"
        assessment_path = assess_dir / f"{slug}.assessment.json"
        cmd = [sys.executable, "-m", "gaia_cli.main", "dev", "prefill", item["skillId"], "--name", item["name"], "--description", item["description"], "--url", item["sourceUrl"], "--source-lane", "source-repository", "--json"]
        env = dict(__import__("os").environ, PYTHONPATH=str(ROOT / "src"))
        result = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
        if result.returncode:
            print(f"BLOCKED {item['skillId']}: prefill exit {result.returncode}: {result.stderr.strip()}", file=sys.stderr)
            continue
        try:
            packet = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"BLOCKED {item['skillId']}: prefill stdout was not a JSON packet", file=sys.stderr)
            continue
        # Apply only the already-recorded L4 topology choice to the discovery packet;
        # do not create l4Resolution/humanReview or invoke any mutation verb.
        if item["disposition"] == "approved-new-generic":
            p = item["proposal"]
            packet["decision"] = {"value":"NEW_GENERIC", "reasonCode":"FOUNDER_L4_APPROVED_NEW_GENERIC_PREP", "proposal":p}
        else:
            packet["decision"] = {"value":"MAP", "reasonCode":"FOUNDER_L4_APPROVED_MAP_PREP", "genericId":item["proposedGeneric"]}
        packet["lifecycle"] = ["discovered","fetched","parsed","normalized","deduped","mapped","review-ready"]
        packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        assess_cmd = [sys.executable, "-m", "gaia_cli.main", "dev", "assess", str(packet_path), "--jev", "off", "--output", str(assessment_path)]
        assessed = subprocess.run(assess_cmd, cwd=ROOT, env=env, text=True, capture_output=True)
        if assessed.returncode:
            print(f"BLOCKED {item['skillId']}: assess exit {assessed.returncode}: {assessed.stderr.strip()}", file=sys.stderr)
            continue
        item["preparedPacket"] = str(packet_path.relative_to(ROOT))
        item["preparedAssessment"] = str(assessment_path.relative_to(ROOT))
        item["preparedSourceSha256"] = packet.get("source", {}).get("contentSha256")
        item["preparedAt"] = packet.get("source", {}).get("fetchedAt")
        item["packetReasonCode"] = packet["decision"]["reasonCode"]
        print(f"READY {item['skillId']} {item['preparedSourceSha256']}")
    inventory_path.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {inventory_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
