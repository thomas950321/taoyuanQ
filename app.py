import os
import threading
import time
import json
import requests
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

def send_loading_animation(chat_id, loading_seconds=20):
    """
    呼叫 LINE Loading Animation API
    """
    url = "https://api.line.me/v2/bot/chat/loading/start"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('LINE_CHANNEL_ACCESS_TOKEN')}"
    }
    data = {
        "chatId": chat_id,
        "loadingSeconds": loading_seconds
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=5)
        if response.status_code == 202:
            app.logger.info(f"Loading animation started for {chat_id}")
        else:
            app.logger.warning(f"Failed to start loading animation: {response.text}")
    except Exception as e:
        app.logger.error(f"Error sending loading animation: {e}")

def process_message_background(event):
    """
    背景處理訊息：顯示 Loading -> AI 思考 -> 回覆
    """
    try:
        # 1. 取得 chatId (優先使用 userId, 其次 groupId/roomId)
        source = event.source
        chat_id = None
        if hasattr(source, 'user_id') and source.user_id:
            chat_id = source.user_id
        elif hasattr(source, 'group_id') and source.group_id:
            chat_id = source.group_id
        elif hasattr(source, 'room_id') and source.room_id:
            chat_id = source.room_id
            
        # 2. 顯示 Loading Animation
        if chat_id:
            send_loading_animation(chat_id)
            
        # 3. 執行 AI 運算
        user_message = event.message.text
        ai_response = ask_ai(user_message)
        
        # 4. 回覆訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
    except Exception as e:
        app.logger.error(f"Background processing error: {e}")


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
    # 啟動背景執行緒處理，讓 Webhook 能立刻回傳 200 OK
    thread = threading.Thread(target=process_message_background, args=(event,))
    thread.start()


if __name__ == "__main__":
    # 本地測試使用 5000 端口
    app.run(host='0.0.0.0', port=5000)
