---
name: codebase-guide
description: ustick リポジトリ（米国上場個別株一覧サイト）の構成・設計判断・データソースの参照先。初めて触る場面や構成変更の前に使う。
---

# コードベースガイド

米国（NYSE・NASDAQ・NYSE American）上場個別株のセクター別一覧を GitHub Pages で公開する静的サイト。仕様の正本は `spec.md`、運用の正本は `README.md`。

## 主要ファイル
- `src/master.py` — 銘柄マスタ（NASDAQ Trader symboldirectory）の取得・パース・普通株フィルタ
- `src/yahoo.py` — 主データソース（価格 + セクター）。`YAHOO_EXCLUDE` で恒常失敗銘柄を管理
- `src/stooq.py` — フォールバック（日次CSV）
- `src/update.py` — オーケストレーション → `docs/data/latest.json`
- `docs/index.html` / `docs/common.js` — セクタータブ＋7列テーブルの UI（日本語UI、検索なし）
- `run_local.sh` — ローカル一括実行（更新 + `docs/` 配信）
- `.github/workflows/update.yml` — UTC 4:15 火-土（JST 13:15 火-土。Yahoo の日次バー確定後）の定期更新＆ push（`[skip ci]`）

## 不変の設計判断
- 対象は普通株のみ（ETF/REIT/優先株/ADR/SPAC 等は除外）。フィルタ条件の変更は spec.md 決定事項 1 に従う。
- 前日比・終値はいずれのソースでも自前計算。Yahoo の `meta.regularMarketChangePercent` は使わない。
- 価格表示は「参考値（USD, YYYY-MM-DD時点）」と必ず明記。
- 詳細ページは作らない。マスタ全列は latest.json の `fields` に保持しても表示しない。
- API キー不要。GitHub secret は設定しない。

## テンプレート
`jptick` リポジトリ（/home/masasikatano/project/jptick/）が構成のテンプレート。新機能を検討する際はまずそちらの実装実態を確認する。
