"""
自動化訂票流程控制器
取代互動式的 BookingFlow，自動完成所有步驟
"""

import time

from requests.models import Response

from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.view_model.error_feedback import ErrorFeedback
from thsr_ticket.view_model.booking_result import BookingResult
from thsr_ticket.view.web.show_booking_result import ShowBookingResult


class CaptchaInvalidError(Exception):
    """驗證碼辨識結果格式不正確（非4碼英數字），需要重新取得驗證碼"""
    pass


class BookingFailedError(Exception):
    """訂票失敗（售完、系統錯誤等），需要整體重試"""
    pass


class AutoBookingFlow:
    def __init__(self, config) -> None:
        self.config = config
        self.client = HTTPRequest()
        self.error_feedback = ErrorFeedback()

    def run(self) -> Response:
        """
        整體重試迴圈：
        - 最多重試 max_booking_retries 次（預設 10）
        - 每次重試間隔 retry_interval 秒（預設 3）
        - 每次重試都是全新的 session + 驗證碼 + 選車
        """
        max_booking_retries = getattr(self.config, 'max_booking_retries', 10)
        retry_interval = getattr(self.config, 'retry_interval', 3)
        max_captcha_retries = self.config.max_captcha_retries

        for booking_attempt in range(1, max_booking_retries + 1):
            print(f"\n{'='*40}")
            print(f"  第 {booking_attempt}/{max_booking_retries} 輪訂票")
            print(f"{'='*40}")

            # 內層：驗證碼重試（同一輪內只重試驗證碼）
            submitted_count = 0
            while submitted_count < max_captcha_retries:
                self.client = HTTPRequest()

                try:
                    result = self._attempt_booking()
                    if result is not None:
                        return result
                    # 提交後收到錯誤（驗證碼錯等）
                    submitted_count += 1
                    print(f"  [驗證碼已提交 {submitted_count}/{max_captcha_retries} 次]")
                except CaptchaInvalidError:
                    print("  重新取得驗證碼...")
                    continue
                except Exception as e:
                    from thsr_ticket.controller.confirm_train_flow_auto import TrainNotInRangeError
                    if isinstance(e, TrainNotInRangeError):
                        # 區間內無班次，跳到外層重試
                        print(f"  {e}")
                        break
                    print(f"  嘗試失敗: {e}")
                    submitted_count += 1

                if submitted_count < max_captcha_retries:
                    print("  重新嘗試中...")

            # 這一輪失敗了，等待後重試
            if booking_attempt < max_booking_retries:
                print(f"\n  本輪訂票未成功，{retry_interval} 秒後重新開始...")
                time.sleep(retry_interval)

        print(f"\n已達最大重試次數 ({max_booking_retries} 輪)，訂票失敗。")
        print("請嘗試手動訂票或調整設定後重試。")
        return None

    def _attempt_booking(self):
        """執行一次訂票嘗試，成功回傳 Response，失敗回傳 None"""
        from thsr_ticket.controller.first_page_flow_auto import FirstPageFlowAuto
        from thsr_ticket.controller.confirm_train_flow_auto import ConfirmTrainFlowAuto
        from thsr_ticket.controller.confirm_ticket_flow_auto import ConfirmTicketFlowAuto

        # Step 1: 首頁 — 填表 + 驗證碼
        print("正在填寫訂票資訊...")
        first_page = FirstPageFlowAuto(client=self.client, config=self.config)
        book_resp = first_page.run()  # 可能會 raise CaptchaInvalidError

        if self._check_error(book_resp.content):
            return None

        # Step 2: 選擇班次（可能 raise TrainNotInRangeError）
        print("正在選擇班次...")
        confirm_train = ConfirmTrainFlowAuto(
            client=self.client,
            book_resp=book_resp,
            config=self.config
        )
        train_resp = confirm_train.run()

        if self._check_error(train_resp.content):
            return None

        # Step 3: 確認訂票資訊
        print("正在確認訂票...")
        confirm_ticket = ConfirmTicketFlowAuto(
            client=self.client,
            train_resp=train_resp,
            config=self.config
        )
        ticket_resp = confirm_ticket.run()

        if self._check_error(ticket_resp.content):
            return None

        # Step 4: 顯示結果
        try:
            result_model = BookingResult().parse(ticket_resp.content)
            book = ShowBookingResult()
            book.show(result_model)
            print("\n訂票成功！請使用官方提供的管道完成後續付款以及取票!!")
            return ticket_resp
        except Exception as e:
            print(f"解析訂票結果失敗: {e}")
            return None

    def _check_error(self, html: bytes) -> bool:
        """檢查回應是否包含錯誤，回傳 True 表示有錯誤"""
        # 重新建立 ErrorFeedback 避免累積舊錯誤
        feedback = ErrorFeedback()
        errors = feedback.parse(html)
        if errors:
            for e in errors:
                print(f"  {e.msg}")
            return True
        return False
