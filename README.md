# 2026年〜 国内震度5以上 地震プロットマップ (AI防災アシスタント搭載)

本プロジェクトは、2026年以降に日本国内で発生した最大震度5弱以上の地震データを、インタラクティブな日本地図上にビジュアルマッピングした高機能Webアプリケーションです。

「漏れなく、ダブりなく」データを可視化する独自の重複回避表示システムや、**Gemini Flash API（最新版）**を活用した高度なAI防災トレンド分析、APIとの自動同期（1日2回）機能を1つのHTMLファイルに凝縮しています。Cloud Run で公開するための Python サーバーも同梱しており、Gemini APIキーをブラウザに渡さずにAI機能を提供できます。

## 💥 主な機能

### 1. インタラクティブな日本地図プロット

* **直感的なスケール設計**: マグニチュード（M）の大きさを円の半径で、最大震度の強さを5色のカラー（5弱:黄 / 5強:オレンジ / 6弱:赤 / 6強:濃赤 / 7:紫）で直感的に表現しています。

* **シームレスなUI連動**: 左側のタイムラインリストと地図上のプロットがホバー・クリックで相互にハイライト＆ズーム連動します。

### 2. 重複震源地の自動分散表示（オフセット配置）

* 島根県東部、長野県北部、茨城県南部など、**全く同じ緯度経度で複数回発生した地震**の重なりを防ぐため、元の震央から約20km相当（緯度0.18度）の半径の円周上に自動で放射状に分散配置し、本来の位置と点線で繋ぐロジックを実装しています。

### 3. 動的衝突回避ラベル（常時表示機能）

* 画面右上のスイッチをONにすることで、プロットの横に日本語ラベル（発生日、震源地、M、最大震度）を常時表示できます。

* オフセット方向（分散角度）に合わせてラベルの展開方向（上下左右）を自動で切り替えるため、**ラベル同士が重複して見えなくなるのを防ぎます**。

### 4. Gemini Flash 連携「AI防災アシスタント」

* **✨ 総合活動レポート**: 蓄積された地震データを分析し、日本列島規模でのひずみ解放のトレンドと実践的な防災アクションプランをAIが一発でレポートします。

* **✨ 個別震源詳細分析**: リストの「✨ AI詳細分析」をクリックすると、その震央周辺の地質学的・プレート境界学的背景、想定されるインフラ被害、今後の警戒余震について、個別最適化された専門知識をGeminiが提示します。

* **✨ 防災チャット**: 日常生活の備え、家具固定、家族の連絡方法など、防災に関する疑問にAIがいつでもお答えします。

### 5. 1日2回の自動API同期（12時間カウントダウン）

* 気象庁が発表する地震情報を配信する「P2P地震情報 API」とバックグラウンドで自動同期。

* 更新頻度は「1日2回（12時間に1回）」に最適化されており、左上のインジケーターで「時:分:秒」単位のカウントダウンを行います。

* 初期起動時には必ず最新情報をフェッチしてマージ・重複排除するため、常に最新状態から始まります。

* **【未来対応】**: データの取得条件を「2026年以降（>=2026）」としているため、2027年以降に発生する未来の地震についても、プログラムを書き換えることなく完全に自動取得・プロット・AI分析が対応可能です。

## 🛠️ 使用テクノロジー

* **Frontend**: HTML5 / CSS3 / ES6+ JavaScript

* **Styling**: Tailwind CSS (CDNによるレスポンシブデザイン)

* **Map Utility**: Leaflet.js (国土地理院 地理院タイル「淡色地図」をCSSフィルタでダーク化)

* **Backend**: Python 3.12 / FastAPI（AI機能の中継、Cloud Run で実行）

* **Generative AI**: Gemini Flash API（最新版エイリアス `gemini-flash-latest`、公式SDK `google-genai`）

* **Data Source API**: P2P地震情報 API

* **Hosting**: Google Cloud Run / Secret Manager

## 🚀 使い方

利用方法は3通りあります。地図・タイムライン・自動同期はどれでも同じように動き、AI機能の呼び出し方だけが異なります。

| 利用方法 | AI機能の呼び出し | Gemini APIキーの置き場所 |
| --- | --- | --- |
| ① Cloud Run で公開 | ブラウザ → サーバー（`/api/ai`）→ Gemini | Secret Manager（サーバーだけが読む） |
| ② ローカルでサーバーを起動 | ①と同じ | 手元の環境変数 `GEMINI_API_KEY` |
| ③ HTML ファイルを直接開く | ブラウザ → Gemini を直接呼ぶ | 画面で入力したご自身のキー |

設計の詳細は [`docs/architecture.md`](docs/architecture.md) を参照してください。

### ③ HTML ファイルを直接開く（いちばん手軽）

1. `web/earthquake_map.html` をお使いのパソコンに保存します。

2. HTML ファイルをダブルクリック、または Google Chrome などのWebブラウザにドラッグ＆ドロップします。

3. AI機能を使う場合は「✨ AI防災分析」タブを開き、「🔑 Gemini APIキー」欄にご自身のキーを入力して「保存」を押します。キーは [Google AI Studio](https://aistudio.google.com/apikey) で取得できます。

* キーは通常、タブを閉じると消えます（`sessionStorage`）。「このブラウザに保存する」をチェックした場合のみ、ブラウザに残ります（`localStorage`）。「削除」でいつでも消せます。
* キーは Gemini API への通信にだけ使われます（`x-goog-api-key` ヘッダー）。HTML ファイルにキーを書き込む必要はありません。

### ② ローカルでサーバーを起動する

Python 3.12 以降が必要です。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt

export GEMINI_API_KEY="ご自身のGemini APIキー"
python server/main.py
```

ブラウザで <http://localhost:8080/> を開きます。Docker を使う場合は次のとおりです。

```bash
docker build -t earthquake-map .
docker run --rm -p 8080:8080 -e GEMINI_API_KEY="ご自身のGemini APIキー" earthquake-map
```

### ① Cloud Run で公開する

事前に [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)（`gcloud`）をインストールし、`gcloud auth login` と `gcloud config set project <プロジェクトID>` を済ませておきます。

```bash
# 使うサービスを有効にする
gcloud services enable run.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com

# 1. Gemini APIキーを Secret Manager に登録する（キーは標準入力から渡し、履歴に残さない）
printf '%s' "ご自身のGemini APIキー" | gcloud secrets create gemini-api-key --data-file=-

# 2. Cloud Run 用のサービスアカウントを作り、キーの読み取りだけを許可する
gcloud iam service-accounts create earthquake-map-run
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:earthquake-map-run@<プロジェクトID>.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 3. デプロイする（リポジトリのルートで実行）
gcloud run deploy earthquake-map \
  --source . \
  --region asia-northeast1 \
  --service-account earthquake-map-run@<プロジェクトID>.iam.gserviceaccount.com \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --min-instances 0 \
  --max-instances 2 \
  --allow-unauthenticated
```

デプロイ後、費用の上限として Cloud Billing の「予算とアラート」で **spend cap** タイプの予算を、Gemini API 用と Cloud Run 用に1つずつ作成します。上限に達すると、そのサービスの利用が月末まで自動で停止します。厳密な上限ではなく超過分も請求されるため、許容額より少し低めに設定してください（詳細は [`docs/architecture.md`](docs/architecture.md) の「コスト管理」）。

#### サーバーの設定（環境変数）

| 変数 | 既定値 | 内容 |
| --- | --- | --- |
| `GEMINI_API_KEY` | （必須） | Gemini APIキー。Cloud Run では Secret Manager から渡す |
| `GEMINI_MODEL` | `gemini-flash-latest` | 使用するモデル |
| `MAX_OUTPUT_TOKENS` | `4096` | 1回の回答の最大トークン数 |
| `RATE_LIMIT_PER_MINUTE` | `10` | 接続元IPごとの1分あたりのAIリクエスト上限 |
| `QUAKE_CACHE_SECONDS` | `600` | サーバーが取得した地震データのキャッシュ時間（秒） |
| `PORT` | `8080` | 待ち受けポート（Cloud Run が自動で設定） |

> ⚠️ **APIキーの取り扱いにご注意ください**
>
> * APIキーを HTML やソースコードに書き込んでコミット・公開しないでください。
> * ローカルでキーをファイルに保存する場合は `.env` などを使ってください（`.gitignore` で除外済み）。

## 🧪 テスト

スモークテストは2種類あります。どちらも本物の Gemini APIキーは使いません。

| テスト | 内容 | 実行時間 | 必要なもの |
| --- | --- | --- | --- |
| サーバー（`tests/test_server.py`） | `/api/ai` の入力検証、回数制限、Gemini のエラー処理、地震データの絞り込みなど | 数秒 | なし（Gemini と P2P地震情報は偽物に置き換え） |
| ブラウザ（`tests/test_browser.py`） | `http(s)://` と `file://` の切り替え、APIキー入力欄、HTML エスケープなど | 20秒前後 | インターネット接続（CDN の読み込み）、Playwright 用のブラウザ |

```bash
pip install -r tests/requirements.txt

# サーバーのテスト（既定。GitHub Actions でも push / PR ごとに自動実行）
pytest

# ブラウザのテスト（初回のみ Playwright 用の Chromium をダウンロード）
playwright install chromium
pytest -m browser

# インストール済みの Google Chrome を使う場合はダウンロード不要
pytest -m browser --browser-channel chrome
```

本物の Gemini での動作確認は、費用とキーが必要なため自動テストに含めていません。「② ローカルでサーバーを起動する」の手順で手動で確認してください。

## 📁 ファイル構成

* `web/earthquake_map.html` — アプリケーション本体（地図・タイムライン・AI機能の画面）

* `server/main.py` — HTML の配信と AI機能の中継を行う Python サーバー

* `server/requirements.txt` — サーバーが使う Python パッケージ

* `tests/` — スモークテスト（サーバー、ブラウザ）とテスト用の依存パッケージ（`tests/requirements.txt`）

* `pyproject.toml` — pytest の設定

* `.github/workflows/test.yml` — GitHub Actions でサーバーのテストを自動実行

* `Dockerfile` — Cloud Run 用のコンテナ定義

* `docs/architecture.md` — 設計書

* `README.md` — 本説明ドキュメント

* `LICENSE` — ライセンス（MIT License）

## 📄 ライセンス

本プロジェクトは [MIT License](LICENSE) のもとで公開されています。詳細は [`LICENSE`](LICENSE) ファイルを参照してください。

Copyright (c) 2026 Tomohiko Ariki

## 💡 免責事項

* 本アプリケーションに表示される地震データは、開発時点および公開APIから提供される実績値を基に可視化されています。

* AI防災アシスタントが生成する情報は、専門的な防災知識に基づいていますが、緊急時の最終的な避難判断や安全確保は、政府・地方自治体などの公式の指示・発表に従ってください。
