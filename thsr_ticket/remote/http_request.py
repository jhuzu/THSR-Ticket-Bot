from typing import Mapping, Any

from curl_cffi import requests
from curl_cffi.requests import Session, Response
from bs4 import BeautifulSoup

from thsr_ticket.configs.web.http_config import HTTPConfig
from thsr_ticket.configs.web.parse_html_element import BOOKING_PAGE

IMPERSONATE = "chrome120"


class HTTPRequest:
    TIMEOUT = 30  # 秒，避免無限等待

    def __init__(self, max_retries: int = 3) -> None:
        self.sess = Session(impersonate=IMPERSONATE)

        self.common_head_html: dict = {
            "Accept": HTTPConfig.HTTPHeader.ACCEPT_HTML,
            "Accept-Language": HTTPConfig.HTTPHeader.ACCEPT_LANGUAGE,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def request_booking_page(self) -> Response:
        return self.sess.get(HTTPConfig.BOOKING_PAGE_URL, headers=self.common_head_html, allow_redirects=True, timeout=self.TIMEOUT)

    def request_security_code_img(self, book_page: bytes) -> Response:
        img_url = parse_security_img_url(book_page)
        return self.sess.get(img_url, headers=self.common_head_html, timeout=self.TIMEOUT)

    def submit_booking_form(self, params: Mapping[str, Any]) -> Response:
        url = HTTPConfig.SUBMIT_FORM_URL.format(self.sess.cookies["JSESSIONID"])
        return self.sess.post(url, headers=self.common_head_html, params=params, allow_redirects=True, timeout=self.TIMEOUT)

    def submit_train(self, params: Mapping[str, Any]) -> Response:
        return self.sess.post(
            HTTPConfig.CONFIRM_TRAIN_URL,
            headers=self.common_head_html,
            params=params,
            allow_redirects=True,
            timeout=self.TIMEOUT
        )

    def submit_ticket(self, params: Mapping[str, Any]) -> Response:
        return self.sess.post(
            HTTPConfig.CONFIRM_TICKET_URL,
            headers=self.common_head_html,
            params=params,
            allow_redirects=True,
            timeout=self.TIMEOUT
        )


def parse_security_img_url(html: bytes) -> str:
    page = BeautifulSoup(html, features="html.parser")
    element = page.find(**BOOKING_PAGE["security_code_img"])
    return HTTPConfig.BASE_URL + element["src"]
