#!/usr/bin/env python3
"""Validate opt-in agent playbooks against their schema and live command spine."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import types
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from gaia_cli.steward.policy import find_banned_capability_terms


CANONICAL_SKILLS = Path(".agents/skills")
SCHEMA_PATH = Path("founder/steward/playbook.schema.json")
PLACEHOLDER_RE = re.compile(r"^\{[a-z][a-z0-9_]*\}$")
ENV_ASSIGNMENT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)
SAFE_PATH_TOKEN_RE = re.compile(r"^[A-Za-z0-9_./,:+%@{}=-]*$")


class CommandContractError(ValueError):
    """A run step is outside the constrained command grammar."""


class _Placeholder(str):
    pass


class _PlaceholderChoices:
    def __init__(self, choices: Any):
        self._choices = choices

    def __contains__(self, value: object) -> bool:
        return (
            isinstance(value, str) and _is_placeholder(value)
        ) or value in self._choices

    def __iter__(self):
        return iter(self._choices)

    def __str__(self) -> str:
        return str(self._choices)


def _is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.fullmatch(value))


def _has_only_supported_placeholder(value: str) -> bool:
    if _is_placeholder(value):
        return True
    assignment = ENV_ASSIGNMENT_RE.fullmatch(value)
    if assignment and _is_placeholder(assignment.group(2)):
        return True
    option_assignment = re.fullmatch(r"--?[A-Za-z0-9][A-Za-z0-9-]*=(\{[a-z][a-z0-9_]*\})", value)
    return bool(option_assignment)


def _placeholder_aware_type(converter: Any):
    def convert(value: str):
        if _is_placeholder(value):
            return _Placeholder(value)
        return converter(value)

    return convert


def _all_parsers(root: argparse.ArgumentParser) -> Iterable[argparse.ArgumentParser]:
    seen: set[int] = set()
    pending = [root]
    while pending:
        parser = pending.pop()
        if id(parser) in seen:
            continue
        seen.add(id(parser))
        yield parser
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                pending.extend(action.choices.values())


def _parse_gaia_arguments(arguments: list[str], repo_root: Path) -> None:
    src = str(repo_root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from gaia_cli.main import get_parser

    parser, _ = get_parser()
    restores: list[tuple[Any, str, Any]] = []

    def fail(_self: argparse.ArgumentParser, message: str) -> None:
        raise CommandContractError(message)

    for nested in _all_parsers(parser):
        restores.append((nested, "allow_abbrev", nested.allow_abbrev))
        nested.allow_abbrev = False
        restores.append((nested, "error", nested.error))
        nested.error = types.MethodType(fail, nested)
        for action in nested._actions:
            if isinstance(action, argparse._SubParsersAction):
                continue
            if action.type is not None:
                restores.append((action, "type", action.type))
                action.type = _placeholder_aware_type(action.type)
            if action.choices is not None:
                restores.append((action, "choices", action.choices))
                action.choices = _PlaceholderChoices(action.choices)

    try:
        parser.parse_args(arguments)
    except CommandContractError:
        raise
    except SystemExit as exc:
        raise CommandContractError(
            f"argparse exited unexpectedly while validating the command (status {exc.code})"
        ) from exc
    finally:
        for target, attribute, original in reversed(restores):
            setattr(target, attribute, original)


def _tokenize_run(command: str) -> tuple[list[str], str | None, str | None]:
    if "`" in command or "$(" in command:
        raise CommandContractError("command substitution is forbidden")
    if re.search(r"[<>]\(", command):
        raise CommandContractError("process substitution is forbidden")

    lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError as exc:
        raise CommandContractError(f"malformed shell quoting: {exc}") from exc
    if not tokens:
        raise CommandContractError("run command is empty")

    operators = [(index, token) for index, token in enumerate(tokens) if token in {"|", "||", "&", "&&", ";", "<", ">", ">>"} or re.fullmatch(r"[|&;<>]+", token)]
    redirect: str | None = None
    redirect_target: str | None = None
    if operators:
        if len(operators) != 1 or operators[0][1] not in {">", ">>"}:
            operator = operators[0][1]
            descriptions = {
                "|": "pipes",
                "||": "chained commands",
                "&&": "chained commands",
                ";": "chained commands",
                "&": "background execution",
                "<": "input redirects",
            }
            raise CommandContractError(f"{descriptions.get(operator, 'shell operator')} '{operator}' is forbidden")
        index, redirect = operators[0]
        if index != len(tokens) - 2:
            raise CommandContractError("stdout redirect must be the final command fragment")
        if index > 0 and tokens[index - 1].isdigit():
            raise CommandContractError("file-descriptor redirects are forbidden; only stdout > or >> is allowed")
        redirect_target = tokens[-1]
        if not redirect_target or redirect_target.startswith("-") or any(char.isspace() for char in redirect_target):
            raise CommandContractError("stdout redirect target must be one placeholder or path")
        if not (_is_placeholder(redirect_target) or SAFE_PATH_TOKEN_RE.fullmatch(redirect_target)):
            raise CommandContractError("stdout redirect target must be one placeholder or path")
        tokens = tokens[:index]

    if any(token in {"(", ")"} for token in tokens):
        raise CommandContractError("subshell syntax is forbidden")
    if any("${" in token or "$" in token for token in tokens):
        raise CommandContractError("shell variable expansion is forbidden; use a {lower_snake} placeholder")
    for token in tokens:
        if ("{" in token or "}" in token) and not _has_only_supported_placeholder(token):
            raise CommandContractError(
                f"malformed placeholder '{token}'; placeholders must use {{lower_snake_case}}"
            )
    return tokens, redirect, redirect_target


def validate_run(command: str, repo_root: Path = REPO_ROOT) -> None:
    tokens, _redirect, _target = _tokenize_run(command)
    while tokens and ENV_ASSIGNMENT_RE.fullmatch(tokens[0]):
        match = ENV_ASSIGNMENT_RE.fullmatch(tokens.pop(0))
        assert match is not None
        name = match.group(1)
        raise CommandContractError(
            f"environment assignment '{name}' is not allowed; command spines must not "
            "override command resolution or process configuration"
        )
    if not tokens:
        raise CommandContractError("environment assignments must be followed by a command")

    executable = tokens.pop(0)
    if executable == "gaia":
        if not tokens:
            raise CommandContractError("gaia must name a command")
        _parse_gaia_arguments(tokens, repo_root)
        return
    if executable in {"python", "python3"}:
        if not tokens:
            raise CommandContractError(f"{executable} must name a tracked scripts/... file")
        script = tokens[0]
        if _is_placeholder(script) or not script.startswith("scripts/"):
            raise CommandContractError(f"{executable} entrypoint must be a literal scripts/... path")
        script_path = (repo_root / script).resolve()
        try:
            script_path.relative_to((repo_root / "scripts").resolve())
        except ValueError as exc:
            raise CommandContractError("Python entrypoint must stay within scripts/") from exc
        if not script_path.is_file():
            raise CommandContractError(f"tracked Python script does not exist: {script}")
        try:
            tracked = subprocess.run(
                ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", script],
                capture_output=True,
                check=False,
                text=True,
            )
        except OSError as exc:
            raise CommandContractError(f"could not verify tracked script {script}: {exc}") from exc
        if tracked.returncode != 0:
            raise CommandContractError(f"Python script is not tracked by git: {script}")
        return
    raise CommandContractError("executable must be gaia, python, or python3")


def _frontmatter(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("missing closing YAML frontmatter delimiter")
    frontmatter_text = parts[1]
    parsed = yaml.safe_load(frontmatter_text)
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError("YAML frontmatter must be an object")
    return parsed


def _format_schema_path(error: Any, data: dict[str, Any]) -> str:
    parts = list(error.absolute_path)
    if len(parts) >= 2 and parts[0] == "steps" and isinstance(parts[1], int):
        index = parts[1]
        steps = data.get("steps")
        step_id = None
        if isinstance(steps, list) and index < len(steps) and isinstance(steps[index], dict):
            step_id = steps[index].get("id")
        label = step_id if isinstance(step_id, str) else f"steps[{index}]"
        suffix = ".".join(str(part) for part in parts[2:])
        return f"step {label}" + (f": {suffix}" if suffix else "")
    path = ".".join(str(part) for part in parts)
    return path or "frontmatter"


def validate_repository(repo_root: Path = REPO_ROOT) -> tuple[int, int, list[str]]:
    schema = json.loads((repo_root / SCHEMA_PATH).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    skills = sorted((repo_root / CANONICAL_SKILLS).glob("**/SKILL.md"))
    opted_in = 0
    errors: list[str] = []

    for skill in skills:
        relative = skill.relative_to(repo_root).as_posix()
        try:
            data = _frontmatter(skill)
        except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
            errors.append(f"{relative}: frontmatter: {exc}")
            continue
        if "playbookVersion" not in data:
            continue
        opted_in += 1
        schema_errors = sorted(
            validator.iter_errors(data),
            key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message),
        )
        for error in schema_errors:
            errors.append(f"{relative}: {_format_schema_path(error, data)}: {error.message}")

        steps = data.get("steps")
        if isinstance(steps, list):
            seen: set[str] = set()
            for index, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                step_id = step.get("id")
                label = step_id if isinstance(step_id, str) else f"steps[{index}]"
                if isinstance(step_id, str):
                    if step_id in seen:
                        errors.append(f"{relative}: step {step_id}: duplicate step id")
                    seen.add(step_id)
                run = step.get("run")
                if isinstance(run, str):
                    try:
                        validate_run(run, repo_root)
                    except CommandContractError as exc:
                        errors.append(f"{relative}: step {label}: run: {exc}")

        capability = data.get("capability")
        if isinstance(capability, str):
            forbidden_terms = find_banned_capability_terms(capability)
            if forbidden_terms:
                errors.append(
                    f"{relative}: capability: remove forbidden routing term(s) "
                    f"{list(forbidden_terms)}; describe the required judgment without routing authority"
                )
    return len(skills), opted_in, errors


def main() -> int:
    scanned, opted_in, errors = validate_repository()
    if errors:
        print("Agent playbook contract validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  ERROR: {error}", file=sys.stderr)
        print(
            f"Playbooks checked: {opted_in}; canonical skills scanned: {scanned}; errors: {len(errors)}",
            file=sys.stderr,
        )
        return 1
    print(f"Agent playbook contract valid ({opted_in} playbook(s), {scanned} canonical skill(s) scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
