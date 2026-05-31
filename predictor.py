# -*- coding: utf-8 -*-
"""
漲跌機率估計模組
用個股自身的歷史資料訓練一個 logistic regression（純 numpy 實作），
根據目前技術面狀態，估算「下一交易日收紅」的機率，
並以 holdout 回測命中率回報模型可靠度。

⚠️ 重要：股市無法被準確預測。此處輸出僅為統計估計，非保證，
        命中率通常僅略高於 50%，請務必搭配回測命中率一起解讀。
"""
import numpy as np
import pandas as pd

import indicators


# ─────────────────────────────────────────────
# 特徵工程
# ─────────────────────────────────────────────
def build_features(df):
    """從含技術指標的 DataFrame 建立特徵矩陣與標籤。

    特徵（皆為與價格無關的相對量）：
      - RSI / 100
      - MACD 柱狀 / 收盤
      - (收盤 - MA20) / MA20      → 乖離
      - (MA5 - MA20) / MA20       → 短中期均線差
      - 近 5 日報酬
      - 成交量 / 20 日均量
    標籤：隔日收盤 > 當日收盤 → 1，否則 0
    """
    d = df.copy()
    if "RSI" not in d:
        d = indicators.enrich(d)

    feat = pd.DataFrame(index=d.index)
    feat["rsi"] = d["RSI"] / 100.0
    feat["macd"] = d["MACD_HIST"] / d["Close"]
    feat["bias20"] = (d["Close"] - d["MA20"]) / d["MA20"]
    feat["ma_diff"] = (d["MA5"] - d["MA20"]) / d["MA20"]
    feat["ret5"] = d["Close"].pct_change(5)
    vol_ma = d["Volume"].rolling(20).mean()
    feat["vol_ratio"] = d["Volume"] / vol_ma.replace(0, np.nan) - 1

    # 標籤：隔日漲跌
    label = (d["Close"].shift(-1) > d["Close"]).astype(int)

    data = feat.copy()
    data["y"] = label
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    return data


# ─────────────────────────────────────────────
# Logistic Regression（numpy 梯度下降）
# ─────────────────────────────────────────────
def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def _train_logistic(X, y, lr=0.1, epochs=600, l2=1e-3):
    n, k = X.shape
    w = np.zeros(k)
    b = 0.0
    for _ in range(epochs):
        z = X @ w + b
        p = _sigmoid(z)
        err = p - y
        grad_w = X.T @ err / n + l2 * w
        grad_b = err.mean()
        w -= lr * grad_w
        b -= lr * grad_b
    return w, b


def predict(df, test_ratio=0.25):
    """訓練並估計最新一筆的上漲機率，同時回傳 holdout 命中率。

    回傳 dict：
      up_prob       — 最新狀態下「隔日收紅」估計機率 (0~1)
      test_acc      — holdout 測試集命中率
      base_rate     — 訓練期實際上漲比例（基準線，用來對照）
      n_samples     — 可用樣本數
      reliable      — 樣本是否足夠（>=120 才算堪用）
    """
    data = build_features(df)
    n = len(data)
    if n < 80:
        return {"up_prob": None, "test_acc": None, "base_rate": None,
                "n_samples": n, "reliable": False}

    cols = [c for c in data.columns if c != "y"]
    X = data[cols].values.astype(float)
    y = data["y"].values.astype(float)

    # 標準化（用全體統計；最後一筆預測也用同一組）
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Xs = (X - mu) / sd

    # 時序切分（前段訓練、後段測試，避免未來資料外洩）
    split = int(n * (1 - test_ratio))
    Xtr, ytr = Xs[:split], y[:split]
    Xte, yte = Xs[split:], y[split:]

    w, b = _train_logistic(Xtr, ytr)

    # holdout 命中率
    if len(yte) > 0:
        pte = _sigmoid(Xte @ w + b)
        test_acc = float(((pte >= 0.5).astype(int) == yte).mean())
    else:
        test_acc = None

    # 用全體重訓一次，估計「最新一筆 → 隔日」機率
    w_all, b_all = _train_logistic(Xs, y)
    latest = Xs[-1]
    up_prob = float(_sigmoid(latest @ w_all + b_all))

    return {
        "up_prob": up_prob,
        "test_acc": test_acc,
        "base_rate": float(y.mean()),
        "n_samples": n,
        "reliable": n >= 120,
    }
