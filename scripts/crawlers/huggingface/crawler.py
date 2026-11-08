"""Crawls HuggingFace for models and spaces representing AI skills."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from common.evidence_scorer import compute_score
from common.candidate_builder import build_candidate, normalize_id
from common.dedup import deduplicate
from common.proposer import write_proposals

HF_API = "https://huggingface.co/api"

TASK_TO_SKILL = {
    "text-generation": "generate-text",
    "summarization": "summarize",
    "token-classification": "extract-entities",
    "text-classification": "classify",
    "question-answering": "retrieve",
    "feature-extraction": "embed-text",
    "text2text-generation": "generate-text",
    "fill-mask": "tokenize",
    "sentence-similarity": "score-relevance",
    "zero-shot-classification": "classify",
}

TASKS_TO_CRAWL = list(TASK_TO_SKILL.keys())


def crawl_models(task: str, limit: int = 20) -> list[dict]:
    """Crawl HuggingFace models for a given task."""
    candidates = []
    try:
        res = requests.get(
            f"{HF_API}/models",
            params={"pipeline_tag": task, "sort": "downloads", "limit": limit},
            timeout=30,
        )
        if res.status_code != 200:
            print(f"HuggingFace models API returned {res.status_code} for task {task}")
            return []

        models = res.json()
        for model in models:
            model_id = model.get("id", model.get("modelId", ""))
            downloads = model.get("downloads", 0)
            likes = model.get("likes", 0)
            updated = model.get("lastModified", "")

            if downloads < 1000:
                continue

            name = model_id.split("/")[-1] if "/" in model_id else model_id
            description = model.get("description", "") or f"HuggingFace model for {task}"
            url = f"https://huggingface.co/{model_id}"

            skill_id = TASK_TO_SKILL.get(task)
            if not skill_id:
                continue

            score_val = compute_score(downloads, likes, updated, has_readme=True)
            if score_val < 30:
                continue

            candidates.append(build_candidate(
                id=f"{skill_id}-hf-{normalize_id(name)[:30]}",
                name=f"{name} ({task})",
                description=description[:200],
                source_url=url,
                source_type="huggingface",
                score=score_val,
            ))
    except Exception as e:
        print(f"Error crawling HuggingFace models for {task}: {e}")

    return candidates


def main():
    print("Crawling HuggingFace...")
    candidates = []
    for task in TASKS_TO_CRAWL:
        print(f"  Task: {task}")
        candidates.extend(crawl_models(task))

    seen_ids = set()
    unique = []
    for c in candidates:
        if c["id"] not in seen_ids:
            seen_ids.add(c["id"])
            unique.append(c)
    candidates = unique

    print(f"Found {len(candidates)} raw candidates")

    candidates = deduplicate(candidates)
    print(f"After dedup: {len(candidates)} new candidates")

    if candidates:
        write_proposals(candidates, source_name="huggingface")


if __name__ == "__main__":
    main()
