"""Phase 4 — LLM topic labeling.

Sends each cluster's top c-TF-IDF terms + representative titles to an
OpenAI-compatible chat model and gets back a strict JSON label
(TH/EN name, one-line description, keywords). Results are cached per
(topic, prompt_hash, model) so reruns cost nothing.

Output: work/05_labels.parquet  (level, topic_id, name_th, name_en, description, keywords)
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from .io_utils import read_table, write_table
from tqdm import tqdm

PROMPT_TEMPLATE = """คุณคือบรรณาธิการวารสารวิชาการไทย ช่วยตั้งชื่อหัวข้อวิจัย (research topic) จากข้อมูลต่อไปนี้

คำสำคัญเด่นของกลุ่ม (c-TF-IDF): {terms}

ตัวอย่างชื่อเรื่องบทความในกลุ่ม:
{titles}

ตอบกลับเป็น JSON เท่านั้น ตาม schema นี้ห้ามมีข้อความอื่น:
{{
  "name_th": "ชื่อหัวข้อภาษาไทย กระชับ ไม่เกิน 8 คำ",
  "name_en": "Concise English topic name, max 6 words",
  "description": "คำอธิบาย 1 บรรทัดว่าหัวข้อนี้ครอบคลุมงานวิจัยแบบไหน",
  "keywords": ["คำสำคัญ", "4-6", "คำ"]
}}"""

SCHEMA_KEYS = ("name_th", "name_en", "description", "keywords")


def _prompt_hash(cfg: dict, model: str) -> str:
    h = hashlib.sha256()
    h.update(PROMPT_TEMPLATE.encode())
    h.update(model.encode())
    h.update(str(cfg["labeling"]["n_repr_titles"]).encode())
    return h.hexdigest()[:12]


def _repr_titles(df: pd.DataFrame, labels: pd.Series, topic_id: int, n: int) -> list[str]:
    sub = df[labels == topic_id]
    # representative = longest abstracts within topic (most informative titles come along)
    sub = sub.assign(_len=sub["abstract"].str.len()).sort_values("_len", ascending=False)
    return sub["title"].head(n).tolist()


def _call_llm(client, model: str, prompt: str, max_retries: int) -> dict:
    delay = 2.0
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            return {k: data.get(k, "" if k != "keywords" else []) for k in SCHEMA_KEYS}
        except Exception as e:  # noqa: BLE001
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def label(cfg: dict, df: pd.DataFrame | None = None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    if df is None:
        df = read_table(work / "02_docs.parquet")
    fine = read_table(work / "04_fine_topics.parquet")
    coarse = read_table(work / "04_coarse_topics.parquet")
    info = read_table(work / "04_topic_info.parquet")

    lcfg = cfg["labeling"]
    if lcfg["provider"] == "off":
        return _fallback_labels(cfg, info, work)

    from openai import OpenAI  # lazy import
    acfg = lcfg["api"]
    api_key = os.environ.get(acfg["api_key_env"], "")
    if not api_key:
        raise EnvironmentError(f"set ${acfg['api_key_env']} for labeling")
    client = OpenAI(base_url=acfg["base_url"], api_key=api_key, timeout=120)
    model = acfg["model"]
    phash = _prompt_hash(cfg, model)

    cache_path = work / "05_labels.parquet"
    cache = read_table(cache_path) if cache_path.exists() else pd.DataFrame(
        columns=["level", "topic_id", "name_th", "name_en", "description", "keywords", "prompt_hash"])

    fine_labels = df["article_id"].map(dict(zip(fine["article_id"], fine["fine_topic"])))
    tasks = []
    for _, row in info.iterrows():
        tid = int(row["topic_id"])
        if ((cache["level"] == "fine") & (cache["topic_id"] == tid) & (cache["prompt_hash"] == phash)).any():
            continue
        titles = _repr_titles(df, fine_labels, tid, lcfg["n_repr_titles"])
        prompt = PROMPT_TEMPLATE.format(
            terms=row["top_terms"],
            titles="\n".join(f"- {t}" for t in titles),
        )
        tasks.append(("fine", tid, prompt))

    print(f"[label] {len(tasks)} topics to label (cached: {len(info) - len(tasks)})")

    def work_one(task):
        level, tid, prompt = task
        d = _call_llm(client, model, prompt, int(acfg.get("max_retries", 5)))
        return {"level": level, "topic_id": tid, **d,
                "keywords": "; ".join(d.get("keywords", [])), "prompt_hash": phash}

    results = []
    with ThreadPoolExecutor(max_workers=int(acfg.get("concurrency", 8))) as ex:
        for r in tqdm(ex.map(work_one, tasks), total=len(tasks), desc="labeling"):
            results.append(r)

    if results:
        cache = pd.concat([cache, pd.DataFrame(results)], ignore_index=True)
        cache = cache.drop_duplicates(subset=["level", "topic_id", "prompt_hash"], keep="last")
        write_table(cache, cache_path)
    print(f"[label] labels -> {cache_path} ({len(cache)} rows)")
    return cache


def _fallback_labels(cfg: dict, info: pd.DataFrame, work: Path) -> pd.DataFrame:
    """No LLM: use top c-TF-IDF terms as the topic name (still fully usable)."""
    rows = []
    for _, r in info.iterrows():
        terms = [t for t in str(r["top_terms"]).split("; ") if t][:3]
        rows.append({
            "level": "fine", "topic_id": int(r["topic_id"]),
            "name_th": " / ".join(terms) or f"หัวข้อ {r['topic_id']}",
            "name_en": " / ".join(terms) or f"Topic {r['topic_id']}",
            "description": "",
            "keywords": "; ".join(terms),
            "prompt_hash": "fallback",
        })
    df = pd.DataFrame(rows)
    write_table(df, work / "05_labels.parquet")
    print(f"[label] provider=off -> term-based labels ({len(df)})")
    return df
