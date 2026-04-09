"""
本機完整測試腳本
直接呼叫 Bot 的處理邏輯，不需要 LINE 連線或 tunnel
"""

import sys
import hashlib
import hmac
import json
import base64

sys.path.append("./")

from dotenv import load_dotenv
load_dotenv()

# 引入 Flask app 但不啟動它
from thsr_ticket.linebot.app import (
    _format_booking_start,
    _format_booking_success,
    HELP_TEXT,
)
from thsr_ticket.linebot.message_parser import parse_booking_command, is_help_command


def simulate_user_message(text: str, dry_run: bool = True):
    """
    模擬使用者發送訊息給 Bot

    dry_run=True  → 只測試解析邏輯，不實際訂票
    dry_run=False → 執行完整訂票流程（會真的訂票！）
    """
    print(f"\n{'='*50}")
    print(f"使用者: {text}")
    print(f"{'='*50}")

    # 說明指令
    if is_help_command(text):
        print(f"\nBot 回應:\n{HELP_TEXT}")
        return

    # 解析訂票指令
    result = parse_booking_command(text)

    if result is None:
        print("\nBot 回應: 輸入「說明」查看使用方式，或直接輸入訂票指令：")
        print("訂票 04/15 08:30-09:00 桃園→台南 2張")
        return

    if not result.success:
        print(f"\nBot 回應: 指令格式錯誤：{result.error_msg}")
        return

    # 顯示 Bot 的第一則回應
    print(f"\nBot 回應 (第一則):\n{_format_booking_start(result)}")

    if dry_run:
        print("\n[模擬模式] 不實際執行訂票")
        print("\n解析結果:")
        print(f"  日期: {result.date}")
        print(f"  時間: {result.time_range}")
        print(f"  路線: {result.from_station} → {result.to_station}")
        print(f"  票數: {result.tickets} 張")
        return

    # 實際執行訂票
    print("\n[實際訂票模式] 開始訂票...")
    try:
        from thsr_ticket.auto_booking import BookingConfig
        from thsr_ticket.controller.booking_flow_auto import AutoBookingFlow
        from thsr_ticket.configs.station_utils import parse_station
        from thsr_ticket.view_model.booking_result import BookingResult

        config = BookingConfig.from_yaml("booking_config.yaml")
        config.date = result.date
        config.time_range = result.time_range
        config.tickets = result.tickets
        config.from_station = parse_station(result.from_station)
        config.to_station = parse_station(result.to_station)
        config.validate()

        flow = AutoBookingFlow(config)
        resp = flow.run()

        if resp:
            tickets = BookingResult().parse(resp.content)
            msg = _format_booking_success(tickets[0])
            print(f"\nBot 推送 (訂票結果):\n{msg}")
        else:
            print("\nBot 推送: 訂票失敗，請稍後再試")

    except Exception as e:
        print(f"\n錯誤: {e}")


def run_interactive():
    """互動式測試模式"""
    print("=== LINE Bot 本機互動測試 ===")
    print("dry_run 模式：只測試解析，不實際訂票")
    print("輸入 'go' 切換到實際訂票模式（小心！）")
    print("輸入 'q' 離開\n")

    dry_run = True
    while True:
        try:
            text = input(f"你 ({'模擬' if dry_run else '實際訂票'}): ").strip()
            if not text:
                continue
            if text.lower() == 'q':
                break
            if text.lower() == 'go':
                dry_run = not dry_run
                print(f"切換為: {'模擬模式' if dry_run else '實際訂票模式 ⚠️'}")
                continue
            simulate_user_message(text, dry_run=dry_run)
        except (KeyboardInterrupt, EOFError):
            break

    print("\n測試結束")


def run_preset_tests():
    """執行一組預設測試案例（全部 dry_run）"""
    test_cases = [
        "說明",
        "訂票 04/20 08:30-09:00 桃園→台南 2張",
        "訂票 04/20 14:00-16:00 台北->左營",
        "訂票 2026-05-01 07:00-08:00 南港→高雄 1張",
        "你好",
        "訂票 04/20 桃園→台南",          # 缺時間（應報錯）
        "訂票 04/20 08:00-10:00 ABC→台南", # 錯誤車站（後面訂票會報錯）
    ]
    for t in test_cases:
        simulate_user_message(t, dry_run=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LINE Bot 本機測試")
    parser.add_argument("--preset", action="store_true", help="執行預設測試案例")
    parser.add_argument("--book", action="store_true", help="實際執行訂票（危險！）")
    parser.add_argument("--msg", help="直接測試一則訊息")
    args = parser.parse_args()

    if args.preset:
        run_preset_tests()
    elif args.msg:
        simulate_user_message(args.msg, dry_run=not args.book)
    else:
        run_interactive()
