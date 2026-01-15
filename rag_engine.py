import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from openai import OpenAI
from scraper import fetch_taoyuanq_content
import time

# 快取設定
import json

# Local Memory Cache Fallback (Global variables)
_LOCAL_MEM_CACHE = None
_LOCAL_MEM_CACHE_TIME = 0
CACHE_TTL = 3600  # 1 hour

def get_redis_client():
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        # 本地無 Redis 不需噴錯，靜默降級即可
        return None

def get_cached_content():
    """
    獲取快取內容。
    回傳: List[Dict] -> [{'url':..., 'content':...}]
    """
    global _LOCAL_MEM_CACHE, _LOCAL_MEM_CACHE_TIME

    # 1. 嘗試從 Redis 讀取
    r = get_redis_client()
    if r:
        try:
            cached_json = r.get("taoyuanq_pages")
            if cached_json:
                data = json.loads(cached_json)
                print(f"[Cache] Hit from Redis! Pages: {len(data)}")
                # 同步更新本地快取
                _LOCAL_MEM_CACHE = data
                _LOCAL_MEM_CACHE_TIME = time.time()
                return data
        except Exception:
            pass
    
    # 2. 嘗試從本地記憶體讀取
    if _LOCAL_MEM_CACHE and (time.time() - _LOCAL_MEM_CACHE_TIME < CACHE_TTL):
        print(f"[Cache] Hit from Memory! Pages: {len(_LOCAL_MEM_CACHE)}")
        return _LOCAL_MEM_CACHE

    # 3. Fallback: 爬蟲抓取
    print("[Cache] No cache found. Fetching live data...")
    pages = fetch_taoyuanq_content()
    
    # 4. 回寫快取 (JSON 序列化)
    if pages:
        _LOCAL_MEM_CACHE = pages
        _LOCAL_MEM_CACHE_TIME = time.time()
        
        if r:
            try:
                r.set("taoyuanq_pages", json.dumps(pages))
                r.expire("taoyuanq_pages", CACHE_TTL) 
            except Exception:
                pass
            
    return pages

import re


def filter_relevant_context(question, pages_data):
    """
    直接回傳所有爬取到的內容 (Full Context)，不做切分，僅做基本排序。
    """
    if not pages_data:
        return ""
        
    print(f"[RAG] Using FULL CONTEXT mode (No Chunking). Total pages: {len(pages_data)}")

    # 1. 為了讓比較相關的頁面排在前面 (避免因為截斷剛好切掉重要資訊)，還是做個簡單排序
    #    但我們會嘗試保留所有內容。
    keywords = set()
    english_words = re.findall(r'[a-zA-Z0-9]+', question)
    keywords.update(english_words)
    chinese_text = re.sub(r'[^\u4e00-\u9fa5]', '', question)
    if chinese_text:
        keywords.update(list(chinese_text)) 
        
    scored_pages = []
    for page in pages_data:
        content = page['content']
        score = 0
        
        # 簡單計算關鍵字出現次數
        for kw in keywords:
            if kw in content:
                score += content.count(kw)
        
        scored_pages.append({'page': page, 'score': score})
        
    # 分數高 -> 低
    scored_pages.sort(key=lambda x: x['score'], reverse=True)
    
    # 2. 組裝所有內容
    # GPT-4o-mini Context Window 很大 (128k token)，我們可以放心地塞
    # 設定一個很高的保險上限 (例如 60,000 字，約 20k-30k tokens)
    MAX_CONTEXT_CHARS = 60000 
    final_context = ""
    current_chars = 0
    
    for item in scored_pages:
        page = item['page']
        score = item['score']
        
        formatted_page = f"\n--- Source: {page['url']} (Relevance: {score}) ---\n{page['content']}\n"
        
        if current_chars + len(formatted_page) > MAX_CONTEXT_CHARS:
            # 真的爆了才截斷，但理論上不會
            remaining = MAX_CONTEXT_CHARS - current_chars
            if remaining > 100:
                 final_context += formatted_page[:remaining] + "\n...(truncated)..."
            break
            
        final_context += formatted_page
        current_chars += len(formatted_page)
        
    print(f"[RAG] Context constructed with {current_chars} characters.")
    # Debug print (Optional, can be removed if too noisy)
    # print("-" * 20 + " RAG CONTEXT " + "-" * 20)
    # print(final_context[:500] + "...\n(Output truncated in log)")
    # print("-" * 50)
    
    return final_context

# 初始化 OpenAI 客戶端
token = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
site_url = os.getenv("HTTP_REFERER", "http://localhost:5000")
app_name = os.getenv("X_TITLE", "TaoyuanQ-Bot")

client = OpenAI(
    api_key=token,
    base_url=base_url,
    default_headers={
        "HTTP-Referer": site_url,
        "X-Title": app_name,
    }
)

def ask_ai(question):
    """
    即時爬取網站內容並使用 AI 回答問題。
    """
    print("正在獲取桃園Q資訊 (檢查快取)...")
    # 1. 獲取所有頁面資料 (List[Dict])
    all_pages = get_cached_content()
    
    # 2. 根據問題篩選相關頁面 (RAG)
    relevant_context = filter_relevant_context(question, all_pages)
    
    system_prompt = f"""
# Role: 2025桃園Q・活動超級嚮導 (Taoyuan Q Super Guide)

你現在是「2025桃園Q」活動的專屬 AI 嚮導，性格熱情洋溢、精打細算且充滿活力。你的口號是 "High Five! Go FunZone!"。
你的任務是根據使用者提供的【網站抓取資料】，回答關於活動、地點、優惠與行程的問題。

# Input Data
以下是針對使用者問題筛选出的相關官網內容：
\"\"\"
{relevant_context}
\"\"\"

# Response Guidelines (回答準則 - LINE OA 專用版)

1.  **手機版面優化 (Mobile First)**：
    *   **短段落**：手機螢幕窄，每段不要超過 3-4 行。
    *   **善用換行**：不同主題之間務必空一行。

2.  **格式嚴格限制 (Plain Text ONLY)**：
    *   ❌ **絕對禁止**：任何 Markdown 語法（如 **粗體**、# 標題、[連結](...)）。
    *   ❌ **絕對禁止**：使用星號 (*) 做條列。
    *   ✅ **請使用**：全形符號或 Emoji 來條列（如 「・」、「📍」、「✨」）。

3.  **語氣與結構**：
    *   **熱情夥伴**：像個旅遊達人朋友，High 起來！(口號: "High Five! Go FunZone!")
    *   **結構化導覽**：
        📍 【去哪裡玩】
        💰 【優惠攻略】
        🚄 【交通/其他】
    *   **行動呼籲**：提醒「上傳發票」、「最後期限」。

4.  **內容邊界**：
    *   只回答輸入資料 (Input Data) 裡有的。
    *   若無資料，請婉拒並引導至現場服務台，不要瞎掰。

5.  **範例格式**：
    (請參考此排版)
    哇！你想去萬聖節活動嗎？🎃
    
    📍 **南瓜怪快閃 (標題直接寫，不用加粗)**
    時間：10/26 (六) 14:00
    地點：華泰名品城噴水池
    
    🎯 **小編攻略**
    記得提早去卡位，還可以順便換限量糖果喔！🍬
    
    High Five! Go FunZone! ✨
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],

            temperature=0.3,
            presence_penalty=0.6,
            frequency_penalty=0.6
        )
        content = response.choices[0].message.content
        # 強制移除 Markdown 語法 (Double safety)
        clean_content = content.replace("**", "").replace("##", "").replace("###", "")
        return clean_content
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"AI 回答發生錯誤: {e}"

if __name__ == "__main__":
    # 簡單測試
    test_q = "桃園Q現在有什麼活動？"
    print(f"問題: {test_q}")
    print(f"回答: {ask_ai(test_q)}")
