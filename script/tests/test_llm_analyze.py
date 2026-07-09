import pytest

from llm_analyze import load_config, NEW_COLUMNS


@pytest.fixture(autouse=True)
def _clean_llm_env(monkeypatch):
    # load_dotenv 会把变量写入进程级 os.environ，跨用例污染；
    # 每个用例前清理这三个键，保证 load_config 行为可被独立验证。
    for key in ("BASE_URL", "API_KEY", "MODEL"):
        monkeypatch.delenv(key, raising=False)


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


from unittest.mock import MagicMock

from llm_analyze import analyze_article


def _fake_client(content):
    """构造一个返回指定 content 的 mock OpenAI client。"""
    client = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    client.chat.completions.create.return_value = MagicMock(choices=[choice])
    return client


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
    assert analyze_article("t", "a", client=client, model="m", max_retries=1) is None
