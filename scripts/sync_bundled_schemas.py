#!/usr/bin/env python3
"""Sync the bundled schema mirror to canonical registry/schema/.

The pip-installed CLI reads JSON schemas from the bundled mirror at
``src/gaia_cli/data/registry/schema/``.  That mirror MUST stay byte-identical to
the canonical ``registry/schema/`` tree, or ``gaia validate`` (Meta sync check in
``scripts/validate.py::check_meta_sync``) fails for released wheels.

This helper makes the sync mechanical instead of hand-copied (issue #727).

Usage:
    python scripts/sync_bundled_schemas.py            # copy canonical -> bundled
    python scripts/sync_bundled_schemas.py --check     # exit 1 if out of sync (no writes)

``--check`` mirrors the comparison CI runs, so you can gate locally before pushing.
"""

import argparse
import filecmp
import os
import shutil
import sys

REPOROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANONICALDIR = os.path.join(REPOROOT, "registry", "schema")
BUNDLEDDIR = os.path.join(REPOROOT, "src", "gaia_cli", "data", "registry", "schema")


def canonicalFiles():
    """Yield paths of every file under the canonical schema tree, relative to it."""
    for root, _dirs, files in os.walk(CANONICALDIR):
        for name in files:
            full = os.path.join(root, name)
            yield os.path.relpath(full, CANONICALDIR)


def checkSync():
    """Return a list of human-readable drift messages (empty when in sync)."""
    drift = []
    for rel in canonicalFiles():
        canonical = os.path.join(CANONICALDIR, rel)
        bundled = os.path.join(BUNDLEDDIR, rel)
        if not os.path.isfile(bundled):
            drift.append(f"missing in bundle: {rel}")
        elif not filecmp.cmp(canonical, bundled, shallow=False):
            drift.append(f"differs from canonical: {rel}")
    return drift


def sync():
    """Copy every canonical schema file into the bundled mirror. Returns count written."""
    written = 0
    for rel in canonicalFiles():
        canonical = os.path.join(CANONICALDIR, rel)
        bundled = os.path.join(BUNDLEDDIR, rel)
        os.makedirs(os.path.dirname(bundled), exist_ok=True)
        if not os.path.isfile(bundled) or not filecmp.cmp(canonical, bundled, shallow=False):
            shutil.copy2(canonical, bundled)
            written += 1
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit non-zero instead of writing",
    )
    args = parser.parse_args()

    if not os.path.isdir(CANONICALDIR):
        print(f"error: canonical schema dir not found: {CANONICALDIR}", file=sys.stderr)
        sys.exit(2)

    if args.check:
        drift = checkSync()
        if drift:
            print(f"bundled schema mirror is out of sync ({len(drift)} file(s)):")
            for msg in drift:
                print(f"  - {msg}")
            print("run: python scripts/sync_bundled_schemas.py")
            sys.exit(1)
        print("bundled schema mirror is in sync with registry/schema/")
        sys.exit(0)

    written = sync()
    if written:
        print(f"synced {written} schema file(s) into src/gaia_cli/data/registry/schema/")
    else:
        print("bundled schema mirror already in sync; nothing to do")


if __name__ == "__main__":
    main()
