#!/bin/sh
# Gaia CLI installer — https://gaia.tiongson.co/install.sh
# Usage: curl -fsSL https://gaia.tiongson.co/install.sh | sh
set -e

PACKAGE="gaia-cli"
MIN_PYTHON=38  # 3.8

# ── Python check ──────────────────────────────────────────────────────────────
PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver=$("$candidate" -c "import sys; print(sys.version_info.major*10+sys.version_info.minor)" 2>/dev/null || true)
    if [ -n "$ver" ] && [ "$ver" -ge "$MIN_PYTHON" ]; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "Error: Python 3.8+ is required."
  echo "Install Python from https://python.org then re-run this script."
  exit 1
fi

# ── Install ───────────────────────────────────────────────────────────────────
# macOS pipx bootstrap support
if [ "$(uname)" = "Darwin" ]; then
  # Ensure setuptools is installed and up-to-date before attempting any pip operations
  echo "Ensuring setuptools is installed..."
  if "$PYTHON" -m pip install --upgrade --user setuptools >/dev/null 2>&1; then
    true
  else
    echo "Warning: Could not upgrade setuptools, continuing anyway..."
  fi

  if ! command -v pipx >/dev/null 2>&1; then
    echo "pipx not found. Attempting to install pipx on macOS..."
    if command -v brew >/dev/null 2>&1; then
      echo "Installing pipx via Homebrew..."
      brew install pipx
    else
      echo "Homebrew not found. Installing pipx via pip..."
      if "$PYTHON" -m pip install --user pipx --break-system-packages >/dev/null 2>&1; then
        echo "Successfully installed pipx."
      elif "$PYTHON" -m pip install --user pipx >/dev/null 2>&1; then
        echo "Successfully installed pipx."
      else
        echo "Warning: Failed to install pipx via pip."
      fi
    fi
  fi
  # Temporarily export common binary directories to PATH for the rest of the script
  export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
  PY_USER_BIN=$("$PYTHON" -c "import sysconfig; print(sysconfig.get_path('scripts', 'posix_user'))" 2>/dev/null || true)
  if [ -n "$PY_USER_BIN" ]; then
    export PATH="$PATH:$PY_USER_BIN"
  fi
fi

if command -v pipx >/dev/null 2>&1; then
  echo "Installing $PACKAGE via pipx..."
  pipx install "$PACKAGE"
else
  echo "Installing $PACKAGE via pip..."
  "$PYTHON" -m pip install --user "$PACKAGE"

  # PATH hint when gaia isn't immediately on PATH after a pip --user install
  if ! command -v gaia >/dev/null 2>&1; then
    USER_BIN=$("$PYTHON" -c "import sysconfig; print(sysconfig.get_path('scripts', 'posix_user'))" 2>/dev/null || true)
    if [ -n "$USER_BIN" ]; then
      echo ""
      echo "  gaia was installed to: $USER_BIN"
      echo "  Add it to your PATH:"
      echo "    export PATH=\"\$PATH:$USER_BIN\""
      echo "  Paste that line into ~/.bashrc or ~/.zshrc to make it permanent."
    fi
  fi
fi

echo ""
echo "Done! Verify with: gaia --version"
