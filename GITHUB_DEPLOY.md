# GitHub Actions 部署（電腦關機也能跑）

部署後，台股交易日每小時會在 GitHub 的雲端伺服器自動執行，把盤中摘要推到你的 Telegram。
你的電腦完全不用開。**免費**（私有 repo 每月有 2000 分鐘額度，這個任務每月用不到 30 分鐘）。

---

## 步驟 1：建立 GitHub Repo
1. 登入 https://github.com → 右上角 **+** → **New repository**
2. 名稱隨意（例如 `tw-ai-stock-monitor`），設為 **Private（私有）**
3. 先不要勾任何 README，按 **Create repository**

## 步驟 2：把程式推上去
在專案資料夾 `E:\Claude\StockMarket` 開 PowerShell，依序執行
（把 `<你的帳號>` 和 `<repo名稱>` 換成實際的）：

```powershell
git init
git add .
git commit -m "台股 AI 監控系統"
git branch -M main
git remote add origin https://github.com/<你的帳號>/<repo名稱>.git
git push -u origin main
```

> ⚠️ `secret_config.py` 已被 `.gitignore` 排除，**不會**被上傳，金鑰安全。

## 步驟 3：設定 Secrets（放金鑰）
在 GitHub 該 repo 頁面：
1. **Settings** → 左側 **Secrets and variables** → **Actions**
2. 按 **New repository secret**，新增兩個：

   | Name | Secret |
   |------|--------|
   | `TG_BOT_TOKEN` | 你的 bot token（BotFather 給的那串） |
   | `TG_CHAT_ID` | 你的 chat id（一串數字） |

## 步驟 4：開啟並測試
1. 到 repo 的 **Actions** 分頁，若提示啟用 workflow 就按啟用
2. 左側點 **台股AI盤中監控** → 右側 **Run workflow**（手動觸發測試）
3. 約 1 分鐘後，手機應收到 Telegram 盤中摘要
   （手動觸發會 `--force`，所以即使現在休市也會跑）

完成後，之後交易日 **台北 09:00–13:00 每小時整點** 會自動推播，不用你管。

---

## 常見問題

**Q：cron 時間準嗎？**
GitHub Actions 的排程在尖峰時可能延遲幾分鐘，對「每小時看趨勢」影響不大。需要分秒精準請改用雲端 VM。

**Q：國定假日也會跑嗎？**
程式只判斷「週一~五 09:00–13:30」，遇到國定假日休市仍會觸發，但抓到的是前一交易日資料。若要精準排除假日，可再串接證交所行事曆 API（需要再跟我說）。

**Q：想改追蹤的股票 / 時間？**
- 股票：改 `config.py` 的 `STOCKS`，commit + push 即可生效
- 頻率：改 `.github/workflows/monitor.yml` 的 `cron`

**Q：想同時有網頁儀表板？**
可加開 GitHub Pages 把 `live.html` 發佈成網址，需要再跟我說。
