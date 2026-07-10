import requests 
from bs4 import BeautifulSoup
import re
import calendar 
from urllib3.exceptions import InsecureRequestWarning 
import pandas as pd
import os

# 项目根目录 = script/ 的上一级；用绝对路径避免依赖运行时 cwd
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# 定义日期转换
def convert_date(date_string):
    match = re.search(r"(\d{4})(?: (\w{3})(?: (\d{1,2}))?)?", date_string)
    # print(f"Original date string: {date_string}")
    # print(f"Converting date: {match}")
    if match:
        year, month, day = match.groups()
        if month:
            month_dict = {v: k for k, v in enumerate(calendar.month_abbr)}
            # print(f"Converting month: {month}")
            # 获取月份，未找到则返回"Unknown"
            month = month_dict.get(month, "Unknown")
            # 若月份为"Unknown"，直接返回
            if month == "Unknown":
                return "Unknown"
            day = day if day else "01"
            return f"{year}-{month:02d}-{day.zfill(2)}"
        else:
            return year
    else:
        return "Unknown"

import requests
import pandas as pd
from bs4 import BeautifulSoup
import re  # 确保导入re（如果convert_date用到的话）


def extract_articles(url, page_start=1):
    data = []
    page = page_start
    while True:
        response = requests.get(url, params={"page": page}, verify=False)
        content = response.content
        soup = BeautifulSoup(content, "html.parser")
        
        # 【关键修改 1】: 循环的基准从 "div.short-view" 改为 "article.article-overview"
        articles = soup.find_all("article", {"class": "article-overview"})
        
        print(f'Found {len(articles)} articles on page {page}')
        if len(articles) == 0:
            break  # 没有文章时退出循环
        
        # 遍历每篇文章
        for count, article in enumerate(articles, 1):
            # 提取标题、期刊等基础信息（保持不变，因为它们都在 article-overview 内部）
            title = article.find("h1", {"class": "heading-title"}).text.strip()
            print("Processing article:", title)
            # journal_abbreviation = article.find("span", {"class": "citation-journal"}).text.strip()
            journal_abbreviation_element = article.find("span", {"class": "citation-journal"})
            if journal_abbreviation_element:
                journal_abbreviation = journal_abbreviation_element.text.strip()
            else:
                journal_abbreviation = "Unknown, Please check manually"
            # print("Raw journal abbreviation:", journal_abbreviation)
            if journal_abbreviation.endswith('.'):
                journal_abbreviation = journal_abbreviation[:-1]
            # publication_date = article.find("span", {"class": "cit"}).text.split(";")[0].strip()
            pub_date_element = article.find("span", {"class": "cit"})
            if pub_date_element:
                publication_date = pub_date_element.text.split(";")[0].strip()
            else:
                publication_date = "Unknown, Please check manually"
            # print("Processing article", count, "on page", page)
            # print("Raw publication date:", publication_date)
            
            publication_date = convert_date(publication_date) # 假设 convert_date 已定义
            
            try:
                doi = article.find("span", {"class": "citation-doi"}).text.split(":")[1].strip()
                if doi.endswith('.'):
                    doi = doi[:-1]
            except AttributeError:
                doi = '暂时缺失，请手动查询'
            
            try:
                pmid = article.find("strong", {"class": "current-id"}).text.strip()
                if pmid == "39327211" or pmid == 39327211:
                    print("调试点")
                pubmed_web = f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
            except AttributeError:
                pmid = '暂时缺失，请手动查询'
                pubmed_web = ''
            
            try:
                pmc = article.find("a", {"data-ga-action": "PMCID"}).text.strip()
            except AttributeError:
                pmc = ''
            
            # 【关键修改 2】: 使用 find() 在 article 内部查找摘要
            abstract = article.find("div", {"class": "abstract"})  
            abstr = abstract.text.strip() if abstract else "" 
            abstr = re.sub(r"\n\s+", "\n", abstr)
            
            # 【关键修改 3】: 使用 find() 在 article 内部查找 stats
            stat = article.find("div", {"class": "stats"})  
            citation_counts = 0  
            
            if stat:  # 只有在当前 article 内部找到了 stats 块
                try:
                    # 在这个 stat 块内部查找
                    cited_li = stat.find("li", {"class": "citedby-count"})
                    if cited_li:
                        cited_text = cited_li.text.strip().replace(" ", "")
                        match = re.search(r'Citedby(\d+)', cited_text)
                        if match:
                            citation_counts = int(match.group(1))  
                except AttributeError:
                    pass  
            
            data.append([
                title, journal_abbreviation, publication_date, pmid, 
                pubmed_web, doi, pmc, abstr, citation_counts
            ])
        
        print(f'PubMed: Completed page {page}')
        page += 1
    
    df = pd.DataFrame(
        data, 
        columns=[
            "Title", "Journal Abbreviation", "Publication Date", "PMID", 
            "Pubmed Web", "DOI", "PMC", "Abstract", "Citation Counts"
        ]
    )
    return df



# def merge_dataframes(df):
#     journal_df = pd.read_csv('../data/J_Medline.csv', usecols=['MedAbbr', 'JournalTitle'])
    
#     df = df.merge(journal_df, left_on='Journal Abbreviation', right_on='MedAbbr', how='left')
    
#     df.drop(columns=['MedAbbr'], inplace=True)
    
#     df_jcr = pd.read_csv('../data/2022-2024IF.csv', usecols=['journal_name', 'category',"if_2023", 'if_2022', 'if_2024'])
    
#     regex_pattern = r"\((Q[1-4])\)$"

#     # 提取括号中的内容，如果匹配成功则提取，否则填充为"NaN"
#     df_jcr['category'] = df_jcr['category'].str.extract(regex_pattern).fillna("NaN")

#     # 将要匹配的列转换为小写并且删除逗号和点，删除单词 "The"，并且将 "and" 替换为 "&"
#     df['JournalTitle_lower'] = df['JournalTitle'].str.lower().str.replace('[.,]', '', regex=True).str.replace(' the ', ' ').str.replace(' and ', ' & ')
#     df_jcr['journal_name_lower'] = df_jcr['journal_name'].str.lower().str.replace('[.,]', '', regex=True).str.replace(' the ', ' ').str.replace(' and ', ' & ')

#     # 合并DataFrame，根据JournalTitle_lower和Journal Name_lower进行连接
#     df = df.merge(df_jcr, left_on='JournalTitle_lower', right_on='journal_name_lower', how='left')

#     df.drop(columns=['JournalTitle_lower', 'journal_name_lower', 'journal_name'], inplace=True)

#     return df

def merge_dataframes(df):
    # 1. 加载期刊缩写对照表 (保持不变)
    # 这一步是为了把 PubMed 爬取的 "Clin J Am Soc Nephrol" 转换为全称 "Clinical Journal of the American Society of Nephrology"
    journal_df = pd.read_csv(os.path.join(DATA_DIR, 'J_Medline.csv'), usecols=['MedAbbr', 'JournalTitle'])
    df = df.merge(journal_df, left_on='Journal Abbreviation', right_on='MedAbbr', how='left')
    df.drop(columns=['MedAbbr'], inplace=True)
    
    # 2. 读取新的 IF 数据 (关键修改点)
    # 读取我们在上一步生成的清洗好的文件 JCR_2025_Ready.csv
    # 该文件应包含列: journal_name, quartile, if_2024
    jcr_path = os.path.join(DATA_DIR, 'JCR_2025_Ready.csv')
    
    # 如果没找到清洗文件，尝试直接读取原始 CSV (作为备选方案，防止报错)
    if not os.path.exists(jcr_path):
        print(f"Warning: {jcr_path} not found. Trying raw file...")
        jcr_path = os.path.join(DATA_DIR, '2025年最新JCR完整版.xlsx')
        df_jcr = pd.read_excel(jcr_path)
        # 临时改名以匹配逻辑
        df_jcr.rename(columns={'Journal Name': 'journal_name', 'JIF Quartile': 'category', 'JIF 2024': 'if_2024'}, inplace=True)
    else:
        df_jcr = pd.read_csv(jcr_path)
        # 将清洗文件中的 'quartile' 改名为 'category'，以便保持输出 Excel 的列名习惯
        if 'quartile' in df_jcr.columns:
            df_jcr.rename(columns={'quartile': 'category'}, inplace=True)

    # 3. 准备匹配键 (保持不变)
    # 将期刊名转换为小写、去标点、标准化 'and'/'the'，以提高匹配率
    df['JournalTitle'] = df['JournalTitle'].fillna('')
    df['JournalTitle_lower'] = df['JournalTitle'].str.lower().str.replace('[.,]', '', regex=True).str.replace(' the ', ' ').str.replace(' and ', ' & ').str.strip()
    
    # 对 JCR 数据做同样的处理
    if 'journal_name_lower' not in df_jcr.columns:
        df_jcr['journal_name_lower'] = df_jcr['journal_name'].str.lower().str.replace('[.,]', '', regex=True).str.replace(' the ', ' ').str.replace(' and ', ' & ').str.strip()

    # 4. 合并数据 (关键修改点)
    # 我们只需要 category (即分区) 和 if_2024
    # 注意：这里不需要再做 regex_pattern 提取了，因为新数据里已经是干净的 "Q1", "Q2" 了
    df = df.merge(df_jcr[['journal_name_lower', 'category', 'if_2024']], 
                  left_on='JournalTitle_lower', 
                  right_on='journal_name_lower', 
                  how='left')

    # 5. 清理临时列
    df.drop(columns=['JournalTitle_lower', 'journal_name_lower'], inplace=True)

    return df