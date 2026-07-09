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

# 1. 在函数定义中加回 download 参数
def main(url, translate, output, name, download_dir, error_download_paper, download):
    if url:
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
        
        out_dir = f"../output/{output}"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        print(f"The results file save in :{out_dir}")

        # Prepare J_Medline file
        if not os.path.exists("../data/J_Medline.csv"):
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