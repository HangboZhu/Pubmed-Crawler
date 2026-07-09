import os
import json

from dotenv import load_dotenv
from openai import OpenAI

# LLM 产出的 4 个新列名
NEW_COLUMNS = ["标题翻译", "摘要翻译", "中文总结", "创新点"]

SYSTEM_PROMPT = "你是生物医学文献分析助手，必须严格按要求的 JSON 格式输出，不要输出 markdown 代码块或多余文字。"

USER_PROMPT_TEMPLATE = """请分析下面这篇文献，返回**严格的 JSON**（无 markdown、无解释文字），JSON 必须包含且仅包含以下四个键：
- "标题翻译": 标题的中文翻译
- "摘要翻译": 摘要的完整中文翻译
- "中文总结": 用中文概括研究的方法与主要结论，3-5 句
- "创新点": 提炼本文的主要创新点，多条用换行分隔，中文

标题：{title}
摘要：{abstract}
"""


def load_config(env_path=None):
    """从 .env 读取 LLM 配置，返回 (base_url, api_key, model)。"""
    if env_path is None:
        # 从本文件所在目录向上查找项目根的 .env
        current = os.path.dirname(os.path.abspath(__file__))
        for _ in range(3):
            candidate = os.path.join(current, ".env")
            if os.path.exists(candidate):
                env_path = candidate
                break
            current = os.path.dirname(current)
    load_dotenv(env_path)

    base_url = os.getenv("BASE_URL")
    api_key = os.getenv("API_KEY")
    model = os.getenv("MODEL")
    missing = [
        name for name, val in
        [("BASE_URL", base_url), ("API_KEY", api_key), ("MODEL", model)]
        if not val
    ]
    if missing:
        raise RuntimeError(f".env 缺少配置项: {', '.join(missing)}")
    return base_url, api_key, model
