#!/usr/bin/env python3
"""Dry-run source-curation runner.

The default mode uses offline GitHub fixtures and makes no network calls. Live
GitHub reads require explicit opt-in. No registry files are mutated; the runner
writes a schema-valid proposal report for review.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaia_cli.sourceCuration import main


if __name__ == "__main__":
    raise SystemExit(main())
