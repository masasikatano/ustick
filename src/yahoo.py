"""Yahoo Finance から終値・前日比・セクターを取得する（主データソース）。

価格エンドポイント: https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d
米国株のためティッカーは接尾辞なし（ティッカーの "." は Yahoo 形式の "-" に置換。

セクターエンドポイント: https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=assetProfile
（chart レスポンスにはセクターが含まれないため別途取得する。
クッキー（fc.yahoo.com）＋ crumb（/v1/test/getcrumb）が必要。未取得時は sector=None）

終値・前日比は close 配列の最後の2点から自前で算出する
（(P_n/P_{n-1}-1)*100。spec.md の定義と一致させるため
meta.regularMarketChangePercent は使わない）。
出来高は indicators.quote の volume 配列から、close と同じ最終ポイントの値を採用する
（最終点が None の場合は直近の有効値にフォールバック）。

取得失敗した銘柄は戻り値に含めず、呼び出し側で Stooq →「データなし」とする。
"""

from __future__ import annotations

import logging
import time
from datetime import date

import requests

log = logging.getLogger("yahoo")

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
PROFILE_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
COOKIE_URL = "https://fc.yahoo.com"
CRUMB_URL = "https://query1.finance.yahoo.com/v1/test/getcrumb"
REQUEST_INTERVAL = 0.1  # リクエスト間の間隔（秒）。4,000+ 銘柄で 7〜8 分
RETRIES = 3

# Yahoo で取得を除外する銘柄コード（必要になったらここに追加。
# 恒常的に Yahoo から取得失敗する銘柄はこれで省き、Stooq フォールバックで埋める）
YAHOO_EXCLUDE: set[str] = set()

HEADERS = {"User-Agent": "Mozilla/5.0"}


def symbol(ticker: str) -> str:
    """ティッカーを Yahoo 形式に変換する（BRK.B → BRK-B。日本株の .T は付けない）。"""
    return ticker.replace(".", "-")


def parse_chart(data: dict) -> dict | None:
    """chart API レスポンスから終値・前日比・出来高・基準日を算出する。

    close 配列の最後の2点から (P_n/P_{n-1}-1)*100 を計算する。
    出来高は close と同じ最終ポイントの volume を採用し、
    最終点が None の場合は直近の有効値にフォールバックする。
    取得できない場合は None を返す。
    """
    try:
        result = data["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        closes = quote["close"]
        volumes = quote.get("volume")
        timestamps = result["timestamp"]
    except (KeyError, IndexError, TypeError):
        return None
    points = [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]
    if not points:
        return None
    last_ts, last_close = points[-1]
    change_pct = None
    if len(points) >= 2:
        prev = points[-2][1]
        if prev:
            change_pct = round((last_close / prev - 1) * 100, 3)
    volume = None
    if volumes:
        for v in reversed(volumes[:len(points)]):
            if v is not None:
                volume = int(v)
                break
    return {
        "close": float(last_close),
        "change_pct": change_pct,
        "volume": volume,
        "as_of": date.fromtimestamp(last_ts).isoformat(),
    }


def parse_profile(data: dict) -> str | None:
    """quoteSummary レスポンスからセクター名を取り出す。取得できなければ None。"""
    try:
        profile = data["quoteSummary"]["result"][0]["assetProfile"]
        sector = profile.get("sector")
        return str(sector) if sector else None
    except (KeyError, IndexError, TypeError):
        return None


class _CrumbClient:
    """Yahoo のクッキー＋crumb を 1 回だけ取得して使い回す。"""

    def __init__(self, session: requests.Session) -> None:
        self.session = session
        self.crumb: str | None = None
        self.failed = False

    def get(self) -> str | None:
        if self.failed:
            return None
        if self.crumb is not None:
            return self.crumb
        try:
            self.session.get(COOKIE_URL, timeout=30)  # 404 でも Set-Cookie される
            res = self.session.get(CRUMB_URL, timeout=30)
            res.raise_for_status()
            crumb = res.text.strip()
            if not crumb or "<" in crumb:
                raise ValueError("unexpected crumb body")
            self.crumb = crumb
            return crumb
        except Exception as e:
            log.warning("Yahoo crumb 取得失敗（セクター未取得で継続）: %s", e)
            self.failed = True
            return None


def _fetch_one(ticker: str, session: requests.Session, crumb: _CrumbClient,
               retries: int = RETRIES) -> dict | None:
    url = CHART_URL.format(symbol=symbol(ticker))
    delay = 2.0
    last: Exception | None = None
    for attempt in range(retries):
        try:
            res = session.get(url, params={"interval": "1d", "range": "5d"}, timeout=30)
            res.raise_for_status()
            parsed = parse_chart(res.json())
            if parsed is None:
                raise ValueError("no data")
            parsed["sector"] = _fetch_sector(ticker, session, crumb)
            return parsed
        except Exception as e:
            last = e
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
    log.warning("Yahoo 取得失敗: %s (%s)", ticker, last)
    return None


def _fetch_sector(ticker: str, session: requests.Session, crumb: _CrumbClient) -> str | None:
    key = crumb.get()
    if key is None:
        return None
    try:
        res = session.get(PROFILE_URL.format(symbol=symbol(ticker)),
                          params={"modules": "assetProfile", "crumb": key}, timeout=30)
        res.raise_for_status()
        return parse_profile(res.json())
    except Exception as e:
        log.debug("セクター取得失敗: %s (%s)", ticker, e)
        return None


def fetch_prices(tickers: list[str], session: requests.Session | None = None) -> dict[str, dict]:
    """ティッカーごとの終値・前日比・出来高・セクターを取得する。

    戻り値: { "ティッカー": {"close": float, "change_pct": float|None,
             "volume": int|None, "as_of": "YYYY-MM-DD", "sector": str|None}, ... }
    取得失敗・除外銘柄は戻り値に含めない（呼び出し側で Stooq →「データなし」扱い）。
    """
    session = session or requests.Session()
    session.headers.update(HEADERS)
    crumb = _CrumbClient(session)
    out: dict[str, dict] = {}
    for ticker in tickers:
        if ticker in YAHOO_EXCLUDE:
            continue
        price = _fetch_one(ticker, session, crumb)
        if price is not None:
            out[ticker] = price
        time.sleep(REQUEST_INTERVAL)
    with_sector = sum(1 for p in out.values() if p.get("sector"))
    log.info("Yahoo Finance: %s/%s 銘柄の価格を取得（セクター付き %s）", len(out), len(tickers), with_sector)
    return out
