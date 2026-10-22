"""Write tests/fixtures/search_parity.json — atlas.search_index query tokenisation, FNV-1a hashes and shard numbers
for PARITY_QUERIES over a small vocabulary (the index tokens of the 11 real ThaiJO fixture files + EXTRA_VOCAB).

The web twin (web/src/lib/searchTokens.ts, its test) reads the same file, so the Python and TypeScript query
tokenisers cannot drift apart. The fixture is self-describing: tokenizer_version, max_token_chars, index_shards,
docs_per_shard and the stopword list are in it. Run from pipeline/:  uv run python scripts/make_search_parity.py
(tests/test_search_index.py checks that regenerating gives the committed bytes).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from atlas.config import SearchCfg  # noqa: E402
from atlas.search_index import STOPWORDS, TOKENIZER_VERSION, fnv1a32, query_tokens, tokens  # noqa: E402
from atlas.sources.thaijo_md import parse_markdown  # noqa: E402

PIPELINE = Path(__file__).resolve().parents[1]
OUT = PIPELINE / "tests" / "fixtures" / "search_parity.json"
THAIJO = PIPELINE / "tests" / "fixtures" / "thaijo_md"
NIKHAHIT_SARA_AA = "\N{THAI CHARACTER NIKHAHIT}\N{THAI CHARACTER SARA AA}"

EXTRA_VOCAB = ["covid", "2563", "การวิจัย", "วิจัย"]
PARITY_QUERIES = [
    "การอ่านหนังสือพิมพ์รายวัน",
    "ประเทศไทย",
    "การตลาดเพื่อสังคม",
    "อุตสาหกรรมชิ้นส่วนยานยนต์",
    "Marketing Mix",
    "e-commerce adoption",
    "COVID-19 ในประเทศไทย",
    "ศตวรรษที่ ๒๑",
    "นวัตกรรม 2563 ๒๕๖๓",
    "ปัญญาประดิษฐ์",
    "การพัฒนา Competency ของบุคลากร",
    "The Study of Thailand",
    "สมรรถนะxyzการผลิต",
    "ร้านกาแฟอาข่า, อาม่า!",
    "ความตลก",
    "  ,,, - ",
    "จ" + NIKHAHIT_SARA_AA + "อวดหน้าม่าน",
    "GREENPEACE Thailand greenpeace",
    "การวิจัยเชิงคุณภาพ",
    "ณ กรุงเทพฯ",
    "ปัญญาประดิษฐ์กับการตลาด",
    "Café culture",
]
HASHED = ["", "การ", "ประเทศ", "marketing", "2019", "covid", "café", "ร้านกาแฟ", "a"]
ORDINALS = [0, 1, 1999, 2000, 123456]


def vocabulary() -> list[str]:
    vocab: set[str] = set(EXTRA_VOCAB)
    for p in sorted(THAIJO.glob("*.md")):
        r = parse_markdown(p.read_text(encoding="utf-8"), p.name)
        text = "\n".join([r["title_th"], r["title_en"], *r["keywords_th"], *r["keywords_en"]])
        vocab.update(tokens(text))
    return sorted(vocab)


def parity() -> dict:
    cfg = SearchCfg()
    vocab = vocabulary()
    vs = set(vocab)
    queries = []
    for q in PARITY_QUERIES:
        known, unknown = query_tokens(q, vs, cfg.max_token_chars)
        queries.append({"q": q, "known": known, "unknown": unknown})
    return {
        "tokenizer_version": TOKENIZER_VERSION, "max_token_chars": cfg.max_token_chars,
        "index_shards": cfg.index_shards, "docs_per_shard": cfg.docs_per_shard,
        "stopwords": sorted(STOPWORDS), "vocab": vocab, "queries": queries,
        "fnv1a32": [{"s": s, "hash": fnv1a32(s), "shard": fnv1a32(s) % cfg.index_shards} for s in HASHED],
        "doc_shards": [{"ordinal": o, "shard": o // cfg.docs_per_shard} for o in ORDINALS],
    }


def fixture_text() -> str:
    return json.dumps(parity(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    OUT.write_text(fixture_text(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(PARITY_QUERIES)} queries)")
