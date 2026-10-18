from atlas.ctfidf import ctfidf_top_terms, topic_keywords, topic_terms


def test_class_specific_terms_rank_first():
    toks = {0: [["rice", "farmer", "study"], ["rice", "yield", "study"]],
            1: [["diabetes", "insulin", "study"], ["diabetes", "glucose", "study"]]}
    top = ctfidf_top_terms(toks, 2)
    assert top[0][0] == "rice" and top[1][0] == "diabetes"
    assert "study" not in top[0] and "study" not in top[1]   # shared by every class → low weight


def test_topic_terms_tokenize_thai():
    texts = {0: ["ข้าวนาปี ผลผลิตข้าวหอมมะลิ", "การปลูกข้าว ของเกษตรกร"], 1: ["ผู้ป่วยเบาหวานและอินซูลิน"] * 2}
    top = topic_terms(texts, top_n=3, max_docs=10, seed=1)
    assert "ข้าว" in top[0] and "เบาหวาน" in top[1]


def test_topic_keywords_keep_phrases():
    kws = {0: ["ผู้สูงอายุ; long-term care", "ผู้สูงอายุ; ผู้ดูแล"], 1: ["เบาหวาน; insulin"]}
    top = topic_keywords(kws, 2)
    assert top[0][0] == "ผู้สูงอายุ"                          # appears twice in class 0
    assert set(top[0]) <= {"ผู้สูงอายุ", "long-term care", "ผู้ดูแล"}
    assert top[1][0] in {"เบาหวาน", "insulin"}


def test_empty_class_gives_empty_list():
    assert ctfidf_top_terms({0: [], 1: [["a"]]}, 3) == {0: [], 1: ["a"]}
