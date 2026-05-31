# -*- coding: utf-8 -*-
"""
資料抓取模組
使用 yfinance 抓取台股歷史 K 線資料，並提供快取機制。
"""
import os
import time
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

import config

CACHE_DIR = os.path.join(config.OUTPUT_DIR, "cache")


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def fetch_one(ticker, period=None, interval=None, use_cache=True):
    """抓取單一標的的歷史資料，回傳 DataFrame（含 OHLCV）。"""
    if yf is None:
        raise ImportError("尚未安裝 yfinance，請先執行：pip install yfinance")

    period = period or config.PERIOD
    interval = interval or config.INTERVAL
    _ensure_cache_dir()

    cache_path = os.path.join(CACHE_DIR, f"{ticker.replace('^', '_')}_{period}_{interval}.csv")

    # 使用當日快取（同一天不重複抓取）
    if use_cache and os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < 12 * 3600:  # 12 小時內視為有效
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            if not df.empty:
                return df

    df = yf.download(
        ticker, period=period, interval=interval,
        auto_adjust=True, progress=False,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    # yfinance 新版回傳 MultiIndex 欄位，攤平處理
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.to_csv(cache_path)
    return df


def fetch_all(tickers=None, **kwargs):
    """批次抓取多檔標的，回傳 {ticker: DataFrame}。"""
    tickers = tickers or list(config.STOCKS.keys())
    result = {}
    for t in tickers:
        try:
            df = fetch_one(t, **kwargs)
            if df.empty:
                print(f"  [警告] {t} 無資料，略過")
                continue
            result[t] = df
            print(f"  [完成] {t} ({config.STOCKS.get(t, t)}) — {len(df)} 筆")
        except Exception as e:
            print(f"  [錯誤] {t}：{e}")
    return result
