import json

import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.topics_time import build_series


def test_series_backfill_guard_and_tables(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    rows, topics = [], []
    for y in range(2019, 2025):
        n = 2 if y == 2024 else 10                         # 2024 incomplete (< 60% of median)
        for i in range(n):
            aid = f"{y}-{i}"
            rows.append({"article_id": aid, "year": y, "journal_name": "jA" if i % 2 else "jB"})
            topics.append({"article_id": aid, "fine_topic": 0 if i < n / 2 else -1})
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    write_table(pd.DataFrame(topics), work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows[::2]], "org_key": "orgX"}),
                work / "01_authors.parquet")
    s = build_series(cfg)
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    assert meta["last_complete_year"] == 2023 and s["year"].max() == 2023
    assert set(s["topic_id"]) == {0}                          # unassigned (-1) never becomes a topic
    assert (s["corpus_total"] == 10).all()                    # ... but counts in the denominator
    assert (s["count"] == 5).all() and (s["count_with_org"] <= s["count"]).all()
    jf = read_table(work / "06_journal_first_year.parquet").set_index("journal")["first_year"]
    assert jf.to_dict() == {"jA": 2019, "jB": 2019}
    assert len(read_table(work / "06_topic_org_year.parquet")) > 0
