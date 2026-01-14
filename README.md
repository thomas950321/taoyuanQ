# 桃園Q AI 活動導覽助手 (TaoyuanQ Bot)

這是一個專為「2025桃園Q」活動設計的 AI LINE 機器人。
它具備 **高併發承載能力**，結合了即時網站爬取、Redis 快取與 OpenAI 生成技術，能即時回答使用者關於活動、優惠與地點的疑問。

---

## 🚀 核心功能與特色

### 1. ⚡ **高效能 RAG 架構 (Retrieval-Augmented Generation)**
- **Redis 分散式快取**: 解決多 Worker 資料不同步問題，大幅降低官網流量壓力。
- **背景自動排程**: 內建 `APScheduler` 每 30 分鐘自動更新資料，避免使用者等待爬蟲時間。
- **自動降級 (Failover)**: 若 Redis失效，自動切換為本地記憶體或即時爬取，確保服務不中斷。

### 2. 🤖 **AI 智能導覽**
- **角色扮演**: 化身為熱情的活動嚮導，提供預算規劃與行程建議。
- **即時資訊**: 資料來源直接同步自活動官網，確保資訊不落後。

---

## 📂 專案結構圖

```text
taoyuanq-bot/
├── app.py              # [核心] Flask Web Server & LINE Webhook 入口
├── rag_engine.py       # [核心] AI 邏輯層 (負責從 Redis 取資料 + 呼叫 OpenAI)
├── scheduler.py        # [排程] 背景任務 (每 30 分鐘爬取官網 -> 寫入 Redis)
├── scraper.py          # [工具] 爬蟲模組 (抓取網頁原始資料)
├── requirements.txt    # 相依套件清單
├── Procfile            # 部署設定 (Render/Heroku)
└── tests/
    └── test_scalability.py  # 自動化測試 (模擬高流量與快取機制)
```

### 架構原理
1. `scheduler.py` 定期爬取官網，將資料存入 `Redis`。
2. 使用者傳送訊息給 LINE Bot。
3. `app.py` 收到 Webhook，呼叫 `rag_engine.py`。
4. `rag_engine` 從 `Redis` 秒讀資料 (不需等待爬蟲)，組合成 Prompt。
5. OpenAI 生成回答，回傳給使用者。

---

## 🛠 安裝與啟動教學

### 1. 環境準備
- Python 3.9+
- Redis Server (建議安裝，或使用雲端 Redis)
    - *若無 Redis，系統仍可執行，但效能會受限於單一 Process*

### 2. 安裝套件
下載專案後，請執行：
```bash
pip install -r requirements.txt
```

### 3. 設定環境變數 (.env)
請在專案根目錄建立 `.env` 檔案，填入以下資訊：
```ini
# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN=你的LINE_Token
LINE_CHANNEL_SECRET=你的LINE_Secret

# OpenAI 設定 (支援 OpenAI 或相容 API)
OPENAI_API_KEY=你的API_Key
# OPENAI_BASE_URL=https://openrouter.ai/api/v1  # 若使用 OpenRouter 請開啟此行

# Redis 設定 (若不填則預設連線 localhost:6379)
REDIS_URL=redis://localhost:6379/0
```

### 4. 啟動服務

#### 開發模式 (Development)
直接執行 `app.py`，它會自動在背景啟動排程器：
```bash
python app.py
```

#### 生產環境 (Production / Docker)
建議使用 `gunicorn` 啟動，搭配多個 Workers 提升效能：
```bash
gunicorn app:app
```
*注意：在多 Worker 模式下，建議將 Scheduler 獨立成一個 Worker 執行，或確保 `app.py` 中的啟動邏輯有處理 Lock (目前程式碼已包含簡易 Lock 機制)*。

---

## 🧪 測試與驗證

本專案包含完整的單元測試，可驗證快取邏輯與穩定性。

執行測試指令：
```bash
python -m unittest tests/test_scalability.py
```
- ✅ **Cache Hit**: 確認有快取時依賴 Redis，不重複爬蟲。
- ✅ **Cache Miss**: 確認無快取時自動觸發爬取。
- ✅ **Failover**: 確認 Redis 當機時系統能自動存活。

---

## ☁️ 部署建議 (Render / Heroku)

1. **建立 Redis 實例**: 在雲端平台 (如 Render Redis) 建立一個 Redis，並取得 `REDIS_URL`。
2. **設定環境變數**: 將上述 `.env` 的內容填入平台的 Environment Variables。
3. **部署 Web Service**: 指向本 Repository。
4. **檢查 Log**: 確認看到 `Scheduler started` 與 `Redis connection success` 字樣。
