import os
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# LINEチャンネルの環境変数から情報を取得
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

if not LINE_CHANNEL_SECRET or not LINE_CHANNEL_ACCESS_TOKEN:
    raise ValueError("環境変数 LINE_CHANNEL_SECRET または LINE_CHANNEL_ACCESS_TOKEN が設定されていません。")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 対応地域名と気象庁エリアコードのマップ
AREA_CODE_MAP = {
    "東京": "130000",
    "大阪": "270000",
    "名古屋": "230000",
    "静岡": "220000",
    "札幌": "016000",
    "福岡": "400000",
}

@app.route("/")
def home():
    return "LINE Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text.strip()

    # 「今日の天気」というキーワードが含まれていたら、東京の天気を返す
    if "今日の天気" in user_message:
        area_code = AREA_CODE_MAP.get("東京")
    else:
        # 地域名が含まれていたら対応コードを取得
        area_code = AREA_CODE_MAP.get(user_message)

    if area_code:
        forecast_url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
        try:
            res = requests.get(forecast_url)
            res.raise_for_status()
            data = res.json()

            # 1日目の天気情報を取得
            area_name = data[0]["timeSeries"][0]["areas"][0]["area"]["name"]
            weather = data[0]["timeSeries"][0]["areas"][0]["weathers"][0]
            reply = f"{area_name}の今日の天気は「{weather}」です。"
        except Exception as e:
            reply = f"天気情報の取得に失敗しました: {str(e)}"
    else:
        reply = "地域名を送ってください（例: 東京、大阪、静岡など）"

    # ユーザーに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
