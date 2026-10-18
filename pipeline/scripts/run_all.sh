#!/usr/bin/env bash
# run_all.sh — รัน pipeline ทั้งสาย (เทียบเท่า uv run atlas run)
#   bash scripts/run_all.sh [config.yaml]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
uv run atlas run --config "${1:-config.yaml}"
