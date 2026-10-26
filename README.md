# 米国上場個別株一覧サイト

NYSE・NASDAQ・NYSE American 上場個別株（普通株）のセクター別一覧を GitHub Pages で公開し、GitHub Actions で定期自動更新する静的サイトです。仕様は [spec.md](spec.md) です。構成は `jptick` リポジトリがテンプレート。

## 動かし方

```bash
./run_local.sh
```

venv 作成、依存インストール、`python -m src.update`、`docs/` の簡易サーバ（既定 8080）まで一気にやります。`docs/data/latest.json` が上書きされます。ブラウザで `http://127.0.0.1:8080/` を開きます。

```bash
./run_local.sh --no-serve    # JSON 更新だけ
./run_local.sh --serve-only  # 既存 latest.json を配信するだけ
PORT=9000 ./run_local.sh
```

## データソース

- **銘柄マスタ**: NASDAQ Trader の symboldirectory（[nasdaqlisted.txt](https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt) / [otherlisted.txt](https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt)。固定 URL・パイプ区切りテキスト）。取得に成功したら `data/*.txt` のスナップショットを差し替え、失敗時はリポジトリ内スナップショットを使う。全列は `fields` として保持する（表示はしない）。
- **対象銘柄の絞り込み**: NYSE・NASDAQ・NYSE American の普通株のみ。otherlisted の Exchange 列は N=NYSE / A=NYSE American のみ対象（P=NYSE Arca / Z=Cboe は除外）。ETF フラグ・NextShares・Test Issue と、セキュリティ名のキーワード（Preferred / Depositary / Warrant / Units / Rights / Notes / Debenture / Ordinary / Acquisition Corp / REIT）で普通株以外を除外する。
- **価格（主）**: Yahoo Finance の chart API（`query1.finance.yahoo.com/v8/finance/chart/{ティッカー}?interval=1d&range=5d`。米国株は接尾辞なし、ティッカーの `.` は `-` に置換）。終値・前日比は close 配列の最後の2点から `(P_n/P_{n-1}-1)*100` で自前計算する。出来高は `volume` 配列の最終ポイント（None なら直近の有効値）。リクエスト間隔は 0.1 秒（4,700 銘柄で 15〜20 分。セクター取得も同タイミングで行うため倍になる）。
- **セクター**: chart レスポンスには含まれないため、Yahoo の quoteSummary（assetProfile モジュール）をクッキー＋crumb で別途取得する。取得できない銘柄は「未分類」タブ。恒常失敗する銘柄は `src/yahoo.py` の `YAHOO_EXCLUDE` で管理し、Yahoo リクエストを省いて Stooq フォールバックで埋める。
- **価格（フォールバック）**: [Stooq](https://stooq.com/) の日次CSV（`https://stooq.com/q/d/l/?s={ティッカー}.us&i=d`。小文字＋`.` → `-`＋`.us`）。Yahoo で取れなかった銘柄だけ埋める。最後の2営業日の Close で同様に終値・前日比を算出し、UI 上は Yahoo の値と混在して「参考値（USD, YYYY-MM-DD時点）」と明記する。日次バーは latest.json に保持しない。

API キーは不要（Yahoo も Stooq も）。リポジトリ secret は設定しない。

## テスト

```bash
pip install -r requirements-dev.txt
pytest -q
```

マスタの列マッピング・フィルタ条件・Yahoo の終値・前日比算出・セクター集約・latest.json スキーマを検証する。symboldirectory の列構成が NASDAQ Trader 側で変わると `tests/test_master.py` が落ちる。

## GitHub Pages

リポジトリ Settings → Pages → **Deploy from a branch** → Branch: `main`、Folder: `/docs`。

GitHub Actions（`.github/workflows/update.yml`）が平日 22:00 UTC（ET 17:00、夏時間 JST 7:00 / 冬時間 JST 8:00）と `workflow_dispatch` で Yahoo Finance から価格を取り（Stooq はフォールバック）、シンボルディレクトリの差分チェック＆差し替えをして `latest.json` を `[skip ci]` 付きで `main` に push します。API キーは不要のため secret は設定しません。`GITHUB_TOKEN` に `contents: write` が必要です。

## プロジェクト構造

```
src/
  master.py    # NASDAQ Trader symboldirectory のダウンロードとパース・普通株フィルタ（銘柄マスタ）
  yahoo.py     # Yahoo Finance 価格・セクター取得（主。終値・前日比の自前計算・除外銘柄管理）
  stooq.py     # Stooq 日次CSV取得（フォールバック用に終値・前日比を返す）
  update.py    # オーケストレーション（Yahoo → Stooq フォールバック）→ docs/data/latest.json
docs/
  index.html   # セクタータブ＋7列シンプルテーブルの一覧。初期表示は前日比%降順、ヘッダクリックで昇順・降順ソート（検索なし）
  common.js    # 共通ユーティリティ
  data/latest.json  # 生成済みスナップショット（git 管理）
data/          # フォールバック用シンボルディレクトリスナップショット（git 管理）
tests/         # pytest 単体テスト
```

## 検証コマンド

```bash
pytest -q
python -m src.update
./run_local.sh --no-serve
```
