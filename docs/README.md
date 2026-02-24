# FOMUS Archive — 運用手順書

## ファイル構成

```
output/
├── index.html      ← メインHTML（CSS・JS含む、単一ファイル）
├── articles.js     ← 記事データ（90記事）
├── netlify.toml    ← Netlifyデプロイ設定
├── README.md       ← この手順書
└── images/         ← 画像ファイル群（214枚）
    ├── 1 自己紹介と目的/
    ├── 2 前日準備/
    └── ...
```

---

## 手順1：パスワードを変更する方法

`index.html` をテキストエディタで開き、以下の行を見つけてください（`<script>` タグ内の先頭付近）：

```javascript
const PASSWORD = 'fomus2024'; // ← パスワードを変更するにはここを変える
```

`fomus2024` の部分を好きなパスワードに書き換えて保存するだけでOKです。

**例：** パスワードを `fomus2025secret` に変更する場合：
```javascript
const PASSWORD = 'fomus2025secret';
```

変更後、Netlifyに再デプロイしてください。

**注意：** パスワード認証はフロントエンド（JavaScript）で行っているため、セキュリティ的には簡易的なものです。高度なセキュリティが必要な場合は、Netlify の認証機能やサーバーサイド認証の導入を検討してください。

---

## 手順2：新しい記事を追加する方法

### 方法A：手動で追加

1. Notionで新しい記事をMarkdownエクスポート
2. エクスポートした `.md` ファイルの内容を読む
3. `articles.js` を開き、配列の最後に新しい記事オブジェクトを追加：

```javascript
{
  "id": 91,
  "num": "091",
  "title": "新しい記事タイトル",
  "category": "cebu",
  "excerpt": "本文の最初の100文字...",
  "body": "<p>本文のHTMLをここに</p>"
}
```

4. 画像がある場合は `images/` フォルダに新しいサブフォルダを作成してコピー
5. Netlifyに再デプロイ

### 方法B：スクリプトで一括更新

プロジェクトルートにある `build_articles.py` を使います：

1. 新しい記事のエクスポートフォルダを `セブ島/まっすー セブ島 活動記/` 内に配置
2. ターミナルで以下を実行：

```bash
cd /Users/masuo/Downloads/海外活動記録の全て
python3 build_articles.py
```

3. `output/articles.js` が自動で再生成されます（既存記事も含む）
4. 画像も再コピーする場合は以下を実行：

```bash
# 新しい記事フォルダの画像をコピー
cp -r "セブ島/まっすー セブ島 活動記/91 新記事タイトル/" "output/images/91 新記事タイトル/"
```

5. Netlifyに再デプロイ

---

## デプロイ手順（Netlify）

### 方法A：ドラッグ＆ドロップ（最も簡単）

1. ブラウザで [https://app.netlify.com](https://app.netlify.com) にアクセス
2. アカウントを作成またはログイン
3. 「Sites」ページの下部にある **ドロップゾーン**（「Drag and drop your site output folder here」）に `output/` フォルダをドラッグ＆ドロップ
4. 数秒でデプロイ完了。自動生成されたURLが表示されます

**再デプロイ：** サイトの「Deploys」タブを開き、同じドロップゾーンに更新した `output/` フォルダをドロップするだけ。

### 方法B：Netlify CLI

```bash
# Netlify CLIのインストール（初回のみ）
npm install -g netlify-cli

# ログイン（初回のみ）
netlify login

# 初回デプロイ（サイト作成）
cd /Users/masuo/Downloads/海外活動記録の全て/output
netlify deploy --prod --dir=.

# 2回目以降の更新
cd /Users/masuo/Downloads/海外活動記録の全て/output
netlify deploy --prod --dir=.
```

### 独自ドメインの設定

1. Netlifyのサイトダッシュボードで **「Domain settings」** をクリック
2. **「Add custom domain」** をクリック
3. ドメイン名を入力（例：`archive.fomus.jp`）
4. DNSの設定：
   - お使いのドメインレジストラ（お名前.com、ムームードメイン等）のDNS管理画面を開く
   - **CNAMEレコード** を追加：
     - ホスト名: `archive`（サブドメインの場合）
     - 値: `あなたのサイト名.netlify.app`
   - **Aレコード**（ルートドメインの場合）:
     - 値: `75.2.60.5`（Netlifyのロードバランサー）
5. Netlifyに戻り、**「Verify DNS configuration」** をクリック
6. HTTPS証明書は自動で発行されます（Let's Encrypt）

**想定URL例：**
- `fomus-archive.netlify.app`（無料、すぐ使える）
- `archive.fomus.jp`（独自ドメイン、DNS設定が必要）

---

## トラブルシューティング

**画像が表示されない場合：**
- `images/` フォルダが `index.html` と同じ階層にあるか確認
- ファイル名に日本語が含まれるため、URLエンコードが正しいか確認

**パスワードを忘れた場合：**
- `index.html` を開いて `const PASSWORD =` の行を確認

**ローカルで動作確認する場合：**
```bash
cd output/
python3 -m http.server 8080
# ブラウザで http://localhost:8080 を開く
```
