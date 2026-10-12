#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export KATAGO_BIN="${KATAGO_BIN:-/workspace/katago-build/katago}"
export KATAGO_MODEL="${KATAGO_MODEL:-/workspace/katago-engine/cpp/tests/models/g170-b6c96-s175395328-d26788732.bin.gz}"
exec python app.py
