"""Case-preserving named-skill identity rules (issue #2055).

A named skill is ``<contributor>/<slug>``. The contributor is a GitHub handle
whose case is part of the approved identity and must reach disk exactly as
approved; GitHub itself treats handles case-insensitively, so two identities
that differ only by case are one account and must collide rather than coexist.

``gaia dev add``, ``gaia dev ratify``, ``gaia dev rename`` and
``gaia push --from-file`` all use this module so they cannot disagree again.
Nothing here ever rewrites case: callers either accept an identity verbatim or
reject it with a message that names the existing spelling.
"""

from __future__ import annotations

import os
import re

from gaia_cli.registry import named_skills_dir

# GitHub handle shape. Underscore stays legal because ``gaia dev add`` has
# always accepted it; case is preserved, never normalized.
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
            "(alphanumeric, underscore or hyphen; case is preserved)"
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
    "Use the existing spelling, or obtain an explicit maintainer ruling before "
    "changing it; Gaia never normalizes an approved identity's case."
)


def identityProblem(registryPath, contributor: str, slug: str, ignoreIds=()) -> str | None:
    """Single-line rejection reason for add/ratify, or None when the identity is free."""
    collisions = findIdentityCollisions(registryPath, contributor, slug, ignoreIds)
    if not collisions:
        return None
    return "; ".join(collisions)
