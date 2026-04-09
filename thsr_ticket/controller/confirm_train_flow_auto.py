"""
自動化班次選擇流程
自動選擇時間區間內最早的一班車
"""

import json
from typing import List

from requests.models import Response

from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.view_model.avail_trains import AvailTrains
from thsr_ticket.configs.web.param_schema import Train, ConfirmTrainModel

class TrainNotInRangeError(Exception):
    """時間區間內找不到匹配班次"""
    pass


class ConfirmTrainFlowAuto:
    def __init__(self, client: HTTPRequest, book_resp: Response, config):
        self.client = client
        self.book_resp = book_resp
        self.config = config

    def run(self) -> Response:
        trains = AvailTrains().parse(self.book_resp.content)
        if not trains:
            raise ValueError("查無可用班次！請確認日期和時間區間設定。")

        # 印出所有可用班次
        print("  可用班次:")
        for idx, train in enumerate(trains, 1):
            print(
                f"    {idx}. {train.id:>4} {train.depart:>5}~{train.arrive:<5} "
                f"行車時間:{train.travel_time:>5} {train.discount_str}"
            )

        # 自動選擇班次
        selected = self._auto_select(trains)
        print(f"  自動選擇: 車次 {selected.id} ({selected.depart}~{selected.arrive})")

        confirm_model = ConfirmTrainModel(
            selected_train=selected.form_value,
        )
        json_params = confirm_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        resp = self.client.submit_train(dict_params)
        return resp

    def _auto_select(self, trains: List[Train]) -> Train:
        """
        根據設定的時間區間選擇最合適的班次
        策略：選擇時間區間內最早的一班
        """
        start_h, start_m, end_h, end_m = self.config.parse_time_range()
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        # 找時間區間內的班次
        for train in trains:
            train_minutes = _parse_train_time(train.depart)
            if start_minutes <= train_minutes <= end_minutes:
                return train

        # 如果沒有完全在區間內的，不退而求其次，丟錯誤讓外層重試
        raise TrainNotInRangeError(
            f"時間區間 {self.config.time_range} 內無匹配班次，需要重試"
        )


def _parse_train_time(time_str: str) -> int:
    """
    解析班次時間字串為分鐘數
    例如: "08:06" → 486, "13:30" → 810
    """
    parts = time_str.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0
