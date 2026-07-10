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
    # 无 LLM 列时不渲染翻译/总结/创新点区块（JS 导出 cols 里的字符串常量不算）
    assert "<h3>摘要翻译</h3>" not in html
    assert "<h3>创新点</h3>" not in html


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


def test_generate_html_escapes_special_chars(tmp_path):
    df = _df_without_llm()
    df.loc[0, "Abstract"] = "Result: p < 0.05 and A & B group"
    out = tmp_path / "r.html"
    generate_html(df, str(out))
    html = out.read_text(encoding="utf-8")
    assert "p &lt; 0.05" in html
    assert "A &amp; B" in html


def test_generate_html_has_data_category(tmp_path):
    out = tmp_path / "r.html"
    generate_html(_df_without_llm(), str(out))
    html = out.read_text(encoding="utf-8")
    assert 'data-category="Q1"' in html


def test_generate_html_has_quartile_filter(tmp_path):
    out = tmp_path / "r.html"
    generate_html(_df_without_llm(), str(out))
    html = out.read_text(encoding="utf-8")
    assert 'id="quartile-toggle"' in html
    assert 'class="quartile-cb"' in html
    # Q1 复选框带计数
    assert "Q1 (1)" in html


def test_generate_html_uncategorized_option(tmp_path):
    # 含未分类（category 为空）文献时，下拉应出现「未分类」项
    df = pd.DataFrame({"Title": ["A", "B"], "category": ["Q1", None]})
    out = tmp_path / "r.html"
    generate_html(df, str(out))
    html = out.read_text(encoding="utf-8")
    assert "未分类" in html
    # None/NaN → 空 data-category（不能渲染成 "nan"，否则未分类筛选失配）
    assert 'data-category=""' in html
    assert 'data-category="nan"' not in html


def test_generate_html_has_favorite_button(tmp_path):
    out = tmp_path / "r.html"
    generate_html(_df_without_llm(), str(out))
    html = out.read_text(encoding="utf-8")
    assert 'class="fav-btn"' in html


def test_generate_html_has_tabs(tmp_path):
    out = tmp_path / "r.html"
    generate_html(_df_without_llm(), str(out))
    html = out.read_text(encoding="utf-8")
    assert 'id="tab-all"' in html
    assert 'id="tab-fav"' in html


def test_generate_html_links_open_new_tab(tmp_path):
    out = tmp_path / "r.html"
    generate_html(_df_without_llm(), str(out))
    html = out.read_text(encoding="utf-8")
    assert 'target="_blank"' in html
    assert 'rel="noopener"' in html


def test_generate_html_has_stable_data_id(tmp_path):
    # _df_without_llm 无 PMID、有 DOI "10.1/x" → data-id="doi:10.1/x"
    out = tmp_path / "r.html"
    generate_html(_df_without_llm(), str(out))
    html = out.read_text(encoding="utf-8")
    assert 'data-id="doi:10.1/x"' in html


def test_generate_html_embeds_records_for_export(tmp_path):
    out = tmp_path / "r.html"
    generate_html(_df_without_llm(), str(out))
    html = out.read_text(encoding="utf-8")
    assert "const RECORDS" in html
    # 导出按钮
    assert 'id="export-csv"' in html
