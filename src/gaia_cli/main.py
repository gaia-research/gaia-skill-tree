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

from gaia_cli.scanner import (
    load_config,
    scan_skill_mds,
    match_skill_to_canonical,
)
from gaia_cli.combinator import get_combinations
from gaia_cli.treeManager import load_tree, save_tree, show_status, show_tree
from gaia_cli.prWriter import open_pr, open_intake_issue
from gaia_cli.push import (
    build_skill_batch,
    write_skill_batch,
    build_proposed_skill,
    detect_source_repo,
    NonPublicRepoError,
)
from gaia_cli.embeddings import generate_embeddings
from gaia_cli.semantic_search import search as semantic_search
from gaia_cli.name import promote_to_named, update_batch_lifecycle
from gaia_cli.install import (
    install_skill,
    install_suite,
    update_skills,
    uninstall_skill,
    interactive_install,
    list_available,
)
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
    meta_verify_tier_command,
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
)
from gaia_cli.cardRenderer import (
    render_appraise_card,
    render_unlock_card,
    render_path_summary,
)
from gaia_cli.promotion import (
    load_promotion_candidates,
    promote_from_candidates,
    promotable_candidates,
    promotion_state,
    LEVEL_NAMES,
)
from gaia_cli.hook import hook_entry
from gaia_cli.formatting import (
    format_skill_plain,
    format_skill_colored,
    format_type_colored,
    format_level_colored,
    TIER_COLORS,
    RANK_COLORS,
    COLOR_CONTRIBUTOR,
    COLOR_LOCAL_USER,
    COLOR_GREY,
    COLOR_FUSION,
    HARNESS_COLORS,
    COLOR_REDACTED,
    REDACTED_BLOCK,
    get_harness_color,
    _rainbow_text,
    _fg,
    _bg,
    _reset,
    _bold,
    _use_color,
)
from gaia_cli.localContext import LocalContext
from gaia_cli.redaction import level_num
from gaia_cli.cardRenderer import render_fusion_diagram
from gaia_cli.interactive import (
    select_skill,
    select_fusion_candidate,
    select_promotion_candidate,
    select_multiple_skills,
    select_fusion_to_edit,
    _has_interactive,
    select_push_batch,
    fuse_style,
    FuseCancelled,
)

DEFAULT_REGISTRY_REF = "https://github.com/mbtiongson1/gaia-skill-tree"

# Brand color roles (using tokens from formatting)
COLOR_APEX_GOLD = RANK_COLORS["6★"]
COLOR_FUSE_PURPLE = COLOR_FUSION

# Star rank color tokens for convenience
C1 = RANK_COLORS["1★"]
C2 = RANK_COLORS["2★"]
C3 = RANK_COLORS["3★"]
C4 = RANK_COLORS["4★"]
C5 = RANK_COLORS["5★"]
C6 = RANK_COLORS["6★"]

COMMAND_USAGE = f"""\
Getting started:
  {_fg(*C1)}gaia init{_reset()} [--user <name>] [--scan <path>] [--yes] [-y]
  {_fg(*C2)}gaia scan{_reset()} [--quiet]
  {_fg(*COLOR_LOCAL_USER)}gaia push{_reset()} [--dry-run] [--no-issue]
  {_rainbow_text("gaia")}                        Open command selector
  {_rainbow_text("gaia skills")}                 Launch skills explorer (TUI)

Daily commands:
  {_fg(*C5)}gaia tree{_reset()} [--named] [--title]
  {_fg(*C5)}gaia promote{_reset()} [<skillId>] [--all] [--name <name>]
  {_fg(*C4)}gaia appraise{_reset()} [<skillId>]
  {_fg(*C4)}gaia stats{_reset()}
  {_fg(*C3)}gaia pull{_reset()}
  {_fg(*COLOR_FUSE_PURPLE)}gaia fuse{_reset()} <skillId> [--name <name>]
  {_fg(*C5)}gaia path{_reset()} <skillId> [--owned-only] [--json]
  {_fg(*C2)}gaia lookup{_reset()} <skillId>
  {_fg(*C1)}gaia graph{_reset()} [--format html|svg|json] [-o <path>] [--no-open]
  {_fg(*COLOR_FUSE_PURPLE)}gaia propose{_reset()} [<skillId>] [--ultimate] [--target <name>] [--no-pr]

Skills:
  {_rainbow_text("gaia skills")} <list|search|info|install|uninstall>
  {_rainbow_text("gaia skills list")} [--exclude-pending]
  {_rainbow_text("gaia skills search")} <query> [--exclude-pending]
  {_rainbow_text("gaia skills info")} <skill_id> [--exclude-pending]
  {_rainbow_text("gaia skills install")} <skill> [--global | --local]
  {_rainbow_text("gaia skills uninstall")} <skill_id>

Share:
  {_fg(*COLOR_LOCAL_USER)}gaia share{_reset()} [--user <name>] [-o <path>] [--stdout]
  {_fg(*C2)}gaia install{_reset()} <bundle.json|url>   Preview & install a shared tree (guided)

Utilities:
  {_fg(*C2)}gaia whoami{_reset()}
  {_fg(*COLOR_LOCAL_USER)}gaia login{_reset()}                    Sign in with GitHub (device flow)
  {_fg(*COLOR_GREY)}gaia logout{_reset()}                   Sign out of GitHub (clears the local token)
  {_fg(*C1)}gaia version{_reset()}
  {_fg(*C3)}gaia update{_reset()}
  {_fg(*HARNESS_COLORS["claude"])}gaia mcp{_reset()}
  {_fg(*COLOR_GREY)}gaia release{_reset()} <patch|minor|major>
  {_fg(*COLOR_GREY)}gaia docs build{_reset()} [--check]

Maintainer commands:  {_fg(*COLOR_GREY)}gaia dev --help{_reset()}
"""

SKILLS_USAGE = """\
Quick usage:
  gaia skills list [--exclude-pending]
  gaia skills search <query> [--exclude-pending]
  gaia skills info <skill_id> [--exclude-pending]
  gaia skills install <skill> [--global | --local]
  gaia skills uninstall <skill_id>
"""

DEV_USAGE = """\
Registry development commands (requires Verifier authorization):

  gaia dev list [--generic] [--named] [--description] [--json]
  gaia dev audit <skill_id>
  gaia dev diff [ref] [--base <ref>]
  gaia dev add <name> [--type <type>] [--description <desc>] [--named]
  gaia dev merge <target> <source1> [source2...] [--named] [--yes]
  gaia dev split <source> <target1> <target2>... [--yes]
  gaia dev rename <old_id> <new_id>
  gaia dev calibrate <skill_id> <level>
  gaia dev rm <skill_id> [--yes]
  gaia dev link <target> <prereqs> [--reset]
  gaia dev reclassify <skill_id> <new_type>
  gaia dev update-named <skill_id> [--status <status>] [--generic-ref <ref>]
  gaia dev evidence <skillId> <source> [--class A|B|C] [--evaluator <user>]
  gaia dev rm-evidence <skill_id> (--index N | --source URL) [--yes]
  gaia dev timeline <skill_id> --action <action> --notes <notes> [--user <username>]
  gaia dev build
  gaia dev verify <skill_id>

Read-only (no Verifier required):
  gaia dev list
  gaia dev audit <skill_id>
  gaia dev diff [ref]
  gaia validate [--intake] [--meta-sync]
  gaia test <suite>
"""

PUBLIC_COMMANDS = (
    "help",
    "init",
    "scan",
    "fetch",
    "pull",
    "update",
    "install",
    "uninstall",
    "share",
    "tree",
    "push",
    "propose",
    "version",
    "whoami",
    "login",
    "logout",
    "reset",
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
MUTATING_DEV_COMMANDS = frozenset(
    {
        "add",
        "merge",
        "split",
        "rename",
        "calibrate",
        "evidence",
        "rm-evidence",
        "link",
        "reclassify",
        "update-named",
        "timeline",
        "rm",
        "verify",
        "verify-tier",
        "build",
    }
)

# Known skill-convention files/dirs, in priority order
_SKILL_CANDIDATES = [
    "AGENTS.md",  # OpenAI Codex
    "SKILLS.md",  # generic
    "SKILL.md",  # single named-skill file
    "agents.md",
    "skills.md",
    ".agents/skills",  # Agent-agnostic skill directory
    ".claude/skills",  # Claude Code skill directory (legacy)
    ".antigravity/skills",  # Antigravity skill directory (legacy)
    ".gemini",  # Gemini skill directory (*.yml inside)
    ".github/copilot-instructions.md",  # GitHub Copilot
    "codex.yml",
    "gemini.yml",
    ".cursor/rules",  # Cursor rules directory
]


def _detect_github_username():
    """Detect GitHub username from git remote URL, email, or display name."""
    import subprocess
    import re

    # Most reliable: parse github.com/USERNAME from origin remote URL
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            m = re.search(r"github\.com[:/]([^/]+?)(?:\.git)?(?:/|$)", r.stdout.strip())
            if m:
                return m.group(1)
    except Exception:
        pass
    # Fallback: noreply GitHub email (e.g. 12345+username@users.noreply.github.com)
    try:
        r = subprocess.run(
            ["git", "config", "user.email"], capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            m = re.match(
                r"^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$", r.stdout.strip()
            )
            if m:
                return m.group(1)
    except Exception:
        pass
    # Fallback: git display name → slug
    try:
        r = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            slug = re.sub(
                r"[^a-zA-Z0-9-]", "", r.stdout.strip().lower().replace(" ", "-")
            )
            if slug:
                return slug
    except Exception:
        pass
    return None


def _detect_skill_files():
    """Return existing skill-related paths in the current working directory."""
    return [c for c in _SKILL_CANDIDATES if os.path.exists(c)]


def whoami_command(args):
    from gaia_cli.authz import (
        current_operator,
        authorization_status,
        OPERATOR_OVERRIDE_ENV,
    )

    registry_path = args.registry
    user = current_operator(registry_path)
    status = authorization_status(user, registry_path)
    authorized = status["authorized"]
    via = status["via"]
    reason = status["reason"]

    print(f"User:      {_fg(*COLOR_LOCAL_USER)}{user}{_reset()}")
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

    # GitHub sign-in status (PRD #155) — read-only, never blocks the above.
    from gaia_cli.auth import TokenStore

    print()
    creds = TokenStore().load()
    if creds and creds.login:
        suffix = "  (session token via env)" if creds.source == "env" else ""
        print(f"GitHub:    signed in as {_fg(*COLOR_LOCAL_USER)}{creds.login}{_reset()}{suffix}")
    elif creds:
        print("GitHub:    signed in (handle unknown — run `gaia login` to refresh)")
    else:
        print("GitHub:    not signed in  (run `gaia login`)")


def login_command(args):
    """Sign in to GitHub via the device flow and persist the token (PRD #155)."""
    from gaia_cli import auth

    config = load_config() or {}
    client_id = auth.resolve_client_id(config)

    if not auth.is_configured(client_id):
        print("GitHub sign-in isn't configured yet.", file=sys.stderr)
        print(
            f"  Set {auth.CLIENT_ID_ENV}=<oauth-app-client-id> (or add "
            "`oauthClientId = \"...\"` to .gaia/config.toml).",
            file=sys.stderr,
        )
        print(
            "  The client_id is public — register a Device-Flow OAuth app under "
            "GitHub → Settings → Developer settings.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        device = auth.request_device_code(client_id)
    except auth.AuthError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("To sign in, open this URL in your browser:")
    print(f"  {_fg(*C2)}{device.verification_uri}{_reset()}")
    print("and enter the code:")
    print(f"  {_fg(*COLOR_LOCAL_USER)}{device.user_code}{_reset()}")
    print()
    print("Waiting for authorization…")

    try:
        token = auth.poll_for_token(client_id, device)
        profile = auth.fetch_user(token)
    except auth.AuthDenied:
        print("Sign-in was denied.", file=sys.stderr)
        sys.exit(1)
    except auth.AuthTimeout:
        print("Sign-in timed out before you authorized. Try `gaia login` again.", file=sys.stderr)
        sys.exit(1)
    except auth.AuthError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    login = profile.get("login", "")
    creds = auth.Credentials(token=token, login=login, scope=auth.DEFAULT_SCOPE)

    backend = "skipped"
    if not getattr(args, "no_store", False):
        backend = auth.TokenStore().save(creds)

    print(f"\n✓ Signed in as {_fg(*COLOR_LOCAL_USER)}{login}{_reset()}")
    if backend == "keyring":
        print("  Token stored in your OS keychain.")
    elif backend == "file":
        print("  Token stored in a chmod-600 file under GAIA_HOME.")
    else:
        print("  Token not stored (--no-store); this session only.")

    repo = getattr(args, "repo", None)
    if repo:
        if "/" not in repo:
            print(f"  (skipping ownership check — expected owner/repo, got {repo!r})")
        else:
            owner, _, name = repo.partition("/")
            owned = auth.verify_repo_ownership(token, owner, name)
            mark = "✓ verified" if owned else "✗ not verified"
            print(f"  Ownership of {repo}: {mark}")


def logout_command(args):
    """Sign out of GitHub by clearing the locally stored token (PRD #155).

    The MVP stores no client secret, and GitHub's revocation endpoint
    (DELETE /applications/{client_id}/token) requires client_id:client_secret
    Basic auth — so a server-side revoke isn't possible here. We clear the
    local token and point the user at GitHub's UI to fully revoke if they want.
    """
    from gaia_cli import auth

    store = auth.TokenStore()
    creds = store.load()
    if not creds:
        print("Not signed in — nothing to do.")
        return

    if creds.source == "env":
        print("Signed in via an environment token — unset it to fully sign out.")

    store.delete()
    handle = f" ({creds.login})" if creds.login else ""
    print(f"✓ Signed out{handle}. Local token cleared.")

    config = load_config() or {}
    client_id = auth.resolve_client_id(config)
    if auth.is_configured(client_id):
        print("  To fully revoke this authorization, visit:")
        print(f"  https://github.com/settings/connections/applications/{client_id}")
    else:
        print("  To fully revoke: GitHub → Settings → Applications → Authorized OAuth Apps.")


def reset_command(args):
    """Clear your local state and skill tree for a fresh start."""
    config = load_config()
    if not config:
        print("Gaia not initialized.")
        return

    username = config.get("gaiaUser")
    if not username:
        print("No user identified in config.")
        return

    if not getattr(args, "yes", False):
        from gaia_cli.interactive import confirm

        if not confirm(
            f"Are you sure you want to reset the local state and skill tree for '{_fg(*COLOR_LOCAL_USER)}{username}{_reset()}'? This cannot be undone."
        ):
            print("Aborted.")
            return

    registry_path = args.registry
    tree_path = user_tree_path(registry_path, username)

    cleared = 0
    # 1. Delete the deprecated skill tree file
    if os.path.exists(tree_path):
        os.remove(tree_path)
        cleared += 1
        print(f"✓ Removed skill tree: {tree_path}")

    # 2. Clear local .gaia/ state (but keep the folder and its config.toml)
    import shutil

    gaia_dir = ".gaia"
    if os.path.exists(gaia_dir):
        for filename in os.listdir(gaia_dir):
            if filename == ".gitignore" or filename == "config.toml":
                continue
            file_path = os.path.join(gaia_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    cleared += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    cleared += 1
            except Exception as e:
                print(f"  failed to delete {file_path}: {e}")
        print(f"✓ Cleared local state in {gaia_dir}/")

    if cleared == 0:
        print("Everything already clean.")
    else:
        print("\n✓ Gaia reset complete. Run `gaia scan` to start afresh.")


def init_command(args):
    config_dir = ".gaia"
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "config.toml")
    if os.path.exists(config_path) and not getattr(args, "force", False):
        print(
            "Gaia is already initialized in this repository. Use --force to overwrite."
        )
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
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(f'username = "{username}"\n')
        f.write(f'gaiaRegistryRef = "{args.registry_ref or DEFAULT_REGISTRY_REF}"\n')
        f.write(f'localRegistryPath = "{local_registry_path}"\n')
        f.write(
            f"autoPromptCombinations = {'true' if args.auto_prompt_combinations else 'false'}\n"
        )
        f.write(
            "scanPaths = [" + ", ".join(json.dumps(path) for path in scan_paths) + "]\n"
        )

    # Color-coded display
    colored_user = f"{_fg(*COLOR_LOCAL_USER)}{username}{_reset()}"
    colored_paths = []
    for path in scan_paths:
        h_color = get_harness_color(path)
        colored_paths.append(f"{_fg(*h_color)}{path}{_reset()}")
    path_str = ", ".join(colored_paths)

    print(f"Initialized Gaia configuration at {config_path}")
    print(f"  user:       {colored_user}")
    print(f"  scanPaths:  {path_str}")
    print(
        "Run `gaia fetch` to download the latest canonical registry, then `gaia scan` to link your local skills."
    )

    fetch_command(args)

    try:
        source = detect_source_repo({"gaiaUser": username})
        if sys.stdin.isatty() and not getattr(args, "yes", False):
            try:
                if _use_color():
                    prompt = (
                        f"\n{_bold()}{_fg(*TIER_COLORS['extra'])}⚡ {_fg(255, 255, 255)}Detected repo: {_fg(*RANK_COLORS['2★'])}{source}{_reset()}\n"
                        f"{_bold()}{_fg(*TIER_COLORS['ultimate'])}? {_fg(255, 255, 255)}Initialize Gaia on this repository? "
                        f"{_fg(*RANK_COLORS['0★'])}[{_fg(*COLOR_LOCAL_USER)}Y{_fg(*RANK_COLORS['0★'])}/n]: {_reset()}"
                    )
                else:
                    prompt = f"Detected repo: {source}\nInitialize Gaia on this repository? [Y/n]: "
                ans = input(prompt).strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                import shutil

                shutil.rmtree(config_dir, ignore_errors=True)
                sys.exit(1)
            if ans == "n":
                import shutil

                shutil.rmtree(config_dir, ignore_errors=True)
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
        save_tree(
            username,
            {
                "userId": username,
                "updatedAt": date.today().isoformat(),
                "unlockedSkills": [],
                "pendingCombinations": [],
                "stats": {
                    "totalUnlocked": 0,
                    "deepestLineage": 0,
                },
            },
            registry_path=".",
        )
        print(f"  skill tree: {tree_path}")

    if os.path.exists("registry/gaia.json"):
        registry_abs = os.path.abspath(".")
        write_global_registry(registry_abs)


def scan_command(args):
    config = load_config()
    if not config:
        print("Gaia not initialized. Run `gaia init` first.")
        return
    quiet = getattr(args, "quiet", False)
    use_json = getattr(args, "json", False)

    if not quiet and not use_json:
        print("Scanning installed custom skills...")

    graph_path = registry_graph_path(args.registry)

    from gaia_cli.registry import bundled_registry_path

    if (
        not quiet
        and not use_json
        and str(args.registry) == str(bundled_registry_path())
    ):
        print("Note: using bundled registry (no local registry clone found).")

    username = config.get("gaiaUser")
    canon = getattr(args, "canon", False)
    global_search = getattr(args, "all", False)

    # Unified local context for display
    ctx = LocalContext.load(
        args.registry, username or "", include_scan=False, global_search=global_search
    )

    # 1. Run codebase scan to find actually used skill tokens
    from gaia_cli.pathEngine import regenerate_paths

    paths = regenerate_paths(args.registry)
    # paths.json IDs are stored WITHOUT leading slashes
    scanned_ids = set(paths.get("detectedIds", [])) | set(paths.get("novelIds", []))

    # 2. Scan filesystem for custom skill metadata (SKILL.md)
    all_installed_skills = scan_skill_mds(global_search=global_search)

    # 3. Filter: Only keep skills that are actually referenced in the code
    installed_skills = []
    for sk in all_installed_skills:
        # scan_skill_mds IDs always start with /
        cid_bare = sk["id"].lstrip("/")
        if cid_bare in scanned_ids:
            installed_skills.append(sk)

    resolved = []

    if installed_skills:
        with open(graph_path, "r", encoding="utf-8") as _gf:
            _gdata_for_match = json.load(_gf)
        canonical_list = _gdata_for_match.get("skills", [])
        smap_for_match = {s["id"]: s for s in canonical_list}

        # Load ORIGIN and NAMED skills
        from gaia_cli.registry import named_skills_index_path

        origin_skills = []
        named_skills = []
        idx_path = named_skills_index_path(args.registry)
        if os.path.exists(idx_path):
            with open(idx_path, "r", encoding="utf-8") as _nf:
                _ndata = json.load(_nf)
                for bucket, items in _ndata.get("buckets", {}).items():
                    for item in items:
                        if item.get("origin"):
                            origin_skills.append(item)
                        else:
                            named_skills.append(item)

        custom_state_skills = []

        for sk in installed_skills:
            cid = sk["id"]
            location = sk.get("location", "")

            # Logic to resolve matching to canonical
            match = match_skill_to_canonical(
                cid,
                sk["name"],
                sk["description"],
                canonical_list,
                origin_skills,
                named_skills,
                threshold=0.15,
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
                    canon_level = next(
                        (
                            o.get("level", "0★")
                            for o in origin_skills
                            if o["id"] == canon_id
                        ),
                        "0★",
                    )
                elif match_type == "named":
                    canon_level = next(
                        (
                            n.get("level", "0★")
                            for n in named_skills
                            if n["id"] == canon_id
                        ),
                        "0★",
                    )
                else:
                    canon_level = smap_for_match.get(canon_id, {}).get("level", "0★")
            elif cid not in smap_for_match:
                mapped_score = 0.0
            else:
                match_type = "exact_generic"
                mapped_score = 1.0

            # Resolve skill type from matched source
            if match_type == "origin":
                skill_type = next(
                    (o.get("type", "basic") for o in origin_skills if o["id"] == canon_id), "basic"
                )
            elif match_type == "named":
                skill_type = next(
                    (n.get("type", "basic") for n in named_skills if n["id"] == canon_id), "basic"
                )
            elif match_type == "exact_generic":
                skill_type = smap_for_match.get(canon_id, {}).get("type", "basic")
            else:
                skill_type = "basic"

            custom_state_skills.append(
                {
                    "id": cid,
                    "name": sk["name"],
                    "description": sk["description"],
                    "location": location,
                    "mapped_to": mapped_id,
                    "mapped_score": mapped_score,
                    "match_type": match_type,
                    "canon_level": canon_level,
                    "skill_type": skill_type,
                    "prerequisites": sk.get("prerequisites", []),
                }
            )

        # Build resolved strictly from mapped custom skills that exist in the registry
        for sk in custom_state_skills:
            if sk["mapped_score"] > 0.0:
                mapped_id = sk["mapped_to"]
                m_type = sk.get("match_type")
                generic_id = mapped_id
                if m_type == "origin":
                    ref = next(
                        (
                            o.get("genericSkillRef")
                            for o in origin_skills
                            if o["id"] == mapped_id
                        ),
                        None,
                    )
                    if ref:
                        generic_id = ref
                elif m_type == "named":
                    ref = next(
                        (
                            n.get("genericSkillRef")
                            for n in named_skills
                            if n["id"] == mapped_id
                        ),
                        None,
                    )
                    if ref:
                        generic_id = ref
                if generic_id and generic_id not in resolved:
                    resolved.append(generic_id)

        if use_json:
            out = {
                "scanned_installed": len(installed_skills),
                "matched": sorted(list(resolved)),
            }
            print(json.dumps(out, indent=2))
            return

        if not quiet:
            print("\nInstalled custom skills:")

            # Group custom skills by category first
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
            origin_group.sort(
                key=lambda s: (
                    -level_num(s.get("canon_level", "0★")),
                    -s.get("mapped_score", 0.0),
                    s["id"],
                )
            )
            named_group.sort(
                key=lambda s: (
                    -level_num(s.get("canon_level", "0★")),
                    -s.get("mapped_score", 0.0),
                    s["id"],
                )
            )
            generic_group.sort(key=lambda s: (-s.get("mapped_score", 0.0), s["id"]))
            other_group.sort(key=lambda s: s["id"])

            def print_group(group_id, skills):
                if group_id == "origin":
                    title = f"{_bg(*COLOR_APEX_GOLD)}{_fg(0, 0, 0)}{_bold()} Origin Skills {_reset()}"
                elif group_id == "named":
                    title = f"{_bg(*COLOR_CONTRIBUTOR)}{_fg(255, 255, 255)}{_bold()} Named Skills {_reset()}"
                elif group_id == "generic":
                    title = f"{_bg(*COLOR_GREY)}{_fg(0, 0, 0)}{_bold()} Starless (Generic) Skills {_reset()}"
                else:
                    title = f"{_bg(*COLOR_LOCAL_USER)}{_fg(0, 0, 0)}{_bold()} Custom — Only in this Repo {_reset()} ({_fg(*COLOR_LOCAL_USER)}{username}{_reset()})"

                print(f"\n{title}:")

                if not skills:
                    print(f"  {_fg(*RANK_COLORS['0★'])}None{_reset()}")
                    return

                # Group skills within this category by directory
                by_dir = {}
                for sk in skills:
                    loc = sk["location"]
                    parent = os.path.dirname(loc) or "."
                    if parent not in by_dir:
                        by_dir[parent] = []
                    by_dir[parent].append(sk)

                for directory in sorted(by_dir.keys()):
                    h_color = get_harness_color(directory)
                    print(f"{_fg(*h_color)}{directory}/{_reset()}")
                    # Sort skills within the directory by id
                    skills_in_dir = sorted(by_dir[directory], key=lambda x: x["id"])
                    for sk in skills_in_dir:
                        cid = sk["id"]
                        mapped_id = sk["mapped_to"]
                        mapped_score = sk["mapped_score"]
                        m_type = sk.get("match_type")
                        canon_level = sk.get("canon_level", "0★")

                        match_note = ""
                        if mapped_score > 0:
                            rank_color = RANK_COLORS.get(canon_level, RANK_COLORS["0★"])

                            if m_type in ("origin", "named") and "/" in mapped_id:
                                parts = mapped_id.split("/", 1)
                                contrib, nickname = parts
                                if contrib == REDACTED_BLOCK:
                                    handle_color = COLOR_REDACTED
                                else:
                                    handle_color = COLOR_CONTRIBUTOR
                                colored_mapped = f"{_fg(*handle_color)}{contrib}{_reset()}/{_fg(*rank_color)}{nickname} {canon_level}{_reset()}"
                            else:
                                colored_mapped = (
                                    f"{_fg(*rank_color)}/{mapped_id.lstrip('/')}{_reset()}"
                                )

                            if m_type in ("origin", "named", "exact_generic"):
                                match_note = f"  {_fg(*RANK_COLORS['0★'])}→ {colored_mapped}{_reset()}"
                            else:
                                match_note = f"  {_fg(*RANK_COLORS['0★'])}→ {colored_mapped}{_fg(*RANK_COLORS['0★'])} ({mapped_score:.0%} semantic){_reset()}"

                        if group_id == "other":
                            user_label = f"{_fg(*COLOR_LOCAL_USER)}{_bold()}/{cid.lstrip('/')}{_reset()}"
                        else:
                            user_label = f"{_fg(*RANK_COLORS['0★'])}{_bold()}/{cid.lstrip('/')}{_reset()}"

                        print(f"  ○ {user_label}{match_note}")

            print_group("origin", origin_group)
            print_group("named", named_group)
            print_group("generic", generic_group)
            print_group("other", other_group)

        # Persist the custom state mapping
        os.makedirs(".gaia", exist_ok=True)
        custom_state_path = ".gaia/custom_state.json"
        full_custom_state = {"customSkills": custom_state_skills}
        if os.path.exists(custom_state_path):
            try:
                with open(custom_state_path, "r", encoding="utf-8") as f:
                    old_state = json.load(f)
                    # Merge customFusions if they exist
                    if "customFusions" in old_state:
                        full_custom_state["customFusions"] = old_state["customFusions"]
            except:
                pass

        with open(custom_state_path, "w", encoding="utf-8") as f:
            json.dump(full_custom_state, f, indent=2)

        # Write scan-state.json — reusable output for fuse and other commands
        from gaia_cli.registry import scan_state_path as _scan_state_path
        _ss_out = _scan_state_path(args.registry)
        os.makedirs(os.path.dirname(_ss_out), exist_ok=True)
        _scan_state = {
            "skills": [
                {
                    "id": sk["mapped_to"],
                    "localId": sk["id"].lstrip("/"),
                    "level": sk["canon_level"],
                    "type": sk.get("skill_type", "basic"),
                    "description": sk.get("description", ""),
                    "local": sk.get("match_type") is None and sk["mapped_score"] == 0.0,
                    "origin": sk.get("match_type") == "origin",
                    "namedRef": sk["mapped_to"] if sk.get("match_type") in ("origin", "named") else None,
                    "matchType": sk.get("match_type"),
                }
                for sk in custom_state_skills
            ]
        }
        with open(_ss_out, "w", encoding="utf-8") as f:
            json.dump(_scan_state, f, indent=2)
        if not quiet:
            print(f"\n{_fg(*COLOR_GREY)}→ Wrote {_ss_out}{_reset()}")

    # Refresh context to include newly mapped custom skills for fusions/paths
    ctx = LocalContext.load(
        args.registry, username or "", include_scan=True, global_search=global_search
    )

    tips = []

    tree = load_tree(username, registry_path=args.registry)
    if tree:
        with open(graph_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
        skill_map = {s["id"]: s for s in graph_data.get("skills", [])}
        unlocked = [s.get("skillId") for s in tree.get("unlockedSkills", [])]

        # Calculate novel IDs (those that didn't resolve to canon)
        novel_ids = [
            sk["id"] for sk in custom_state_skills if sk["mapped_score"] == 0.0
        ]

        combos = get_combinations(graph_data, unlocked, resolved)
        if combos:
            # Persist fusion candidates so `gaia fuse` can find them
            tree["pendingCombinations"] = combos
            save_tree(username, tree, registry_path=args.registry)
            if not quiet:
                print("\nNew fusion candidates:")
                for c in combos:
                    result_skill = skill_map.get(c["candidateResult"], {})
                    result_type = result_skill.get("type", "extra")
                    print(
                        render_fusion_diagram(
                            c["detectedSkills"],
                            c["candidateResult"],
                            result_type,
                            canon=canon,
                            ctx=ctx,
                        )
                    )
                tips.append(
                    f"`{_fg(*COLOR_FUSE_PURPLE)}gaia fuse <skill>{_reset()}`: Confirm detected combinations"
                )

        # Path engine integration
        old_paths = load_paths()
        owned_ids = [s.get("skillId") for s in tree.get("unlockedSkills", [])]
        new_paths = compute_paths(graph_data, owned_ids, resolved, novel_ids=novel_ids)
        new_paths["userId"] = username
        changes = diff_paths(old_paths, new_paths)
        save_paths(new_paths)

        # Show unlock cards for newly reachable skills
        if changes.get("new_near_unlocks"):
            print()
            for sid in changes["new_near_unlocks"]:
                skill = skill_map.get(sid)
                if skill:
                    opened = [
                        p
                        for p in new_paths.get("availablePaths", [])
                        if p.get("distance", 99) <= 2
                    ]
                    print(render_unlock_card(skill, opened[:3], canon=canon, ctx=ctx))
                    print()

        # Path summary
        if new_paths.get("nearUnlocks") or new_paths.get("oneAway"):
            print(render_path_summary(new_paths))

        render_user_tree_outputs(
            username,
            tree,
            graph_data,
            args.registry,
            quiet=quiet,
            is_global=getattr(args, "global_flag", False),
            custom=not canon,
        )

        if not quiet and not use_json:
            # Collect final tips
            if any(sk.get("mapped_score", 0) == 0 for sk in custom_state_skills):
                tips.append(
                    f"`{_fg(*COLOR_LOCAL_USER)}gaia push{_reset()}`: Push your custom skills for review"
                )

            tips.append(
                f"`{_fg(*COLOR_FUSE_PURPLE)}gaia fuse{_reset()}`: Create custom fusion paths"
            )

            tips.append(
                f"`{_fg(*COLOR_APEX_GOLD)}gaia tree{_reset()}`: Visualize your progress"
            )

            if tips:
                print(f"\n{_bold()}Tips:{_reset()}")
                for tip in tips:
                    print(f"  • {tip}")


def render_user_tree_outputs(
    username: str,
    tree: dict | None,
    graph_data: dict | None,
    registry_path: str,
    quiet: bool = False,
    is_global: bool = False,
    custom: bool = True,
) -> tuple[str, str] | None:
    if not tree:
        return None
    mode = "default"
    buf = StringIO()
    with redirect_stdout(buf):
        show_tree(
            tree,
            graph_data=graph_data,
            registry_path=registry_path,
            mode=mode,
            custom=custom,
            username=username,
        )
    text = buf.getvalue()

    # Save to local workspace by default, only use registry path if --global is set
    if is_global:
        out_dir = generated_output_dir(registry_path)
    else:
        out_dir = os.path.join(os.getcwd(), "generated-output")

    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, "tree.md")
    html_path = os.path.join(out_dir, "tree.html")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Gaia Skill Tree\n\n```text\n")
        f.write(text)
        f.write("```\n")
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
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
        print(f"\n{_fg(*COLOR_GREY)}→ Saved {md_path} & {html_path}{_reset()}")
    return html_path, md_path


def promote_all_candidates(username: str, registry_path: str) -> list[dict]:
    promoted = []
    for candidate in promotable_candidates(registry_path, username=username):
        promoted.append(
            promote_from_candidates(
                username,
                candidate["skillId"],
                registry_path,
            )
        )
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
            s
            for s in graph_data.get("skills", [])
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
                    print(
                        f"  /{candidate['id']} - {candidate.get('name', candidate['id'])}"
                    )
            sys.exit(1)

    skill_id = skill["id"]
    canon = getattr(args, "canon", False)

    config = load_config() or {}
    username = config.get("gaiaUser")
    ctx = (
        LocalContext.load(args.registry, username, include_scan=False)
        if username
        else None
    )

    if canon:
        display = f"/{skill_id}"
    elif ctx and ctx.is_named(skill_id):
        display = ctx.display_name(skill_id)
    else:
        display = skill.get("name") or f"/{skill_id}"
    print(f"{display}")

    user_level = ctx.skill_level(skill_id) if ctx else skill.get("level", "?")
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
    username = config.get("gaiaUser")
    tree = load_tree(username, registry_path=args.registry)
    if not tree:
        print(f'No skill tree found for user "{_fg(*COLOR_LOCAL_USER)}{username}{_reset()}".')
        print("Next steps:")
        print("  gaia scan")
        print("  gaia push --dry-run")
        print("  gaia push --no-pr")
        print(f"Or create skill-trees/{_fg(*COLOR_LOCAL_USER)}{username}{_reset()}/skill-tree.json in the registry.")
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

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    skill_map = {s["id"]: s for s in graph_data.get("skills", [])}
    username = config.get("gaiaUser")
    tree = load_tree(username, registry_path=args.registry)

    # Determine which skill to appraise
    skill_id = getattr(args, "skillId", None)
    if not skill_id:
        # Try interactive picker first
        all_skills = []
        for s in skill_map.values():
            all_skills.append({
                "id": s["id"],
                "type": s.get("type", "basic"),
                "level": s.get("level", "0★"),
                "description": s.get("description", ""),
                "local": False,
                "origin": False,
                "named_ref": None,
            })
        
        picked = select_skill(all_skills, "Select a skill to appraise:", username=username)
        if picked:
            skill_id = picked
        elif tree and tree.get("unlockedSkills"):
            # Fallback: most recently unlocked skill
            sorted_skills = sorted(
                tree["unlockedSkills"],
                key=lambda s: s.get("unlockedAt", ""),
                reverse=True,
            )
            skill_id = sorted_skills[0]["skillId"]
        else:
            # Fall back to most recent near-unlock from paths
            paths = load_paths()
            if paths and paths.get("nearUnlocks"):
                skill_id = paths["nearUnlocks"][0]["skillId"]
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
        owned_ids = {s["skillId"] for s in tree.get("unlockedSkills", [])}
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
    for p in skill.get("prerequisites", []):
        prereq_status[p] = p in available

    # Derivatives
    derivatives = []
    for d_id in skill.get("derivatives", []):
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

    print(
        render_appraise_card(
            skill,
            prereq_status,
            derivatives,
            actions,
            owned=owned,
            canon=canon,
            display_name=display_name,
        )
    )
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

    username = config.get("gaiaUser")
    graph_path = registry_graph_path(args.registry)

    if not os.path.exists(graph_path):
        print("Registry graph not found.")
        return

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    tree = load_tree(username, registry_path=args.registry)
    if not tree:
        if not os.path.exists(promotion_candidates_path(args.registry)):
            print(
                "No promotion candidates found. Run `gaia scan` first to detect skills.",
                file=sys.stderr,
            )
        else:
            print(f"No skill tree found for user '{_fg(*COLOR_LOCAL_USER)}{username}{_reset()}'.", file=sys.stderr)
        return

    skill_id = getattr(args, "skillId", None)
    display_name = getattr(args, "name", None)

    try:
        if getattr(args, "unique", False):
            if not skill_id:
                print("Usage: gaia promote <skill> --unique", file=sys.stderr)
                sys.exit(2)
            from .promotion import promote_to_unique

            result = promote_to_unique(skill_id, args.registry)
            print(
                f"\n◉ {result['displayName']} promoted to Unique Skill (type: unique)!"
            )
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
                picked = select_promotion_candidate(
                    candidates, "Select skill to promote:"
                )
                if picked:
                    skill_id = picked
            if not skill_id:
                from gaia_cli.registry import promotion_candidates_path

                if not os.path.exists(promotion_candidates_path(args.registry)):
                    print(
                        "No promotion candidates found. Run `gaia scan` first to detect skills.",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "Usage: gaia promote <skill> or gaia promote --all",
                        file=sys.stderr,
                    )
                sys.exit(2)
        result = promote_from_candidates(
            username, skill_id, args.registry, new_display_name=display_name
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    # Show celebration
    skill_map = {s["id"]: s for s in graph_data.get("skills", [])}
    skill = skill_map.get(skill_id, {"id": skill_id, "name": skill_id, "type": "basic"})
    level_name = LEVEL_NAMES.get(result["newLevel"], result["newLevel"])
    print(
        f"\n✦ {skill.get('name', skill_id)} promoted to Level {result['newLevel']} ({level_name})!"
    )
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
        print(
            f"Skill '{skill_id}' is not an ultimate skill. Use --ultimate only for ultimate skills."
        )
        return
    if not getattr(args, "ultimate", False) and skill.get("type") == "ultimate":
        print(
            "Tip: this is an ultimate skill. Re-run with `gaia propose /<skill> --ultimate`."
        )

    print(f"Appraisal: /{skill['id']} ({skill.get('type', 'unknown')})")
    print(f"Name: {skill.get('name', skill['id'])}")
    print(f"Description: {skill.get('description', '')}")

    suggested = f"{config.get('gaiaUser', 'gaiabot')}/{skill_id}"
    target_named = getattr(args, "target", None)
    if not target_named:
        if sys.stdin.isatty() and not getattr(args, "yes", False):
            target_named = (
                input(f"Name this skill as [{suggested}]: ").strip() or suggested
            )
        else:
            target_named = suggested
    if "/" not in target_named:
        print("Named skill must be in '<contributor>/<name>' format.")
        return
    contributor, skill_name = target_named.split("/", 1)

    proposed_skill = build_proposed_skill(skill_id, detect_source_repo(config))
    proposed_skill["name"] = skill.get("name", proposed_skill["name"])
    proposed_skill["description"] = skill.get(
        "description", proposed_skill["description"]
    )
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
        registry_path=args.registry,
    )
    print(f"Proposed named skill: {target_named}")
    print(f"  saved {os.path.basename(batch_path)}")

    if getattr(args, "no_pr", False) or getattr(args, "no_issue", False):
        print("Skipped issue creation (--no-pr/--no-issue).")
        return
    open_intake_issue(
        config.get("gaiaUser", "unknown"),
        batch,
        batch_path=batch_path,
        repo_root=args.registry,
    )


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
                print(
                    f"    level: {n.get('levelFloor')} (effective: {n.get('effectiveLevelFloor')})"
                )
            prereqs = n.get("satisfiedPrereqs", [])
            if prereqs:
                print(f"    from: {', '.join(prereqs)}")
        print()

    one_away = paths.get("oneAway", [])
    if one_away:
        print("One prerequisite away:")
        for o in one_away[:8]:
            print(
                f"  ○ {o.get('name', o['skillId'])} - missing: {o.get('missingPrereq', '?')}"
            )
            if o.get("levelFloor") and o.get("effectiveLevelFloor"):
                print(
                    f"    level: {o.get('levelFloor')} (effective: {o.get('effectiveLevelFloor')})"
                )
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
        owned_ids = {
            s["skillId"] for s in tree.get("unlockedSkills", []) if s.get("skillId")
        }

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
            text = render_unlock_path(
                graph_data, skill_id, owned_ids, owned_only=owned_only
            )
            print(text)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def hook_command(args):
    """Internal command invoked by Claude Code hook."""
    hook_entry(event=getattr(args, "event", "file_edit"))


def doctor_command(args):
    config_path = ".gaia/config.toml"
    config = load_config()
    registry_path = os.path.abspath(str(args.registry))
    print("Gaia CLI: OK")
    print(f"Registry path: {args.registry}")
    print(
        f"Registry graph: {'found' if os.path.exists(registry_graph_path(registry_path)) else 'missing'}"
    )
    print(f"Config: {config_path if os.path.exists(config_path) else 'missing'}")
    if not config:
        print("User: unknown")
        print("Skill tree: unknown")
        return

    username = config.get("gaiaUser")
    print(f"User: {_fg(*COLOR_LOCAL_USER)}{username}{_reset()}")
    tree_path = user_tree_path(registry_path, username or "")
    print(f"Skill tree: {'found' if os.path.exists(tree_path) else 'missing'}")
    emb_path = embeddings_path(registry_path)
    print(f"Embeddings: {'found' if os.path.exists(emb_path) else 'missing'}")
    print("Scan paths:")
    for path in config.get("scanPaths", []):
        h_color = get_harness_color(path)
        status = 'exists' if os.path.exists(path) else 'missing'
        print(f"  - {_fg(*h_color)}{path}{_reset()} {status}")


def tree_command(args):
    if getattr(args, "check", False):
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
        with open(graph_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    tree = load_tree(config.get("gaiaUser"), registry_path=args.registry)
    mode = (
        "named"
        if getattr(args, "named", False)
        else ("title" if getattr(args, "title", False) else "default")
    )
    canon = getattr(args, "canon", False)
    custom = getattr(args, "custom", False) or (not canon and mode != "named")
    known_only = not getattr(args, "show_all", False)
    show_tree(
        tree,
        graph_data=graph_data,
        registry_path=args.registry,
        mode=mode,
        canon=canon,
        custom=custom,
        known_only=known_only,
        username=config.get("gaiaUser"),
    )
    try:
        detect_source_repo(config)
    except NonPublicRepoError:
        print(
            "\nTip: link a public GitHub repo and approved skills will start at 2★ once named."
        )
    except Exception:
        pass


def fuse_command(args):
    config = load_config()
    if not config:
        return
    username = config.get("gaiaUser")
    registry_path = args.registry

    # Load custom state
    custom_state_path = os.path.join(".gaia", "custom_state.json")
    custom_state = {"customSkills": [], "customFusions": {}}
    if os.path.exists(custom_state_path):
        try:
            with open(custom_state_path, "r", encoding="utf-8") as f:
                custom_state = json.load(f)
        except Exception:
            pass

    # Handle --delete
    fuse_color = TIER_COLORS["extra"]
    if getattr(args, "delete", False):
        target = getattr(args, "skillId", None)
        fusions = custom_state.get("customFusions", {})
        if not target and sys.stdin.isatty():
            if not fusions:
                print(f"{_fg(*fuse_color)}No custom fusions found.{_reset()}")
                return
            target = select_fusion_to_edit(fusions, "Select custom fusion to delete:")

        if target and target in fusions:
            del fusions[target]
            custom_state["customFusions"] = fusions
            os.makedirs(".gaia", exist_ok=True)
            with open(custom_state_path, "w", encoding="utf-8") as f:
                json.dump(custom_state, f, indent=2)
            print(f"{_fg(*fuse_color)}Deleted custom fusion /{target}.{_reset()}")
        else:
            print(f"{_fg(*fuse_color)}Custom fusion /{target} not found.{_reset()}")
        return

    # Programmatic custom fusion: gaia fuse --skills skill1,skill2 --name target-id
    if getattr(args, "skills", None):
        target = getattr(args, "skillId", None) or getattr(args, "name", None)
        if not target:
            print(
                f"{_fg(*fuse_color)}Error: must specify target skill ID (e.g. `gaia fuse target-id --skills s1,s2`){_reset()}",
                file=sys.stderr,
            )
            return
        sources = [s.strip().lstrip("/") for s in args.skills.split(",")]
        custom_state.setdefault("customFusions", {})[target] = sources
        os.makedirs(".gaia", exist_ok=True)
        with open(custom_state_path, "w", encoding="utf-8") as f:
            json.dump(custom_state, f, indent=2)
        print(
            f"{_fg(*fuse_color)}Saved custom fusion: {' + '.join('/' + s for s in sources)} → /{target}{_reset()}"
        )
        print(
            f"\n{_fg(*fuse_color)}Note: Custom fusions are saved locally in .gaia/custom_state.json.{_reset()}"
        )
        print(
            f"{_fg(*fuse_color)}If pushed to the registry and accepted into canon, this fusion becomes permanent for all users!{_reset()}"
        )
        return

    # Interactive Menu
    target = getattr(args, "skillId", None)
    if not target and sys.stdin.isatty():
        if not _has_interactive():
            print("\nInteractive fuse requires the 'questionary' package.")
            print("Install it with: pip install questionary")
            print("\nOr use the programmatic form:")
            print(
                f"  {_fg(*COLOR_FUSE_PURPLE)}gaia fuse <skill_id> --skills skill1,skill2{_reset()}"
            )
            return

        import questionary

        while True:
            tree = load_tree(username, registry_path=registry_path)
            pending_combos = tree.get("pendingCombinations", []) if tree else []

            choices = []
            if pending_combos:
                choices.append(
                    questionary.Choice(
                        "Confirm detected combination (from scan)", value="pending"
                    )
                )

            # Check for promotions
            promo_payload = {}
            try:
                promo_payload = load_promotion_candidates(registry_path)
                if promo_payload.get("candidates"):
                    choices.append(
                        questionary.Choice(
                            "Promote a skill (level-up)", value="promote"
                        )
                    )
            except:
                pass

            choices.extend(
                [
                    questionary.Choice("Create new custom fusion path", value="new"),
                    questionary.Choice("Edit existing custom fusions", value="edit"),
                    questionary.Choice("Delete custom fusion", value="delete"),
                    questionary.Choice("Exit", value="exit"),
                ]
            )

            choice = questionary.select(
                "Gaia Fuse Menu:  (Ctrl+C to cancel)",
                choices=choices,
                style=fuse_style(),
            ).ask()
            if not choice or choice == "exit":
                return

            if choice == "delete":
                args.delete = True
                fuse_command(args)
                return  # Delete command handles its own state

            if choice == "pending":
                picked = select_fusion_candidate(
                    pending_combos, "Select fusion candidate:"
                )
                if picked:
                    target = picked
                    break  # Exit loop to perform fusion
                continue  # Back to menu

            elif choice == "promote":
                candidates = promo_payload.get("candidates", [])
                picked = select_promotion_candidate(candidates)
                if picked:
                    target = picked
                    break  # Exit loop to perform fusion
                continue  # Back to menu

            elif choice == "edit":
                fusions = custom_state.get("customFusions", {})
                if not fusions:
                    print(f"{_fg(*fuse_color)}No custom fusions found.{_reset()}")
                    continue
                # Load scan-state for rich flowchart rendering (level, named_ref, origin)
                from gaia_cli.registry import scan_state_path as _ssp_edit
                _skill_meta_edit: dict = {}
                _ss_edit = _ssp_edit(registry_path)
                if os.path.exists(_ss_edit):
                    try:
                        with open(_ss_edit, "r", encoding="utf-8") as _fe:
                            for _entry in json.load(_fe).get("skills", []):
                                _skill_meta_edit[_entry["id"]] = _entry
                                if _entry.get("localId"):
                                    _skill_meta_edit["/" + _entry["localId"]] = _entry
                    except Exception:
                        pass
                target = select_fusion_to_edit(
                    fusions,
                    "Select custom fusion to edit:",
                    skill_meta=_skill_meta_edit,
                    username=username,
                )
                if not target:
                    continue
                # Fall through to 'new' logic but with pre-filled or specific edit behavior
                choice = "new"

            if choice == "new":
                # Select skills to combine
                # Load all available skills (unlocked + detected)
                ctx = LocalContext.load(
                    registry_path, username or "", include_scan=True
                )
                all_ids = sorted(list(ctx.owned_ids))

                # Load generic graph for fallback metadata
                graph_data = {}
                graph_p = registry_graph_path(registry_path)
                if os.path.exists(graph_p):
                    with open(graph_p, "r") as f:
                        graph_data = json.load(f)
                skill_info_map = {s["id"]: s for s in graph_data.get("skills", [])}

                # Load scan-state.json (written by `gaia scan`) — authoritative
                # source for named/origin level, type, and description.
                from gaia_cli.registry import scan_state_path as _ssp
                scan_map = {}
                _ss_path = _ssp(registry_path)
                if os.path.exists(_ss_path):
                    try:
                        with open(_ss_path, "r", encoding="utf-8") as _f:
                            for entry in json.load(_f).get("skills", []):
                                scan_map[entry["id"]] = entry
                                if entry.get("localId"):
                                    scan_map["/" + entry["localId"]] = entry
                    except Exception:
                        pass

                selector_choices = []
                for sid in all_ids:
                    ss = scan_map.get(sid) or {}
                    sinfo = skill_info_map.get(sid, {})
                    selector_choices.append(
                        {
                            "id": sid,
                            "type": ss.get("type") or sinfo.get("type", "basic"),
                            "level": ss.get("level") or sinfo.get("level", "0★"),
                            "description": ss.get("description") or sinfo.get("description", ""),
                            "local": ss.get("local", sid in ctx.novel_ids),
                            "origin": ss.get("origin", ctx.is_origin(sid)),
                            "named_ref": ss.get("namedRef") or ctx.named_ref(sid),
                        }
                    )

                selected = select_multiple_skills(
                    selector_choices,
                    f"Select skills to combine into /{target if target else '???'}:",
                    username=username,
                )
                if not selected:
                    continue  # Back to menu

                # Calculate max star count from prerequisites
                max_stars = 0
                for sid in selected:
                    ss = scan_map.get(sid) or {}
                    sinfo = skill_info_map.get(sid, {})
                    lvl = ss.get("level") or sinfo.get("level", "0★")
                    max_stars = max(max_stars, level_num(lvl))
                max_stars_str = f"{max_stars}★"

                if not target:
                    # Stage 2: pick the target from the same installed/detected list
                    target = select_skill(
                        selector_choices,
                        "Select target skill to reach:",
                        disabled_ids=selected,
                        username=username,
                    )
                if not target:
                    continue  # Back to menu

                # Save fusion with metadata (EXTRA type and inherited level)
                custom_state.setdefault("customFusions", {})[target] = {
                    "sources": selected,
                    "type": "extra",
                    "level": max_stars_str,
                }
                os.makedirs(".gaia", exist_ok=True)
                with open(custom_state_path, "w", encoding="utf-8") as f:
                    json.dump(custom_state, f, indent=2)

                print(
                    f"\n✓ Saved custom fusion: {' + '.join('/' + s for s in selected)} → /{target} (EXTRA {max_stars_str})"
                )
                print(
                    f"\n{_fg(*fuse_color)}Note: Custom fusions are saved locally in .gaia/custom_state.json.{_reset()}"
                )
                print(
                    f"{_fg(*fuse_color)}If pushed to the registry and accepted into canon, this fusion becomes permanent for all users!{_reset()}"
                )
                return

    # If we have a target but didn't go through 'new' flow, it might be a pending combo or promotion
    if not target:
        print(
            f"{_fg(*fuse_color)}Usage: gaia fuse <skill_id>{_reset()}", file=sys.stderr
        )
        return

    # Check combinations first
    tree = load_tree(username, registry_path=registry_path)
    pending_combos = tree.get("pendingCombinations", []) if tree else []
    combo_match = next(
        (p for p in pending_combos if p.get("candidateResult") == target), None
    )

    if combo_match:
        print(f"{_fg(*fuse_color)}Fusing combination /{target}...{_reset()}")
        tree.setdefault("unlockedSkills", []).append(
            {
                "skillId": target,
                "level": combo_match.get("levelFloor"),
                "unlockedAt": datetime.now(timezone.utc).isoformat(),
                "unlockedIn": "local-repo",
                "combinedFrom": combo_match.get("detectedSkills", []),
            }
        )
        tree["pendingCombinations"] = [
            p for p in pending_combos if p.get("candidateResult") != target
        ]
        stats = tree.get("stats", {})
        stats["totalUnlocked"] = stats.get("totalUnlocked", 0) + 1
        tree["stats"] = stats
        save_tree(username, tree, registry_path=registry_path)

        from gaia_cli.timeline import append_skill_tree_event

        append_skill_tree_event(
            username,
            target,
            "fuse",
            f"Fused from {', '.join(combo_match.get('detectedSkills', []))}",
            registry_path=registry_path,
        )

        open_pr(username, tree, candidate_result=target)
        return

    # Check promotions next
    try:
        payload = load_promotion_candidates(registry_path)
        if any(c.get("skillId") == target for c in payload.get("candidates", [])):
            print(f"{_fg(*fuse_color)}Fusing promotion for /{target}...{_reset()}")
            result = promote_from_candidates(
                username,
                target,
                registry_path,
                new_display_name=getattr(args, "name", None),
            )
            print(f"Promoted /{result['skillId']} to Level {result['newLevel']}.")
            return
    except Exception:
        pass

    print(
        f"{_fg(*fuse_color)}Skill /{target} is not a valid combination or promotion candidate.{_reset()}"
    )
    print(
        f"{_fg(*fuse_color)}Run `gaia scan` to refresh candidates, or use interactive `{_fg(*COLOR_FUSE_PURPLE)}gaia fuse{_reset()}{_fg(*fuse_color)}` to create a custom path.{_reset()}"
    )


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
    col_id = max(len(r["id"]) for r in results)
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

    try:
        batch = build_skill_batch([], config, args.registry)
        source_repo = batch["sourceRepo"]
    except NonPublicRepoError as exc:
        print(
            "\nYour skills are ready for review!\n"
            "Skills pushed from outside a public GitHub repo start at 1★ in the registry.\n"
            "Once you link a public repo, approved skills will start at 2★ instead.\n"
            "  → Add a remote:  git remote add origin https://github.com/<you>/<repo>\n",
            file=sys.stderr,
        )
        username_fallback = str(exc)
        batch = build_skill_batch(
            [], config, args.registry, source_repo=f"{username_fallback}/local-repo"
        )

    # Guard 1: check if empty initially
    if (
        not batch.get("proposedSkills")
        and not batch.get("knownSkills")
        and not batch.get("proposedCombinations")
    ):
        print(
            f"Error: No skills to be pushed. Please install newer skills then gaia scan, or `{_fg(*COLOR_FUSE_PURPLE)}gaia fuse{_reset()}` custom skills before pushing.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Interactive Selection of items to push
    if sys.stdin.isatty() and not getattr(args, "yes", False) and _has_interactive():
        selected = select_push_batch(
            batch, f"Select items to push to registry from {batch['sourceRepo']}:"
        )
        if not selected:
            print("Aborted.")
            return

        selected_set = set(selected)
        batch["proposedCombinations"] = [
            f
            for f in batch.get("proposedCombinations", [])
            if f"fusion:{f['candidateResult']}" in selected_set
        ]
        batch["knownSkills"] = [
            k
            for k in batch.get("knownSkills", [])
            if f"known:{k['skillId']}" in selected_set
        ]
        batch["proposedSkills"] = [
            p
            for p in batch.get("proposedSkills", [])
            if f"proposed:{p['id']}" in selected_set
        ]
        # Filter similarity map to only include selected proposed skills
        selected_proposed_ids = {p["id"] for p in batch["proposedSkills"]}
        batch["similarity"] = [
            s
            for s in batch.get("similarity", [])
            if s.get("sourceSkillId") in selected_proposed_ids
        ]
    elif sys.stdin.isatty() and not getattr(args, "yes", False):
        # Fallback for non-interactive but TTY
        fusions = batch.get("proposedCombinations", [])
        if fusions:
            print(f"\n{_bold()}{_fg(*COLOR_LOCAL_USER)}1. Fuses -> Review{_reset()}")
            for f in fusions:
                res = f.get("candidateResult", "?")
                srcs = f.get("detectedSkills", [])
                print(f"   [FUSION] {' + '.join(srcs)} → {res}")

        proposed = batch.get("proposedSkills", [])
        if proposed:
            print(
                f"\n{_bold()}{_fg(*COLOR_LOCAL_USER)}2. Custom skills -> Review{_reset()}"
            )
            for p in proposed:
                print(f"   [CUSTOM] {p.get('id')}")

        known = batch.get("knownSkills", [])
        if known:
            print(
                f"\n{_bold()}{_fg(*COLOR_LOCAL_USER)}3. Starless skills -> Named proposal{_reset()}"
            )
            for k in known:
                sid = k.get("skillId", "?")
                local_id = k.get("localId")
                if local_id and local_id != sid:
                    print(f"   [STARLESS] /{local_id} -> /{sid}")
                else:
                    print(f"   [STARLESS] /{sid}")
        print()

    # Guard 2: check if empty after filtering
    if (
        not batch.get("proposedSkills")
        and not batch.get("knownSkills")
        and not batch.get("proposedCombinations")
    ):
        print(
            f"Error: No items selected to be pushed. Run `gaia scan` or `{_fg(*COLOR_FUSE_PURPLE)}gaia fuse{_reset()}` to find more.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.dry_run:
        print(json.dumps(batch, indent=2))
        return

    # Security scanner — runs after the batch is finalised but before we
    # persist anything.  Blocks on high-severity findings unless the caller
    # supplies --allow-unsafe AND --reason (audit trail).  Medium/low
    # findings are surfaced as warnings only.
    from gaia_cli.push import scanBatchForSecurity
    from gaia_cli.securityScanner import (
        formatFindings,
        hasHighSeverity,
    )

    findings = scanBatchForSecurity(batch, args.registry)
    if findings:
        print(formatFindings(findings), file=sys.stderr)
        if hasHighSeverity(findings):
            allowUnsafe = getattr(args, "allowUnsafe", False)
            overrideReason = (getattr(args, "overrideReason", "") or "").strip()
            highCount = sum(1 for f in findings if f.severity == "high")
            if not allowUnsafe:
                print(
                    f"Security scanner blocked {highCount} high-severity finding(s). "
                    f"Re-run with --allow-unsafe and --reason \"<text>\" to override.",
                    file=sys.stderr,
                )
                sys.exit(2)
            if not overrideReason:
                print(
                    "Use --reason to document override (required for audit trail).",
                    file=sys.stderr,
                )
                sys.exit(2)
            print(
                f"Security scanner override accepted: {highCount} high-severity "
                f"finding(s) bypassed. Reason: {overrideReason}",
                file=sys.stderr,
            )

    if sys.stdin.isatty() and not getattr(args, "yes", False):
        try:
            if _use_color():
                push_color = COLOR_LOCAL_USER
                grey = RANK_COLORS["0★"]
                prompt = (
                    f"{_bold()}{_fg(*TIER_COLORS['ultimate'])}? {_fg(255, 255, 255)}Push selected items to gaia registry from {_fg(*RANK_COLORS['2★'])}{batch['sourceRepo']}{_reset()}{_fg(255, 255, 255)}? "
                    f"{_fg(*grey)}[{_fg(*push_color)}Y{_fg(*grey)}/n]: {_reset()}"
                )
            else:
                prompt = f"Push selected items to gaia registry from {batch['sourceRepo']}? [Y/n]: "
            ans = input(prompt).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(1)
        if ans == "n":
            print("Aborted.")
            return

    batch_path = write_skill_batch(batch, args.registry)
    push_color = COLOR_LOCAL_USER  # Green
    print(f"  {_fg(*push_color)}saved {os.path.basename(batch_path)}{_reset()}")

    from gaia_cli.timeline import append_skill_tree_event

    username = config.get("gaiaUser")
    if username:
        for known in batch.get("knownSkills", []):
            append_skill_tree_event(
                username,
                known.get("skillId"),
                "push",
                f"Pushed in batch {batch.get('batchId')}",
                registry_path=args.registry,
            )

    if getattr(args, "no_issue", False):
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
    location = getattr(args, "install_location", None)
    if location in ("local", "global"):
        return location
    return "local"


def install_command(args):
    from gaia_cli.share import _looks_like_bundle_ref, install_bundle

    location = _resolve_install_location(args)

    if args.list:
        interactive_install(args.registry, location=location)
        return
    # A bundle ref (a .json path or an http(s) URL) routes to the guided
    # share-bundle flow; a bare slug or contributor/slug is a named skill.
    if args.skill_id and _looks_like_bundle_ref(args.skill_id):
        try:
            install_bundle(args.skill_id, args.registry, location=location)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        return
    if not args.skill_id:
        print("Usage: gaia install <skill_id>", file=sys.stderr)
        print("  To update the Gaia CLI, use: gaia update", file=sys.stderr)
        print(
            "  To update all installed skills, use: gaia skills update", file=sys.stderr
        )
        sys.exit(2)

    # Use suite logic if flagged or implicitly requested
    if getattr(args, "ultimate", False) or getattr(args, "suite", False):
        success = install_suite(args.skill_id, args.registry, location=location)
    else:
        success = install_skill(args.skill_id, args.registry, location=location)

    if not success:
        sys.exit(1)


def uninstall_command(args):

    success = uninstall_skill(args.skill_id.lstrip("/"))
    if not success:
        sys.exit(1)


def share_command(args):
    from gaia_cli.share import build_share_bundle, default_bundle_path, write_bundle

    config = load_config()
    if not config:
        print("Gaia not initialized. Run `gaia init` first.", file=sys.stderr)
        sys.exit(1)
    username = getattr(args, "user", None) or config.get("gaiaUser")
    if not username:
        print(
            "No Gaia user configured. Run `gaia init --user <name>`.", file=sys.stderr
        )
        sys.exit(1)

    try:
        bundle = build_share_bundle(username, args.registry)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if getattr(args, "stdout", False):
        print(json.dumps(bundle, indent=2))
        return

    out_path = getattr(args, "output", None) or default_bundle_path(
        username, args.registry
    )
    write_bundle(bundle, out_path)

    n_skills = len(bundle.get("skillMeta", {}))
    n_install = len(bundle.get("install", []))
    try:
        rel = os.path.relpath(out_path)
    except ValueError:
        rel = out_path
    print(f"\n{_fg(*COLOR_LOCAL_USER)}✓ Share bundle written:{_reset()} {rel}")
    print(f"  {n_skills} skill(s), {n_install} installable")
    print("\nShare it — anyone with the file can preview your tree and install:")
    print(f"  gaia install {rel}")
    print("\nOr host the file and share the URL:")
    print("  gaia install https://<host>/<file>.json")


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
                pending.append(
                    {
                        "id": skill.get("id"),
                        "name": skill.get("name", skill.get("id")),
                        "description": skill.get("description", ""),
                        "level": skill.get("level", "1★"),
                        "pending": True,
                    }
                )
    return pending


def _load_skill_record_for_info(skill_id: str, registry_path: str) -> dict | None:
    """Load the on-disk record for a skill so verification can be recomputed.

    Returns the parsed dict (named-skill YAML frontmatter or generic-skill JSON
    node), or None when the skill cannot be located. Used by `gaia skills info`
    to reach the evidence + timeline arrays that the named-index summary view
    omits.
    """
    from gaia_cli.commands.dev import (
        _find_named_file,
        _parse_md,
    )
    from gaia_cli.registry import named_skills_dir, registry_nodes_dir

    if "/" in skill_id:
        named_dir = Path(named_skills_dir(registry_path))
        target = _find_named_file(named_dir, skill_id)
        if not target:
            return None
        meta, _ = _parse_md(target)
        return meta or {}

    nodes_dir = Path(registry_nodes_dir(registry_path))
    if not nodes_dir.is_dir():
        return None
    for path in nodes_dir.glob("**/*.json"):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("id") == skill_id:
            return data
    return None


def _print_verification_block(skill_id: str, registry_path: str) -> None:
    """Print the 4-tier verification breakdown for a skill, if computable.

    Recomputed on the fly from disk so the output is fresh even when the
    cached `verification.tier` field is missing or stale. Stays silent when
    the underlying record cannot be loaded (no noisy errors during info).
    """
    record = _load_skill_record_for_info(skill_id, registry_path)
    if record is None:
        return

    from gaia_cli.verification import (
        TIER_ORDER,
        filterScanEvents,
        resolveTier,
        utcNow,
    )

    evidence = record.get("evidence") or []
    timeline = record.get("timeline") or []
    scanEvents = filterScanEvents(timeline)
    highest, statusMap = resolveTier(record, evidence, scanEvents, utcNow())
    headline = highest if highest else "(none)"
    print(f"  Verification: {headline}")
    for tier in reversed(TIER_ORDER):
        status = statusMap[tier]
        marker = "✓" if status["passed"] else "✗"
        print(f"    {marker} {tier} — {status['reason']}")


def skills_command(args):

    config = load_config() or {}
    username = config.get("gaiaUser") or config.get("username")
    pending = (
        []
        if getattr(args, "exclude_pending", False)
        else _pending_skills(args.registry, username)
    )
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
        {
            "id": sid,
            "name": meta.get("name") or sid,
            "level": meta.get("level", "?"),
            "type": meta.get("type", "basic"),
            "description": meta.get("description", ""),
        }
        for sid, meta in list_available(args.registry)
    ]
    items = available + pending
    query = getattr(args, "query", None)
    if verb == "search" and query:
        q = query.lower()
        items = [
            item
            for item in items
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
        from gaia_cli.install import resolve_named_skill_reference
        try:
            resolved_id, _ = resolve_named_skill_reference(args.skill_id, args.registry)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        q = resolved_id if resolved_id else args.skill_id.lstrip("/")
        match = next((item for item in items if item.get("id") == q), None)
        if not match:
            print(f"Skill '/{q}' not found.", file=sys.stderr)
            sys.exit(1)
        sid = match.get("id", q)
        level = match.get("level", "?")
        skill_type = match.get("type", "basic")
        named_contrib = (
            ctx.named_contributor(sid) if ctx and ctx.is_named(sid) else None
        )
        is_local = ctx.is_local(sid) if ctx else False
        display = format_skill_colored(
            sid,
            level,
            named_contributor=named_contrib,
            is_local=is_local,
            local_user=ctx_user,
        )
        suffix = " (pending)" if match.get("pending") else ""
        print(f"{display}{suffix}")
        print(f"  Type:  {format_type_colored(skill_type)}")
        print(f"  Level: {format_level_colored(level)}")
        if match.get("description"):
            print(f"  {match['description']}")
        _print_verification_block(sid, args.registry)
        return
    if not items:
        print("No skills found.")
        return

    width = max(
        5,
        *(
            len(
                format_skill_plain(
                    item.get("id", ""),
                    named_contributor=ctx.named_contributor(item.get("id", ""))
                    if ctx and ctx.is_named(item.get("id", ""))
                    else None,
                    is_local=ctx.is_local(item.get("id", "")) if ctx else False,
                    local_user=ctx_user,
                )
            )
            for item in items
        ),
    )
    print(f"{'Skill':<{width}}  Level  Type")
    print("─" * (width + 22))
    for item in items:
        sid = item.get("id", "")
        level = item.get("level", "?")
        skill_type = item.get("type", "basic")
        named_contrib = (
            ctx.named_contributor(sid) if ctx and ctx.is_named(sid) else None
        )
        is_local = ctx.is_local(sid) if ctx else False

        display = format_skill_colored(
            sid,
            level,
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

    print("Fetching latest canonical registry from mbtiongson1/gaia-skill-tree...")
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
        no_upstream = any(
            p in stderr
            for p in (
                "no tracking information",
                "no upstream",
                "There is no tracking",
                "does not track",
                "has no upstream",
            )
        )
        if no_upstream:
            print(
                "Note: Could not git-pull registry (no upstream configured). Proceeding with package update...",
                file=sys.stderr,
            )
        else:
            print(
                f"Warning: git pull failed. Proceeding with package update...\n  {stderr}",
                file=sys.stderr,
            )
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
    pip_ok = (
        subprocess.run(
            [sys.executable, "-m", "pip"] + pip_args + ["gaia-cli", "--upgrade"],
        ).returncode
        == 0
    )
    if not pip_ok:
        pipx = subprocess.run(["pipx", "upgrade", "gaia-cli"]).returncode
        if pipx != 0:
            print(
                "Update failed: pip and pipx both returned non-zero.", file=sys.stderr
            )
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
            raise SystemExit(f"git {' '.join(cmd)} failed:\n{result.stderr.strip()}")
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


class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter to colorize specific commands in the help output."""

    def _format_action(self, action):
        import re

        parts = super()._format_action(action)
        if isinstance(action, argparse._SubParsersAction):
            # Commands considered "dev" or maintenance-heavy
            dev_cmds = ("dev", "validate", "test", "docs")
            ansi_escape = r"(?:\x1B\[[0-9;]*[a-zA-Z])*"
            
            for cmd in dev_cmds:
                # 1. Colorize the command in the {choices} list
                # Match start of list, middle of list, or end of list
                parts = parts.replace(f"{{{cmd},", f"{{{_fg(*COLOR_GREY)}{cmd}{_reset()},")
                parts = parts.replace(f",{cmd},", f",{_fg(*COLOR_GREY)}{cmd}{_reset()},")
                parts = parts.replace(f",{cmd}}}", f",{_fg(*COLOR_GREY)}{cmd}{_reset()}}}")

                # 2. Colorize the command in the individual help lines
                # Pattern: start of line, some whitespace, the command name (possibly colored), then at least two spaces
                parts = re.sub(
                    rf"^(\s+)({ansi_escape}{cmd}{ansi_escape})(\s\s+)",
                    rf"\1{_fg(*COLOR_GREY)}{cmd}{_reset()}\3",
                    parts,
                    flags=re.MULTILINE,
                )
        return parts


def get_parser():
    parser = argparse.ArgumentParser(
        prog="gaia",
        description="Gaia Registry CLI",
        epilog=COMMAND_USAGE,
        formatter_class=ColoredHelpFormatter,
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="Path to a local Gaia registry checkout. Defaults to auto-resolved local or global registry.",
    )
    parser.add_argument(
        "--global",
        "-g",
        dest="global_flag",
        action="store_true",
        help="Use global GAIA_HOME registry, ignoring any local .gaia/ config.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="store_true",
        help="Print the Gaia CLI version and exit.",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch the TUI (Terminal User Interface).",
    )
    parser.add_argument(
        "--canon",
        action="store_true",
        help="Show canonical registry data instead of local-first view.",
    )
    subparsers = parser.add_subparsers(
        dest="command", metavar="{" + ",".join(PUBLIC_COMMANDS) + "}", help=argparse.SUPPRESS
    )
    subparsers.add_parser("help", help="Show command help")
    init_parser = subparsers.add_parser(
        "init", help="Create or update local Gaia config"
    )
    init_parser.add_argument(
        "--user", help="Gaia username to write into .gaia/config.toml"
    )
    init_parser.add_argument(
        "--registry-ref", help="Gaia registry URL to write into .gaia/config.toml"
    )
    init_parser.add_argument(
        "--scan", action="append", help="Path to scan; repeat for multiple paths"
    )
    init_parser.add_argument(
        "--yes", "-y", "--y", action="store_true", help="Use non-interactive defaults"
    )
    init_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing .gaia/config.toml"
    )
    init_parser.add_argument(
        "--auto-prompt-combinations",
        action="store_true",
        help="Enable automatic prompts for detected skill combinations",
    )
    scan_parser = subparsers.add_parser(
        "scan", help="Scan configured paths and installed skills for skill evidence"
    )
    scan_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress scan output; only show notifications",
    )
    scan_parser.add_argument(
        "--json", action="store_true", help="Output scan results as JSON"
    )
    scan_parser.add_argument(
        "--all",
        action="store_true",
        help="Scan globally installed skills in addition to the local repository",
    )
    subparsers.add_parser(
        "fetch", help="Download the latest canonical registry files to .gaia/registry"
    )
    subparsers.add_parser("pull", help="Fetch registry data and run a full scan")
    subparsers.add_parser("update", help="Update Gaia CLI and registry")

    install_parser = subparsers.add_parser("install", help="Install a named skill")
    install_parser.add_argument(
        "skill_id",
        nargs="?",
        help="Skill ID, catalogRef, or unique bare slug to install",
    )
    install_parser.add_argument(
        "--list",
        action="store_true",
        help="List and interactively select skills to install",
    )
    install_parser.add_argument(
        "--ultimate",
        action="store_true",
        help="Batch-install all component skills (alias for --suite)",
    )
    install_parser.add_argument(
        "--suite",
        action="store_true",
        help="Batch-install all component skills for a suite",
    )
    install_parser.add_argument(
        "--install-location",
        dest="install_location",
        choices=["local", "global"],
        default="local",
        help="Where to install: local (.agents/.claude, default) or global (~/.gaia/skills)",
    )
    uninstall_parser = subparsers.add_parser(
        "uninstall", help="Uninstall a named skill"
    )
    uninstall_parser.add_argument("skill_id", help="Skill ID to uninstall")

    share_parser = subparsers.add_parser(
        "share", help="Export a portable share bundle of your skill tree"
    )
    share_parser.add_argument(
        "--user", help="User whose tree to share (default: configured gaiaUser)"
    )
    share_parser.add_argument(
        "-o", "--output", help="Path to write the bundle JSON (default: generated-output/share/)"
    )
    share_parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the bundle JSON to stdout instead of writing a file",
    )

    tree_parser = subparsers.add_parser("tree", help="Show your Gaia skill tree")
    tree_parser.add_argument(
        "--named",
        action="store_true",
        help="Show only skills that have a named implementation",
    )
    tree_parser.add_argument(
        "--title",
        action="store_true",
        help="Show display name instead of slash command / contributor ID",
    )
    tree_parser.add_argument(
        "--canon",
        action="store_true",
        help="Show canonical registry data instead of custom skills only.",
    )
    tree_parser.add_argument(
        "--check",
        action="store_true",
        help="Self-test: print all tier glyphs and rank chips in resolved token colors",
    )
    tree_parser.add_argument(
        "--custom", action="store_true", help="Show only custom skills (default)"
    )
    tree_parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        dest="show_all",
        help="Show all prerequisites including unowned (/??? entries)",
    )
    push_parser = subparsers.add_parser(
        "push", help="Prepare detected skills for review and file a GitHub issue"
    )
    push_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the skill batch without writing it",
    )
    push_parser.add_argument(
        "--no-issue",
        action="store_true",
        dest="no_issue",
        help="Write intake record without creating a GitHub issue",
    )
    push_parser.add_argument(
        "--no-pr", action="store_true", dest="no_issue", help=argparse.SUPPRESS
    )  # backward compat alias
    push_parser.add_argument(
        "--yes", "-y", "--y", action="store_true", dest="yes", help="Skip confirmation prompts"
    )
    push_parser.add_argument(
        "--allow-unsafe",
        action="store_true",
        dest="allowUnsafe",
        help="Override the security scanner block on high-severity findings (requires --reason)",
    )
    push_parser.add_argument(
        "--reason",
        type=str,
        default="",
        dest="overrideReason",
        help="Document an --allow-unsafe override for the audit trail",
    )
    propose_parser = subparsers.add_parser(
        "propose", help="Propose a single canonical skill as a named PR"
    )
    propose_parser.add_argument(
        "skillId", help="Canonical skill ID (accepts /skill-id form)"
    )
    propose_parser.add_argument(
        "--target", help="Named skill target in contributor/skill-name format"
    )
    propose_parser.add_argument(
        "--ultimate",
        action="store_true",
        help="Require that the selected skill is ultimate",
    )
    propose_parser.add_argument(
        "--yes", "-y", "--y", action="store_true", help="Use defaults without interactive prompts"
    )
    propose_parser.add_argument(
        "--no-pr",
        action="store_true",
        help="Write intake proposal without opening a PR",
    )
    subparsers.add_parser("version", help="Print the Gaia CLI version")
    subparsers.add_parser(
        "whoami", help="Show your Gaia identity and Verifier/operator status"
    )
    login_parser = subparsers.add_parser(
        "login", help="Sign in with GitHub via the device flow"
    )
    login_parser.add_argument(
        "--repo",
        help="Verify ownership of this owner/repo after signing in",
    )
    login_parser.add_argument(
        "--no-store",
        action="store_true",
        help="Authenticate for this session only; do not persist the token",
    )
    subparsers.add_parser(
        "logout",
        help="Sign out of GitHub (clears the local token; revoke in GitHub settings)",
    )
    reset_parser = subparsers.add_parser(
        "reset", help="Clear your skill tree and local state for a fresh start"
    )
    reset_parser.add_argument(
        "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
    )
    subparsers.add_parser(
        "mcp",
        help="Run the bundled Gaia MCP server",
        description=(
            "Start the Gaia MCP (Model Context Protocol) server, which exposes the skill registry "
            "to AI tools and IDE integrations via stdio. "
            "Requires building the server first: run `npm run build` inside packages/mcp/."
        ),
    )
    release_parser = subparsers.add_parser(
        "release", help="Bump version, commit, tag, and push to trigger GitHub Release"
    )
    release_parser.add_argument("release_type", choices=("patch", "minor", "major"))
    release_parser.add_argument(
        "--sync",
        action="store_true",
        help="Force sync versions if they disagree before bump",
    )
    release_parser.add_argument(
        "--no-push",
        action="store_true",
        help="Skip git push (commit and tag locally only)",
    )
    graph_parser = subparsers.add_parser(
        "graph", help="Generate and open the Gaia skill graph"
    )
    graph_parser.add_argument(
        "--format",
        choices=("html", "svg", "json"),
        default="html",
        help="Graph artifact format (default: html)",
    )
    graph_parser.add_argument(
        "-o", "--output", help="Output path (default: registry/render/gaia.html)"
    )
    graph_parser.add_argument(
        "--open",
        dest="open",
        action="store_true",
        default=True,
        help="Open the generated graph (default)",
    )
    graph_parser.add_argument(
        "--no-open",
        dest="open",
        action="store_false",
        help="Do not open the generated graph",
    )
    graph_parser.add_argument(
        "--custom",
        action="store_true",
        help="Only include custom skills in the graph (default)",
    )
    graph_parser.add_argument(
        "--canon",
        action="store_true",
        help="Show canonical registry graph instead of custom skills only",
    )
    graph_parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        dest="show_all",
        help="Include unowned prerequisite nodes in the graph",
    )
    stats_parser = subparsers.add_parser(
        "stats", help="Show registry health at a glance"
    )
    stats_parser.add_argument(
        "--canon",
        action="store_true",
        help="Show canonical registry data instead of local-first view.",
    )
    appraise_parser = subparsers.add_parser(
        "appraise", help="Inspect a skill card with status and actions"
    )
    appraise_parser.add_argument(
        "skillId",
        nargs="?",
        default=None,
        help="Skill ID to appraise (default: most recent)",
    )
    promote_parser = subparsers.add_parser(
        "promote", help="Promote a skill eligible for level-up"
    )
    promote_parser.add_argument(
        "skillId", nargs="?", default=None, help="Skill ID to promote"
    )
    promote_parser.add_argument(
        "--all", action="store_true", help="Promote every candidate from the last scan"
    )
    promote_parser.add_argument(
        "--unique",
        action="store_true",
        help="Promote a basic skill to unique type (4★+ graph-isolated with named impl)",
    )
    promote_parser.add_argument(
        "--name", help="Optional display name for the promoted skill"
    )
    fuse_parser = subparsers.add_parser(
        "fuse", help="Confirm a skill combination or create a custom fusion path"
    )
    fuse_parser.add_argument(
        "skillId", nargs="?", default=None, help="Skill ID to fuse or promote"
    )
    fuse_parser.add_argument("--name", help="Optional display name for the skill")
    fuse_parser.add_argument(
        "--skills", help="Comma-separated list of skills to combine for a custom fusion"
    )
    fuse_parser.add_argument(
        "--delete", action="store_true", help="Delete an existing custom fusion"
    )
    docs_parser = subparsers.add_parser(
        "docs", help="Documentation maintenance commands"
    )
    docs_sub = docs_parser.add_subparsers(dest="docs_command")
    docs_build = docs_sub.add_parser(
        "build", help="Regenerate generated documentation regions"
    )
    docs_build.add_argument(
        "--check", action="store_true", help="Fail if docs are stale without writing"
    )
    lookup_parser = subparsers.add_parser(
        "lookup", help="Look up a canonical skill and its named implementations"
    )
    lookup_parser.add_argument("skillId", help="Skill ID to inspect")

    path_parser = subparsers.add_parser(
        "path",
        help="Show prerequisite unlock-path tree toward a target skill",
    )
    path_parser.add_argument(
        "skillId", help="Canonical skill ID (or /slash-form) to build the path toward"
    )
    path_parser.add_argument(
        "--owned-only",
        action="store_true",
        dest="owned_only",
        help="Prune already-owned branches; show only skills still needed",
    )
    path_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the tree display",
    )

    dev_parser = subparsers.add_parser(
        "dev", help="Registry development and maintenance (requires writable registry)",
        epilog=DEV_USAGE, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    dev_sub = dev_parser.add_subparsers(dest="dev_command")

    dev_list = dev_sub.add_parser(
        "list", help="List skills in the registry with filtering"
    )
    dev_list.add_argument(
        "--generic", action="store_true", help="Include generic (canonical) skills"
    )
    dev_list.add_argument("--named", action="store_true", help="Include named skills")
    dev_list.add_argument(
        "--description", action="store_true", help="Include skill descriptions"
    )
    dev_list.add_argument("--level", action="store_true", help="Include skill level")
    dev_list.add_argument(
        "--evidence", action="store_true", help="Include evidence count (generic only)"
    )
    dev_list.add_argument(
        "--contributor",
        action="store_true",
        help="Include contributor name (named only)",
    )
    dev_list.add_argument("--json", action="store_true", help="Output in JSON format")
    dev_list.add_argument(
        "--extra", action="append", help="Include extra schema fields in output"
    )

    dev_merge = dev_sub.add_parser(
        "merge", help="Merge one or more skills into a target skill"
    )
    dev_merge.add_argument("target", help="Target skill ID to merge into")
    dev_merge.add_argument("sources", nargs="+", help="Source skill IDs to merge from")
    dev_merge.add_argument(
        "--named",
        action="store_true",
        help="Also merge named implementation references",
    )
    dev_merge.add_argument(
        "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
    )

    dev_split = dev_sub.add_parser(
        "split", help="Split a skill into multiple new skills"
    )
    dev_split.add_argument("source", help="Source skill ID to split")
    dev_split.add_argument("targets", nargs="+", help="Target skill IDs to create")
    dev_split.add_argument(
        "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
    )

    dev_rename = dev_sub.add_parser(
        "rename", help="Rename a skill and update all references"
    )
    dev_rename.add_argument("old_id", help="Original skill ID")
    dev_rename.add_argument("new_id", help="New skill ID")

    dev_verify = dev_sub.add_parser(
        "verify", help="Verify or dispute a skill's evidence"
    )
    dev_verify.add_argument("skill_id", help="Skill ID to verify")
    dev_verify.add_argument(
        "--index", type=int, required=True, help="Index of the evidence entry to verify"
    )
    dev_verify.add_argument(
        "--dispute",
        action="store_true",
        help="Mark evidence as disputed instead of verified",
    )
    dev_verify.add_argument(
        "--notes", help="Optional notes about the verification/dispute"
    )
    dev_verify.add_argument("--source", help="URL to the verification discussion or PR")
    dev_verify.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after verification",
    )

    dev_verify_tier = dev_sub.add_parser(
        "verify-tier",
        help="Recompute and persist a skill's verification tier (community/benchmark/security/enterprise)",
    )
    dev_verify_tier.add_argument(
        "skill_id", help="Skill ID (generic ref or contributor/named) to evaluate"
    )

    dev_calibrate = dev_sub.add_parser("calibrate", help="Update the level of a skill")
    dev_calibrate.add_argument("skill_id", help="Skill ID to calibrate")
    dev_calibrate.add_argument("level", help="New level (e.g. 3★)")
    dev_calibrate.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after calibrating",
    )

    dev_add = dev_sub.add_parser("add", help="Add a new skill to the registry")
    dev_add.add_argument("name", help="Human-readable name of the skill")
    dev_add.add_argument(
        "--id", help="Explicit ID for the skill (defaults to slugified name)"
    )
    dev_add.add_argument(
        "--type",
        choices=("basic", "extra", "ultimate", "unique"),
        default="basic",
        help="Skill type (default: basic)",
    )
    dev_add.add_argument("--description", help="Skill description")
    dev_add.add_argument(
        "--named", action="store_true", help="Add as a named skill instead of generic"
    )
    dev_add.add_argument(
        "--contributor", help="Contributor name for named skill (default: gaiabot)"
    )
    dev_add.add_argument(
        "--generic-ref", help="Generic skill reference for named skill"
    )
    dev_add.add_argument(
        "--status",
        help="Initial status (default: named for named skills, provisional for generic)",
    )
    dev_add.add_argument("--title", help="Display title (lore title) for named skills")
    dev_add.add_argument(
        "--level", help="Initial level (default: 2★ for named, 1★ for generic)"
    )
    dev_add.add_argument(
        "--extra-fields", help="JSON string of additional schema fields"
    )
    dev_add.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after adding",
    )

    dev_rm = dev_sub.add_parser("rm", help="Remove a skill from the registry")
    dev_rm.add_argument("skill_id", help="Skill ID to remove")
    dev_rm.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after removing",
    )
    dev_rm.add_argument(
        "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
    )

    dev_link = dev_sub.add_parser("link", help="Link skills by adding prerequisites")
    dev_link.add_argument(
        "target", help="Target skill ID that receives the prerequisites"
    )
    dev_link.add_argument(
        "prereqs", help="Comma-separated list of prerequisite skill IDs"
    )
    dev_link.add_argument(
        "--reset",
        action="store_true",
        help="Overwrite existing prerequisites instead of appending",
    )
    dev_link.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after linking",
    )

    dev_reclassify = dev_sub.add_parser(
        "reclassify", help="Change the type of a generic skill"
    )
    dev_reclassify.add_argument("skill_id", help="Generic skill ID to reclassify")
    dev_reclassify.add_argument(
        "new_type",
        choices=("basic", "extra", "ultimate", "unique"),
        help="New skill type",
    )
    dev_reclassify.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after reclassifying",
    )
    dev_update_named = dev_sub.add_parser(
        "update-named", help="Update frontmatter properties of a named skill"
    )
    dev_update_named.add_argument("skill_id", help="Named skill ID (e.g. author/skill)")
    dev_update_named.add_argument("--status", help="New status (e.g. awakened, named)")
    dev_update_named.add_argument("--generic-ref", help="New generic skill reference")
    dev_update_named.add_argument(
        "--suite-components", help="Comma-separated list of suite components"
    )
    dev_update_named.add_argument(
        "--suite-ref",
        help="Suite capstone ID this skill belongs to (e.g. garrytan/gstack). Sets suiteRef in frontmatter.",
    )
    dev_update_named.add_argument(
        "--installation-file",
        metavar="PATH",
        help="Path to a markdown file whose content replaces the '## Installation' section in the capstone skill.",
    )
    dev_update_named.add_argument(
        "--origin",
        choices=["true", "false"],
        help="Set the origin flag to true or false",
    )
    dev_update_named.add_argument(
        "--github-link",
        help="New GitHub URL link for the named skill (must be a blob link for 3★+)",
    )
    dev_update_named.add_argument(
        "--installable",
        choices=["true", "false"],
        help="Set the installable flag to true or false",
    )
    dev_update_named.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after updating",
    )

    dev_timeline = dev_sub.add_parser(
        "timeline",
        help="Append a standalone event to a skill's or user tree's timeline",
    )
    dev_timeline.add_argument(
        "skill_id",
        help="Skill ID to append the event to (generic, named, or user-tree)",
    )
    dev_timeline.add_argument(
        "--action",
        required=True,
        choices=(
            "propose",
            "rank_up",
            "demote",
            "verified",
            "disputed",
            "type_change",
            "suite_ref_set",
            "note",
        ),
        help="The type of event action",
    )
    dev_timeline.add_argument("--notes", required=True, help="Description of the event")
    dev_timeline.add_argument(
        "--user",
        help="Write to skill-trees/<user>/skill-tree.json instead of the registry node",
    )
    dev_timeline.add_argument(
        "--timestamp",
        help="ISO 8601 timestamp for the event (e.g. 2026-03-01T00:00:00Z); defaults to now. Use for historical backfills.",
    )
    dev_timeline.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after appending event",
    )

    dev_evidence = dev_sub.add_parser("evidence", help="Add evidence to a skill")
    dev_evidence.add_argument("skill_id", help="Skill ID to add evidence to")
    dev_evidence.add_argument("source", help="URL to the evidence source")
    dev_evidence.add_argument(
        "--index",
        type=int,
        metavar="N",
        help=(
            "Re-grade the existing evidence entry at this index in place "
            "(0-based) instead of appending a new one. Sets --type/--trust/"
            "--notes on that entry while preserving its other fields (e.g. "
            "the deprecated class). Used by the class→grade backfill."
        ),
    )
    dev_evidence.add_argument(
        "--type",
        dest="evidence_type",
        metavar="TYPE",
        help="Evidence type (e.g. arxiv, repo, github-stars). Validated against meta.json evidence.types.",
    )
    dev_evidence.add_argument(
        "--trust",
        type=float,
        metavar="NUMBER",
        help="Trust number 0-100. Grade is auto-derived: S≥90, A≥80, B≥60, C≥40; <40=ungraded.",
    )
    dev_evidence.add_argument(
        "--class",
        dest="evidence_class",
        choices=("A", "B", "C"),
        default=None,
        help="[DEPRECATED] Use --trust instead. Evidence class (A/B/C).",
    )
    dev_evidence.add_argument("--evaluator", help="GitHub username of the evaluator")
    dev_evidence.add_argument("--date", help="Date of evaluation (ISO 8601)")
    dev_evidence.add_argument("--notes", help="Optional notes about the evaluation")
    dev_evidence.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after adding evidence",
    )

    dev_rm_evidence = dev_sub.add_parser(
        "rm-evidence",
        help="Remove an evidence entry (by --index or --source) from a skill",
    )
    dev_rm_evidence.add_argument(
        "skill_id",
        help="Skill ID to remove evidence from (bare id = generic; contributor/skill = named)",
    )
    dev_rm_evidence.add_argument(
        "--index", type=int, help="Index of the evidence entry to remove"
    )
    dev_rm_evidence.add_argument(
        "--source",
        help="Remove all evidence entries whose source URL matches this exactly",
    )
    dev_rm_evidence.add_argument(
        "--no-build",
        action="store_true",
        help="Skip rebuilding docs and graph assets after removing evidence",
    )
    dev_rm_evidence.add_argument(
        "--yes", "-y", "--y", action="store_true", help="Skip confirmation prompt"
    )

    dev_build = dev_sub.add_parser(
        "build", help="Regenerate registry and documentation site"
    )

    dev_audit = dev_sub.add_parser("audit", help="Run registry maintenance linter")
    dev_audit.add_argument("--level", type=int, help="Filter audit by level threshold")

    dev_diff = dev_sub.add_parser(
        "diff",
        help="Show substantive registry additions in a branch vs main (strips generated noise)",
    )
    dev_diff.add_argument(
        "ref",
        nargs="?",
        help="Branch or ref to compare (default: current branch). "
        "Short names are auto-prefixed with origin/.",
    )
    dev_diff.add_argument(
        "--base",
        default="origin/main",
        help="Base ref to compare against (default: origin/main)",
    )

    trust_parser = subparsers.add_parser(
        "trust", help="Trust Magnitude diagnostics"
    )
    trust_sub = trust_parser.add_subparsers(dest="trust_command")
    trust_explain_parser = trust_sub.add_parser(
        "explain", help="Show per-row multiplier chain for a skill's Trust Magnitude"
    )
    trust_explain_parser.add_argument(
        "skillId", help="Canonical skill ID to explain"
    )

    validate_parser = subparsers.add_parser(
        "validate", help="Validate the Gaia registry"
    )
    validate_parser.add_argument(
        "--intake",
        action="store_true",
        help="Validate intake batches instead of canonical graph",
    )
    validate_parser.add_argument(
        "--meta-sync",
        action="store_true",
        help="Verify meta.json is in sync with gaia.json",
    )

    test_parser = subparsers.add_parser("test", help="Run self-verification tests")
    test_parser.add_argument("suite", choices=("meta", "all"), help="Test suite to run")

    skills_parser = subparsers.add_parser(
        "skills",
        help="Browse and manage named skills",
        epilog=SKILLS_USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    skills_sub = skills_parser.add_subparsers(dest="skills_command")
    skills_list = skills_sub.add_parser("list", help="List available named skills")
    skills_list.add_argument(
        "--exclude-pending", action="store_true", help="Hide pending skill proposals"
    )
    skills_search = skills_sub.add_parser("search", help="Search named skills")
    skills_search.add_argument("query", help="Search query")
    skills_search.add_argument(
        "--exclude-pending", action="store_true", help="Hide pending skill proposals"
    )
    skills_info = skills_sub.add_parser("info", help="Show details for a named skill")
    skills_info.add_argument("skill_id", help="Skill ID to inspect")
    skills_info.add_argument(
        "--exclude-pending", action="store_true", help="Hide pending skill proposals"
    )
    skills_install = skills_sub.add_parser("install", help="Install a named skill")
    skills_install.add_argument(
        "skill_id",
        metavar="skill",
        help="Skill ID, catalogRef, or unique bare slug to install",
    )
    skills_install.add_argument(
        "--suite", action="store_true", help="Install as a suite (recursive)"
    )
    skills_install.add_argument(
        "--install-location",
        dest="install_location",
        choices=["local", "global"],
        default="local",
        help="Where to install: local (.agents/.claude, default) or global (~/.gaia/skills)",
    )
    skills_update = skills_sub.add_parser(
        "update", help="Update all installed skills from source"
    )
    skills_uninstall = skills_sub.add_parser(
        "uninstall", help="Uninstall a named skill"
    )
    skills_uninstall.add_argument("skill_id", help="Skill ID to uninstall")
    hook_parser = subparsers.add_parser("_hook", help=argparse.SUPPRESS)
    subparsers._choices_actions = [
        action for action in subparsers._choices_actions if action.dest != "_hook"
    ]
    hook_parser.add_argument("--event", default="file_edit", help=argparse.SUPPRESS)
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
        cmd.extend(
            [
                str(repo_root / "tests" / "test_meta_ops.py"),
                str(repo_root / "tests" / "test_authz.py"),
            ]
        )
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
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    # Ensure UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError for box-drawing)
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser, skills_parser = get_parser()
    args = parser.parse_args()

    # --tui flag now redirects to `gaia skills` (TUI lives there)
    if args.tui:
        os.execvp(sys.argv[0], [sys.argv[0], "skills"])

    # No args + interactive terminal → command selector
    if len(sys.argv) == 1 and sys.stdin.isatty() and sys.stdout.isatty():
        from gaia_cli.selector import run_selector
        run_selector(parser)
        return

    args.registry = resolve_registry_path(args.registry, global_flag=args.global_flag)
    require_explicit_writable_registry(parser, args)
    if args.version:
        version_command(args)
        return
    if args.command == "init":
        init_command(args)
    elif args.command == "help":
        parser.print_help()
    elif args.command == "scan":
        scan_command(args)
    elif args.command == "fetch":
        fetch_command(args)
    elif args.command == "pull":
        pull_command(args)
    elif args.command == "update":
        update_command(args)
    elif args.command == "install":
        install_command(args)
    elif args.command == "uninstall":
        uninstall_command(args)
    elif args.command == "share":
        share_command(args)
    elif args.command == "tree":
        tree_command(args)
    elif args.command == "push":
        push_command(args)
    elif args.command == "propose":
        propose_command(args)
    elif args.command == "version":
        version_command(args)
    elif args.command == "whoami":
        whoami_command(args)
    elif args.command == "login":
        login_command(args)
    elif args.command == "logout":
        logout_command(args)
    elif args.command == "reset":
        reset_command(args)
    elif args.command == "mcp":
        mcp_command(args)
    elif args.command == "release":
        release_command(args)
    elif args.command == "graph":
        graph_command(args)
    elif args.command == "stats":
        stats_command(args)
    elif args.command == "appraise":
        appraise_command(args)
    elif args.command == "promote":
        promote_command(args)
    elif args.command == "fuse":
        try:
            fuse_command(args)
        except FuseCancelled:
            pass
    elif args.command == "docs" and getattr(args, "docs_command", None) == "build":
        docs_command(args)
    elif args.command == "lookup":
        lookup_command(args)
    elif args.command == "dev":
        dev_cmd = getattr(args, "dev_command", None)
        if dev_cmd in MUTATING_DEV_COMMANDS:
            from gaia_cli.authz import require_operator

            require_operator(f"dev {dev_cmd}", args.registry)
        if dev_cmd == "list":
            meta_list_command(args)
        elif dev_cmd == "merge":
            meta_merge_command(args)
        elif dev_cmd == "split":
            meta_split_command(args)
        elif dev_cmd == "rename":
            meta_rename_command(args)
        elif dev_cmd == "verify":
            meta_verify_command(args)
        elif dev_cmd == "verify-tier":
            meta_verify_tier_command(args)
        elif dev_cmd == "calibrate":
            meta_calibrate_command(args)
        elif dev_cmd == "add":
            meta_add_command(args)
        elif dev_cmd == "rm":
            meta_remove_command(args)
        elif dev_cmd == "link":
            meta_link_command(args)
        elif dev_cmd == "reclassify":
            meta_reclassify_command(args)
        elif dev_cmd == "update-named":
            meta_update_named_command(args)
        elif dev_cmd == "timeline":
            meta_timeline_command(args)
        elif dev_cmd == "evidence":
            meta_evidence_command(args)
        elif dev_cmd == "rm-evidence":
            meta_rm_evidence_command(args)
        elif dev_cmd == "build":
            meta_build_command(args)
        elif dev_cmd == "audit":
            meta_audit_command(args)
        elif dev_cmd == "diff":
            meta_diff_command(args)
        else:
            _, subparsers = get_parser()
            subparsers.choices["dev"].print_help()
    elif args.command == "path":
        path_command(args)
    elif args.command == "trust":
        if getattr(args, "trust_command", None) == "explain":
            trust_explain_command(args)
        else:
            _, subparsers = get_parser()
            subparsers.choices["trust"].print_help()
    elif args.command == "validate":
        validate_command(args)
    elif args.command == "test":
        test_command(args)
    elif args.command == "skills":
        if not getattr(args, "skills_command", None):
            try:
                from gaia_cli.tui import GaiaApp
                GaiaApp().run()
            except ImportError:
                skills_parser.print_help()
            return
        skills_command(args)
    elif args.command == "_hook":
        hook_command(args)
    else:
        parser.print_help()


def trust_explain_command(args):
    """Implement `gaia trust explain <skillId>`."""
    from gaia_cli.trustMagnitude import explainTrustMagnitude
    from gaia_cli.registry import load_registry

    skillId = args.skillId
    registry = load_registry()
    skills = registry.get("skills") or registry.get("nodes") or []

    # Build maps
    genericSkillMap = {s["id"]: s for s in skills if s.get("id") and not s.get("genericSkillRef")}
    namedSkillMap = {s["id"]: s for s in skills if s.get("id") and s.get("genericSkillRef")}

    # Try named first, then generic
    skill = namedSkillMap.get(skillId) or genericSkillMap.get(skillId)
    if skill is None:
        print(f"Skill '{skillId}' not found in registry.")
        return 1

    output = explainTrustMagnitude(skill, genericSkillMap=genericSkillMap, namedSkillMap=namedSkillMap)
    print(output)
    return 0


if __name__ == "__main__":
    main()
