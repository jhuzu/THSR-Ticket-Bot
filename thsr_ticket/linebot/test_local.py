"""
本地測試 LINE Bot 邏輯（不需要實際連線 LINE）
模擬使用者傳訊息，印出 Bot 的回應內容
"""

import sys
sys.path.append("./")

from thsr_ticket.linebot.message_parser import parse_booking_command, is_help_command, HELP_TEXT if False else None

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


def simulate(text: str):
    print(f"\n使用者: {text}")
    print("Bot:", end=" ")

    from thsr_ticket.linebot.message_parser import parse_booking_command, is_help_command

    if is_help_command(text):
        print(HELP_TEXT)
        return

    result = parse_booking_command(text)
    if result is None:
        print("輸入「說明」查看使用方式，或直接輸入訂票指令：\n訂票 04/15 08:30-09:00 桃園→台南 2張")
        return

    if not result.success:
        print(f"指令格式錯誤：{result.error_msg}")
        return

    print(
        f"收到訂票請求，開始處理...\n"
        f"日期：{result.date}\n"
        f"時間：{result.time_range}\n"
        f"路線：{result.from_station} → {result.to_station}\n"
        f"票數：{result.tickets} 張\n"
        f"驗證碼辨識中，請稍候..."
    )
    print("\n[模擬模式：不實際執行訂票]")


if __name__ == "__main__":
    print("=== LINE Bot 本地測試 ===")
    print("輸入 'q' 離開\n")

    while True:
        try:
            text = input("你: ").strip()
            if text.lower() == 'q':
                break
            if text:
                simulate(text)
        except (KeyboardInterrupt, EOFError):
            break
