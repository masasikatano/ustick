"""Stooq から日次CSVを取得し、Yahoo で取得失敗した銘柄の価格を埋める（フォールバック）。

エンドポイント: https://stooq.com/q/d/l/?s={ティッカー}.us&i=d
ティッカーは小文字にし "." を "-" に置換する（BRK.B → brk-b.us、AAPL → aapl.us）。

終値・前日比は CSV の最後の2営業日の Close で (P_n/P_{n-1}-1)*100 を自前計算する。
出来高は最終営業日の Volume。日次バー全体は latest.json に保持しない。
"""

from __future__ import annotations

import csv
import io
import logging
import time

import requests

log = logging.getLogger("stooq")

CSV_URL = "https://stooq.com/q/d/l/"
REQUEST_INTERVAL = 0.1
RETRIES = 3


def symbol(ticker: str) -> str:
    """ティッカーを Stooq 形式に変換する（BRK.B → brk-b.us）。"""
    return ticker.replace(".", "-").lower() + ".us"


def parse_csv(text: str) -> dict | None:
    """日次CSVのテキストから終値・前日比・出来高・基準日を算出する。

    最後の2営業日の Close で (P_n/P_{n-1}-1)*100 を計算する。
    データが不足する場合は None を返す。
    """
    rows = [r for r in csv.DictReader(io.StringIO(text)) if r.get("Close")]
    if not rows:
        return None
    try:
        closes = [float(r["Close"]) for r in rows]
        last = rows[-1]
        volume = int(float(last["Volume"])) if last.get("Volume") else None
    except (KeyError, ValueError):
        return None
    change_pct = None
    if len(closes) >= 2 and closes[-2]:
        change_pct = round((closes[-1] / closes[-2] - 1) * 100, 3)
    return {
        "close": closes[-1],
        "change_pct": change_pct,
        "volume": volume,
        "as_of": last["Date"],
    }


def _fetch_one(ticker: str, session: requests.Session, retries: int = RETRIES) -> dict | None:
    delay = 2.0
    last: Exception | None = None
    for attempt in range(retries):
        try:
            res = session.get(CSV_URL, params={"s": symbol(ticker), "i": "d"}, timeout=30)
            res.raise_for_status()
            parsed = parse_csv(res.text)
            if parsed is None:
                raise ValueError("no data")
            return parsed
        except Exception as e:
            last = e
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
    log.warning("Stooq 取得失敗: %s (%s)", ticker, last)
    return None


def fetch_prices(tickers: list[str], session: requests.Session | None = None) -> dict[str, dict]:
    """ティッカーごとの終値・前日比を Stooq で取得する（Yahoo 失敗銘柄のみに使う）。

    戻り値: { "ティッカー": {"close": float, "change_pct": float|None,
             "volume": int|None, "as_of": "YYYY-MM-DD"}, ... }
    取得失敗銘柄は戻り値に含めない（呼び出し側で「データなし」扱い）。
    """
    session = session or requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    out: dict[str, dict] = {}
    for ticker in tickers:
        price = _fetch_one(ticker, session)
        if price is not None:
            out[ticker] = price
        time.sleep(REQUEST_INTERVAL)
    log.info("Stooq: %s/%s 銘柄の価格を取得", len(out), len(tickers))
    return out
