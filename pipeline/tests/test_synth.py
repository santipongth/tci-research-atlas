import pandas as pd

from atlas.ingest import read_thaijo_corpus
from atlas.synth import NEW_JOURNAL, TOPICS, YEARS, generate, yearly_counts


def test_yearly_counts_shape_and_total():
    c = yearly_counts(20_000, seed=7)
    assert abs(c["count"].sum() - 20_000) / 20_000 < 0.02
    em = c[c.topic == "genai_edu"].set_index("year")["count"]
    assert em[2024] > em[2023] > em[2022] > em[2019]
    conf = c[c.topic == "buddhist_media"].set_index("year")["count"]
    assert conf[[y for y in YEARS if y < 2022]].sum() == 0
    dec = c[c.topic == "print_media"].set_index("year")["count"]
    assert dec[2024] < dec[2023] < dec[2022] < dec[2019]


def test_generate_writes_parseable_corpus(tmp_path):
    truth = generate(tmp_path, n=600, seed=3)
    assert (tmp_path / "_truth.csv").exists()
    assert set(truth["role"]) >= {"stable", "hot", "declining"}
    recs = read_thaijo_corpus(tmp_path)
    parsed = pd.DataFrame(recs).drop_duplicates("article_id").set_index("article_id")
    t = truth.set_index("article_id")
    assert set(parsed.index) == set(t.index)
    assert (parsed.loc[t.index, "year"].astype(int) == t["year"]).all()     # 1970 dates recovered from DOI
    assert parsed["authors"].map(len).min() >= 1


def test_confound_topic_uses_only_new_journal(tmp_path):
    truth = generate(tmp_path, n=4000, seed=1)
    conf = truth[truth.role == "confound"]
    assert len(conf) > 0 and set(conf.journal) == {NEW_JOURNAL} and conf.year.min() >= 2022


def test_topics_have_six_terms_each():
    for _key, _role, th, en in TOPICS:
        assert len(th) == 6 and len(en) == 6


def test_dois_are_unique(tmp_path):
    generate(tmp_path, n=3000, seed=2)
    dois = [r["doi"] for r in read_thaijo_corpus(tmp_path) if r["doi"] and "_dup" not in r["source_path"]]
    assert len(dois) == len(set(dois))


def test_ingest_loses_no_synthetic_article(make_cfg, tmp_path):
    from atlas.ingest import ingest

    corpus = tmp_path / "synth"
    generate(corpus, n=3000, seed=2)
    originals = [p for p in corpus.glob("*.md") if "_dup" not in p.name]
    df = ingest(make_cfg(corpus))
    assert len(df) == len(originals)                 # dedup removes exactly the planted _dup copies
