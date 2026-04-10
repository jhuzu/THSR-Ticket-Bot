# 🚄 高鐵自動訂票小幫手

> 用指令一鍵訂高鐵票，支援 **本機 CLI** 和 **LINE Bot 遠端訂票**。

**⚠️ 純研究用途，請勿用於不當用途。**

---

## 功能一覽

| 功能 | 說明 |
|------|------|
| 🎯 自動訂票 | 填好設定就全自動完成，不需手動操作網頁 |
| 🤖 驗證碼自動辨識 | 使用 OCR（ddddocr）自動辨識驗證碼，辨識失敗自動重試 |
| 🚉 中文車站名 | 直接填「桃園」「台南」等中文名，也支援英文和編號 |
| ⏰ 時間區間篩選 | 設定想搭乘的時段，自動選擇區間內最早班次 |
| 💺 座位偏好 | 可指定靠窗 / 走道 |
| 🔄 自動重試 | 驗證碼辨識失敗、無班次等情況都會自動重試 |
| 💬 LINE Bot | 透過 LINE 聊天室直接下指令訂票，結果會推播回來 |

---

## 快速開始

### 1. 環境需求

- **Python 3.9+**（建議 3.10 或 3.11）
- macOS / Linux / Windows 皆可

### 2. 下載專案

```bash
git clone https://github.com/BreezeWhite/THSR-Ticket.git
cd THSR-Ticket
```

### 3. 建立虛擬環境（建議）

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 4. 安裝套件

```bash
pip install -r requirements.txt
```

---

## 使用方式一：設定檔訂票（推薦 👍）

最簡單的方式，只要填一份設定檔就好。

### Step 1：建立設定檔

```bash
cp booking_config.example.yaml booking_config.yaml
```

### Step 2：編輯設定檔

用任何文字編輯器打開 `booking_config.yaml`，修改成你的資訊：

```yaml
personal:
  id: "A123456789"          # 你的身分證字號
  phone: "0912345678"       # 你的手機號碼

booking:
  date: "2026-04-15"        # 出發日期（YYYY-MM-DD）
  time_range: "08:00-10:00" # 想搭乘的時間區間
  from_station: "桃園"       # 起站
  to_station: "台南"         # 到站
  tickets: 2                # 票數（1-10）
  seat_prefer: "aisle"      # window 靠窗 / aisle 走道 / none 無偏好

automation:
  max_captcha_retries: 10   # 驗證碼辨識失敗重試次數
  auto_select_train: true   # 自動選最早一班
```

### Step 3：執行

```bash
python -m thsr_ticket.auto_booking --config booking_config.yaml
```

成功畫面會像這樣：

```
==================================================
        高鐵自動訂票系統
==================================================
  身分證字號: A12*******
  手機號碼:   0912******
  出發日期:   2026-04-15
  時間區間:   08:00-10:00
  起始站:     桃園
  終點站:     台南
  票數:       2 張成人票
  座位偏好:   aisle
==================================================

正在填寫訂票資訊...
正在選擇班次...
  自動選擇: 車次  613 (08:06~09:42)
正在確認訂票...

訂票成功！請使用官方提供的管道完成後續付款以及取票!!
```

> 💡 訂票成功後，記得在**繳費期限**前完成付款！

---

## 使用方式二：命令列參數

如果不想建設定檔，也可以直接用命令列參數：

```bash
python -m thsr_ticket.auto_booking \
  --id A123456789 \
  --phone 0912345678 \
  -d 2026-04-15 \
  -t 08:00-10:00 \
  -f 桃園 \
  -o 台南 \
  -n 2 \
  --seat-prefer aisle
```

也可以**混用**：設定檔 + 命令列，命令列的值會覆蓋設定檔：

```bash
# 設定檔寫好個資，只在命令列指定日期和時間
python -m thsr_ticket.auto_booking -c booking_config.yaml -d 2026-04-20 -t 14:00-18:00
```

### 所有命令列參數

| 參數 | 縮寫 | 說明 | 範例 |
|------|------|------|------|
| `--config` | `-c` | YAML 設定檔路徑 | `booking_config.yaml` |
| `--date` | `-d` | 出發日期 | `2026-04-15` |
| `--time-range` | `-t` | 時間區間 | `08:00-10:00` |
| `--from-station` | `-f` | 起站 | `桃園` |
| `--to-station` | `-o` | 到站 | `台南` |
| `--tickets` | `-n` | 票數 | `2` |
| `--id` | | 身分證字號 | `A123456789` |
| `--phone` | | 手機號碼 | `0912345678` |
| `--seat-prefer` | | 座位偏好 | `window` / `aisle` / `none` |

---

## 使用方式三：LINE Bot 訂票

透過 LINE 聊天視窗直接下指令，適合部署到雲端（如 Render）後遠端使用。

### LINE Bot 指令格式

```
訂票 日期 時間區間 起站→到站 張數
```

### 範例

```
訂票 04/15 08:30-09:00 桃園→台南 2張
訂票 2026-05-01 07:00-08:00 南港→高雄 1張
訂票 04/20 14:00-16:00 台北->左營
```

> 張數可以省略，預設為 1 張。

傳入「**說明**」或「**幫助**」可查看使用說明。

### LINE Bot 部署

1. 複製環境變數範本：
   ```bash
   cp .env.example .env
   ```

2. 在 `.env` 中填入你的 LINE Bot 憑證：
   ```
   LINE_CHANNEL_SECRET=你的_channel_secret
   LINE_CHANNEL_ACCESS_TOKEN=你的_access_token
   ```

3. 啟動 LINE Bot Server：
   ```bash
   python -m thsr_ticket.linebot.app
   ```

4. 將 Webhook URL 設為 `https://你的網址/callback`

---

## 車站對照表

| 編號 | 車站 | 英文 |
|:----:|:----:|:----:|
| 1 | 南港 | Nangang |
| 2 | 台北 | Taipei |
| 3 | 板橋 | Banqiao |
| 4 | 桃園 | Taoyuan |
| 5 | 新竹 | Hsinchu |
| 6 | 苗栗 | Miaoli |
| 7 | 台中 | Taichung |
| 8 | 彰化 | Changhua |
| 9 | 雲林 | Yunlin |
| 10 | 嘉義 | Chiayi |
| 11 | 台南 | Tainan |
| 12 | 左營 | Zuouing |

> 💡 輸入車站時，中文名、英文名、編號（1-12）都可以。「高雄」也可以用，會自動對應到「左營」。

---

## 常見問題

### Q：驗證碼一直失敗怎麼辦？

驗證碼辨識使用 OCR 模型，不是每次都能成功。程式會自動重試，預設每輪最多 10 次。如果還是不行，可以把 `max_captcha_retries` 調高：

```yaml
automation:
  max_captcha_retries: 20
```

### Q：訂票失敗顯示「時間區間內無匹配班次」？

代表你設定的 `time_range` 太窄，沒有車次落在範圍內。請放寬時間區間，例如改成 `06:00-23:00`。

### Q：可以訂學生票 / 敬老票嗎？

目前只支援**成人票**。

### Q：可以選擇特定車次嗎？

目前只支援依時間區間自動選擇最早的一班。如果想搭特定車次，可以將 `time_range` 設定成該車次的前後幾分鐘。

### Q：訂票成功後怎麼付款？

訂票成功後會顯示**訂位代號**和**繳費期限**，請前往以下管道付款：
- 高鐵官網 / APP
- 超商 ibon / FamiPort
- 高鐵車站售票窗口

---

## 專案結構

```
THSR-Ticket/
├── booking_config.yaml          # 你的訂票設定（不會被 git 追蹤）
├── booking_config.example.yaml  # 設定檔範本
├── .env                         # LINE Bot 憑證（不會被 git 追蹤）
├── .env.example                 # 環境變數範本
├── requirements.txt             # Python 套件清單
└── thsr_ticket/
    ├── auto_booking.py          # 自動訂票 CLI 入口
    ├── main.py                  # 互動式訂票入口（舊版）
    ├── controller/              # 訂票流程控制
    ├── configs/                 # 車站對照、參數設定
    ├── ml/                      # 驗證碼 OCR 辨識
    ├── linebot/                 # LINE Bot 整合
    ├── model/                   # 資料模型
    ├── remote/                  # HTTP 請求
    ├── view/                    # 結果顯示
    └── view_model/              # 畫面資料解析
```

---

## 致謝

本專案 fork 自 [BreezeWhite/THSR-Ticket](https://github.com/BreezeWhite/THSR-Ticket)，加入了自動驗證碼辨識、設定檔訂票、LINE Bot 遠端訂票等功能。
