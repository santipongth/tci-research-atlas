import pandas as pd

from atlas.export_exec import topic_institutions
from atlas.io_utils import write_table


def test_topic_institutions_link_only_published_institutions(tmp_path):
    write_table(pd.DataFrame({"article_id": ["a1", "a2", "a3"], "inst_key": ["big", "big", "tiny"]}),
                tmp_path / "15_article_institutions.parquet")
    write_table(pd.DataFrame({"inst_key": ["big", "tiny"], "name_th": ["ใหญ่", "เล็ก"], "name_en": ["Big", "Tiny"]}),
                tmp_path / "15_institutions.parquet")
    out = topic_institutions(tmp_path, ["a1", "a2", "a3"], [0, 0, 0], {"big": "inst-big"}, 10)
    # organisations (not people) are named on topic pages; only published ones (≥ min articles) get a page link
    assert [(i.key, i.count, i.id) for i in out[0]] == [("ใหญ่", 2, "inst-big"), ("เล็ก", 1, None)]
