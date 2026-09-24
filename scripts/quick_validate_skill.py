#!/usr/bin/env python3
"""Quick validation script for skills and playbooks.

Reconciles generic skill-creator quick validation with Gaia playbook frontmatter:
- For ordinary skills, enforces standard generic skill properties and detects unexpected keys.
- For Gaia playbooks (opt-in via `playbookVersion: 1`), recognizes extended playbook
  contract fields (class, objective, capability, preconditions, steps, stopConditions,
  proof, done) alongside base properties, while still detecting arbitrary unknown keys.
- Provides adapt_upstream_validator() to wrap an external/upstream quick_validate function.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
PLAYBOOK_SCHEMA_PATH = REPO_ROOT / "founder" / "steward" / "playbook.schema.json"

# Generic skill-creator allowed frontmatter properties (Anthropic skill spec)
ALLOWED_BASE_PROPERTIES = frozenset({
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
})

# Gaia repository skill metadata extensions
GAIA_METADATA_PROPERTIES = frozenset({
    "version",
    "argument-hint",
    "disable-model-invocation",
    "genericSkillRef",
})

# Gaia agent playbook extension properties (opt-in via playbookVersion: 1)
PLAYBOOK_PROPERTIES = frozenset({
    "playbookVersion",
    "class",
    "objective",
    "capability",
    "preconditions",
    "steps",
    "stopConditions",
    "proof",
    "done",
})


def validate_frontmatter_dict(
    frontmatter: dict[str, Any],
    *,
    strict_upstream: bool = False,
    is_playbook_override: bool | None = None,
) -> tuple[bool, str, bool]:
    """Validate frontmatter keys according to validator precedence.

    Returns:
        (valid, error_message, is_playbook)
    """
    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a YAML dictionary", False

    is_playbook = (
        is_playbook_override
        if is_playbook_override is not None
        else ("playbookVersion" in frontmatter)
    )

    if is_playbook:
        version = frontmatter.get("playbookVersion")
        if version != 1:
            return (
                False,
                f"Unsupported playbookVersion '{version}'; only playbookVersion: 1 is supported",
                True,
            )
        allowed = set(ALLOWED_BASE_PROPERTIES | PLAYBOOK_PROPERTIES)
        if not strict_upstream:
            allowed.update(GAIA_METADATA_PROPERTIES)
    else:
        allowed = set(ALLOWED_BASE_PROPERTIES)
        if not strict_upstream:
            allowed.update(GAIA_METADATA_PROPERTIES)

    unexpected_keys = set(frontmatter.keys()) - allowed
    if unexpected_keys:
        return (
            False,
            (
                f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
                f"Allowed properties are: {', '.join(sorted(allowed))}"
            ),
            is_playbook,
        )

    return True, "", is_playbook


def _validate_playbook_contract_internal(
    frontmatter: dict[str, Any], repo_root: Path = REPO_ROOT
) -> tuple[bool, str]:
    """Run schema and command spine validation for a playbook."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return True, ""

    if not PLAYBOOK_SCHEMA_PATH.is_file():
        return True, ""

    try:
        schema = json.loads(PLAYBOOK_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(frontmatter))
        if errors:
            first = errors[0]
            path = ".".join(str(p) for p in first.absolute_path) or "frontmatter"
            return False, f"Playbook contract schema error at {path}: {first.message}"
    except Exception as exc:
        return False, f"Playbook contract check failed: {exc}"

    # Also check capability terms and steps if checker is importable
    try:
        if str(repo_root / "src") not in sys.path:
            sys.path.insert(0, str(repo_root / "src"))
        from gaia_cli.steward.policy import find_banned_capability_terms
        from scripts.check_playbook_contract import validate_run

        capability = frontmatter.get("capability")
        if isinstance(capability, str):
            forbidden = find_banned_capability_terms(capability)
            if forbidden:
                return (
                    False,
                    f"Playbook capability contains forbidden routing term(s): {list(forbidden)}",
                )

        steps = frontmatter.get("steps")
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and "run" in step:
                    validate_run(step["run"], repo_root)
    except Exception as exc:
        return False, f"Playbook contract check failed: {exc}"

    return True, ""


def validate_skill(
    skill_path: str | Path,
    *,
    strict_upstream: bool = False,
    check_contract: bool = False,
    upstream_validator: Callable[[Any], tuple[bool, str]] | None = None,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    """Validate a skill directory or SKILL.md file.

    Returns:
        (valid, message)
    """
    path_obj = Path(skill_path)
    if path_obj.is_file():
        skill_md = path_obj
        skill_dir = path_obj.parent
    else:
        skill_dir = path_obj
        skill_md = path_obj / "SKILL.md"

    if not skill_md.exists():
        return False, f"SKILL.md not found in {skill_dir}"

    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception as exc:
        return False, f"Failed to read SKILL.md: {exc}"

    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        return False, f"Invalid YAML in frontmatter: {exc}"

    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a YAML dictionary"

    valid_keys, key_msg, is_playbook = validate_frontmatter_dict(
        frontmatter, strict_upstream=strict_upstream
    )
    if not valid_keys:
        return False, key_msg

    # Required fields
    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    # If an external upstream validator is provided, wrap its execution
    if upstream_validator is not None:
        if not is_playbook:
            # Ordinary skills can be passed straight to upstream validator
            up_valid, up_msg = upstream_validator(skill_dir)
            if not up_valid:
                return False, up_msg
        else:
            # Playbook: pass a sanitized frontmatter (base fields only) in a temp dir
            # so upstream validator checks name, description length, etc. without choke on playbook keys
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_skill_dir = Path(tmpdir)
                tmp_md = tmp_skill_dir / "SKILL.md"
                allowed_tmp_keys = ALLOWED_BASE_PROPERTIES | (
                    set() if strict_upstream else GAIA_METADATA_PROPERTIES
                )
                sanitized_fm = {k: v for k, v in frontmatter.items() if k in allowed_tmp_keys}
                # If description has angle brackets for trigger notation (<skill>), mask them for upstream
                if not strict_upstream and isinstance(sanitized_fm.get("description"), str):
                    sanitized_fm["description"] = (
                        sanitized_fm["description"].replace("<", "(").replace(">", ")")
                    )
                body = content[match.end() :]
                tmp_md.write_text(
                    f"---\n{yaml.safe_dump(sanitized_fm, sort_keys=False)}---\n{body}",
                    encoding="utf-8",
                )
                up_valid, up_msg = upstream_validator(tmp_skill_dir)
                if not up_valid:
                    return False, up_msg
    else:
        # Native upstream-compatible validation
        name = frontmatter.get("name", "")
        if not isinstance(name, str):
            return False, f"Name must be a string, got {type(name).__name__}"
        name = name.strip()
        if not name:
            return False, "Missing 'name' in frontmatter"
        if not re.match(r"^[a-z0-9-]+$", name):
            return (
                False,
                f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)",
            )
        if name.startswith("-") or name.endswith("-") or "--" in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
        if len(name) > 64:
            return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

        description = frontmatter.get("description", "")
        if not isinstance(description, str):
            return False, f"Description must be a string, got {type(description).__name__}"
        description = description.strip()
        if not description:
            return False, "Missing 'description' in frontmatter"
        if strict_upstream and not is_playbook:
            if "<" in description or ">" in description:
                return False, "Description cannot contain angle brackets (< or >)"
        if len(description) > 1024:
            return (
                False,
                f"Description is too long ({len(description)} characters). Maximum is 1024 characters.",
            )

        compatibility = frontmatter.get("compatibility")
        if compatibility:
            if not isinstance(compatibility, str):
                return False, f"Compatibility must be a string, got {type(compatibility).__name__}"
            if len(compatibility) > 500:
                return (
                    False,
                    f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters.",
                )

    if is_playbook and check_contract:
        contract_valid, contract_msg = _validate_playbook_contract_internal(
            frontmatter, repo_root=repo_root
        )
        if not contract_valid:
            return False, contract_msg

    return True, "Skill is valid!"


def adapt_upstream_validator(
    upstream_validate_fn: Callable[[Any], tuple[bool, str]],
    *,
    strict_upstream: bool = False,
    check_contract: bool = False,
    repo_root: Path = REPO_ROOT,
) -> Callable[[Any], tuple[bool, str]]:
    """Wrap an upstream skill-creator validate_skill function to recognize Gaia playbooks."""

    def adapted_validate(skill_path: str | Path) -> tuple[bool, str]:
        return validate_skill(
            skill_path,
            strict_upstream=strict_upstream,
            check_contract=check_contract,
            upstream_validator=upstream_validate_fn,
            repo_root=repo_root,
        )

    return adapted_validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Quick validation script for agent skills and Gaia playbooks.",
    )
    parser.add_argument("skill_directory", help="Path to the skill directory or SKILL.md file")
    parser.add_argument(
        "--strict-upstream",
        action="store_true",
        help="Disallow Gaia-specific metadata extensions for ordinary skills and forbid angle brackets.",
    )
    parser.add_argument(
        "--check-contract",
        action="store_true",
        help="Also validate the playbook contract (schema and command spine) if the skill is a playbook.",
    )
    parser.add_argument(
        "--upstream-validator",
        type=str,
        default=None,
        help="Path to an upstream quick_validate.py script to wrap.",
    )

    args = parser.parse_args(argv)

    upstream_fn = None
    if args.upstream_validator:
        upstream_path = Path(args.upstream_validator).resolve()
        if not upstream_path.is_file():
            print(f"Upstream validator not found: {upstream_path}", file=sys.stderr)
            return 1
        import importlib.util

        spec = importlib.util.spec_from_file_location("upstream_quick_validate", upstream_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            upstream_fn = getattr(mod, "validate_skill", None)

    valid, message = validate_skill(
        args.skill_directory,
        strict_upstream=args.strict_upstream,
        check_contract=args.check_contract,
        upstream_validator=upstream_fn,
    )
    print(message)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
