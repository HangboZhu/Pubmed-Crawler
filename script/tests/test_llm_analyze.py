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
