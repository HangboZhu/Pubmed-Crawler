# LLM 翻译/总结/创新点 + HTML 阅读视图 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `-t` 从百度翻译切换为调用 `.env` 配置的 DeepSeek（DashScope 兼容模式），对 Q1 文献产出标题翻译/摘要翻译/中文总结/创新点四列，并生成卡片式 HTML 阅读视图。

**Architecture:** 新建 `llm_analyze.py`（配置加载 + 单篇 LLM 分析 + DataFrame 批处理）与 `html_report.py`（Jinja2 渲染自包含 HTML）。`main.py` 的 `-t` 改调 `analyze_df`，写完 xlsx 后调 `generate_html`。百度翻译参数移除，`translator.py` 保留不删。

**Tech Stack:** Python 3.10+、openai SDK、python-dotenv、jinja2、pandas、pytest（dev）。

参考 spec: `docs/superpowers/specs/2026-07-09-llm-translate-html-design.md`

---

## 文件结构

| 文件 | 职责 | 动作 |
|---|---|---|
| `pyproject.toml` | 依赖 | 新增 openai/python-dotenv/jinja2 + dev pytest |
| `.env` | LLM 配置 | 规范为 `KEY=VALUE`，修正 `MODEl→MODEL` |
| `script/llm_analyze.py` | LLM 配置加载、单篇分析、批处理 | 新建 |
| `script/html_report.py` | 卡片式 HTML 渲染 | 新建 |
| `script/main.py` | `-t` 改调 LLM；移除百度参数；生成 HTML | 修改 |
| `script/tests/conftest.py` | 测试 sys.path 注入 | 新建 |
| `script/tests/test_llm_analyze.py` | llm_analyze 测试 | 新建 |
| `script/tests/test_html_report.py` | html_report 测试 | 新建 |

> 说明：`.gitignore` 忽略 `script/test*.py`，但 `script/tests/` 目录下的文件不被匹配，可纳入版本管理。

---

## Task 1: 依赖安装与 .env 规范化

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env`
- Create: `script/tests/conftest.py`

- [ ] **Step 1: 安装运行依赖**

Run:
```bash
uv add openai python-dotenv jinja2
```
Expected: `pyproject.toml` 的 `[project].dependencies` 出现 `openai`、`python-dotenv`、`jinja2`，`uv.lock` 更新。

- [ ] **Step 2: 安装测试依赖**

Run:
```bash
uv add --dev pytest
```
Expected: `pyproject.toml` 出现 `[dependency-groups].dev = ["pytest>=..."]`。

- [ ] **Step 3: 规范 .env 格式**

把 `.env` 内容改为（**保留你现有的 API_KEY 值不变**，仅改分隔符与 key 名）：
```
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
API_KEY=<你现有的 sk-... 保持不变>
MODEL=deepseek-v3.2
```

- [ ] **Step 4: 创建测试 conftest**

Create `script/tests/conftest.py`:
```python
import os
import sys

# 让 tests 能 import script 目录下的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 5: 验证依赖可用**

Run:
```bash
uv run python -c "import openai, dotenv, jinja2; print('ok')"
uv run pytest --version
```
Expected: 打印 `ok` 与 pytest 版本号。

---

## Task 2: llm_analyze.load_config（TDD）

**Files:**
- Create: `script/llm_analyze.py`
- Create: `script/tests/test_llm_analyze.py`

- [ ] **Step 1: 写失败测试**

Create `script/tests/test_llm_analyze.py`:
```python
import pytest

from llm_analyze import load_config, NEW_COLUMNS


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
```

- [ ] **Step 2: 运行测试确认失败**

Run:
```bash
cd script && uv run pytest tests/test_llm_analyze.py -v
```
Expected: FAIL（`ModuleNotFoundError: llm_analyze`）。

- [ ] **Step 3: 写最小实现**

Create `script/llm_analyze.py`:
```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd script && uv run pytest tests/test_llm_analyze.py -v
```
Expected: 3 passed。

- [ ] **Step 5: Commit**

```bash
git add script/llm_analyze.py script/tests/
git commit -m "feat: add llm_analyze config loading"
```

---

## Task 3: llm_analyze.analyze_article（TDD，mock LLM）

**Files:**
- Modify: `script/llm_analyze.py`
- Modify: `script/tests/test_llm_analyze.py`

- [ ] **Step 1: 追加失败测试**

Append to `script/tests/test_llm_analyze.py`:
```python
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
```

- [ ] **Step 2: 运行确认失败**

Run:
```bash
cd script && uv run pytest tests/test_llm_analyze.py -v
```
Expected: 3 个新测试 FAIL（`analyze_article` 未定义）。

- [ ] **Step 3: 实现 analyze_article 与 _build_client**

Append to `script/llm_analyze.py`:
```python
def _build_client():
    """读取配置并构造 OpenAI 兼容 client。"""
    base_url, api_key, model = load_config()
    return OpenAI(base_url=base_url, api_key=api_key), model


def analyze_article(title, abstract, client=None, model=None, max_retries=1):
    """分析单篇文献，返回 dict；失败或空输入返回 None。"""
    if not title or not abstract:
        return None
    if client is None or model is None:
        client, model = _build_client()

    user_msg = USER_PROMPT_TEMPLATE.format(title=title, abstract=abstract)
    last_err = None
    for _ in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            content = resp.choices[0].message.content
            return json.loads(content)
        except Exception as e:  # noqa: BLE001 - 重试并最终降级为 None
            last_err = e
            continue
    print(f"[WARN] 分析失败，跳过: {title[:40]}... | 原因: {last_err}")
    return None
```

- [ ] **Step 4: 运行确认通过**

Run:
```bash
cd script && uv run pytest tests/test_llm_analyze.py -v
```
Expected: 6 passed。

- [ ] **Step 5: Commit**

```bash
git add script/llm_analyze.py script/tests/test_llm_analyze.py
git commit -m "feat: add analyze_article with json parsing and retry"
```

---

## Task 4: llm_analyze.analyze_df（TDD）

**Files:**
- Modify: `script/llm_analyze.py`
- Modify: `script/tests/test_llm_analyze.py`

- [ ] **Step 1: 追加失败测试**

Append to `script/tests/test_llm_analyze.py`:
```python
import pandas as pd

from llm_analyze import analyze_df


def _sample_df():
    return pd.DataFrame({
        "Title": ["T1", "T2", "T3"],
        "Abstract": ["A1", "A2", "A3"],
        "category": ["Q1", "Q2", "Q1"],
    })


def _client_returning(content):
    client = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    client.chat.completions.create.return_value = MagicMock(choices=[choice])
    return client


def test_analyze_df_only_processes_q1():
    client = _client_returning(
        '{"标题翻译":"x","摘要翻译":"y","中文总结":"z","创新点":"w"}'
    )
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
```

- [ ] **Step 2: 运行确认失败**

Run:
```bash
cd script && uv run pytest tests/test_llm_analyze.py -v
```
Expected: 2 个新测试 FAIL（`analyze_df` 未定义）。

- [ ] **Step 3: 实现 analyze_df**

Append to `script/llm_analyze.py`:
```python
def analyze_df(df, client=None, model=None):
    """对 category=='Q1' 的行调用 LLM，填充 4 个新列。"""
    for col in NEW_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    own_client = client is None
    if own_client:
        try:
            client, model = _build_client()
        except RuntimeError as e:
            print(f"[ERROR] 无法加载 LLM 配置，跳过翻译: {e}")
            return df

    if "category" not in df.columns:
        print("[WARN] 缺少 category 列，跳过 LLM 分析。")
        return df

    q1 = df[df["category"] == "Q1"]
    total = len(q1)
    print(f"开始分析 {total} 篇 Q1 文献...")

    for i, (index, row) in enumerate(q1.iterrows(), 1):
        title = row.get("Title", "") or ""
        abstract = row.get("Abstract", "") or ""
        print(f"[{i}/{total}] {title[:50]}")
        result = analyze_article(title, abstract, client=client, model=model)
        for col in NEW_COLUMNS:
            df.at[index, col] = result.get(col, "") if result else ""

    print("LLM 分析完成。")
    return df
```

- [ ] **Step 4: 运行确认通过**

Run:
```bash
cd script && uv run pytest tests/test_llm_analyze.py -v
```
Expected: 8 passed。

- [ ] **Step 5: Commit**

```bash
git add script/llm_analyze.py script/tests/test_llm_analyze.py
git commit -m "feat: add analyze_df for q1 batch processing"
```

---

## Task 5: html_report.generate_html（TDD）

**Files:**
- Create: `script/html_report.py`
- Create: `script/tests/test_html_report.py`

- [ ] **Step 1: 写失败测试**

Create `script/tests/test_html_report.py`:
```python
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
    # 没有 LLM 列时不应报错，且不渲染翻译区块
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
```

- [ ] **Step 2: 运行确认失败**

Run:
```bash
cd script && uv run pytest tests/test_html_report.py -v
```
Expected: FAIL（`html_report` 未定义）。

- [ ] **Step 3: 实现 html_report.py**

Create `script/html_report.py`:
```python
import os

import pandas as pd
from jinja2 import Template

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>文献阅读视图</title>
<style>
:root{--bg:#f5f5f7;--card:#fff;--accent:#2563eb;--text:#1f2937;--muted:#6b7280;--border:#e5e7eb;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}
header{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--border);padding:12px 20px;z-index:10;}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;max-width:920px;margin:0 auto;}
input[type=search]{flex:1;min-width:200px;padding:8px 12px;border:1px solid var(--border);border-radius:8px;font-size:14px;}
button{padding:8px 12px;border:1px solid var(--border);background:var(--card);border-radius:8px;cursor:pointer;font-size:14px;}
button.active{background:var(--accent);color:#fff;border-color:var(--accent);}
.stats{color:var(--muted);font-size:13px;}
.container{max-width:920px;margin:0 auto;padding:20px;}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.04);}
.card h2{margin:0 0 4px;font-size:18px;line-height:1.4;}
.zh-title{color:var(--accent);font-size:15px;margin-bottom:8px;}
.meta{display:flex;gap:6px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin-bottom:12px;}
.meta span{background:var(--bg);padding:2px 8px;border-radius:10px;}
.section{margin-top:12px;}
.section h3{margin:0 0 4px;font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;}
.section p{margin:0;font-size:14px;line-height:1.7;white-space:pre-wrap;word-break:break-word;}
details summary{cursor:pointer;color:var(--muted);font-size:13px;}
.links{margin-top:12px;font-size:13px;}
.links a{color:var(--accent);text-decoration:none;margin-right:12px;}
.empty{text-align:center;color:var(--muted);padding:40px;}
</style>
</head>
<body>
<header>
  <div class="toolbar">
    <input type="search" id="search" placeholder="搜索标题(中英文)...">
    <button id="sort-cite" class="sort-btn">按引用</button>
    <button id="sort-date" class="sort-btn">按日期</button>
    <span class="stats" id="stats"></span>
  </div>
</header>
<div class="container" id="list">
  {% for r in records %}
  <div class="card"
       data-title="{{ ((r.get('Title','') or '') ~ (r.get('标题翻译','') or '')) | lower }}"
       data-cite="{{ r.get('Citation Counts',0) or 0 }}"
       data-date="{{ r.get('Publication Date','') or '' }}">
    <h2>{{ r.get('Title','') or '' }}</h2>
    {% if r.get('标题翻译') %}<div class="zh-title">{{ r['标题翻译'] }}</div>{% endif %}
    <div class="meta">
      {% set jn = r.get('JournalTitle') or r.get('Journal Abbreviation') %}
      {% if jn %}<span>{{ jn }}</span>{% endif %}
      {% if r.get('Publication Date') %}<span>{{ r['Publication Date'] }}</span>{% endif %}
      {% if r.get('Citation Counts') is not none %}<span>引用 {{ r.get('Citation Counts',0) }}</span>{% endif %}
      {% if r.get('category') %}<span>{{ r['category'] }}</span>{% endif %}
      {% if r.get('if_2024') %}<span>IF {{ r['if_2024'] }}</span>{% endif %}
    </div>
    {% if r.get('Abstract') %}
    <div class="section"><details><summary>摘要原文</summary><p>{{ r['Abstract'] }}</p></details></div>
    {% endif %}
    {% if has_llm %}
      {% if r.get('摘要翻译') %}<div class="section"><h3>摘要翻译</h3><p>{{ r['摘要翻译'] }}</p></div>{% endif %}
      {% if r.get('中文总结') %}<div class="section"><h3>中文总结</h3><p>{{ r['中文总结'] }}</p></div>{% endif %}
      {% if r.get('创新点') %}<div class="section"><h3>创新点</h3><p>{{ r['创新点'] }}</p></div>{% endif %}
    {% endif %}
    <div class="links">
      {% if r.get('DOI') %}<a href="https://doi.org/{{ r['DOI'] }}">DOI</a>{% endif %}
      {% if r.get('PMC') %}<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/{{ r['PMC'] }}/">PMC</a>{% endif %}
      {% if r.get('Pubmed Web') %}<a href="{{ r['Pubmed Web'] }}">PubMed</a>{% endif %}
    </div>
  </div>
  {% endfor %}
  {% if not records %}<div class="empty">没有文献</div>{% endif %}
</div>
<script>
const cards = Array.from(document.querySelectorAll('.card'));
const list = document.getElementById('list');
const stats = document.getElementById('stats');
const TOTAL = {{ total }}, Q1 = {{ q1_count }};
let sortKey = null, sortDir = -1;

function apply(){
  const q = document.getElementById('search').value.trim().toLowerCase();
  let visible = cards.filter(c => !q || c.dataset.title.includes(q));
  if(sortKey){
    visible.sort((a,b) => {
      let x = a.dataset[sortKey], y = b.dataset[sortKey];
      if(sortKey === 'cite'){ return ((+x||0) - (+y||0)) * sortDir; }
      return x < y ? -sortDir : (x > y ? sortDir : 0);
    });
  }
  list.innerHTML = '';
  visible.forEach(c => list.appendChild(c));
  stats.textContent = q ? `显示 ${visible.length}/${TOTAL} 篇` : `共 ${TOTAL} 篇 · Q1 ${Q1} 篇`;
}

document.getElementById('search').addEventListener('input', apply);

function bindSort(id, key){
  const btn = document.getElementById(id);
  btn.addEventListener('click', () => {
    document.querySelectorAll('.sort-btn').forEach(x => x.classList.remove('active'));
    if(sortKey === key){ sortDir = -sortDir; } else { sortKey = key; sortDir = -1; }
    btn.classList.add('active');
    apply();
  });
}
bindSort('sort-cite', 'cite');
bindSort('sort-date', 'date');
apply();
</script>
</body>
</html>
"""


def generate_html(df, output_path):
    """把 DataFrame 渲染为卡片式 HTML，返回输出路径。"""
    records = df.to_dict(orient="records")
    has_llm = all(col in df.columns for col in ["标题翻译", "摘要翻译", "中文总结", "创新点"])
    q1_count = int((df["category"] == "Q1").sum()) if "category" in df.columns else 0

    html = Template(HTML_TEMPLATE).render(
        records=records,
        has_llm=has_llm,
        total=len(records),
        q1_count=q1_count,
    )

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
```

- [ ] **Step 4: 运行确认通过**

Run:
```bash
cd script && uv run pytest tests/test_html_report.py -v
```
Expected: 4 passed。

- [ ] **Step 5: Commit**

```bash
git add script/html_report.py script/tests/test_html_report.py
git commit -m "feat: add card-style html report generation"
```

---

## Task 6: main.py 集成

**Files:**
- Modify: `script/main.py`

- [ ] **Step 1: 移除百度翻译参数，-t 改调 analyze_df，生成 HTML**

修改 `script/main.py`：

① 删除 import 中的 `from translator import *`（第 9 行），改为：
```python
from llm_analyze import analyze_df
from html_report import generate_html
```

② 把 `main` 函数签名中的 `appid, appkey, apispeed` 三个参数移除。新签名：
```python
def main(url, translate, output, name, download_dir, error_download_paper, download):
```

③ 把翻译块（原第 64-66 行）替换为：
```python
        # LLM 分析（翻译/总结/创新点）
        if translate:
            df = analyze_df(df)
```

④ 在 `df.to_excel(xlsx_path, index=False)` 与其后 print 之后，追加 HTML 生成：
```python
        # 生成 HTML 阅读视图
        html_path = xlsx_path.replace(".xlsx", ".html")
        generate_html(df, html_path)
        print(f"HTML saved to {html_path}")
```

⑤ 删除 argparse 中的三个百度参数定义（`--appid`、`--appkey`、`--apispeed`）。

⑥ 更新 `main(...)` 调用，移除 appid/appkey/apispeed 实参，新调用：
```python
    main(args.url, args.translate, output, args.name,
         args.download_dir, args.error_download_paper, args.download)
```

- [ ] **Step 2: 验证帮助信息正常**

Run:
```bash
cd script && uv run python main.py -h
```
Expected: 帮助中不再出现 `--appid/--appkey/--apispeed`，仍保留 `-t/-o/--output-folder/-n/-d/--download_dir`。

- [ ] **Step 3: 验证 import 无误**

Run:
```bash
cd script && uv run python -c "import main; print('import ok')"
```
Expected: 打印 `import ok`。

- [ ] **Step 4: 运行全部测试**

Run:
```bash
cd script && uv run pytest -v
```
Expected: 全部 passed。

- [ ] **Step 5: Commit**

```bash
git add script/main.py
git commit -m "feat: switch -t to llm analyze and generate html"
```

---

## Task 7: 端到端冒烟验证

**Files:** 无（仅运行验证）

- [ ] **Step 1: 不带 -t 的冒烟（验证 HTML 基础功能，不耗 API）**

Run:
```bash
cd script && uv run python main.py \
  -u 'https://pubmed.ncbi.nlm.nih.gov/?term=%28%22Virtual+Immunology%22+OR+%22Computational+Immunology%22%29&filter=years.2024-2026&format=abstract' \
  -o smoke_test -n smoke
```
Expected:
- 控制台打印 `Excel saved to ../output/smoke_test/smoke.xlsx` 与 `HTML saved to ../output/smoke_test/smoke.html`。
- 用浏览器打开 `output/smoke_test/smoke.html`，看到卡片列表、搜索框、排序按钮可用（此时无翻译/总结/创新点区块）。

- [ ] **Step 2: 带 -t 的真实验证（消耗 API，需 .env 已配置）**

Run:
```bash
cd script && uv run python main.py \
  -u 'https://pubmed.ncbi.nlm.nih.gov/?term=%28%22Virtual+Immunology%22+OR+%22Computational+Immunology%22%29&filter=years.2024-2026&format=abstract' \
  -o smoke_t -n smoke_t -t
```
Expected:
- 控制台出现 `开始分析 N 篇 Q1 文献...` 与逐篇 `[i/N] ...` 进度。
- xlsx 中 Q1 行出现 `标题翻译/摘要翻译/中文总结/创新点` 四列且有内容。
- HTML 中对应卡片出现「摘要翻译/中文总结/创新点」区块。

- [ ] **Step 3: 清理冒烟产物（可选）**

```bash
rm -rf output/smoke_test output/smoke_t
```

---

## Self-Review 结论

- **Spec 覆盖**：配置加载(T2)、单篇分析+容错(T3)、批处理+Q1 过滤(T4)、HTML 卡片+列缺失自适应(T5)、main 集成+移除旧参数(T6)、端到端(T7)——spec 各节均有对应 task。
- **占位符扫描**：无 TBD/TODO；`.env` 的 `API_KEY` 用「保留现有值」说明（敏感值不在文档落地），属合理处理。
- **类型/命名一致性**：`NEW_COLUMNS`、`load_config`、`analyze_article`、`analyze_df`、`generate_html` 签名在各 task 与 main 调用处一致；列名中文四列全程统一。
