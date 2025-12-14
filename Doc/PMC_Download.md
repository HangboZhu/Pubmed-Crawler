# 📄 PMC & Sci-Hub PDF Downloader

An advanced PDF downloading pipeline designed to retrieve academic papers from **PubMed Central (PMC)** and **Sci-Hub**. It features a robust Selenium-based scraper specifically optimized to bypass PMC's strict anti-bot measures.

## 🛠️ Implementation Details: How PMC Download Works

Downloading from PMC is challenging due to dynamic rendering, hidden links, and bot detection (WAF/Cloudflare). This tool implements a sophisticated **"Human-Simulation" strategy**:

1.  **Anti-Detection Configuration**:
    * The scraper runs a visible Chrome instance (or Headless with patches) with automation flags removed (`enable-automation`, `useAutomationExtension`).
    * It patches `navigator.webdriver` to `undefined` to hide Selenium traces.

2.  **Precision DOM Targeting**:
    * Instead of unreliable XPath searches, we target the specific **Google Analytics label** used by PMC: `a[data-ga-label='pdf_download_desktop']`.
    * This ensures the scraper interacts *only* with the actual download button, ignoring hidden metadata links or sidebar ads.

3.  **Human-Like Interaction (ActionChains)**:
    * Simple `.click()` events often trigger anti-bot refreshes (page reload without download).
    * We use Selenium `ActionChains` to simulate a full human mouse sequence: **Move to Element → Hover (0.5s) → Click & Hold (0.3s) → Release**.

4.  **Sandbox Download Environment**:
    * **Temp Directories**: Each download spawns a unique, randomized temporary folder (`temp_pmc_ID_XXXX`) to prevent file conflicts.
    * **Force Download**: Chrome preferences are set to `plugins.always_open_pdf_externally: True`, forcing PDFs to download instead of opening in the built-in viewer.
    * **Auto-Cleanup**: The temporary directory is automatically deleted after the file is successfully moved to the destination or if the process fails.

5.  **Smart Fallback**:
    * If the UI interaction fails, the script extracts the direct PDF URL and forces a browser navigation within the same authenticated session to trigger the download.