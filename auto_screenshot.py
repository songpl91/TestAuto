import os
import time
import subprocess
from datetime import datetime

def take_screenshots(output_dir, interval_ms=10, duration_sec=5):
    """
    自动截图功能
    :param output_dir: 截图保存目录
    :param interval_ms: 截图间隔(毫秒)
    :param duration_sec: 总持续时间(秒)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    start_time = time.time()
    end_time = start_time + duration_sec
    
    print(f"开始截图，将持续{duration_sec}秒，间隔{interval_ms}毫秒...")
    
    while time.time() < end_time:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        screenshot_path = os.path.join(output_dir, f"screenshot_{timestamp}.png")
        
        # 执行adb截图命令
        subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screenshot.png"])
        subprocess.run(["adb", "pull", "/sdcard/screenshot.png", screenshot_path])
        
        print(f"已保存截图: {screenshot_path}")
        time.sleep(interval_ms / 1000)
    
    print("截图完成")

if __name__ == "__main__":
    # 示例用法
    output_folder = "d:\\UnityProjects\\TestAuto\\samsung_SM-G9910_20250328_174910\\screenshots"
    take_screenshots(output_folder)