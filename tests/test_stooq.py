"""Stooq フォールバックのテスト（モック使用）。"""

from unittest.mock import patch

from src import stooq

CSV_SAMPLE = """Date,Open,High,Low,Close,Volume
2026-10-21,248.0,251.0,247.0,250.0,1000
2026-10-22,250.0,256.0,249.0,255.0,1200
2026-10-23,255.0,257.0,253.0,256.5,900
"""


def test_symbol():
    # Stooq 形式は小文字＋"." → "-"＋.us 接尾辞
    assert stooq.symbol("AAPL") == "aapl.us"
    assert stooq.symbol("BRK.B") == "brk-b.us"


def test_parse_csv():
    parsed = stooq.parse_csv(CSV_SAMPLE)
    assert parsed["close"] == 256.5
    assert abs(parsed["change_pct"] - round((256.5 / 255.0 - 1) * 100, 3)) < 1e-9
    assert parsed["volume"] == 900  # 終値と同じ最終営業日の出来高
    assert parsed["as_of"] == "2026-10-23"


def test_parse_csv_single_row():
    parsed = stooq.parse_csv("Date,Open,High,Low,Close,Volume\n2026-10-23,1,1,1,10.0,100\n")
    assert parsed["close"] == 10.0
    assert parsed["change_pct"] is None


def test_parse_csv_no_data():
    assert stooq.parse_csv("Exceeded the daily hits limit") is None
    assert stooq.parse_csv("") is None


@patch("src.stooq._fetch_one")
def test_fetch_prices_skips_failures(mock_fetch):
    mock_fetch.side_effect = [
        {"close": 255.0, "change_pct": 0.5, "volume": 1200, "as_of": "2026-10-23"},
        None,
    ]
    out = stooq.fetch_prices(["AAPL", "ZZZZ"])
    assert out == {"AAPL": {"close": 255.0, "change_pct": 0.5, "volume": 1200, "as_of": "2026-10-23"}}
