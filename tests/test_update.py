"""latest.json スキーマのテスト。"""

from src.update import build_payload

RECORDS = [
    {"ticker": "AAPL", "name": "Apple Inc. Common Stock", "exchange": "NASDAQ",
     "fields": {"Symbol": "AAPL", "Security Name": "Apple Inc. Common Stock"}},
    {"ticker": "XOM", "name": "Exxon Mobil Corporation Common Stock", "exchange": "NYSE",
     "fields": {"ACT Symbol": "XOM", "Security Name": "Exxon Mobil Corporation Common Stock"}},
    {"ticker": "ZZZZ", "name": "取得対象外銘柄 Common Stock", "exchange": "NYSE",
     "fields": {"ACT Symbol": "ZZZZ", "Security Name": "取得対象外銘柄 Common Stock"}},
]

# 価格は「ティッカー → {close, change_pct, volume, as_of, sector}」の最小形
PRICES = {
    "AAPL": {"close": 255.0, "change_pct": round((255.0 / 250.0 - 1) * 100, 3),
             "volume": 1200, "as_of": "2026-10-23", "sector": "Technology"},
    "XOM": {"close": 120.0, "change_pct": None,
            "volume": None, "as_of": "2026-10-23", "sector": None},
}


def test_schema():
    p = build_payload(RECORDS, PRICES)
    assert p["reference"] is True
    assert p["count"] == 3
    by_ticker = {i["ticker"]: i for i in p["items"]}
    aapl = by_ticker["AAPL"]
    assert aapl["exchange"] == "NASDAQ"
    assert aapl["sector"] == "Technology"
    assert aapl["price"]["close"] == 255.0
    assert abs(aapl["price"]["change_pct"] - round((255.0 / 250.0 - 1) * 100, 3)) < 1e-9
    # 日次バーは latest.json に含めない
    assert "bars" not in aapl
    # セクター未取得は「未分類」
    assert by_ticker["XOM"]["sector"] == "未分類"
    # 価格未取得も行を残し price=None
    miss = by_ticker["ZZZZ"]
    assert miss["price"] is None
    assert miss["sector"] == "未分類"
    # セクタータブ集計（銘柄数順）
    cats = [(c["id"], c["count"]) for c in p["categories"]]
    assert dict(cats)["Technology"] == 1
    assert dict(cats)["未分類"] == 2
    counts = [n for _, n in cats]
    assert counts == sorted(counts, reverse=True)
    assert p["reference_date"] == "2026-10-23"
    # 免責表現は USD を明記
    assert "USD" in p["reference_note"]
    assert "2026-10-23" in p["reference_note"]
    # 詳細ページ用の sections は持たない
    assert "sections" not in p


def test_no_prices():
    p = build_payload(RECORDS, {})
    assert p["with_price_count"] == 0
    assert all(i["price"] is None for i in p["items"])
    assert all(i["sector"] == "未分類" for i in p["items"])
    assert p["reference_date"] is None
