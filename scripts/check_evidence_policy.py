#!/usr/bin/env python3
"""Check #2473 evidence-policy agreement across schema/API metadata and active docs/skills."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gaia_cli.steward.knowledge_contracts import check_evidence_policy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify active evidence policy surfaces and exit non-zero on violations (default behavior)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="repository root to inspect (default: repo root)",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    violations = check_evidence_policy(repo_root)
    if violations:
        print(f"Evidence policy check failed ({len(violations)} violation(s)):", file=sys.stderr)
        for v in violations:
            print(f"  [{v['rule']}] {v['source']}: {v['detail']}", file=sys.stderr)
        return 1

    print("Evidence policy check passed (0 violations).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
