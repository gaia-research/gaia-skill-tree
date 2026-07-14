import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from check_verifier_signoffs import is_github_remote

def test_is_github_remote():
    assert is_github_remote("https://github.com/o/r.git") is True
    assert is_github_remote("git@github.com:o/r.git") is True
    assert is_github_remote("https://api.github.com/x") is True
    assert is_github_remote("https://github.com.attacker.com/o/r") is False
    assert is_github_remote("https://notgithub.com/o/r") is False
