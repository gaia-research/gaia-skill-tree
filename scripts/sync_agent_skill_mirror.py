#!/usr/bin/env python3
"""Sync the Claude agent skill mirror to canonical .agents/skills/.

Project skills are delivered in both ``.agents/skills/`` (canonical,
agent-agnostic) and ``.claude/skills/`` (the Claude Code surface).  CLAUDE.md
requires the two copies to stay byte-identical; in practice a skill added to one
tree and forgotten in the other is the most common repository drift there is.

A small set of paths is locally owned by the mirror and is deliberately neither
compared nor overwritten: the ``skill-creator`` bundle and Python bytecode.

This helper makes the sync mechanical instead of hand-copied, and gives Gaia
Steward's Class A ``agent-skill-mirror`` repair an independent proof command.

Usage:
    python scripts/sync_agent_skill_mirror.py            # copy canonical -> mirror
    python scripts/sync_agent_skill_mirror.py --check     # exit 1 if out of sync (no writes)

``--check`` performs no writes, so you can gate locally before pushing.
"""

import argparse
import filecmp
import fnmatch
import os
import shutil
import sys

REPOROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANONICALDIR = os.path.join(REPOROOT, ".agents", "skills")
MIRRORDIR = os.path.join(REPOROOT, ".claude", "skills")

# Locally owned mirror paths. Keep in lockstep with AGENT_SKILL_MIRROR.ignore in
# src/gaia_cli/steward/mirrors.py; tests/steward/test_repairs.py asserts parity.
IGNORE = ("skill-creator/**", "**/__pycache__/**", "**/*.pyc")


def isIgnored(relative):
    """Return whether one mirror-relative path is locally owned, not mirrored."""
    for pattern in IGNORE:
        if fnmatch.fnmatchcase(relative, pattern):
            return True
        if pattern.endswith("/**") and relative.startswith(pattern[:-3] + "/"):
            return True
    return False


def treeFiles(base):
    """Yield mirrored paths under one tree, relative to it, skipping owned paths."""
    if not os.path.isdir(base):
        return
    for root, _dirs, files in os.walk(base):
        for name in files:
            full = os.path.join(root, name)
            relative = os.path.relpath(full, base).replace(os.sep, "/")
            if isIgnored(relative):
                continue
            yield relative


def checkSync():
    """Return a list of human-readable drift messages (empty when in sync)."""
    drift = []
    canonical = sorted(treeFiles(CANONICALDIR))
    for relative in canonical:
        mirrored = os.path.join(MIRRORDIR, relative)
        if not os.path.isfile(mirrored):
            drift.append(f"missing in mirror: {relative}")
        elif not filecmp.cmp(os.path.join(CANONICALDIR, relative), mirrored, shallow=False):
            drift.append(f"differs from canonical: {relative}")
    known = set(canonical)
    for relative in sorted(treeFiles(MIRRORDIR)):
        if relative not in known:
            drift.append(f"mirror-only path: {relative}")
    return drift


def sync():
    """Copy every canonical skill file into the mirror. Returns count written."""
    written = 0
    for relative in sorted(treeFiles(CANONICALDIR)):
        canonical = os.path.join(CANONICALDIR, relative)
        mirrored = os.path.join(MIRRORDIR, relative)
        os.makedirs(os.path.dirname(mirrored), exist_ok=True)
        if not os.path.isfile(mirrored) or not filecmp.cmp(canonical, mirrored, shallow=False):
            shutil.copy2(canonical, mirrored)
            written += 1
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing; exit 1 when the mirror is stale",
    )
    args = parser.parse_args()

    if not os.path.isdir(CANONICALDIR):
        print(f"canonical skill tree is missing: {CANONICALDIR}", file=sys.stderr)
        return 1

    if args.check:
        drift = checkSync()
        if drift:
            print("agent skill mirror is out of sync:", file=sys.stderr)
            for message in drift:
                print(f"  {message}", file=sys.stderr)
            print(
                "run: python scripts/sync_agent_skill_mirror.py",
                file=sys.stderr,
            )
            return 1
        print("agent skill mirror is in sync")
        return 0

    # A mirror-only path is a deletion decision, not a copy. Refuse it here for
    # the same reason the Steward repair does: the tool cannot tell an
    # intentional Claude-only skill from a stale leftover.
    orphans = [message for message in checkSync() if message.startswith("mirror-only path: ")]
    if orphans:
        print("refusing to sync while the mirror has mirror-only paths:", file=sys.stderr)
        for message in orphans:
            print(f"  {message}", file=sys.stderr)
        return 1

    written = sync()
    print(f"agent skill mirror synced ({written} file(s) written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
