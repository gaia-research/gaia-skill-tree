import argparse
import json
import os
import subprocess
import sys
import re
from pathlib import Path

import shlex

def run_command(cmd, capture_output=True):
    """Helper to run shell commands safely without shell=True to prevent command injection."""
    try:
        # If cmd is a string, safely split it (assuming no complex shell interpolations are intended)
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=capture_output,
            text=True
        )
        return result.stdout.strip() if result.stdout else None
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}\n{e.stderr}", file=sys.stderr)
        return None

def check_gh_auth():
    """Verify GitHub CLI is authenticated."""
    result = run_command(["gh", "auth", "status"])
    if result is None:
        print("GitHub CLI not authenticated. Please run 'gh auth login'.", file=sys.stderr)
        return False
    return True

def parse_graph_report(report_path):
    """Extract actionable sections from GRAPH_REPORT.md."""
    if not os.path.exists(report_path):
        return None
    
    content = Path(report_path).read_text(encoding='utf-8')
    
    sections = {
        "god_nodes": [],
        "surprises": [],
        "questions": []
    }
    
    # Simple regex parsing for standard graphify report sections
    god_match = re.search(r"## God Nodes.*?\n(.*?)(?=\n##|$)", content, re.S)
    if god_match:
        sections["god_nodes"] = [l.strip("- ").strip() for l in god_match.group(1).strip().split("\n") if l.strip()]

    surprise_match = re.search(r"## Surprising Connections.*?\n(.*?)(?=\n##|$)", content, re.S)
    if surprise_match:
        sections["surprises"] = [l.strip("- ").strip() for l in surprise_match.group(1).strip().split("\n") if l.strip()]

    question_match = re.search(r"## Suggested Questions.*?\n(.*?)(?=\n##|$)", content, re.S)
    if question_match:
        lines = question_match.group(1).strip().split("\n")
        current_q = None
        for line in lines:
            if line.startswith("- **"):
                if current_q: sections["questions"].append(current_q)
                current_q = {"title": line.strip("- ").strip(), "context": ""}
            elif current_q and line.strip().startswith("_"):
                current_q["context"] = line.strip("_ ")
        if current_q: sections["questions"].append(current_q)
        
    return sections

def create_issue_payloads(sections):
    """Convert parsed sections into GH issue payloads."""
    payloads = []
    
    # 1. God Node Optimization
    if sections["god_nodes"]:
        nodes_str = "\n".join([f"- {n}" for n in sections["god_nodes"][:3]])
        payloads.append({
            "title": "[Architectural Refactor] Decouple God Nodes identified by Graphify",
            "body": f"The following nodes have high centrality and may be bottlenecks or over-coupled abstractions:\n\n{nodes_str}\n\n### Tasks\n1. Analyze dependencies of these nodes.\n2. Extract sub-modules to improve cohesion.\n3. Verify with `graphify cluster-only`.",
            "labels": ["enhancement", "architecture"]
        })
    
    # 2. Suggested Research/Audit Questions
    for q in sections["questions"]:
        payloads.append({
            "title": f"[Audit] {q['title']}",
            "body": f"{q['context']}\n\nThis issue was automatically generated based on architectural patterns detected by Graphify.",
            "labels": ["audit", "question"]
        })
        
    return payloads

def main():
    parser = argparse.ArgumentParser(description='Graphify Triage Orchestrator')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Audit command
    p_audit = subparsers.add_parser('audit', help='Run graphify and generate issue payloads')
    p_audit.add_argument('--path', default='.', help='Path to scan')
    p_audit.add_argument('--output', required=True, help='Path to save payloads JSON')

    # Sync command
    p_sync = subparsers.add_parser('sync', help='Push payloads to GitHub as issues')
    p_sync.add_argument('--input', required=True, help='Path to payloads JSON')
    p_sync.add_argument('--repo', help='Target repo (owner/repo). Defaults to current origin.')

    args = parser.parse_args()

    if args.command == 'audit':
        print(f"Running graphify on {args.path}...")
        run_command(["graphify", ".", "--update"], capture_output=False)
        
        report_path = os.path.join(args.path, "graphify-out/GRAPH_REPORT.md")
        sections = parse_graph_report(report_path)
        
        if not sections:
            print("No report found or parsing failed.", file=sys.stderr)
            sys.exit(1)
            
        payloads = create_issue_payloads(sections)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(payloads, f, indent=2)
        print(f"Audit complete. {len(payloads)} proposed issues saved to {args.output}")

    elif args.command == 'sync':
        if not check_gh_auth():
            sys.exit(1)
            
        with open(args.input, 'r', encoding='utf-8') as f:
            payloads = json.load(f)
            
        for p in payloads:
            print(f"Creating issue: {p['title']}")
            cmd = ["gh", "issue", "create"]

            if args.repo:
                cmd.extend(["-R", args.repo])

            cmd.extend(["--title", p['title'], "--body", p['body']])

            for lbl in p.get("labels", []):
                cmd.extend(["--label", lbl])
            
            run_command(cmd, capture_output=False)
        
        print(f"Sync complete. {len(payloads)} issues created.")

if __name__ == '__main__':
    main()
