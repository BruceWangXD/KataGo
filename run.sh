#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python_bin="$(command -v python3 || command -v python)"
if [ "$(uname -s)" = Darwin ]; then
  if ! "$python_bin" -c 'from app import find_katago; find_katago()'; then
    bash setup_macos.sh
  fi
fi
exec "$python_bin" app.py
