# 桃園Q AI 活動導覽助手 (TaoyuanQ Bot)

這是一個專為「2025桃園Q」活動設計的 AI LINE 機器人。
主要特色為導入 **Advanced RAG (Retrieval-Augmented Generation)** 技術，利用網站爬蟲即時獲取活動資訊，並透過高準確度的檢索增強生成技術，提供精準的活動導覽與問答服務。

---

## 🚀 核心功能與特色

### 1. 🧠 **Advanced RAG 架構 (先進檢索增強生成)**
本專案摒棄傳統僅依賴關鍵字匹配的做法，採用更先進的 RAG 流程以提升回答品質：

1.  **高保真網頁解析 (High-Fidelity Parsing)**:
    *   使用 **Docling** (`DocumentConverter`) 將複雜的 HTML 網頁精準轉換為結構化的 Markdown 格式。
    *   有效保留網頁中的表格、清單與標題層級，讓 AI 能理解上下文結構。

2.  **父子文檔檢索 (Parent Document Retrieval)**:
    *   **Chunking (切分策略)**: 採用 `RecursiveCharacterTextSplitter` 進行雙層切分。
        *   **Child Chunks (索引塊)**: 小片段 (400 chars)，用於計算 Embedding 與精準搜尋。
        *   **Parent Chunks (內容塊)**: 大片段 (2000 chars)，包含完整的上下文資訊。
    *   **Retrieval (檢索機制)**: 當使用者的問題匹配到某個 "Child Chunk" 時，系統會回傳其所屬的完整 "Parent Chunk"。
    *   **優勢**: 兼具「精準搜尋」與「完整上下文」，避免斷章取義。

3.  **向量資料庫 (Vector Store)**:
    *   使用 **ChromaDB** 儲存向量索引。
    *   搭配 **OpenAI Embeddings (text-embedding-3-small)** 進行語意向量化。

### 2. 🤖 **AI 智能導覽 (LINE OA 優化)**
- **角色扮演**: 化身為「2025桃園Q・活動超級嚮導」，口號 "High Five! Go FunZone!"。
- **LINE 格式優化**: 專為手機介面設計的排版，禁用 Markdown，改以 Emoji 與分段呈現清晰易讀的資訊。
- **Token 監控**: 支援在測試模式下查看每次對話的 Token 消耗量 (`Input` / `Output` / `Total`)，利於成本控管。

---

## 📂 專案結構圖

```text
taoyuanq-bot/
├── advanced_rag.py     # [核心] Advanced RAG 邏輯 (爬蟲 -> Docling 解析 -> Chroma 向量化 -> 檢索 -> LLM)
├── app.py              # [入口] Flask Web Server & LINE Webhook 處理
├── test_console.py     # [工具] 本地測試終端機 (支援 Token 使用量顯示)
├── scheduler.py        # [排程] (目前作為參考，實際爬蟲邏輯整併於 advanced_rag)
├── scraper.py          # [輔助] 基礎網頁連結爬取工具
├── requirements.txt    # 相依套件清單
└── Dockerfile / Procfile # 部署設定
```

### RAG 運作流程 (advanced_rag.py)
1. **Initialize**: 啟動時檢查是否需要重建索引。
2. **Crawl & Parse**: 
    - 爬蟲抓取 `https://a18.taoyuanq.com/zh` 及其子頁面。
    - `Docling` 將 HTML 轉為 Markdown。
3. **Index**: 
    - 透過 `ParentDocumentRetriever` 將文檔切分為 Parent/Child 兩層。
    - Child chunks 存入 ChromaDB (Vector Store)。
    - Parent chunks 存入 InMemoryStore (Doc Store)。
4. **Query**:
    - 使用者提問 -> 搜尋最相關的 Child chunks -> 取出對應的 Parent chunks。
    - 將 Parent chunks 組合為 context，放入 System Prompt。
5. **Generate**:
    - 呼叫 OpenAI `gpt-4o-mini` 生成符合 LINE 格式的回答。
    - (Optional) 回傳 Token Usage 數據。

---

## 🛠 安裝與使用教學

### 1. 環境準備
- Python 3.10+
- OpenAI API Key

### 2. 安裝套件
```bash
pip install -r requirements.txt
```

### 3. 設定環境變數
請建立 `.env` 檔案：
```ini
LINE_CHANNEL_ACCESS_TOKEN=你的LINE_Token
LINE_CHANNEL_SECRET=你的LINE_Secret
OPENAI_API_KEY=你的OpenAI_API_Key
# OPENAI_BASE_URL=https://openrouter.ai/api/v1  # 若使用 OpenRouter
```

### 4. 啟動與測試

#### 🖥️ 本地測試模式 (推薦)
使用 `test_console.py` 進行對話測試，支援顯示 Token 消耗。

**互動模式 (Interactive Mode):**
```bash
python test_console.py
```
> 輸入問題後，Bot 會回答並顯示 `[Token Usage] Input: 1500, Output: 300, Total: 1800`。

**單次問答 (One-shot Mode):**
```bash
python test_console.py "請問有什麼優惠活動？"
```

#### 🌐 啟動 Web Server (LINE Webhook)
```bash
python app.py
```
- 伺服器預設運行於 `http://0.0.0.0:5000`。
- 需搭配 `ngrok` 或部署至雲端 (如 Render) 以供 LINE Platform 連線。

---

## ☁️ 部署注意事項

1. **ChromaDB Persistence**: 在無狀態容器 (如 Render Free Tier) 重啟後，ChromaDB 資料會重置。建議在應用程式啟動時執行一次 `fetch_and_process_website()` 以確保有資料可查。
2. **記憶體用量**: `Docling` 與 `Chroma` 載入模型與索引會消耗一定記憶體，部署時請留意資源限制。
