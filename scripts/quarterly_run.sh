#!/usr/bin/env bash
# quarterly_run.sh — รอบรันรายไตรมาส: profile คลัง → pipeline ทั้งสาย
#   bash scripts/quarterly_run.sh [pipeline/config.yaml]
# อ่าน input.path จาก config (โฟลเดอร์ .md) — ผล profile อยู่ที่ logs/profile_YYYYMMDD.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$(realpath "${1:-$ROOT/pipeline/config.yaml}")"
STAMP="$(date +%Y%m%d)"
mkdir -p "$ROOT/logs"
cd "$ROOT/pipeline"
# the path goes in as an argument (not inside the code string): Git Bash converts /d/... argv for
# native Windows programs, but a path embedded in `python -c "..."` would be read as D:\d\...
CORPUS="$(uv run python - "$CONFIG" <<'PY'
import sys
from atlas.config import load_config
print(load_config(sys.argv[1])["input"]["path"])
PY
)"
uv run atlas profile "$CORPUS" --out "$ROOT/logs/profile_$STAMP.json" --md "$ROOT/logs/profile_$STAMP.md" --workers 4 > /dev/null
echo "[quarterly] profile → logs/profile_$STAMP.md  (ตรวจปี/วารสารที่อัปโหลดย้อนหลังก่อนเชื่อผล)"
uv run atlas run --config "$CONFIG"
echo "[quarterly] เสร็จ → pipeline/output/  ต่อด้วย: bash scripts/import_atlas.sh"
