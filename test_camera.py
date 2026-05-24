#!/usr/bin/env python3
"""
カメラテストプログラム
"""

import cv2
from datetime import datetime
from pathlib import Path

def test_camera():
    """カメラの動作確認"""
    print("カメラテスト開始...")
    
    camera = cv2.VideoCapture(0)
    
    if not camera.isOpened():
        print("✗ カメラが開けませんでした")
        return
    
    print("✓ カメラ接続成功")
    print("Enterキーで撮影、qキーで終了")
    
    save_dir = Path.home() / "Pictures"
    save_dir.mkdir(exist_ok=True)
    
    while True:
        ret, frame = camera.read()
        
        if not ret:
            print("✗ フレーム取得失敗")
            break
        
        # 画面に表示（VSCodeリモートでは表示されない場合があります）
        cv2.imshow('Camera Test', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("終了します")
            break
        elif key == 13:  # Enterキー
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}.jpg"
            filepath = save_dir / filename
            
            cv2.imwrite(str(filepath), frame)
            print(f"✓ 保存: {filepath}")
    
    camera.release()
    cv2.destroyAllWindows()
    print("カメラテスト終了")

if __name__ == "__main__":
    test_camera()