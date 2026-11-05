"""Yahoo Finance 価格取得のテスト（モック使用）。"""

from datetime import datetime, timezone
from unittest.mock import patch

from src import yahoo

# timestamp: 2026-10-22 / 2026-10-23 (UTC)
TS = [int(datetime(2026, 10, d, tzinfo=timezone.utc).timestamp()) for d in (22, 23)]


def _chart_body(closes, volumes=None):
    return {
        "chart": {
            "result": [{
                "timestamp": TS[:len(closes)],
                "indicators": {"quote": [{"close": closes, "volume": volumes}]},
            }],
        },
    }


def _profile_body(sector):
    return {"quoteSummary": {"result": [{"assetProfile": {"sector": sector}}]}}


def test_parse_chart_calculates_change_pct():
    # close 配列の最後の2点から (P_n/P_{n-1}-1)*100 で自前計算する
    parsed = yahoo.parse_chart(_chart_body([250.0, 255.0], [1000, 1200]))
    assert parsed["close"] == 255.0
    assert abs(parsed["change_pct"] - round((255.0 / 250.0 - 1) * 100, 3)) < 1e-9
    assert parsed["volume"] == 1200  # close と同じ最終ポイントの出来高
    assert parsed["as_of"] == "2026-10-23"
    # RVol = 当日出来高 / 直近20日平均出来高
    assert parsed["avg_volume_20d"] == 1100.0
    assert parsed["rvol"] == round(1200 / 1100.0, 2)


def test_parse_chart_volume_fallback_and_missing():
    parsed = yahoo.parse_chart(_chart_body([250.0, 255.0], [1000, None]))
    assert parsed["volume"] == 1000
    # 平均出来高なし（RVol 算出不可）の銘柄は avg None・rvol None で保持する
    parsed = yahoo.parse_chart(_chart_body([250.0, 255.0]))
    assert parsed["volume"] is None
    assert parsed["avg_volume_20d"] is None
    assert parsed["rvol"] is None


def test_parse_chart_single_point_no_change():
    parsed = yahoo.parse_chart(_chart_body([255.0]))
    assert parsed["close"] == 255.0
    assert parsed["change_pct"] is None


def test_parse_chart_no_data():
    assert yahoo.parse_chart({"chart": {"result": []}}) is None
    assert yahoo.parse_chart(_chart_body([None, None])) is None


def test_parse_profile():
    assert yahoo.parse_profile(_profile_body("Technology")) == "Technology"
    assert yahoo.parse_profile(_profile_body(None)) is None
    assert yahoo.parse_profile({"quoteSummary": {"result": []}}) is None


def test_symbol():
    # 米国株は接尾辞なし。ティッカーの "." は Yahoo 形式の "-" に置換
    assert yahoo.symbol("AAPL") == "AAPL"
    assert yahoo.symbol("BRK.B") == "BRK-B"


@patch("src.yahoo._fetch_sector", return_value="Technology")
@patch("src.yahoo._fetch_one")
def test_fetch_prices_skips_failures(mock_fetch, mock_sector):
    # 取得失敗した銘柄は戻り値に含めず「データなし」扱いにする
    mock_fetch.side_effect = [
        {"close": 255.0, "change_pct": 0.5, "volume": 1200,
         "as_of": "2026-10-23", "sector": "Technology",
         "avg_volume_20d": 1000.0, "rvol": 1.2},
        None,
    ]
    out = yahoo.fetch_prices(["AAPL", "ZZZZ"])
    assert out == {"AAPL": {"close": 255.0, "change_pct": 0.5, "volume": 1200,
                            "as_of": "2026-10-23", "sector": "Technology",
                            "avg_volume_20d": 1000.0, "rvol": 1.2}}


def test_parse_chart_rvol_uses_last_20_volumes():
    n = 25
    closes = [100.0 + i for i in range(n)]
    volumes = [1000] * 20 + [5000] * 5
    body = {
        "chart": {
            "result": [{
                "timestamp": list(range(1, n + 1)),
                "indicators": {"quote": [{"close": closes, "volume": volumes}]},
            }],
        },
    }
    parsed = yahoo.parse_chart(body)
    # 直近20営業日の平均（1000*15 + 5000*5)/20 = 2000、RVol = 5000/2000 = 2.5
    assert parsed["avg_volume_20d"] == 2000.0
    assert parsed["rvol"] == 2.5
    # 終値・前日比は最後の2点から自前計算
    assert parsed["close"] == closes[-1]


def test_fetch_one_uses_range_1mo():
    import requests
    from unittest.mock import MagicMock
    session = MagicMock(spec=requests.Session)
    resp = MagicMock()
    resp.json.return_value = _chart_body([250.0, 255.0], [1000, 1200])
    resp.raise_for_status.return_value = None
    session.get.return_value = resp
    crumb = MagicMock()
    crumb.get.return_value = None
    yahoo._fetch_one("AAPL", session, crumb)
    args, kwargs = session.get.call_args
    assert kwargs["params"] == {"interval": "1d", "range": "1mo"}


@patch("src.yahoo._fetch_one")
def test_fetch_prices_respects_exclude(mock_fetch):
    yahoo.YAHOO_EXCLUDE.add("ZZZZ")
    try:
        out = yahoo.fetch_prices(["ZZZZ"])
        assert out == {}
        mock_fetch.assert_not_called()
    finally:
        yahoo.YAHOO_EXCLUDE.discard("ZZZZ")
