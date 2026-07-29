"""Embedding generation for Gaia semantic search.

Uses sentence-transformers (all-MiniLM-L6-v2) to embed skill descriptions.
Outputs to registry/embeddings.json for use by search and similarity tools.
"""

import json
import os
import re
from datetime import date

from gaia_cli.registry import embeddings_path, named_skills_dir, registry_graph_path


def loadNamedFrontmatter(mdText):
    """Parse the YAML frontmatter block of a named-skill .md file.

    Returns a dict of the frontmatter fields, or an empty dict if no
    frontmatter is present. Mirrors the frontmatter-reading pattern used by
    treeManager._iter_manifest_refs: prefer PyYAML, fall back to a small
    pure-Python line parser when PyYAML is unavailable.
    """
    match = re.match(r"^---\n(.*?)\n---", mdText, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)
    try:
        import yaml
        return yaml.safe_load(block) or {}
    except ImportError:
        pass
    frontmatter = {}
    for line in block.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Only treat top-level "key: value" lines (no leading indent) as fields;
        # skip nested/list lines the pure-Python fallback cannot model.
        if line[:1] in (" ", "\t", "-"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        frontmatter[key] = value
    return frontmatter


def load_skills(registry_path="."):
    """Load skills from gaia.json plus any named skills from registry/named/.

    Named skills are authored as .md files with YAML frontmatter (not .json),
    so both the legacy .json path and the .md frontmatter path are read here.
    Each named .md contributes its 'id' (contributor/slug), 'name', and
    'description' to the embedded set.

    Returns a list of dicts with at least 'id', 'name', and 'description'.
    """
    skills = []
    seen = set()

    # Load canonical skills from gaia.json
    gaia_path = registry_graph_path(registry_path)
    if os.path.exists(gaia_path):
        try:
            with open(gaia_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for skill in data.get("skills", []):
                sid = skill["id"]
                if sid in seen:
                    continue
                seen.add(sid)
                skills.append({
                    "id": sid,
                    "name": skill.get("name", sid),
                    "description": skill.get("description", ""),
                })
        except Exception as e:
            print(f"Warning: could not load {gaia_path}: {e}")

    # Load named skills from registry/named/**/*.md (YAML frontmatter) and any
    # legacy registry/named/*.json entries.
    named_dir = named_skills_dir(registry_path)
    if os.path.isdir(named_dir):
        for dirpath, _dirnames, filenames in os.walk(named_dir):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                if fname.endswith(".json"):
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            skill = json.load(f)
                        sid = skill.get("id")
                        if sid and sid not in seen:
                            seen.add(sid)
                            skills.append({
                                "id": sid,
                                "name": skill.get("name", sid),
                                "description": skill.get("description", ""),
                            })
                    except Exception as e:
                        print(f"Warning: could not load {fpath}: {e}")
                elif fname.endswith(".md"):
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            frontmatter = loadNamedFrontmatter(f.read())
                        sid = frontmatter.get("id")
                        if sid and sid not in seen:
                            seen.add(sid)
                            skills.append({
                                "id": sid,
                                "name": frontmatter.get("name", sid),
                                "description": frontmatter.get("description", ""),
                            })
                    except Exception as e:
                        print(f"Warning: could not load {fpath}: {e}")

    return skills


def embed_skills(skills, model_name="all-MiniLM-L6-v2"):
    """Generate embeddings for each skill using '{name}: {description}' as input text.

    Returns a list of dicts: [{"id": ..., "vector": [...]}, ...]
    Raises ImportError with a helpful message if sentence-transformers is missing.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers"
        )

    print(f"Loading model '{model_name}'...", flush=True)
    model = SentenceTransformer(model_name)

    texts = [
        f"{skill['name']}: {skill['description']}" for skill in skills
    ]

    print(f"Encoding {len(texts)} skills...", flush=True)
    vectors = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    entries = []
    for skill, vector in zip(skills, vectors):
        entries.append({
            "id": skill["id"],
            "vector": vector.tolist(),
        })

    return entries, vectors.shape[1] if len(vectors) > 0 else 384


def save_embeddings(entries, output_path, model_name, dimensions):
    """Write embeddings to registry/embeddings.json.

    Args:
        entries: list of {"id": ..., "vector": [...]}
        output_path: absolute or relative path to write the JSON file
        model_name: name of the model used to generate embeddings
        dimensions: embedding vector size
    """
    payload = {
        "model": model_name,
        "dimensions": dimensions,
        "generatedAt": str(date.today()),
        "entries": entries,
    }
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved {len(entries)} embeddings to {output_path}")


def generate_embeddings(registry_path=".", model_name="all-MiniLM-L6-v2"):
    """Orchestrate the full embedding generation flow.

    Loads skills, embeds them, and writes registry/embeddings.json.
    """
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError:
        print(
            "Error: sentence-transformers is not installed.\n"
            "Install it with:  pip install sentence-transformers"
        )
        return

    skills = load_skills(registry_path)
    if not skills:
        print("No skills found. Make sure the registry path is correct.")
        return

    print(f"Loaded {len(skills)} skills from {registry_path}.")

    entries, dimensions = embed_skills(skills, model_name=model_name)

    output_path = embeddings_path(registry_path)
    save_embeddings(entries, output_path, model_name=model_name, dimensions=dimensions)
