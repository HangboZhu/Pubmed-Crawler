import os

import pandas as pd

from html_report import generate_html


def _df_without_llm():
    return pd.DataFrame({
        "Title": ["Deep Learning Test"],
        "Journal Abbreviation": ["Nat"],
        "Publication Date": ["2024-03-01"],
        "category": ["Q1"],
        "Citation Counts": [5],
        "if_2024": [50.0],
        "DOI": ["10.1/x"],
        "PMC": [""],
        "Pubmed Web": ["http://pubmed/x"],
    })


def test_generate_html_creates_file(tmp_path):
    out = tmp_path / "r.html"
    generate_html(_df_without_llm(), str(out))
    assert os.path.exists(str(out))
    html = out.read_text(encoding="utf-8")
    assert "Deep Learning Test" in html
    assert "Nat" in html


def test_generate_html_without_llm_columns(tmp_path):
    out = tmp_path / "r.html"
    generate_html(_df_without_llm(), str(out))
    html = out.read_text(encoding="utf-8")
    assert "摘要翻译" not in html


def test_generate_html_with_llm_columns(tmp_path):
    df = _df_without_llm()
    df["标题翻译"] = "深度学习测试"
    df["摘要翻译"] = "翻译内容"
    df["中文总结"] = "总结内容"
    df["创新点"] = "创新内容"
    out = tmp_path / "r.html"
    generate_html(df, str(out))
    html = out.read_text(encoding="utf-8")
    assert "深度学习测试" in html
    assert "创新内容" in html


def test_generate_html_empty_df(tmp_path):
    out = tmp_path / "r.html"
    generate_html(pd.DataFrame(), str(out))
    assert os.path.exists(str(out))
