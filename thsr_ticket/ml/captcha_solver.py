"""
自動辨識高鐵驗證碼模組
使用 ddddocr 進行驗證碼 OCR 辨識
"""

import re
import ddddocr


class CaptchaSolver:
    def __init__(self):
        self._ocr = ddddocr.DdddOcr(show_ad=False)

    def solve(self, image_bytes: bytes) -> str:
        """
        辨識驗證碼圖片

        Args:
            image_bytes: 驗證碼圖片的原始 bytes

        Returns:
            辨識出的驗證碼字串（4 碼英數字大寫）
            若辨識結果不符合格式，回傳空字串
        """
        result = self._ocr.classification(image_bytes)
        result = result.upper().strip()

        # 高鐵驗證碼為 4 碼英數字
        # 過濾掉明顯不正確的結果
        if not re.match(r'^[A-Z0-9]{4}$', result):
            return ""

        return result


# 模組級單例，避免重複初始化模型
_solver = None


def get_solver() -> CaptchaSolver:
    """取得 CaptchaSolver 單例"""
    global _solver
    if _solver is None:
        _solver = CaptchaSolver()
    return _solver


def solve_captcha(image_bytes: bytes) -> str:
    """便捷函數：直接辨識驗證碼"""
    return get_solver().solve(image_bytes)
