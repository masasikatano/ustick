---
name: test-and-verify
description: pytest の実行、テストの追加・修正、コミット前の検証フロー。src/ の変更後の確認に使う。
---

# テスト・検証

## 実行方法
```bash
pip install -r requirements-dev.txt
pytest -q
```

## テストの役割
- `tests/test_master.py`: NASDAQ Trader symboldirectory の列マッピング・フィルタ条件。列構成が変わるとここが落ちる（意図された警報）。
- `tests/test_yahoo.py`: 終値・前日比算出・セクター集約。前日比 = `(P_n/P_{n-1}-1)*100` は必ず自前計算。
- `tests/test_stooq.py`: Stooq CSV のパースと `.us` ティッカー変換（BRK.B → brk-b.us）。
- `tests/test_update.py`: latest.json スキーマ。

## ルール
- 新しい除外条件や算出ロジックを変えたら、必ず対応するテストも更新する。
- 仕様の判断に迷ったら `spec.md` の「決定事項」が正。README と spec が矛盾する場合はユーザーの確認を取る。
