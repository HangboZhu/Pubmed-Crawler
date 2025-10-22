## 1. Introduction
Hey there! This project is designed to help you **scrape search results from Pubmed** and automatically organize them into **structured text** (like Excel spreadsheets). It’s super handy for literature analysis and screening—no more manual copy-pasting!

For Chinese user, Please Refer to [this](./Doc/README.md)

This project is modified from [pubmed_get](https://github.com/PiaoyangGuohai1/pubmed_get). A big thanks to the original author for their open-source contribution!


### 1.1 Fields in Structured Text
The final output spreadsheet includes these key fields to keep your literature data organized:
- Title: Article title
- Journal Abbreviation: Abbreviated journal name (e.g., "Clin J Am Soc Nephrol")
- Publication Date: Publication date (format: "2023-05-15")
- PMID: Pubmed unique ID (easy for finding articles)
- Pubmed Web: Direct Pubmed webpage link of the article
- DOI: Article DOI (links directly to the original journal page)
- PMC: PMC ID (if the article is available in PMC)
- Abstract: Full article abstract (no need to click into the Pubmed page)
- Citation Counts: Number of citations (quickly gauge article impact)
- JournalTitle: Full journal name (e.g., "Clinical Journal of the American Society of Nephrology")
- category: Journal category (e.g., JCR Q1, CAS Tier 2)
- if_2023: 2023 Journal Impact Factor


### 1.2 Structured Text Example
Here’s a real example to show you what the output looks like:

| Title | Journal Abbreviation | Publication Date | PMID | Pubmed Web | DOI | PMC | Abstract | Citation Counts | JournalTitle | category | if_2023 |
|-------|----------------------|------------------|------|------------|-----|-----|----------|----------------|--------------|----------|---------|
| The Gut-Kidney Axis: Mechanisms and Therapeutic Implications | Clin J Am Soc Nephrol | 2023-05-15 | 37172890 | https://pubmed.ncbi.nlm.nih.gov/37172890/ | 10.2215/CJN.08450822 | PMC10183456 | The gut-kidney axis refers to the bidirectional communication between the gastrointestinal tract and the kidneys. Dysregulation of this axis is closely associated with chronic kidney disease (CKD) and gut microbiota dysbiosis... | 42 | Clinical Journal of the American Society of Nephrology | JCR Q1 | 11.0 |


## 2. How to Use
Super easy to get started—just follow these steps!


### 2.1 First: Install and Use uv (Dependency Manager)
Tired of slow pip installs and dependency issues? Try **uv**—a lightweight, fast Python dependency manager. Highly recommended!

- uv’s official GitHub repo: [astral-sh/uv](https://github.com/astral-sh/uv) (for more details)
- Install uv (copy the command for your OS):
  - Windows: Open PowerShell and run:
    ```powershell
    iwr https://astral.sh/uv/install.ps1 -useb | iex
    ```
  - macOS/Linux: Open Terminal and run:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
- After installation, go to the **project root directory** and sync dependencies (may take a few seconds first time):
  ```bash
  uv sync
  source .venv/bin/activate
  ```


### 2.2 Core Step: Scrape Pubmed Data
It only takes one command! Here’s how:

1. First, enter the `script` folder (all scripts are here):
   ```bash
   cd ./script
   ```

2. Run the scraping command:
   ```bash
   python main.py -u $url -o your_project_name
   ```

   - Explanations:
     - `$url`: Must be the **abstract page link** from your Pubmed search (not the homepage or list page!)
     - `-o your_project_name`: Name your scraping task (e.g., "gut_kidney_axis_2023-2025"). Results will be saved in `output/your_project_name`.


### 2.3 Key: How to Get $url (Pubmed Abstract Page Link)
Many people mix up the link at first—here’s a step-by-step guide:
1. Go to Pubmed: https://pubmed.ncbi.nlm.nih.gov/
2. Enter your search keywords (e.g., "gut-kidney axis", "diabetes AND kidney")
3. After searching, find the "Display Option" option in the top-right corner of the results page, select "Abstract" (see image below)
4. The link in your browser’s address bar is your `$url`! Copy it.
#### Example Image
![](./images/pubmed-crawler_image.jpg)


### 2.4 Optional: Download PMC Articles
If your results have PMC IDs, you can auto-download full texts:
```bash
cd ./script
python main.py -d "../output/your_project_name/PubMed_xxx.xlsx"
```
- Replace `../output/your_project_name/PubMed_xxx.xlsx` with the actual path of your scraped Excel file. Articles will be downloaded to the same folder as the Excel file.


## 3. Update Plan
We’ll keep optimizing the project. The confirmed plan so far:
- Add **2025 Journal Impact Factor** data (Note: This data is only accessible/usable in Mainland China)
- Future features may include more category info, faster batch translation, etc.—based on user needs. Stay tuned!