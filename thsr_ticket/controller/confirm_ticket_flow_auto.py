"""
自動化確認訂票流程
自動填入身分證和手機號碼
"""

import json

from bs4 import BeautifulSoup
from requests.models import Response

from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.configs.web.param_schema import ConfirmTicketModel


class ConfirmTicketFlowAuto:
    def __init__(self, client: HTTPRequest, train_resp: Response, config):
        self.client = client
        self.train_resp = train_resp
        self.config = config

    def run(self) -> Response:
        page = BeautifulSoup(self.train_resp.content, features='html.parser')

        ticket_model = ConfirmTicketModel(
            personal_id=self.config.personal_id,
            phone_num=self.config.phone,
            member_radio=_parse_member_radio(page),
        )

        json_params = ticket_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        resp = self.client.submit_ticket(dict_params)
        return resp


def _parse_member_radio(page: BeautifulSoup) -> str:
    candidates = page.find_all(
        'input',
        attrs={
            'name': 'TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup'
        },
    )
    tag = next((cand for cand in candidates if 'checked' in cand.attrs))
    return tag.attrs['value']
