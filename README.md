# Pubmed-Crawler

## 1. Introduction
Hey there! This project helps you **scrape PubMed search results** and automatically organize them into a **structured spreadsheet (Excel)** — and now also generates a **card-style HTML reading view**, with optional **LLM-powered Chinese analysis** (translation / summary / innovation points). Super handy for literature screening and review prep, no more manual copy-pasting!

![](./images/Gemini_Generated_Image_qalaifqalaifqala.png)

For Chinese users, please refer to [中文文档](./Doc/README.md).

> Built on [pubmed_get](https://github.com/PiaoyangGuohai1/pubmed_get). A big thanks to the original author for their open-source contribution!

### Highlights
- 🔎 **One-command scrape** → structured Excel (title, journal, date, PMID, DOI, abstract, citations, JCR quartile, IF…)
- 🤖 **Optional LLM analysis** (`-t`): Chinese translation of title/abstract, plus a summary and innovation points
- 🌐 **Card-style HTML reading view**: search, sort (by citation / date), JCR quartile filter, favorites (persisted in the browser), favorites tab, and one-click CSV export of favorites
- 📥 **Batch PDF download** (Sci-Hub / PMC)

### 1.1 Fields in the Structured Text
The output spreadsheet includes these key fields:
- **Title**: Article title
- **Journal Abbreviation**: Abbreviated journal name (e.g., "Clin J Am Soc Nephrol")
- **JournalTitle**: Full journal name
- **Publication Date**: Publication date (format: "2023-05-15")
- **PMID / DOI / PMC**: PubMed ID, DOI, and PMC ID (when available)
- **Pubmed Web**: Direct PubMed link of the article
- **Abstract**: Full article abstract
- **Citation Counts**: Number of citations (quickly gauge impact)
- **category**: JCR quartile (e.g., Q1, Q2)
- **if_2024**: 2024 Journal Impact Factor (when JCR data is available)
- *(Only when run with `-t`)* **标题翻译 / 摘要翻译 / 中文总结 / 创新点**: LLM-generated Chinese translation, summary, and innovation points

### 1.2 Structured Text Example
| Title | Journal Abbreviation | Publication Date | PMID | DOI | PMC | Abstract | Citation Counts | JournalTitle | category | if_2024 |
|-------|----------------------|------------------|------|-----|-----|----------|----------------|--------------|----------|---------|
| The Gut-Kidney Axis: Mechanisms and Therapeutic Implications | Clin J Am Soc Nephrol | 2023-05-15 | 37172890 | 10.2215/CJN.08450822 | PMC10183456 | The gut-kidney axis refers to the bidirectional communication between the gastrointestinal tract and the kidneys... | 42 | Clinical Journal of the American Society of Nephrology | Q1 | 11.0 |


## 2. How to Use

### 2.1 Install dependencies with uv (recommended)
**uv** is a fast, lightweight Python dependency manager — highly recommended.

- Repo: [astral-sh/uv](https://github.com/astral-sh/uv)
- Install uv:
  - Windows (PowerShell):
    ```powershell
    iwr https://astral.sh/uv/install.ps1 -useb | iex
    ```
  - macOS / Linux:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
- In the **project root**, sync dependencies:
  ```bash
  uv sync
  source .venv/bin/activate   # Windows: .venv\Scripts\activate
  ```

### 2.2 Core step: scrape PubMed data
1. Enter the `script` folder:
   ```bash
   cd ./script
   ```
2. Run the scrape:
   ```bash
   python main.py -u "$url" -o your_project_name
   ```
   - `$url`: must be the **abstract-page link** from your PubMed search (not the homepage or list page).
   - `-o your_project_name`: name this task (e.g., `gut_kidney_axis`). Results are saved to `output/your_project_name/`.
   - Output: `PubMed_<keywords>.xlsx` plus a card-style `PubMed_<keywords>.html`.

### 2.3 Optional: LLM analysis (`-t`)
Adds Chinese translation / summary / innovation points for every article.

1. Copy the example config and fill in your credentials (`.env` is gitignored):
   ```bash
   cp .env.example .env
   ```
   `.env` uses any **OpenAI-compatible** endpoint. Defaults target Alibaba Cloud DashScope with `deepseek-v3.2`:
   ```env
   BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
   API_KEY=your-api-key-here
   MODEL=deepseek-v3.2
   ```
2. Run with `-t`:
   ```bash
   python main.py -u "$url" -o your_project_name -t
   ```
   The four extra columns (标题翻译 / 摘要翻译 / 中文总结 / 创新点) are written into both the Excel and HTML outputs.

### 2.4 HTML reading view
The `.html` file generated next to the Excel is a standalone reading view. Open it in any browser to:
- 🔍 search titles (Chinese + English)
- ↕️ sort by citation count or publication date
- ▦ filter by JCR quartile
- ☆ favorite articles (saved in the browser's localStorage, keyed by PMID/DOI)
- switch between **All / Favorites** tabs
- ⬇ export favorites to CSV (UTF-8 with BOM, Excel-friendly)

### 2.5 Optional: download PDFs
Download full texts alongside the scrape:
```bash
python main.py -u "$url" \
  -o your_project_name \
  --download_dir ./download/your_topic \
  --error_download_paper failed_downloads.txt
```
Failed PMIDs are recorded in `failed_downloads.txt` for retry.

### 2.6 Key: how to get `$url` (PubMed abstract page link)
1. Go to PubMed: https://pubmed.ncbi.nlm.nih.gov/
2. Enter your keywords (e.g., `gut-kidney axis`, `diabetes AND kidney`)
3. On the results page, open **Display Options** (top-right) and select **Abstract**
4. The link in the address bar is your `$url` — copy it.

![](./images/pubmed-crawler_image.jpg)


## 3. CLI reference
| Flag | Description |
|------|-------------|
| `-u, --url` | PubMed abstract-page URL (required) |
| `-o, --output` | Output folder name under `output/` |
| `--output-folder` | Alternative output folder name |
| `-n, --name` | Custom Excel/HTML file name |
| `-t, --translate` | Enable LLM analysis (needs `.env`) |
| `--download_dir` | Directory to save downloaded PDFs |
| `--error_download_paper` | File path to record failed PMIDs |
| `-d, --download` | Legacy download parameter |


## 4. Roadmap
- ✅ 2024 Journal Impact Factor & JCR quartile
- ✅ PMC / Sci-Hub PDF download
- ✅ LLM analysis (translation / summary / innovation points)
- ✅ Card-style HTML reading view (favorites, tabs, CSV export, quartile filter)
- 🔜 More category info (e.g., CAS tiers), faster batch LLM processing, incremental updates
