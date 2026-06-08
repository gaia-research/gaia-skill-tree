"""Local-first skill context.

Merges user tree, detected tokens, named skill map, and canonical registry
into a unified data source that commands consume by default.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from gaia_cli.registry import registry_graph_path, registry_nodes_dir, named_skills_dir
from gaia_cli.treeManager import load_tree
from gaia_cli.pathEngine import load_paths


@dataclass
class LocalContext:
    """Unified local-first view of skill state."""

    username: str
    owned_ids: set[str] = field(default_factory=set)
    detected_ids: set[str] = field(default_factory=set)
    novel_ids: set[str] = field(default_factory=set)
    named_map: dict[str, str] = field(
        default_factory=dict
    )  # generic_skill_id -> "contributor/name"
    tree_data: Optional[dict] = None
    graph_data: Optional[dict] = None
    _skill_map: dict[str, dict] = field(default_factory=dict, repr=False)
    _effective_ranks: dict[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def load(
        cls, registry_path: str, username: str, *, include_scan: bool = True
    ) -> "LocalContext":
        """Build context from local state.

        Args:
            registry_path: Path to the registry root
            username: Gaia username
            include_scan: Whether to load last scan results (paths.json)
        """
        # Load user tree
        tree_data = load_tree(username, registry_path=registry_path)
        owned_ids = set()
        if tree_data:
            owned_ids = {
                s.get("skillId")
                for s in tree_data.get("unlockedSkills", [])
                if s.get("skillId")
            }
        
        # Inject custom skills into owned_ids so they appear unlocked
        custom_state_path = os.path.join(".gaia", "custom_state.json")
        if os.path.exists(custom_state_path):
            try:
                with open(custom_state_path, "r", encoding="utf-8") as f:
                    cstate = json.load(f)
                    for sk in cstate.get("customSkills", []):
                        if sk.get("mapped_to"):
                            owned_ids.add(sk["mapped_to"])
                        else:
                            owned_ids.add(sk["id"])
            except Exception:
                pass

        # Load canon graph metadata (for type symbols etc)
        graph_path = registry_graph_path(registry_path)
        graph_data = None
        if os.path.isfile(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)

        # Load skills from modular nodes
        skill_map = {}
        canon_ids = set()
        nodes_dir = registry_nodes_dir(registry_path)
        if os.path.isdir(nodes_dir):
            for root, _, files in os.walk(nodes_dir):
                for file in files:
                    if file.endswith(".json"):
                        try:
                            with open(
                                os.path.join(root, file), "r", encoding="utf-8"
                            ) as f:
                                skill = json.load(f)
                                sid = skill.get("id")
                                if sid:
                                    skill_map[sid] = skill
                                    canon_ids.add(sid)
                        except (OSError, json.JSONDecodeError):
                            continue
        elif graph_data:
            # Fallback to legacy gaia.json if nodes dir missing
            for skill in graph_data.get("skills", []):
                sid = skill.get("id")
                if sid:
                    skill_map[sid] = skill
                    canon_ids.add(sid)

        # Load detected skills from last scan
        detected_ids = set()
        novel_ids = set()
        if include_scan:
            paths = load_paths()
            if paths:
                # nearUnlocks and oneAway contain detected skill IDs
                for path_entry in paths.get("availablePaths", []):
                    for prereq in path_entry.get("ownedPrereqs", []):
                        detected_ids.add(prereq)
                # Also consider owned as detected
                detected_ids |= owned_ids
                # Novel = detected but not in canon
                novel_ids = detected_ids - canon_ids

        # Build named_map: local-first merge of registry, agent dirs, and manifest
        named_map = _build_local_first_map(registry_path, list(skill_map.values()), username)
        
        # Build effective rank map for generic skills
        effective_ranks = {}
        from gaia_cli.registry import named_skills_index_path
        from gaia_cli.redaction import level_num
        idx_path = named_skills_index_path(registry_path)
        if os.path.isfile(idx_path):
            try:
                with open(idx_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for bucket, skills in data.get("buckets", {}).items():
                        ranks = [level_num(s.get("level", "0★")) for s in skills]
                        if ranks:
                            effective_ranks[bucket] = f"{max(ranks)}★"
            except Exception:
                pass

        ctx = cls(
            username=username,
            owned_ids=owned_ids,
            detected_ids=detected_ids,
            novel_ids=novel_ids,
            named_map=named_map,
            tree_data=tree_data,
            graph_data=graph_data,
        )
        ctx._skill_map = skill_map
        ctx._effective_ranks = effective_ranks
        return ctx

    def is_named(self, skill_id: str) -> bool:
        """Check if a canonical skill has a named implementation."""
        return skill_id in self.named_map

    def level_of(self, skill_id: str) -> str:
        """Return the canonical level string for a skill (e.g. '3★').

        For a starless/generic ref this is the *effective rank* — the top star
        among its named children — which is exactly the signal the redaction
        gate needs: a bucket whose top star is ≤ 1★ has no named child, so its
        contributor handle is withheld. Defaults to '0★' when unknown.
        """
        # First check effective rank from named skills index
        if skill_id in self._effective_ranks:
            return self._effective_ranks[skill_id]
        
        # Fallback to direct skill map level
        return (self._skill_map.get(skill_id) or {}).get("level", "0★")

    def is_redacted(self, skill_id: str) -> bool:
        """True when this skill's contributor handle must be withheld (≤ 1★)."""
        from gaia_cli.redaction import is_redacted
        return is_redacted(self.level_of(skill_id))

    def named_ref(self, skill_id: str) -> Optional[str]:
        """Return 'contributor/name' for a named skill, or None.

        Pre-named (≤ 1★) buckets have their contributor segment redacted so the
        handle never escapes the resolver into a renderer.
        """
        ref = self.named_map.get(skill_id)
        if not ref:
            return None
        return self._redact_ref(ref, skill_id)

    def _redact_ref(self, ref: str, skill_id: str) -> str:
        """Replace the contributor segment of ``contrib/name`` with the
        redaction block when the bucket is pre-named/demoted. The caller's own
        handle is never redacted (you can always see your own work)."""
        from gaia_cli.redaction import REDACTED_BLOCK, is_redacted
        if "/" not in ref:
            return ref
        contrib, nickname = ref.split("/", 1)
        if contrib == self.username:
            return ref
        if is_redacted(self.level_of(skill_id)):
            return f"{REDACTED_BLOCK}/{nickname}"
        return ref

    def named_contributor(self, skill_id: str) -> Optional[str]:
        """Return just the contributor name for a named skill (redacted ≤ 1★)."""
        ref = self.named_map.get(skill_id)
        if ref and "/" in ref:
            contrib = ref.split("/", 1)[0]
            if contrib == self.username:
                return contrib
            from gaia_cli.redaction import REDACTED_BLOCK, is_redacted
            if is_redacted(self.level_of(skill_id)):
                return REDACTED_BLOCK
            return contrib
        return None

    def is_local(self, skill_id: str) -> bool:
        """Check if skill is local-only (not in canon)."""
        return skill_id in self.novel_ids

    def is_owned(self, skill_id: str) -> bool:
        """Check if user owns (has unlocked) this skill."""
        return skill_id in self.owned_ids

    def skill_level(self, skill_id: str) -> str:
        """Get the user's level for a skill, or canon level, or '0★'."""
        if self.tree_data:
            for s in self.tree_data.get("unlockedSkills", []):
                if s.get("skillId") == skill_id:
                    return s.get("level", "0★")
        skill = self._skill_map.get(skill_id)
        if skill:
            return skill.get("level", "0★")
        return "0★"

    def skill_type(self, skill_id: str) -> str:
        """Get skill type (basic/extra/ultimate)."""
        skill = self._skill_map.get(skill_id)
        if skill:
            return skill.get("type", "basic")
        return "basic"

    def all_skills(self) -> list[dict]:
        """Return merged skill list: canon + novel local skills."""
        skills = list(self._skill_map.values())
        for novel_id in self.novel_ids:
            if novel_id not in self._skill_map:
                skills.append(
                    {
                        "id": novel_id,
                        "name": novel_id,
                        "type": "basic",
                        "level": "0★",
                        "rarity": "common",
                        "prerequisites": [],
                        "derivatives": [],
                        "local": True,
                    }
                )
        return skills

    def display_name(self, skill_id: str, canon: bool = False) -> str:
        """Return the best display name for a skill.

        Priority (Local-First):
        - Nickname ID (e.g. /gaia-curate or karpathy/autoresearch)
        - Human-readable Name (e.g. Research)
        - Generic ID as fallback (/research)

        If canon=True, always returns /skill-id.
        """
        if canon:
            return f"/{skill_id}"

        # 1. Check for named nickname (Pet Nickname)
        if skill_id in self.named_map:
            ref = self.named_map[skill_id]
            if "/" in ref:
                contrib, nickname = ref.split("/", 1)
                if contrib == self.username:
                    return f"/{nickname}"
                # Pre-named / demoted buckets: withhold the contributor handle.
                return self._redact_ref(ref, skill_id)
            return f"/{ref}"

        # 2. Check for local novel skill
        if skill_id in self.novel_ids:
            return f"/{skill_id}"

        # 3. Fallback to generic slash ID
        return f"/{skill_id}"


def _build_named_map(registry_path: str) -> dict[str, str]:
    """Scan registry/named/ to build generic_skill_id -> 'contributor/name' map.
    Optimized to use pre-compiled named-skills.json index when available."""
    named_map: dict[str, str] = {}

    # Try fast path: load from pre-compiled index
    from gaia_cli.registry import named_skills_index_path

    index_path = named_skills_index_path(registry_path)
    if os.path.isfile(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Combine named and awakened skills
                all_skills = []
                for bucket, skills in data.get("buckets", {}).items():
                    all_skills.extend(skills)
                all_skills.extend(data.get("awaitingClassification", []))

                # Reconstruct path logic for stable overwrite order (matches sorted glob)
                valid_skills = []
                for s in all_skills:
                    skill_id = s.get("id")
                    if not skill_id:
                        continue

                    rel_path = f"{skill_id}.md"
                    if rel_path.count("/") == 1:
                        valid_skills.append((rel_path, s))

                valid_skills.sort(key=lambda x: x[0])

                for path, skill in valid_skills:
                    generic_ref = skill.get("genericSkillRef")
                    skill_id = skill.get("id")
                    if generic_ref and skill_id:
                        named_map[generic_ref] = skill_id
            return named_map
        except (OSError, json.JSONDecodeError):
            pass

    # Fallback to scanning markdown files directly
    named_dir = Path(named_skills_dir(registry_path))
    if not named_dir.is_dir():
        return named_map
    for md_path in sorted(named_dir.glob("*/*.md")):
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---\n"):
            continue
        # Parse frontmatter for genericSkillRef and id
        frontmatter_end = text.find("\n---", 4)
        if frontmatter_end == -1:
            continue
        frontmatter = text[4:frontmatter_end]
        skill_id = None
        generic_ref = None
        for line in frontmatter.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key == "id":
                skill_id = value
            elif key == "genericSkillRef":
                generic_ref = value
        if generic_ref and skill_id:
            named_map[generic_ref] = skill_id
    return named_map


def _build_install_map(registry_path: str) -> dict[str, str]:
    """Build {generic_ref: contributor/name} from .gaia/install-manifest.json."""
    from gaia_cli.treeManager import _iter_manifest_refs
    result: dict[str, str] = {}
    for ref, entry in _iter_manifest_refs(registry_path):
        sid = entry.get("id", "")
        if sid:
            result[ref] = sid
    return result


def _build_agent_dir_map(
    canonical_skills: list,
    manifest_covered: set,
    username: str,
    root: str = ".",
) -> dict[str, str]:
    """Build {canonical_id: username/dirname} for agent skill dirs not already in manifest."""
    if not username:
        return {}
    from gaia_cli.scanner import scan_skill_mds, match_skill_to_canonical
    result: dict[str, str] = {}
    for entry in scan_skill_mds(root=root):
        dir_name = entry["id"]
        if dir_name in manifest_covered:
            continue
        match = match_skill_to_canonical(
            entry["id"], entry["name"], entry["description"], canonical_skills
        )
        if match:
            canonical_id, _ = match
            result[canonical_id] = f"{username}/{dir_name}"
    return result


def _build_local_first_map(
    registry_path: str,
    canonical_skills: list,
    username: str,
) -> dict[str, str]:
    """Merge named_map sources with priority: install > agent-dirs > registry."""
    base = _build_named_map(registry_path)                          # priority 3
    install = _build_install_map(registry_path)                    # priority 1 (highest)
    manifest_covered = {
        v.split("/", 1)[1] if "/" in v else v
        for v in install.values()
    }
    if username:
        agents = _build_agent_dir_map(
            canonical_skills, manifest_covered, username
        )
        base.update(agents)                                        # priority 2
    base.update(install)
    return base
