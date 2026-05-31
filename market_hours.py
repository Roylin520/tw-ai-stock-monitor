# -*- coding: utf-8 -*-
"""
台股交易時段判斷
正常交易：週一至週五 09:00–13:30（台北時間 UTC+8）。
（不含國定假日；如需精準可再串接證交所行事曆 API。）
"""
from datetime import datetime, time, timezone, timedelta

TPE = timezone(timedelta(hours=8))
OPEN_TIME = time(9, 0)
CLOSE_TIME = time(13, 30)


def now_tpe():
    return datetime.now(TPE)


def is_market_open(dt=None):
    dt = dt or now_tpe()
    if dt.weekday() >= 5:          # 週六(5)、週日(6)
        return False
    return OPEN_TIME <= dt.time() <= CLOSE_TIME


def market_status(dt=None):
    dt = dt or now_tpe()
    if dt.weekday() >= 5:
        return "休市（週末）"
    t = dt.time()
    if t < OPEN_TIME:
        return "尚未開盤"
    if t > CLOSE_TIME:
        return "已收盤"
    return "盤中"
