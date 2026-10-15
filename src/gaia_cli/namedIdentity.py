"""Lowercase-only named-skill identity rules (issue #2055).

A named skill is ``<contributor>/<slug>`` with a lowercase contributor.
Mixed-case input is rejected with its expected spelling, never normalized.
GitHub handles remain case-insensitive for collision detection, including legacy
mixed-case registry entries. Add, rename, ratify, push and the intake adapter
share this validation contract.
"""

from __future__ import annotations

import os
import re

from gaia_cli.registry import named_skills_dir

# GitHub handle shape. Underscore stays legal because ``gaia dev add`` has
# always accepted it; uppercase is recognized only to explain the rejection.
HANDLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
# The skill slug segment stays lowercase.
NAMED_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def validateContributor(value) -> str | None:
    """Return an error message for a malformed contributor handle, else None."""
    if not isinstance(value, str) or not value.strip():
        return "contributor is required"
    if "/" in value:
        return f"contributor '{value}' cannot contain '/'"
    if not HANDLE_RE.fullmatch(value):
        return (
            f"contributor '{value}' is not a valid handle "
            "(lowercase alphanumeric, underscore or hyphen)"
        )
    if value != value.lower():
        return (
            f"contributor '{value}' must be lowercase; expected '{value.lower()}'. "
            "Gaia never normalizes identities silently"
        )
    return None


def identityKey(contributor: str, slug: str) -> str:
    """Case-insensitive collision key for ``contributor/slug``."""
    return f"{contributor}/{slug}".casefold()


def findIdentityCollisions(registryPath, contributor: str, slug: str, ignoreIds=()) -> list[str]:
    """Describe every on-disk named identity that collides with the candidate.

    Returns human-readable lines, empty when the identity is free. Detects an
    exact duplicate, a skill that differs only by case, and a contributor
    directory that differs only by case (the same GitHub account under a second
    spelling). ``ignoreIds`` lists exact ids the caller is deliberately
    replacing, e.g. the old id of a maintainer-driven rename.
    """
    namedRoot = named_skills_dir(registryPath)
    if not os.path.isdir(namedRoot):
        return []
    ignored = {str(item) for item in ignoreIds}
    wantedDir = contributor.casefold()
    wantedSlug = slug.casefold()
    collisions: list[str] = []
    for directory in sorted(os.listdir(namedRoot)):
        directoryPath = os.path.join(namedRoot, directory)
        if not os.path.isdir(directoryPath) or directory.casefold() != wantedDir:
            continue
        if directory != contributor:
            collisions.append(
                f"contributor directory '{directory}' already exists and differs from "
                f"'{contributor}' only by case"
            )
        for filename in sorted(os.listdir(directoryPath)):
            if not filename.endswith(".md"):
                continue
            stem = filename[:-3]
            if stem.casefold() != wantedSlug:
                continue
            existing = f"{directory}/{stem}"
            if existing in ignored:
                continue
            if existing == f"{contributor}/{slug}":
                collisions.append(f"named skill '{existing}' already exists")
            else:
                collisions.append(
                    f"named skill '{existing}' already exists and differs from "
                    f"'{contributor}/{slug}' only by case"
                )
    return collisions


COLLISION_FIX = (
    "Resolve the existing identity collision with a maintainer before retrying; "
    "new contributor identities must be lowercase. Gaia never normalizes identities silently."
)


def identityProblem(registryPath, contributor: str, slug: str, ignoreIds=()) -> str | None:
    """Single-line rejection reason for add/ratify, or None when the identity is free."""
    collisions = findIdentityCollisions(registryPath, contributor, slug, ignoreIds)
    if not collisions:
        return None
    return "; ".join(collisions)
