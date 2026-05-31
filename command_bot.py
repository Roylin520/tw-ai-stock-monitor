# -*- coding: utf-8 -*-
"""
Telegram 指令處理（方法 A）
由排程每 ~15 分鐘執行一次：讀取使用者在 Telegram 傳的指令，更新 watchlist.json，
並回覆確認訊息。狀態（last_update_id + 清單）全存在 watchlist.json，冪等可重跑。

支援指令：
  /list                 顯示目前追蹤清單
  /add 代號 [中文名]     新增（如 /add 3034 聯詠；名稱可省略）
  /remove 代號          移除（如 /remove 2330）
  /reset                還原成預設清單
  /help                 顯示說明

本機測試：python command_bot.py
"""
import os
import sys
import json
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import config

API = "https://api.telegram.org/bot{token}/{method}"


def _token():
    tok = os.environ.get("TG_BOT_TOKEN")
    if not tok:
        try:
            import secret_config
            tok = getattr(secret_config, "TG_BOT_TOKEN", None)
        except ImportError:
            pass
    return tok


def _call(token, method, params, timeout=30):
    url = API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _reply(token, chat_id, text):
    try:
        _call(token, "sendMessage", {
            "chat_id": chat_id, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": "true",
        })
    except Exception as e:
        print(f"回覆失敗：{e}")


# ─────────────────────────────────────────────
# 股票代號驗證：找出正確後綴(.TW/.TWO)並嘗試取得名稱
# ─────────────────────────────────────────────
def resolve_ticker(code, name=None):
    """回傳 (ticker, name) 或 (None, 錯誤訊息)。"""
    import yfinance as yf
    code = code.strip().upper().replace(".TW", "").replace(".TWO", "")
    for suffix in (".TW", ".TWO"):
        ticker = code + suffix
        try:
            df = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if not name:
                    # 嘗試抓官方名稱，失敗就先用代號當名稱
                    try:
                        info = yf.Ticker(ticker).info
                        name = info.get("shortName") or info.get("longName") or code
                    except Exception:
                        name = code
                return ticker, name
        except Exception:
            continue
    return None, f"找不到代號 {code}（.TW / .TWO 都查無資料），請確認是否正確。"


# ─────────────────────────────────────────────
# 指令解析
# ─────────────────────────────────────────────
def _help_text():
    return (
        "📋 <b>追蹤清單管理指令</b>\n\n"
        "/list － 顯示目前追蹤清單\n"
        "/add 代號 [中文名] － 新增，例：<code>/add 3034 聯詠</code>\n"
        "/remove 代號 － 移除，例：<code>/remove 2330</code>\n"
        "/reset － 還原成預設清單\n"
        "/help － 顯示本說明\n\n"
        "<i>※ 指令由排程每約 15 分鐘處理一次，非即時。</i>"
    )


def _list_text(stocks):
    if not stocks:
        return "目前追蹤清單是空的。用 /add 代號 新增。"
    lines = [f"📌 <b>目前追蹤 {len(stocks)} 檔</b>："]
    for t, n in stocks.items():
        lines.append(f"・{n}（{t}）")
    return "\n".join(lines)


def handle_command(text, stocks):
    """處理單一指令，回傳 (回覆文字, 清單是否異動)。"""
    parts = text.strip().split()
    if not parts:
        return None, False
    cmd = parts[0].lower().split("@")[0]  # 去掉 /add@botname 的 @botname
    args = parts[1:]

    if cmd in ("/start", "/help"):
        return _help_text(), False

    if cmd == "/list":
        return _list_text(stocks), False

    if cmd == "/reset":
        stocks.clear()
        stocks.update(config.DEFAULT_STOCKS)
        return "✅ 已還原成預設清單。\n\n" + _list_text(stocks), True

    if cmd == "/add":
        if not args:
            return "用法：/add 代號 [中文名]，例：/add 3034 聯詠", False
        code = args[0]
        name = " ".join(args[1:]) if len(args) > 1 else None
        ticker, resolved = resolve_ticker(code, name)
        if ticker is None:
            return "⚠️ " + resolved, False
        if ticker in stocks:
            return f"ℹ️ {stocks[ticker]}（{ticker}）已在清單中。", False
        stocks[ticker] = resolved
        return f"✅ 已新增 {resolved}（{ticker}）。目前共 {len(stocks)} 檔。", True

    if cmd == "/remove":
        if not args:
            return "用法：/remove 代號，例：/remove 2330", False
        code = args[0].strip().upper().replace(".TW", "").replace(".TWO", "")
        # 比對 .TW / .TWO 兩種
        for suffix in (".TW", ".TWO"):
            t = code + suffix
            if t in stocks:
                name = stocks.pop(t)
                return f"✅ 已移除 {name}（{t}）。目前剩 {len(stocks)} 檔。", True
        return f"⚠️ 清單中找不到代號 {code}。用 /list 查看目前清單。", False

    # 非本系統指令，忽略（不回覆，避免洗版）
    return None, False


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────
def main():
    token = _token()
    if not token:
        print("未設定 TG_BOT_TOKEN，結束。")
        return

    data = config.load_watchlist()
    last_id = data["last_update_id"]
    stocks = data["stocks"]

    # 取得新訊息（offset = 上次處理過的最大 id + 1，確保不重複處理）
    try:
        res = _call(token, "getUpdates", {"offset": last_id + 1, "timeout": 0})
    except Exception as e:
        print(f"getUpdates 失敗：{e}")
        return

    updates = res.get("result", []) if res.get("ok") else []
    if not updates:
        print("沒有新指令。")
        return

    changed = False
    max_id = last_id
    for upd in updates:
        max_id = max(max_id, upd.get("update_id", max_id))
        msg = upd.get("message") or upd.get("edited_message") or {}
        text = msg.get("text", "")
        chat_id = (msg.get("chat") or {}).get("id")
        if not text or not chat_id:
            continue
        reply, did_change = handle_command(text, stocks)
        if did_change:
            changed = True
        if reply:
            _reply(token, chat_id, reply)
            print(f"處理指令：{text!r} → 回覆已送出")

    # 寫回狀態（即使清單沒變，也要更新 last_update_id 避免重複處理）
    data["last_update_id"] = max_id
    data["stocks"] = stocks
    config.save_watchlist(data)
    print(f"完成。last_update_id={max_id}，清單共 {len(stocks)} 檔，異動={changed}")


if __name__ == "__main__":
    main()
