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
# GitHub Pages 發佈目錄（手機版儀表板）
PUBLIC_DIR = "public"
PUBLIC_PATH = os.path.join(PUBLIC_DIR, "index.html")


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
    _write_dashboard(rows, ts, status)
    _notify_summary(rows, ts)
    print(f"  完成，已更新 {LIVE_PATH} 與 {PUBLIC_PATH}")


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


def _write_dashboard(rows, ts, status):
    """產生手機版儀表板 public/index.html（卡片式，響應式）。"""
    valid = sorted(rows, key=lambda x: (x["up_prob"] or 0), reverse=True)

    cards = ""
    for r in valid:
        p = r["up_prob"]
        pcolor = _prob_color(p)
        chg_color = "#e74c3c" if r["pct"] >= 0 else "#27ae60"
        acc = f"{r['test_acc']:.0f}%" if r["test_acc"] is not None else "—"
        rel = "" if r["reliable"] else "<span class='warn'>樣本不足</span>"
        width = p if p is not None else 0
        sig = r["signals"] or "—"
        cards += f"""
      <div class="card">
        <div class="row1">
          <div class="name">{r['name']} <span class="tk">{r['ticker']}</span></div>
          <div class="price">{r['close']} <span style="color:{chg_color}">{r['pct']:+.2f}%</span></div>
        </div>
        <div class="prob">
          <span class="plabel">隔日收紅機率</span>
          <span class="pval" style="color:{pcolor}">{p if p is not None else '—'}%</span>
          <span class="acc">回測命中 {acc} {rel}</span>
        </div>
        <div class="barwrap"><div class="bar" style="width:{width}%;background:{pcolor}"></div></div>
        <div class="sig">{sig}</div>
      </div>"""

    html = f"""<!DOCTYPE html><html lang="zh-Hant"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<meta http-equiv="refresh" content="300">
<title>台股 AI 盤中監控</title>
<style>
  * {{ box-sizing:border-box; -webkit-tap-highlight-color:transparent; }}
  body {{ font-family:-apple-system,"Microsoft JhengHei",sans-serif; margin:0;
          background:#0f1115; color:#e8eaed; padding:14px 12px 40px; }}
  header {{ position:sticky; top:0; background:#0f1115; padding:6px 2px 12px; z-index:10; }}
  h1 {{ font-size:19px; margin:0 0 2px; }}
  .meta {{ color:#8a8f98; font-size:12px; }}
  .card {{ background:#1a1d24; border-radius:14px; padding:13px 15px; margin:11px 0;
           box-shadow:0 1px 3px rgba(0,0,0,.4); }}
  .row1 {{ display:flex; justify-content:space-between; align-items:baseline; }}
  .name {{ font-size:17px; font-weight:600; }}
  .tk {{ color:#7d828b; font-size:12px; font-weight:400; }}
  .price {{ font-size:15px; font-variant-numeric:tabular-nums; }}
  .prob {{ display:flex; align-items:baseline; gap:8px; margin:9px 0 6px; flex-wrap:wrap; }}
  .plabel {{ font-size:12px; color:#8a8f98; }}
  .pval {{ font-size:24px; font-weight:700; font-variant-numeric:tabular-nums; }}
  .acc {{ font-size:11px; color:#8a8f98; margin-left:auto; }}
  .warn {{ color:#e0a800; }}
  .barwrap {{ height:7px; background:#2a2e37; border-radius:4px; overflow:hidden; }}
  .bar {{ height:100%; border-radius:4px; transition:width .4s; }}
  .sig {{ font-size:12px; color:#9aa0aa; margin-top:8px; }}
  .disc {{ margin-top:22px; padding:12px 14px; background:#241f12; border-radius:12px;
           font-size:11px; color:#c8a45a; line-height:1.6; }}
  .legend {{ font-size:11px; color:#8a8f98; margin:4px 2px 0; }}
</style></head><body>
  <header>
    <h1>📈 台股 AI 盤中監控</h1>
    <div class="meta">更新 {ts}（台北）　狀態：{status}　每 5 分鐘自動刷新</div>
    <div class="legend">🔴≥60% 偏多　▪️中性　🟢≤40% 偏弱（依收紅機率排序）</div>
  </header>
  {cards}
  <div class="disc">⚠️「隔日收紅機率」為技術面統計模型估計，<b>非投資建議、非保證</b>。
  請對照「回測命中」判讀可靠度——越接近 50% 代表幾乎等於丟銅板。投資有風險，請自負盈虧。</div>
</body></html>"""
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    with open(PUBLIC_PATH, "w", encoding="utf-8") as f:
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
