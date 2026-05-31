# Telegram 通知設定（約 3 分鐘）

## 步驟 1：建立 Bot，取得 Token
1. 在 Telegram 搜尋 **@BotFather**，開啟對話
2. 輸入 `/newbot`
3. 依指示輸入 bot 名稱與帳號（帳號需以 `bot` 結尾，例如 `tw_ai_stock_bot`）
4. BotFather 會回給你一串 **Token**，長得像：
   `123456789:AAH...xyz`　← 複製起來

## 步驟 2：取得你的 Chat ID
1. 在 Telegram 搜尋你剛建立的 bot，**對它傳一句話**（例如 `hi`）
2. 先把 Token 填進設定檔（見步驟 3 第 1 點）
3. 在專案資料夾執行：
   ```powershell
   python telegram_notify.py --get-chat-id
   ```
4. 它會印出你的 `chat_id`（一串數字）

## 步驟 3：填入設定
1. 複製 `secret_config.example.py` 成 `secret_config.py`
2. 填入：
   ```python
   TG_BOT_TOKEN = "123456789:AAH...xyz"   # 步驟1的 Token
   TG_CHAT_ID   = "123456789"             # 步驟2的 chat id
   ```

## 步驟 4：測試
```powershell
python telegram_notify.py --test
```
手機收到「Telegram 推播測試成功！」就完成了。

之後執行 `python hourly_monitor.py --force` 就會把盤中摘要推到你的 Telegram。

---

### 雲端部署（電腦關機也能跑）時
不要把金鑰寫進檔案，改設環境變數：
- `TG_BOT_TOKEN`
- `TG_CHAT_ID`

程式會優先讀環境變數，比較安全。
