# -*- coding: utf-8 -*-
"""
盤中每小時監控
開盤時段執行：抓最新價 → 估計各標的隔日上漲機率 → 桌面通知 +
寫入 output/hourly_log.csv + 更新 output/live.html。

手動測試（無視交易時段）： python hourly_monitor.py --force
排程用（非交易時段自動跳過）： python hourly_monitor.py
"""
import os
import sys
import csv
from datetime import datetime

# Windows 主控台 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import config
import data_fetcher
import indicators
import analyzer
import predictor
import market_hours
import notify
import telegram_notify

LOG_PATH = os.path.join(config.OUTPUT_DIR, "hourly_log.csv")
LIVE_PATH = os.path.join(config.OUTPUT_DIR, "live.html")


def run_once(force=False):
    status = market_hours.market_status()
    ts = market_hours.now_tpe().strftime("%Y-%m-%d %H:%M")

    if not force and not market_hours.is_market_open():
        print(f"[{ts}] {status}，非交易時段，跳過。")
        return

    print(f"[{ts}] {status} — 開始掃描 {len(config.STOCKS)} 檔 ...")

    rows = []
    for ticker, name in config.STOCKS.items():
        try:
            # 盤中要最新價，跳過快取
            df = data_fetcher.fetch_one(ticker, use_cache=False)
            if df.empty or len(df) < 80:
                continue
            enr = indicators.enrich(df)
            sig = analyzer.trend_signal(enr)
            pred = predictor.predict(enr)
            rows.append({
                "time": ts, "ticker": ticker, "name": name,
                "close": round(sig["close"], 2),
                "pct": round(sig["pct"], 2),
                "verdict": sig["verdict"],
                "up_prob": round(pred["up_prob"] * 100, 1) if pred["up_prob"] is not None else None,
                "test_acc": round(pred["test_acc"] * 100, 1) if pred["test_acc"] is not None else None,
                "reliable": pred["reliable"],
                "signals": " / ".join(sig["signals"]),
            })
        except Exception as e:
            print(f"  [錯誤] {ticker}: {e}")

    if not rows:
        print("  無有效資料。")
        return

    _append_log(rows)
    _write_live(rows, ts, status)
    _notify_summary(rows, ts)
    print(f"  完成，已更新 {LIVE_PATH}")


def _append_log(rows):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    new = not os.path.exists(LOG_PATH)
    cols = ["time", "ticker", "name", "close", "pct", "verdict",
            "up_prob", "test_acc", "reliable", "signals"]
    with open(LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        w.writerows(rows)


def _prob_color(p):
    if p is None:
        return "#888"
    if p >= 60:
        return "#d62728"
    if p <= 40:
        return "#2ca02c"
    return "#e8a33d"


def _write_live(rows, ts, status):
    body = ""
    for r in sorted(rows, key=lambda x: (x["up_prob"] or 0), reverse=True):
        p = r["up_prob"]
        pcolor = "#d62728" if r["pct"] >= 0 else "#2ca02c"
        acc = f"{r['test_acc']}%" if r["test_acc"] is not None else "—"
        rel = "" if r["reliable"] else " ⚠樣本不足"
        bar = ""
        if p is not None:
            bar = f"<div class='barwrap'><div class='bar' style='width:{p}%;background:{_prob_color(p)}'></div></div>"
        body += f"""
        <tr>
          <td><b>{r['name']}</b><br><span class="tk">{r['ticker']}</span></td>
          <td>{r['close']}</td>
          <td style="color:{pcolor}">{r['pct']:+.2f}%</td>
          <td><b style="color:{_prob_color(p)}">{p if p is not None else '—'}%</b>{bar}</td>
          <td>{acc}{rel}</td>
          <td>{r['verdict']}</td>
          <td class="sig">{r['signals'] or '—'}</td>
        </tr>"""

    html = f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="300">
<title>盤中即時監控</title><style>
body{{font-family:"Microsoft JhengHei",sans-serif;background:#f4f5f7;margin:0;padding:24px}}
.wrap{{max-width:1100px;margin:0 auto}}
h1{{font-size:22px;margin:0 0 4px}}
.meta{{color:#888;font-size:13px;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;
box-shadow:0 1px 4px rgba(0,0,0,.08);font-size:14px}}
th,td{{padding:9px 11px;text-align:center;border-bottom:1px solid #eee}}
th{{background:#2c3e50;color:#fff}}
td.sig{{text-align:left;color:#666;font-size:12px}}
.tk{{color:#999;font-size:12px}}
.barwrap{{height:5px;background:#eee;border-radius:3px;margin-top:3px;overflow:hidden}}
.bar{{height:100%}}
.disc{{margin-top:24px;padding:12px;background:#fff3cd;border-radius:8px;font-size:12px;color:#856404}}
</style></head><body><div class="wrap">
<h1>🔴 台股 AI 產業盤中監控</h1>
<div class="meta">更新：{ts}（台北）　狀態：{status}　每 5 分鐘自動刷新頁面</div>
<table>
<tr><th>標的</th><th>現價</th><th>漲跌</th><th>隔日收紅機率</th><th>回測命中率</th><th>評等</th><th>訊號</th></tr>
{body}
</table>
<div class="disc">⚠️ 「隔日收紅機率」為技術面統計模型估計，<b>非保證</b>。
請對照「回測命中率」判讀可靠度（接近 50% 代表幾乎等於丟銅板）。本工具不構成投資建議。</div>
</div></body></html>"""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    with open(LIVE_PATH, "w", encoding="utf-8") as f:
        f.write(html)


def _notify_summary(rows, ts):
    """推播盤中摘要：Telegram（主）+ 桌面通知（備援）。"""
    valid = [r for r in rows if r["up_prob"] is not None]
    if not valid:
        return
    valid.sort(key=lambda x: x["up_prob"], reverse=True)

    # ── Telegram：完整排序清單
    lines = [f"📊 <b>台股 AI 盤中監控</b>  {ts}", ""]
    for r in valid:
        arrow = "🔴" if r["pct"] >= 0 else "🟢"
        prob = r["up_prob"]
        face = "🔺" if prob >= 60 else ("🔻" if prob <= 40 else "▪️")
        acc = f"{r['test_acc']:.0f}%" if r["test_acc"] is not None else "—"
        rel = "" if r["reliable"] else "⚠"
        lines.append(
            f"{arrow} <b>{r['name']}</b> {r['close']} ({r['pct']:+.1f}%)　"
            f"{face}收紅 {prob:.0f}% <i>(準{acc}{rel})</i>"
        )
    lines.append("")
    lines.append("<i>※ 機率為技術面統計估計，非保證；準=回測命中率，越接近50%越不可靠。</i>")
    msg = "\n".join(lines)
    sent = telegram_notify.send(msg)

    # ── 桌面通知備援（本機執行時）
    top = valid[:2]
    bottom = valid[-2:]
    up_txt = "、".join(f"{r['name']}{r['up_prob']:.0f}%" for r in top)
    dn_txt = "、".join(f"{r['name']}{r['up_prob']:.0f}%" for r in bottom)
    notify.toast(f"台股AI監控 {ts}", f"偏多: {up_txt}｜偏弱: {dn_txt}")

    print(f"  Telegram 推播：{'成功' if sent else '未送出（檢查金鑰）'}")


if __name__ == "__main__":
    run_once(force="--force" in sys.argv)
