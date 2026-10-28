# 米国上場個別株一覧サイト 仕様

NYSE・NASDAQ・NYSE American 上場個別株（普通株）のセクター別一覧を GitHub Pages で公開し、GitHub Actions で定期自動更新する静的サイト。構成は `/home/masasikatano/project/jptick/` をテンプレートにする。

## 決定事項（grilling による合意）

1. **データソース（銘柄マスタ）**
   - NASDAQ Trader の symboldirectory（`nasdaqlisted.txt` / `nyse-listed.txt` / `nyse-american-listed.txt` 等）を正（master）とする。固定URL・タブ区切りテキストで、GitHub Actions からの定期取得が容易。ETF・test issue 等の除外フラグも含まれる。
   - 3 ファイルとも定期ダウンロードし差分チェック＆差し替える。ダウンロード失敗時はリポジトリ内のフォールバックスナップショットを使う。
   - **対象は NYSE・NASDAQ・NYSE American の普通株のみ**（4,000〜4,500 銘柄想定）。ETF/ETN・REIT・優先株式・ADR・外国株式・SPAC・ユニット等は除外する。除外判定はマスタのセキュリティタイプ列（ETF / NextShares / 優先株 / デポジタリ受託証券 / ユニット等）と test issue フラグで行う。ティッカーに `.` 等が含まる特殊銘柄の扱いは実装時に列の値域テストで固定する。
   - **価格は Yahoo Finance（主）と Stooq（フォールバック）**。
     - Yahoo: `query1.finance.yahoo.com/v8/finance/chart/{ティッカー}?interval=1d&range=5d`（日本株の `.T` 接尾辞は不要）。終値・前日比は close 配列の最後の2点から `(P_n/P_{n-1}-1)*100` で自前計算する（`meta.regularMarketChangePercent` は使わない）。リクエスト間隔は 0.1 秒（4,000+ 銘柄で 7〜8分）。
     - Stooq: Yahoo で取得失敗した銘柄のみ、日次CSV（`https://stooq.com/q/d/l/?s={ティッカー}.us&i=d`）の最後の2営業日の close で同様に算出して埋める。APIキー不要。日次バー全体は latest.json に保持しない。

2. **更新スケジュール**
   - 日次1回。**Yahoo の日次バー確定（ET で当日分が揃うのは翌日未明頃）を待って**、UTC 4:15 火-土（JST 13:15 火-土、ET 前日 23:15 / 当日 0:15）と `workflow_dispatch` で Actions を回し、米国市場クローズ後の確定値で (a) Yahoo Finance から価格取得（Stooq フォールバック）、(b) マスタの差分チェック＆差し替え。
   - `[skip ci]` 付きで main に push（jptick 同様）。

3. **セクター区分**
   - NASDAQ Trader のマスタには業種列がないため、**セクターは Yahoo から取得する**（価格取得と同じレスポンス系列に sector/industry を含める）。
   - GICS 11セクター相当のタブに集約する。Yahoo からセクターが取得できない銘柄は「未分類」タブに入れる。
   - セクターは latest.json に保持し、新規上場銘柄にも自動追従する。

4. **詳細ページ**
   - **詳細ページは作らない**（jptick と同じく一覧テーブルのみ）。マスタの全列は `fields` として latest.json に保持するが表示はしない（将来の復活に備えデータは残す）。

5. **データファイル構成**
   - 単一 `docs/data/latest.json`。銘柄マスタ（全列）＋ 各銘柄の価格 `{ close, change_pct, volume, as_of }` ＋ セクター の最小形。日次バーは含めない。サイズは 3〜5MB 想定。

6. **一覧ページ機能**
   - セクタータブ（GICS 11セクター相当＋「未分類」）のみのシンプル一覧。検索はつけない。
   - 表示列は ティッカー / 銘柄名 / 取引所（NYSE・NASDAQ・NYSE American） / セクター / 終値 / 前日比 / 出来高 の7列（jptick 同型）。時価総額列は追加しない。
   - 初期表示は前日比%降順、列ヘッダクリックで昇順・降順ソート（jptick の実装実態に合わせる）。
   - 価格はサイトの免責表現として「参考値（USD, YYYY-MM-DD時点）」と必ず明記する（Yahoo の最新終値も含めて）。
   - セクタータブは銘柄数順で並べる。1タブ最大でも約800銘柄程度になりうる。

7. **UI言語**
   - **日本語UI**。タブ名・列見出し・免責表現は日本語、銘柄名・ティッカーは英語のまま。

8. **価格データソースの扱い（重要）**
   - Yahoo Finance を主とし、取得失敗した銘柄は Stooq でフォールバックする。それも失敗・未対象銘柄は行を残し「データなし」表示（jptick 同方針）。
   - 恒常的に Yahoo から取得失敗する銘柄は `src/yahoo.py` の `YAHOO_EXCLUDE` で管理し、Yahoo リクエストを省いて Stooq フォールバックで埋める。
   - 終値・前日比はいずれのソースでも close の最後の2点から自前計算する（前日比% = (P_n/P_{n-1}-1)*100）。Yahoo の `meta.regularMarketChangePercent` は使わない。
   - 出来高は終値と同じ基準日のものを使う（Yahoo は `indicators.quote.volume` の最終ポイント、Stooq は最終営業日の `Volume`）。取得できなければ `volume: null` で表示は「—」。
   - Stooq のティッカー形式は `{ティッカー}.us`（例: AAPL → `aapl.us`、BRK.B → `brk-b.us` のような置換ルールが必要。実装時に値域をテストで固定する）。
   - API キーは不要（Yahoo も Stooq も）。リポジトリ secret は設定しない。

9. **構成・技術**
   - jptick 同型の独立リポジトリ（`/home/masasikatano/project/ustick/`。作成時点では未 git init）。jptick から src/・tests/・docs/・run_local.sh・requirements*.txt・.github/workflows/update.yml・.gitignore をコピーして改造する。
   - Pages: branch `main` の `/docs`。バニラ JS（index.html / common.js）、Python パイプライン（`python -m src.update`）、pytest、run_local.sh。
   - 改造の要点:
     - `src/master.py`: NASDAQ Trader の symboldirectory テキストのダウンロード・パース。3 ファイルを統合し、普通株のみにフィルタ。
     - `src/yahoo.py`: ティッカー形式（接尾辞なし）への変更＋ sector/industry 取得の追加。終値・前日比の自前計算・フォールバック・除外管理ロジックはほぼ流用。
     - `src/stooq.py`: `src/jquants.py` に相当する新規モジュール。Stooq 日次CSV の取得・パース・終値・前日比算出。
     - `docs/index.html`: セクタータブ＋7列テーブル。前日比降順の初期表示＋ヘッダソート。
     - `tests/`: マスタの列マッピング・フィルタ条件・Yahoo の終値・前日比算出・セクター集約・latest.json スキーマを検証。

## 残リスク・注意

- Yahoo Finance のレート制限・レスポンス変更（4,000+ 銘柄・数千リクエスト規模で顕在化しやすい。リトライ＋リクエスト間隔 0.1 秒で対処。恒常失敗銘柄は `YAHOO_EXCLUDE`）。
- セクターは Yahoo 依存のため、Yahoo 側の仕様変更・取得失敗で「未分類」が増えうる（表示は崩れないがタブの意味が薄れる。未取得時の挙動をテストで固定する）。
- Stooq のレート制限・CSV 形式変更（フォールバックは Yahoo の失敗銘柄のみに絞る。リトライ＋バックオフ）。
- NASDAQ Trader の symboldirectory の列構成・セキュリティタイプの値域変更（列マッピング・値域のテストで防ぐ）。
- 米国の休場日（祝日・ハリケーン等）は取得ウィンドウ `range=5d` で吸収するが、連休明けの前日比は直近営業日ベースになる点を免責表現でカバーする。
- 4,000+ 銘柄のブラウザ描画・latest.json サイズ（3〜5MB 想定。問題になったらセクターごと分割を検討）。
- Stooq の `.us` ティッカー変換ルール（BRK.B → brk-b 等）は実装時に代表的銘柄で検証する。
