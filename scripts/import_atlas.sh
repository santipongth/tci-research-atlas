#!/usr/bin/env bash
# import_atlas.sh — นำ atlas_data.json จาก pipeline เข้าเว็บ แล้ว build
#
# การใช้ (จาก root ของ repo):
#   bash scripts/import_atlas.sh [path/atlas_data.json]   # default: pipeline/output/atlas_data.json
#
# ทำอะไรบ้าง:
#   1. ตรวจว่า JSON มี meta/groups/nodes ครบ (กันไฟล์เพี้ยนหลุดขึ้นเว็บ)
#   2. คัดลอกไป web/public/data/atlas_data.json
#   3. npm install (ถ้ายังไม่มี node_modules) + npm run build
#   4. รายงานสรุป — หลังจบ ให้ deploy/publish ตามช่องทางของหน่วยงาน
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-$ROOT/pipeline/output/atlas_data.json}"
DEST_DIR="$ROOT/web/public/data"
DEST="$DEST_DIR/atlas_data.json"

[[ -f "$SRC" ]] || { echo "ERROR: ไม่พบ $SRC — รัน pipeline ก่อน" >&2; exit 1; }

# --- 1) validate JSON structure ---
(cd "$ROOT/pipeline" && uv run python - "$SRC") <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
missing = [k for k in ("meta", "groups", "nodes") if k not in d]
if missing:
    sys.exit(f"ERROR: atlas_data.json ขาด key: {missing}")
n, g = len(d["nodes"]), len(d["groups"])
print(f"[import] JSON OK — schema {d['meta'].get('schema_version', '1.0')}, definition v{d['meta'].get('definition_version', 1)}, "
      f"{g} groups, {n} nodes, {d['meta'].get('total_articles', 0):,} articles, "
      f"data through {d['meta'].get('last_complete_year', '?')}")
if n == 0:
    sys.exit("ERROR: nodes ว่าง")
PY

# --- 2) copy ---
mkdir -p "$DEST_DIR"
cp "$SRC" "$DEST"
echo "[import] คัดลอก -> web/public/data/atlas_data.json"

# --- 3) build ---
cd "$ROOT/web"
[[ -d node_modules ]] || npm install
npm run build

echo
echo "[import] เสร็จสิ้น ✓"
echo "  - ดูผล local:  cd web && npm run preview"
echo "  - deploy:       อัปโหลด dist/ ขึ้น static host หรือกด publish บน Kimi"
echo "  - หน้าเว็บควรขึ้น badge: ● ข้อมูลสดจาก pipeline"
