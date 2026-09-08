# インターホン連携顔認証システム

Raspberry Pi とカメラを使い、インターホンが押されたタイミングで訪問者の顔を撮影・認証し、**家族以外の来訪者のみ Discord に通知**する監視システムです。

## 特徴

- インターホン(GPIO入力)検知をトリガーに自動で写真を撮影
- 事前登録した家族の顔は認証してスルー（誤通知を防止）
- 家族以外の来訪者を検知した場合のみ Discord Webhook で画像付き通知
- 連続押下防止のクールダウン機能
- 動作ログをファイル・コンソール両方に出力
- GPIOなしでも実行できるテストモードを搭載

## 動作環境

- Raspberry Pi（GPIO・カメラモジュール利用のため）
- Python 3.8 以上
- USBカメラ または Raspberry Pi カメラモジュール

## 必要なライブラリ

```bash
pip install opencv-python face_recognition RPi.GPIO requests
```

> `face_recognition` は内部で `dlib` を利用しているため、Raspberry Pi 環境では別途ビルド依存パッケージ（`cmake`, `build-essential` など）が必要になる場合があります。

## セットアップ

### 1. ディレクトリ構成

初回実行時に以下のディレクトリが自動作成されます。

```
~/intercom_project/
├── data/
│   └── family/      # 家族の顔写真を配置する場所
└── logs/
    ├── system.log   # 実行ログ
    └── visitors/    # 来訪者の撮影画像
```

### 2. 家族の顔を登録

`~/intercom_project/data/family/` に家族一人につき1枚、顔がはっきり写った画像（jpg / jpeg / png）を配置してください。**ファイル名がそのまま認識時の表示名になります**（例: `taro.jpg` → 「taro」として認識）。

### 3. Discord Webhook の設定

Discordのチャンネル設定からWebhook URLを発行し、環境変数に設定します。

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/xxxx/xxxx"
```

### 4. GPIO配線

デフォルトでは GPIO17（プルダウン、立ち上がりエッジ検知）をインターホン検知の入力ピンとして使用しています。配線環境に応じて `BUTTON_PIN` の値をコードから変更してください。

## 使い方

### 本番モード（常駐監視）

```bash
python3 intercom_face_recognition.py
```

インターホンのボタン押下（GPIO入力）を検知するたびに、撮影 → 顔認証 → 家族以外なら通知、という処理を自動で行います。`Ctrl+C` で終了します。

### テストモード（手動で1回実行）

GPIOトリガーを使わず、コマンド実行のタイミングで即座に撮影・認証を行いたい場合に利用します。

```bash
python3 intercom_face_recognition.py test
```

## 主要な設定項目

`IntercomFaceRecognitionSystem.__init__` 内で調整できます。

| 項目 | 説明 | デフォルト |
|---|---|---|
| `BUTTON_PIN` | インターホン検知用GPIOピン番号 | `17` |
| `cooldown_time` | 連続検知を防ぐクールダウン秒数 | `10` |
| `recognition_tolerance` | 顔認証の厳密さ（`0.4`〜`0.7`、小さいほど厳密） | `0.6` |
| カメラ解像度 | `CAP_PROP_FRAME_WIDTH` / `HEIGHT` | `640×480` |

## 処理フロー

1. インターホンのGPIO立ち上がりエッジを検知
2. クールダウン中でなければカメラで撮影し、来訪者画像として保存
3. 撮影画像から顔を検出し、登録済みの家族の顔データと照合
4. 家族と判定された場合はログのみでスルー
5. 家族以外（または未登録の顔）と判定された場合、画像とタイムスタンプ・信頼度を添えて Discord に通知

## ログ

すべての動作は `~/intercom_project/logs/system.log` に記録され、同時に標準出力にも表示されます。

## 注意事項・既知の制限

- 家族の顔写真は1人1枚のみ登録される仕様です（同一人物の複数枚登録には未対応）。
- `face_recognition`（dlib）はRaspberry Pi上でのビルドに時間がかかることがあります。
- 顔検出には高速な HOG モデルを使用しているため、CNNモデルに比べて認識精度はやや劣ります。
- 本システラムはあくまで簡易的な家庭用途を想定しており、セキュリティ用途としての堅牢性は保証されません。

