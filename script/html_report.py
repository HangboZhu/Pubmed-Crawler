import os

import pandas as pd
from jinja2 import Template

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>文献阅读视图</title>
<style>
:root{--bg:#f5f5f7;--card:#fff;--accent:#2563eb;--text:#1f2937;--muted:#6b7280;--border:#e5e7eb;--fav:#f59e0b;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}
header{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--border);padding:12px 20px;z-index:10;}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;max-width:920px;margin:0 auto;}
input[type=search]{flex:1;min-width:200px;padding:8px 12px;border:1px solid var(--border);border-radius:8px;font-size:14px;}
button{padding:8px 12px;border:1px solid var(--border);background:var(--card);border-radius:8px;cursor:pointer;font-size:14px;}
button.active{background:var(--accent);color:#fff;border-color:var(--accent);}
.stats{color:var(--muted);font-size:13px;}
.tabs{display:flex;gap:6px;align-items:center;max-width:920px;margin:12px auto 0;}
.tab{padding:6px 14px;border:1px solid var(--border);background:var(--card);border-radius:8px;cursor:pointer;font-size:14px;}
.tab.active{background:var(--accent);color:#fff;border-color:var(--accent);}
.export-btn{margin-left:auto;color:var(--accent);border-color:var(--accent);}
.container{max-width:920px;margin:0 auto;padding:20px;}
.card{position:relative;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.04);}
.fav-btn{position:absolute;top:12px;right:12px;background:none;border:none;cursor:pointer;font-size:22px;line-height:1;color:#d1d5db;padding:4px;}
.fav-btn:hover{color:var(--fav);}
.fav-btn.active{color:var(--fav);}
.card h2{margin:0 0 4px;font-size:18px;line-height:1.4;padding-right:36px;}
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
.dropdown{position:relative;}
.dropdown-menu{display:none;position:absolute;top:calc(100% + 4px);right:0;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px;min-width:170px;box-shadow:0 4px 12px rgba(0,0,0,.12);z-index:20;}
.dropdown-menu.open{display:block;}
.dropdown-actions{display:flex;justify-content:space-between;gap:8px;margin-bottom:6px;padding-bottom:6px;border-bottom:1px solid var(--border);font-size:12px;}
.dropdown-actions a{color:var(--accent);text-decoration:none;cursor:pointer;}
.dropdown-item{display:flex;align-items:center;gap:6px;padding:4px;font-size:13px;cursor:pointer;}
.dropdown-item input{margin:0;}
</style>
</head>
<body>
<header>
  <div class="toolbar">
    <input type="search" id="search" placeholder="搜索标题(中英文)...">
    <button id="sort-cite" class="sort-btn">按引用</button>
    <button id="sort-date" class="sort-btn">按日期</button>
    {% if quartiles %}
    <div class="dropdown">
      <button id="quartile-toggle" class="sort-btn">按分区 ▾</button>
      <div id="quartile-menu" class="dropdown-menu">
        <div class="dropdown-actions">
          <a href="#" id="quartile-all">全选</a>
          <a href="#" id="quartile-none">清空</a>
        </div>
        {% for q in quartiles %}
        <label class="dropdown-item">
          <input type="checkbox" class="quartile-cb"
                 data-key="{{ '' if q.uncategorized else q.name }}" checked>
          <span>{{ q.name }} ({{ q.count }})</span>
        </label>
        {% endfor %}
      </div>
    </div>
    {% endif %}
    <span class="stats" id="stats"></span>
  </div>
  <div class="tabs">
    <button class="tab active" id="tab-all">全部</button>
    <button class="tab" id="tab-fav">收藏 (<span id="fav-count">0</span>)</button>
    <button class="export-btn" id="export-csv">⬇ 导出收藏 CSV</button>
  </div>
</header>
<div class="container" id="list">
  {% for r in records %}
  <div class="card"
       data-id="{{ r._id }}"
       data-title="{{ ((r.get('Title','') or '') ~ (r.get('标题翻译','') or '')) | lower }}"
       data-cite="{{ r.get('Citation Counts',0) or 0 }}"
       data-date="{{ r.get('Publication Date','') or '' }}"
       data-category="{{ r.get('category','') or '' }}">
    <button class="fav-btn" data-id="{{ r._id }}" title="收藏/取消收藏">☆</button>
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
      {% if r.get('DOI') %}<a href="https://doi.org/{{ r['DOI'] }}" target="_blank" rel="noopener">DOI</a>{% endif %}
      {% if r.get('PMC') %}<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/{{ r['PMC'] }}/" target="_blank" rel="noopener">PMC</a>{% endif %}
      {% if r.get('Pubmed Web') %}<a href="{{ r['Pubmed Web'] }}" target="_blank" rel="noopener">PubMed</a>{% endif %}
    </div>
  </div>
  {% endfor %}
  {% if not records %}<div class="empty">没有文献</div>{% endif %}
</div>
<script>
// 嵌入完整记录，供「导出收藏 CSV」使用
const RECORDS = {{ records|tojson }};
const FAV_KEY = 'pubmed_favorites';
let favorites = new Set(JSON.parse(localStorage.getItem(FAV_KEY) || '[]'));
let currentTab = 'all';

const cards = Array.from(document.querySelectorAll('.card'));
const list = document.getElementById('list');
const stats = document.getElementById('stats');
const TOTAL = {{ total }}, Q1 = {{ q1_count }};
const allCbs = Array.from(document.querySelectorAll('.quartile-cb'));
let sortKey = null, sortDir = -1;
let activeQuartiles = new Set(allCbs.map(cb => cb.dataset.key));

function saveFav(){ localStorage.setItem(FAV_KEY, JSON.stringify([...favorites])); }

function syncFavUI(){
  document.querySelectorAll('.fav-btn').forEach(btn => {
    const on = favorites.has(btn.dataset.id);
    btn.textContent = on ? '★' : '☆';
    btn.classList.toggle('active', on);
  });
  cards.forEach(c => c.classList.toggle('favorited', favorites.has(c.dataset.id)));
  document.getElementById('fav-count').textContent = favorites.size;
}

function apply(){
  const q = document.getElementById('search').value.trim().toLowerCase();
  const filtering = q || activeQuartiles.size < allCbs.length || currentTab === 'fav';
  let visible = cards.filter(c => {
    const matchSearch = !q || c.dataset.title.includes(q);
    const matchQuartile = activeQuartiles.has(c.dataset.category);
    const matchTab = currentTab === 'all' || c.classList.contains('favorited');
    return matchSearch && matchQuartile && matchTab;
  });
  if(sortKey){
    visible.sort((a,b) => {
      let x = a.dataset[sortKey], y = b.dataset[sortKey];
      if(sortKey === 'cite'){ return ((+x||0) - (+y||0)) * sortDir; }
      return x < y ? -sortDir : (x > y ? sortDir : 0);
    });
  }
  list.innerHTML = '';
  visible.forEach(c => list.appendChild(c));
  if(visible.length === 0){
    const msg = currentTab === 'fav'
      ? '还没有收藏的文献（点卡片右上角 ☆ 收藏）'
      : (q ? '没有匹配的文献' : '没有文献');
    const e = document.createElement('div');
    e.className = 'empty'; e.textContent = msg;
    list.appendChild(e);
  }
  stats.textContent = filtering
    ? `显示 ${visible.length}/${TOTAL} 篇`
    : `共 ${TOTAL} 篇 · Q1 ${Q1} 篇`;
}

document.getElementById('search').addEventListener('input', apply);

// 收藏切换
document.querySelectorAll('.fav-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const id = btn.dataset.id;
    if(favorites.has(id)){ favorites.delete(id); } else { favorites.add(id); }
    saveFav(); syncFavUI(); apply();
  });
});

// Tab 切换（全部 / 收藏）
function switchTab(t){
  currentTab = t;
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  document.getElementById(t === 'all' ? 'tab-all' : 'tab-fav').classList.add('active');
  apply();
}
document.getElementById('tab-all').addEventListener('click', () => switchTab('all'));
document.getElementById('tab-fav').addEventListener('click', () => switchTab('fav'));

// 导出收藏为 CSV（UTF-8 BOM，Excel 友好）
function escCsv(v){
  if(v === null || v === undefined || (typeof v === 'number' && isNaN(v))) v = '';
  v = String(v);
  return /[",\n]/.test(v) ? '"' + v.replace(/"/g,'""') + '"' : v;
}
document.getElementById('export-csv').addEventListener('click', () => {
  const favRecords = RECORDS.filter(r => favorites.has(r._id));
  if(favRecords.length === 0){ alert('还没有收藏的文献，先点卡片右上角 ☆ 收藏吧'); return; }
  const cols = ['Title','JournalTitle','Journal Abbreviation','Publication Date','PMID','DOI','PMC','category','if_2024','Citation Counts','标题翻译','摘要翻译','中文总结','创新点','Pubmed Web'];
  const lines = [cols.join(',')];
  favRecords.forEach(r => { lines.push(cols.map(c => escCsv(r[c])).join(',')); });
  const csv = '﻿' + lines.join('\n');
  const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'favorites.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
});

// 分区筛选
allCbs.forEach(cb => {
  cb.addEventListener('change', () => {
    if(cb.checked){ activeQuartiles.add(cb.dataset.key); } else { activeQuartiles.delete(cb.dataset.key); }
    apply();
  });
});
document.getElementById('quartile-all').addEventListener('click', (e) => {
  e.preventDefault();
  allCbs.forEach(cb => { cb.checked = true; activeQuartiles.add(cb.dataset.key); });
  apply();
});
document.getElementById('quartile-none').addEventListener('click', (e) => {
  e.preventDefault();
  allCbs.forEach(cb => { cb.checked = false; });
  activeQuartiles = new Set();
  apply();
});
const qToggle = document.getElementById('quartile-toggle');
const qMenu = document.getElementById('quartile-menu');
if(qToggle){
  qToggle.addEventListener('click', (e) => { e.stopPropagation(); qMenu.classList.toggle('open'); });
  document.addEventListener('click', (e) => {
    if(qMenu && !qMenu.contains(e.target) && e.target !== qToggle){ qMenu.classList.remove('open'); }
  });
}

// 排序
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

syncFavUI();
apply();
</script>
</body>
</html>
"""


def _record_id(rec):
    """文献稳定 ID：PMID 优先，DOI 备选，标题兜底（用于收藏持久化）。"""
    for key, prefix in (("PMID", "pmid"), ("DOI", "doi")):
        val = rec.get(key)
        # 跳过 NaN（float 且 self-unequal）
        if isinstance(val, float) and val != val:
            continue
        s = str(val).strip() if val is not None else ""
        if s and s.lower() != "nan":
            return f"{prefix}:{s}"
    title = str(rec.get("Title", "") or "").strip()
    return f"title:{title}"


def _build_quartiles(df):
    """从 category 列构造分区筛选列表：Q1→Q4 顺序 + 其他 + 未分类。"""
    if "category" not in df.columns:
        return []
    cat = df["category"].fillna("")
    counts = cat.value_counts()
    known = ["Q1", "Q2", "Q3", "Q4"]
    quartiles = []
    for q in known:
        c = int(counts.get(q, 0))
        if c > 0:
            quartiles.append({"name": q, "count": c, "uncategorized": False})
    for name, c in counts.items():
        name = str(name)
        if name and name not in known:
            quartiles.append({"name": name, "count": int(c), "uncategorized": False})
    uncat = int((cat == "").sum())
    if uncat > 0:
        quartiles.append({"name": "未分类", "count": uncat, "uncategorized": True})
    return quartiles


def generate_html(df, output_path):
    """把 DataFrame 渲染为卡片式 HTML，返回输出路径。"""
    # category 的空值（NaN/None）统一成空串，避免渲染成 "nan" 导致未分类筛选失配
    df = df.copy()
    if "category" in df.columns:
        df["category"] = df["category"].fillna("")
    records = df.to_dict(orient="records")
    for rec in records:
        rec["_id"] = _record_id(rec)
    has_llm = all(col in df.columns for col in ["标题翻译", "摘要翻译", "中文总结", "创新点"])
    q1_count = int((df["category"] == "Q1").sum()) if "category" in df.columns else 0
    quartiles = _build_quartiles(df)

    html = Template(HTML_TEMPLATE, autoescape=True).render(
        records=records,
        has_llm=has_llm,
        total=len(records),
        q1_count=q1_count,
        quartiles=quartiles,
    )

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
