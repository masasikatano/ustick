# Potent Scan / Pre-market Scan 仕様

## 決定事項（grilling による合意）

1. **方針**
   - Potent Scan は自前実装する。Pre-market Scan は TradingView 埋め込み（heatmap と同じ方式）とする。

2. **Potent 条件（固定値）**
   - 株価（終値）> $2、出来高 > 300,000株、前日比 > +4%、RVol > 2.0。
   - RVol = 当日出来高 / 20日平均出来高（`avg_volume_20d`）。
   - バリエーション（$5 / 50万株 / +10% 等）の切替 UI は作らない。

3. **RVol の分母**
   - Yahoo Finance の取得を `range=5d` から `range=1mo` に延ばし、出来高の直近20営業日平均を `avg_volume_20d` として算出する。
   - リクエスト数は変えない（レスポンスが少し重くなるだけ）。
   - Stooq フォールバック銘柄の平均出来高は取得しない。

4. **平均出来高なしの扱い**
   - `avg_volume_20d` がない銘柄も、他3条件（価格・出来高・前日比）を満たせば Potent 対象として掲載し、RVol 列は「—」表示とする。
   - `latest.json` の価格オブジェクトには `avg_volume_20d: null` で保持する。

5. **ページ構成**
   - `docs/scan.html`（Potent 自前表示）を新規作成する。
   - `docs/premarket.html`（Pre-market 専用、TradingView 埋め込みのみ）を新規作成する。Python・GitHub Actions は触らない。
   - `docs/index.html` の7列テーブル仕様は変えず、3ページ間の相互リンクだけ追加する。

6. **Potent ページ表示**
   - 列は既存7列（ティッカー / 銘柄名 / 取引所 / セクター / 終値 / 前日比 / 出来高）＋ RVol 列の8列。
   - 掲載対象は Potent 条件に合致した銘柄のみ。初期表示は前日比%降順、列ヘッダクリックで昇順・降順ソート。
   - 日本語UI・「参考値（USD, YYYY-MM-DD時点）」の免責表記は既存に合わせる。

7. **データファイル構成**
   - `docs/data/latest.json` の価格オブジェクトを `{ close, change_pct, volume, as_of, sector, avg_volume_20d, rvol }` に拡張する（`rvol` は `volume / avg_volume_20d`、算出不可は `null`）。
   - 日次バー全体は保持しない（既存方針どおり）。

8. **更新パイプラインへの影響**
   - `src/yahoo.py` の取得レンジ変更（`range=1mo`）＋平均出来高・RVol 算出の追加、`src/update.py` のスキーマ拡張、対応する `tests/` の追加・更新を行う。
   - 更新スケジュール・`[skip ci]` push・secret 不要の方針は変えない（`spec.md` どおり）。

## 非ゴール

- Pre-market の自前データ取得・場中リアルタイム更新はしない。
- `index.html` の一覧テーブル仕様変更はしない。
- 週末用 Leader Scan（過去30日上昇率トップ）は今回含めない。
- セクター重複表示・EMA パーフェクトオーダー分類・押し目アラート等の絞り込み支援は今回含めない。
