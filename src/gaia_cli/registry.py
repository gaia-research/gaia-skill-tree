"""Registry path resolution for the Gaia CLI."""

import json
import os
from importlib import resources
from pathlib import Path


WRITE_COMMANDS = {"push", "propose", "name", "fuse", "embed", "sync", "promote", "release", "docs", "merge", "split", "add", "evidence"}


def _gaia_home_dir() -> Path:
    """Return the gaia data home: $GAIA_HOME if set, else ~/.gaia."""
    gaia_home = os.environ.get("GAIA_HOME")
    if gaia_home:
        return Path(gaia_home)
    return Path.home() / ".gaia"


def _global_config_path() -> Path:
    """Return the global gaia config path, honouring GAIA_HOME if set."""
    return _gaia_home_dir() / "config.json"


def bundled_registry_path():
    """Return the bundled read-only registry data path."""
    return resources.files("gaia_cli").joinpath("data")


def registry_dir(registry_path) -> str:
    return os.path.join(str(registry_path), "registry")


def registry_graph_path(registry_path):
    return os.path.join(registry_dir(registry_path), "gaia.json")


def registry_nodes_dir(registry_path) -> str:
    return os.path.join(registry_dir(registry_path), "nodes")


def registry_schema_dir(registry_path) -> str:
    return os.path.join(registry_dir(registry_path), "schema")


def named_skills_dir(registry_path) -> str:
    return os.path.join(registry_dir(registry_path), "named")


def named_skills_index_path(registry_path) -> str:
    return os.path.join(registry_dir(registry_path), "named-skills.json")


def registry_for_review_dir(registry_path) -> str:
    return os.path.join(str(registry_path), "registry-for-review")


def skill_batches_dir(registry_path) -> str:
    return os.path.join(registry_for_review_dir(registry_path), "skill-batches")


def skill_trees_dir(registry_path) -> str:
    return os.path.join(str(registry_path), "skill-trees")


def user_tree_path(registry_path, username: str) -> str:
    return os.path.join(skill_trees_dir(registry_path), username, "skill-tree.json")


def generated_output_dir(registry_path) -> str:
    return os.path.join(str(registry_path), "generated-output")


def promotion_candidates_path(registry_path) -> str:
    return os.path.join(generated_output_dir(registry_path), "promotion-candidates.json")


def embeddings_path(registry_path) -> str:
    return os.path.join(registry_dir(registry_path), "embeddings.json")


def real_skill_catalog_path(registry_path) -> str:
    return os.path.join(registry_dir(registry_path), "real-skills.json")


def read_global_registry():
    """Return the globally-registered registry path, or None if not set."""
    try:
        with open(_global_config_path(), encoding="utf-8") as f:
            data = json.load(f)
        path = data.get("defaultRegistry")
        if path and Path(path).is_dir():
            return path
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    return None


def read_local_registry() -> str | None:
    """Return registry path from .gaia config in CWD, or None if not found."""
    local_cfg = Path(".gaia") / "config.toml"
    legacy_cfg = Path(".gaia") / "config.json"
    cfg_path = local_cfg if local_cfg.exists() else legacy_cfg
    if not cfg_path.exists():
        return None
    try:
        raw = cfg_path.read_text(encoding="utf-8")
        if cfg_path.suffix == ".toml":
            data = {}
            for line in raw.splitlines():
                if "=" not in line or line.strip().startswith("#"):
                    continue
                key, _, value = line.partition("=")
                data[key.strip()] = value.strip().strip('"')
        else:
            data = json.loads(raw)
        registry_path = data.get("localRegistryPath") or os.path.abspath(".")
        p = Path(registry_path)
        if p.is_dir() and (p / "registry" / "gaia.json").exists():
            return str(p)
    except (OSError, json.JSONDecodeError):
        pass
    return None


def write_global_registry(path: str) -> None:
    """Persist the registry path to the global ~/.gaia/config.json."""
    cfg = _global_config_path()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if cfg.exists():
        try:
            with open(cfg, encoding="utf-8") as f:
                existing = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    existing["defaultRegistry"] = str(Path(path).resolve())
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def read_cwd_registry() -> str | None:
    """Return CWD when it looks like a Gaia registry checkout."""
    cwd = Path.cwd()
    if (cwd / "registry" / "gaia.json").exists():
        return str(cwd)
    return None


def resolve_registry_path(explicit_registry=None, global_flag=False):
    """Resolve the registry path: explicit → --global → local .gaia → CWD clone → global config → bundled."""
    if explicit_registry:
        return os.path.abspath(os.path.expanduser(explicit_registry))
    if global_flag:
        global_reg = read_global_registry()
        return global_reg if global_reg else str(bundled_registry_path())
    local_reg = read_local_registry()
    if local_reg:
        return local_reg
    cwd_reg = read_cwd_registry()
    if cwd_reg:
        return cwd_reg
    global_reg = read_global_registry()
    if global_reg:
        return global_reg
    return str(bundled_registry_path())


def require_explicit_writable_registry(parser, args):
    """Reject mutating commands unless the registry resolves to a writable checkout."""
    command = getattr(args, "command", None)
    if command not in WRITE_COMMANDS:
        return
    registry_path = Path(args.registry)
    bundled = Path(str(bundled_registry_path()))
    if registry_path != bundled and registry_path.is_dir() and os.access(registry_path, os.W_OK):
        return
    if registry_path == bundled:
        parser.error(
            f"`gaia {args.command}` needs a writable registry. Either:\n"
            "  • Run `gaia init` from your gaia-skill-tree clone (sets localRegistryPath automatically), or\n"
            "  • Pass --registry PATH explicitly."
        )
    parser.error(
        f"`gaia {args.command}` requires --registry PATH to point at a writable registry directory."
    )
