import sys
import os
import json
import datetime
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from gaia_cli.registry import (
    registry_graph_path,
    named_skills_index_path,
    registry_nodes_dir,
    named_skills_dir,
)
from gaia_cli.scanner import load_config


_GENERATED_PREFIXES = (
    "docs/",
    "skill-trees/",
    "registry/gaia.gexf",
    "registry/gaia.svg",
    "registry/named-skills.json",
    "registry/combinations.md",
    "registry/registry.md",
    "registry/skill-sources.md",
)
_GENERATED_SUFFIXES = (
    ".gexf",
    ".svg",
    ".html",
)
_GENERATED_EXACT = {
    "uv.lock",
    "docs/css/tokens.css",
    "docs/tree.md",
}
_VERSION_FILES = {
    "pyproject.toml",
    "packages/cli-npm/package.json",
    "packages/mcp/package.json",
    "registry/gaia.json",
    "docs/graph/gaia.json",
}


@dataclass(frozen=True)
class DevPreflightError(Exception):
    """A mutating `gaia dev` command would violate an invariant before writing."""

    message: str
    fix: str | None = None


def _format_dev_preflight_error(error: DevPreflightError) -> str:
    lines = [f"Error: {error.message}"]
    if error.fix:
        lines.append(f"Fix: {error.fix}")
    return "\n".join(lines)


def _fail_dev_preflight(message: str, *, fix: str | None = None) -> None:
    raise DevPreflightError(message=message, fix=fix)


def _run_dev_preflights(checks: Iterable[Callable[[], None]]) -> None:
    """Run invariant checks and abort before any write if one fails."""
    try:
        for check in checks:
            check()
    except DevPreflightError as error:
        print(_format_dev_preflight_error(error), file=sys.stderr)
        sys.exit(1)


def _preflight_named_status_identity(skill_id: str, meta: dict, args) -> None:
    new_status = getattr(args, "status", None)
    if new_status != "named":
        return
    if (
        meta.get("title")
        or meta.get("catalogRef")
        or getattr(args, "title", None)
        or getattr(args, "catalog_ref", None)
    ):
        return
    _fail_dev_preflight(
        f"status='named' requires 'title' or 'catalogRef' on {skill_id}.",
        fix=(
            f"Re-run `gaia dev update-named {skill_id} --status named "
            f"--title \"<lore title>\"` (or `--catalog-ref <slug>`) to satisfy "
            f"the schema constraint."
        ),
    )


def _preflight_starbar_blob_link(skill_id: str, skill_data: dict, level: str) -> None:
    three_star_plus = {"3★", "4★", "5★", "6★"}
    if level not in three_star_plus:
        return
    github_url = (skill_data.get("links") or {}).get("github", "")
    if github_url and "/blob/" in github_url:
        return
    _fail_dev_preflight(
        f"Cannot calibrate {skill_id} to {level}: `links.github` is missing or not a `blob/` URL.",
        fix=(
            "The Star Bar (META.md §2.4) requires a verified GitHub blob URL for 3★+ skills. "
            f"Current value: {github_url!r}. Re-run `gaia dev update-named {skill_id} "
            "--github-link https://github.com/<owner>/<repo>/blob/<branch>/<path-to-skill>`."
        ),
    )


def _preflight_evidence_static(args, valid_types: set[str] | list[str] | tuple[str, ...]) -> None:
    evidence_type = getattr(args, "evidence_type", None)
    if evidence_type is not None and evidence_type not in valid_types:
        valid_list = ", ".join(valid_types)
        _fail_dev_preflight(
            f"unknown evidence type '{evidence_type}'.",
            fix=f"Use one of: {valid_list}",
        )

    percentile = getattr(args, "percentile", None)
    if evidence_type == "benchmark-result":
        if percentile is None:
            _fail_dev_preflight(
                "`--type benchmark-result` requires `--percentile <0-100>`.",
                fix=(
                    "Pass `--percentile <int>` (0-100 inclusive). If the percentile is unknown, "
                    "use `--type peer-review` with `--reviewers` instead for a gradeable entry."
                ),
            )
        if not (0 <= int(percentile) <= 100):
            _fail_dev_preflight(f"`--percentile` must be in range 0-100; got {percentile!r}.")

    for attr, flag in (("date", "--date"), ("source_started_at", "--source-started-at")):
        value = getattr(args, attr, None)
        if value is None:
            continue
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            _fail_dev_preflight(f"{flag} must be ISO YYYY-MM-DD; got '{value}'.")

    index = getattr(args, "index", None)
    patch_fields = (
        "trust",
        "evidence_type",
        "notes",
        "evaluator",
        "date",
        "stars",
        "views",
        "citations",
        "reviewers",
        "commits",
        "contributors",
        "skill_count_in_repo",
        "percentile",
        "source_started_at",
    )
    if index is not None and not any(getattr(args, field, None) is not None for field in patch_fields):
        _fail_dev_preflight(
            "--index requires at least one update field.",
            fix="Pass one of --trust, --type, --notes, --date, --source-started-at, or a numeric payload flag.",
        )


def _preflight_evidence_index_bounds(skill_id: str, ev_list: list, index: int | None) -> None:
    if index is None:
        return
    if index < 0 or index >= len(ev_list):
        _fail_dev_preflight(
            f"Evidence index {index} out of range for skill '{skill_id}' ({len(ev_list)} entries).",
            fix="Use a valid zero-based --index value or omit --index to append new evidence.",
        )


def _run_docs_build(registry_path) -> None:
    import gaia_cli.commands.dev as dev
    patched = getattr(dev, "_run_docs_build", None)
    if patched and patched is not _run_docs_build:
        patched(registry_path)
        return

    cmd = [sys.executable, "-m", "gaia_cli"]
    if registry_path:
        cmd += ["--registry", str(registry_path)]
    cmd += ["docs", "build"]
    subprocess.run(cmd, check=True)



def _get_contributor():
    config = load_config() or {}
    return config.get("gaiaUser") or config.get("username") or "unknown"


def _is_verifier(username, registry_path=".") -> bool:
    """Check if the user holds at least one 4★ skill implementation."""
    index_path = named_skills_index_path(registry_path)
    if not os.path.exists(index_path):
        return False
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        for entries in index.get("buckets", {}).values():
            for e in entries:
                if e.get("contributor") == username:
                    level = e.get("level", "2★")
                    if level and level[0].isdigit() and int(level[0]) >= 4:
                        return True
    except Exception:
        pass
    return False


def _confirm_destructive(message: str, args) -> None:
    """Prompt for confirmation before a destructive operation.

    Skipped when ``args.yes`` is True.  In non-interactive contexts (CI, piped
    stdin) ``confirm()`` returns the default value (False), so automation MUST
    pass ``--yes`` explicitly to avoid an implicit abort.
    """
    if getattr(args, "yes", False):
        return
    from gaia_cli.interactive import confirm
    if not confirm(message, default=False):
        print("Aborted.")
        sys.exit(0)


def _parse_md(path):
    import yaml
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content
    _, frontmatter, body = content.split("---", 2)
    return (yaml.safe_load(frontmatter) or {}), body


def _write_md(path, meta, body) -> None:
    import yaml
    path.write_text(
        "---\n" + yaml.dump(meta, sort_keys=False, allow_unicode=True) + "---" + body,
        encoding="utf-8",
    )


def _find_named_file(named_dir, skill_id):
    for p in named_dir.glob("**/*.md"):
        meta, _ = _parse_md(p)
        if meta.get("id") == skill_id:
            return p
    return None


def _replace_section(body: str, section_heading: str, new_content: str) -> str:
    """Replace (or append) a top-level markdown section in the body text.

    Matches ``## {section_heading}`` through the next ``##``-level heading
    or end-of-string, then substitutes new_content.  If the section is not
    found it is appended.
    """
    import re

    pattern = rf"(##\s+{re.escape(section_heading)}\s*\n)(.*?)(?=\n##\s|\Z)"
    replacement = rf"\g<1>{new_content}\n"
    result, n = re.subn(pattern, replacement, body, flags=re.DOTALL)
    if n == 0:
        result = body.rstrip("\n") + f"\n\n## {section_heading}\n\n{new_content}\n"
    return result


def _update_named_skill_ref(md_path: Path, old_ref: str, new_ref: str):
    """Update genericSkillRef in a named skill markdown file."""
    meta, body = _parse_md(md_path)
    if meta.get("genericSkillRef") == old_ref:
        meta["genericSkillRef"] = new_ref
        _write_md(md_path, meta, body)
        return True
    return False


def _is_generated(path):
    if path in _GENERATED_EXACT:
        return True
    for prefix in _GENERATED_PREFIXES:
        if path.startswith(prefix):
            return True
    for suffix in _GENERATED_SUFFIXES:
        if path.endswith(suffix):
            return True
    return False


def _parse_named_frontmatter(content):
    """Extract key/value pairs from YAML frontmatter in a named skill file."""
    if not content.startswith("---"):
        return {}
    lines = content.split("\n")
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}
    meta = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip("'\"")
    return meta


def genericSkillExists(registryPath: str, skillId: str) -> bool:
    """Check if a generic skill with the given ID exists."""
    from gaia_cli.registry import registry_nodes_dir
    nodesDir = Path(registry_nodes_dir(registryPath))
    for p in nodesDir.glob("**/*.json"):
        if p.stem == skillId:
            return True
    return False


def loadGenericNodes(registryPath: str) -> list[tuple[Path, dict]]:
    """Load all parseable generic registry nodes once for dev preflights."""
    nodesDir = Path(registry_nodes_dir(registryPath))
    nodes = []
    for p in nodesDir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        nodes.append((p, data))
    return nodes


def indexGenericNodes(nodes: list[tuple[Path, dict]]) -> dict[str, list[tuple[Path, dict]]]:
    """Return node rows grouped by id so callers can detect collisions."""
    byId: dict[str, list[tuple[Path, dict]]] = {}
    for path, data in nodes:
        nodeId = data.get("id")
        if nodeId:
            byId.setdefault(nodeId, []).append((path, data))
    return byId


def _require_single_generic(byId: dict[str, list[tuple[Path, dict]]], skillId: str, label: str) -> tuple[Path, dict]:
    matches = byId.get(skillId, [])
    if not matches:
        _fail_dev_preflight(f"{label} skill '{skillId}' does not exist.")
    if len(matches) > 1:
        locations = ", ".join(str(path) for path, _ in matches)
        _fail_dev_preflight(
            f"{label} skill '{skillId}' is duplicated in registry nodes.",
            fix=f"Resolve the ID collision before mutating it. Matches: {locations}",
        )
    return matches[0]


def _reject_duplicate_values(values: list[str], label: str) -> None:
    seen = set()
    duplicates = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    if duplicates:
        _fail_dev_preflight(
            f"Duplicate {label} IDs are not allowed: {', '.join(duplicates)}.",
            fix=f"Remove duplicate IDs from the {label} list.",
        )


def _valid_generic_id(skillId: str) -> bool:
    import re
    return bool(re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", skillId))


def preflightMergeCommand(args) -> None:
    registryPath = args.registry
    targetId = args.target.lstrip("/")
    sources = [source.lstrip("/") for source in args.sources]
    if not sources:
        _fail_dev_preflight("Merge requires at least one source skill.")
    _reject_duplicate_values(sources, "source")
    if targetId in sources:
        _fail_dev_preflight(
            f"Target skill '{targetId}' cannot also be a source skill.",
            fix="Remove the target from the source list or choose a different target.",
        )

    if "/" in targetId:
        namedDir = Path(named_skills_dir(registryPath))
        if not _find_named_file(namedDir, targetId):
            _fail_dev_preflight(f"Target named skill '{targetId}' does not exist.")
        for sourceId in sources:
            if "/" not in sourceId:
                _fail_dev_preflight(
                    f"Cannot merge generic source '{sourceId}' into named target '{targetId}'.",
                    fix="Use all named IDs or all generic IDs in one merge.",
                )
            if not _find_named_file(namedDir, sourceId):
                _fail_dev_preflight(f"Source named skill '{sourceId}' does not exist.")
        return

    for sourceId in sources:
        if "/" in sourceId:
            _fail_dev_preflight(
                f"Cannot merge named source '{sourceId}' into generic target '{targetId}'.",
                fix="Use all named IDs or all generic IDs in one merge.",
            )
    nodes = loadGenericNodes(registryPath)
    byId = indexGenericNodes(nodes)
    _require_single_generic(byId, targetId, "Target")
    for sourceId in sources:
        _require_single_generic(byId, sourceId, "Source")


def preflightSplitCommand(args) -> None:
    registryPath = args.registry
    sourceId = args.source.lstrip("/")
    targets = [target.lstrip("/") for target in args.targets]
    if not targets:
        _fail_dev_preflight("Split requires at least one target skill ID.")
    _reject_duplicate_values(targets, "split target")
    if sourceId in targets:
        _fail_dev_preflight(
            f"Split source '{sourceId}' cannot also be a target.",
            fix="Choose new target IDs that do not match the source.",
        )
    for targetId in targets:
        if not _valid_generic_id(targetId):
            _fail_dev_preflight(
                f"Split target ID '{targetId}' is invalid.",
                fix="Use a valid lowercase, hyphenated generic skill slug.",
            )

    nodes = loadGenericNodes(registryPath)
    byId = indexGenericNodes(nodes)
    sourcePath, _ = _require_single_generic(byId, sourceId, "Source")
    for targetId in targets:
        if targetId in byId:
            _fail_dev_preflight(f"Split target '{targetId}' already exists in registry.")
        targetPath = sourcePath.parent / f"{targetId}.json"
        if targetPath.exists():
            _fail_dev_preflight(
                f"Split target '{targetId}' already exists on disk at {targetPath}.",
                fix="Choose a new target ID or remove the stale file first.",
            )


def preflightRenameCommand(args) -> None:
    registryPath = args.registry
    oldId = args.old_id.lstrip("/")
    newId = args.new_id.lstrip("/")
    if oldId == newId:
        _fail_dev_preflight(
            f"Cannot rename skill '{oldId}' to itself.",
            fix="Choose a distinct new ID.",
        )
    if not _valid_generic_id(newId):
        _fail_dev_preflight(
            f"New skill ID '{newId}' is invalid.",
            fix="Use a valid lowercase, hyphenated generic skill slug.",
        )
    nodes = loadGenericNodes(registryPath)
    byId = indexGenericNodes(nodes)
    oldPath, _ = _require_single_generic(byId, oldId, "Source")
    if newId in byId:
        _fail_dev_preflight(f"Skill with id '{newId}' already exists in registry.")
    newPath = oldPath.parent / f"{newId}.json"
    if newPath.exists():
        _fail_dev_preflight(
            f"'{newId}' already exists on disk at {newPath}.",
            fix="Choose a new ID or remove the stale file before renaming.",
        )


def preflightRemoveCommand(args) -> None:
    registryPath = args.registry
    skillId = args.skill_id.lstrip("/")
    nodes = loadGenericNodes(registryPath)
    byId = indexGenericNodes(nodes)
    _require_single_generic(byId, skillId, "Generic")

    namedDir = Path(named_skills_dir(registryPath))
    genericRefUsers = []
    suiteRefUsers = []
    for p in namedDir.glob("**/*.md"):
        meta, _ = _parse_md(p)
        namedId = meta.get("id") or str(p)
        if meta.get("genericSkillRef") == skillId:
            genericRefUsers.append(namedId)
        if meta.get("suiteRef") == skillId:
            suiteRefUsers.append(namedId)
    if genericRefUsers:
        _fail_dev_preflight(
            f"Cannot remove generic skill '{skillId}' while named skills reference it as genericSkillRef: {', '.join(genericRefUsers)}.",
            fix="Repoint those named skills with `gaia dev update-named --generic-ref` before removing the generic skill.",
        )
    if suiteRefUsers:
        _fail_dev_preflight(
            f"Cannot remove skill '{skillId}' while named skills reference it as suiteRef: {', '.join(suiteRefUsers)}.",
            fix="Clear or repoint those suiteRef values before removing the skill.",
        )


def preflightReclassifyCommand(args) -> None:
    registryPath = args.registry
    skillId = args.skill_id.lstrip("/")
    newType = args.new_type
    validTypes = {"basic", "extra", "ultimate", "unique"}
    if newType not in validTypes:
        _fail_dev_preflight(
            f"Type '{newType}' is invalid.",
            fix=f"Type must be one of: {', '.join(sorted(validTypes))}",
        )
    nodes = loadGenericNodes(registryPath)
    byId = indexGenericNodes(nodes)
    nodePath, data = _require_single_generic(byId, skillId, "Skill")
    oldType = data.get("type", "basic")
    if oldType == newType:
        return
    nodesDir = Path(registry_nodes_dir(registryPath))
    newPath = nodesDir / newType / f"{skillId}.json"
    if newPath.exists() and newPath != nodePath:
        _fail_dev_preflight(
            f"Cannot reclassify '{skillId}' to {newType}: destination file already exists at {newPath}.",
            fix="Resolve the destination collision before reclassifying.",
        )


def namedSkillExists(registryPath: str, contributor: str, skillId: str) -> bool:
    """Check if a named skill with the given ID exists."""
    from gaia_cli.registry import named_skills_dir
    namedDir = Path(named_skills_dir(registryPath))
    destFile = namedDir / contributor / f"{skillId}.md"
    return destFile.exists()


def parseCommaSeparatedIds(rawValue: str | None, label: str) -> list[str]:
    """Parse a comma-separated ID list and reject empty entries."""
    if rawValue is None or rawValue == "":
        return []
    entries = [entry.strip() for entry in rawValue.split(",")]
    emptyPositions = [str(index + 1) for index, entry in enumerate(entries) if not entry]
    if emptyPositions:
        _fail_dev_preflight(
            f"Empty {label} entries are not allowed at position(s): {', '.join(emptyPositions)}.",
            fix=f"Remove extra commas from the {label} list."
        )
    return entries


def preflightSuiteComponents(registryPath: str, suiteComponentsStr: str | None) -> None:
    """Validate suite components exist and have no duplicates."""
    components = parseCommaSeparatedIds(suiteComponentsStr, "suite component")
    if not components:
        return
    seen = set()
    duplicates = []
    for comp in components:
        if comp in seen:
            duplicates.append(comp)
        else:
            seen.add(comp)
    if duplicates:
        duplicateList = ", ".join(duplicates)
        _fail_dev_preflight(
            f"Duplicate suite components are not allowed: {duplicateList}.",
            fix="Remove the duplicates from the --suite-components list."
        )
    from gaia_cli.registry import named_skills_dir
    namedDir = Path(named_skills_dir(registryPath))
    for comp in components:
        if not _find_named_file(namedDir, comp):
            _fail_dev_preflight(
                f"Suite component '{comp}' does not exist in the registry.",
                fix=f"Ensure the named skill '{comp}' is added to the registry before referencing it as a suite component."
            )


def preflightGithubLink(githubLink: str | None) -> None:
    """Validate GitHub link uses the blob/<branch>/<subpath> format."""
    import re
    if not githubLink:
        return
    if not githubLink.startswith("https://github.com/"):
        _fail_dev_preflight(
            f"GitHub link must start with 'https://github.com/'; got {githubLink!r}.",
            fix="Use https://github.com/<owner>/<repo>/blob/<branch>/<subpath>."
        )
    if "/tree/" in githubLink:
        _fail_dev_preflight(
            f"GitHub URL uses '/tree/' which is not supported: {githubLink!r}.",
            fix="Convert the '/tree/' segment to '/blob/' and specify the path to the skill file/directory."
        )
    if "/blob/" not in githubLink:
        _fail_dev_preflight(
            f"GitHub URL is missing the '/blob/' segment: {githubLink!r}.",
            fix="Ensure the URL uses the 'blob/<branch>/<subpath>' format rather than a bare repository URL."
        )
    match = re.match(r"^https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$", githubLink)
    if not match:
        _fail_dev_preflight(
            f"GitHub URL must match 'https://github.com/<owner>/<repo>/blob/<branch>/<subpath>'; got {githubLink!r}.",
            fix="Provide a complete URL including the owner, repo, branch, and subpath."
        )


def preflightAddCommand(args) -> None:
    """Validate arguments for the add command."""
    import re
    import json
    registryPath = args.registry
    skillName = args.name
    isNamed = getattr(args, "named", False)
    skillId = args.id or skillName.lower().replace(" ", "-")
    descriptionText = (getattr(args, "description", None) or "").strip()
    if len(descriptionText) < 10:
        _fail_dev_preflight(
            f"Skill description must be at least 10 characters; got {len(descriptionText)}.",
            fix="Provide a longer, more descriptive --description."
        )
    if isNamed:
        contributorVal = getattr(args, "contributor", "gaiabot")
        if contributorVal is None:
            contributorVal = "gaiabot"
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", contributorVal):
            _fail_dev_preflight(
                f"Contributor username '{contributorVal}' is invalid.",
                fix="Use only alphanumeric characters, underscores, or hyphens."
            )
        fullId = f"{contributorVal}/{skillId}"
        if not re.match(r"^[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*$", fullId):
            _fail_dev_preflight(
                f"Named skill ID '{fullId}' is invalid.",
                fix="Ensure both the contributor username and skill ID are valid lowercase slug patterns."
            )
        if namedSkillExists(registryPath, contributorVal, skillId):
            _fail_dev_preflight(
                f"Named skill '{fullId}' already exists.",
                fix="Use a different ID or update the existing skill using `gaia dev update-named`."
            )
        levelVal = getattr(args, "level", "2★")
        if levelVal is None:
            levelVal = "2★"
        validLevels = {"1★", "2★", "3★", "4★", "5★", "6★"}
        if levelVal not in validLevels:
            _fail_dev_preflight(
                f"Level '{levelVal}' is invalid.",
                fix=f"Level must be one of: {', '.join(sorted(validLevels))}"
            )
        statusVal = getattr(args, "status", "named")
        if statusVal is None:
            statusVal = "named"
        validStatuses = {"awakened", "named"}
        if statusVal not in validStatuses:
            _fail_dev_preflight(
                f"Status '{statusVal}' is invalid for named skill.",
                fix="Status must be 'awakened' or 'named'."
            )
        titleVal = getattr(args, "title", None)
        catalogRefVal = None
        extraFieldsStr = getattr(args, "extra_fields", None)
        if extraFieldsStr:
            try:
                extra = json.loads(extraFieldsStr)
                if isinstance(extra, dict):
                    catalogRefVal = extra.get("catalogRef")
            except json.JSONDecodeError:
                pass
        if statusVal == "named" and not titleVal and not catalogRefVal:
            _fail_dev_preflight(
                f"status='named' requires 'title' or 'catalogRef' on {fullId}.",
                fix="Pass --title '<lore title>' or include catalogRef in --extra-fields."
            )
        genericRef = getattr(args, "generic_ref", "unknown")
        if genericRef is None:
            genericRef = "unknown"
        if genericRef != "unknown":
            if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", genericRef):
                _fail_dev_preflight(
                    f"Generic skill reference '{genericRef}' has an invalid ID pattern.",
                    fix="Use a valid lowercase, hyphenated slug pattern."
                )
            if not genericSkillExists(registryPath, genericRef):
                _fail_dev_preflight(
                    f"Referenced generic skill '{genericRef}' does not exist.",
                    fix="Ensure the generic skill exists before referencing it as genericSkillRef."
                )
    else:
        if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", skillId):
            _fail_dev_preflight(
                f"Generic skill ID '{skillId}' is invalid.",
                fix="Use a valid lowercase, hyphenated slug pattern matching '^[a-z][a-z0-9]*(-[a-z0-9]+)*$'."
            )
        if genericSkillExists(registryPath, skillId):
            _fail_dev_preflight(
                f"Generic skill '{skillId}' already exists.",
                fix="Use a different ID or edit the existing skill file directly."
            )
        typeVal = getattr(args, "type", "basic")
        if typeVal is None:
            typeVal = "basic"
        validTypes = {"basic", "extra", "ultimate", "unique"}
        if typeVal not in validTypes:
            _fail_dev_preflight(
                f"Type '{typeVal}' is invalid.",
                fix=f"Type must be one of: {', '.join(sorted(validTypes))}"
            )
        statusVal = getattr(args, "status", "provisional")
        if statusVal is None:
            statusVal = "provisional"
        validStatuses = {"provisional", "validated", "disputed", "deprecated"}
        if statusVal not in validStatuses:
            _fail_dev_preflight(
                f"Status '{statusVal}' is invalid for generic skill.",
                fix=f"Status must be one of: {', '.join(sorted(validStatuses))}"
            )


def preflightLinkCommand(args) -> None:
    """Validate arguments for the link command."""
    import json
    registryPath = args.registry
    targetId = args.target.lstrip("/")
    prereqsList = parseCommaSeparatedIds(args.prereqs, "prerequisite")
    if not prereqsList:
        _fail_dev_preflight(
            "No prerequisite skills specified.",
            fix="Provide a comma-separated list of prerequisite skill IDs."
        )
    if not genericSkillExists(registryPath, targetId):
        _fail_dev_preflight(
            f"Target skill '{targetId}' does not exist.",
            fix="Ensure the target skill exists before adding prerequisites to it."
        )
    for prereqId in prereqsList:
        if not genericSkillExists(registryPath, prereqId):
            _fail_dev_preflight(
                f"Prerequisite skill '{prereqId}' does not exist.",
                fix=f"Ensure the prerequisite skill '{prereqId}' exists in the registry first."
            )
    for prereqId in prereqsList:
        if prereqId == targetId:
            _fail_dev_preflight(
                f"Cannot link skill '{targetId}' to itself.",
                fix="Remove the target skill ID from the prerequisite list."
            )
    seen = set()
    duplicatesInList = []
    for prereqId in prereqsList:
        if prereqId in seen:
            duplicatesInList.append(prereqId)
        else:
            seen.add(prereqId)
    if duplicatesInList:
        dupListStr = ", ".join(duplicatesInList)
        _fail_dev_preflight(
            f"Duplicate prerequisite IDs are not allowed in the link list: {dupListStr}.",
            fix="Remove duplicate IDs from the prerequisite list."
        )
    if not getattr(args, "reset", False):
        from gaia_cli.registry import registry_nodes_dir
        nodesDir = Path(registry_nodes_dir(registryPath))
        targetPrereqs = []
        for p in nodesDir.glob("**/*.json"):
            if p.stem == targetId:
                with open(p, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        targetPrereqs = data.get("prerequisites", [])
                    except Exception:
                        pass
                break
        existingDups = [p for p in prereqsList if p in targetPrereqs]
        if existingDups:
            dupRelStr = ", ".join(existingDups)
            _fail_dev_preflight(
                f"Relationship already exists: {targetId} is already linked to prerequisite(s): {dupRelStr}.",
                fix="Remove the already-linked prerequisite(s) from the list, or use --reset to overwrite them."
            )
