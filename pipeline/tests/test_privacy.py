"""atlas.privacy: e-mail / ORCID anywhere, author names inside organisation strings."""
import json
from pathlib import Path

import pandas as pd

from atlas.io_utils import write_table
from atlas.privacy import contains_name, scan_release


def _release(tmp_path: Path, inst_name: str, topic_inst: str = "มหาวิทยาลัยนเรศวร", extra: str = "") -> Path:
    root = tmp_path / "2026Q4"
    (root / "topics").mkdir(parents=True)
    (root / "institutions.json").write_text(json.dumps({"institutions": [{"name_th": inst_name}]}), encoding="utf-8")
    (root / "topics" / "T000001.json").write_text(
        json.dumps({"institutions": [{"key": topic_inst, "count": 3}], "title": extra}), encoding="utf-8")
    return root


def _work(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    write_table(pd.DataFrame({"article_id": ["a", "b"], "name": ["สมชาย ใจดี", None],
                              "name_en": ["Somchai Jaidee", "Anan Example"]}), work / "01_authors.parquet")
    return work


def test_a_clean_release_passes(tmp_path):
    assert scan_release(_release(tmp_path, "มหาวิทยาลัยเชียงใหม่"), _work(tmp_path)) == []


def test_an_author_name_inside_an_organisation_string_is_an_error(tmp_path):
    root = _release(tmp_path, "Somchai Jaidee Mahidol University")
    errs = scan_release(root, _work(tmp_path))
    assert len(errs) == 1 and "institutions.json" in errs[0] and "author's full name" in errs[0]
    errs = scan_release(_release(tmp_path / "b", "มหาวิทยาลัยมหิดล", topic_inst="สมชาย ใจดี มหาวิทยาลัยมหิดล"),
                        _work(tmp_path))
    assert any("topics/T000001.json" in e for e in errs)


def test_emails_and_orcid_are_errors_without_a_work_dir(tmp_path):
    root = _release(tmp_path, "x", extra="write to somchai@example.org")
    (root / "journals.json").write_text('{"orcid": "0000-0002-1825-0097"}', encoding="utf-8")
    errs = scan_release(root, None)
    assert any("e-mail" in e for e in errs) and any("ORCID" in e for e in errs)


def test_name_matching_ignores_case_spacing_and_tone_marks():
    names = {"somchaijaidee"}
    assert contains_name("Dr. SOMCHAI  Jaidee, Mahidol University", names)
    assert not contains_name("Somchai University", names)
