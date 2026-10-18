#!/usr/bin/env bash
# quarterly_run.sh — รัน pipeline ครบทุกขั้นสำหรับรอบไตรมาส
#
# การใช้:
#   bash scripts/quarterly_run.sh [path/ไฟล์ export จาก TCI]
#
# ทำอะไรบ้าง:
#   1. (ถ้าระบุไฟล์) คัดลอกไฟล์ export ไปที่ pipeline/data/tci_articles.csv
#   2. validate input ก่อนเสียงบ API
#   3. รัน pipeline ทั้งสาย
#   4. เก็บสำเนาผลลัพธ์ลง runs/<ปี>Q<ไตรมาส>/
#
# หมายเหตุ: ต้องตั้ง ATLAS_API_KEY ไว้ใน environment ถ้าใช้โหมด api
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIPE="$ROOT/pipeline"
INPUT_FILE="${1:-}"

cd "$PIPE"

# --- 1) รับไฟล์ export ใหม่ (ถ้ามี) ---
if [[ -n "$INPUT_FILE" ]]; then
  if [[ ! -f "$INPUT_FILE" ]]; then
    echo "ERROR: ไม่พบไฟล์ $INPUT_FILE" >&2; exit 1
  fi
  mkdir -p data
  cp "$INPUT_FILE" data/tci_articles.csv
  echo "[quarterly] คัดลอก $INPUT_FILE -> pipeline/data/tci_articles.csv"
  echo "[quarterly] ตรวจว่า config.yaml: input.path ชี้มาที่ไฟล์นี้"
fi

# --- 2) activate venv ถ้ามี ---
if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

CONFIG="config.yaml"
[[ -f "$CONFIG" ]] || CONFIG="config.example.yaml"

# --- 3) validate ---
python scripts/validate_input.py --config "$CONFIG"

# --- 4) run ทั้งสาย ---
python -m atlas.pipeline --config "$CONFIG"

# --- 5) เก็บสำเนารอบรัน ---
Q=$(( (10#$(date +%m) - 1) / 3 + 1 ))
RUN_DIR="$ROOT/runs/$(date +%Y)Q${Q}"
mkdir -p "$RUN_DIR"
cp -f output/* "$RUN_DIR/" 2>/dev/null || true
echo "[quarterly] เก็บสำเนาผลลัพธ์ -> $RUN_DIR"
echo "[quarterly] เสร็จสิ้น — ขั้นต่อไป: bash scripts/import_atlas.sh"
