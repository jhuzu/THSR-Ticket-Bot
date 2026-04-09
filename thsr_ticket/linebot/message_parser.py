"""
LINE Bot 訊息解析器
解析使用者輸入的訂票指令

支援的格式:
  訂票 04/15 08:30-09:00 桃園→台南 2張
  訂票 2026-04-15 08:00-10:00 台北->左營 1張
  訂票 04/15 08:30-09:00 桃園→台南     (預設1張)
  說明 / 幫助 / help
"""

import re
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date


@dataclass
class ParseResult:
    """解析結果"""
    success: bool
    error_msg: str = ""

    # 訂票參數（success=True 時有值）
    date: str = ""          # YYYY-MM-DD
    time_range: str = ""    # HH:MM-HH:MM
    from_station: str = ""  # 使用者輸入的車站名（中文）
    to_station: str = ""    # 使用者輸入的車站名（中文）
    tickets: int = 1


def parse_booking_command(text: str) -> Optional[ParseResult]:
    """
    解析訂票指令
    回傳 None 表示不是訂票指令
    回傳 ParseResult 表示解析成功或失敗
    """
    text = text.strip()

    # 說明指令
    if text.lower() in ["說明", "幫助", "help", "?", "？", "使用說明"]:
        return None  # 由 Flask app 統一處理

    # 必須以「訂票」開頭
    if not text.startswith("訂票"):
        return None

    body = text[2:].strip()

    # 解析日期
    date_str = _parse_date(body)
    if not date_str:
        return ParseResult(
            success=False,
            error_msg="日期格式錯誤。\n範例：04/15 或 2026-04-15"
        )

    # 移除日期後繼續解析
    body = _remove_date(body)

    # 解析時間區間
    time_range = _parse_time_range(body)
    if not time_range:
        return ParseResult(
            success=False,
            error_msg="時間區間格式錯誤。\n範例：08:30-09:00"
        )
    body = _remove_time_range(body, time_range)

    # 解析車站
    stations = _parse_stations(body)
    if not stations:
        return ParseResult(
            success=False,
            error_msg="車站格式錯誤。\n範例：桃園→台南 或 台北->左營"
        )
    from_station, to_station, body = stations

    # 解析票數（可選，預設1）
    tickets = _parse_tickets(body)

    return ParseResult(
        success=True,
        date=date_str,
        time_range=time_range,
        from_station=from_station,
        to_station=to_station,
        tickets=tickets,
    )


def is_help_command(text: str) -> bool:
    """判斷是否為說明指令"""
    return text.strip().lower() in ["說明", "幫助", "help", "?", "？", "使用說明"]


# ── 內部解析函式 ──────────────────────────────────────────────


def _parse_date(text: str) -> Optional[str]:
    """解析日期，回傳 YYYY-MM-DD 格式"""
    year = datetime.now().year

    # MM/DD 格式
    m = re.search(r'(\d{1,2})/(\d{1,2})', text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            d = date(year, month, day)
            # 如果月份已過，自動跳下一年
            if d < date.today():
                d = date(year + 1, month, day)
            return d.strftime('%Y-%m-%d')
        except ValueError:
            return None

    # YYYY-MM-DD 格式
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if m:
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return d.strftime('%Y-%m-%d')
        except ValueError:
            return None

    return None


def _remove_date(text: str) -> str:
    """移除日期字串"""
    text = re.sub(r'\d{4}-\d{1,2}-\d{1,2}', '', text)
    text = re.sub(r'\d{1,2}/\d{1,2}', '', text)
    return text.strip()


def _parse_time_range(text: str) -> Optional[str]:
    """解析時間區間，回傳 HH:MM-HH:MM 格式"""
    m = re.search(r'(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})', text)
    if m:
        start, end = m.group(1), m.group(2)
        # 補齊小時位數
        start = _normalize_time(start)
        end = _normalize_time(end)
        return f"{start}-{end}"
    return None


def _normalize_time(t: str) -> str:
    h, m = t.split(':')
    return f"{int(h):02d}:{m}"


def _remove_time_range(text: str, time_range: str) -> str:
    """移除時間區間字串"""
    return re.sub(r'\d{1,2}:\d{2}\s*[-~]\s*\d{1,2}:\d{2}', '', text).strip()


def _parse_stations(text: str) -> Optional[tuple]:
    """解析車站，回傳 (from_station, to_station, remaining_text)"""
    # 支援 → 和 -> 和 ➔
    m = re.search(r'([^\s→\-\>➔]+)\s*[→\-\>➔]+\s*([^\s\d張]+)', text)
    if m:
        from_s = m.group(1).strip()
        to_s = m.group(2).strip()
        remaining = text[m.end():].strip()
        return from_s, to_s, remaining
    return None


def _parse_tickets(text: str) -> int:
    """解析票數，預設 1"""
    m = re.search(r'(\d+)\s*張', text)
    if m:
        n = int(m.group(1))
        return max(1, min(10, n))  # 限制在 1-10 之間
    return 1
