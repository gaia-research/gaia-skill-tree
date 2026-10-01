#!/usr/bin/env python3
"""Run the offline Gaia generic retrieval benchmark; never mutates registry."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaia_cli.curation.retrieval import loadRetrievalConfig
from gaia_cli.curation.evaluation import DEFAULT_RERANKER, DEFAULT_RERANKER_REVISION, run


def main() -> int:
    default_cfg = loadRetrievalConfig(ROOT)
    default_model = default_cfg.get("defaultModel", "all-MiniLM-L6-v2")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--model",
        default=default_model,
        help=f"Embedding model ID or alias (default: {default_model} from retrieval config)",
    )
    p.add_argument(
        "--revision",
        help="Optional pinned model revision hash (defaults to retrieval config declared revision)",
    )
    p.add_argument(
        "--reranker",
        nargs="?",
        const=DEFAULT_RERANKER,
        default=None,
        help=f"Optional CrossEncoder model ID (default when flag given without value: {DEFAULT_RERANKER})",
    )
    p.add_argument(
        "--reranker-revision",
        default=DEFAULT_RERANKER_REVISION,
        help=f"Pinned revision hash for reranker model (default: {DEFAULT_RERANKER_REVISION})",
    )
    p.add_argument(
        "--corpus",
        default=str(ROOT / "tests/fixtures/curation-oracle.json"),
        help="Path to evaluation oracle JSON fixture",
    )
    p.add_argument(
        "--output",
        help="Write report JSON (stdout if omitted)",
    )
    p.add_argument(
        "--predictions",
        help="Use captured predictions JSON; fully offline, no model load",
    )
    p.add_argument(
        "--limit",
        type=int,
        help="Limit number of corpus cases to evaluate",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-K candidates to evaluate and report in details (default: 5)",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size for model inference (default: 16)",
    )
    p.add_argument(
        "--threads",
        type=int,
        choices=[1],
        help="CPU threads (1 is the verified portable inference contract)",
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass cached document vectors in generated-output/curation/cache",
    )

    a = p.parse_args()

    report = run(
        root=ROOT,
        corpus_path=a.corpus,
        model=a.model,
        revision=a.revision,
        reranker=a.reranker,
        reranker_revision=a.reranker_revision,
        predictions_path=a.predictions,
        limit=a.limit,
        top_k=a.top_k,
        batch_size=a.batch_size,
        threads=a.threads,
        use_cache=not a.no_cache,
    )

    text = json.dumps(report, indent=2) + "\n"
    if a.output:
        out_path = Path(a.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
