import argparse
import re
import os
import pandas as pd
import datetime
import csv
import random
from pubmed_get import *
from prepare import *
from pdf_download import *
from llm_analyze import analyze_df
from html_report import generate_html

# 项目根目录 = script/ 的上一级；用绝对路径避免依赖运行时 cwd（uv run 与 cd script 都能跑）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


def normalize_pubmed_url(url):
    """规范化 PubMed URL：去反斜杠转义残留、自动补 format=abstract、清理首尾空格。
    用户从终端粘贴的 URL 可能带 \? \= \& 等多余反斜杠，或缺少 format=abstract，
    这里统一修正，避免在 main() 里被硬性检查直接拦下。"""
    original = url
    # 清理首尾空格 + 去掉反斜杠转义残留
    url = url.strip().replace("\\", "")
    # 缺少 format=abstract 时自动补上（PubMed 搜索 URL 一定有 ?，所以通常用 & 拼接）
    if "format=abstract" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}format=abstract"
    # 发生改动时打印一行提示，方便用户察觉粘贴问题；URL 本就正确则静默
    if url != original:
        print(f"[INFO] URL auto-normalized: {url}")
    return url


# 1. 在函数定义中加回 download 参数
def main(url, translate, output, name, download_dir, error_download_paper, download):
    if url:
        # 规范化 URL：去反斜杠、补 format=abstract，让用户能直接粘贴原始搜索 URL
        url = normalize_pubmed_url(url)
        if "format=abstract" not in url:
            print("URL format is incorrect. Please switch to abstract URL format.")
            return

        # 处理输出目录名称：优先使用 -o，然后是 -d，最后是随机生成
        if not output:
            # 2. 这里使用了 download，所以参数里必须有它
            if download and not download.endswith('.xlsx'):
                output = download
                download = None 
            else:
                rd=random.randint(1000,9999)
                output=f'project_{rd}'
        
        out_dir = os.path.join(OUTPUT_DIR, output)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        print(f"The results file save in :{out_dir}")

        # Prepare J_Medline file
        if not os.path.exists(os.path.join(DATA_DIR, "J_Medline.csv")):
            J_Med_download()

        # 构造输出文件名
        if name:
            if not name.endswith('.xlsx'):
                name = name + '.xlsx'
            xlsx_name = name
        else:
            try:
                keywords = re.search(r"term=(.*)", url).group(1)
                keywords = re.sub(r"\d+", "", keywords)
                keywords = re.sub(r"[^\w\s]", "", keywords).replace(" ", "_")
                if "&" in keywords:
                    keywords = keywords.split("&")[0]
            except:
                keywords = "result"
            print(f"Search Keywords：{keywords}")
            xlsx_name = f"PubMed_{keywords}.xlsx"

        xlsx_path = f"{out_dir}/{xlsx_name}"
        
        # Extract articles from PubMed
        df = extract_articles(url)
        
        # Gain JCR Category and IF
        df = merge_dataframes(df)
        
        # LLM 分析（翻译/总结/创新点）
        if translate:
            df = analyze_df(df)
        
        # 输出合并后的DataFrame
        df.to_excel(xlsx_path, index=False)
        print(f"Excel saved to {xlsx_path}")

        # 生成 HTML 阅读视图
        html_path = xlsx_path.replace(".xlsx", ".html")
        generate_html(df, html_path)
        print(f"HTML saved to {html_path}")
        
        # === 下载逻辑 ===
        if download_dir:
            print("\n" + "="*30)
            print("Start processing PDF downloads...")
            
            # 路径处理：支持相对路径
            if not os.path.isabs(download_dir) and not download_dir.startswith('.'):
                 download_dir = os.path.join(out_dir, download_dir)

            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
            
            if not error_download_paper:
                error_download_paper = os.path.join(out_dir, "failed_downloads.txt")
                
            batch_download_scihub(df, download_dir, error_download_paper)
            
            print("="*30 + "\n")
                    
    print("程序结束!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PubMed Crawler')
    parser.add_argument('-u', '--url', type=str, help='The web URL to be processed.')
    parser.add_argument('-t', '--translate', action='store_true', help='Enable LLM analysis (title/abstract translation, summary, innovation points).')
    parser.add_argument('-o','--output', type=str, help='which folder you want to save the result.')
    parser.add_argument('--output-folder', type=str, help='Alternative way to specify output folder name.')
    parser.add_argument('-n','--name', type=str, help='Custom Excel file name')
    
    # 3. 恢复 -d 参数，防止报错
    parser.add_argument('-d', '--download', type=str, help='Legacy download parameter')
    
    parser.add_argument('--download_dir', type=str, help='Directory to save downloaded PDFs.')
    parser.add_argument('--error_download_paper', type=str, help='File path to save failed PMIDs.')

    args = parser.parse_args()
    # 合并输出目录：-o 优先，其次 --output-folder
    output = args.output or args.output_folder
    # 4. 传参时包含 download
    main(args.url, args.translate, output, args.name,
         args.download_dir, args.error_download_paper, args.download)