"""
高鐵自動訂票 CLI 入口
用法:
  python -m thsr_ticket.auto_booking --config booking_config.yaml
  python -m thsr_ticket.auto_booking -d 2026-04-15 -t 08:00-10:00 -f 台北 -o 左營 -n 2
"""

import sys
import argparse
from dataclasses import dataclass, field
from typing import Optional

import yaml

sys.path.append("./")

from thsr_ticket.configs.station_utils import parse_station, station_name_chinese


@dataclass
class BookingConfig:
    """訂票設定資料"""
    # 個人資訊
    personal_id: str = ""
    phone: str = ""

    # 訂票資訊
    date: str = ""                    # YYYY-MM-DD
    time_range: str = "06:00-23:00"   # HH:MM-HH:MM
    from_station: int = 2             # StationMapping value
    to_station: int = 12              # StationMapping value
    tickets: int = 1
    seat_prefer: str = "aisle"        # window / aisle / none

    # 自動化設定
    max_captcha_retries: int = 10
    auto_select_train: bool = True

    @classmethod
    def from_yaml(cls, path: str) -> "BookingConfig":
        """從 YAML 設定檔載入"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = cls()
        if personal := data.get("personal"):
            config.personal_id = str(personal.get("id", ""))
            config.phone = str(personal.get("phone", ""))

        if booking := data.get("booking"):
            config.date = str(booking.get("date", ""))
            config.tickets = int(booking.get("tickets", 1))
            config.seat_prefer = str(booking.get("seat_prefer", "aisle"))
            config.time_range = str(booking.get("time_range", "06:00-23:00"))

            if from_station := booking.get("from_station"):
                config.from_station = parse_station(str(from_station))
            if to_station := booking.get("to_station"):
                config.to_station = parse_station(str(to_station))

        if automation := data.get("automation"):
            config.max_captcha_retries = int(automation.get("max_captcha_retries", 5))
            config.auto_select_train = bool(automation.get("auto_select_train", True))

        return config

    def parse_time_range(self):
        """
        解析時間區間字串為 (start_hour, start_min, end_hour, end_min)

        Returns:
            (start_hour, start_min, end_hour, end_min)
        """
        parts = self.time_range.split("-")
        start = parts[0].strip().split(":")
        end = parts[1].strip().split(":")
        return (
            int(start[0]), int(start[1]),
            int(end[0]), int(end[1]),
        )

    def validate(self):
        """驗證設定是否完整"""
        errors = []
        if not self.personal_id:
            errors.append("缺少身分證字號 (personal.id)")
        if not self.date:
            errors.append("缺少出發日期 (booking.date)")
        if self.from_station == self.to_station:
            errors.append("起始站與終點站不能相同")
        if not (1 <= self.tickets <= 10):
            errors.append(f"票數必須在 1-10 之間，目前: {self.tickets}")
        if errors:
            raise ValueError("設定檔驗證失敗:\n" + "\n".join(f"  - {e}" for e in errors))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="高鐵自動訂票工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 使用設定檔
  python -m thsr_ticket.auto_booking --config booking_config.yaml

  # 使用設定檔 + 覆蓋日期和時間
  python -m thsr_ticket.auto_booking -c booking_config.yaml -d 2026-04-20 -t 14:00-18:00

  # 全部用命令列參數
  python -m thsr_ticket.auto_booking -d 2026-04-15 -t 08:00-10:00 -f 台北 -o 左營 -n 2 --id T225619095 --phone 0926615421

車站對照表:
  1.南港  2.台北  3.板橋  4.桃園  5.新竹  6.苗栗
  7.台中  8.彰化  9.雲林  10.嘉義  11.台南  12.左營
        """,
    )

    parser.add_argument("-c", "--config", help="YAML 設定檔路徑")
    parser.add_argument("-d", "--date", help="出發日期 (YYYY-MM-DD)")
    parser.add_argument("-t", "--time-range", help="時間區間 (HH:MM-HH:MM)")
    parser.add_argument("-f", "--from-station", help="起始站 (中文/英文/編號)")
    parser.add_argument("-o", "--to-station", help="終點站 (中文/英文/編號)")
    parser.add_argument("-n", "--tickets", type=int, help="成人票數 (1-10)")
    parser.add_argument("--id", help="身分證字號")
    parser.add_argument("--phone", help="手機號碼")
    parser.add_argument("--seat-prefer", choices=["window", "aisle", "none"],
                        help="座位偏好 (window/aisle/none)")

    return parser


def load_config(args) -> BookingConfig:
    """從設定檔和命令列參數合併載入設定"""
    # 先載入設定檔
    if args.config:
        config = BookingConfig.from_yaml(args.config)
    else:
        config = BookingConfig()

    # 命令列參數覆蓋設定檔
    if args.date:
        config.date = args.date
    if args.time_range:
        config.time_range = args.time_range
    if args.from_station:
        config.from_station = parse_station(args.from_station)
    if args.to_station:
        config.to_station = parse_station(args.to_station)
    if args.tickets is not None:
        config.tickets = args.tickets
    if args.id:
        config.personal_id = args.id
    if args.phone:
        config.phone = args.phone
    if args.seat_prefer:
        config.seat_prefer = args.seat_prefer

    return config


def print_config_summary(config: BookingConfig):
    """印出訂票設定摘要"""
    from_name = station_name_chinese(config.from_station)
    to_name = station_name_chinese(config.to_station)

    print("=" * 50)
    print("        高鐵自動訂票系統")
    print("=" * 50)
    print(f"  身分證字號: {config.personal_id[:3]}{'*' * (len(config.personal_id) - 3)}")
    print(f"  手機號碼:   {config.phone[:4]}{'*' * (len(config.phone) - 4)}")
    print(f"  出發日期:   {config.date}")
    print(f"  時間區間:   {config.time_range}")
    print(f"  起始站:     {from_name}")
    print(f"  終點站:     {to_name}")
    print(f"  票數:       {config.tickets} 張成人票")
    print(f"  座位偏好:   {config.seat_prefer}")
    print(f"  驗證碼重試: 最多 {config.max_captcha_retries} 次")
    print("=" * 50)


def main():
    parser = build_parser()
    args = parser.parse_args()

    # 載入設定
    try:
        config = load_config(args)
        config.validate()
    except Exception as e:
        print(f"設定錯誤: {e}")
        sys.exit(1)

    # 顯示設定摘要
    print_config_summary(config)
    print()

    # 執行自動訂票
    from thsr_ticket.controller.booking_flow_auto import AutoBookingFlow
    flow = AutoBookingFlow(config)
    flow.run()


if __name__ == "__main__":
    main()
