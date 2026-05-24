#!/usr/bin/env python3
"""
インターホン連携顔認証システム
"""

import time
import cv2
import face_recognition
import RPi.GPIO as GPIO
from datetime import datetime
import os
import logging
import requests
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/system.log'),
        logging.StreamHandler()
    ]
)

class IntercomFaceRecognitionSystem:
    def __init__(self):
        # パス設定
        self.base_dir = Path.home() / "intercom_project"
        self.family_dir = self.base_dir / "data" / "family"
        self.visitor_dir = self.base_dir / "logs" / "visitors"
        
        # ディレクトリ作成
        self.visitor_dir.mkdir(parents=True, exist_ok=True)
        
        # GPIO設定
        self.BUTTON_PIN = 17  # インターホン検知用（必要に応じて変更）
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # カメラ初期化
        self.camera = cv2.VideoCapture(0)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 家族の顔データ
        self.known_faces = []
        self.known_names = []
        
        # Discord Webhook URL（後で設定）
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
        
        # 設定
        self.cooldown_time = 10  # 連続押下防止（秒）
        self.last_detection_time = 0
        self.recognition_tolerance = 0.6  # 認識の厳密さ（0.4-0.7）
        
        logging.info("システム初期化完了")
    
    def load_family_faces(self):
        """家族の顔データを読み込み"""
        logging.info("家族の顔データを読み込み中...")
        
        if not self.family_dir.exists():
            logging.warning(f"家族フォルダが存在しません: {self.family_dir}")
            return
        
        image_files = list(self.family_dir.glob("*.jpg")) + \
                     list(self.family_dir.glob("*.png")) + \
                     list(self.family_dir.glob("*.jpeg"))
        
        if not image_files:
            logging.warning("家族の写真が登録されていません")
            return
        
        for image_path in image_files:
            try:
                # 画像を読み込み
                image = face_recognition.load_image_file(str(image_path))
                encodings = face_recognition.face_encodings(image)
                
                if encodings:
                    self.known_faces.append(encodings[0])
                    name = image_path.stem  # ファイル名（拡張子なし）
                    self.known_names.append(name)
                    logging.info(f"✓ 登録成功: {name}")
                else:
                    logging.warning(f"✗ 顔が検出できませんでした: {image_path.name}")
            
            except Exception as e:
                logging.error(f"✗ エラー ({image_path.name}): {e}")
        
        logging.info(f"合計 {len(self.known_names)} 人を登録しました")
    
    def capture_photo(self):
        """写真を撮影（既存の方法を使用）"""
        ret, frame = self.camera.read()
        
        if not ret:
            logging.error("カメラ撮影失敗")
            return None
        
        # 画像を保存（既存の形式を維持）
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}.jpg"
        filepath = self.visitor_dir / filename
        
        cv2.imwrite(str(filepath), frame)
        logging.info(f"写真保存: {filename}")
        
        return frame, filepath
    
    def recognize_face(self, frame):
        """顔認証を実行"""
        # RGB変換
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 顔検出（高速なHOGモデル使用）
        face_locations = face_recognition.face_locations(
            rgb_frame,
            model="hog"  # "cnn"より高速
        )
        
        if not face_locations:
            logging.info("顔が検出されませんでした")
            return False, "顔なし", 0
        
        # 顔のエンコーディング
        face_encodings = face_recognition.face_encodings(
            rgb_frame, 
            face_locations
        )
        
        is_family = False
        recognized_name = "不明な訪問者"
        max_confidence = 0
        
        # 各顔について家族と照合
        for face_encoding in face_encodings:
            if not self.known_faces:
                # 家族が登録されていない場合
                break
            
            # 家族の顔と比較
            matches = face_recognition.compare_faces(
                self.known_faces,
                face_encoding,
                tolerance=self.recognition_tolerance
            )
            
            # 距離を計算（小さいほど似ている）
            face_distances = face_recognition.face_distance(
                self.known_faces,
                face_encoding
            )
            
            if True in matches:
                best_match_index = face_distances.argmin()
                
                if matches[best_match_index]:
                    is_family = True
                    recognized_name = self.known_names[best_match_index]
                    max_confidence = 1 - face_distances[best_match_index]
                    break
        
        return is_family, recognized_name, max_confidence
    
    def send_discord_notification(self, name, confidence, image_path):
        """Discord Webhookで通知"""
        if not self.webhook_url:
            logging.warning("Discord Webhook URLが設定されていません")
            return False
        
        try:
            with open(image_path, 'rb') as f:
                files = {'file': (image_path.name, f)}
                
                content = f"🚪 **訪問者検知**\n"
                content += f"👤 {name}\n"
                content += f"⏰ {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n"
                
                if confidence > 0:
                    content += f"📊 信頼度: {confidence:.2%}"
                
                data = {
                    'content': content,
                    'username': 'インターホン監視システム'
                }
                
                response = requests.post(
                    self.webhook_url,
                    data=data,
                    files=files,
                    timeout=10
                )
                
                if response.status_code in [200, 204]:
                    logging.info("Discord通知送信成功")
                    return True
                else:
                    logging.error(f"Discord通知失敗: {response.status_code}")
                    return False
        
        except Exception as e:
            logging.error(f"Discord通知エラー: {e}")
            return False
    
    def handle_doorbell(self, channel=None):
        """インターホン押下時の処理"""
        current_time = time.time()
        
        # クールダウンチェック（連続押下防止）
        if current_time - self.last_detection_time < self.cooldown_time:
            logging.info("クールダウン中（連続押下防止）")
            return
        
        self.last_detection_time = current_time
        logging.info("=" * 50)
        logging.info("🔔 インターホン検知！")
        
        # 写真撮影
        result = self.capture_photo()
        if result is None:
            logging.error("撮影失敗")
            return
        
        frame, image_path = result
        
        # 顔認証
        is_family, name, confidence = self.recognize_face(frame)
        
        if is_family:
            logging.info(f"✓ 家族を認識: {name} (信頼度: {confidence:.2%})")
            # 家族の場合は通知なし
        else:
            logging.warning(f"⚠ 家族以外を検知: {name}")
            # 通知を送信
            self.send_discord_notification(name, confidence, image_path)
        
        logging.info("=" * 50)
    
    def test_recognition(self):
        """顔認証のテスト（手動実行用）"""
        logging.info("テストモード: 写真を撮影して顔認証を実行します")
        self.handle_doorbell()
    
    def run(self):
        """システム起動"""
        logging.info("インターホン連携顔認証システム起動")
        logging.info(f"家族データフォルダ: {self.family_dir}")
        logging.info(f"訪問者画像保存先: {self.visitor_dir}")
        
        # 家族の顔データを読み込み
        self.load_family_faces()
        
        # GPIO割り込み設定
        GPIO.add_event_detect(
            self.BUTTON_PIN,
            GPIO.RISING,
            callback=self.handle_doorbell,
            bouncetime=300
        )
        
        logging.info("待機中... (Ctrl+Cで終了)")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("\nシステム停止中...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        GPIO.cleanup()
        self.camera.release()
        logging.info("リソース解放完了")

def main():
    """メイン関数"""
    system = IntercomFaceRecognitionSystem()
    
    # テストモードか本番モードか選択
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # テストモード
        system.load_family_faces()
        system.test_recognition()
        system.cleanup()
    else:
        # 本番モード
        system.run()

if __name__ == "__main__":
    main()