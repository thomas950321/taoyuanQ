# 桃園Q 即時 AI LINE 機器人製作教學 (動態爬蟲版)

本專案實作了一個能「即時爬取」桃園Q官網內容並由 AI 生成回答的 LINE 機器人。與靜態知識庫不同，本版本在每次收到問題時都會訪問官網，確保資訊與網站同步更新。

## 🚀 核心特色
- **動態爬蟲**: 使用 `requests` 與 `BeautifulSoup` 即時抓取官網文字。
- **即時 RAG**: AI 根據當下抓取的內容進行分析，不瞎掰。
- **全免費方案**: 建議部署於 Render 或 Vercel。

---

## 📂 專案結構
```text
taoyuanq-bot/
├── app.py              # LINE Webhook 伺服器
├── scraper.py          # 即時爬蟲模組 (負責抓取官網)
├── rag_engine.py       # AI 回答邏輯 (整合爬蟲與 OpenAI)
├── test_ai.py          # 繞過 LINE 的即時測試腳本
├── requirements.txt    # 必要的套件清單
└── README.md           # 本教學文件
```

---

## 🛠 快速開始
1. **安裝套件**:
   ```bash
   pip install -r requirements.txt
   ```
2. **設定環境變數**:
   在您的電腦或雲端平台上設定以下變數：
   - `OPENAI_API_KEY`: 您的 AI API 金鑰。
   - `LINE_CHANNEL_ACCESS_TOKEN`: LINE 存取權杖。
   - `LINE_CHANNEL_SECRET`: LINE 頻道密鑰。
3. **本地測試 (繞過 LINE)**:
   執行以下指令，AI 會即時爬取官網並回答您的問題：
   ```bash
   python test_ai.py
   ```

---

## ☁️ 部署至 Render (免費)
1. 將此資料夾上傳至 GitHub。
2. 在 [Render.com](https://render.com/) 建立新的 **Web Service**。
3. 設定環境變數並部署。
4. 將 LINE Developers Console 的 Webhook URL 指向 `https://您的網址/callback`。

---

## ⚠️ 注意事項
- **爬取延遲**: 因為每次都會即時爬取，回答速度會比靜態版慢約 2-5 秒。
- **網站結構變更**: 若桃園Q官網大幅改版，可能需要調整 `scraper.py` 中的抓取邏輯。
- **不瞎掰保證**: 程式已設定 System Prompt，若官網無相關資訊，AI 會誠實回答不知道。
