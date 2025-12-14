import os
import requests
import time
import random
import shutil
import glob
from bs4 import BeautifulSoup
import os
import time
import random
import shutil

import os
import time
import random
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ===========================
# 1. 辅助工具函数
# ===========================

def get_doi_by_pmid(pmid):
    pmid = str(pmid).strip()
    if not pmid or pmid == 'nan':
        return None
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=pubmed_crawler&email=example@test.com&ids={pmid}&format=json"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if "records" in data and len(data["records"]) > 0:
            return data["records"][0].get("doi")
    except Exception as e:
        print(f"    [Error] Fetching DOI failed: {e}")
    return None

# ===========================
# 2. Sci-Hub 下载函数 (修复 NameError 的关键)
# ===========================

def download_one_paper(doi, save_path, proxies=None):
    if not doi:
        return False

    mirrors = [
        "https://sci-hub.se", 
        "https://sci-hub.ru", 
        "https://sci-hub.st", 
        "https://sci-hub.ren", 
        "https://sci-hub.ee"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    for mirror in mirrors:
        try:
            target_url = f"{mirror}/{doi}"
            # print(f"    Trying mirror: {mirror}...") # 调试用
            
            # 先请求页面找到真实链接
            res = requests.get(target_url, headers=headers, verify=False, timeout=20, proxies=proxies)
            if res.status_code != 200: continue

            soup = BeautifulSoup(res.content, 'html.parser')
            download_url = None
            
            # 解析 iframe 或 button
            iframe = soup.find('iframe', attrs={'id': 'pdf'})
            if iframe: download_url = iframe.get('src')
            
            if not download_url:
                buttons = soup.find_all('button', attrs={'onclick': True})
                for btn in buttons:
                    if 'location.href' in btn['onclick']:
                        download_url = btn['onclick'].split("'")[1]
                        break
            
            if not download_url: continue

            # 修正 URL
            if download_url.startswith('//'): download_url = 'https:' + download_url
            elif download_url.startswith('/'): download_url = mirror + download_url
            
            # 下载文件
            pdf_res = requests.get(download_url, headers=headers, verify=False, timeout=60, proxies=proxies, stream=True)
            if pdf_res.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in pdf_res.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)
                return True
        except Exception:
            pass
            
    return False

# ===========================
# 3. PMC 下载函数 (Selenium 增强版)
# ===========================
def download_from_pmc(pmc_id, save_path, proxies=None):
    """
    【生产环境版】
    1. 自动清理临时文件夹 (解决 temp_* 残留)
    2. 自动关闭浏览器 (释放内存)
    3. 仅保留核心下载逻辑
    """
    if not pmc_id or str(pmc_id).lower() == 'nan':
        return False

    abs_save_path = os.path.abspath(save_path)
    base_dir = os.path.dirname(abs_save_path)
    # 临时目录
    temp_download_dir = os.path.join(base_dir, f"temp_pmc_{pmc_id}_{random.randint(1000,9999)}")
    
    if os.path.exists(temp_download_dir):
        shutil.rmtree(temp_download_dir)
    os.makedirs(temp_download_dir)

    # === 配置 Chrome ===
    chrome_options = Options()
    # 生产模式建议开启 Headless，如果反爬严重可注释掉下面这行
    # chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    # 禁用自动化栏
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True, 
        "profile.default_content_settings.popups": 0
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 反爬特征抹除
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # 1. 访问主页
        article_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"
        print(f"    [Selenium] Visiting: {article_url}")
        driver.get(article_url)
        
        # 2. 精确寻找按钮
        target_link = None
        try:
            wait = WebDriverWait(driver, 10)
            target_link = wait.until(EC.visibility_of_element_located((
                By.CSS_SELECTOR, "a[data-ga-label='pdf_download_desktop']"
            )))
            
            if target_link:
                # 拟人点击
                actions = ActionChains(driver)
                actions.move_to_element(target_link).pause(0.5).click_and_hold(target_link).pause(0.3).release(target_link).perform()
                print("    [Status] Clicked. Waiting for download...")
                time.sleep(5) # 初步等待
                
                # 如果没反应，尝试保底跳转
                if not os.listdir(temp_download_dir):
                    pdf_href = target_link.get_attribute('href')
                    if pdf_href:
                        driver.get(pdf_href)

        except Exception as e:
            print(f"    [Warning] Button click failed, trying fallback: {e}")

        # 3. 监控下载
        final_file = None
        for i in range(60):
            if not os.path.exists(temp_download_dir): break
            files = os.listdir(temp_download_dir)
            pdfs = [f for f in files if f.endswith('.pdf')]
            
            if pdfs:
                target = os.path.join(temp_download_dir, pdfs[0])
                if os.path.getsize(target) > 1024:
                    time.sleep(1)
                    final_file = target
                    break
            time.sleep(1)

        if final_file:
            # 校验并移动
            try:
                with open(final_file, 'rb') as f:
                    if f.read(4) == b'%PDF':
                        # 如果目标文件存在，shutil.move 默认会报错，所以先删除旧文件
                        if os.path.exists(abs_save_path):
                            os.remove(abs_save_path)
                            
                        shutil.move(final_file, abs_save_path)
                        print(f"    -> Success: {abs_save_path}")
                        return True
            except:
                pass
        
        return False

    except Exception as e:
        print(f"    [Error] {e}")
        return False
        
    finally:
        # === 关键清理逻辑 ===
        if driver:
            try:
                driver.quit() # 关闭浏览器
            except:
                pass
        # 删除临时文件夹
        if os.path.exists(temp_download_dir):
            try:
                shutil.rmtree(temp_download_dir) # 强制删除文件夹
                print("    [Clean] Temp folder removed.")
            except:
                pass

# ===========================
# 4. 批量下载主逻辑
# ===========================

def batch_download_scihub(df, download_dir, error_file, proxy_url=None, overwrite=True): # <--- 默认开启覆盖
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}
        print(f"Using Proxy: {proxy_url}")
    else:
        proxies = None
    
    total = len(df)
    print(f"Start downloading {total} papers...")
    
    for col in ['Title', 'PMID', 'DOI', 'PMC']:
        if col not in df.columns: df[col] = ''

    with open(error_file, 'a', encoding='utf-8') as error_f:
        for index, row in df.iterrows():
            pmid = str(row['PMID']).strip()
            title = str(row['Title'])[:30]
            safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
            save_name = f"{pmid}_{safe_title}.pdf"
            save_path = os.path.join(download_dir, save_name)

            print(f"\n[{index+1}/{total}] Processing: {save_name}")

            # === 智能跳过逻辑 ===
            if os.path.exists(save_path):
                # 如果不强制覆盖，且文件看起来是好的(大于2KB)，才跳过
                if not overwrite and os.path.getsize(save_path) > 2048:
                    print(f"    -> Skipped (Exists & Valid)")
                    continue
                else:
                    print(f"    -> File exists but overwrite=True or invalid. Retrying...")
            # ===================

            # 1. 尝试 PMC
            pmc_id = str(row['PMC']).strip()
            pmc_success = False
            if pmc_id and pmc_id.startswith('PMC'):
                print(f"    Trying PMC: {pmc_id}")
                if download_from_pmc(pmc_id, save_path, proxies):
                    pmc_success = True
                    # 成功后随机休息一下
                    time.sleep(random.uniform(2, 4))
                else:
                    print(f"    -> PMC failed, falling back to Sci-Hub...")
            
            if pmc_success: continue

            # 2. 尝试 Sci-Hub
            doi = str(row['DOI']).strip()
            if not doi or doi.lower() in ['nan', 'none', '']:
                doi = get_doi_by_pmid(pmid)
            
            if not doi:
                print(f"    -> Failed: No DOI found")
                error_f.write(f"{pmid}\tNO_DOI\n")
                continue
            
            print(f"    Downloading Sci-Hub: {doi}")
            if download_one_paper(doi, save_path, proxies):
                print(f"    -> Success (Sci-Hub)")
            else:
                print(f"    -> Failed (All mirrors tried)")
                error_f.write(f"{pmid}\tDOWNLOAD_FAILED\n")
            
            time.sleep(random.uniform(1, 2))

    print(f"\nDownload process finished.")