"""NASDAQ Trader の symboldirectory を取得・パースする（銘柄マスタ）。

対象は NYSE・NASDAQ・NYSE American の普通株のみ。
ETF/ETN・REIT・優先株式・ADR・外国株式・SPAC・ユニット等は除外する。

取得ファイル（固定 URL・パイプ区切りテキスト）:
- nasdaqlisted.txt: NASDAQ 上場銘柄。列は
  Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
- otherlisted.txt: NYSE / NYSE American / NYSE Arca / Cboe 等。列は
  ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
  Exchange 列の値域は A=NYSE American / N=NYSE / P=NYSE Arca / Z=Cboe（対象外）。

除外判定はセキュリティタイプ列（ETF / NextShares / Test Issue）と
セキュリティ名のキーワード（Preferred / Depositary / Warrant / Unit / Notes 等）で行う。

取得失敗時はリポジトリ内のフォールバックスナップショット（data/*.txt）を使う。
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

log = logging.getLogger("master")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SYMDIR_URL = "https://www.nasdaqtrader.com/dynamic/symdir/{name}"

FILES = ("nasdaqlisted.txt", "otherlisted.txt")

# otherlisted の Exchange 列 → 表示名（P=NYSE Arca / Z=Cboe / それ以外は対象外）
EXCHANGE_LABEL = {
    "N": "NYSE",
    "A": "NYSE American",
}

# セキュリティ名に含まれたら普通株以外として除外するキーワード（小文字比較）
EXCLUDE_NAME_KEYWORDS = (
    "preferred",      # 優先株式
    "preference",     # 優先株式
    "depositary",     # ADR / 預託証券
    "warrant",        # ウォラント
    "units",          # ユニット
    "rights",         # 新株予約権
    "notes",          # 社債・ETN
    "debenture",      # 社債
    "ordinary",       # 外国普通株 / ADR（Ordinary Shares）
    "acquisition corp",  # SPAC
    "reit",           # REIT
)


def normalize_value(v: object) -> object:
    return v.strip() if isinstance(v, str) else v


def is_excluded_name(name: str) -> bool:
    low = name.lower()
    return any(k in low for k in EXCLUDE_NAME_KEYWORDS)


def _parse_lines(text: str) -> list[dict]:
    """シンボルディレクトリテキストをヘッダ付き行の dict リストにパースする。

    フッタ行（File Creation Time: 〜）は除外する。"""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    header = lines[0].split("|")
    rows = []
    for ln in lines[1:]:
        if ln.startswith("File Creation Time:"):
            continue
        cols = ln.split("|")
        if len(cols) != len(header):
            continue
        rows.append({h: normalize_value(c) for h, c in zip(header, cols)})
    return rows


def _row_to_record(fields: dict) -> dict | None:
    if "Symbol" in fields:  # nasdaqlisted.txt
        ticker = fields["Symbol"]
        exchange = "NASDAQ"
        if fields.get("Test Issue") != "N":
            return None
        if fields.get("ETF") != "N" or fields.get("NextShares") != "N":
            return None
    else:  # otherlisted.txt
        ticker = fields["ACT Symbol"]
        exchange = EXCHANGE_LABEL.get(fields.get("Exchange") or "")
        if exchange is None:
            return None
        if fields.get("Test Issue") != "N" or fields.get("ETF") != "N":
            return None
    name = fields.get("Security Name") or ""
    if not ticker or is_excluded_name(name):
        return None
    return {
        "ticker": ticker,
        "name": name,
        "exchange": exchange,
        "fields": fields,
    }


def parse_directory(text: str) -> list[dict]:
    return [r for r in (_row_to_record(f) for f in _parse_lines(text)) if r]


def fetch_file(name: str, timeout: int = 30) -> str | None:
    """シンボルディレクトリをダウンロードする。失敗時は None。"""
    try:
        res = requests.get(SYMDIR_URL.format(name=name), timeout=timeout)
        res.raise_for_status()
        return res.text
    except Exception as e:
        log.warning("%s ダウンロード失敗: %s", name, e)
        return None


def load_master(fetch: bool = True) -> list[dict]:
    """2 ファイルを統合し、普通株レコードのリストを返す。

    各レコードは ticker / name / exchange / fields。
    fields はマスタの全列を保持する（詳細ページ復活に備えて残すが表示はしない）。
    ダウンロードに成功した場合は data/ のスナップショットを差し替える。
    """
    records: list[dict] = []
    for name in FILES:
        text = fetch_file(name) if fetch else None
        snapshot = DATA_DIR / name
        if text is None:
            text = snapshot.read_text(encoding="utf-8")
        else:
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text(text, encoding="utf-8")
        rows = parse_directory(text)
        log.info("%s: %s 銘柄（フィルタ後）", name, len(rows))
        records.extend(rows)
    return records
