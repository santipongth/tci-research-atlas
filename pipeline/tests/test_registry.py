"""Journal identity from the corpus and the optional registry/journals.csv."""
from pathlib import Path

import pandas as pd
import pytest

from atlas.config import AtlasConfig, load_config
from atlas.registry import (
    REGISTRY_COLUMNS,
    RegistryError,
    journal_code,
    journal_key,
    journal_keys,
    load_registry,
    match_registry,
)

PIPELINE = Path(__file__).resolve().parent.parent


def test_journal_key_comes_from_the_article_id_and_falls_back_to_the_name():
    assert journal_key("so02:BECJournal:74136", "BECJournal") == "so02:BECJournal"
    assert journal_key("file:0a1b2c", "Journal of Things ") == "name:journalofthings"
    assert journal_key("", "") == ""
    df = pd.DataFrame({"article_id": ["so05:jedu:1", "x"], "journal_name": ["jedu", "วารสาร ก"]})
    assert journal_keys(df).tolist() == ["so05:jedu", "name:วารสารก"]


def test_journal_code_is_url_safe_and_stable():
    assert journal_code("so02:BECJournal") == "so02.BECJournal"
    thai = journal_code("name:วารสารก")
    assert thai.startswith("J") and len(thai) == 13 and thai == journal_code("name:วารสารก")
    assert journal_code("so02:a b") != journal_code("so02:a_b")


def test_missing_registry_is_empty(tmp_path):
    df, warns = load_registry(tmp_path / "none.csv")
    assert list(df.columns) == REGISTRY_COLUMNS and df.empty and warns == []
    assert load_registry(None)[0].empty


def test_registry_loads_excel_csv_with_bom_and_optional_columns(tmp_path):
    p = tmp_path / "journals.csv"
    p.write_text("journal_key,name_th,issn,tci_tier\nso02:BECJournal,วารสาร ก,19059566,กลุ่ม 2\nBECX, ,,\n",
                 encoding="utf-8-sig")
    df, warns = load_registry(p)
    row = df.set_index("journal_key").loc["so02:BECJournal"]
    assert row["name_th"] == "วารสาร ก" and row["issn"] == "1905-9566" and int(row["tci_tier"]) == 2
    assert pd.isna(df.set_index("journal_key").loc["BECX", "tci_tier"]) and row["url"] == ""
    assert warns == []


@pytest.mark.parametrize("body, message", [
    ("name_th\nก\n", "journal_key column"),
    ("journal_key,owner\na,b\n", "unknown columns"),
    ("journal_key\na\nb\na\n", "row 4: journal_key 'a' appears more than once"),
])
def test_registry_errors_name_the_problem(tmp_path, body, message):
    p = tmp_path / "j.csv"
    p.write_text(body, encoding="utf-8")
    with pytest.raises(RegistryError, match=message):
        load_registry(p)


def test_a_bad_issn_is_kept_with_a_warning(tmp_path):
    p = tmp_path / "j.csv"
    p.write_text("journal_key,issn\na,12-34\n", encoding="utf-8")
    df, warns = load_registry(p)
    assert df.loc[0, "issn"] == "12-34" and "row 2" in warns[0]


def test_match_on_full_key_or_unique_bare_path():
    reg = pd.DataFrame([{**dict.fromkeys(REGISTRY_COLUMNS, ""), "journal_key": k}
                        for k in ("so02:A", "B", "C", "nowhere")])
    matched, warns = match_registry(["so02:A", "so03:B", "so04:C", "so05:C"], reg)
    assert set(matched) == {"so02:A", "so03:B"}
    assert any("match no journal" in w for w in warns) and any("several servers" in w for w in warns)
    two = pd.DataFrame([{**dict.fromkeys(REGISTRY_COLUMNS, ""), "journal_key": k} for k in ("so03:B", "B")])
    with pytest.raises(RegistryError, match="same journal"):
        match_registry(["so03:B"], two)


def test_example_registry_loads_and_config_resolves_its_path(tmp_path):
    df, warns = load_registry(PIPELINE / "registry" / "journals.example.csv")
    assert len(df) >= 1 and warns == []
    p = tmp_path / "c.yaml"
    p.write_text("journals:\n  registry_path: ./reg/j.csv\n", encoding="utf-8")
    assert Path(load_config(p)["journals"]["registry_path"]) == (tmp_path / "reg" / "j.csv").resolve()
    with pytest.raises(ValueError, match="unknown completeness components"):
        AtlasConfig.model_validate({"journals": {"completeness_weights": {"pages": 1.0}}})


def test_a_tier_outside_1_to_3_is_a_warning_and_a_null_tier(tmp_path):
    p = tmp_path / "j.csv"
    p.write_text("journal_key,tci_tier\na,4\nb,2\n", encoding="utf-8")
    df, warns = load_registry(p)
    by = df.set_index("journal_key")
    assert pd.isna(by.loc["a", "tci_tier"]) and by.loc["b", "tci_tier"] == 2
    assert len(warns) == 1 and "row 2" in warns[0] and "tci_tier" in warns[0]


def test_a_row_with_the_wrong_number_of_fields_names_the_row(tmp_path):
    p = tmp_path / "short.csv"
    p.write_text("journal_key,name_th,issn\na,ก,1234-5678\nb,ข\n", encoding="utf-8")
    with pytest.raises(RegistryError, match=r"short\.csv row 3: 2 fields but the header has 3"):
        load_registry(p)
    long = tmp_path / "long.csv"
    long.write_text("journal_key,name_th\na,ก\nb,ข,extra\n", encoding="utf-8")
    with pytest.raises(RegistryError, match=r"long\.csv.*row 3.*fields"):
        load_registry(long)


def test_an_empty_column_in_the_header_is_an_unknown_column_not_a_shifted_index(tmp_path):
    ok = tmp_path / "ok.csv"
    ok.write_text("journal_key,name_th,\na,ก,\nb,ข,\n", encoding="utf-8")        # Excel-style trailing commas
    with pytest.raises(RegistryError, match="unknown columns"):
        load_registry(ok)


def test_an_unreadable_file_is_a_registry_error_with_a_hint(tmp_path):
    ansi = tmp_path / "ansi.csv"
    ansi.write_bytes("journal_key,name_th\na,วารสาร\n".encode("cp874"))        # Excel "CSV" on a Thai PC
    with pytest.raises(RegistryError, match=r"ansi\.csv.*UTF-8"):
        load_registry(ansi)
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(RegistryError, match=r"empty\.csv.*UTF-8"):
        load_registry(empty)
