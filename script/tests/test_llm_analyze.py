import pandas as pd
import pytest
from unittest.mock import MagicMock

from llm_analyze import load_config, analyze_article, analyze_df, NEW_COLUMNS


@pytest.fixture(autouse=True)
def _clean_llm_env(monkeypatch):
    # load_dotenv 会把变量写入进程级 os.environ，跨用例污染；
    # 每个用例前清理这三个键，保证 load_config 行为可被独立验证。
    for key in ("BASE_URL", "API_KEY", "MODEL"):
        monkeypatch.delenv(key, raising=False)


def _fake_client(content):
    """构造一个返回指定 content 的 mock OpenAI client。"""
    client = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    client.chat.completions.create.return_value = MagicMock(choices=[choice])
    return client


def _sample_df():
    return pd.DataFrame({
        "Title": ["T1", "T2", "T3"],
        "Abstract": ["A1", "A2", "A3"],
        "category": ["Q1", "Q2", "Q1"],
    })


# ---- load_config ----

def test_load_config_success(tmp_path):
    env = tmp_path / ".env"
    env.write_text("BASE_URL=http://x\nAPI_KEY=sk-x\nMODEL=m\n", encoding="utf-8")
    base, key, model = load_config(str(env))
    assert base == "http://x"
    assert key == "sk-x"
    assert model == "m"


def test_load_config_missing_key(tmp_path):
    env = tmp_path / ".env"
    env.write_text("BASE_URL=http://x\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="API_KEY"):
        load_config(str(env))


def test_new_columns_constant():
    assert NEW_COLUMNS == ["标题翻译", "摘要翻译", "中文总结", "创新点"]


# ---- analyze_article ----

def test_analyze_article_parses_json():
    client = _fake_client('{"标题翻译":"T","摘要翻译":"A","中文总结":"S","创新点":"I"}')
    r = analyze_article("Title", "Abstract", client=client, model="m")
    assert r == {"标题翻译": "T", "摘要翻译": "A", "中文总结": "S", "创新点": "I"}


def test_analyze_article_empty_input_returns_none():
    client = _fake_client("{}")
    assert analyze_article("", "abs", client=client, model="m") is None
    assert analyze_article("t", "", client=client, model="m") is None


def test_analyze_article_retry_then_fail_returns_none():
    client = MagicMock()
    client.chat.completions.create.side_effect = Exception("boom")
    # max_retries=1 → 初始 1 次 + 重试 1 次 = 共 2 次调用后返回 None
    assert analyze_article("t", "a", client=client, model="m", max_retries=1) is None
    assert client.chat.completions.create.call_count == 2


def test_analyze_article_retry_then_success():
    # 首次抛异常，重试返回正常 JSON
    client = _fake_client('{"标题翻译":"T","摘要翻译":"A","中文总结":"S","创新点":"I"}')
    client.chat.completions.create.side_effect = [
        Exception("transient"),
        client.chat.completions.create.return_value,
    ]
    r = analyze_article("t", "a", client=client, model="m", max_retries=1)
    assert r == {"标题翻译": "T", "摘要翻译": "A", "中文总结": "S", "创新点": "I"}
    assert client.chat.completions.create.call_count == 2


# ---- analyze_df ----

def test_analyze_df_only_processes_q1():
    client = _fake_client('{"标题翻译":"x","摘要翻译":"y","中文总结":"z","创新点":"w"}')
    df = analyze_df(_sample_df(), client=client, model="m")
    # Q1 行被填充
    assert df.loc[0, "标题翻译"] == "x"
    assert df.loc[2, "中文总结"] == "z"
    # Q2 行保持空
    assert df.loc[1, "标题翻译"] == ""
    # 四列都存在
    for col in NEW_COLUMNS:
        assert col in df.columns


def test_analyze_df_failed_article_leaves_blank():
    client = MagicMock()
    client.chat.completions.create.side_effect = Exception("boom")
    df = analyze_df(_sample_df(), client=client, model="m")
    # Q1 行因失败而留空，但不报错
    assert df.loc[0, "标题翻译"] == ""


def test_analyze_df_skips_when_no_category_column():
    # 缺 category 列时跳过 LLM 分析，不报错，client 从未被调用
    df = pd.DataFrame({"Title": ["T1"], "Abstract": ["A1"]})
    client = MagicMock()
    result = analyze_df(df, client=client, model="m")
    assert client.chat.completions.create.called is False
    for col in NEW_COLUMNS:
        assert col in result.columns
