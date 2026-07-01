#!/usr/bin/env python3
"""Dry-run source-curation runner.

No network calls are made. No registry files are mutated. The runner writes a
schema-valid proposal report for review.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaia_cli.sourceCuration import main


if __name__ == "__main__":
    raise SystemExit(main())
