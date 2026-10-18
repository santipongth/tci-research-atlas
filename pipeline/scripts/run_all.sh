#!/usr/bin/env bash
# รัน pipeline ทั้งสายแบบกันลืม — ใช้: bash scripts/run_all.sh [path/to/config.yaml]
set -euo pipefail
cd "$(dirname "$0")/.."
CFG="${1:-config.yaml}"

if [ ! -f "$CFG" ]; then
  echo "ไม่พบ $CFG — สร้างจาก config.example.yaml ก่อน: cp config.example.yaml config.yaml" >&2
  exit 1
fi

echo "[1/2] validate input"
python scripts/validate_input.py --config "$CFG"

echo "[2/2] run pipeline"
python -m atlas.pipeline --config "$CFG"

echo "done → ดูผลใน output/ (atlas_data.json, topics.csv, emerging.csv, forecasts.csv)"
