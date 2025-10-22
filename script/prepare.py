import os
import pandas as pd

def J_Med_download():
    # 定义路径
    csv_path = "../data/J_Medline.csv"
    txt_path = "../data/J_Medline.txt"
    url = "https://ftp.ncbi.nlm.nih.gov/pubmed/J_Medline.txt"
    
    # 定义列名
    columns = ["JrId", "JournalTitle", "MedAbbr", "ISSN (Print)", "ISSN (Online)", "IsoAbbr", "NlmId"]

    # 确保 ../data 目录存在
    data_dir = os.path.dirname(csv_path)
    os.makedirs(data_dir, exist_ok=True)

    # 1. 检查目标CSV文件是否已存在
    if os.path.exists(csv_path):
        print(f"File '{csv_path}' already exists. Skipping.")
    else:
        print(f"Target '{csv_path}' not found. Generating...")
        
        # 2. 检查源TXT文件是否存在，不存在则下载
        if not os.path.exists(txt_path):
            print(f"Source file '{txt_path}' not found. Downloading from NCBI...")
            # 使用 -O 参数指定下载文件的输出路径
            os.system(f"wget {url} -O {txt_path}")
            print("Download complete.")
        else:
            print(f"Found existing source file '{txt_path}'.")

        # 3. 解析TXT文件
        print(f"Parsing '{txt_path}'...")
        data = []
        
        try:
            with open(txt_path, "r", encoding="utf-8") as file:
                lines = file.readlines()

            # 遍历文件，步长为8
            for i in range(1, len(lines), 8):
                try:
                    # 使用 .split(':', 1) 确保只在第一个冒号处分割
                    jr_id = lines[i].split(":", 1)[1].strip()
                    journal_title = lines[i+1].split(":", 1)[1].strip()
                    med_abbr = lines[i+2].split(":", 1)[1].strip()
                    issn_print = lines[i+3].split(":", 1)[1].strip()
                    issn_online = lines[i+4].split(":", 1)[1].strip()
                    iso_abbr = lines[i+5].split(":", 1)[1].strip()
                    nlm_id = lines[i+6].split(":", 1)[1].strip()

                    data.append([jr_id, journal_title, med_abbr, issn_print, issn_online, iso_abbr, nlm_id])
                
                except IndexError:
                    print(f"Warning: Skipping malformed data near line {i}.")
                    continue
        
        except FileNotFoundError:
            print(f"Error: File '{txt_path}' not found. Download may have failed.")
            return 
        except Exception as e:
            print(f"Error reading or parsing file: {e}")
            return

        if data:
            print("Parse complete. Creating DataFrame and saving to CSV...")
            df = pd.DataFrame(data, columns=columns)
            
            df.to_csv(csv_path, index=False)
            print(f"Successfully created '{csv_path}'.")
        else:
            print("No data parsed from TXT file.")

    print("J_Medline file is ready.")

# if __name__ == "__main__":
#     J_Med_download() 