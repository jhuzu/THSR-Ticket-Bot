"""
自動化首頁流程：自動填寫訂票參數 + 驗證碼辨識
"""

import json
from typing import Tuple

from bs4 import BeautifulSoup
from requests.models import Response

from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.configs.web.param_schema import BookingModel
from thsr_ticket.configs.web.parse_html_element import BOOKING_PAGE
from thsr_ticket.configs.common import AVAILABLE_TIME_TABLE
from thsr_ticket.ml.captcha_solver import solve_captcha
from thsr_ticket.controller.booking_flow_auto import CaptchaInvalidError


class FirstPageFlowAuto:
    def __init__(self, client: HTTPRequest, config) -> None:
        self.client = client
        self.config = config

    def run(self) -> Response:
        # 取得訂票頁面
        book_page = self.client.request_booking_page().content
        img_resp = self.client.request_security_code_img(book_page).content
        page = BeautifulSoup(book_page, features='html.parser')

        # 自動辨識驗證碼
        captcha_code = solve_captcha(img_resp)

        if not captcha_code:
            print("  驗證碼辨識失敗（格式不正確），跳過此次")
            raise CaptchaInvalidError("辨識結果非 4 碼英數字")

        print(f"  驗證碼辨識結果: {captcha_code}")

        # 根據時間區間選擇最接近的出發時間
        outbound_time = self._select_time_from_range()
        print(f"  選擇出發時間: {outbound_time}")

        # 座位偏好
        seat_prefer = self._resolve_seat_prefer(page)

        # 建立表單
        book_model = BookingModel(
            start_station=self.config.from_station,
            dest_station=self.config.to_station,
            outbound_date=self.config.date,
            outbound_time=outbound_time,
            adult_ticket_num=f"{self.config.tickets}F",
            seat_prefer=seat_prefer,
            types_of_trip=_parse_types_of_trip_value(page),
            search_by=_parse_search_by(page),
            security_code=captcha_code,
        )

        json_params = book_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        resp = self.client.submit_booking_form(dict_params)
        return resp

    def _select_time_from_range(self) -> str:
        """
        根據設定的時間區間，選擇 AVAILABLE_TIME_TABLE 中
        落在區間內的最早時間。
        """
        start_h, start_m, end_h, end_m = self.config.parse_time_range()
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        for time_code in AVAILABLE_TIME_TABLE:
            minutes = _time_code_to_minutes(time_code)
            if start_minutes <= minutes <= end_minutes:
                return time_code

        # 找不到完全匹配的，選最接近 start 的
        print(f"  時間區間 {self.config.time_range} 內無精確匹配，選擇最接近的時間")
        best = None
        best_diff = float('inf')
        for time_code in AVAILABLE_TIME_TABLE:
            minutes = _time_code_to_minutes(time_code)
            diff = abs(minutes - start_minutes)
            if diff < best_diff:
                best_diff = diff
                best = time_code
        return best

    def _resolve_seat_prefer(self, page: BeautifulSoup) -> str:
        """
        根據設定決定座位偏好值
        高鐵網頁的座位偏好選項值：
        - 0: 無偏好
        - 1: 靠窗
        - 2: 走道
        """
        prefer_map = {
            "none": "0",
            "window": "1",
            "aisle": "2",
        }
        prefer = self.config.seat_prefer.lower()
        if prefer in prefer_map:
            return prefer_map[prefer]

        # fallback: 從頁面解析預設值
        options = page.find(**BOOKING_PAGE["seat_prefer_radio"])
        preferred_seat = options.find_next(selected='selected')
        return preferred_seat.attrs['value']


def _time_code_to_minutes(time_code: str) -> int:
    """
    將 AVAILABLE_TIME_TABLE 的時間代碼轉為分鐘數（從 00:00 起算）
    例如:
      '800A'  → 480  (08:00)
      '1230P' → 750  (12:30)
      '1200N' → 720  (12:00)
      '1201A' → 1    (00:01)
    """
    suffix = time_code[-1]  # A, P, or N
    num_part = time_code[:-1]
    num = int(num_part)

    hours = num // 100
    mins = num % 100

    if suffix == 'N':
        # 1200N = 12:00 noon
        return 12 * 60 + mins
    elif suffix == 'A':
        # AM: 1201A = 00:01, 600A = 06:00, 1230A = 00:30
        if hours == 12:
            hours = 0
        return hours * 60 + mins
    elif suffix == 'P':
        # PM: 1230P = 12:30, 100P = 13:00
        if hours != 12:
            hours += 12
        return hours * 60 + mins

    return 0


def _parse_types_of_trip_value(page: BeautifulSoup) -> int:
    options = page.find(**BOOKING_PAGE["types_of_trip"])
    tag = options.find_next(selected='selected')
    return int(tag.attrs['value'])


def _parse_search_by(page: BeautifulSoup) -> str:
    candidates = page.find_all('input', {'name': 'bookingMethod'})
    tag = next((cand for cand in candidates if 'checked' in cand.attrs))
    return tag.attrs['value']
