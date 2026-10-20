from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward.primitives import (
    SensorUnavailable,
    finding_payload,
    parse_python,
    read_text_bounded,
    tracked_files,
)
from tests.steward.sensor_fixtures import make_repo


def test_tracked_files_uses_git_inventory_not_filesystem(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"src/a.py": "x = 1\n", "src/b.txt": "b"})
    (root / "src" / "untracked.py").write_text("y = 2\n", encoding="utf-8")
    assert tracked_files(root, ["src"], suffixes=[".py"]) == ["src/a.py"]


def test_tracked_files_excludes_prefixes(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"src/a.py": "", "src/vendor/b.py": ""})
    assert tracked_files(root, ["src"], exclude=["src/vendor"]) == ["src/a.py"]


def test_truncated_inventory_is_unavailable_not_partial(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {f"src/{i}.py": "" for i in range(5)})
    with pytest.raises(SensorUnavailable, match="exceeds the bounded limit"):
        tracked_files(root, ["src"], max_files=3)


def test_empty_required_inventory_is_unavailable(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x"})
    with pytest.raises(SensorUnavailable, match="required inventory is empty"):
        tracked_files(root, ["src"])
    assert tracked_files(root, ["src"], require_any=False) == []


def test_non_git_root_is_unavailable(tmp_path: Path) -> None:
    (tmp_path / "plain").mkdir()
    with pytest.raises(SensorUnavailable):
        tracked_files(tmp_path / "plain", ["src"])


def test_missing_root_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(SensorUnavailable):
        tracked_files(tmp_path / "absent", ["src"])


def test_read_text_bounded_refuses_oversized_and_binary(tmp_path: Path) -> None:
    big = tmp_path / "big.txt"
    big.write_text("x" * 100, encoding="utf-8")
    with pytest.raises(SensorUnavailable, match="read limit"):
        read_text_bounded(big, limit=10)
    binary = tmp_path / "bin.txt"
    binary.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(SensorUnavailable, match="not UTF-8"):
        read_text_bounded(binary)


def test_parse_python_reports_syntax_error_as_finding(tmp_path: Path) -> None:
    good = tmp_path / "good.py"
    good.write_text("x = 1\n", encoding="utf-8")
    bad = tmp_path / "bad.py"
    bad.write_text("def (:\n", encoding="utf-8")
    assert parse_python(good)[1] is None
    tree, error = parse_python(bad)
    assert tree is None and error and error.startswith("SyntaxError")


def test_finding_payload_counts_everything_and_caps_display() -> None:
    payload = finding_payload(list(range(25)), cap=20)
    assert payload == {"findingCount": 25, "findings": list(range(20)), "findingsCapped": True}
    assert finding_payload([1])["findingsCapped"] is False
