import json

import pytest

from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run


def test_full_pipeline_on_eleven_real_files(make_cfg, thaijo_dir, tmp_path):
    cfg = make_cfg(thaijo_dir)
    cfg["clustering"]["reducer"] = "pca"
    run(cfg, STEPS)
    atlas = json.loads((tmp_path / "out" / "atlas_data.json").read_text(encoding="utf-8"),
                       parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert atlas["meta"]["total_articles"] == 11 and atlas["meta"]["definition_version"] == 3
    em = read_table(tmp_path / "work" / "07_emerging.parquet")
    assert set(em["status"]) == {"LOW_DATA"}               # 11 articles can never support a trend claim
    assert (tmp_path / "state" / "prev" / "centroids.npy").exists()


@pytest.mark.slow
def test_umap_on_eleven_real_files_never_publishes_separation_nonsense(make_cfg, thaijo_dir, tmp_path):
    # this config produced 4 topics and crashed (OverflowError) / published growth ~1e7 before v3
    cfg = make_cfg(thaijo_dir)
    cfg["clustering"].update(reducer="umap", n_groups=2)
    cfg["clustering"]["fine"].update(umap_n_components=2, umap_n_neighbors=4, hdbscan_min_cluster_size=2,
                                     hdbscan_min_samples=1)
    run(cfg, STEPS)
    em = read_table(tmp_path / "work" / "07_emerging.parquet")
    assert len(em) >= 2
    assert set(em["status"]) == {"LOW_DATA"}
    assert not (em["share_growth"].abs() > 1e3).any()
    json.loads((tmp_path / "out" / "atlas_data.json").read_text(encoding="utf-8"),
               parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
