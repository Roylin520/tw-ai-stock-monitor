# 台股 AI 產業趨勢分析系統

針對 AI 產業相關台股（台積電、聯電、聯發科、廣達、緯創… ＋ ETF 0050/0056）的技術面自動分析工具。
一鍵抓取資料、計算指標、產生視覺化 HTML 報告。

## 功能

- **資料抓取**：透過 yfinance 抓取歷史 K 線，含 12 小時本地快取
- **技術指標**：MA(5/20/60)、RSI、MACD、布林通道
- **趨勢訊號**：均線排列、黃金/死亡交叉、超買超賣 → 多空綜合評等
- **相對強弱**：個股相對加權指數（^TWII）的超額報酬
- **相關性分析**：AI 概念股之間的日報酬相關性熱力圖
- **HTML 報告**：個股訊號總覽表 ＋ 三區技術圖 ＋ 相關性矩陣

## 安裝

```powershell
pip install -r requirements.txt
```

## 執行

```powershell
python main.py
```

完成後自動開啟 `output/report.html`。
不想自動開啟瀏覽器：`python main.py --no-open`

## 自訂

編輯 `config.py`：

- `STOCKS`：增減追蹤標的（上市 `.TW`、上櫃 `.TWO`）
- `PERIOD`：資料期間（`6mo` / `1y` / `2y` / `5y`）
- `MA_WINDOWS` / `RSI_PERIOD` 等：調整指標參數

## 檔案結構

| 檔案 | 說明 |
|------|------|
| `config.py` | 股票清單與所有參數設定 |
| `data_fetcher.py` | 資料抓取與快取 |
| `indicators.py` | 技術指標計算 |
| `analyzer.py` | 趨勢判斷與相關性 |
| `report.py` | 繪圖與 HTML 產生 |
| `main.py` | 主程式入口 |

## ⚠️ 免責聲明

本系統所有指標與評等僅為技術面統計，**不構成任何投資建議**。投資有風險，請自負盈虧。
