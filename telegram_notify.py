# -*- coding: utf-8 -*-
"""
Telegram 推播通知
零額外套件（只用內建 urllib），本機與雲端皆可用。

金鑰讀取優先序：
  1. 環境變數 TG_BOT_TOKEN / TG_CHAT_ID（雲端部署用，較安全）
  2. 同目錄 secret_config.py 內的 TG_BOT_TOKEN / TG_CHAT_ID（本機用）

取得 Chat ID（先跟你的 bot 傳一句話，再執行）：
  python telegram_notify.py --get-chat-id
測試推播：
  python telegram_notify.py --test
"""
import os
import sys
import json
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"


def _load_credentials():
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        try:
            import secret_config
            token = token or getattr(secret_config, "TG_BOT_TOKEN", None)
            chat_id = chat_id or getattr(secret_config, "TG_CHAT_ID", None)
        except ImportError:
            pass
    return token, chat_id


def _call(token, method, params, timeout=15):
    url = API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def send(message, parse_mode="HTML"):
    """送出一則訊息。回傳 True/False。"""
    token, chat_id = _load_credentials()
    if not token or not chat_id:
        print("[Telegram] 尚未設定 TG_BOT_TOKEN / TG_CHAT_ID，略過推播。")
        return False
    try:
        res = _call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": "true",
        })
        if not res.get("ok"):
            print(f"[Telegram] 失敗：{res}")
        return bool(res.get("ok"))
    except Exception as e:
        print(f"[Telegram] 例外：{e}")
        return False


def get_chat_id():
    """列出最近跟 bot 互動的 chat id（協助初次設定）。"""
    token, _ = _load_credentials()
    if not token:
        print("請先設定 TG_BOT_TOKEN（環境變數或 secret_config.py）。")
        return
    try:
        res = _call(token, "getUpdates", {})
    except Exception as e:
        print(f"取得失敗：{e}")
        return
    if not res.get("ok") or not res.get("result"):
        print("沒有收到任何訊息。請先在 Telegram 對你的 bot 傳一句話（例如 hi），再重跑一次。")
        return
    seen = {}
    for upd in res["result"]:
        msg = upd.get("message") or upd.get("channel_post") or {}
        chat = msg.get("chat", {})
        if chat.get("id"):
            seen[chat["id"]] = chat.get("title") or chat.get("username") or chat.get("first_name", "")
    print("找到以下 chat id：")
    for cid, name in seen.items():
        print(f"  chat_id = {cid}   ({name})")
    print("\n把上面的 chat_id 填到 secret_config.py 的 TG_CHAT_ID 即可。")


if __name__ == "__main__":
    if "--get-chat-id" in sys.argv:
        get_chat_id()
    elif "--test" in sys.argv:
        ok = send("✅ <b>台股 AI 監控</b>\nTelegram 推播測試成功！")
        print("已送出" if ok else "送出失敗，請檢查 token / chat_id")
    else:
        print(__doc__)
