"""Topic labeling.

LLM mode: author keywords + c-TF-IDF words + representative titles (nearest to the
centroid, diversified with MMR) → strict JSON (TH/EN name, description, keywords).
The cache key is a hash of the exact prompt + model, stored in state_dir — so a topic is
re-labelled only when its content changes (v1 keyed by topic_id, which silently swapped
names after re-clustering). Master prompt text: prompts/topic_label.th.md (keep in sync).

Off mode: names from the topic's most distinctive author keywords (TH and EN).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.thai import thai_ratio

PROMPT_TEMPLATE = """คุณคือบรรณาธิการวารสารวิชาการไทย ช่วยตั้งชื่อหัวข้อวิจัย (research topic) จากข้อมูลต่อไปนี้

คำสำคัญที่ผู้เขียนใช้บ่อยในกลุ่มนี้: {keywords}
คำเด่นจากเนื้อหา (c-TF-IDF): {terms}

ตัวอย่างชื่อเรื่องบทความที่เป็นตัวแทนของกลุ่ม:
{titles}

ตอบกลับเป็น JSON เท่านั้น ตาม schema นี้ ห้ามมีข้อความอื่น:
{{
  "name_th": "ชื่อหัวข้อภาษาไทย กระชับ ไม่เกิน 8 คำ",
  "name_en": "Concise English topic name, max 6 words",
  "description": "คำอธิบาย 1 บรรทัดว่าหัวข้อนี้ครอบคลุมงานวิจัยแบบไหน",
  "keywords": ["คำสำคัญ", "4-6", "คำ"]
}}"""
LABEL_COLUMNS = ["level", "topic_id", "name_th", "name_en", "description", "keywords", "cache_key"]
CACHE_COLUMNS = ["cache_key", "name_th", "name_en", "description", "keywords"]


def representative_indices(member_emb: np.ndarray, centroid: np.ndarray, n: int, lam: float) -> list[int]:
    """Maximal Marginal Relevance: close to the centroid, but not near-duplicates of each other."""
    sims = member_emb @ centroid
    chosen = [int(np.argmax(sims))]
    while len(chosen) < min(n, len(member_emb)):
        redundancy = (member_emb @ member_emb[chosen].T).max(axis=1)
        score = lam * sims - (1 - lam) * redundancy
        score[chosen] = -np.inf
        chosen.append(int(np.argmax(score)))
    return chosen


def _cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}\n{prompt}".encode()).hexdigest()[:16]


def _call_llm(client, model: str, prompt: str, temperature: float, max_retries: int) -> dict:
    delay = 2.0
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model, temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            kws = data.get("keywords", [])
            return {"name_th": str(data.get("name_th", "")), "name_en": str(data.get("name_en", "")),
                    "description": str(data.get("description", "")),
                    "keywords": "; ".join(kws) if isinstance(kws, list) else str(kws)}
        except Exception:  # noqa: BLE001 — retry transport/JSON errors
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def _fallback(top_keywords: str, top_terms: str, tid: int) -> dict:
    kws = [k for k in str(top_keywords).split("; ") if k]
    terms = [t for t in str(top_terms).split("; ") if t]
    th = [k for k in kws if thai_ratio(k) > 0.5][:2] or [t for t in terms if thai_ratio(t) > 0.5][:3]
    en = [k for k in kws if thai_ratio(k) <= 0.5][:2] or [t for t in terms if thai_ratio(t) <= 0.5][:3]
    return {"name_th": " / ".join(th) or f"หัวข้อ {tid}", "name_en": " / ".join(en) or f"Topic {tid}",
            "description": "", "keywords": "; ".join(kws[:6])}


def label(cfg: dict, client=None) -> pd.DataFrame:
    work, state = Path(cfg["pipeline"]["work_dir"]), Path(cfg["pipeline"]["state_dir"])
    info = read_table(work / "04_topic_info.parquet")
    lcfg = cfg["labeling"]

    if lcfg["provider"] == "off" and client is None:
        out = pd.DataFrame([{"level": "fine", "topic_id": int(r.topic_id),
                             **_fallback(r.top_keywords, r.top_terms, int(r.topic_id)), "cache_key": "fallback"}
                            for r in info.itertuples()], columns=LABEL_COLUMNS)
        write_table(out, work / "05_labels.parquet")
        print(f"[label] provider=off → keyword-based labels for {len(out)} topics")
        return out

    df = read_table(work / "02_docs.parquet")
    labels = (df[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id", how="left")
              ["fine_topic"].fillna(-1).astype(int).to_numpy())
    emb = np.load(work / "03_embeddings.npy")
    C = np.load(work / "04_centroids.npy")
    pos = {t: i for i, t in enumerate(json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8")))}
    acfg = lcfg["api"]
    model = acfg["model"]

    prompts: dict[int, tuple[str, str]] = {}
    for r in info.itertuples():
        tid = int(r.topic_id)
        members = np.where(labels == tid)[0]
        idx = representative_indices(emb[members], C[pos[tid]], int(lcfg["n_repr_docs"]), float(lcfg["mmr_lambda"]))
        titles = "\n".join(f"- {t}" for t in df["title"].iloc[members[idx]])
        prompt = PROMPT_TEMPLATE.format(keywords=r.top_keywords, terms=r.top_terms, titles=titles)
        prompts[tid] = (_cache_key(model, prompt), prompt)

    cache_path = state / "label_cache.parquet"
    try:
        cache = read_table(cache_path)
    except FileNotFoundError:
        cache = pd.DataFrame(columns=CACHE_COLUMNS)
    known = set(cache["cache_key"])
    todo = [(k, p) for k, p in dict(prompts.values()).items() if k not in known]
    print(f"[label] {len(todo)} topics to label, {len(prompts) - len(todo)} from cache")
    if todo:
        if client is None:
            from openai import OpenAI  # optional dependency

            api_key = os.environ.get(acfg["api_key_env"], "")
            if not api_key:
                raise OSError(f"set ${acfg['api_key_env']} for labeling.provider=api")
            client = OpenAI(base_url=acfg["base_url"], api_key=api_key, timeout=120)

        def one(item):
            key, prompt = item
            return {"cache_key": key, **_call_llm(client, model, prompt, float(acfg["temperature"]),
                                                  int(acfg["max_retries"]))}

        with ThreadPoolExecutor(max_workers=int(acfg["concurrency"])) as ex:
            new = list(ex.map(one, todo))
        cache = pd.concat([cache, pd.DataFrame(new, columns=CACHE_COLUMNS)], ignore_index=True)
        write_table(cache.drop_duplicates("cache_key", keep="last"), cache_path)

    by_key = cache.drop_duplicates("cache_key", keep="last").set_index("cache_key")
    out = pd.DataFrame([{"level": "fine", "topic_id": tid, **by_key.loc[key, CACHE_COLUMNS[1:]].to_dict(),
                         "cache_key": key} for tid, (key, _) in sorted(prompts.items())], columns=LABEL_COLUMNS)
    write_table(out, work / "05_labels.parquet")
    return out
