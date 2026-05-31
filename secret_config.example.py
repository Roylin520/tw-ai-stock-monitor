# -*- coding: utf-8 -*-
"""
Telegram 金鑰設定（本機用）
使用方式：
  1. 把這個檔案複製成 secret_config.py
  2. 填入你的 Bot Token 與 Chat ID
  3. secret_config.py 已被 .gitignore 排除，不會上傳到 GitHub

雲端部署時改用環境變數 TG_BOT_TOKEN / TG_CHAT_ID，不要把金鑰寫進程式。
"""
TG_BOT_TOKEN = "在這裡貼上 BotFather 給你的 token，例如 123456:ABC-DEF..."
TG_CHAT_ID = "在這裡貼上你的 chat id，例如 123456789"
