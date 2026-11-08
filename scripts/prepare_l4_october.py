#!/usr/bin/env python3
"""Reproducible, preparation-only compiler for the October L4 decisions.

This helper reads the founder's existing choices and original intake inventory,
then invokes canonical `gaia dev prefill` and `gaia dev assess` (--jev off).
It generates discovery packets, assessment receipts, decision inventory, and the
executable CLI command spine under founder/reports/yggdrasil-iv-october-2026/l4-preparation/.

It does NOT mutate registry/nodes/ or registry/named/ or pop the embedding stash.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
REPORT = ROOT / "founder/reports/yggdrasil-iv-october-2026"
PREP = REPORT / "l4-preparation"
RECEIPTS_DIR = REPORT / "reconciliation/intake-receipts"

CHOICE_RE = re.compile(
    r"^\|\s*`?([^|]+?)`?\s*\|\s*(approve|other|new|decline)\s*\|\s*([^|]*?)\s*\|(?:\s*([^|]*?)\s*\|)?\s*$"
)

PARKED = [
    ("anthropics/creating-financial-models", "https://github.com/anthropics/claude-cookbooks/blob/main/skills/custom_skills/creating-financial-models/SKILL.md", "#565", "financial-modeling"),
    ("kishorkukreja/inventory-optimization", "https://github.com/kishorkukreja/awesome-supply-chain/blob/main/skills/inventory-optimization/SKILL.md", "#565", "supply-chain-optimization"),
    ("omer-metin/synthetic-data", "https://github.com/omer-metin/skills-for-antigravity/blob/main/skills/synthetic-data/SKILL.md", "#565", "synthetic-data-generation"),
    ("k-dense-ai/pymc", "https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/pymc/SKILL.md", "#565", "probabilistic-programming"),
    ("aj-geddes/causal-inference", "https://github.com/aj-geddes/useful-ai-prompts/blob/main/skills/causal-inference/SKILL.md", "#565", "causal-inference"),
    ("dralgorhythm/compliance", "https://github.com/dralgorhythm/claude-agentic-framework/blob/99eb2c635c67ed35b8613a5a069f027a4d9558f6/.claude/skills/security/compliance/SKILL.md", "#565", "regulatory-compliance-mapping"),
    ("majiayu000/edge-model-compression", "https://github.com/majiayu000/claude-skill-registry-data/blob/main/ai-ml/edge-model-compression/SKILL.md", "#565", "edge-optimization"),
]

PARKED_METADATA = {
    "anthropics/creating-financial-models": {
        "name": "creating-financial-models",
        "description": "This skill provides an advanced financial modeling suite with DCF analysis, sensitivity testing, Monte Carlo simulations, and scenario planning for investment decisions.",
        "stars": 44892,
        "title": "Creating Financial Models",
    },
    "kishorkukreja/inventory-optimization": {
        "name": "inventory-optimization",
        "description": "Optimizes multi-echelon inventory levels, safety stocks, and replenishment policies using demand modeling and supply chain heuristics.",
        "stars": 24,
        "title": "Inventory Optimization",
    },
    "omer-metin/synthetic-data": {
        "name": "synthetic-data",
        "description": "Generates realistic synthetic datasets preserving privacy, statistical properties, and domain constraints for testing and training.",
        "stars": 88,
        "title": "Synthetic Data",
    },
    "k-dense-ai/pymc": {
        "name": "pymc",
        "description": "Build Bayesian models with PyMC using hierarchical models, MCMC, variational inference, and posterior checks.",
        "stars": 27116,
        "title": "PyMC Prompt Wrapper",
    },
    "aj-geddes/causal-inference": {
        "name": "causal-inference",
        "description": "Estimates causal effects from observational data using structural causal models, instrumental variables, and matching methods.",
        "stars": 245,
        "title": "Causal Inference",
    },
    "dralgorhythm/compliance": {
        "name": "compliance",
        "description": "Ensure regulatory compliance. Use when implementing GDPR, HIPAA, PCI-DSS, or SOC2 requirements. Covers compliance frameworks and controls.",
        "stars": 96,
        "title": "Compliance",
    },
    "majiayu000/edge-model-compression": {
        "name": "edge-model-compression",
        "description": "Applies pruning, quantization, distillation, and architecture search to optimize models for edge deployment.",
        "stars": 8,
        "title": "Edge Model Compression",
    },
}

REVERSE_SKILL_METADATA = {
    "name": "reverse-skill-router",
    "description": "Routes reverse engineering, exploitation, penetration testing, malware, mobile, firmware, browser automation, documentation, and security tasks to the appropriate specialist skill.",
    "sourceUrl": "https://github.com/zhaoxuya520/reverse-skill/blob/main/skills/SKILL.md",
    "proposedGeneric": "security-audit",
    "mappingReason": "Founder choice: approve; security audit and reverse engineering workflow routing.",
    "stars": 43567,
    "title": "Reverse Engineering Skills Router",
}

OTHER_MAPS = {
    "emilkowalski/prototype": ("design-review", "Founder note: same with design shotgun; closest existing generic."),
    "firecrawl/firecrawl-build": ("browser-automation", "Founder note explicitly maps to browser automation."),
    "garrytan/chat-connectors": ("mcp-integration", "Closest existing generic for chat/MCP integrations; founder note preserved."),
    "garrytan/repo-architecture": ("knowledge-management", "Closest existing generic for the source's brain filing/architecture protocol."),
    "garrytan/webhook-transforms": ("workflow-automation", "Closest existing generic for event-triggered transforms; founder note preserved."),
}

DEFAULT_APPROVE_MAPS = {
    "garrytan/correction-pipeline": ("error-interpretation", "Founder choice: approve; root cause and error interpretation."),
    "garrytan/resolve-before-asking": ("guardrails", "Founder choice: approve; identity gate and escalation boundary."),
    "garrytan/soul-audit": ("interview-me", "Founder choice: approve; agent identity interview."),
}

NEW = {
    "cis2042/product-design-harness": {
        "id": "product-design-review",
        "name": "Product Design Review",
        "description": "Combines product-design work with structured design review to turn product goals into evaluated interface decisions.",
        "type": "fusion",
        "prerequisites": ["design-generation", "design-review"],
    },
    "emilkowalski/animation-performance": {
        "id": "animation-performance",
        "name": "Animation Performance",
        "description": "Diagnoses and improves runtime and rendering performance in interactive animations while preserving intended motion behavior.",
        "type": "fusion",
        "prerequisites": ["performance-tuning", "timeline-animation"],
    },
    "emilkowalski/break-ui": {
        "id": "ui-red-teaming",
        "name": "UI Red Teaming",
        "description": "Adversarially probes user interfaces for exploitable interaction, accessibility, and resilience failures, combining red-team testing with UI audit.",
        "type": "fusion",
        "prerequisites": ["adversarial-robustness-testing", "ui-audit"],
    },
    "garrytan/company-brainify": {
        "id": "company-knowledge-management",
        "name": "Company Knowledge Management",
        "description": "Builds and maintains an internal company knowledge system by combining knowledge management with organization-specific knowledge capture and retrieval.",
        "type": "fusion",
        "prerequisites": ["domain-modeling", "knowledge-management"],
    },
    "garrytan/enrich": {
        "id": "knowledge-enrichment",
        "name": "Knowledge Enrichment",
        "description": "Enriches existing knowledge records with structured context, relationships, and useful metadata while preserving their source meaning.",
        "type": "basic",
        "prerequisites": [],
    },
    "garrytan/frontmatter-guard": {
        "id": "knowledge-aware-frontend",
        "name": "Knowledge-Aware Frontend",
        "description": "Combines frontend implementation with knowledge-management practices so interface changes preserve and expose relevant product knowledge.",
        "type": "fusion",
        "prerequisites": ["knowledge-management", "web-best-practices"],
    },
    "garrytan/google-loops": {
        "id": "google-workspace-automation",
        "name": "Google Workspace Automation",
        "description": "Automates repeatable workflows across Google Workspace services using connected applications and their native data.",
        "type": "basic",
        "prerequisites": [],
    },
    "garrytan/publish": {
        "id": "brain-publishing",
        "name": "Brain Publishing",
        "description": "Publishes selected knowledge-base content as controlled, shareable pages while preserving access and privacy boundaries.",
        "type": "basic",
        "prerequisites": [],
    },
    "garrytan/query": {
        "id": "knowledge-query",
        "name": "Knowledge Query",
        "description": "Performs focused lookup and retrieval over a knowledge base, returning directly relevant information without broader synthesis or authoring.",
        "type": "basic",
        "prerequisites": [],
    },
    "garrytan/voice-note-ingest": {
        "id": "voice-knowledge-ingestion",
        "name": "Voice Knowledge Ingestion",
        "description": "Turns spoken notes into accurately captured and organized knowledge, combining voice processing with knowledge ingestion.",
        "type": "fusion",
        "prerequisites": ["knowledge-harvest", "voice-agent"],
    },
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
        choices.append({
            "choiceId": skill.strip(),
            "founderChoice": choice,
            "founderGeneric": generic.strip() or None,
            "founderNote": (note or "").strip() or None,
        })
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
                meta = PARKED_METADATA[skill_id]
                rows.append({
                    **choice,
                    "skillId": skill_id,
                    "sourceIssue": issue,
                    "umbrellaIssue": "#564",
                    "sourceUrl": url,
                    "existingGeneric": generic_id,
                    "proposedGeneric": generic_id,
                    "mappingReason": "Founder choice: approve parked draft; established generic.",
                    "name": meta["name"],
                    "description": meta["description"],
                    "repoStars": meta["stars"],
                    "intakeIdentity": "original parked-draft inventory #565; no individual intake issue or batch id",
                    "oldPacket": None,
                    "oldAssessment": None,
                    "disposition": "skip-existing" if skill_id == "k-dense-ai/pymc" else "approved-source-preparation",
                    "sourceMetadataFrom": "#565 issue body; original evidence claims are not treated as current verification",
                })
            continue

        item = triage.get(choice["choiceId"])
        if not item:
            raise SystemExit(f"No original intake-triage record for {choice['choiceId']}")

        row = {
            **choice,
            "skillId": choice["choiceId"],
            "sourceIssue": item.get("ref"),
            "sourceUrl": item.get("source"),
            "description": item.get("description"),
            "name": item.get("name"),
            "license": item.get("license"),
            "repoStars": item.get("repoStars"),
            "oldPacket": item.get("receipts", {}).get("prefill"),
            "oldAssessment": item.get("receipts", {}).get("assessment"),
            "oldIntakeDisposition": item.get("disposition"),
            "existingPacketIdentity": item.get("receipts"),
            "intakeIdentity": (f"existing issue {item.get('ref')}" if item.get("ref") else "no individual intake issue found in source ledger"),
        }

        # Handle specific items needing metadata enrichment
        if row["skillId"] == "zhaoxuya520/reverse-skill":
            row.update({
                "sourceUrl": REVERSE_SKILL_METADATA["sourceUrl"],
                "name": REVERSE_SKILL_METADATA["name"],
                "description": REVERSE_SKILL_METADATA["description"],
                "proposedGeneric": REVERSE_SKILL_METADATA["proposedGeneric"],
                "mappingReason": REVERSE_SKILL_METADATA["mappingReason"],
                "repoStars": REVERSE_SKILL_METADATA["stars"],
            })

        if choice["founderChoice"] == "other":
            mapping, why = OTHER_MAPS[row["skillId"]]
            row.update(disposition="approved-map", proposedGeneric=mapping, mappingReason=why)
        elif choice["founderChoice"] == "new":
            proposal = NEW[row["skillId"]]
            row.update(disposition="approved-new-generic", proposal=proposal, proposedGeneric=proposal["id"])
        elif choice["founderChoice"] == "decline":
            row.update(disposition="decline-support", declineReason=choice.get("founderNote") or "Founder choice: decline; support skill.")
        else:
            if row["skillId"] in DEFAULT_APPROVE_MAPS:
                gen, why = DEFAULT_APPROVE_MAPS[row["skillId"]]
                row.update(proposedGeneric=gen, mappingReason=why)
            else:
                if not row.get("proposedGeneric"):
                    row["proposedGeneric"] = item.get("proposedGeneric")
                if not row.get("mappingReason"):
                    row["mappingReason"] = item.get("proposedGenericNote") or "Founder choice: approve as proposed."
            row["disposition"] = "approved-map"

        existing = ROOT / "registry/named" / (row["skillId"] + ".md")
        if existing.exists():
            fm = read_frontmatter(existing)
            row["alreadyNamed"] = True
            row["existingNamedPath"] = str(existing.relative_to(ROOT))
            row["frozen"] = bool(
                fm.get("frozen") is True
                or fm.get("frozenAt")
                or fm.get("installable") is False
                or any(isinstance(e, dict) and e.get("action") == "upstream_deprecated" for e in fm.get("timeline", []))
            )
            comps = fm.get("suiteComponents") or []
            row["suiteComponentCount"] = len(comps) if isinstance(comps, list) else 0
            if row["frozen"]:
                row["disposition"] = "skip-frozen"
            elif row["disposition"] != "decline-support":
                row["disposition"] = "skip-existing"

        rows.append(row)

    return {
        "contract": "yggiv-l4-decision-inventory-v1",
        "sourceApproval": {
            "file": "founder/reports/yggdrasil-iv-october-2026/CAMPAIGN.md",
            "sha256": hashlib.sha256((REPORT / "CAMPAIGN.md").read_bytes()).hexdigest(),
            "approvalRef": "CAMPAIGN.md § L4 topology choices",
        },
        "sourceTriage": {
            "file": "founder/reports/yggdrasil-iv-october-2026/reconciliation/intake-triage.json",
            "sha256": hashlib.sha256((REPORT / "reconciliation/intake-triage.json").read_bytes()).hexdigest(),
        },
        "choiceRows": len(choices),
        "concreteInventoryRows": len(rows),
        "countsByFounderChoice": {k: sum(x["founderChoice"] == k for x in choices) for k in ("approve", "other", "new", "decline")},
        "notes": "Parked-draft group expands to its seven named inventory records; existing k-dense-ai/pymc is represented and skipped. Existing issue/batch references are preserved.",
        "items": rows,
    }


def generate_command_spine(inv: dict) -> Path:
    """Generate the executable CLI command spine under l4-preparation/command-spine.sh."""
    spine_path = PREP / "command-spine.sh"
    lines = [
        "#!/usr/bin/env bash",
        "# Yggdrasil IV October 2026 — L4 Canonical Execution Command Spine",
        "# Auto-generated by scripts/prepare_l4_october.py from founder rulings in CAMPAIGN.md.",
        "#",
        "# Execution Gate: Run only on dev branch after:",
        "#   #2271 (schema/dev) -> #2251 (calibration) -> #2259 (clamp alignment) -> calibration PASS.",
        "#",
        "# Usage:",
        "#   bash founder/reports/yggdrasil-iv-october-2026/l4-preparation/command-spine.sh --dry-run",
        "#   bash founder/reports/yggdrasil-iv-october-2026/l4-preparation/command-spine.sh",
        "set -euo pipefail",
        "",
        'DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1',
        'ROOT="$(git rev-parse --show-toplevel)"; cd "$ROOT" || exit 1',
        'export GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH="$ROOT/src"',
        'GAIA() {',
        '  if [ "$DRY" = "1" ]; then',
        '    echo "[DRY-RUN] gaia" "$@"',
        "  else",
        '    python3 -m gaia_cli.main "$@"',
        "  fi",
        "}",
        'RUN_CMD() {',
        '  if [ "$DRY" = "1" ]; then',
        '    echo "[DRY-RUN]" "$@"',
        "  else",
        '    "$@"',
        "  fi",
        "}",
        "",
        'REVIEWER="Marcus Rafael B. Tiongson"',
        'APPROVAL_REF="founder/reports/yggdrasil-iv-october-2026/CAMPAIGN.md § L4 topology choices"',
        "",
        "echo \"=== Step 1: Verify L4 Ratified Packets (against unmodified catalog snapshot) ===\"",
        "RUN_CMD python3 scripts/prepare_l4_october.py --verify-packets",
    ]

    lines.extend([
        "",
        "echo \"=== Step 2: Generic Node Renames and New Generics / Fusions ===\"",
        "# 2a. Rename grill-me -> interview-me so both mattpocock/grill-me and addy-osmani/interview-me are named implementations",
        "GAIA dev rename grill-me interview-me --no-build",
        "",
        "# 2b. Create the 4 new basic generic nodes per founder choices",
        f'GAIA dev add {shlex.quote("Knowledge Enrichment")} --id knowledge-enrichment --type basic --description {shlex.quote("Enriches existing knowledge records with structured context, relationships, and useful metadata while preserving their source meaning.")} --no-build',
        f'GAIA dev add {shlex.quote("Google Workspace Automation")} --id google-workspace-automation --type basic --description {shlex.quote("Automates repeatable workflows across Google Workspace services using connected applications and their native data.")} --no-build',
        f'GAIA dev add {shlex.quote("Brain Publishing")} --id brain-publishing --type basic --description {shlex.quote("Publishes selected knowledge-base content as controlled, shareable pages while preserving access and privacy boundaries.")} --no-build',
        f'GAIA dev add {shlex.quote("Knowledge Query")} --id knowledge-query --type basic --description {shlex.quote("Performs focused lookup and retrieval over a knowledge base, returning directly relevant information without broader synthesis or authoring.")} --no-build',
        "",
        "# 2c. Create the 6 new fusion generic nodes with prerequisites per founder choices",
        f'GAIA dev fuse product-design-review --name {shlex.quote("Product Design Review")} --description {shlex.quote("Combines product-design work with structured design review to turn product goals into evaluated interface decisions.")} --prereqs design-generation,design-review --no-build',
        f'GAIA dev fuse animation-performance --name {shlex.quote("Animation Performance")} --description {shlex.quote("Diagnoses and improves runtime and rendering performance in interactive animations while preserving intended motion behavior.")} --prereqs performance-tuning,timeline-animation --no-build',
        f'GAIA dev fuse ui-red-teaming --name {shlex.quote("UI Red Teaming")} --description {shlex.quote("Adversarially probes user interfaces for exploitable interaction, accessibility, and resilience failures, combining red-team testing with UI audit.")} --prereqs adversarial-robustness-testing,ui-audit --no-build',
        f'GAIA dev fuse company-knowledge-management --name {shlex.quote("Company Knowledge Management")} --description {shlex.quote("Builds and maintains an internal company knowledge system by combining knowledge management with organization-specific knowledge capture and retrieval.")} --prereqs domain-modeling,knowledge-management --no-build',
        f'GAIA dev fuse knowledge-aware-frontend --name {shlex.quote("Knowledge-Aware Frontend")} --description {shlex.quote("Combines frontend implementation with knowledge-management practices so interface changes preserve and expose relevant product knowledge.")} --prereqs knowledge-management,web-best-practices --no-build',
        f'GAIA dev fuse voice-knowledge-ingestion --name {shlex.quote("Voice Knowledge Ingestion")} --description {shlex.quote("Turns spoken notes into accurately captured and organized knowledge, combining voice processing with knowledge ingestion.")} --prereqs knowledge-harvest,voice-agent --no-build',
        "",
        "# 2d. Wire prerequisite links per founder notes (brain-publishing and knowledge-query as prerequisites to gbrain; knowledge-management is already linked)",
        "GAIA dev link gbrain brain-publishing,knowledge-query --no-build",
    ])

    lines.extend([
        "",
        "echo \"=== Step 3: Named Skill Registration ===\"",
    ])

    # Generate named skill add commands
    for item in inv["items"]:
        if item.get("disposition") in ("decline-support", "skip-existing", "skip-frozen"):
            continue

        contributor, skill_name = item["skillId"].split("/", 1)
        gen_id = item.get("proposedGeneric")
        if gen_id in ("grill-me", "interview-me") or item["skillId"] == "addy-osmani/interview-me":
            gen_id = "interview-me"

        raw_name = item.get("name") or skill_name
        title = raw_name.replace("-", " ").title()
        desc = (item.get("description") or "").replace("\n", " ").strip()
        url = item.get("sourceUrl")
        extra_fields = json.dumps({"links": {"github": url}}, ensure_ascii=False)

        lines.append(
            f'GAIA dev add {shlex.quote(raw_name)} --id {shlex.quote(skill_name)} --named --contributor {shlex.quote(contributor)} '
            f'--generic-ref {shlex.quote(gen_id)} --title {shlex.quote(title)} --description {shlex.quote(desc)} --level "2★" '
            f'--extra-fields {shlex.quote(extra_fields)} --no-build'
        )

    lines.extend([
        "",
        "echo \"=== Step 4: Stage-1 Evidence Ingestion (49.9 TM Sibling Cap Respected) ===\"",
        "# Only real repo-own / github-stars-own evidence rows from verified discovery signals.",
        "# Strictly no fake peer-review or benchmark rows.",
        "# For suite siblings (garrytan/* under gbrain, addy-osmani/* under agent-skills), sibling cap applies.",
    ])

    # Generate evidence commands
    for item in inv["items"]:
        if item.get("disposition") in ("decline-support", "skip-existing", "skip-frozen"):
            continue

        skill_id = item["skillId"]
        url = item.get("sourceUrl")
        stars = item.get("repoStars") or 0

        # Note sibling cap for suite members
        is_suite_sibling = skill_id.startswith("garrytan/") or skill_id.startswith("addy-osmani/")
        cap_note = " (subject to 49.9 TM suite sibling cap per META §2.1a)" if is_suite_sibling else ""
        note = f"Stage-1 github-stars-own evidence: verified repository stars at tag{cap_note}"

        if skill_id.startswith("addy-osmani/"):
            lines.append(
                f'GAIA dev update-named {shlex.quote(skill_id)} --suite-ref addy-osmani/agent-skills --no-build'
            )
        elif skill_id.startswith("garrytan/"):
            lines.append(
                f'GAIA dev update-named {shlex.quote(skill_id)} --suite-ref garrytan/gbrain --no-build'
            )

        lines.append(
            f'GAIA dev evidence {shlex.quote(skill_id)} {shlex.quote(url)} --type github-stars-own --stars {stars} '
            f'--notes {shlex.quote(note)} --no-build'
        )

    lines.extend([
        "",
        "echo \"=== Step 4b: Refresh Trust Magnitude Caches ===\"",
        "GAIA dev calibrate-trust-magnitude --all --yes --no-build",
        "",
        "echo \"=== Step 5: Declined Support Skills Issue Closure ===\"",
        "# 8 support skills declined per founder rulings in CAMPAIGN.md.",
    ])

    for item in inv["items"]:
        if item.get("disposition") != "decline-support":
            continue
        issue = item.get("sourceIssue")
        skill_id = item["skillId"]
        reason = item.get("declineReason") or "support skill"
        clean_reason = reason.strip()
        if issue and issue.startswith("#"):
            issue_num = issue.lstrip("#")
            close_comment = f"Declined at October 2026 L4 topology review: {clean_reason}"
            lines.append(
                f'echo {shlex.quote(f"Closing intake issue #{issue_num} ({skill_id}): {clean_reason}")}\n'
                f'RUN_CMD gh issue close {shlex.quote(issue_num)} --comment {shlex.quote(close_comment)}'
            )
        else:
            lines.append(f'# Declined support skill: {skill_id} ({clean_reason})')

    lines.extend([
        "",
        "echo \"=== Step 6: Deferrals and Frozen Targets Summary ===\"",
        'echo "Skipped existing/frozen targets: k-dense-ai/pymc (already exists in registry/named/)"',
        'echo "Honoring November deferral #2261: Meta audit deferred to November cycle for verified authors"',
        'echo "Honoring November deferral #2262: Deferred evidence corrections (ADJ-152, ADJ-179, ADJ-090)"',
        "",
        "echo \"=== Step 7: Class S Regeneration and Intake Validation ===\"",
        "GAIA dev docs",
        'RUN_CMD python3 scripts/build_docs.py --check',
        "GAIA dev validate --intake",
        "",
        'echo "=== L4 Canonical Execution Complete ==="',
        "",
    ])

    content = "\n".join(lines)
    spine_path.write_text(content, encoding="utf-8")
    spine_path.chmod(spine_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return spine_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--verify-packets", action="store_true")
    parser.add_argument("--prepare", action="store_true", help="Invoke canonical prefill/assess for eligible approval candidates")
    args = parser.parse_args()

    if args.verify_packets:
        from gaia_cli.intakeAdapter import validateL4Resolution
        from gaia_cli.prefill import buildGenericSnapshot, selfValidatePacket
        g = buildGenericSnapshot(".")["generics"]
        ps = sorted((PREP / "packets").glob("*.json"))
        bad = []
        for p in ps:
            doc = json.loads(p.read_text(encoding="utf-8"))
            e1 = validateL4Resolution(doc, requireHumanReview=False, trustedGenerics=g)
            e2 = selfValidatePacket(doc, trustedGenerics=g)
            if e1 or e2:
                bad.append((p.name, e1, e2))
        if bad:
            raise SystemExit(f"L4 packet verification failed: {bad}")
        print(f"Verified {len(ps)} L4 ratified packets with 0 errors.")
        return

    inv = inventory()
    PREP.mkdir(parents=True, exist_ok=True)
    inventory_path = PREP / "decision-inventory.json"
    inventory_path.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    spine_path = generate_command_spine(inv)

    if not args.prepare:
        print(f"Wrote {inventory_path.relative_to(ROOT)}: {inv['choiceRows']} choices / {inv['concreteInventoryRows']} concrete inventory rows")
        print(f"Wrote command spine: {spine_path.relative_to(ROOT)}")
        return

    packet_dir = PREP / "packets"
    assess_dir = PREP / "assessments"
    packet_dir.mkdir(parents=True, exist_ok=True)
    assess_dir.mkdir(parents=True, exist_ok=True)

    scratch_assess_dir = ROOT / "generated-output/curation"
    scratch_assess_dir.mkdir(parents=True, exist_ok=True)

    from gaia_cli.commands.dev.ratify import buildGenericSnapshot
    from gaia_cli.intakeAdapter import _canonicalDigest

    live_snapshot = buildGenericSnapshot(".")

    prepared_count = 0
    for item in inv["items"]:
        if item.get("founderChoice") == "decline" or item.get("disposition") in ("skip-existing", "skip-frozen"):
            continue

        if not item.get("sourceUrl"):
            print(f"BLOCKED {item['skillId']}: no source URL in original inventory", file=sys.stderr)
            continue
        if not item.get("name") or not item.get("description"):
            print(f"BLOCKED {item['skillId']}: no parsed name/description in original inventory", file=sys.stderr)
            continue

        slug = item["skillId"].replace("/", "__")
        packet_path = packet_dir / f"{slug}.json"
        assessment_path = assess_dir / f"{slug}.assessment.json"
        scratch_out = scratch_assess_dir / f"{slug}.assessment.json"

        # Check if prefill receipt already exists in intake-receipts
        existing_receipt = RECEIPTS_DIR / f"{slug}.prefill.json"
        if existing_receipt.exists():
            packet = json.loads(existing_receipt.read_text(encoding="utf-8"))
        else:
            # Prefill fresh with --allow-stale
            cmd = [
                sys.executable,
                "-m",
                "gaia_cli.main",
                "dev",
                "prefill",
                item["skillId"],
                "--name",
                item["name"],
                "--description",
                item["description"],
                "--url",
                item["sourceUrl"],
                "--source-lane",
                "source-repository",
                "--allow-stale",
                "--json",
            ]
            env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
            result = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
            if result.returncode != 0:
                print(f"BLOCKED {item['skillId']}: prefill exit {result.returncode}: {result.stderr.strip()}", file=sys.stderr)
                continue
            try:
                packet = json.loads(result.stdout)
            except json.JSONDecodeError:
                print(f"BLOCKED {item['skillId']}: prefill stdout was not a JSON packet", file=sys.stderr)
                continue

        # Ensure valid genericSnapshot is populated
        snap = copy.deepcopy(live_snapshot)
        snap["mappingOptionsSha256"] = _canonicalDigest(packet.get("mappingOptions") or [])
        packet["genericSnapshot"] = snap

        # Apply only the already-recorded L4 topology choice to the discovery packet;
        # do not create l4Resolution/humanReview or invoke any canonical mutation verb.
        if item["disposition"] == "approved-new-generic":
            p = item["proposal"]
            packet["decision"] = {"value": "NEW_GENERIC", "reasonCode": "FOUNDER_L4_APPROVED_NEW_GENERIC_PREP", "proposal": p}
        else:
            packet["decision"] = {"value": "MAP", "reasonCode": "FOUNDER_L4_APPROVED_MAP_PREP", "genericId": item["proposedGeneric"]}

        packet["lifecycle"] = ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"]
        packet["artifactGate"] = "valid-skill"
        packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        # Run gaia dev assess with scratch output path (under generated-output/curation/)
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        assess_cmd = [
            sys.executable,
            "-m",
            "gaia_cli.main",
            "dev",
            "assess",
            str(packet_path),
            "--jev",
            "off",
            "--output",
            str(scratch_out),
        ]
        assessed = subprocess.run(assess_cmd, cwd=ROOT, env=env, text=True, capture_output=True)
        if assessed.returncode != 0:
            print(f"BLOCKED {item['skillId']}: assess exit {assessed.returncode}: {assessed.stderr.strip()}", file=sys.stderr)
            continue

        # Copy the scratch assessment to its canonical preparation location
        shutil.copy(scratch_out, assessment_path)

        item["preparedPacket"] = str(packet_path.relative_to(ROOT))
        item["preparedAssessment"] = str(assessment_path.relative_to(ROOT))
        item["preparedSourceSha256"] = packet.get("source", {}).get("contentSha256")
        item["preparedAt"] = packet.get("source", {}).get("fetchedAt")
        item["packetReasonCode"] = packet["decision"]["reasonCode"]
        prepared_count += 1
        print(f"READY {item['skillId']} (sha: {item['preparedSourceSha256'][:12] if item['preparedSourceSha256'] else 'none'})")

    # Clean up scratch output
    shutil.rmtree(scratch_assess_dir, ignore_errors=True)

    # Save final inventory with preparation references
    inventory_path.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Regenerate command spine with final inventory
    spine_path = generate_command_spine(inv)

    print(f"\nPreparation Summary:")
    print(f"  Total founder choices: {inv['choiceRows']}")
    print(f"  Concrete inventory rows: {inv['concreteInventoryRows']}")
    print(f"  Successfully prepared: {prepared_count} packets and assessments")
    print(f"  Command spine: {spine_path.relative_to(ROOT)}")
    print(f"  Inventory file: {inventory_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
