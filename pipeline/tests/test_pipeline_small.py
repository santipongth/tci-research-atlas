import json

from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run


def test_full_pipeline_on_eleven_real_files(make_cfg, thaijo_dir, tmp_path):
    cfg = make_cfg(thaijo_dir)
    cfg["clustering"]["reducer"] = "pca"
    run(cfg, STEPS)
    atlas = json.loads((tmp_path / "out" / "atlas_data.json").read_text(encoding="utf-8"),
                       parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert atlas["meta"]["total_articles"] == 11 and atlas["meta"]["definition_version"] == 2
    em = read_table(tmp_path / "work" / "07_emerging.parquet")
    assert set(em["status"]) == {"LOW_DATA"}               # 11 articles can never support a trend claim
    assert (tmp_path / "state" / "prev" / "centroids.npy").exists()
