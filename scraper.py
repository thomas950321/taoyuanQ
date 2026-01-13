import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_all_links(base_url, html_content):
    """從 HTML 中解析出所有屬於該網域的連結"""
    soup = BeautifulSoup(html_content, 'html.parser')
    links = set()
    
    # 解析 base_url 的 domain，避免抓到外部連結
    domain = urlparse(base_url).netloc
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)
        
        # 條件：
        # 1. 必須是同一個 domain
        # 2. 必須以 base_url (包含 /zh) 開頭，確保是中文頁面相關
        # 3. 排除錨點 (#) 和非 HTTP 協定
        if (parsed_url.netloc == domain and 
            full_url.startswith(base_url) and 
            parsed_url.scheme in ["http", "https"]):
            
            # 去除 fragment (URL # 後面的部分)
            clean_url = full_url.split('#')[0]
            links.add(clean_url)
            
    return links

def fetch_url_content(url, headers):
    """抓取單一網址的內容"""
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除雜訊
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
            
            text = soup.get_text(separator='\n')
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return f"\n--- 來源: {url} ---\n{clean_text}\n"
    except Exception:
        pass # 忽略錯誤，避免拖慢整體
    return ""

def fetch_taoyuanq_content():
    """
    動態爬取桃園Q官網所有頁面。
    使用多執行緒加速。
    """
    base_url = "https://a18.taoyuanq.com/zh"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"正在分析網站結構: {base_url} ...")
    
    # 1. 先抓首頁來獲取連結清單
    try:
        response = requests.get(base_url, headers=headers, timeout=10)
        start_urls = get_all_links(base_url, response.text)
        # 確保首頁也在清單中
        start_urls.add(base_url)
    except Exception as e:
        return f"網站連接失敗: {e}"

    print(f"發現 {len(start_urls)} 個頁面，開始並行抓取...")
    
    combined_content = ""
    
    # 2. 使用 ThreadPool 平行抓取所有頁面
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_url_content, url, headers): url for url in start_urls}
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                combined_content += data
            except Exception as e:
                print(f"抓取 {url} 發生錯誤: {e}")
                
    return combined_content

if __name__ == "__main__":
    import time
    start_time = time.time()
    print("正在測試動態全站爬蟲...")
    content = fetch_taoyuanq_content()
    print(f"抓取完成，總字數: {len(content)}")
    print(f"耗時: {time.time() - start_time:.2f} 秒")
    # 檢查是否有抓到重要關鍵字
    print(f"是否包含 '萬聖': {'萬聖' in content}")

