# -*- coding: utf-8 -*-
"""
Windows 桌面通知
使用內建 PowerShell + Windows.UI.Notifications，無需額外安裝套件。
若失敗則靜默略過（不影響主流程）。
"""
import os
import subprocess


def toast(title, message):
    """跳出 Windows 通知（非 Windows 環境自動略過）。"""
    if os.name != "nt":
        return
    # 轉義單引號
    t = title.replace("'", "''")
    m = message.replace("'", "''")
    ps = f"""
$ErrorActionPreference = 'SilentlyContinue'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
$tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$texts = $tpl.GetElementsByTagName('text')
$texts.Item(0).AppendChild($tpl.CreateTextNode('{t}')) | Out-Null
$texts.Item(1).AppendChild($tpl.CreateTextNode('{m}')) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($tpl)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('台股AI監控')
$notifier.Show($toast)
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=15,
        )
    except Exception:
        pass
