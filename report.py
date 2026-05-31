# -*- coding: utf-8 -*-
"""
報告產生模組
為每檔標的繪製 K 線＋均線＋技術指標圖，並彙整成一份 HTML 報告。
"""
import os
import base64
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # 無視窗環境
import matplotlib.pyplot as plt
from matplotlib import font_manager

import config

# 嘗試載入中文字型（Windows 內建微軟正黑體）
for _fp in [
    r"C:\Windows\Fonts\msjh.ttc",
    r"C:\Windows\Fonts\mingliu.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
]:
    if os.path.exists(_fp):
        font_manager.fontManager.addfont(_fp)
        matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=_fp).get_name()
        break
matplotlib.rcParams["axes.unicode_minus"] = False


def _fig_to_base64(fig):
    """把 matplotlib 圖轉成 base64 內嵌字串。"""
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def plot_stock(ticker, df):
    """繪製單檔三區圖：K線+均線+布林 / MACD / RSI。回傳 base64 PNG。"""
    name = config.STOCKS.get(ticker, ticker)
    fig, axes = plt.subplots(
        3, 1, figsize=(11, 8), sharex=True,
        gridspec_kw={"height_ratios": [3, 1, 1]},
    )
    ax1, ax2, ax3 = axes
    x = df.index

    # ── 主圖：收盤價 + 均線 + 布林通道
    ax1.plot(x, df["Close"], label="收盤", color="#222", linewidth=1.3)
    for w, c in zip(config.MA_WINDOWS, ["#e6194b", "#3cb44b", "#4363d8"]):
        col = f"MA{w}"
        if col in df:
            ax1.plot(x, df[col], label=col, linewidth=0.9, color=c)
    if "BOLL_UP" in df:
        ax1.plot(x, df["BOLL_UP"], color="#999", linewidth=0.6, linestyle="--")
        ax1.plot(x, df["BOLL_LOW"], color="#999", linewidth=0.6, linestyle="--")
        ax1.fill_between(x, df["BOLL_LOW"], df["BOLL_UP"], color="#bbb", alpha=0.12)
    ax1.set_title(f"{name} ({ticker})  收盤價與技術指標", fontsize=13)
    ax1.legend(loc="upper left", fontsize=8, ncol=5)
    ax1.grid(alpha=0.3)

    # ── MACD
    if "MACD_DIF" in df:
        ax2.plot(x, df["MACD_DIF"], label="DIF", color="#e6194b", linewidth=0.9)
        ax2.plot(x, df["MACD_DEA"], label="DEA", color="#4363d8", linewidth=0.9)
        colors = ["#d62728" if v >= 0 else "#2ca02c" for v in df["MACD_HIST"].fillna(0)]
        ax2.bar(x, df["MACD_HIST"], color=colors, width=1.0)
        ax2.axhline(0, color="#888", linewidth=0.5)
        ax2.legend(loc="upper left", fontsize=8)
        ax2.set_ylabel("MACD", fontsize=9)
        ax2.grid(alpha=0.3)

    # ── RSI
    if "RSI" in df:
        ax3.plot(x, df["RSI"], color="#9467bd", linewidth=1.0)
        ax3.axhline(70, color="#d62728", linewidth=0.6, linestyle="--")
        ax3.axhline(30, color="#2ca02c", linewidth=0.6, linestyle="--")
        ax3.set_ylim(0, 100)
        ax3.set_ylabel("RSI", fontsize=9)
        ax3.grid(alpha=0.3)

    fig.tight_layout()
    return _fig_to_base64(fig)


def plot_correlation(corr):
    """相關性熱力圖。回傳 base64 PNG。"""
    if corr.empty:
        return None
    fig, ax = plt.subplots(figsize=(9, 7.5))
    im = ax.imshow(corr.values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(corr.index, fontsize=8)
    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center",
                    fontsize=7, color="#000")
    ax.set_title("AI 概念股 日報酬相關性矩陣", fontsize=13)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return _fig_to_base64(fig)


def _verdict_color(verdict):
    return {"偏多": "#d62728", "偏空": "#2ca02c", "中性": "#888"}.get(verdict, "#888")


def build_html(stock_imgs, summaries, corr_img, rs_data):
    """組合 HTML 報告字串。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 摘要表格列
    rows = ""
    for ticker, s in summaries.items():
        name = config.STOCKS.get(ticker, ticker)
        rs = rs_data.get(name, {})
        excess = rs.get("excess")
        excess_str = f"{excess:+.1f}%" if excess is not None else "—"
        pct_color = "#d62728" if s["pct"] >= 0 else "#2ca02c"
        rsi_str = f"{s['rsi']:.0f}" if s["rsi"] is not None else "—"
        rows += f"""
        <tr>
          <td><b>{name}</b><br><span class="tk">{ticker}</span></td>
          <td>{s['close']:.1f}</td>
          <td style="color:{pct_color}">{s['pct']:+.2f}%</td>
          <td>{rsi_str}</td>
          <td>{excess_str}</td>
          <td><span class="badge" style="background:{_verdict_color(s['verdict'])}">{s['verdict']}</span></td>
          <td class="sig">{' / '.join(s['signals']) or '—'}</td>
        </tr>"""

    # 個股圖卡片
    cards = ""
    for ticker, img in stock_imgs.items():
        name = config.STOCKS.get(ticker, ticker)
        cards += f"""
        <div class="card">
          <h3>{name} <span class="tk">{ticker}</span></h3>
          <img src="data:image/png;base64,{img}" />
        </div>"""

    corr_section = ""
    if corr_img:
        corr_section = f"""
        <h2>相關性分析</h2>
        <p class="note">數值越接近 1，代表兩檔股票走勢越同步；接近 0 表示連動性低。可用於分散風險與配對交易參考。</p>
        <div class="card"><img src="data:image/png;base64,{corr_img}" /></div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>台股 AI 產業分析報告</title>
<style>
  body {{ font-family:"Microsoft JhengHei",sans-serif; margin:0; background:#f4f5f7; color:#222; }}
  .wrap {{ max-width:1200px; margin:0 auto; padding:24px; }}
  h1 {{ font-size:24px; margin:0 0 4px; }}
  .meta {{ color:#888; font-size:13px; margin-bottom:20px; }}
  h2 {{ border-left:5px solid #4363d8; padding-left:10px; margin-top:36px; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:8px; overflow:hidden;
          box-shadow:0 1px 4px rgba(0,0,0,.08); font-size:14px; }}
  th,td {{ padding:10px 12px; text-align:center; border-bottom:1px solid #eee; }}
  th {{ background:#2c3e50; color:#fff; font-weight:600; }}
  td.sig {{ text-align:left; color:#555; font-size:13px; }}
  .tk {{ color:#999; font-size:12px; font-weight:normal; }}
  .badge {{ color:#fff; padding:3px 12px; border-radius:12px; font-size:13px; }}
  .card {{ background:#fff; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,.08);
           padding:14px; margin:18px 0; }}
  .card img {{ width:100%; height:auto; display:block; }}
  .card h3 {{ margin:0 0 8px; }}
  .note {{ color:#777; font-size:13px; }}
  .disclaimer {{ margin-top:40px; padding:14px; background:#fff3cd; border-radius:8px;
                 font-size:12px; color:#856404; }}
</style></head><body>
<div class="wrap">
  <h1>📈 台股 AI 產業趨勢分析報告</h1>
  <div class="meta">產生時間：{now}　|　資料期間：{config.PERIOD}　|　共 {len(summaries)} 檔標的</div>

  <h2>個股訊號總覽</h2>
  <table>
    <tr><th>標的</th><th>收盤</th><th>漲跌</th><th>RSI</th><th>相對大盤</th><th>評等</th><th>訊號</th></tr>
    {rows}
  </table>

  {corr_section}

  <h2>個股技術圖</h2>
  {cards}

  <div class="disclaimer">
    ⚠️ 免責聲明：本報告由程式自動產生，所有指標與評等僅為技術面統計，<b>不構成任何投資建議</b>。
    投資有風險，請審慎評估並自負盈虧。
  </div>
</div></body></html>"""


def generate(stock_imgs, summaries, corr_img, rs_data):
    """寫出 HTML 報告，回傳檔案路徑。"""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    html = build_html(stock_imgs, summaries, corr_img, rs_data)
    path = os.path.join(config.OUTPUT_DIR, config.REPORT_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
