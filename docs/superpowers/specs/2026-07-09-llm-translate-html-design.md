# LLM 翻译/总结/创新点 + HTML 阅读视图 设计

- 日期: 2026-07-09
- 状态: 已批准（待实现）

## 1. 背景与目标

现有 `-t` 参数调用百度翻译 API（`translator.py`），仅对 Q1 期刊做标题/摘要的逐句翻译，
产出 `Title_translated` / `Abstract_translated` 两列，结果生硬、缺少提炼。

用户希望：

1. `-t` 改为调用 `.env` 配置的 LLM（阿里云 DashScope 兼容模式 + DeepSeek-v3.2），
   不再使用百度翻译逻辑。
2. LLM 一次性产出每篇文献的：**标题中文翻译、摘要中文翻译、中文总结、创新点**，
   作为新列加入表格。
3. 额外生成一个**卡片式 HTML 阅读视图**，把表格内容以易读的形式呈现。

## 2. 决策摘要

| 维度 | 决策 |
|---|---|
| 处理范围 | 仅 `category == "Q1"` 的行（沿用现有范围，控制成本） |
| 结果分列 | 拆成 4 个独立列，一次 LLM 调用返回 JSON 后拆分 |
| 表格格式 | 保持 `.xlsx`（追加 4 列） |
| 阅读视图 | 自包含卡片式 HTML（CSS/JS 内联，离线可用） |
| 列名语言 | 新增列用中文列名 |
| 旧参数 | 移除 `--appid` / `--appkey` / `--apispeed`（百度翻译专用） |

## 3. 技术方案

### 3.1 LLM 接入
- 使用 `openai` SDK 走 DashScope 的 OpenAI 兼容模式（`.env` 的 `BASE_URL` 即兼容端点）。
- 一次调用，prompt 要求严格返回 JSON，并用 `response_format={"type": "json_object"}` 强制。
- 顺序调用 + 进度打印；单篇失败重试 1 次，仍失败则该行 4 列留空并记 warning。

### 3.2 HTML 生成
- 使用 Jinja2 模板渲染卡片式布局；模板字符串内联在模块中，单文件输出。
- CSS/JS 全部内联到产物 HTML，保证离线打开与可分享。

### 3.3 模块组织
- **新建 `script/llm_analyze.py`**：LLM 配置加载 + 单篇分析 + DataFrame 批处理。
- **新建 `script/html_report.py`**：Jinja2 渲染卡片式 HTML。
- **改 `script/main.py`**：`-t` 改调 `analyze_df`；写完 xlsx 后调 `generate_html`；
  移除百度翻译相关参数与调用。
- **保留 `script/translator.py`**：文件不删除（留作历史/回退），但不再被 `-t` 引用。

## 4. 配置加载（.env）

将现有 `.env` 规范为标准 `KEY=VALUE` 格式（当前为冒号分隔，且 `MODEl` 拼写有误）：

```
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
API_KEY=<保持现有 key 不变>
MODEL=deepseek-v3.2
```

- 用 `python-dotenv` 的 `load_dotenv()` 加载，查找路径向上追溯到项目根。
- 任一 key 缺失 → 打印清晰错误并退出。

## 5. 数据流

```
extract_articles(url)            # pubmed_get.py
  → merge_dataframes(df)         # 合并期刊全称 / JCR 分区 / IF
  → [-t] analyze_df(df)          # 新增 4 列（仅 Q1 行）
  → df.to_excel(xlsx_path)       # 保持现有输出
  → generate_html(df, html_path) # 新增：无论是否 -t 都生成
```

## 6. 新增列定义

仅对 Q1 行填充，非 Q1 行留空：

| 列名 | 内容 |
|---|---|
| 标题翻译 | Title 的中文翻译 |
| 摘要翻译 | Abstract 的中文翻译 |
| 中文总结 | 用中文概括研究内容（方法/结论），3-5 句 |
| 创新点 | 提炼本文的主要创新（条目列表，中文） |

LLM 返回 JSON 结构：
```json
{"标题翻译": "...", "摘要翻译": "...", "中文总结": "...", "创新点": "..."}
```

## 7. HTML 卡片规格

- 每篇一张卡片，自上而下：
  - 英文标题 + 中文标题翻译
  - 元信息条：期刊 · 发表日期 · 引用数 · 分区 · IF
  - 摘要原文（可折叠）
  - 摘要中文翻译
  - 中文总结
  - 创新点
  - 链接：DOI / PMC / PubMed
- 顶部工具栏：标题搜索框（原生 JS 实时过滤）+ 按引用数/日期排序 + 统计（总数 / Q1 数）。
- 未带 `-t` 时，翻译/总结/创新点区块不渲染（列缺失自动隐藏）。
- 产物路径：`output/{project}/{name}.html`（与 xlsx 同目录同名）。

## 8. 错误处理

- `.env` 缺失或 key 无效 → 清晰报错退出。
- LLM 调用异常 / JSON 解析失败 → 重试 1 次 → 仍失败则该行 4 列留空，继续下一篇。
- 无 Q1 文献 → 跳过 LLM，仍生成 HTML（只显示已有信息）。
- 空标题/空摘要 → 跳过该篇 LLM 调用，对应列留空。

## 9. 依赖变更（pyproject.toml）

新增：
- `openai`
- `python-dotenv`
- `jinja2`

移除：无（现有依赖保留）。

## 10. 测试策略

注意 `.gitignore` 忽略 `script/test*.py`，测试文件命名为 `verify_*.py` 以纳入版本管理，
或添加 gitignore 例外。重点验证：
- LLM 返回 JSON 的解析与容错（用 mock，不真实调用）。
- `analyze_df` 的 Q1 过滤与新列填充。
- `generate_html` 的列缺失自适应、搜索/排序标记存在。
- `.env` 加载与缺 key 报错。
