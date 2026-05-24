# -
🚪 インターホン連携顔認証システム  Raspberry Piを使った自動訪問者識別システム。インターホンが押されると自動的にカメラで撮影し、顔認証で家族かどうかを判定。写真と日時を記録するシステムです。  主な機能: - リアルタイム顔認証（face_recognition使用） - GPIO経由でインターホン検知 - 家族/非家族の自動判定- 訪問者履歴の自動保存 - 低コスト（約18,000円）で実装可能  Tech Stack: Python, OpenCV, face_recognition, RPi.GPIO。今後 - Discord/LINE 通知実装予定 
