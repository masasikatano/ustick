# ヒートマップページ仕様（Technology 上位・TradingView）

## 決定事項（grilling による合意）

1. **ページ配置・形式**
   - `docs/heatmap.html` を新規作成する独立静的ページとする。
   - 既存 `docs/index.html`（一覧テーブル）とは分離し、相互リンクで行き来する。

2. **TradingView ウィジェット方式**
   - 公式 Stock Heatmap ウィジェット（`embed-widget-stock-heatmap.js`）を使う。
   - 取引所 `NASDAQ / NYSE`、グループ `Technology`、サイズ基準は時価総額、カラーは前日比。
   - 銘柄50件を自前で固定管理しない（ウィジェット任せ）。

3. **「上位50件」の扱い**
   - 件数はウィジェットの表示にお任せでOK（厳密な50件切りにはこだわらない）。
   - ウィジェット側で Technology グループ内・時価総額降順の上位表示ができる場合はそれを使い、できなければ可能な範囲の件数制限を使う。

4. **見た目・導線・免責**
   - 既存 `index.html` と同じダークテーマ・日本語ヘッダーに合わせる。
   - `index.html` ↔ `heatmap.html` の相互リンクを付ける。
   - 「参考値・TradingView提供」の免責表記を付ける。

5. **データ更新パイプラインへの影響**
   - Python 側（`src/`・`docs/data/latest.json`・GitHub Actions）は一切触らない。
   - ブラウザが直接 TradingView から取得するフロント埋め込みだけで完結させる。

## 非ゴール

- `src/` への時価総額取得追加、銘柄50件の自前管理はしない。
- `index.html` の一覧テーブル仕様変更はしない。
