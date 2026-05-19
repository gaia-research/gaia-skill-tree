#!/usr/bin/env python3
"""Fetch all SKILL.md files from ruvnet/ruflo and write generated-output/ruflo-skills-raw.json.

Skills are fetched from https://github.com/ruvnet/ruflo .claude/skills/ via raw.githubusercontent.com.
The dual-mode skill is special: it has multiple sub-skill files instead of a single SKILL.md.

Usage:
    python scripts/fetch_ruflo_skills.py [--out PATH] [--verbose]

Exit codes:
    0 — All skills fetched (or loaded from cache)
    1 — Fatal error
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "generated-output" / "ruflo-skills-raw.json"
BASE_RAW = "https://raw.githubusercontent.com/ruvnet/ruflo/main/.claude/skills"

# Canonical 39-skill directory list from .claude/skills/ (verified 2026-05-19)
SKILL_DIRS = [
    "agentdb-advanced",
    "agentdb-learning",
    "agentdb-memory-patterns",
    "agentdb-optimization",
    "agentdb-vector-search",
    "agentic-jujutsu",
    "browser",
    "dual-mode",       # special: has sub-skill files, not a single SKILL.md
    "flow-nexus-neural",
    "flow-nexus-platform",
    "flow-nexus-swarm",
    "github-code-review",
    "github-multi-repo",
    "github-project-management",
    "github-release-management",
    "github-workflow-automation",
    "hive-mind-advanced",
    "hooks-automation",
    "pair-programming",
    "performance-analysis",
    "reasoningbank-agentdb",
    "reasoningbank-intelligence",
    "skill-builder",
    "sparc-methodology",
    "stream-chain",
    "swarm-advanced",
    "swarm-orchestration",
    "v3-cli-modernization",
    "v3-core-implementation",
    "v3-ddd-architecture",
    "v3-integration-deep",
    "v3-mcp-optimization",
    "v3-memory-unification",
    "v3-performance-optimization",
    "v3-security-overhaul",
    "v3-swarm-coordination",
    "verification-quality",
    "worker-benchmarks",
    "worker-integration",
]

# dual-mode has sub-files instead of SKILL.md
DUAL_MODE_FILES = ["dual-collect.md", "dual-coordinate.md", "dual-spawn.md"]

# Suite membership map
SUITES: dict[str, list[str]] = {
    "flow-nexus": ["flow-nexus-swarm", "flow-nexus-platform", "flow-nexus-neural"],
    "agentdb": [
        "agentdb-advanced",
        "agentdb-learning",
        "agentdb-memory-patterns",
        "agentdb-optimization",
        "agentdb-vector-search",
    ],
    "github": [
        "github-code-review",
        "github-multi-repo",
        "github-project-management",
        "github-release-management",
        "github-workflow-automation",
    ],
    "hive-mind": ["hive-mind-advanced"],
    "reasoningbank": ["reasoningbank-agentdb", "reasoningbank-intelligence"],
    "swarm": ["swarm-orchestration", "swarm-advanced"],
    "v3": [
        "v3-cli-modernization",
        "v3-core-implementation",
        "v3-ddd-architecture",
        "v3-integration-deep",
        "v3-mcp-optimization",
        "v3-memory-unification",
        "v3-performance-optimization",
        "v3-security-overhaul",
        "v3-swarm-coordination",
    ],
    "standalone": [
        "agentic-jujutsu",
        "browser",
        "dual-mode",
        "hooks-automation",
        "pair-programming",
        "performance-analysis",
        "skill-builder",
        "sparc-methodology",
        "stream-chain",
        "verification-quality",
        "worker-benchmarks",
        "worker-integration",
    ],
}

# Fusion plan per suite
FUSIONS: dict[str, dict] = {
    "flow-nexus": {
        "named_id": "ruvnet/flow-nexus",
        "canon_id": "flow-nexus-orchestration",
        "type": "extra",
        "level": "4★",
        "origin": True,
        "note": "Queen Seraphina AI assistant lives in flow-nexus-platform",
    },
    "agentdb": {
        "named_id": "ruvnet/agentdb",
        "canon_id": "agent-memory-platform",
        "type": "ultimate",
        "level": "5★",
        "origin": True,
        "note": "QUIC/HNSW perf claims (150x-12500x) serve as Class B evidence",
    },
    "github": {
        "named_id": "ruvnet/github-suite",
        "canon_id": "github-platform-mastery",
        "type": "extra",
        "level": "4★",
        "origin": False,
        "note": "Individual skills are origin:false variants; only the fusion is novel",
    },
    "hive-mind": {
        "named_id": "hive-mind-advanced",
        "canon_id": "hive-mind-coordination",
        "type": "unique",
        "level": "4★",
        "origin": True,
        "note": "Unique (◉): graph-isolated, no prereqs; Byzantine consensus + queen hierarchy",
    },
    "reasoningbank": {
        "named_id": "ruvnet/reasoningbank",
        "canon_id": "reasoning-pattern-bank",
        "type": "extra",
        "level": "3★",
        "origin": True,
        "note": "Adaptive learning loop on top of vector memory",
    },
    "swarm": {
        "named_id": None,
        "canon_id": None,
        "type": None,
        "level": None,
        "origin": None,
        "note": "No suite fusion — swarm skills folded into v3-swarm-coordination as prereqs",
    },
    "v3": {
        "named_id": "ruvnet/ruflo-v3",
        "canon_id": "platform-modernization-sprint",
        "type": "extra",
        "level": "4★",
        "origin": True,
        "note": "Time-bounded sprint; tags: v3-sprint, modernization. Absorbs swarm skills as prereqs.",
    },
    "standalone": {
        "named_id": None,
        "canon_id": None,
        "type": None,
        "level": None,
        "origin": None,
        "note": "No suite fusion for standalone skills",
    },
}

CAPSTONE = {
    "named_id": "ruvnet/ruflo",
    "canon_id": "ruflo",
    "type": "ultimate",
    "level": "6★",
    "origin": True,
    "prerequisites": [
        "flow-nexus-orchestration",
        "agent-memory-platform",
        "github-platform-mastery",
        "hive-mind-coordination",
        "reasoning-pattern-bank",
        "platform-modernization-sprint",
    ],
    "note": "Grandmaster Path: 34k+ stars + AgentDB 5★ ultimate. Needs Class A evidence from gaia-curate sweep.",
}

# Existing Gaia canon node mappings (no new node needed)
EXISTING_CANON: dict[str, str] = {
    "flow-nexus-swarm": "multi-agent-orchestration-v",
    "github-code-review": "code-review-pipeline",
    "github-project-management": "project-management",
    "github-release-management": "release-automation",
    "github-workflow-automation": "workflow-automation",
    "v3-ddd-architecture": "ubiquitous-language",
    "v3-mcp-optimization": "mcp-integration",
    "v3-memory-unification": "memory-manage",
    "v3-security-overhaul": "security-audit",
    "v3-swarm-coordination": "multi-agent-orchestration-v",
    "browser": "browser-automation",
    "hooks-automation": "workflow-automation",
    "pair-programming": "subagent-driven-development",
    "skill-builder": "skill-authoring",
    "sparc-methodology": "agentic-workflow-design",
    "verification-quality": "verification-before-completion",
    "worker-benchmarks": "skill-performance-benchmarking",
    "swarm-orchestration": "multi-agent-orchestration-v",
}

# New canon nodes that need to be created (type → list of new IDs)
NEW_CANON: dict[str, dict] = {
    "flow-nexus-platform":     {"canon_id": "cloud-platform-management",       "type": "extra"},
    "flow-nexus-neural":       {"canon_id": "distributed-neural-training",      "type": "extra"},
    "agentdb-advanced":        {"canon_id": "distributed-vector-memory",        "type": "extra"},
    "agentdb-learning":        {"canon_id": "agent-memory-learning",            "type": "extra"},
    "agentdb-memory-patterns": {"canon_id": "memory-pattern-design",            "type": "basic"},
    "agentdb-optimization":    {"canon_id": "vector-db-optimization",           "type": "basic"},
    "agentdb-vector-search":   {"canon_id": "vector-search",                    "type": "basic"},
    "hive-mind-advanced":      {"canon_id": "hive-mind-coordination",           "type": "unique"},
    "reasoningbank-intelligence": {"canon_id": "adaptive-pattern-learning",     "type": "basic"},
    "reasoningbank-agentdb":   {"canon_id": "learned-memory-integration",       "type": "basic"},
    "swarm-orchestration":     {"canon_id": "swarm-topology-management",        "type": "basic"},
    "swarm-advanced":          {"canon_id": "advanced-swarm-coordination",      "type": "extra"},
    "v3-cli-modernization":    {"canon_id": "cli-modernization",                "type": "basic"},
    "v3-core-implementation":  {"canon_id": "core-platform-implementation",     "type": "basic"},
    "v3-integration-deep":     {"canon_id": "system-integration",               "type": "basic"},
    "v3-performance-optimization": {"canon_id": "performance-tuning",           "type": "basic"},
    "github-multi-repo":       {"canon_id": "multi-repo-coordination",          "type": "basic"},
    "agentic-jujutsu":         {"canon_id": "git-diff-risk-analysis",           "type": "basic"},
    "performance-analysis":    {"canon_id": "performance-tuning",               "type": "basic"},
    "stream-chain":            {"canon_id": "stream-chain-pipeline",            "type": "extra"},
    "worker-integration":      {"canon_id": "worker-agent-integration",         "type": "extra"},
    "dual-mode":               {"canon_id": "hybrid-agent-orchestration",       "type": "extra"},
}

# Origin flag per skill (true = ruvnet is first/origin)
ORIGIN_FLAGS: dict[str, bool] = {
    "flow-nexus-swarm":          True,   # already named as origin
    "flow-nexus-platform":       True,
    "flow-nexus-neural":         True,
    "agentdb-advanced":          True,
    "agentdb-learning":          True,
    "agentdb-memory-patterns":   True,
    "agentdb-optimization":      True,
    "agentdb-vector-search":     True,
    "hive-mind-advanced":        True,
    "reasoningbank-intelligence": True,
    "reasoningbank-agentdb":     True,
    "swarm-orchestration":       False,  # maps to existing multi-agent-orchestration-v
    "swarm-advanced":            False,  # new canon but not first-of-kind orchestration
    "v3-cli-modernization":      True,
    "v3-core-implementation":    True,
    "v3-ddd-architecture":       False,  # maps to ubiquitous-language (mattpocock first)
    "v3-integration-deep":       True,
    "v3-mcp-optimization":       False,  # maps to mcp-integration (garrytan first)
    "v3-memory-unification":     False,  # maps to memory-manage
    "v3-performance-optimization": True,
    "v3-security-overhaul":      False,  # maps to security-audit (garrytan first)
    "v3-swarm-coordination":     False,  # maps to multi-agent-orchestration-v
    "github-code-review":        False,
    "github-multi-repo":         True,   # new canon, ruvnet first
    "github-project-management": False,
    "github-release-management": False,
    "github-workflow-automation": False,
    "agentic-jujutsu":           True,
    "browser":                   False,
    "dual-mode":                 True,
    "hooks-automation":          False,
    "pair-programming":          False,
    "performance-analysis":      True,   # new canon
    "skill-builder":             False,
    "sparc-methodology":         True,   # ruvnet's SPARC is well-documented
    "stream-chain":              True,
    "verification-quality":      False,
    "worker-benchmarks":         False,
    "worker-integration":        True,
}


def _fetch_url(url: str, retries: int = 3, delay: float = 1.0) -> str | None:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt < retries - 1:
                time.sleep(delay * (2 ** attempt))
        except Exception:
            if attempt < retries - 1:
                time.sleep(delay * (2 ** attempt))
    return None


def fetch_skill(name: str, verbose: bool = False) -> dict:
    """Fetch skill content. Returns a skill dict."""
    entry: dict = {
        "id": name,
        "suite": _suite_of(name),
        "origin": ORIGIN_FLAGS.get(name, False),
        "canon_mapping": EXISTING_CANON.get(name) or NEW_CANON.get(name, {}).get("canon_id"),
        "canon_is_new": name in NEW_CANON,
        "canon_type": NEW_CANON.get(name, {}).get("type"),
        "content": None,
        "fetch_status": "ok",
    }

    if name == "dual-mode":
        # Compose from sub-skill files
        parts = []
        for fname in DUAL_MODE_FILES:
            url = f"{BASE_RAW}/dual-mode/{fname}"
            text = _fetch_url(url)
            if text:
                parts.append(f"## {fname}\n\n{text}")
        if parts:
            entry["content"] = "\n\n---\n\n".join(parts)
            entry["sub_skills"] = DUAL_MODE_FILES
        else:
            entry["fetch_status"] = "not_found"
    else:
        url = f"{BASE_RAW}/{name}/SKILL.md"
        text = _fetch_url(url)
        if text:
            entry["content"] = text
        else:
            entry["fetch_status"] = "not_found"

    if verbose:
        status = "✓" if entry["fetch_status"] == "ok" else "✗"
        print(f"  {status} {name}")
    return entry


def _suite_of(name: str) -> str:
    for suite, members in SUITES.items():
        if name in members:
            return suite
    return "standalone"


def build(out: Path, verbose: bool) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {len(SKILL_DIRS)} skills from ruvnet/ruflo…")
    skills = []
    ok = 0
    missing = []
    for name in SKILL_DIRS:
        entry = fetch_skill(name, verbose)
        skills.append(entry)
        if entry["fetch_status"] == "ok":
            ok += 1
        else:
            missing.append(name)

    result = {
        "source": "https://github.com/ruvnet/ruflo",
        "fetched_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "total": len(SKILL_DIRS),
        "fetched_ok": ok,
        "missing": missing,
        "suites": SUITES,
        "fusions": FUSIONS,
        "capstone": CAPSTONE,
        "skills": skills,
    }

    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out} — {ok}/{len(SKILL_DIRS)} fetched")
    if missing:
        print(f"WARNING: {len(missing)} skills not found: {missing}")
    return 0 if not missing else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch all ruflo SKILL.md files.")
    parser.add_argument("--out", default=str(OUT_DEFAULT), help="Output JSON path")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)
    return build(Path(args.out), args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
