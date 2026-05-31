# -*- coding: utf-8 -*-
"""
分析模組
產生個股趨勢摘要訊號，以及 AI 概念股之間的相關性矩陣。
"""
import pandas as pd
import config


def trend_signal(df):
    """根據最新一筆指標，產生趨勢判斷摘要 dict。"""
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last
    close = float(last["Close"])

    signals = []
    score = 0  # 多空綜合分數

    # 1) 均線多空排列
    if "MA5" in df and "MA20" in df and "MA60" in df:
        ma5, ma20, ma60 = last["MA5"], last["MA20"], last["MA60"]
        if pd.notna(ma5) and pd.notna(ma20) and pd.notna(ma60):
            if ma5 > ma20 > ma60:
                signals.append("均線多頭排列")
                score += 2
            elif ma5 < ma20 < ma60:
                signals.append("均線空頭排列")
                score -= 2
            if close > ma20:
                score += 1
            else:
                score -= 1

    # 2) RSI
    if "RSI" in df and pd.notna(last["RSI"]):
        rsi = float(last["RSI"])
        if rsi >= 70:
            signals.append(f"RSI 超買({rsi:.0f})")
            score -= 1
        elif rsi <= 30:
            signals.append(f"RSI 超賣({rsi:.0f})")
            score += 1

    # 3) MACD 黃金/死亡交叉
    if "MACD_DIF" in df and "MACD_DEA" in df:
        if pd.notna(last["MACD_DIF"]) and pd.notna(prev["MACD_DIF"]):
            if prev["MACD_DIF"] <= prev["MACD_DEA"] and last["MACD_DIF"] > last["MACD_DEA"]:
                signals.append("MACD 黃金交叉")
                score += 2
            elif prev["MACD_DIF"] >= prev["MACD_DEA"] and last["MACD_DIF"] < last["MACD_DEA"]:
                signals.append("MACD 死亡交叉")
                score -= 2

    # 4) 布林通道位置
    if "BOLL_UP" in df and "BOLL_LOW" in df:
        if pd.notna(last["BOLL_UP"]) and pd.notna(last["BOLL_LOW"]):
            if close >= last["BOLL_UP"]:
                signals.append("觸及布林上軌")
            elif close <= last["BOLL_LOW"]:
                signals.append("觸及布林下軌")

    # 漲跌幅
    pct = (close / float(prev["Close"]) - 1) * 100 if float(prev["Close"]) else 0.0

    # 綜合評等
    if score >= 3:
        verdict = "偏多"
    elif score <= -3:
        verdict = "偏空"
    else:
        verdict = "中性"

    return {
        "close": close,
        "pct": pct,
        "rsi": float(last["RSI"]) if "RSI" in df and pd.notna(last["RSI"]) else None,
        "score": score,
        "verdict": verdict,
        "signals": signals,
    }


def correlation_matrix(data):
    """以收盤價日報酬率計算 AI 概念股相關性矩陣。"""
    closes = {}
    for ticker, df in data.items():
        name = config.STOCKS.get(ticker, ticker)
        closes[name] = df["Close"]
    if not closes:
        return pd.DataFrame()
    price = pd.DataFrame(closes)
    returns = price.pct_change().dropna(how="all")
    return returns.corr()


def relative_strength(data, benchmark_df):
    """計算各標的相對大盤的近期報酬（相對強弱）。"""
    if benchmark_df is None or benchmark_df.empty:
        return {}
    bench_ret = benchmark_df["Close"].iloc[-1] / benchmark_df["Close"].iloc[0] - 1
    result = {}
    for ticker, df in data.items():
        name = config.STOCKS.get(ticker, ticker)
        stock_ret = df["Close"].iloc[-1] / df["Close"].iloc[0] - 1
        result[name] = {
            "stock_return": stock_ret * 100,
            "excess": (stock_ret - bench_ret) * 100,
        }
    return result
