---
name: update-data
description: docs/data/latest.json のデータ更新パイプラインを実行・検証する。価格更新の実行、取得失敗銘柄の調査、YAHOO_EXCLUDE の追加判断が必要な場面で使う。
---

# データ更新パイプライン

`./run_local.sh --no-serve` で一括実行できる（venv → 依存インストール → `python -m src.update`）。

## 処理の流れ
1. `src/master.py`: NASDAQ Trader の symboldirectory（nasdaqlisted.txt / otherlisted.txt）をダウンロードし、取得に成功したら `data/*.txt` スナップショットを差し替え、失敗時は既存スナップショットを使用。NYSE / NASDAQ / NYSE American の普通株のみにフィルタ。
2. `src/yahoo.py`: chart API（`range=5d&interval=1d`）で終値・出来高を取得。前日比は close の最後の2点から `(P_n/P_{n-1}-1)*100` で自前計算（`meta.regularMarketChangePercent` は使わない）。セクターは quoteSummary（assetProfile）をクッキー＋crumb で取得。
3. `src/stooq.py`: Yahoo 失敗銘柄のみ、日次CSV（`{ticker}.us`、`.` → `-`）でフォールバック。
4. `src/update.py`: 統合して `docs/data/latest.json` に書き出す。

## 注意点
- 4,700 銘柄で 15〜20 分かかる。タイムアウトは長めに。
- 恒常的に Yahoo で失敗する銘柄は `src/yahoo.py` の `YAHOO_EXCLUDE` に追加し、Yahoo リクエストを省いて Stooq で埋める。
- 更新後は `tests/` を回してスキーマや算出ロジックの劣化がないか確認する。
