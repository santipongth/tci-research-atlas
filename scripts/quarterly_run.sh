#!/usr/bin/env bash
# quarterly_run.sh — รอบรันรายไตรมาสด้วยคำสั่งเดียว (= uv run atlas quarterly)
#
#   bash scripts/quarterly_run.sh --corpus /data/corpus/2026Q4 --release 2026Q4
#   bash scripts/quarterly_run.sh                      # ใช้ input.path ของ pipeline/config.yaml และไตรมาสของวันนี้
#   bash scripts/quarterly_run.sh --prepare ...        # หยุดหลังตรวจคลัง (ก่อน embedding ครั้งใหญ่ครั้งแรก)
#
# ผล: runs/<release>/ (config, ตรวจคลัง, log, validate, summary.md) และ deploy/<release>/site/ + zip พร้อมอัปโหลด
# คู่มือ: docs/OPERATIONS.md §1
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/pipeline"
exec uv run atlas quarterly "$@"
