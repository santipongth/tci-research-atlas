#!/usr/bin/env python3
"""ตรวจไฟล์ input ก่อนรัน pipeline — เช็คคอลัมน์, ปี, ความยาว abstract, ค่าว่าง

Usage: python scripts/validate_input.py --config config.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlas.config import load_config  # noqa: E402
from atlas.ingest import _read_any  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)

    df = _read_any(cfg["input"]["path"])
    colmap = cfg["input"]["columns"]
    print(f"file: {cfg['input']['path']}  rows: {len(df):,}\n")

    problems = 0
    for canon, src in colmap.items():
        if src not in df.columns:
            print(f"  ✗ column '{src}' (→ {canon}) NOT FOUND")
            problems += 1
    if problems:
        print(f"\n{problems} missing columns — fix config input.columns first")
        sys.exit(1)

    df = df.rename(columns={v: k for k, v in colmap.items()})
    if "year" in df:
        y = df["year"].astype(str).str.extract(r"(\d{4})")[0].astype(float)
        print(f"year range: {int(y.min())}–{int(y.max())}, missing: {y.isna().sum():,}")
    for c in ("title_th", "abstract_th", "keywords_th"):
        if c in df:
            empty = (df[c].astype(str).str.strip() == "").sum()
            print(f"{c}: empty {empty:,} ({empty / len(df) * 100:.1f}%)")
    if "abstract_th" in df:
        med = df["abstract_th"].astype(str).str.len().median()
        print(f"abstract_th median length: {med:.0f} chars "
              f"{'(สั้นมาก — embedding จะพึ่ง title+keywords เป็นหลัก)' if med < 200 else ''}")
    if "journal_name" in df:
        print(f"journals: {df['journal_name'].nunique():,}")
    print("\nOK — พร้อมรัน pipeline")
    print("หมายเหตุ: ถ้า abstract ว่าง >40% ให้พิจารณา scrape เพิ่ม หรือยอมรับว่า topic จะหยาบกว่าปกติ")


if __name__ == "__main__":
    main()
