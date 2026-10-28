# 2026年〜 国内震度5以上 地震プロットマップ (AI防災アシスタント搭載)

本プロジェクトは、2026年以降に日本国内で発生した最大震度5弱以上の地震データを、インタラクティブな日本地図上にビジュアルマッピングした高機能Webアプリケーションです。

「漏れなく、ダブりなく」データを可視化する独自の重複回避表示システムや、**Gemini 2.5 Flash API**を活用した高度なAI防災トレンド分析、リアルタイムのAPI自動同期（1日2回）機能を1つのHTMLファイルに凝縮しています。

## 💥 主な機能

### 1. インタラクティブな日本地図プロット

*   **直感的なスケール設計**: マグニチュード（M）の大きさを円の半径で、最大震度の強さを5色のカラー（5弱:黄 / 5強:オレンジ / 6弱:赤 / 6強:濃赤 / 7:紫）で直感的に表現しています。
    
*   **シームレスなUI連動**: 左側のタイムラインリストと地図上のプロットがホバー・クリックで相互にハイライト＆ズーム連動します。
    

### 2. 重複震源地の自動分散表示（オフセット配置）

*   島根県東部、長野県北部、茨城県南部など、**全く同じ緯度経度で複数回発生した地震**の重なりを防ぐため、元の震央から15km相当の半径の円周上に自動で放射状に分散配置し、本来の位置と点線で繋ぐロジックを実装しています。
    

### 3. 動的衝突回避ラベル（常時表示機能）

*   画面右上のスイッチをONにすることで、プロットの横に日本語ラベル（発生日、震源地、M、最大震度）を常時表示できます。
    
*   オフセット方向（分散角度）に合わせてラベルの展開方向（上下左右）を自動で切り替えるため、**ラベル同士が重複して見えなくなるのを防ぎます**。
    

### 4. Gemini 2.5 Flash 連携「AI防災アシスタント」

*   **✨ 総合活動レポート**: 蓄積された地震データを分析し、日本列島規模でのひずみ解放のトレンドと実践的な防災アクションプランをAIが一発でレポートします。
    
*   **✨ 個別震源詳細分析**: リストの「✨ AI詳細分析」をクリックすると、その震央周辺の地質学的・プレート境界学的背景、想定されるインフラ被害、今後の警戒余震について、個別最適化された専門知識をGeminiが提示します。
    
*   **✨ 防災チャット**: 日常生活の備え、家具固定、家族の連絡方法など、防災に関する疑問にAIがいつでもお答えします。
    

### 5. 1日2回の自動API同期（12時間カウントダウン）

*   気象協会などの情報を反映する「P2P地震情報 API」とバックグラウンドで自動同期。
    
*   更新頻度は「1日2回（12時間に1回）」に最適化されており、左上のインジケーターで「時:分:秒」単位のカウントダウンを行います。
    
*   初期起動時には必ず最新情報をフェッチしてマージ・重複排除するため、常に最新状態から始まります。
    
*   **【未来対応】**: データの取得条件を「2026年以降（>=2026）」としているため、2027年以降に発生する未来の地震についても、プログラムを書き換えることなく完全に自動取得・プロット・AI分析が対応可能です。
    

## 🛠️ 使用テクノロジー

*   **Frontend**: HTML5 / CSS3 / ES6+ JavaScript
    
*   **Styling**: Tailwind CSS (CDNによるレスポンシブデザイン)
    
*   **Map Utility**: Leaflet.js (国土地理院 地理院タイル「淡色地図」をCSSフィルタでダーク化)
    
*   **Generative AI**: Gemini 2.5 Flash API (`generativelanguage.googleapis.com`)
    
*   **Data Source API**: P2P地震情報 API
    

## 🚀 実行方法（ローカル起動手順）

本プロジェクトは **シングルファイル（One-File Mandate）** で構築されているため、特別なサーバー環境（Node.jsなど）を構築することなく、誰でも即座に起動できます。

1.  プロジェクト内の `earthquake_map_2026.html` をお使いのパソコンに保存します。
    
2.  保存した HTML ファイルをダブルクリック、または Google Chrome などのWebブラウザにドラッグ＆ドロップします。
    
3.  インターネットに繋がっている環境であれば、地図タイルやAPI自動同期、AI機能がすべてロードされ、すぐに動作します。
    

## 🔑 Gemini APIキーの設定について（AI機能を利用する場合）

※ローカル環境で本格的にGemini APIを利用する場合、ファイル内のスクリプトの一部をご自身のAPIキーに置き換えてください。

`earthquake_map.html` の772行目付近（`callGeminiAPI` 関数内）にある以下の記述を書き換えます。

```
// 変更前
async function callGeminiAPI(userQuery) {
    const apiKey = ""; 
    ...
}

// 変更後（ご自身のGemini APIキーを記述）
async function callGeminiAPI(userQuery) {
    const apiKey = "AIzaSyYourOwnActualGeminiApiKeyHere..."; 
    ...
}

```

## 📁 ファイル構成

*   `earthquake_map.html` — アプリケーション本体（全ソースコード統合）
    
*   `README.md` — 本説明ドキュメント
    

## 📄 ライセンス

本プロジェクトは MIT License のもとで公開されています。

Copyright (c) 2026 Tomohiko Ariki

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 💡 免責事項

*   本アプリケーションに表示される地震データは、開発時点および公開APIから提供される実績値を基に可視化されています。
    
*   AI防災アシスタントが生成する情報は、専門的な防災知識に基づいていますが、緊急時の最終的な避難判断や安全確保は、政府・地方自治体などの公式の指示・発表に従ってください。