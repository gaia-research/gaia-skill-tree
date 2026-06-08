import functools
import json
import os
from gaia_cli.registry import registry_graph_path


@functools.lru_cache(maxsize=1)
def load_canonical_skills(registry_path=None):
    if registry_path is None:
        registry_path = registry_graph_path(".")
    if not os.path.exists(registry_path):
        pass
    canonical_skills = set()
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for skill in data.get("skills", []):
                canonical_skills.add(skill["id"])
    except Exception:
        pass
    return canonical_skills


def resolve_skills(detected_tokens, registry_path=None):
    if registry_path is None:
        registry_path = registry_graph_path(".")
    canonical = load_canonical_skills(registry_path)
    return list(set(detected_tokens).intersection(canonical))
