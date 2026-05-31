# -*- coding: utf-8 -*-
"""
台股 AI 產業分析系統 — 主程式
執行：python main.py
完成後會在 output/report.html 產生互動報告。
"""
import os
import sys
import webbrowser

# Windows 主控台預設 cp950，強制改用 UTF-8 以正確顯示中文與符號
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import config
import data_fetcher
import indicators
import analyzer
import report


def main(open_browser=True):
    print("=" * 50)
    print(" 台股 AI 產業分析系統")
    print("=" * 50)

    # 1) 抓資料
    print("\n[1/5] 抓取個股資料 ...")
    data = data_fetcher.fetch_all()
    if not data:
        print("沒有抓到任何資料，請檢查網路或股票代號。")
        sys.exit(1)

    print("\n[2/5] 抓取大盤指數 ...")
    try:
        benchmark = data_fetcher.fetch_one(config.BENCHMARK)
    except Exception as e:
        print(f"  大盤抓取失敗：{e}")
        benchmark = None

    # 2) 計算指標
    print("\n[3/5] 計算技術指標 ...")
    enriched = {t: indicators.enrich(df) for t, df in data.items()}

    # 3) 分析
    print("\n[4/5] 產生趨勢訊號與相關性 ...")
    summaries = {t: analyzer.trend_signal(df) for t, df in enriched.items()}
    corr = analyzer.correlation_matrix(data)
    rs_data = analyzer.relative_strength(data, benchmark)

    # 終端機摘要
    print("\n  個股評等：")
    for t, s in summaries.items():
        name = config.STOCKS.get(t, t)
        print(f"    {name:<8}{t:<11} 收{s['close']:>8.1f}  {s['pct']:+6.2f}%  "
              f"[{s['verdict']}]  {' / '.join(s['signals'])}")

    # 4) 繪圖 + 報告
    print("\n[5/5] 繪製圖表並產生 HTML 報告 ...")
    stock_imgs = {t: report.plot_stock(t, df) for t, df in enriched.items()}
    corr_img = report.plot_correlation(corr)
    path = report.generate(stock_imgs, summaries, corr_img, rs_data)

    abspath = os.path.abspath(path)
    print(f"\n✅ 完成！報告已產生：{abspath}")
    if open_browser:
        webbrowser.open("file://" + abspath)


if __name__ == "__main__":
    main(open_browser="--no-open" not in sys.argv)
