import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gaia_cli.versioning import verify_lockstep  # noqa: E402

def main():
    try:
        verify_lockstep(Path("."))
        print("Success: all version manifests are in lockstep.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
