import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from openai import OpenAI
from scraper import fetch_taoyuanq_content
import time

# 快取設定
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
    獲取快取內容。優先使用 Redis，若失敗降級為本地快取或直接爬取。
    """
    global _LOCAL_MEM_CACHE, _LOCAL_MEM_CACHE_TIME

    # 1. 嘗試從 Redis 讀取
    r = get_redis_client()
    if r:
        try:
            cached = r.get("taoyuanq_content")
            if cached:
                print(f"[Cache] Hit from Redis! Length: {len(cached)}")
                # 同步更新本地快取，避免 Redis 突然斷線
                _LOCAL_MEM_CACHE = cached
                _LOCAL_MEM_CACHE_TIME = time.time()
                return cached
        except Exception:
            pass
    
    # 2. 嘗試從本地記憶體讀取 (Redis 掛掉或沒裝時)
    if _LOCAL_MEM_CACHE and (time.time() - _LOCAL_MEM_CACHE_TIME < CACHE_TTL):
        print(f"[Cache] Hit from Memory! (Redis unavailable) Length: {len(_LOCAL_MEM_CACHE)}")
        return _LOCAL_MEM_CACHE

    # 3. Fallback: 真的沒資料才爬蟲
    print("[Cache] No cache found (Redis & Local miss). Fetching live data...")
    content = fetch_taoyuanq_content()
    
    # 4. 回寫快取
    # 寫入本地記憶體
    if content:
        _LOCAL_MEM_CACHE = content
        _LOCAL_MEM_CACHE_TIME = time.time()

    # 嘗試回寫 Redis
    if r and content:
        try:
            r.set("taoyuanq_content", content)
            r.expire("taoyuanq_content", CACHE_TTL) 
        except Exception:
            pass
            
    return content

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
    # 使用快取機制獲取內容
    live_knowledge = get_cached_content()
    
    system_prompt = f"""
# Role: 2025桃園Q・活動超級嚮導 (Taoyuan Q Super Guide)

你現在是「2025桃園Q」活動的專屬 AI 嚮導，性格熱情洋溢、精打細算且充滿活力。你的口號是 "High Five! Go FunZone!"。
你的任務是根據使用者提供的【網站抓取資料】，回答關於活動、地點、優惠與行程的問題。

# Input Data
以下是從官網即時抓取的內容，這是你唯一已知的資訊來源：
\"\"\"
{live_knowledge}
\"\"\"

# Response Guidelines (回答準則)

1.  **熱情與帶入感**：
    * 請使用像朋友般輕鬆、興奮的語氣（例如：「哇！這預算太完美了！」、「記得千萬別錯過...」）。
    * 適度使用 Emoji 來增加視覺活潑度 (🎃, 💰, ✨, 🚄)。
    * 回答開頭或結尾可以融入活動口號 "High Five! Go FunZone!"。

2.  **攻略型思維 (不僅僅是回答，而是提供策略)**：
    * **預算最大化**：若使用者提到金額，請**主動**幫他計算戰略。
        * *範例*：「你有 1000 元？太棒了！這代表你可以累積 **2 次** 抽 $88,888 的機會（每滿 500 抽一次）！」
    * **行動呼籲 (CTA)**：不斷提醒使用者「關鍵動作」（如：現在立刻上傳票根、結帳記得拿發票）。

3.  **結構化但自然**：不要死板的條列，而是用「導覽」的方式呈現。
    * 📍 **去哪裡玩 (Hot Spots)**：根據網站列出的合作店家（如華泰、Xpark...）推薦。
    * 🎯 **你的專屬攻略 (Strategy)**：針對使用者條件（預算/時間）的客製化建議。
    * 🎁 **不花錢也能玩 (Freebie)**：強調尋寶、即時抽等免費活動。
    * � **小編提醒**：任何關於截止日期、地點限制的重要備註。

4.  **資料邊界控制 (Strict Context)**：
    * **嚴格限制**：只能回答【網站抓取資料】內有的資訊。
    * **圓滑避險**：如果資料裡找不到答案（例如：「停車費多少？」網站若沒寫），請誠實但委婉地說：「哎呀，目前的活動官網資料中沒有特別提到這點，建議您直接詢問現場服務台，或是專注在我們的抽獎活動上喔！」**絕對不要瞎掰不存在的資訊。**
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
        return response.choices[0].message.content
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"AI 回答發生錯誤: {e}"

if __name__ == "__main__":
    # 簡單測試
    test_q = "桃園Q現在有什麼活動？"
    print(f"問題: {test_q}")
    print(f"回答: {ask_ai(test_q)}")
