import argparse
import sys
import os
import json
import signal
import subprocess
from datetime import date, datetime, timezone
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from gaia_cli.scanner import scan_repo, scan_repo_detailed, load_config, scan_skill_mds, match_skill_to_canonical
from gaia_cli.resolver import resolve_skills
from gaia_cli.combinator import get_combinations
from gaia_cli.treeManager import load_tree, save_tree, show_status, show_tree
from gaia_cli.prWriter import open_pr, open_intake_issue
from gaia_cli.push import build_skill_batch, write_skill_batch, build_proposed_skill, detect_source_repo, NonPublicRepoError
from gaia_cli.embeddings import generate_embeddings
from gaia_cli.semantic_search import search as semantic_search, load_embeddings
from gaia_cli.name import find_awakened_skill, promote_to_named, update_batch_lifecycle
from gaia_cli.install import install_skill, install_suite, update_skills, uninstall_skill, list_installed, interactive_install, list_available
from gaia_cli.graph import graph_command
from gaia_cli.commands.stats import stats_command
from gaia_cli.commands.dev import (
    meta_list_command,
    meta_merge_command,
    meta_split_command,
    meta_add_command,
    meta_remove_command,
    meta_link_command,
    meta_reclassify_command,
    meta_update_named_command,
    meta_timeline_command,
    meta_rename_command,
    meta_verify_command,
    meta_calibrate_command,
    meta_evidence_command,
    meta_rm_evidence_command,
    meta_build_command,
    meta_audit_command,
    meta_diff_command,
)
from gaia_cli.registry import (
    generated_output_dir,
    embeddings_path,
    named_skills_dir,
    named_skills_index_path,
    promotion_candidates_path,
    registry_graph_path,
    skill_batches_dir,
    user_tree_path,
    require_explicit_writable_registry,
    resolve_registry_path,
    write_global_registry,
)
from gaia_cli.pathEngine import (
    compute_paths,
    load_paths,
    save_paths,
    diff_paths,
    render_unlock_path,
    _path_tree_to_dict,
    unlock_path,
)
from gaia_cli.cardRenderer import (
    render_card,
    render_appraise_card,
    render_unlock_card,
    render_path_summary,
    render_promotion_prompt,
    load_and_render,
)
from gaia_cli.promotion import (
    check_promotion_eligibility,
    detect_unique_candidates,
    load_promotion_candidates,
    promote_from_candidates,
    promote_skill,
    promotable_candidates,
    promotion_state,
    write_promotion_candidates,
    next_level,
    LEVEL_NAMES,
)
from gaia_cli.hook import hook_entry
from gaia_cli.formatting import (
    format_skill_plain,
    format_skill_colored,
    format_type_label,
    format_type_colored,
    format_level_colored,
    fusion_equation,
    TIER_COLORS,
    RANK_COLORS,
    TYPE_SYMBOLS,
    COLOR_CONTRIBUTOR,
    COLOR_LOCAL_USER,
    COLOR_REDACTED,
    REDACTED_BLOCK,
    _fg,
    _reset,
    _bold,
    _use_color,
)
from gaia_cli.localContext import LocalContext
from gaia_cli.cardRenderer import render_fusion_diagram
from gaia_cli.interactive import select_skill, select_fusion_candidate, select_promotion_candidate

DEFAULT_REGISTRY_REF = "https://github.com/mbtiongson1/gaia-skill-tree"

COMMAND_USAGE = """\
Quick usage:
  gaia                        Launch the TUI (interactive dashboard)
  gaia init [--user <name>] [--scan <path>] [--yes]
  gaia scan [--quiet]
  gaia pull
  gaia tree [--named] [--title]
  gaia push [--dry-run] [--no-issue]
  gaia propose [<skillId>] [--ultimate] [--target <name>] [--no-pr]
  gaia version
  gaia whoami
  gaia mcp
  gaia release <patch|minor|major>
  gaia graph [--format html|svg|json] [-o <path>] [--no-open]
  gaia appraise [<skillId>]
  gaia promote [<skillId>] [--all] [--name <name>]
  gaia fuse <skillId> [--name <name>]
  gaia update
  gaia stats
  gaia docs build [--check]
  gaia lookup <skillId>

  -- dev: read-only (no authorization required) --
  gaia dev list [--generic] [--named] [--description] [--json]
  gaia dev audit <skill_id>
  gaia dev diff [ref] [--base <ref>]

  -- dev: mutating (requires Verifier role — see gaia whoami) --
  gaia dev add <name> [--id <id>] [--type <type>] [--description <desc>] [--named] [--contributor <user>] [--status <status>] [--title <title>] [--level <level>]
  gaia dev merge <target> <source1> [source2...] [--named] [--yes]
  gaia dev split <source> <target1> <target2>... [--yes]
  gaia dev rename <old_id> <new_id>
  gaia dev calibrate <skill_id> <level>
  gaia dev rm <skill_id> [--yes]
  gaia dev link <target> <prereqs> [--reset]
  gaia dev reclassify <skill_id> <new_type>
  gaia dev update-named <skill_id> [--status <status>] [--generic-ref <ref>] [--suite-components <c1,c2...>]
  gaia dev evidence <skillId> <source> [--class A|B|C] [--evaluator <user>] [--date <date>] [--notes <notes>]
  gaia dev rm-evidence <skill_id> (--index N | --source URL) [--yes]
  gaia dev timeline <skill_id> --action <action> --notes <notes> [--user <username>] [--timestamp <iso8601>]
  gaia dev build

  gaia validate [--intake] [--meta-sync]
  gaia test <suite>
  gaia skills <list|search|info|install|uninstall>
  gaia skills list [--exclude-pending]
  gaia skills search <query> [--exclude-pending]
  gaia skills info <skill_id> [--exclude-pending]
  gaia skills install <skill> [--global | --local]
  gaia skills uninstall <skill_id>
  gaia path <skillId> [--owned-only] [--json]
"""

SKILLS_USAGE = """\
Quick usage:
  gaia skills list [--exclude-pending]
  gaia skills search <query> [--exclude-pending]
  gaia skills info <skill_id> [--exclude-pending]
  gaia skills install <skill> [--global | --local]
  gaia skills uninstall <skill_id>
"""

PUBLIC_COMMANDS = (
    "help",
    "init",
    "scan",
    "pull",
    "update",
    "install",
    "uninstall",
    "tree",
    "push",
    "propose",
    "version",
    "whoami",
    "mcp",
    "release",
    "graph",
    "stats",
    "appraise",
    "promote",
    "fuse",
    "docs",
    "lookup",
    "path",
    "dev",
    "validate",
    "test",
    "skills",
)

# dev subcommands that mutate the registry or user trees.
# Dispatch in main() checks this set and calls require_operator() before routing.
# Read-only subcommands (list, audit, diff) are intentionally absent.
MUTATING_DEV_COMMANDS = frozenset({
    "add", "merge", "split", "rename", "calibrate",
    "evidence", "rm-evidence", "link", "reclassify",
    "update-named", "timeline", "rm", "verify", "build",
})

# Known skill-convention files/dirs, in priority order
_SKILL_CANDIDATES = [
    'AGENTS.md',                         # OpenAI Codex
    'SKILLS.md',                         # generic
    'SKILL.md',                          # single named-skill file
    'agents.md',
    'skills.md',
    '.agents/skills',                    # Agent-agnostic skill directory
    '.claude/skills',                    # Claude Code skill directory (legacy)
    '.antigravity/skills',               # Antigravity skill directory (legacy)
    '.gemini',                           # Gemini skill directory (*.yml inside)
    '.github/copilot-instructions.md',   # GitHub Copilot
    'codex.yml',
    'gemini.yml',
    '.cursor/rules',                     # Cursor rules directory
]


def _detect_github_username():
    """Detect GitHub username from git remote URL, email, or display name."""
    import subprocess
    import re
    # Most reliable: parse github.com/USERNAME from origin remote URL
    try:
        r = subprocess.run(['git', 'remote', 'get-url', 'origin'],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            m = re.search(r'github\.com[:/]([^/]+?)(?:\.git)?(?:/|$)', r.stdout.strip())
            if m:
                return m.group(1)
    except Exception:
        pass
    # Fallback: noreply GitHub email (e.g. 12345+username@users.noreply.github.com)
    try:
        r = subprocess.run(['git', 'config', 'user.email'],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            m = re.match(r'^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$', r.stdout.strip())
            if m:
                return m.group(1)
    except Exception:
        pass
    # Fallback: git display name → slug
    try:
        r = subprocess.run(['git', 'config', 'user.name'],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            slug = re.sub(r'[^a-zA-Z0-9-]', '', r.stdout.strip().lower().replace(' ', '-'))
            if slug:
                return slug
    except Exception:
        pass
    return None


def _detect_skill_files():
    """Return existing skill-related paths in the current working directory."""
    return [c for c in _SKILL_CANDIDATES if os.path.exists(c)]


def whoami_command(args):
    from gaia_cli.authz import current_operator, authorization_status, OPERATOR_OVERRIDE_ENV
    registry_path = args.registry
    user = current_operator(registry_path)
    status = authorization_status(user, registry_path)
    authorized = status["authorized"]
    via = status["via"]
    reason = status["reason"]

    print(f"User:      {user}")
    print(f"Registry:  {registry_path}")
    print(f"Operator:  {'yes' if authorized else 'no'}  (via: {via})")
    print(f"Reason:    {reason}")
    print()
    if authorized:
        print("You can run all `gaia dev` subcommands (including mutating ones).")
    else:
        print("Read-only dev commands available:  gaia dev list / audit / diff")
        print("Mutating dev commands are blocked until you hold a 4★+ named skill.")
        print(f"CI/bots may bypass via {OPERATOR_OVERRIDE_ENV}=1 (always shown here).")


def init_command(args):
    config_dir = '.gaia'
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, 'config.toml')
    if os.path.exists(config_path) and not getattr(args, "force", False):
        print("Gaia is already initialized in this repository. Use --force to overwrite.")
        return

    username = args.user or _detect_github_username()
    if not username and sys.stdin.isatty() and not getattr(args, "yes", False):
        username = input("Gaia username: ").strip()
    username = username or "gaiabot"

    # Auto-detect skill files if no --scan flags given
    if args.scan:
        scan_paths = args.scan
    else:
        detected = _detect_skill_files()
        scan_paths = detected if detected else ["scripts", "packages/cli-npm"]

    local_registry_path = os.path.abspath(".")
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(f'username = "{username}"\n')
        f.write(f'gaiaRegistryRef = "{args.registry_ref or DEFAULT_REGISTRY_REF}"\n')
        f.write(f'localRegistryPath = "{local_registry_path}"\n')
        f.write(f'autoPromptCombinations = {"true" if args.auto_prompt_combinations else "false"}\n')
        f.write("scanPaths = [" + ", ".join(json.dumps(path) for path in scan_paths) + "]\n")
    print(f"Initialized Gaia configuration at {config_path}")
    print(f"  user:       {username}")
    print(f"  scanPaths:  {scan_paths}")
    print("Run `gaia fetch` to download the latest canonical registry, then `gaia scan` to link your local skills.")

    fetch_command(args)

    try:
        source = detect_source_repo({"gaiaUser": username})
        if sys.stdin.isatty() and not getattr(args, 'yes', False):
            try:
                if _use_color():
                    prompt = (
                        f"\n{_bold()}{_fg(99, 102, 241)}⚡ {_fg(255, 255, 255)}Detected repo: {_fg(45, 212, 191)}{source}{_reset()}\n"
                        f"{_bold()}{_fg(234, 179, 8)}? {_fg(255, 255, 255)}Initialize Gaia on this repository? "
                        f"{_fg(148, 163, 184)}[{_fg(74, 222, 128)}Y{_fg(148, 163, 184)}/n]: {_reset()}"
                    )
                else:
                    prompt = f"Detected repo: {source}\nInitialize Gaia on this repository? [Y/n]: "
                ans = input(prompt).strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                import shutil; shutil.rmtree(config_dir, ignore_errors=True)
                sys.exit(1)
            if ans == 'n':
                import shutil; shutil.rmtree(config_dir, ignore_errors=True)
                print("Aborted.")
                return
    except NonPublicRepoError:
        print(
            "\nNo GitHub remote detected in this directory.\n"
            "  → To unlock the full workflow:\n"
            "     • Add a remote:  git remote add origin https://github.com/<you>/<repo>\n"
            "     • Or clone the gaia-skill-tree registry and run gaia init there\n"
            "Your skills are still scannable and pushable — once linked to a public repo,\n"
            "approved skills will start at 2★ instead of 1★.\n"
        )

    # If we're inside a registry clone, register its path globally so that
    # commands like `gaia push` work from any project without --registry.
    tree_path = user_tree_path(".", username)
    if os.path.exists("registry/gaia.json") and not os.path.exists(tree_path):
        save_tree(username, {
            "userId": username,
            "updatedAt": date.today().isoformat(),
            "unlockedSkills": [],
            "pendingCombinations": [],
            "stats": {"totalUnlocked": 0, "highestRarity": "common", "deepestLineage": 0},
        }, registry_path=".")
        print(f"  skill tree: {tree_path}")

    if os.path.exists("registry/gaia.json"):
        registry_abs = os.path.abspath(".")
        write_global_registry(registry_abs)
        print(f"  registry:   {registry_abs} (saved to ~/.gaia/config.json)")
        
        # Auto-install git hooks
        hook_script = os.path.join(registry_abs, "scripts", "install-git-hooks.sh")
        if os.path.exists(hook_script):
            print("  git hooks:  found hook script (run manually if trusted: sh scripts/install-git-hooks.sh)")


def scan_command(args):
    config = load_config()
    if not config:
        print("Gaia not initialized. Run `gaia init` first.")
        return
    quiet = getattr(args, 'quiet', False)
    use_json = getattr(args, 'json', False)
    
    if not quiet and not use_json:
        print("Scanning repository...")
    scan_result = scan_repo_detailed()
    raw_tokens = {t.lstrip('/') for t in scan_result["tokens"]}
    graph_path = registry_graph_path(args.registry)

    from gaia_cli.registry import bundled_registry_path
    if not quiet and not use_json and str(args.registry) == str(bundled_registry_path()):
        print("Note: using bundled registry (no local registry clone found).")

    resolved = resolve_skills(raw_tokens, registry_path=graph_path)
    
    username = config.get('gaiaUser')
    canon = getattr(args, 'canon', False)
    
    # Unified local context for display
    ctx = LocalContext.load(args.registry, username or "", include_scan=False)

    if use_json:
        out = {
            "scanned": scan_result["files_scanned"],
            "candidates": scan_result["candidate_count"],
            "matched": sorted(list(resolved)),
        }
        print(json.dumps(out, indent=2))
        return

    if not quiet:
        print(
            f"Scanned {scan_result['files_scanned']} file(s) across "
            f"{len(scan_result['paths_found'])} configured path(s)."
        )
        if scan_result["paths_missing"]:
            print("Missing scan paths: " + ", ".join(scan_result["paths_missing"]))
        print(f"Found {scan_result['candidate_count']} candidate token(s).")
        print(f"Matched {len(resolved)} canonical skill(s).")
        if resolved:
            # Colored skill list with type glyphs
            graph_path_file = registry_graph_path(args.registry)
            if not os.path.exists(graph_path_file):
                print("Registry graph not found. Run `gaia init` from a gaia-skill-tree clone.")
                return
            with open(graph_path_file, 'r', encoding='utf-8') as gf:
                gdata = json.load(gf)
            smap = {s['id']: s for s in gdata.get('skills', [])}
            
            skill_parts = []
            for sid in sorted(resolved):
                sk = smap.get(sid, {})
                glyph = TYPE_SYMBOLS.get(sk.get('type', 'basic'), '○')
                
                # Resolve display name via LocalContext
                display = ctx.display_name(sid, canon=canon)
                rank_color = RANK_COLORS.get(sk.get('level', '0★'), RANK_COLORS["0★"])
                
                # Apply nickname coloring if not canon and it's a nickname
                if not canon and ("/" in display or sid in ctx.novel_ids):
                    # Check if it's our own nickname (starts with /)
                    if display.startswith("/"):
                        colored_name = f"{_fg(*COLOR_LOCAL_USER)}{_bold()}{display}{_reset()}"
                    else:
                        # Other contributor nickname: contrib in red, rest in rank
                        # color. Pre-named/demoted buckets arrive pre-redacted from
                        # the resolver (handle → REDACTED_BLOCK) — paint that
                        # segment slate, never honor-red.
                        parts = display.split("/", 1)
                        if len(parts) == 2:
                            handle_color = COLOR_REDACTED if parts[0] == REDACTED_BLOCK else COLOR_CONTRIBUTOR
                            colored_name = f"{_fg(*handle_color)}{parts[0]}{_reset()}/{_fg(*rank_color)}{parts[1]}{_reset()}"
                        else:
                            colored_name = f"{_fg(*rank_color)}{display}{_reset()}"
                else:
                    colored_name = f"{_fg(*rank_color)}{display}{_reset()}"
                
                skill_parts.append(f"  {glyph} {colored_name}")
            print("\n".join(skill_parts))
        else:
            print('Tip: try `gaia skills search "code review"` or expand scanPaths.')

    # ── Semantic scan: detect installed skill .md files ──────────────────────
    global_search = getattr(args, 'all', False)
    installed_skills = scan_skill_mds(global_search=global_search)
    if installed_skills:
        with open(graph_path, 'r', encoding='utf-8') as _gf:
            _gdata_for_match = json.load(_gf)
        canonical_list = _gdata_for_match.get('skills', [])
        smap_for_match = {s['id']: s for s in canonical_list}

        # Load ORIGIN and NAMED skills
        from gaia_cli.registry import named_skills_index_path
        origin_skills = []
        named_skills = []
        idx_path = named_skills_index_path(args.registry)
        if os.path.exists(idx_path):
            with open(idx_path, 'r', encoding='utf-8') as _nf:
                _ndata = json.load(_nf)
                for bucket, items in _ndata.get('buckets', {}).items():
                    for item in items:
                        if item.get('origin'):
                            origin_skills.append(item)
                        else:
                            named_skills.append(item)

        # Keep the matching logic that adds matching custom skills to resolved
        for sk in installed_skills:
            sid = sk['id']
            if sid in smap_for_match and sid not in resolved:
                resolved.append(sid)

        custom_state_skills = []
            
        for sk in installed_skills:
            cid = sk['id']
            location = sk.get('location', '')
            
            # Logic to resolve matching to canonical
            match = match_skill_to_canonical(
                cid, sk['name'], sk['description'], 
                canonical_list, origin_skills, named_skills, 
                threshold=0.15, origin_threshold=0.20
            )
            
            mapped_id = cid
            mapped_score = 1.0
            match_type = None
            canon_level = "0★"
            
            if match:
                canon_id, score, m_type = match
                mapped_id = canon_id
                mapped_score = score
                match_type = m_type
                
                if match_type == "origin":
                    canon_level = next((o.get("level", "0★") for o in origin_skills if o["id"] == canon_id), "0★")
                elif match_type == "named":
                    canon_level = next((n.get("level", "0★") for n in named_skills if n["id"] == canon_id), "0★")
                else:
                    canon_level = smap_for_match.get(canon_id, {}).get("level", "0★")
            elif cid not in smap_for_match:
                mapped_score = 0.0
            else:
                match_type = "exact_generic"
                mapped_score = 1.0

            custom_state_skills.append({
                "id": cid,
                "name": sk['name'],
                "description": sk['description'],
                "location": location,
                "mapped_to": mapped_id,
                "mapped_score": mapped_score,
                "match_type": match_type,
                "canon_level": canon_level,
                "prerequisites": sk.get("prerequisites", [])
            })

        if not quiet:
            print("\nInstalled custom skills:")
            
            # Group custom skills
            origin_group = []
            named_group = []
            generic_group = []
            other_group = []
            
            for sk in custom_state_skills:
                m_type = sk.get("match_type")
                if m_type == "origin":
                    origin_group.append(sk)
                elif m_type == "named":
                    named_group.append(sk)
                elif m_type in ("generic", "exact_generic"):
                    generic_group.append(sk)
                else:
                    other_group.append(sk)
            
            # Sort each group
            from gaia_cli.redaction import level_num
            origin_group.sort(key=lambda s: (-level_num(s.get("canon_level", "0★")), -s.get("mapped_score", 0.0), s["id"]))
            named_group.sort(key=lambda s: (-level_num(s.get("canon_level", "0★")), -s.get("mapped_score", 0.0), s["id"]))
            generic_group.sort(key=lambda s: (-s.get("mapped_score", 0.0), s["id"]))
            other_group.sort(key=lambda s: s["id"])

            COLOR_APEX_GOLD = (251, 191, 36)

            def print_group(group_id, skills):
                if not skills:
                    return
                
                # Format header with requested coloring
                if group_id == "origin":
                    title = f"{_fg(*COLOR_APEX_GOLD)}{_bold()}Origin Skills{_reset()}"
                elif group_id == "named":
                    title = f"{_fg(*COLOR_CONTRIBUTOR)}{_bold()}Named Skills{_reset()}"
                elif group_id == "generic":
                    title = f"{_bold()}Starless (Generic) Skills{_reset()}"
                else:
                    title = f"{_bold()}Custom - Only in this Repo{_reset()} ({_fg(*COLOR_LOCAL_USER)}{username}{_reset()})"
                
                print(f"\n{title}:")
                for sk in skills:
                    cid = sk['id']
                    location = sk['location']
                    mapped_id = sk['mapped_to']
                    mapped_score = sk['mapped_score']
                    m_type = sk.get("match_type")
                    
                    match_note = ""
                    if mapped_score > 0:
                        rank_color = RANK_COLORS.get(sk.get('canon_level', '0★'), RANK_COLORS["0★"])
                        star_ranking = sk.get('canon_level', '0★')
                        
                        if m_type in ("origin", "named") and "/" in mapped_id:
                            parts = mapped_id.split("/", 1)
                            contrib, nickname = parts
                            if contrib == username:
                                handle_color = COLOR_LOCAL_USER
                            elif contrib == REDACTED_BLOCK:
                                handle_color = COLOR_REDACTED
                            else:
                                handle_color = COLOR_CONTRIBUTOR
                            colored_mapped = f"{_fg(*handle_color)}{contrib}{_reset()}/{_fg(*rank_color)}{nickname} {star_ranking}{_reset()}"
                        else:
                            colored_mapped = f"{_fg(*rank_color)}/{mapped_id}{_reset()}"
                        
                        if m_type == "origin":
                            match_note = f"  {_fg(100,100,100)}→ {colored_mapped}{_reset()}"
                        elif m_type == "named":
                            match_note = f"  {_fg(100,100,100)}→ {colored_mapped}{_reset()}"
                        elif m_type == "exact_generic":
                            match_note = f"  {_fg(100,100,100)}→ {colored_mapped}{_reset()}"
                        else:
                            match_note = f"  {_fg(100,100,100)}→ {colored_mapped}{_fg(100,100,100)} ({mapped_score:.0%} semantic){_reset()}"
                    
                    user_label = f"{_fg(*COLOR_LOCAL_USER)}{_bold()}/{cid}{_reset()}"
                    if group_id == "other":
                        user_label = f"{user_label} {_fg(*RANK_COLORS['0★'])}0★{_reset()}"
                    
                    print(f"  ○ {user_label} custom skill{match_note}")
                    print(f"    (found in {location})")

            print_group("origin", origin_group)
            print_group("named", named_group)
            print_group("generic", generic_group)
            print_group("other", other_group)

            if other_group:
                print(f"\n{_fg(99, 102, 241)}⚡ {_bold()}{_fg(255, 255, 255)}Tip: Run `{_fg(45, 212, 191)}gaia push{_fg(255, 255, 255)}` to submit your custom skills for review.{_reset()}")

        # Clean up output fields to keep file clean
        for sk in custom_state_skills:
            sk.pop("match_type", None)
            sk.pop("canon_level", None)

        # Persist the custom state mapping
        os.makedirs(".gaia", exist_ok=True)
        with open(".gaia/custom_state.json", "w", encoding="utf-8") as f:
            json.dump({"customSkills": custom_state_skills}, f, indent=2)

    tree = load_tree(username, registry_path=args.registry)
    if tree:
        with open(graph_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        skill_map = {s['id']: s for s in graph_data.get('skills', [])}
        unlocked = [s.get('skillId') for s in tree.get('unlockedSkills', [])]
        combos = get_combinations(graph_data, unlocked, resolved)
        if combos:
            # Persist fusion candidates so `gaia fuse` can find them
            tree['pendingCombinations'] = combos
            save_tree(username, tree, registry_path=args.registry)
            if not quiet:
                print("\nNew fusion candidates:")
                for c in combos:
                    result_skill = skill_map.get(c['candidateResult'], {})
                    result_type = result_skill.get('type', 'extra')
                    print(render_fusion_diagram(
                        c['detectedSkills'], c['candidateResult'], result_type,
                        canon=canon, ctx=ctx
                    ))
                print("Run `gaia fuse <skill>` to confirm.")

        # Path engine integration
        old_paths = load_paths()
        owned_ids = [s.get('skillId') for s in tree.get('unlockedSkills', [])]
        new_paths = compute_paths(graph_data, owned_ids, resolved)
        new_paths["userId"] = username
        changes = diff_paths(old_paths, new_paths)
        save_paths(new_paths)

        # Show unlock cards for newly reachable skills
        if changes.get("new_near_unlocks"):
            print()
            for sid in changes["new_near_unlocks"]:
                skill = skill_map.get(sid)
                if skill:
                    opened = [p for p in new_paths.get("availablePaths", []) if p.get("distance", 99) <= 2]
                    print(render_unlock_card(skill, opened[:3], canon=canon, ctx=ctx))
                    print()

        # Path summary
        if new_paths.get("nearUnlocks") or new_paths.get("oneAway"):
            print(render_path_summary(new_paths))

        render_user_tree_outputs(username, tree, graph_data, args.registry, quiet=quiet)


def render_user_tree_outputs(username: str, tree: dict | None, graph_data: dict | None, registry_path: str, quiet: bool = False) -> tuple[str, str] | None:
    if not tree:
        return None
    mode = "default"
    buf = StringIO()
    with redirect_stdout(buf):
        show_tree(tree, graph_data=graph_data, registry_path=registry_path, mode=mode)
    text = buf.getvalue()
    out_dir = generated_output_dir(registry_path)
    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, "tree.md")
    html_path = os.path.join(out_dir, "tree.html")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Gaia Skill Tree\n\n```text\n")
        f.write(text)
        f.write("```\n")
    html = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>Gaia Skill Tree - {username}</title>"
        "<style>body{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;margin:2rem;line-height:1.45}"
        "pre{white-space:pre-wrap}</style></head><body>"
        f"<h1>Gaia Skill Tree - {username}</h1><pre>"
        + text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        + "</pre></body></html>\n"
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    if not quiet:
        print(f"  saved {html_path} & {md_path}")
    return html_path, md_path


def promote_all_candidates(username: str, registry_path: str) -> list[dict]:
    promoted = []
    for candidate in promotable_candidates(registry_path, username=username):
        promoted.append(promote_from_candidates(
            username,
            candidate["skillId"],
            registry_path,
        ))
    return promoted


def _entry_role(entry):
    return entry.get("role") or ("origin" if entry.get("origin") is True else "variant")


def lookup_command(args):
    graph_path = registry_graph_path(args.registry)
    if not os.path.exists(graph_path):
        print("Registry graph not found.", file=sys.stderr)
        sys.exit(1)

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    query = args.skillId.strip().lstrip("/")
    skill_map = {s["id"]: s for s in graph_data.get("skills", [])}
    skill = skill_map.get(query)
    if not skill:
        matches = [
            s for s in graph_data.get("skills", [])
            if query.lower() in s.get("id", "").lower()
            or query.lower() in s.get("name", "").lower()
        ]
        if len(matches) == 1:
            skill = matches[0]
        else:
            print(f"Skill '{query}' not found.", file=sys.stderr)
            if matches:
                print("Matches:")
                for candidate in matches[:10]:
                    print(f"  /{candidate['id']} - {candidate.get('name', candidate['id'])}")
            sys.exit(1)

    skill_id = skill["id"]
    canon = getattr(args, 'canon', False)

    config = load_config() or {}
    username = config.get("gaiaUser")
    ctx = LocalContext.load(args.registry, username, include_scan=False) if username else None

    if canon:
        display = f"/{skill_id}"
    elif ctx and ctx.is_named(skill_id):
        display = ctx.display_name(skill_id)
    else:
        display = skill.get("name") or f"/{skill_id}"
    print(f"{display}")
    
    user_level = ctx.skill_level(skill_id) if ctx else skill.get('level', '?')
    print(f"Type: {skill.get('type', 'unknown')}    Level: {user_level}")
    if skill.get("description"):
        print(skill["description"])

    named_path = named_skills_index_path(args.registry)
    named_index = {}
    if os.path.exists(named_path):
        with open(named_path, "r", encoding="utf-8") as f:
            named_index = json.load(f)
    entries = named_index.get("buckets", {}).get(skill_id, [])
    if entries:
        print("\nNamed implementations:")
        for entry in entries:
            role = _entry_role(entry)
            name = entry.get("name") or entry.get("id", "unknown")
            entry_id = entry.get("id", "unknown")
            print(f"- [{role}] {name} ({entry_id})")
    else:
        print("\nNamed implementations: none")

def status_command(args):
    config = load_config()
    if not config:
        print("Gaia not initialized.")
        return
    username = config.get('gaiaUser')
    tree = load_tree(username, registry_path=args.registry)
    if not tree:
        print(f'No skill tree found for user "{username}".')
        print("Next steps:")
        print("  gaia scan")
        print("  gaia push --dry-run")
        print("  gaia push --no-pr")
        print(f"Or create skill-trees/{username}/skill-tree.json in the registry.")
        return
    show_status(tree)


def appraise_command(args):
    """Render an appraise card for a skill."""
    config = load_config()
    if not config:
        print("Gaia not initialized. Run `gaia init` first.")
        return

    graph_path = registry_graph_path(args.registry)
    if not os.path.exists(graph_path):
        print("Registry graph not found.")
        return

    with open(graph_path, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)

    skill_map = {s['id']: s for s in graph_data.get('skills', [])}
    username = config.get('gaiaUser')
    tree = load_tree(username, registry_path=args.registry)

    # Determine which skill to appraise
    skill_id = getattr(args, 'skillId', None)
    if not skill_id:
        # Try interactive picker first
        all_skills = list(skill_map.values())
        picked = select_skill(all_skills, "Select a skill to appraise:")
        if picked:
            skill_id = picked
        elif tree and tree.get('unlockedSkills'):
            # Fallback: most recently unlocked skill
            sorted_skills = sorted(
                tree['unlockedSkills'],
                key=lambda s: s.get('unlockedAt', ''),
                reverse=True,
            )
            skill_id = sorted_skills[0]['skillId']
        else:
            # Fall back to most recent near-unlock from paths
            paths = load_paths()
            if paths and paths.get('nearUnlocks'):
                skill_id = paths['nearUnlocks'][0]['skillId']
            else:
                print("No skill to appraise. Pass a skill ID or run `gaia scan` first.")
                return

    skill = skill_map.get(skill_id)
    if not skill:
        print(f"Skill '{skill_id}' not found in registry.")
        return

    # Build prereq status
    owned_ids = set()
    if tree:
        owned_ids = {s['skillId'] for s in tree.get('unlockedSkills', [])}
    # Also include detected skills from paths
    paths = load_paths()
    detected_ids = set()
    if paths:
        for nu in paths.get("nearUnlocks", []):
            detected_ids.update(nu.get("satisfiedPrereqs", []))
        for oa in paths.get("oneAway", []):
            detected_ids.update(oa.get("satisfiedPrereqs", []))
    available = owned_ids | detected_ids

    prereq_status = {}
    for p in skill.get('prerequisites', []):
        prereq_status[p] = p in available

    # Derivatives
    derivatives = []
    for d_id in skill.get('derivatives', []):
        d_skill = skill_map.get(d_id)
        if d_skill:
            derivatives.append(d_skill)
        else:
            derivatives.append({"id": d_id, "name": d_id, "type": "unknown"})

    # Contextual actions
    owned = skill_id in owned_ids
    actions = []
    if not owned and all(prereq_status.values()) and prereq_status:
        actions.append("[F] Fuse")
    if owned:
        state = promotion_state(skill_id, tree, graph_data)
        if state == "eligible":
            actions.append("[P] Promote")
    actions.append("[S] Scan")
    if derivatives:
        actions.append("[→] Paths")

    # Local-first display name
    canon = getattr(args, "canon", False)
    ctx = LocalContext.load(args.registry, username or "", include_scan=False)
    display_name = ctx.display_name(skill_id, canon=canon)

    print(render_appraise_card(
        skill, prereq_status, derivatives, actions, 
        owned=owned, canon=canon, display_name=display_name
    ))
    try:
        candidates = load_promotion_candidates(args.registry).get("candidates", [])
        matching = [c for c in candidates if c.get("skillId") == skill_id]
        if matching:
            labels = ", ".join(c.get("suggestedLevel", "?") for c in matching)
            print(f"\nLast scan flagged this skill as promotable to: {labels}")
    except ValueError:
        pass


def promote_command(args):
    """Run promotion flow for an eligible skill."""
    config = load_config()
    if not config:
        print("Gaia not initialized.")
        return

    username = config.get('gaiaUser')
    graph_path = registry_graph_path(args.registry)

    if not os.path.exists(graph_path):
        print("Registry graph not found.")
        return

    with open(graph_path, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)

    tree = load_tree(username, registry_path=args.registry)
    if not tree:
        if not os.path.exists(promotion_candidates_path(args.registry)):
            print("No promotion candidates found. Run `gaia scan` first to detect skills.",
                  file=sys.stderr)
        else:
            print(f"No skill tree found for user '{username}'.", file=sys.stderr)
        return

    skill_id = getattr(args, 'skillId', None)
    display_name = getattr(args, 'name', None)

    try:
        if getattr(args, "unique", False):
            if not skill_id:
                print("Usage: gaia promote <skill> --unique", file=sys.stderr)
                sys.exit(2)
            from .promotion import promote_to_unique
            result = promote_to_unique(skill_id, args.registry)
            print(f"\n◉ {result['displayName']} promoted to Unique Skill (type: unique)!")
            print(f"  Level: {result['level']}")
            print()
            return

        if getattr(args, "all", False):
            results = promote_all_candidates(username, args.registry)
            if not results:
                print("No skills eligible for promotion.")
                return
            for result in results:
                print(f"Promoted /{result['skillId']} to Level {result['newLevel']}.")
            return
        if not skill_id:
            # Try interactive picker
            candidates = promotable_candidates(args.registry, username)
            if candidates:
                picked = select_promotion_candidate(candidates, "Select skill to promote:")
                if picked:
                    skill_id = picked
            if not skill_id:
                from gaia_cli.registry import promotion_candidates_path
                if not os.path.exists(promotion_candidates_path(args.registry)):
                    print("No promotion candidates found. Run `gaia scan` first to detect skills.",
                          file=sys.stderr)
                else:
                    print("Usage: gaia promote <skill> or gaia promote --all", file=sys.stderr)
                sys.exit(2)
        result = promote_from_candidates(username, skill_id, args.registry, new_display_name=display_name)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    # Show celebration
    skill_map = {s['id']: s for s in graph_data.get('skills', [])}
    skill = skill_map.get(skill_id, {"id": skill_id, "name": skill_id, "type": "basic"})
    level_name = LEVEL_NAMES.get(result["newLevel"], result["newLevel"])
    print(f"\n✦ {skill.get('name', skill_id)} promoted to Level {result['newLevel']} ({level_name})!")
    if display_name:
        print(f"  Renamed to: {display_name}")
    print()


def propose_command(args):
    """Propose a single canonical skill as a named skill intake."""
    config = load_config()
    if not config:
        print("Gaia not initialized.")
        return
    skill_id = (getattr(args, "skillId", "") or "").lstrip("/")
    graph_path = registry_graph_path(args.registry)
    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
    skill_map = {s["id"]: s for s in graph_data.get("skills", [])}
    skill = skill_map.get(skill_id)
    if not skill:
        print(f"Skill '{skill_id}' not found in canonical graph.")
        return
    if getattr(args, "ultimate", False) and skill.get("type") != "ultimate":
        print(f"Skill '{skill_id}' is not an ultimate skill. Use --ultimate only for ultimate skills.")
        return
    if not getattr(args, "ultimate", False) and skill.get("type") == "ultimate":
        print("Tip: this is an ultimate skill. Re-run with `gaia propose /<skill> --ultimate`.")

    print(f"Appraisal: /{skill['id']} ({skill.get('type', 'unknown')})")
    print(f"Name: {skill.get('name', skill['id'])}")
    print(f"Description: {skill.get('description', '')}")

    suggested = f"{config.get('gaiaUser', 'gaiabot')}/{skill_id}"
    target_named = getattr(args, "target", None)
    if not target_named:
        if sys.stdin.isatty() and not getattr(args, "yes", False):
            target_named = input(f"Name this skill as [{suggested}]: ").strip() or suggested
        else:
            target_named = suggested
    if "/" not in target_named:
        print("Named skill must be in '<contributor>/<name>' format.")
        return
    contributor, skill_name = target_named.split("/", 1)

    proposed_skill = build_proposed_skill(skill_id, detect_source_repo(config))
    proposed_skill["name"] = skill.get("name", proposed_skill["name"])
    proposed_skill["description"] = skill.get("description", proposed_skill["description"])
    proposed_skill["type"] = skill.get("type", "basic")
    batch = {
        "batchId": f"proposal-{skill_id}-{date.today().isoformat()}",
        "userId": config.get("gaiaUser", "unknown"),
        "sourceRepo": detect_source_repo(config),
        "generatedAt": f"{date.today().isoformat()}T00:00:00Z",
        "knownSkills": [{"skillId": skill_id}],
        "proposedSkills": [proposed_skill],
        "similarity": [],
    }
    batch_path = write_skill_batch(batch, args.registry)
    promote_to_named(proposed_skill, contributor, skill_name, args.registry)
    update_batch_lifecycle(batch_path, skill_id, "named")

    from gaia_cli.timeline import append_skill_tree_event
    append_skill_tree_event(
        config.get("gaiaUser", "unknown"),
        skill_id,
        "propose",
        f"Proposed as named skill {target_named}",
        registry_path=args.registry
    )
    print(f"Proposed named skill: {target_named}")
    print(f"  saved {os.path.basename(batch_path)}")

    if getattr(args, "no_pr", False) or getattr(args, "no_issue", False):
        print("Skipped issue creation (--no-pr/--no-issue).")
        return
    open_intake_issue(config.get("gaiaUser", "unknown"), batch, batch_path=batch_path, repo_root=args.registry)


def paths_command(args):
    """Display current progression paths."""
    paths = load_paths()
    if not paths:
        print("No paths computed yet. Run `gaia scan` first.")
        return

    print(render_path_summary(paths))
    print()

    near = paths.get("nearUnlocks", [])
    if near:
        print("Ready to fuse:")
        for n in near:
            print(f"  ◇ {n.get('name', n['skillId'])} ({n.get('type', '?')})")
            if n.get("levelFloor") and n.get("effectiveLevelFloor"):
                print(f"    level: {n.get('levelFloor')} (effective: {n.get('effectiveLevelFloor')})")
            prereqs = n.get('satisfiedPrereqs', [])
            if prereqs:
                print(f"    from: {', '.join(prereqs)}")
        print()

    one_away = paths.get("oneAway", [])
    if one_away:
        print("One prerequisite away:")
        for o in one_away[:8]:
            print(f"  ○ {o.get('name', o['skillId'])} - missing: {o.get('missingPrereq', '?')}")
            if o.get("levelFloor") and o.get("effectiveLevelFloor"):
                print(f"    level: {o.get('levelFloor')} (effective: {o.get('effectiveLevelFloor')})")
        if len(one_away) > 8:
            print(f"  ... and {len(one_away) - 8} more")
        print()


def path_command(args):
    """Print a prerequisite unlock-path tree toward a target skill.

    Accepts canonical IDs or slash-form IDs (leading slash is stripped).
    Exits with code 1 when the skill ID is unknown or a cycle is detected.
    """
    graph_path = registry_graph_path(args.registry)
    if not os.path.exists(graph_path):
        print("Registry graph not found.", file=sys.stderr)
        sys.exit(1)

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    # Accept /skill-id form and plain id form.
    skill_id = args.skillId.strip().lstrip("/")

    # Resolve owned skills from user tree.
    config = load_config() or {}
    username = config.get("gaiaUser") or ""
    tree = load_tree(username, registry_path=args.registry) if username else None
    owned_ids: set[str] = set()
    if tree:
        owned_ids = {s["skillId"] for s in tree.get("unlockedSkills", []) if s.get("skillId")}

    use_json = getattr(args, "json", False)
    owned_only = getattr(args, "owned_only", False)

    try:
        if use_json:
            from gaia_cli.pathEngine import unlock_path, _path_tree_to_dict
            tree_node = unlock_path(graph_data, skill_id, owned_ids)
            skill_map = {s["id"]: s for s in graph_data.get("skills", [])}
            out = {
                "skillId": skill_id,
                "ownedIds": sorted(owned_ids),
                "tree": _path_tree_to_dict(tree_node, skill_map),
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            text = render_unlock_path(graph_data, skill_id, owned_ids, owned_only=owned_only)
            print(text)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def hook_command(args):
    """Internal command invoked by Claude Code hook."""
    hook_entry(event=getattr(args, 'event', 'file_edit'))


def doctor_command(args):
    config_path = ".gaia/config.toml"
    config = load_config()
    registry_path = os.path.abspath(str(args.registry))
    print("Gaia CLI: OK")
    print(f"Registry path: {args.registry}")
    print(f"Registry graph: {'found' if os.path.exists(registry_graph_path(registry_path)) else 'missing'}")
    print(f"Config: {config_path if os.path.exists(config_path) else 'missing'}")
    if not config:
        print("User: unknown")
        print("Skill tree: unknown")
        return

    username = config.get('gaiaUser')
    print(f"User: {username}")
    tree_path = user_tree_path(registry_path, username or '')
    print(f"Skill tree: {'found' if os.path.exists(tree_path) else 'missing'}")
    emb_path = embeddings_path(registry_path)
    print(f"Embeddings: {'found' if os.path.exists(emb_path) else 'missing'}")
    print("Scan paths:")
    for path in config.get('scanPaths', []):
        print(f"  - {path} {'exists' if os.path.exists(path) else 'missing'}")

def tree_command(args):
    if getattr(args, 'check', False):
        from gaia_cli.treeManager import show_color_check
        show_color_check()
        return
    config = load_config()
    if not config:
        print("Gaia not initialized.")
        return
    graph_data = None
    graph_path = registry_graph_path(args.registry)
    if os.path.exists(graph_path):
        with open(graph_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
    tree = load_tree(config.get('gaiaUser'), registry_path=args.registry)
    mode = "named" if getattr(args, 'named', False) else ("title" if getattr(args, 'title', False) else "default")
    canon = getattr(args, 'canon', False)
    custom = getattr(args, 'custom', False) or (not canon)
    show_tree(tree, graph_data=graph_data, registry_path=args.registry, mode=mode, canon=canon, custom=custom)
    if tree:
        render_user_tree_outputs(config.get('gaiaUser'), tree, graph_data, args.registry, quiet=False)
    try:
        detect_source_repo(config)
    except NonPublicRepoError:
        print("\nTip: link a public GitHub repo and approved skills will start at 2★ once named.")
    except Exception:
        pass

def fuse_command(args):
    config = load_config()
    if not config:
        return
    username = config.get('gaiaUser')
    tree = load_tree(username, registry_path=args.registry)
    if not tree:
        return

    target = getattr(args, 'skillId', None)
    display_name = getattr(args, 'name', None)

    # Interactive picker when no target specified
    if not target:
        pending_combos = tree.get('pendingCombinations', [])
        if pending_combos:
            picked = select_fusion_candidate(pending_combos, "Select fusion candidate:")
            if picked:
                target = picked
        if not target:
            print("Usage: gaia fuse <skill>", file=sys.stderr)
            print("Run `gaia scan` to detect fusion candidates.")
            return

    # Check combinations first
    pending_combos = tree.get('pendingCombinations', [])
    combo_match = next((p for p in pending_combos if p.get('candidateResult') == target), None)
    
    if combo_match:
        print(f"Fusing combination /{target}...")
        tree.setdefault('unlockedSkills', []).append({
            "skillId": target,
            "level": combo_match.get('levelFloor'),
            "unlockedAt": datetime.now(timezone.utc).isoformat(),
            "unlockedIn": "local-repo",
            "combinedFrom": combo_match.get('detectedSkills', [])
        })
        tree['pendingCombinations'] = [p for p in pending_combos if p.get('candidateResult') != target]
        stats = tree.get('stats', {})
        stats['totalUnlocked'] = stats.get('totalUnlocked', 0) + 1
        tree['stats'] = stats
        save_tree(username, tree, registry_path=args.registry)

        from gaia_cli.timeline import append_skill_tree_event
        append_skill_tree_event(
            username,
            target,
            "fuse",
            f"Fused from {', '.join(combo_match.get('detectedSkills', []))}",
            registry_path=args.registry
        )

        open_pr(username, tree, candidate_result=target)
        return

    # Check promotions next
    try:
        payload = load_promotion_candidates(args.registry)
        if any(c.get('skillId') == target for c in payload.get('candidates', [])):
            print(f"Fusing promotion for /{target}...")
            result = promote_from_candidates(username, target, args.registry, new_display_name=display_name)
            print(f"Promoted /{result['skillId']} to Level {result['newLevel']}.")
            return
    except Exception:
        pass

    print(f"Skill /{target} is not a valid combination or promotion candidate.")
    print("Run `gaia scan` to refresh candidates.")

_EMBEDDINGS_INSTALL_STEPS = """\

  +----------------------------------------------------------------+
  |  Semantic search requires the embeddings package.              |
  +----------------------------------------------------------------+

  Step 1 -- Install the embeddings library:
            pip install "gaia-cli[embeddings]"

  Step 2 -- Generate embeddings (run once, ~30 seconds):
            gaia embed

  Step 3 -- Search:
            gaia skills search "<your query>"

  Tip: Re-run `gaia embed` whenever new skills are added to the registry.\
"""

_EMBEDDINGS_MISSING_STEPS = """\

  +----------------------------------------------------------------+
  |  Embeddings have not been generated yet.                       |
  +----------------------------------------------------------------+

  Generate them now (run once from the registry root, ~30 seconds):
    gaia embed

  Then retry:
    gaia skills search "{query}"

  Tip: Re-run `gaia embed` whenever new skills are added to the registry.\
"""


def embed_command(args):
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        print(_EMBEDDINGS_INSTALL_STEPS)
        sys.exit(1)
    generate_embeddings(registry_path=args.registry)

def search_command(args):
    emb_path = embeddings_path(args.registry)
    try:
        results = semantic_search(args.query, emb_path, top_k=args.top_k)
    except FileNotFoundError:
        print(_EMBEDDINGS_MISSING_STEPS.format(query=args.query))
        return
    except ImportError:
        print(_EMBEDDINGS_INSTALL_STEPS)
        return
    if not results:
        print("No results found.")
        return
    col_id = max(len(r['id']) for r in results)
    col_id = max(col_id, 4)  # at least width of "Skill"
    header = f"{'Rank':<5}  {'Skill':<{col_id}}  {'Score'}"
    print(header)
    print("-" * len(header))
    for rank, r in enumerate(results, start=1):
        print(f"{rank:<5}  {r['id']:<{col_id}}  {r['score']:.4f}")

def push_command(args):
    config = load_config()
    if not config:
        print("Gaia not initialized. Run `gaia init` first.", file=sys.stderr)
        sys.exit(1)

    raw_tokens = scan_repo()
    try:
        batch = build_skill_batch(raw_tokens, config, args.registry)
        source_repo = batch["sourceRepo"]
        if sys.stdin.isatty() and not getattr(args, 'yes', False):
            try:
                ans = input(f"Push skills to gaia registry from {source_repo}? [Y/n]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                sys.exit(1)
            if ans == 'n':
                print("Aborted.")
                return
    except NonPublicRepoError as exc:
        print(
            "\nYour skills are ready for review!\n"
            "Skills pushed from outside a public GitHub repo start at 1★ in the registry.\n"
            "Once you link a public repo, approved skills will start at 2★ instead.\n"
            "  → Add a remote:  git remote add origin https://github.com/<you>/<repo>\n",
            file=sys.stderr,
        )
        username_fallback = str(exc)
        batch = build_skill_batch(raw_tokens, config, args.registry,
                                  source_repo=f"{username_fallback}/local-repo")

    # Guard 1: check if empty initially
    if not batch.get("proposedSkills") and not batch.get("knownSkills"):
        print("Error: No skills to be pushed. Please install newer skills then gaia scan, or fuse custom skills before pushing.", file=sys.stderr)
        sys.exit(1)

    # Custom skills injection and interactive exclusion
    installed_skills = scan_skill_mds(global_search=False)
    batch_proposed_ids = {s["id"] for s in batch.get("proposedSkills", [])}
    batch_known_ids = {s["skillId"] for s in batch.get("knownSkills", [])}

    # Ensure all local custom skills are included in the batch
    for sk in installed_skills:
        cid = sk["id"]
        if cid not in batch_proposed_ids and cid not in batch_known_ids:
            batch.setdefault("proposedSkills", []).append({
                "id": cid,
                "name": sk.get("name", cid),
                "type": "basic",
                "description": sk.get("description", f"Local custom skill {cid}"),
                "sourceRepo": batch.get("sourceRepo", "unknown"),
                "lifecycle": "pending",
            })
            batch_proposed_ids.add(cid)

    pushable_custom_skills = installed_skills

    if pushable_custom_skills:
        pushable_custom_skills.sort(key=lambda x: x["id"])
        print("The following custom skills will be pushed:")
        for idx, sk in enumerate(pushable_custom_skills, 1):
            print(f"  {idx}. /{sk['id']} (found in {sk.get('location', '')})")
        print()

        try:
            user_input = input("Please select which skills you do NOT want to push (space or comma separated numbers, or press Enter to push all): ")
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(1)

        excluded_ids = set()
        if user_input.strip():
            import re
            tokens = re.split(r'[,\s]+', user_input.strip())
            for t in tokens:
                if t.isdigit():
                    idx = int(t) - 1
                    if 0 <= idx < len(pushable_custom_skills):
                        excluded_ids.add(pushable_custom_skills[idx]["id"])

        if excluded_ids:
            batch["proposedSkills"] = [s for s in batch.get("proposedSkills", []) if s["id"] not in excluded_ids]
            batch["knownSkills"] = [s for s in batch.get("knownSkills", []) if s["skillId"] not in excluded_ids]
            batch["similarity"] = [s for s in batch.get("similarity", []) if s.get("sourceSkillId") not in excluded_ids]

    # Guard 2: check if empty after filtering
    if not batch.get("proposedSkills") and not batch.get("knownSkills"):
        print("Error: No skills to be pushed. Please install newer skills then gaia scan, or fuse custom skills before pushing.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(json.dumps(batch, indent=2))
        return

    batch_path = write_skill_batch(batch, args.registry)
    print(f"  saved {os.path.basename(batch_path)}")

    from gaia_cli.timeline import append_skill_tree_event
    username = config.get('gaiaUser')
    if username:
        for known in batch.get("knownSkills", []):
            append_skill_tree_event(
                username,
                known.get("skillId"),
                "push",
                f"Pushed in batch {batch.get('batchId')}",
                registry_path=args.registry
            )

    if getattr(args, 'no_issue', False):
        print("Skipped issue creation (--no-issue).")
        return
    open_intake_issue(username, batch, batch_path=batch_path, repo_root=args.registry)

def name_command(args):
    with open(args.batch_file, "r") as f:
        batch = json.load(f)

    proposed_skills = batch.get("proposedSkills", [])
    if args.skill_index < 0 or args.skill_index >= len(proposed_skills):
        print(
            f"Error: skill-index {args.skill_index} is out of range "
            f"(batch has {len(proposed_skills)} proposed skills).",
            file=sys.stderr,
        )
        sys.exit(1)

    skill_data = proposed_skills[args.skill_index]
    lifecycle = skill_data.get("lifecycle", "pending")
    if lifecycle not in ("pending", "awakened"):
        print(
            f"Error: skill '{skill_data['id']}' has lifecycle '{lifecycle}'. "
            "Only 'pending' or 'awakened' skills can be promoted to named.",
            file=sys.stderr,
        )
        sys.exit(1)

    parts = args.named_id.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        print(
            f"Error: named ID must be in the form 'contributor/skill-name', "
            f"got '{args.named_id}'.",
            file=sys.stderr,
        )
        sys.exit(1)
    contributor, skill_name = parts

    named_path = promote_to_named(skill_data, contributor, skill_name, args.registry)
    update_batch_lifecycle(args.batch_file, skill_data["id"], "named")
    print(f"Named skill created: {named_path}")
    print(f"Batch lifecycle updated: '{skill_data['id']}' -> named")

def _resolve_install_location(args) -> str:
    """Extract location from --install-location flag, defaulting to 'local'."""
    location = getattr(args, 'install_location', None)
    if location in ("local", "global"):
        return location
    return "local"


def install_command(args):
    from gaia_cli.install import interactive_install, install_skill, install_suite, update_skills
    location = _resolve_install_location(args)

    if args.list:
        interactive_install(args.registry, location=location)
        return
    if not args.skill_id:
        print("Usage: gaia install <skill_id>", file=sys.stderr)
        print("  To update all installed skills, use: gaia update", file=sys.stderr)
        sys.exit(2)

    # Use suite logic if flagged or implicitly requested
    if getattr(args, 'ultimate', False) or getattr(args, 'suite', False):
        success = install_suite(args.skill_id, args.registry, location=location)
    else:
        success = install_skill(args.skill_id, args.registry, location=location)

    if not success:
        sys.exit(1)


def uninstall_command(args):
    from gaia_cli.install import uninstall_skill
    success = uninstall_skill(args.skill_id.lstrip("/"))
    if not success:
        sys.exit(1)


def _load_json_file(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _pending_skills(registry_path: str, username: str | None = None) -> list[dict]:
    batches_root = Path(skill_batches_dir(registry_path))
    paths = []
    if batches_root.is_dir():
        paths.extend(batches_root.glob("*.json"))
        paths.extend(batches_root.glob("*/*.json"))
    pending = []
    for path in sorted(paths):
        batch = _load_json_file(str(path), default={}) or {}
        if username and batch.get("userId") not in (None, username):
            continue
        for skill in batch.get("proposedSkills", []):
            if skill.get("lifecycle", "pending") == "pending":
                pending.append({
                    "id": skill.get("id"),
                    "name": skill.get("name", skill.get("id")),
                    "description": skill.get("description", ""),
                    "level": skill.get("level", "1★"),
                    "pending": True,
                })
    return pending


def skills_command(args):
    from gaia_cli.install import list_available, install_skill, install_suite, uninstall_skill, update_skills
    config = load_config() or {}
    username = config.get("gaiaUser") or config.get("username")
    pending = [] if getattr(args, "exclude_pending", False) else _pending_skills(args.registry, username)
    verb = getattr(args, "skills_command", None)
    if verb == "install":
        location = _resolve_install_location(args)
        if getattr(args, "suite", False):
            success = install_suite(args.skill_id, args.registry, location=location)
        else:
            success = install_skill(args.skill_id, args.registry, location=location)
        if not success:
            sys.exit(1)
        return
    if verb == "update":
        update_skills(args.registry)
        return
    if verb == "uninstall":
        success = uninstall_skill(args.skill_id.lstrip("/"))
        if not success:
            sys.exit(1)
        return


    available = [
        {"id": sid, "name": meta.get("name") or sid, "level": meta.get("level", "?"), "type": meta.get("type", "basic"), "description": meta.get("description", "")}
        for sid, meta in list_available(args.registry)
    ]
    items = available + pending
    query = getattr(args, "query", None)
    if verb == "search" and query:
        q = query.lower()
        items = [
            item for item in items
            if q in str(item.get("id", "")).lower()
            or q in str(item.get("name", "")).lower()
            or q in str(item.get("description", "")).lower()
        ]

    # Build local context for named-first display
    config = load_config() or {}
    ctx_user = config.get("gaiaUser") or config.get("username") or ""
    try:
        ctx = LocalContext.load(args.registry, ctx_user, include_scan=False)
    except Exception:
        ctx = None

    if verb == "info":
        q = args.skill_id.lstrip("/")
        match = next((item for item in items if item.get("id") == q), None)
        if not match:
            print(f"Skill '/{q}' not found.", file=sys.stderr)
            sys.exit(1)
        sid = match.get("id", q)
        level = match.get("level", "?")
        skill_type = match.get("type", "basic")
        named_contrib = ctx.named_contributor(sid) if ctx and ctx.is_named(sid) else None
        is_local = ctx.is_local(sid) if ctx else False
        display = format_skill_colored(sid, level, named_contributor=named_contrib,
                                       is_local=is_local, local_user=ctx_user)
        suffix = " (pending)" if match.get("pending") else ""
        print(f"{display}{suffix}")
        print(f"  Type:  {format_type_colored(skill_type)}")
        print(f"  Level: {format_level_colored(level)}")
        if match.get("description"):
            print(f"  {match['description']}")
        return
    if not items:
        print("No skills found.")
        return

    width = max(5, *(len(format_skill_plain(
        item.get("id", ""),
        named_contributor=ctx.named_contributor(item.get("id", "")) if ctx and ctx.is_named(item.get("id", "")) else None,
        is_local=ctx.is_local(item.get("id", "")) if ctx else False,
        local_user=ctx_user,
    )) for item in items))
    print(f"{'Skill':<{width}}  Level  Type")
    print("─" * (width + 22))
    for item in items:
        sid = item.get("id", "")
        level = item.get("level", "?")
        skill_type = item.get("type", "basic")
        named_contrib = ctx.named_contributor(sid) if ctx and ctx.is_named(sid) else None
        is_local = ctx.is_local(sid) if ctx else False

        display = format_skill_colored(
            sid, level,
            named_contributor=named_contrib,
            is_local=is_local,
            local_user=ctx_user,
        )
        plain_display = format_skill_plain(
            sid,
            named_contributor=named_contrib,
            is_local=is_local,
            local_user=ctx_user,
        )
        level_col = format_level_colored(level)
        type_col = format_type_colored(skill_type)
        suffix = " (pending)" if item.get("pending") else ""
        # Use plain width for padding since ANSI codes don't count
        pad = width - len(plain_display)
        print(f"{display}{' ' * max(0, pad)}  {level_col:<5}  {type_col}{suffix}")


def fetch_command(args):
    """Downloads the latest canonical registry JSON files to .gaia/registry/."""
    import urllib.request
    import urllib.error
    from pathlib import Path
    import sys
    
    registry_dir = Path(".gaia") / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    
    gaia_json_url = "https://raw.githubusercontent.com/mbtiongson1/gaia-skill-tree/main/registry/gaia.json"
    named_skills_url = "https://raw.githubusercontent.com/mbtiongson1/gaia-skill-tree/main/registry/named-skills.json"
    
    print(f"Fetching latest canonical registry from mbtiongson1/gaia-skill-tree...")
    try:
        urllib.request.urlretrieve(gaia_json_url, registry_dir / "gaia.json")
        urllib.request.urlretrieve(named_skills_url, registry_dir / "named-skills.json")
        print(f"✅ Successfully fetched registry to {registry_dir}/")
    except urllib.error.URLError as e:
        print(f"❌ Failed to fetch registry: {e}")
        sys.exit(1)

def pull_command(args):
    """Fetches the latest canonical registry and then runs a full scan."""
    fetch_command(args)
    scan_command(args)


def update_command(args):
    res = subprocess.run(
        ["git", "-C", args.registry, "pull", "--ff-only"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        stderr = res.stderr.strip()
        no_upstream = any(p in stderr for p in (
            "no tracking information", "no upstream", "There is no tracking",
            "does not track", "has no upstream",
        ))
        if no_upstream:
            print("Note: Could not git-pull registry (no upstream configured). Proceeding with package update...", file=sys.stderr)
        else:
            print(f"Warning: git pull failed. Proceeding with package update...\n  {stderr}", file=sys.stderr)
    registry_pyproject = Path(args.registry) / "pyproject.toml"
    
    # PEP 668 fix: use --break-system-packages if not in a venv
    pip_args = ["install"]
    if not (os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")):
        pip_args.append("--break-system-packages")

    if registry_pyproject.exists():
        # Editable source install — pipx doesn't support -e, so pip only
        subprocess.run(
            [sys.executable, "-m", "pip"] + pip_args + ["-e", args.registry],
            check=True,
        )
        return
    # Non-editable: try pip first, fall back to pipx
    pip_ok = subprocess.run(
        [sys.executable, "-m", "pip"] + pip_args + ["gaia-cli", "--upgrade"],
    ).returncode == 0
    if not pip_ok:
        pipx = subprocess.run(["pipx", "upgrade", "gaia-cli"]).returncode
        if pipx != 0:
            print("Update failed: pip and pipx both returned non-zero.", file=sys.stderr)
            sys.exit(1)


def version_command(args):
    pyproject = Path(args.registry) / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("version = "):
                print(line.split("=", 1)[1].strip().strip('"'))
                return
    try:
        # Performance optimization:
        # Deferring importlib.metadata import to avoid ~80ms overhead on every CLI invocation.
        # This import is only needed when running the version command.
        from importlib.metadata import PackageNotFoundError, version as package_version
        print(package_version("gaia-cli"))
    except PackageNotFoundError:
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8") if pyproject.exists() else ""
        for line in text.splitlines():
            if line.startswith("version = "):
                print(line.split("=", 1)[1].strip().strip('"'))
                return
        print("unknown")


def mcp_command(args):
    script = Path(args.registry) / "packages" / "mcp" / "dist" / "bin" / "gaia-mcp.js"
    if not script.exists():
        print(f"MCP server build not found: {script}", file=sys.stderr)
        print("Run `npm run build` in packages/mcp first.", file=sys.stderr)
        sys.exit(1)
    
    env = os.environ.copy()
    env["GAIA_REGISTRY_PATH"] = str(args.registry)
    
    config = load_config()
    if config and config.get("gaiaUser"):
        env["GAIA_USER"] = config["gaiaUser"]
        
    raise SystemExit(subprocess.call(["node", str(script)], env=env))


def docs_command(args):
    script = Path(args.registry) / "scripts" / "build_docs.py"
    cmd = [sys.executable, str(script)]
    if getattr(args, "check", False):
        cmd.append("--check")
    raise SystemExit(subprocess.call(cmd))


def release_command(args):
    from gaia_cli.versioning import bump_versions, read_versions, sync_versions

    if args.sync:
        # If --sync is provided, we first align everything to the highest version
        # found among the manifest files to resolve any drift.
        versions = read_versions(args.registry)
        target = max(versions.values())
        sync_versions(args.registry, target)
        print(f"Force-synced manifest files to version {target}.")

    new_version = bump_versions(args.registry, args.release_type)
    print(f"Gaia version bumped to {new_version}.")

    root = args.registry or "."

    # Commit the version bump, create an annotated tag, and push both so that
    # the GitHub Actions release workflow (triggered by 'push tags: v*') fires.
    version_files = [
        "pyproject.toml",
        "packages/cli-npm/package.json",
        "packages/mcp/package.json",
        "registry/gaia.json",
    ]

    def _run_git(*cmd, cwd=root):
        result = subprocess.run(
            ["git", *cmd],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(
                f"git {' '.join(cmd)} failed:\n{result.stderr.strip()}"
            )
        return result.stdout.strip()

    print("Creating release commit…")
    _run_git("add", "--", *version_files)
    _run_git(
        "commit",
        "-m",
        f"chore: release v{new_version} [skip-gen]",
    )

    tag = f"v{new_version}"
    print(f"Creating tag {tag}…")
    _run_git("tag", "-a", tag, "-m", f"Release {tag}")

    if not args.no_push:
        print("Pushing commit and tag to origin…")
        _run_git("push", "origin", "HEAD")
        _run_git("push", "origin", tag)
        print(f"✓ Released {tag} — GitHub Actions will create the GitHub Release.")

def get_parser():
    parser = argparse.ArgumentParser(
        prog="gaia",
        description="Gaia Registry CLI",
        epilog=COMMAND_USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--registry',
        default=None,
        help="Path to a local Gaia registry checkout. Defaults to auto-resolved local or global registry.",
    )
    parser.add_argument(
        '--global', '-g',
        dest='global_flag',
        action='store_true',
        help="Use global GAIA_HOME registry, ignoring any local .gaia/ config.",
    )
    parser.add_argument(
        '--version', '-v',
        action='store_true',
        help="Print the Gaia CLI version and exit.",
    )
    parser.add_argument(
        '--tui',
        action='store_true',
        help="Launch the TUI (Terminal User Interface).",
    )
    parser.add_argument(
        '--canon',
        action='store_true',
        help="Show canonical registry data instead of local-first view.",
    )
    subparsers = parser.add_subparsers(dest='command', metavar="{" + ",".join(PUBLIC_COMMANDS) + "}")
    subparsers.add_parser('help', help="Show command help")
    init_parser = subparsers.add_parser('init', help="Create or update local Gaia config")
    init_parser.add_argument('--user', help='Gaia username to write into .gaia/config.toml')
    init_parser.add_argument('--registry-ref', help='Gaia registry URL to write into .gaia/config.toml')
    init_parser.add_argument('--scan', action='append', help='Path to scan; repeat for multiple paths')
    init_parser.add_argument('--yes', action='store_true', help='Use non-interactive defaults')
    init_parser.add_argument('--force', action='store_true', help='Overwrite existing .gaia/config.toml')
    init_parser.add_argument(
        '--auto-prompt-combinations',
        action='store_true',
        help='Enable automatic prompts for detected skill combinations',
    )
    scan_parser = subparsers.add_parser('scan', help="Scan configured paths and installed skills for skill evidence")
    scan_parser.add_argument('--quiet', action='store_true', help="Suppress scan output; only show notifications")
    scan_parser.add_argument('--auto-promote', action='store_true', help="Promote every scan-recommended candidate after scanning")
    scan_parser.add_argument('--json', action='store_true', help="Output scan results as JSON")
    scan_parser.add_argument('--all', action='store_true', help="Scan globally installed skills in addition to the local repository")
    subparsers.add_parser('fetch', help="Download the latest canonical registry files to .gaia/registry")
    subparsers.add_parser('pull', help="Fetch registry data and run a full scan")
    subparsers.add_parser('update', help="Update all installed remote skills")
    
    install_parser = subparsers.add_parser('install', help="Install a named skill")
    install_parser.add_argument('skill_id', nargs='?', help="Skill ID, catalogRef, or unique bare slug to install")
    install_parser.add_argument('--list', action='store_true', help="List and interactively select skills to install")
    install_parser.add_argument('--ultimate', action='store_true', help="Batch-install all component skills (alias for --suite)")
    install_parser.add_argument('--suite', action='store_true', help="Batch-install all component skills for a suite")
    install_parser.add_argument('--install-location', dest='install_location', choices=['local', 'global'], default='local', help='Where to install: local (.agents/.claude, default) or global (~/.gaia/skills)')
    uninstall_parser = subparsers.add_parser('uninstall', help="Uninstall a named skill")
    uninstall_parser.add_argument('skill_id', help="Skill ID to uninstall")

    tree_parser = subparsers.add_parser('tree', help="Show your Gaia skill tree")
    tree_parser.add_argument('--named', action='store_true', help="Show only skills that have a named implementation")
    tree_parser.add_argument('--title', action='store_true', help="Show display name instead of slash command / contributor ID")
    tree_parser.add_argument('--canon', action='store_true', help="Show canonical registry data instead of custom skills only.")
    tree_parser.add_argument('--check', action='store_true', help="Self-test: print all tier glyphs and rank chips in resolved token colors")
    tree_parser.add_argument('--custom', action='store_true', help="Show only custom skills (default)")
    push_parser = subparsers.add_parser('push', help="Prepare detected skills for review and file a GitHub issue")
    push_parser.add_argument('--dry-run', action='store_true', help="Print the skill batch without writing it")
    push_parser.add_argument('--no-issue', action='store_true', dest='no_issue', help="Write intake record without creating a GitHub issue")
    push_parser.add_argument('--no-pr', action='store_true', dest='no_issue', help=argparse.SUPPRESS)  # backward compat alias
    push_parser.add_argument('--yes', '-y', action='store_true', dest='yes', help="Skip confirmation prompts")
    propose_parser = subparsers.add_parser('propose', help="Propose a single canonical skill as a named PR")
    propose_parser.add_argument('skillId', help="Canonical skill ID (accepts /skill-id form)")
    propose_parser.add_argument('--target', help="Named skill target in contributor/skill-name format")
    propose_parser.add_argument('--ultimate', action='store_true', help="Require that the selected skill is ultimate")
    propose_parser.add_argument('--yes', action='store_true', help="Use defaults without interactive prompts")
    propose_parser.add_argument('--no-pr', action='store_true', help="Write intake proposal without opening a PR")
    subparsers.add_parser('version', help="Print the Gaia CLI version")
    subparsers.add_parser('whoami', help="Show your Gaia identity and Verifier/operator status")
    subparsers.add_parser(
        'mcp',
        help="Run the bundled Gaia MCP server",
        description=(
            "Start the Gaia MCP (Model Context Protocol) server, which exposes the skill registry "
            "to AI tools and IDE integrations via stdio. "
            "Requires building the server first: run `npm run build` inside packages/mcp/."
        ),
    )
    release_parser = subparsers.add_parser('release', help="Bump version, commit, tag, and push to trigger GitHub Release")
    release_parser.add_argument('release_type', choices=('patch', 'minor', 'major'))
    release_parser.add_argument('--sync', action='store_true', help="Force sync versions if they disagree before bump")
    release_parser.add_argument('--no-push', action='store_true', help="Skip git push (commit and tag locally only)")
    graph_parser = subparsers.add_parser('graph', help="Generate and open the Gaia skill graph")
    graph_parser.add_argument('--format', choices=('html', 'svg', 'json'), default='html', help="Graph artifact format (default: html)")
    graph_parser.add_argument('-o', '--output', help="Output path (default: registry/render/gaia.html)")
    graph_parser.add_argument('--open', dest='open', action='store_true', default=True, help="Open the generated graph (default)")
    graph_parser.add_argument('--no-open', dest='open', action='store_false', help="Do not open the generated graph")
    graph_parser.add_argument('--custom', action='store_true', help="Only include custom skills in the graph (default)")
    graph_parser.add_argument('--canon', action='store_true', help="Show canonical registry graph instead of custom skills only")
    stats_parser = subparsers.add_parser('stats', help="Show registry health at a glance")
    stats_parser.add_argument('--canon', action='store_true', help="Show canonical registry data instead of local-first view.")
    appraise_parser = subparsers.add_parser('appraise', help="Inspect a skill card with status and actions")
    appraise_parser.add_argument('skillId', nargs='?', default=None, help="Skill ID to appraise (default: most recent)")
    promote_parser = subparsers.add_parser('promote', help="Promote a skill eligible for level-up")
    promote_parser.add_argument('skillId', nargs='?', default=None, help="Skill ID to promote")
    promote_parser.add_argument('--all', action='store_true', help="Promote every candidate from the last scan")
    promote_parser.add_argument('--unique', action='store_true', help="Promote a basic skill to unique type (4★+ graph-isolated with named impl)")
    promote_parser.add_argument('--name', help="Optional display name for the promoted skill")
    fuse_parser = subparsers.add_parser('fuse', help="Confirm a skill combination or promotion candidate")
    fuse_parser.add_argument('skillId', nargs='?', default=None, help="Skill ID to fuse or promote")
    fuse_parser.add_argument('--name', help="Optional display name for the skill")
    docs_parser = subparsers.add_parser('docs', help="Documentation maintenance commands")
    docs_sub = docs_parser.add_subparsers(dest='docs_command')
    docs_build = docs_sub.add_parser('build', help="Regenerate generated documentation regions")
    docs_build.add_argument('--check', action='store_true', help="Fail if docs are stale without writing")
    lookup_parser = subparsers.add_parser('lookup', help="Look up a canonical skill and its named implementations")
    lookup_parser.add_argument('skillId', help='Skill ID to inspect')

    path_parser = subparsers.add_parser(
        'path',
        help="Show prerequisite unlock-path tree toward a target skill",
    )
    path_parser.add_argument('skillId', help="Canonical skill ID (or /slash-form) to build the path toward")
    path_parser.add_argument(
        '--owned-only',
        action='store_true',
        dest='owned_only',
        help="Prune already-owned branches; show only skills still needed",
    )
    path_parser.add_argument(
        '--json',
        action='store_true',
        help="Emit machine-readable JSON instead of the tree display",
    )

    dev_parser = subparsers.add_parser('dev', help="Registry development and maintenance (requires writable registry)")
    dev_sub = dev_parser.add_subparsers(dest='dev_command')

    dev_list = dev_sub.add_parser('list', help="List skills in the registry with filtering")
    dev_list.add_argument('--generic', action='store_true', help="Include generic (canonical) skills")
    dev_list.add_argument('--named', action='store_true', help="Include named skills")
    dev_list.add_argument('--description', action='store_true', help="Include skill descriptions")
    dev_list.add_argument('--level', action='store_true', help="Include skill level")
    dev_list.add_argument('--evidence', action='store_true', help="Include evidence count (generic only)")
    dev_list.add_argument('--contributor', action='store_true', help="Include contributor name (named only)")
    dev_list.add_argument('--json', action='store_true', help="Output in JSON format")
    dev_list.add_argument('--extra', action='append', help="Include extra schema fields in output")

    dev_merge = dev_sub.add_parser('merge', help="Merge one or more skills into a target skill")
    dev_merge.add_argument('target', help="Target skill ID to merge into")
    dev_merge.add_argument('sources', nargs='+', help="Source skill IDs to merge from")
    dev_merge.add_argument('--named', action='store_true', help="Also merge named implementation references")
    dev_merge.add_argument('--yes', '-y', action='store_true', help="Skip confirmation prompt")

    dev_split = dev_sub.add_parser('split', help="Split a skill into multiple new skills")
    dev_split.add_argument('source', help="Source skill ID to split")
    dev_split.add_argument('targets', nargs='+', help="Target skill IDs to create")
    dev_split.add_argument('--yes', '-y', action='store_true', help="Skip confirmation prompt")

    dev_rename = dev_sub.add_parser('rename', help="Rename a skill and update all references")
    dev_rename.add_argument('old_id', help="Original skill ID")
    dev_rename.add_argument('new_id', help="New skill ID")

    dev_verify = dev_sub.add_parser('verify', help="Verify or dispute a skill's evidence")
    dev_verify.add_argument('skill_id', help="Skill ID to verify")
    dev_verify.add_argument('--index', type=int, required=True, help="Index of the evidence entry to verify")
    dev_verify.add_argument('--dispute', action='store_true', help="Mark evidence as disputed instead of verified")
    dev_verify.add_argument('--notes', help="Optional notes about the verification/dispute")
    dev_verify.add_argument('--source', help="URL to the verification discussion or PR")
    dev_verify.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after verification")

    dev_calibrate = dev_sub.add_parser('calibrate', help="Update the level of a skill")
    dev_calibrate.add_argument('skill_id', help="Skill ID to calibrate")
    dev_calibrate.add_argument('level', help="New level (e.g. 3★)")
    dev_calibrate.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after calibrating")

    dev_add = dev_sub.add_parser('add', help="Add a new skill to the registry")
    dev_add.add_argument('name', help="Human-readable name of the skill")
    dev_add.add_argument('--id', help="Explicit ID for the skill (defaults to slugified name)")
    dev_add.add_argument('--type', choices=('basic', 'extra', 'ultimate', 'unique'), default='basic', help="Skill type (default: basic)")
    dev_add.add_argument('--description', help="Skill description")
    dev_add.add_argument('--named', action='store_true', help="Add as a named skill instead of generic")
    dev_add.add_argument('--contributor', help="Contributor name for named skill (default: gaiabot)")
    dev_add.add_argument('--generic-ref', help="Generic skill reference for named skill")
    dev_add.add_argument('--status', help="Initial status (default: named for named skills, provisional for generic)")
    dev_add.add_argument('--title', help="Display title (lore title) for named skills")
    dev_add.add_argument('--level', help="Initial level (default: 2★ for named, 1★ for generic)")
    dev_add.add_argument('--extra-fields', help="JSON string of additional schema fields")
    dev_add.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after adding")

    dev_rm = dev_sub.add_parser('rm', help="Remove a skill from the registry")
    dev_rm.add_argument('skill_id', help="Skill ID to remove")
    dev_rm.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after removing")
    dev_rm.add_argument('--yes', '-y', action='store_true', help="Skip confirmation prompt")

    dev_link = dev_sub.add_parser('link', help="Link skills by adding prerequisites")
    dev_link.add_argument('target', help="Target skill ID that receives the prerequisites")
    dev_link.add_argument('prereqs', help="Comma-separated list of prerequisite skill IDs")
    dev_link.add_argument('--reset', action='store_true', help="Overwrite existing prerequisites instead of appending")
    dev_link.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after linking")

    dev_reclassify = dev_sub.add_parser('reclassify', help="Change the type of a generic skill")
    dev_reclassify.add_argument('skill_id', help="Generic skill ID to reclassify")
    dev_reclassify.add_argument('new_type', choices=('basic', 'extra', 'ultimate', 'unique'), help="New skill type")
    dev_reclassify.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after reclassifying")
    dev_update_named = dev_sub.add_parser('update-named', help="Update frontmatter properties of a named skill")
    dev_update_named.add_argument('skill_id', help="Named skill ID (e.g. author/skill)")
    dev_update_named.add_argument('--status', help="New status (e.g. awakened, named)")
    dev_update_named.add_argument('--generic-ref', help="New generic skill reference")
    dev_update_named.add_argument('--suite-components', help="Comma-separated list of suite components")
    dev_update_named.add_argument('--suite-ref', help="Suite capstone ID this skill belongs to (e.g. garrytan/gstack). Sets suiteRef in frontmatter.")
    dev_update_named.add_argument('--installation-file', metavar='PATH', help="Path to a markdown file whose content replaces the '## Installation' section in the capstone skill.")
    dev_update_named.add_argument('--origin', choices=['true', 'false'], help="Set the origin flag to true or false")
    dev_update_named.add_argument('--github-link', help="New GitHub URL link for the named skill (must be a blob link for 3★+)")
    dev_update_named.add_argument('--installable', choices=['true', 'false'], help="Set the installable flag to true or false")
    dev_update_named.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after updating")



    dev_timeline = dev_sub.add_parser('timeline', help="Append a standalone event to a skill's or user tree's timeline")
    dev_timeline.add_argument('skill_id', help="Skill ID to append the event to (generic, named, or user-tree)")
    dev_timeline.add_argument('--action', required=True, choices=('propose', 'rank_up', 'demote', 'verified', 'disputed', 'type_change', 'suite_ref_set', 'note'), help="The type of event action")
    dev_timeline.add_argument('--notes', required=True, help="Description of the event")
    dev_timeline.add_argument('--user', help="Write to skill-trees/<user>/skill-tree.json instead of the registry node")
    dev_timeline.add_argument('--timestamp', help="ISO 8601 timestamp for the event (e.g. 2026-03-01T00:00:00Z); defaults to now. Use for historical backfills.")
    dev_timeline.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after appending event")

    dev_evidence = dev_sub.add_parser('evidence', help="Add evidence to a skill")
    dev_evidence.add_argument('skill_id', help="Skill ID to add evidence to")
    dev_evidence.add_argument('source', help="URL to the evidence source")
    dev_evidence.add_argument('--class', dest='evidence_class', choices=('A', 'B', 'C'), default='C', help="Evidence class (default: C)")
    dev_evidence.add_argument('--evaluator', help="GitHub username of the evaluator")
    dev_evidence.add_argument('--date', help="Date of evaluation (ISO 8601)")
    dev_evidence.add_argument('--notes', help="Optional notes about the evaluation")
    dev_evidence.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after adding evidence")

    dev_rm_evidence = dev_sub.add_parser('rm-evidence', help="Remove an evidence entry (by --index or --source) from a skill")
    dev_rm_evidence.add_argument('skill_id', help="Skill ID to remove evidence from (bare id = generic; contributor/skill = named)")
    dev_rm_evidence.add_argument('--index', type=int, help="Index of the evidence entry to remove")
    dev_rm_evidence.add_argument('--source', help="Remove all evidence entries whose source URL matches this exactly")
    dev_rm_evidence.add_argument('--no-build', action='store_true', help="Skip rebuilding docs and graph assets after removing evidence")
    dev_rm_evidence.add_argument('--yes', '-y', action='store_true', help="Skip confirmation prompt")

    dev_build = dev_sub.add_parser('build', help="Regenerate registry and documentation site")

    dev_audit = dev_sub.add_parser('audit', help="Run registry maintenance linter")
    dev_audit.add_argument('--level', type=int, help="Filter audit by level threshold")

    dev_diff = dev_sub.add_parser(
        'diff',
        help="Show substantive registry additions in a branch vs main (strips generated noise)",
    )
    dev_diff.add_argument(
        'ref', nargs='?',
        help="Branch or ref to compare (default: current branch). "
             "Short names are auto-prefixed with origin/.",
    )
    dev_diff.add_argument(
        '--base', default='origin/main',
        help="Base ref to compare against (default: origin/main)",
    )

    validate_parser = subparsers.add_parser('validate', help="Validate the Gaia registry")
    validate_parser.add_argument('--intake', action='store_true', help="Validate intake batches instead of canonical graph")
    validate_parser.add_argument('--meta-sync', action='store_true', help="Verify meta.json is in sync with gaia.json")

    test_parser = subparsers.add_parser('test', help="Run self-verification tests")
    test_parser.add_argument('suite', choices=('meta', 'all'), help="Test suite to run")

    skills_parser = subparsers.add_parser(
        'skills',
        help="Browse and manage named skills",
        epilog=SKILLS_USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    skills_sub = skills_parser.add_subparsers(dest='skills_command')
    skills_list = skills_sub.add_parser('list', help="List available named skills")
    skills_list.add_argument('--exclude-pending', action='store_true', help="Hide pending skill proposals")
    skills_search = skills_sub.add_parser('search', help="Search named skills")
    skills_search.add_argument('query', help="Search query")
    skills_search.add_argument('--exclude-pending', action='store_true', help="Hide pending skill proposals")
    skills_info = skills_sub.add_parser('info', help="Show details for a named skill")
    skills_info.add_argument('skill_id', help="Skill ID to inspect")
    skills_info.add_argument('--exclude-pending', action='store_true', help="Hide pending skill proposals")
    skills_install = skills_sub.add_parser('install', help="Install a named skill")
    skills_install.add_argument('skill_id', metavar='skill', help="Skill ID, catalogRef, or unique bare slug to install")
    skills_install.add_argument('--suite', action='store_true', help="Install as a suite (recursive)")
    skills_install.add_argument('--install-location', dest='install_location', choices=['local', 'global'], default='local', help='Where to install: local (.agents/.claude, default) or global (~/.gaia/skills)')
    skills_update = skills_sub.add_parser('update', help="Update all installed skills from source")
    skills_uninstall = skills_sub.add_parser('uninstall', help="Uninstall a named skill")
    skills_uninstall.add_argument('skill_id', help="Skill ID to uninstall")
    hook_parser = subparsers.add_parser('_hook', help=argparse.SUPPRESS)
    subparsers._choices_actions = [
        action for action in subparsers._choices_actions if action.dest != '_hook'
    ]
    hook_parser.add_argument('--event', default='file_edit', help=argparse.SUPPRESS)
    return parser, skills_parser

def validate_command(args):
    """Run registry validation."""
    repo_root = Path(args.registry)
    if args.intake:
        script = repo_root / "scripts" / "validate_intake.py"
        raise SystemExit(subprocess.call([sys.executable, str(script)]))

    script = repo_root / "scripts" / "validate.py"
    cmd = [sys.executable, str(script)]
    if args.meta_sync:
        cmd.append("--check-meta-sync")
    rc = subprocess.call(cmd)

    # Redaction gate — prove every pre-named/demoted (≤1★) handle is withheld
    # across the generated public assets, and no named (2★+) skill is
    # over-redacted. This is the safety net that makes the universal redaction
    # gate auditable rather than hoped-for.
    redaction_script = repo_root / "scripts" / "validate_redaction.py"
    if redaction_script.exists():
        rc = subprocess.call([sys.executable, str(redaction_script)]) or rc

    # Transparency Gate — every rank change must leave an auditable timeline
    # event; prove no silent demotion/promotion that the Hero's Journey omits.
    timeline_script = repo_root / "scripts" / "validate_timelines.py"
    if timeline_script.exists():
        rc = subprocess.call([sys.executable, str(timeline_script)]) or rc

    raise SystemExit(rc)

def test_command(args):
    """Run self-verification tests."""
    repo_root = Path(__file__).parent.parent.parent

    # Always use the same Python that is running gaia so the test process
    # inherits the correct virtual-env / site-packages (including gaia_cli
    # itself, pyyaml, textual, etc.).  Relying on a bare "pytest" from PATH
    # can pick up an isolated uv-tool pytest that lacks these packages.
    cmd = [sys.executable, "-m", "pytest"]
    if args.suite == "meta":
        cmd.extend([str(repo_root / "tests" / "test_meta_ops.py"),
                    str(repo_root / "tests" / "test_authz.py")])
    elif args.suite == "all":
        cmd.append(str(repo_root / "tests"))

    print(f"Running tests: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(repo_root))
    if result.returncode != 0:
        sys.exit(result.returncode)

def main():
    # Suppress BrokenPipeError traceback when output is piped to head/less/etc.
    # Placed here (not __main__.py) so it covers all entry paths: console script,
    # `python -m gaia_cli`, and programmatic callers.
    if hasattr(signal, 'SIGPIPE'):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    # Ensure UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError for box-drawing)
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser, skills_parser = get_parser()
    args = parser.parse_args()

    # Launch TUI if explicitly requested OR if no args + interactive terminal
    wants_tui = args.tui or (len(sys.argv) == 1 and sys.stdin.isatty() and sys.stdout.isatty())

    if wants_tui:
        try:
            from gaia_cli.tui import GaiaApp
            GaiaApp().run()
            return
        except ImportError:
            if args.tui:
                # Explicit request failed -> error
                print("TUI requires the 'textual' package. Install with: pip install 'gaia-cli[tui]'", file=sys.stderr)
                sys.exit(1)
            # Implicit request failed -> fall through to argparse

    args.registry = resolve_registry_path(args.registry, global_flag=args.global_flag)
    require_explicit_writable_registry(parser, args)
    if args.version:
        version_command(args)
        return
    if args.command == 'init':
        init_command(args)
    elif args.command == 'help':
        parser.print_help()
    elif args.command == 'scan':
        scan_command(args)
    elif args.command == 'fetch':
        fetch_command(args)
    elif args.command == 'pull':
        pull_command(args)
    elif args.command == 'update':
        update_command(args)
    elif args.command == 'install':
        install_command(args)
    elif args.command == 'uninstall':
        uninstall_command(args)
    elif args.command == 'tree':
        tree_command(args)
    elif args.command == 'push':
        push_command(args)
    elif args.command == 'propose':
        propose_command(args)
    elif args.command == 'version':
        version_command(args)
    elif args.command == 'whoami':
        whoami_command(args)
    elif args.command == 'mcp':
        mcp_command(args)
    elif args.command == 'release':
        release_command(args)
    elif args.command == 'graph':
        graph_command(args)
    elif args.command == 'stats':
        stats_command(args)
    elif args.command == 'appraise':
        appraise_command(args)
    elif args.command == 'promote':
        promote_command(args)
    elif args.command == 'fuse':
        fuse_command(args)
    elif args.command == 'docs' and getattr(args, 'docs_command', None) == 'build':
        docs_command(args)
    elif args.command == 'lookup':
        lookup_command(args)
    elif args.command == 'dev':
        dev_cmd = getattr(args, 'dev_command', None)
        if dev_cmd in MUTATING_DEV_COMMANDS:
            from gaia_cli.authz import require_operator
            require_operator(f"dev {dev_cmd}", args.registry)
        if dev_cmd == 'list':
            meta_list_command(args)
        elif dev_cmd == 'merge':
            meta_merge_command(args)
        elif dev_cmd == 'split':
            meta_split_command(args)
        elif dev_cmd == 'rename':
            meta_rename_command(args)
        elif dev_cmd == 'verify':
            meta_verify_command(args)
        elif dev_cmd == 'calibrate':
            meta_calibrate_command(args)
        elif dev_cmd == 'add':
            meta_add_command(args)
        elif dev_cmd == 'rm':
            meta_remove_command(args)
        elif dev_cmd == 'link':
            meta_link_command(args)
        elif dev_cmd == 'reclassify':
            meta_reclassify_command(args)
        elif dev_cmd == 'update-named':
            meta_update_named_command(args)
        elif dev_cmd == 'timeline':
            meta_timeline_command(args)
        elif dev_cmd == 'evidence':
            meta_evidence_command(args)
        elif dev_cmd == 'rm-evidence':
            meta_rm_evidence_command(args)
        elif dev_cmd == 'build':
            meta_build_command(args)
        elif dev_cmd == 'audit':
            meta_audit_command(args)
        elif dev_cmd == 'diff':
            meta_diff_command(args)
        else:
            _, subparsers = get_parser()
            subparsers.choices['dev'].print_help()
    elif args.command == 'path':
        path_command(args)
    elif args.command == 'validate':
        validate_command(args)
    elif args.command == 'test':
        test_command(args)
    elif args.command == 'skills':
        if not getattr(args, 'skills_command', None):
            skills_parser.print_help()
            return
        skills_command(args)
    elif args.command == '_hook':
        hook_command(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
