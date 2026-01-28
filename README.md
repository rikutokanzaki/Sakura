# Sakura - 動的多層型ハニーポットシステム

Sakuraは、SSH/HTTPプロトコルに対応した多層型インタラクティブハニーポットシステムです。攻撃者の行動を段階的に検知し、脅威レベルに応じて適切なハニーポット層へ自動的に振り分けます。

## 概要

Sakuraは以下の3層構造で構成されています：

### 1. Dispatcher

- **Paramiko（SSH）**: SSH接続を受け付け、認証・コマンド実行を監視してハニーポットへルーティング
- **OpenResty（HTTP）**: Luaスクリプトによる動的リクエスト解析により、WordPressスキャンや攻撃パターンを検知して振り分け

### 2. Layers（ハニーポット）

- **Active Layer（能動型）**
  - **Heralding**: SSH/HTTPなど複数プロトコルの認証試行を記録
- **Passive Layer（受動型）**
  - **Cowrie**: SSH MITMハニーポット
  - **Wordpot**: WordPress特化型ハニーポット
  - **H0neytr4p**: Web攻撃全般を記録する

### 3. Launcher

- Docker コンテナの動的起動・停止を管理
- セッション追跡による自動タイムアウト機能
- REST API経由でハニーポットの起動をトリガー

### 4. ELK Stack

- **Elasticsearch**: ログデータの保存・検索
- **Logstash**: 各ハニーポットからのログを正規化・集約
- **Kibana**: ダッシュボードによる可視化

## アーキテクチャ

```
攻撃者
  ↓
┌─────────────────────────────────────┐
│ Dispatcher                          │
│  - Paramiko (SSH:22)                │
│  - OpenResty (HTTP:80)              │
└─────────────────────────────────────┘
  ↓ 攻撃種別判定
┌─────────────────────────────────────┐
│ Launcher (Port :5000)               │
│  - Docker Manegement                │
│  - Session                          │
└─────────────────────────────────────┘
  ↓ コンテナ起動
┌──────────────────────────────────────┐
│ Honeypots                            │
│  Active:  Heralding                  │
│  Passive: Cowrie, Wordpot, H0neytr4p │
└──────────────────────────────────────┘
  ↓ ログ出力
┌──────────────────────────────────────┐
│ ELK Stack                            │
│  - Elasticsearch                     │
│  - Logstash                          │
│  - Kibana                            │
└──────────────────────────────────────┘
```

## 主な特徴

### SSH処理

1. Paramiko Dispatcherで認証情報を記録（Heraldingへ転送）
2. 認証成功後、初期コマンドをインタラクティブシェルで受付
3. 攻撃的なコマンド検知時、CowrieコンテナをLauncher経由で起動
4. セッションをシームレスにCowrieへ移行（コマンド履歴を再生）

### HTTP処理

1. OpenRestyのLuaスクリプトでリクエストを解析
2. WordPressパターン検知 → Wordpot起動
3. 攻撃ツール（sqlmap/nmap等）検知 → H0neytr4p起動
4. 通常アクセス → Heralding

### 動的リソース管理

- 攻撃が検知されない限り、受動型ハニーポットは停止状態
- セッション終了後、5分間（`SESSION_TIMEOUT`）のタイムアウトで自動停止
- リソース効率化と攻撃者へのリアルな動作遅延を再現

## 構成ファイル

### ディレクトリ構造

```
Sakura/
├── install.sh               # インストールスクリプト
├── uninstall.sh             # アンインストール・バックアップスクリプト
├── .env                     # 環境変数設定
├── compose/                 # Docker Composeプロファイル
│     ├── standard.yml       # 全機能有効
│     ├── ssh.yml            # SSHのみ
│     └── http.yml           # HTTPのみ
├── dispatcher/
│     ├── paramiko/          # SSHリバースプロキシ
│     │     ├── Dockerfile
│     │     ├── requirements.txt
│     │     ├── config/
│     │     │     ├── user.txt
│     │     │     └── motd.txt
│     │     └── src/
│     │           ├── main.py
│     │           ├── auth/
│     │           ├── connector/
│     │           ├── session/
│     │           ├── detector/
│     │           ├── reader/
│     │           ├── notifier/
│     │           └── utils/
│     └── openresty/         # HTTPリバースプロキシ
│           ├── Dockerfile
│           ├── nginx.conf
│           ├── conf.d/
│           │     └── http.conf
│           └── lua/
│                 └── detect.lua    # 振り分けロジック
├── launcher/
│     ├── Dockerfile
│     ├── requirements.txt
│     ├── src/
│     │     └── launch.py
│     └── app/
│           ├── routes.py
│           ├── controllers/
│           │     ├── docker_manager.py
│           │     └── session_manager.py
│           ├── utils/
│           │     └── flatten.py
│           ├── static/
│           └── templates/
├── layers/
│     └── core/
│           └── config/
│                 └── userdb.txt    # Cowrie認証
├── elk/
│     ├── logstash/
│     │     └── logstash.conf
│     ├── kibana/
│     │     └── export.ndjson       # kibanaダッシュボード定義
│     └── metricbeat/
│           └── metricbeat.yml
└── data/                           # 各ハニーポットのログ出力先（.gitignore）
      ├── paramiko/
      ├── openresty/
      ├── heralding/
      ├── cowrie/
      ├── wordpot/
      └── h0neytr4p/
```

## インストール

### 前提条件

- Docker & Docker Compose
- sudo権限
- ポート22, 80, 5000が利用可能

### 手順

#### 1. **環境変数設定**

`.env`ファイルを編集：

```bash
SAKURA_DATA_PATH=../data
ARCHIVE_DATA_PATH=/path/to/archive
ALLOWED_NETWORKS=192.168.1.0/24
HOST_NAME=svr01
ELASTIC_PASSWORD=YourPassword
KIBANA_PASSWORD=YourPassword
STACK_VERSION=8.7.1
```

#### 2. **インストール実行**

```bash
./install.sh
```

#### 3. **プロファイル選択**

インストールスクリプトが起動時に以下から選択します：

- `standard.yml`: SSH + HTTP（推奨）
- `ssh.yml`: SSH のみ
- `http.yml`: HTTP のみ

#### 4. **動作確認**

```bash
docker compose -f compose/standard.yml ps
curl http://localhost:5000  # Launcher UI
```

## 使用方法

### Kibanaダッシュボード

```
http://localhost:64297
ユーザー名: elastic
パスワード: (KIBANA_PASSWORD)
```

### Launcher Web UI

```
http://localhost:5000
```

### ハニーポットの手動起動

```bash
curl -X POST http://localhost:5000/trigger/cowrie
curl -X POST http://localhost:5000/trigger/wordpot
curl -X POST http://localhost:5000/trigger/h0neytr4p
```

または、http://localhost:5000でブラウザから起動できます

## アンインストール

```bash
./uninstall.sh
```

アンインストール時、`data/`ディレクトリは自動的にバックアップされます：

```
${ARCHIVE_DATA_PATH}/Sakura/${INSTALL_DATE}-${TODAY}-${TIME}/data/
```

## 設定カスタマイズ

### SSH認証成功条件の変更

[dispatcher/paramiko/config/user.txt](dispatcher/paramiko/config/user.txt) を編集

### WordPressパターンの追加

[dispatcher/openresty/lua/detect.lua](dispatcher/openresty/lua/detect.lua) の `wordpress_patterns` 配列を編集

### セッションタイムアウト時間の変更

[launcher/app/controllers/session_manager.py](launcher/app/controllers/session_manager.py)

```python
SESSION_TIMEOUT = 300  # 秒
```

### Cowrieユーザーアカウントの追加

[layers/core/config/userdb.txt](layers/core/config/userdb.txt) を編集（Cowrie標準形式）

ただし、[dispatcher/paramiko/config/user.txt](dispatcher/paramiko/config/user.txt) に記述したユーザでのログインをここでも許可しておく必要があります。

## 技術詳細

### Paramiko Dispatcher

- Paramiko ServerInterfaceによるSSHサーバー実装
- pty/shellリクエストを処理し、インタラクティブシェル提供
- LineReaderで端末制御シーケンス（ANSI、カーソル移動、履歴）をエミュレート
- Cowrie起動後、既存セッションのコマンド履歴を再生してシームレスに移行

### OpenResty Dispatcher

- Luaスクリプト（`rewrite_by_lua_file`）でリクエスト前処理
- 脅威パターンマッチング後、Launcher APIをHTTP POSTで呼び出し
- `ngx.socket.tcp()`でアップストリームの起動完了をポーリング
- タイムアウト時はHeraldingへフォールバック

### Launcher

- Flask + Gunicornによるマイクロサービス
- Docker Python SDKでコンテナ制御
- `session_manager`がスレッドごとにサービスのタイムアウトを監視
- `docker_manager`がヘルスチェック・ポート開放を待機

### Logstash

- 各ハニーポットの異なるログフォーマットを統一
- CSV（Heralding）、JSON（Cowrie/Wordpot/H0neytr4p）、カスタム（NGINX）を正規化
- `src_ip`, `src_port`, `dest_port`, `username`, `password`, `request_uri` などの共通フィールドへマッピング

## 関連プロジェクト

- **Yozakura**: 静的多層型ハニーポットシステム
- **Spring**: ハニーポットシステム切替運用フレームワーク
- **Tsubomi**: ハニーポット単体運用
- **bloom-insight**: ログ分析・評価システム
