"""Lane B7 round-2 lock scope (M1): two checkouts that share a repository cannot both close one issue on one machine.

The lock is repo-keyed and lives in the user-level lock directory, so two checkouts with two different receipts
stores still serialize. The real-process test runs two interpreters with two checkouts and proves their critical
sections do not overlap.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from gaia_cli.steward.issuehygiene.closure import closureLock, repoIssueLockName, userLockDir

SRC = Path(__file__).resolve().parents[3] / "src"

CHILD = textwrap.dedent('''
    import json, sys, time
    sys.path.insert(0, {src!r})
    from pathlib import Path
    from gaia_cli.steward.issuehygiene.closure import closureLock
    root, tag, repo = sys.argv[1], sys.argv[2], sys.argv[3]
    with closureLock(Path(root) / ".gaia/steward/issue-hygiene/receipts/R.jsonl", "upstream-candidate:o/r:x", 10, repo):
        print(json.dumps({{"tag": tag, "start": time.time()}}), flush=True)
        time.sleep(1.0)
        print(json.dumps({{"tag": tag, "end": time.time()}}), flush=True)
''')


def test_the_user_lock_directory_is_shared_and_keyed_by_repo_and_issue() -> None:
    assert userLockDir() == Path(tempfile.gettempdir()) / "gaia-steward-locks"
    assert repoIssueLockName("Gaia-Research/Gaia-Skill-Tree", 10) == repoIssueLockName("gaia-research/gaia-skill-tree", 10)
    assert repoIssueLockName("gaia-research/gaia-skill-tree", 10) != repoIssueLockName("gaia-research/gaia-skill-tree", 11)


def test_two_checkouts_on_one_machine_never_close_one_issue_at_the_same_time(tmp_path: Path) -> None:
    shared = tmp_path / "shared-tmp"
    shared.mkdir()
    env = {**os.environ, "TMPDIR": str(shared)}
    script = tmp_path / "child.py"
    script.write_text(CHILD.format(src=str(SRC)), encoding="utf-8")
    checkoutA = tmp_path / "checkout-a"
    checkoutB = tmp_path / "checkout-b"
    checkoutA.mkdir()
    checkoutB.mkdir()
    repo = "gaia-research/gaia-skill-tree"
    procs = [subprocess.Popen([sys.executable, str(script), str(root), tag, repo], stdout=subprocess.PIPE,
                              text=True, env=env, cwd=str(tmp_path))
             for root, tag in ((checkoutA, "A"), (checkoutB, "B"))]
    spans = {}
    for proc in procs:
        out, _ = proc.communicate(timeout=60)
        assert proc.returncode == 0, out
        for line in out.splitlines():
            entry = json.loads(line)
            spans.setdefault(entry["tag"], {}).update({k: v for k, v in entry.items() if k != "tag"})
    a, b = spans["A"], spans["B"]
    first, second = (a, b) if a["start"] <= b["start"] else (b, a)
    assert second["start"] >= first["end"] - 0.01, "the two closers overlapped on one repository and issue"


def test_a_lock_held_by_one_closer_blocks_the_same_repository_issue_in_another_checkout(tmp_path: Path) -> None:
    from gaia_cli.steward.issuehygiene.closure import repoIssueLock

    with repoIssueLock("gaia-research/gaia-skill-tree", 10):
        probe = subprocess.run(
            [sys.executable, "-c", textwrap.dedent(f'''
                import fcntl, sys
                sys.path.insert(0, {str(SRC)!r})
                from gaia_cli.steward.issuehygiene.closure import userLockDir, repoIssueLockName
                handle = open(userLockDir() / repoIssueLockName("gaia-research/gaia-skill-tree", 10), "w")
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    print("free")
                except BlockingIOError:
                    print("held")
            ''')], capture_output=True, text=True, env={**os.environ, "TMPDIR": tempfile.gettempdir()}, timeout=60)
    assert probe.stdout.strip() == "held"
