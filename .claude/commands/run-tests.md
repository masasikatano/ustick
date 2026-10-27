---
description: pytest で全テストを実行し、結果を報告する
---

`pytest -q` を実行してテスト結果を報告してください。

- 失敗があれば `tests/test_master.py` の列マッピング（NASDAQ Trader の列構成変更の検知）や `tests/test_yahoo.py` の終値・前日比算出を中心に原因を調査すること。
- 依存が足りなければ `pip install -r requirements-dev.txt` してから再実行すること。
