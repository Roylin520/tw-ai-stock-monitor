# -*- coding: utf-8 -*-
"""
技術指標計算模組
純 pandas/numpy 實作，不依賴 TA-Lib。
"""
import pandas as pd
import config


def add_ma(df, windows=None):
    """移動平均線 MA。"""
    windows = windows or config.MA_WINDOWS
    for w in windows:
        df[f"MA{w}"] = df["Close"].rolling(window=w).mean()
    return df


def add_rsi(df, period=None):
    """相對強弱指標 RSI（0~100）。"""
    period = period or config.RSI_PERIOD
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, 1e-10)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def add_macd(df, fast=None, slow=None, signal=None):
    """MACD 指標（DIF / DEA / 柱狀）。"""
    fast = fast or config.MACD_FAST
    slow = slow or config.MACD_SLOW
    signal = signal or config.MACD_SIGNAL
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD_DIF"] = ema_fast - ema_slow
    df["MACD_DEA"] = df["MACD_DIF"].ewm(span=signal, adjust=False).mean()
    df["MACD_HIST"] = df["MACD_DIF"] - df["MACD_DEA"]
    return df


def add_bollinger(df, period=None, n_std=None):
    """布林通道（上軌 / 中軌 / 下軌）。"""
    period = period or config.BOLL_PERIOD
    n_std = n_std or config.BOLL_STD
    mid = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    df["BOLL_MID"] = mid
    df["BOLL_UP"] = mid + n_std * std
    df["BOLL_LOW"] = mid - n_std * std
    return df


def enrich(df):
    """一次套用所有指標。"""
    df = df.copy()
    df = add_ma(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger(df)
    return df
