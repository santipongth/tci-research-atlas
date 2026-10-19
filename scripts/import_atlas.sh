#!/usr/bin/env bash
# import_atlas.sh — build web v2 and put the latest validated release on it (data/ + latest.json + offline HTML)
#
# การใช้ (จาก root ของ repo):
#   bash scripts/import_atlas.sh [pipeline/config.yaml]
#
# ทำอะไรบ้าง:
#   1. npm ci (ถ้ายังไม่มี node_modules) + npm run build  → web/dist/ และ web/dist/offline-template.html
#   2. uv run atlas publish --site web/dist                → web/dist/data/<release>/, data/latest.json, atlas-offline.html
#      (publish ตรวจ release ก่อน — ถ้ามี error จะไม่วางอะไรเลย)
#   3. รายงานผล — จากนั้นอัปโหลด web/dist/ ขึ้น static host (รอบถัดไปคัดลอกแค่ data/ ก็พอ)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:-$ROOT/pipeline/config.yaml}"

cd "$ROOT/web"
[[ -d node_modules ]] || npm ci
npm run build

cd "$ROOT/pipeline"
uv run atlas publish -c "$CONFIG" --site "$ROOT/web/dist"

echo
echo "[import] เสร็จสิ้น ✓"
echo "  - ดูผล local:  cd web && node scripts/serve.mjs --site dist   แล้วเปิด http://127.0.0.1:4173/"
echo "  - ไฟล์ออฟไลน์: web/dist/atlas-offline.html (เปิดได้โดยไม่ต่อเน็ต)"
echo "  - deploy:       อัปโหลด web/dist/ ขึ้น static host"
