import signal
import sys
from gaia_cli.main import main

if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

if __name__ == "__main__":
    sys.exit(main() or 0)
