import requests 
from bs4 import BeautifulSoup
import re
import calendar 
from urllib3.exceptions import InsecureRequestWarning 
import pandas as pd

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning) 

# 定义日期转换
def convert_date(date_string):
    match = re.search(r"(\d{4})(?: (\w{3})(?: (\d{1,2}))?)?", date_string)
    if match:
        year, month, day = match.groups()
        if month:
            month_dict = {v: k for k, v in enumerate(calendar.month_abbr)}
            month = month_dict[month]
            day = day if day else "01"
            return f"{year}-{month:02d}-{day.zfill(2)}"
        else:
            return year
    else:
        return "Unknown"

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
            journal_abbreviation = article.find("span", {"class": "citation-journal"}).text.strip()
            if journal_abbreviation.endswith('.'):
                journal_abbreviation = journal_abbreviation[:-1]
            publication_date = article.find("span", {"class": "cit"}).text.split(";")[0].strip()
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



def merge_dataframes(df):
    journal_df = pd.read_csv('../data/J_Medline.csv', usecols=['MedAbbr', 'JournalTitle'])
    
    df = df.merge(journal_df, left_on='Journal Abbreviation', right_on='MedAbbr', how='left')
    
    df.drop(columns=['MedAbbr'], inplace=True)
    
    df_jcr = pd.read_csv('../data/2022-2023IF.csv', usecols=['journal_name', 'category',"if_2023", 'if_2022'])
    
    regex_pattern = r"\((Q[1-4])\)$"

    # 提取括号中的内容，如果匹配成功则提取，否则填充为"NaN"
    df_jcr['category'] = df_jcr['category'].str.extract(regex_pattern).fillna("NaN")

    # 将要匹配的列转换为小写并且删除逗号和点，删除单词 "The"，并且将 "and" 替换为 "&"
    df['JournalTitle_lower'] = df['JournalTitle'].str.lower().str.replace('[.,]', '', regex=True).str.replace(' the ', ' ').str.replace(' and ', ' & ')
    df_jcr['journal_name_lower'] = df_jcr['journal_name'].str.lower().str.replace('[.,]', '', regex=True).str.replace(' the ', ' ').str.replace(' and ', ' & ')

    # 合并DataFrame，根据JournalTitle_lower和Journal Name_lower进行连接
    df = df.merge(df_jcr, left_on='JournalTitle_lower', right_on='journal_name_lower', how='left')

    df.drop(columns=['JournalTitle_lower', 'journal_name_lower', 'journal_name'], inplace=True)

    return df