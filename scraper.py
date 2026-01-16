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
