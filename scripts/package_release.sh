#!/usr/bin/env bash
# package_release.sh — after import_atlas.sh: bundle the published site data (web/dist/data + atlas-offline.html) into
# one zip, ready to put live on GitHub Pages without committing any data to the repo.
#
# การใช้ (จาก root ของ repo, หลัง bash scripts/import_atlas.sh):
#   bash scripts/package_release.sh            → atlas-site-data-<release>.zip ที่ root ของ repo
#   bash scripts/package_release.sh --upload   → และสร้าง GitHub Release "data-<release>" แนบ zip นั้น (ต้องมี gh login)
# จากนั้น: Actions → Pages → Run workflow → ใส่ data_release = data-<release>
# (ดู docs/OPERATIONS.md §21) — สคริปต์ปฏิเสธรอบที่เป็นข้อมูลตัวอย่าง (embedding_provider fixture | lite)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE="$ROOT/web/dist"
[[ -f "$SITE/data/latest.json" ]] || { echo "[package] ไม่พบ $SITE/data/latest.json — รัน bash scripts/import_atlas.sh ก่อน" >&2; exit 1; }

REL="$(node -e "const l=require(process.argv[1]);const m=require(require('path').join(process.argv[2],l.path));if(['fixture','lite'].includes(m.embedding_provider)){console.error('sample');process.exit(2)}console.log(l.release)" "$SITE/data/latest.json" "$SITE/data")" \
  || { echo "[package] รอบใน web/dist/data เป็นข้อมูลตัวอย่าง — ไม่แพ็กขึ้นเว็บจริง" >&2; exit 1; }

ZIP="$ROOT/atlas-site-data-$REL.zip"
rm -f "$ZIP"
( cd "$SITE" && zip -qr "$ZIP" data $( [[ -f atlas-offline.html ]] && echo atlas-offline.html ) )
echo "[package] $ZIP ✓ (รอบ $REL)"

if [[ "${1:-}" == "--upload" ]]; then
  TAG="data-$REL"
  if gh release view "$TAG" >/dev/null 2>&1; then
    gh release upload "$TAG" "$ZIP" --clobber
  else
    gh release create "$TAG" "$ZIP" --title "Atlas data $REL" --notes "ข้อมูลเผยแพร่ของรอบ $REL (data/ + atlas-offline.html) สำหรับ GitHub Pages — ไม่มีชื่อผู้แต่งหรือบทคัดย่อ"
  fi
  echo "[package] อัปโหลดแล้ว → Actions → Pages → Run workflow → data_release = $TAG"
fi
