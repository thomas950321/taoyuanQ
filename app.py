import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from rag_engine import ask_ai

app = Flask(__name__)
from scheduler import start_scheduler

# 在 App 啟動時嘗試啟動排程器 (注意: 生產環境 Gunicorn 若多 Worker 需避免重開啟動)
if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
    # 這裡只在非常簡單的部署或第一次加載時執行
    # 若在 Gunicorn 下，建議 Scheduler 獨立一支 Process 跑，或是使用一個 Dedicated Worker
    # 此處為簡化範例：
    try:
        start_scheduler()
    except Exception as e:
        app.logger.error(f"Failed to start scheduler: {e}")

# 從環境變數讀取 LINE API 金鑰 (部署時需設定)
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET', 'YOUR_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 LINE 請求標頭中的簽章
    signature = request.headers['X-Line-Signature']

    # 獲取請求內容
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 驗證簽章並處理訊息
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    # 呼叫 AI 引擎獲取答案
    ai_response = ask_ai(user_message)
    
    # 回傳訊息給使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_response)
    )

if __name__ == "__main__":
    # 本地測試使用 5000 端口
    app.run(host='0.0.0.0', port=5000)
