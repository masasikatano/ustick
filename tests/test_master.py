"""NASDAQ Trader symboldirectory の列マッピング・普通株フィルタの回帰テスト。"""

import pytest

from src.master import DATA_DIR, is_excluded_name, load_master, parse_directory

NASDAQLISTED_SAMPLE = """Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAPL|Apple Inc. Common Stock|Q|N|N|100|N|N
QQQ|Invesco QQQ Trust Series 1|G|N|N|100|Y|N
TEST|Test Issue Common Stock|Q|Y|N|100|N|N
SPAC|XYZ Acquisition Corp. Class A Ordinary Share|S|N|N|100|N|N
PREFF|Some Bancorp Preferred Stock|Q|N|N|100|N|N
File Creation Time: 1026202603:03
"""

OTHERLISTED_SAMPLE = """ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
BRK.B|Berkshire Hathaway Inc. Class B Common Stock|N|BRK.B|N|100|N|BRK.B
BAC$L|Bank of America Corporation Non Cumulative Perpetual Conv Pfd Ser L|N|BACpL|N|10|N|BAC-L
WI|Some Inc Common Stock When-Issued|N|WI|N|100|N|WI
XOM|Exxon Mobil Corporation Common Stock|N|XOM|N|100|N|XOM
SPY|SPDR S&P 500 ETF Trust|P|SPY|Y|100|N|SPY
ARCA|Some Arca Inc. Common Stock|P|ARCA|N|100|N|ARCA
AMEX|Some Amex Inc. Common Stock|A|AMEX|N|100|N|AMEX
UNIT|Some Holding Units|A|UNIT|N|100|N|UNIT
File Creation Time: 1026202603:03
"""


def test_parse_nasdaqlisted_filters():
    recs = parse_directory(NASDAQLISTED_SAMPLE)
    tickers = {r["ticker"] for r in recs}
    assert tickers == {"AAPL"}
    assert recs[0]["exchange"] == "NASDAQ"
    assert recs[0]["fields"]["Security Name"] == "Apple Inc. Common Stock"


def test_parse_otherlisted_exchange_filter():
    recs = parse_directory(OTHERLISTED_SAMPLE)
    by_ticker = {r["ticker"]: r for r in recs}
    assert set(by_ticker) == {"BRK.B", "XOM", "AMEX"}
    assert by_ticker["BRK.B"]["exchange"] == "NYSE"
    assert by_ticker["AMEX"]["exchange"] == "NYSE American"
    # NYSE Arca（P）は対象外、ユニット・優先株（$）・when-issued も除外
    assert "ARCA" not in by_ticker
    assert "UNIT" not in by_ticker
    assert "SPY" not in by_ticker  # ETF フラグ
    assert "BAC$L" not in by_ticker  # 優先株クラス
    assert "WI" not in by_ticker  # when-issued


def test_footer_line_skipped():
    recs = parse_directory(NASDAQLISTED_SAMPLE)
    assert all("File Creation" not in r["ticker"] for r in recs)


def test_is_excluded_name():
    assert is_excluded_name("ABC Preferred Stock")
    assert is_excluded_name("XYZ Depositary Shares")
    assert is_excluded_name("Some Corp. Units")
    assert is_excluded_name("AA Acquisition Corp. Common Stock")
    assert is_excluded_name("Foreign Co. Ordinary Shares")
    assert not is_excluded_name("Apple Inc. Common Stock")
    assert not is_excluded_name("Berkshire Hathaway Inc. Class B Common Stock")


@pytest.fixture(scope="module")
def records():
    assert (DATA_DIR / "nasdaqlisted.txt").is_file(), "テスト用のローカルスナップショット（data/*.txt）が必要"
    return load_master(fetch=False)


def test_record_count(records):
    # NYSE・NASDAQ・NYSE American の普通株は 4,000〜5,000 銘柄想定
    assert 3800 <= len(records) <= 5500


def test_only_target_exchanges(records):
    exchanges = {r["exchange"] for r in records}
    assert exchanges == {"NYSE", "NASDAQ", "NYSE American"}
    for rec in records:
        assert rec["fields"].get("Test Issue") == "N"
        assert rec["fields"].get("ETF") == "N"


def test_aapl_and_brkb(records):
    by_ticker = {r["ticker"]: r for r in records}
    aapl = by_ticker["AAPL"]
    assert "Apple" in aapl["name"]
    assert aapl["exchange"] == "NASDAQ"
    brkb = by_ticker["BRK.B"]
    assert "Berkshire" in brkb["name"]
    assert brkb["exchange"] == "NYSE"


def test_fields_preserved(records):
    for rec in records:
        assert "Security Name" in rec["fields"]
        assert len(rec["fields"]) >= 7, f"{rec['ticker']}: 列が不足"


def test_no_obvious_non_common(records):
    # フィルタ漏れの代表例が残っていないか
    for rec in records:
        low = rec["name"].lower()
        assert "preferred" not in low
        assert "depositary" not in low
        assert "warrant" not in low
        assert "units" not in low
