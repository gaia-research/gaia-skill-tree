"""Named skill promotion logic.

Promotes an awakened skill from intake batch to a full named skill
in registry/named/{contributor}/{skill-name}.md
"""

import datetime
import json
import os
import re

from gaia_cli.registry import named_skills_dir

_CONTRIBUTOR_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
_SKILL_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def find_awakened_skill(batch_path, skill_id):
    """Find a skill by id in the proposedSkills list of an intake batch.

    Parameters
    ----------
    batch_path : str
        Absolute or relative path to the intake batch JSON file.
    skill_id : str
        The ``id`` field of the proposed skill to locate.

    Returns
    -------
    dict
        The skill dict from the batch.

    Raises
    ------
    FileNotFoundError
        If ``batch_path`` does not exist.
    ValueError
        If no proposed skill with ``skill_id`` is found in the batch.
    """
    with open(batch_path, "r") as f:
        batch = json.load(f)

    for skill in batch.get("proposedSkills", []):
        if skill.get("id") == skill_id:
            return skill

    raise ValueError(
        f"No proposed skill with id '{skill_id}' found in {batch_path}"
    )


def promote_to_named(skill_data, contributor, skill_name, registry_path):
    """Create a named skill .md file in registry/named/{contributor}/{skill-name}.md.

    Parameters
    ----------
    skill_data : dict
        The proposed skill dict (must contain 'id', 'name', 'description').
    contributor : str
        GitHub username or org name of the contributor.
    skill_name : str
        Kebab-case name for the skill (becomes the filename stem and the
        second segment of the named skill id).
    registry_path : str
        Root of the local Gaia registry clone.

    Returns
    -------
    str
        Absolute path to the written .md file.
    """
    today = datetime.date.today().isoformat()
    if not _CONTRIBUTOR_RE.match(contributor):
        raise ValueError(f"Invalid contributor: {contributor!r}")
    if not _SKILL_NAME_RE.match(skill_name):
        raise ValueError(f"Invalid skill_name: {skill_name!r}")
    named_id = f"{contributor}/{skill_name}"
    dest_dir = os.path.join(named_skills_dir(registry_path), contributor)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, f"{skill_name}.md")

    content = (
        "---\n"
        f"id: {named_id}\n"
        f"name: {skill_data['name']}\n"
        f"contributor: {contributor}\n"
        "origin: true\n"
        f"genericSkillRef: {skill_data['id']}\n"
        "status: named\n"
        "level: 2★\n"
        f"description: {skill_data['description']}\n"
        "links:\n"
        f"  github: https://github.com/{contributor}/{skill_name}\n"
        "tags: []\n"
        f'createdAt: "{today}"\n'
        f'updatedAt: "{today}"\n'
        "---\n"
        "\n"
        "## Overview\n"
        "\n"
        f"{skill_data['description']}\n"
        "\n"
        "## Origin\n"
        "\n"
        f"First published by @{contributor}. This is the origin implementation "
        f"for the \"{skill_data['id']}\" skill bucket.\n"
    )

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

    from gaia_cli.timeline import append_skill_event
    append_skill_event(
        skill_data['id'],
        "name",
        contributor,
        f"Named by @{contributor} as {contributor}/{skill_name}",
        registry_path
    )

    return dest_path


def update_batch_lifecycle(batch_path, skill_id, new_status):
    """Update the lifecycle field of a proposed skill in an intake batch file.

    Parameters
    ----------
    batch_path : str
        Path to the intake batch JSON file.
    skill_id : str
        The ``id`` of the proposed skill to update.
    new_status : str
        The new lifecycle value (e.g. ``"awakened"``, ``"named"``).

    Raises
    ------
    ValueError
        If no proposed skill with ``skill_id`` is found in the batch.
    """
    with open(batch_path, "r") as f:
        batch = json.load(f)

    found = False
    for skill in batch.get("proposedSkills", []):
        if skill.get("id") == skill_id:
            skill["lifecycle"] = new_status
            found = True
            break

    if not found:
        raise ValueError(
            f"No proposed skill with id '{skill_id}' found in {batch_path}"
        )

    with open(batch_path, "w") as f:
        json.dump(batch, f, indent=2)
        f.write("\n")
