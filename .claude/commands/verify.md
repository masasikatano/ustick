---
description: 変更前の標準検証（pytest + データ更新）をすべて実行する
---

以下の検証コマンドをすべて実行し、結果をまとめて報告してください:

```bash
pytest -q
./run_local.sh --no-serve
```

- いずれかが失敗した場合は原因を特定し、修正はユーザーに確認してから行うこと。
- `python -m src.update` は `./run_local.sh --no-serve` が内部で実行するため個別に実行不要。
