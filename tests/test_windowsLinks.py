"""Tests for gaia_cli.windowsLinks.

The default code path (real ``os.symlink``) is exercised on every platform.
The Windows-only fallbacks (junction, hardlink, copy) are exercised by
monkeypatching ``os.symlink`` to raise ``OSError`` and forcing ``sys.platform``
to ``win32`` for that single call. The fallback unit tests are skipped on
non-Windows because they depend on the ``cmd /c mklink /J`` subprocess which
only exists on Windows.
"""

from __future__ import annotations

import os
import sys
import pytest

from gaia_cli import windowsLinks
from gaia_cli.windowsLinks import makeLink, isLinkOrJunction, readLinkTarget
pytestmark = [pytest.mark.integration]



class TestMakeLinkPrimaryPath:
    """The default path: os.symlink succeeds. Works on every platform."""

    def testDirectoryLinkRoundTrip(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        (src / "marker.txt").write_text("hello")

        dst = tmp_path / "linked"
        try:
            mechanism = makeLink(src, dst)
        except OSError:
            # Windows without symlink privilege: skip the primary-path test
            # (the fallback test below covers the Windows behavior).
            pytest.skip("Symlink creation not permitted on this host")

        assert mechanism in {"symlink", "junction"}
        assert isLinkOrJunction(dst)
        assert (dst / "marker.txt").read_text() == "hello"
        assert readLinkTarget(dst) == os.path.realpath(str(src))

    def testFileLinkRoundTrip(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("content")

        dst = tmp_path / "linked.txt"
        try:
            mechanism = makeLink(src, dst)
        except OSError:
            pytest.skip("Symlink creation not permitted on this host")

        assert mechanism in {"symlink", "hardlink", "copy"}
        assert dst.exists()
        assert dst.read_text() == "content"

    def testInferredDirectoryFlag(self, tmp_path):
        """targetIsDirectory is inferred from src when None."""
        src = tmp_path / "src-dir"
        src.mkdir()
        dst = tmp_path / "dst-dir"
        try:
            makeLink(src, dst)
        except OSError:
            pytest.skip("Symlink creation not permitted on this host")
        assert dst.is_dir()


class TestMakeLinkFallbacks:
    """Force ``os.symlink`` to raise so the Windows fallback branches run."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Junctions are Windows-only")
    def testJunctionFallbackForDirectory(self, tmp_path, monkeypatch):
        src = tmp_path / "source"
        src.mkdir()
        (src / "marker.txt").write_text("hi")

        def boom(*args, **kwargs):
            raise OSError("simulated symlink denial")

        monkeypatch.setattr(os, "symlink", boom)

        dst = tmp_path / "junction"
        mechanism = makeLink(src, dst)
        assert mechanism == "junction"
        assert isLinkOrJunction(dst)
        assert (dst / "marker.txt").read_text() == "hi"
        # os.readlink does NOT work on junctions — verify readLinkTarget does.
        assert readLinkTarget(dst) == os.path.realpath(str(src))

    @pytest.mark.skipif(sys.platform != "win32", reason="File fallback uses os.link semantics that vary")
    def testHardlinkOrCopyFallbackForFile(self, tmp_path, monkeypatch):
        src = tmp_path / "source.txt"
        src.write_text("payload")

        def boom(*args, **kwargs):
            raise OSError("simulated symlink denial")

        monkeypatch.setattr(os, "symlink", boom)

        dst = tmp_path / "linked.txt"
        mechanism = makeLink(src, dst)
        assert mechanism in {"hardlink", "copy"}
        assert dst.read_text() == "payload"

    def testLinuxRaisesWhenSymlinkFails(self, tmp_path, monkeypatch):
        """On Linux/macOS the fallback path must NOT execute — OSError propagates."""
        if sys.platform == "win32":
            pytest.skip("This test pins the non-Windows propagation behavior")

        def boom(*args, **kwargs):
            raise OSError("simulated denial")

        monkeypatch.setattr(os, "symlink", boom)

        src = tmp_path / "source"
        src.mkdir()
        dst = tmp_path / "linked"
        with pytest.raises(OSError, match="simulated denial"):
            makeLink(src, dst)


class TestIsLinkOrJunction:
    def testRegularDirectoryReturnsFalse(self, tmp_path):
        d = tmp_path / "real"
        d.mkdir()
        assert isLinkOrJunction(d) is False

    def testRegularFileReturnsFalse(self, tmp_path):
        f = tmp_path / "real.txt"
        f.write_text("x")
        assert isLinkOrJunction(f) is False

    def testNonexistentPathReturnsFalse(self, tmp_path):
        assert isLinkOrJunction(tmp_path / "missing") is False


class TestReadLinkTarget:
    def testResolvesThroughLink(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dst = tmp_path / "dst"
        try:
            makeLink(src, dst)
        except OSError:
            pytest.skip("Link creation not permitted on this host")
        assert readLinkTarget(dst) == os.path.realpath(str(src))
