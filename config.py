# -*- coding: utf-8 -*-
"""
台股 AI 產業分析系統 - 設定檔
集中管理股票清單、分析參數與輸出設定。

追蹤清單可由 Telegram 指令（/add /remove）動態修改，存於 watchlist.json；
若該檔不存在則使用下方 DEFAULT_STOCKS 預設清單。
"""
import os
import json

# ─────────────────────────────────────────────
# AI 產業相關標的預設清單（代號 : 中文名稱）
# yfinance 上市股票後綴為 .TW，上櫃為 .TWO
# ─────────────────────────────────────────────
DEFAULT_STOCKS = {
    # 半導體 / 晶圓代工
    "2330.TW": "台積電",
    "2303.TW": "聯電",
    "2454.TW": "聯發科",
    "3443.TW": "創意",
    "3661.TW": "世芯-KY",
    "5274.TWO": "信驊",
    # AI 伺服器 / 代工
    "2317.TW": "鴻海",
    "2382.TW": "廣達",
    "3231.TW": "緯創",
    "6669.TW": "緯穎",
    "2376.TW": "技嘉",
    "2357.TW": "華碩",
    "2377.TW": "微星",
    # ETF
    "0050.TW": "元大台灣50",
    "0056.TW": "元大高股息",
    "006208.TW": "富邦台50",
}

# 追蹤清單檔（由 command_bot.py 維護）
WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")


def load_watchlist():
    """讀取 watchlist.json，回傳完整 dict（含 last_update_id 與 stocks）。
    檔案不存在時以預設清單初始化。"""
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data.get("stocks"), dict) and data["stocks"]:
                return {"last_update_id": data.get("last_update_id", 0),
                        "stocks": data["stocks"]}
        except Exception:
            pass
    return {"last_update_id": 0, "stocks": dict(DEFAULT_STOCKS)}


def save_watchlist(data):
    """寫回 watchlist.json。"""
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 目前生效的追蹤清單（其他模組 import config.STOCKS 即可）
STOCKS = load_watchlist()["stocks"]

# 大盤指標（用於比較相對強弱）
BENCHMARK = "^TWII"  # 台股加權指數
BENCHMARK_NAME = "加權指數"

# ─────────────────────────────────────────────
# 資料抓取參數
# ─────────────────────────────────────────────
PERIOD = "1y"        # 抓取期間：6mo / 1y / 2y / 5y
INTERVAL = "1d"      # K 線週期：1d / 1wk

# ─────────────────────────────────────────────
# 技術指標參數
# ─────────────────────────────────────────────
MA_WINDOWS = [5, 20, 60]   # 移動平均線（週/月/季線）
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLL_PERIOD = 20
BOLL_STD = 2

# ─────────────────────────────────────────────
# 輸出設定
# ─────────────────────────────────────────────
OUTPUT_DIR = "output"
REPORT_FILE = "report.html"
