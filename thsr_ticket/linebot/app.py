"""
LINE Bot Flask Webhook Server
高鐵自動訂票 LINE Bot 主程式

不依賴 line-bot-sdk，直接用 requests 呼叫 LINE API
"""

import os
import sys
import time
import json
import hmac
import hashlib
import base64
import threading

import requests as http_requests
from flask import Flask, request, abort
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

load_dotenv()

app = Flask(__name__)

# 記錄 server 啟動時間，用來判斷是否剛從睡眠喚醒
_start_time = time.time()

# LINE Bot 憑證（從 .env 讀取）
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

if not LINE_CHANNEL_SECRET or not LINE_CHANNEL_ACCESS_TOKEN:
    print("錯誤：缺少 LINE_CHANNEL_SECRET 或 LINE_CHANNEL_ACCESS_TOKEN")
    print("請確認 .env 檔案設定正確")
    sys.exit(1)

# 預設訂票人個資（從 booking_config.yaml 讀取）
_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'booking_config.yaml'
)

HELP_TEXT = """\
[高鐵自動訂票 Bot]

指令格式：
訂票 日期 時間區間 起站→終站 張數

範例：
  訂票 04/15 08:30-09:00 桃園→台南 2張
  訂票 04/20 14:00-16:00 台北->左營
  訂票 2026-05-01 07:00-08:00 南港→高雄 1張

車站：南港、台北、板橋、桃園、新竹、苗栗、
      台中、彰化、雲林、嘉義、台南、左營

說明 / 幫助 → 顯示此訊息"""


# ── LINE API 工具函式 ──────────────────────────────────────────


def verify_signature(body: str, signature: str) -> bool:
    """驗證 LINE webhook 簽名"""
    hash_val = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(hash_val).decode('utf-8')
    return hmac.compare_digest(expected, signature)


def reply_message(reply_token: str, text: str):
    """回覆 LINE 訊息"""
    http_requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        },
        json={
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": text}],
        },
    )


def push_message(user_id: str, text: str):
    """主動推送 LINE 訊息"""
    http_requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        },
        json={
            "to": user_id,
            "messages": [{"type": "text", "text": text}],
        },
    )


# ── Flask 路由 ──────────────────────────────────────────


@app.route("/ping", methods=["GET", "HEAD"])
def ping():
    """Keep-alive 端點，給 UptimeRobot 定期 ping 使用"""
    uptime = int(time.time() - _start_time)
    return {"status": "ok", "uptime_seconds": uptime}, 200


@app.route("/", methods=["GET"])
def index():
    return {"bot": "THSR 訂高鐵", "status": "running"}, 200


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    if not verify_signature(body, signature):
        abort(400)

    data = json.loads(body)
    events = data.get("events", [])

    for event in events:
        if event.get("type") == "message" and event["message"].get("type") == "text":
            handle_text_message(event)

    return "OK"


# ── 訊息處理 ──────────────────────────────────────────


def handle_text_message(event):
    text = event["message"]["text"].strip()
    reply_token = event["replyToken"]
    user_id = event["source"]["userId"]

    from thsr_ticket.linebot.message_parser import parse_booking_command, is_help_command

    # 若 server 剛啟動（可能是從睡眠喚醒），先告知使用者稍後重試
    uptime = time.time() - _start_time
    if uptime < 15:
        reply_message(
            reply_token,
            "Bot 剛從待機狀態喚醒，請稍等 10 秒後再傳一次指令。\n"
            "（這只有第一次用時才會發生）"
        )
        return

    # 說明指令
    if is_help_command(text):
        reply_message(reply_token, HELP_TEXT)
        return

    # 解析訂票指令
    result = parse_booking_command(text)
    if result is None:
        reply_message(
            reply_token,
            "輸入「說明」查看使用方式，或直接輸入訂票指令：\n訂票 04/15 08:30-09:00 桃園→台南 2張"
        )
        return

    if not result.success:
        reply_message(reply_token, f"指令格式錯誤：{result.error_msg}\n\n輸入「說明」查看使用方式")
        return

    # 開始訂票流程（非同步執行，避免 webhook 逾時）
    reply_message(reply_token, _format_booking_start(result))
    threading.Thread(
        target=_run_booking,
        args=(user_id, result),
        daemon=True
    ).start()


def _run_booking(user_id: str, result):
    """在背景執行訂票，完成後主動推送結果"""
    from thsr_ticket.auto_booking import BookingConfig
    from thsr_ticket.controller.booking_flow_auto import AutoBookingFlow

    try:
        # 從 booking_config.yaml 讀取個資
        config = BookingConfig.from_yaml(_DEFAULT_CONFIG_PATH)

        # 套用使用者指定的參數
        config.date = result.date
        config.time_range = result.time_range
        config.tickets = result.tickets

        from thsr_ticket.configs.station_utils import parse_station
        config.from_station = parse_station(result.from_station)
        config.to_station = parse_station(result.to_station)

        config.validate()
    except Exception as e:
        push_message(user_id, f"設定錯誤：{e}")
        return

    # 執行訂票
    try:
        flow = AutoBookingFlow(config)
        resp = flow.run()

        if resp is None:
            push_message(user_id, "訂票失敗，請稍後再試或手動前往高鐵官網訂票。")
            return

        # 解析結果並推送
        from thsr_ticket.view_model.booking_result import BookingResult
        tickets = BookingResult().parse(resp.content)
        push_message(user_id, _format_booking_success(tickets[0]))

    except Exception as e:
        push_message(user_id, f"訂票過程發生錯誤：{e}\n請稍後再試。")


def _format_booking_start(result) -> str:
    return (
        f"收到訂票請求，開始處理...\n"
        f"\n"
        f"日期：{result.date}\n"
        f"時間：{result.time_range}\n"
        f"路線：{result.from_station} → {result.to_station}\n"
        f"票數：{result.tickets} 張\n"
        f"\n"
        f"驗證碼辨識中，請稍候..."
    )


def _format_booking_success(ticket) -> str:
    return (
        f"訂票成功！\n"
        f"{'─' * 20}\n"
        f"訂位代號：{ticket.id}\n"
        f"繳費期限：{ticket.payment_deadline}\n"
        f"{'─' * 20}\n"
        f"日期：{ticket.date}\n"
        f"車次：{ticket.train_id}\n"
        f"{ticket.start_station} {ticket.depart_time} → "
        f"{ticket.dest_station} {ticket.arrival_time}\n"
        f"{'─' * 20}\n"
        f"座位：{ticket.seat}\n"
        f"票種：{ticket.ticket_num_info}\n"
        f"總價：{ticket.price}\n"
        f"{'─' * 20}\n"
        f"請至官方管道完成付款取票"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
