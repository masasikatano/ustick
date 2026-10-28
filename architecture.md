# アーキテクチャ

## 概要

米国（NYSE・NASDAQ・NYSE American）上場個別株のセクター別一覧を GitHub Pages で公開する静的サイト。データの正本は外部の公開データソースで、リポジトリは「取得パイプライン + 生成済み JSON + 表示 UI」の3層構成。

```
[NASDAQ Trader symboldirectory]   [Yahoo Finance]        [Stooq]
        │ 銘柄マスタ・フィルタ       │ 価格(主)・セクター      │ 価格(フォールバック)
        ▼                          ▼                       ▼
   src/master.py              src/yahoo.py             src/stooq.py
        └────────────┬───────────┴────────────┬───────────┘
                     ▼                        ▼
               src/update.py（オーケストレーション）
                     ▼
            docs/data/latest.json（3〜5MB、git 管理）
                     ▼
        docs/index.html + common.js（セクタータブ＋7列テーブル）
                     ▼
        GitHub Pages（main ブランチ /docs）
```

## 更新フロー

1. **銘柄マスタ**（`src/master.py`）: NASDAQ Trader の `nasdaqlisted.txt` / `otherlisted.txt` をダウンロード。成功時は `data/*.txt` スナップショットを差し替え、失敗時はリポジトリ内スナップショットで継続。NYSE / NASDAQ / NYSE American の普通株のみ抽出（ETF・REIT・優先株・ADR・SPAC・ユニット等は除外）。
2. **価格・セクター**（`src/yahoo.py`）: chart API（`range=5d&interval=1d`）で終値・出来高を取得。終値・前日比は close の最後の2点から `(P_n/P_{n-1}-1)*100` で自前計算。セクターは quoteSummary（assetProfile、クッキー＋crumb）で別途取得し、失敗銘柄は「未分類」。恒常失敗銘柄は `YAHOO_EXCLUDE` で Yahoo リクエストを省略。
3. **フォールバック**（`src/stooq.py`）: Yahoo 失敗銘柄のみ、日次CSV（`{ticker}.us`）の最後の2営業日で同様に算出。
4. **統合**（`src/update.py`）: 銘柄マスタ（全列を `fields` に保持）＋価格 `{close, change_pct, volume, as_of}`＋セクターを `docs/data/latest.json` に書き出す。日次バーは保持しない。

## 配信フロー

- ローカル: `run_local.sh` が venv 作成・依存インストール・更新・`docs/` 簡易サーバまで担う。
- CI/CD: `.github/workflows/update.yml` が UTC 4:15 火-土（JST 13:15 火-土。Yahoo の日次バー確定後）に実行し、`[skip ci]` 付きで `main` に push。GitHub Pages（branch `main` / `/docs`）が配信。API キー・secret は不要。

## 主要な設計判断（変更時は spec.md と照合）

- 前日比はどのソースでも自前計算（Yahoo の `meta.regularMarketChangePercent` は不使用）。
- 詳細ページなし。検索なし。表示は7列（ティッカー/銘柄名/取引所/セクター/終値/前日比/出来高）。
- 日本語UI。価格は「参考値（USD, YYYY-MM-DD時点）」表記必須。
- 取得ウィンドウ `range=5d` で米国休場日を吸収するが、連休明けの前日比は直近営業日ベース（免責表現でカバー）。
- リクエスト間隔 0.1 秒（4,700 銘柄で 15〜20 分。セクター取得を含めると倍）。
- `tests/test_master.py` が symboldirectory の列構成変更を検知する（意図された警報として機能）。
