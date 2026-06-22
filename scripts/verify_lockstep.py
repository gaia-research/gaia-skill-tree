import sys
from pathlib import Path
from gaia_cli.versioning import verify_lockstep

def main():
    try:
        verify_lockstep(Path("."))
        print("Success: all version manifests are in lockstep.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
