"""
車站名稱工具：支援中文 ↔ 英文 ↔ 編號互轉
"""

from thsr_ticket.configs.web.enums import StationMapping


# 中文名 → StationMapping
CHINESE_TO_STATION = {
    "南港": StationMapping.Nangang,
    "台北": StationMapping.Taipei,
    "臺北": StationMapping.Taipei,
    "板橋": StationMapping.Banqiao,
    "桃園": StationMapping.Taoyuan,
    "新竹": StationMapping.Hsinchu,
    "苗栗": StationMapping.Miaoli,
    "台中": StationMapping.Taichung,
    "臺中": StationMapping.Taichung,
    "彰化": StationMapping.Changhua,
    "雲林": StationMapping.Yunlin,
    "嘉義": StationMapping.Chiayi,
    "台南": StationMapping.Tainan,
    "臺南": StationMapping.Tainan,
    "左營": StationMapping.Zuouing,
    "高雄": StationMapping.Zuouing,  # 方便使用者用高雄代替左營
}

# 英文名 → StationMapping（不分大小寫）
ENGLISH_TO_STATION = {s.name.lower(): s for s in StationMapping}


def parse_station(value: str) -> int:
    """
    將使用者輸入的車站名解析為 StationMapping 的 value（數字）

    支援的格式：
    - 數字: "2" → 2
    - 中文: "台北" → 2
    - 英文: "Taipei" → 2

    Args:
        value: 使用者輸入的車站名（字串）

    Returns:
        StationMapping 的數字值

    Raises:
        ValueError: 無法辨識的車站名
    """
    value = value.strip()

    # 嘗試數字
    try:
        num = int(value)
        if 1 <= num <= 12:
            return num
        raise ValueError(f"車站編號必須在 1-12 之間，收到: {num}")
    except ValueError:
        pass

    # 嘗試中文
    if value in CHINESE_TO_STATION:
        return CHINESE_TO_STATION[value].value

    # 嘗試英文（不分大小寫）
    lower = value.lower()
    if lower in ENGLISH_TO_STATION:
        return ENGLISH_TO_STATION[lower].value

    # 列出所有可用車站
    chinese_names = ", ".join(CHINESE_TO_STATION.keys())
    raise ValueError(
        f"無法辨識的車站名: '{value}'\n"
        f"可用的中文名: {chinese_names}\n"
        f"或使用編號 1-12"
    )


def station_name_chinese(station_value: int) -> str:
    """將 StationMapping 數字值轉為中文名"""
    canonical = {
        1: "南港", 2: "台北", 3: "板橋", 4: "桃園",
        5: "新竹", 6: "苗栗", 7: "台中", 8: "彰化",
        9: "雲林", 10: "嘉義", 11: "台南", 12: "左營",
    }
    return canonical.get(station_value, f"未知({station_value})")

