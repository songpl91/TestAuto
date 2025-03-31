import subprocess
import os
from appium.options.android import UiAutomator2Options
from appium import webdriver
import time

def get_connected_devices():
    """获取所有已连接的设备ID"""
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    devices = []
    for line in result.stdout.split('\n')[1:]:  # 跳过第一行的"List of devices attached"
        if line.strip() and 'device' in line:
            devices.append(line.split()[0])
    return devices

def check_and_uninstall_app(device_id, package_name):
    """检查并卸载已存在的应用"""
    result = subprocess.run(['adb', '-s', device_id, 'shell', 'pm', 'list', 'packages', package_name], 
                          capture_output=True, text=True)
    if package_name in result.stdout:
        print(f"正在从设备 {device_id} 卸载应用 {package_name}")
        subprocess.run(['adb', '-s', device_id, 'uninstall', package_name])

def install_apk(device_id, apk_path):
    """安装APK到指定设备"""
    print(f"正在向设备 {device_id} 安装 {os.path.basename(apk_path)}")
    result = subprocess.run(['adb', '-s', device_id, 'install', apk_path], 
                          capture_output=True, text=True)
    return result.returncode == 0

def measure_app_launch_time(device_id, package_name):
    """测量应用启动时间"""
    # 初始化driver变量
    driver = None
    
    try:
        # 设置Appium capabilities
        desired_caps = {
            'platformName': 'Android',
            'platformVersion': '11',
            'deviceName': device_id,
            'automationName': 'UiAutomator2',
            'appPackage': package_name,
            'appActivity': 'com.unity3d.player.UnityPlayerActivity',
            'noReset': True,
            'newCommandTimeout': 60,
            'autoGrantPermissions': True,
            'uiautomator2ServerInstallTimeout': 60000,
            'adbExecTimeout': 60000,
            'androidDeviceReadyTimeout': 60
        }
        
        # 连接到 Appium 服务器
        driver = webdriver.Remote(
            command_executor='http://127.0.0.1:4723',
            desired_capabilities=desired_caps
        )
        
        # 记录开始时间
        start_time = time.time()
        
        # 启动应用
        driver.activate_app(package_name)
        
        # 等待主界面加载
        driver.implicitly_wait(10)
        
        # 记录结束时间
        end_time = time.time()
        
        # 计算启动时间
        launch_time = end_time - start_time
        print(f"应用启动时间: {launch_time:.2f} 秒")
        
        # 关闭应用
        driver.terminate_app(package_name)
        driver.quit()
        
        return launch_time
        
    except Exception as e:
        print(f"测量启动时间时发生错误: {str(e)}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return None

def main():
    # APK文件路径
    apk_path = r"D:\\UnityProjects\\HexaMatch\\Test_HexaMatch_2025-03-26.apk"
    package_name = "com.kiwifun.game.android.hexacrush.puzzles"

    # 检查APK文件是否存在
    if not os.path.exists(apk_path):
        print(f"错误：找不到APK文件：{apk_path}")
        return

    # 获取已连接的设备
    devices = get_connected_devices()
    if not devices:
        print("错误：没有找到已连接的设备")
        return

    print(f"找到 {len(devices)} 个设备")

    # 对每个设备进行操作
    for device_id in devices:
        print(f"\n处理设备：{device_id}")
        
        # 检查并卸载已存在的应用
        check_and_uninstall_app(device_id, package_name)
        
        # 安装新应用
        if install_apk(device_id, apk_path):
            print(f"设备 {device_id} 安装成功")
            
            # 测量应用启动时间
            print(f"正在测量设备 {device_id} 上的应用启动时间...")
            launch_time = measure_app_launch_time(device_id, package_name)
            if launch_time:
                print(f"设备 {device_id} 的应用启动时间测试完成")
        else:
            print(f"设备 {device_id} 安装失败")

if __name__ == "__main__":
    main()