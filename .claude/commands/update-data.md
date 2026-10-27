---
description: 価格データを最新に更新する（NASDAQ Trader 銘柄マスタ差分チェック＆差し替え + Yahoo / Stooq 価格取得 + docs/data/latest.json 再生成）
---

米国上場個別株の `docs/data/latest.json` を最新に更新してください。

手順:
1. `./run_local.sh --no-serve` を実行してデータ更新を行う（venv、依存インストール、`python -m src.update` まで自動実行される）。
2. 出力で Yahoo の取得失敗銘柄数と Stooq フォールバックの件数を確認する。
3. 失敗が恒常化している銘柄があれば `src/yahoo.py` の `YAHOO_EXCLUDE` に追加を検討し、ユーザーに報告する。

注意:
- 4,700 銘柄程度で 15〜20 分かかることがある。タイムアウトを長めに設定すること。
- `docs/data/latest.json` が上書きされることを前提とするが、git の差分は大きくなるため commit はユーザーに確認してから行うこと。
