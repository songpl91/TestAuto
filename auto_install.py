import subprocess
import os
import glob
import time
import re
import json
import datetime
import platform
import sys

def get_latest_apk(directory):
    """获取指定目录下最新的APK文件"""
    apk_files = glob.glob(os.path.join(directory, '*.apk'))
    if not apk_files:
        return None
    return max(apk_files, key=os.path.getmtime)

def get_platform_version(device_id):
    """获取设备的Android版本"""
    result = subprocess.run(['adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release'], capture_output=True, text=False)
    try:
        # 尝试使用UTF-8解码
        output = result.stdout.decode('utf-8', errors='replace')
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试使用其他编码
        try:
            output = result.stdout.decode('gbk', errors='replace')
        except UnicodeDecodeError:
            # 最后尝试使用latin1（可以解码任何字节序列）
            output = result.stdout.decode('latin1')
    return output.strip()

def get_connected_devices():
    """获取所有已连接的设备ID"""
    try:
        print("正在检查ADB设备连接状态...")
        # 使用text=False避免编码问题，然后手动处理解码
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=False)
        if result.returncode != 0:
            print(f"错误：执行adb devices命令失败：{result.stderr}")
            return []
        
        try:
            # 尝试使用UTF-8解码
            output = result.stdout.decode('utf-8', errors='replace')
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试使用其他编码
            try:
                output = result.stdout.decode('gbk', errors='replace')
            except UnicodeDecodeError:
                # 最后尝试使用latin1（可以解码任何字节序列）
                output = result.stdout.decode('latin1')
        
        devices = []
        for line in output.split('\n')[1:]:  # 跳过第一行的"List of devices attached"
            if line.strip() and 'device' in line:
                devices.append(line.split()[0])
        
        if not devices:
            print("警告：未检测到任何已连接的Android设备")
        else:
            print(f"检测到 {len(devices)} 个设备：{', '.join(devices)}")
        return devices
    except Exception as e:
        print(f"错误：检查设备连接时发生异常：{str(e)}")
        return []

def check_and_uninstall_app(device_id, package_name):
    """检查并卸载已存在的应用"""
    result = subprocess.run(['adb', '-s', device_id, 'shell', 'pm', 'list', 'packages', package_name],
                            capture_output=True, text=True)
    if package_name in result.stdout:
        print(f"正在从设备 {device_id} 卸载应用 {package_name}")
        subprocess.run(['adb', '-s', device_id, 'uninstall', package_name])

def install_apk(device_id, apk_path, package_name, result_dir=None, device_info=None):
    """安装APK到指定设备"""
    print(f"正在向设备 {device_id} 安装 {os.path.basename(apk_path)}")
    
    # 准备安装信息字典
    install_info = {
        'device_id': device_id,
        'package_name': package_name,
        'apk_file': os.path.basename(apk_path),
        'install_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 获取安装前APK文件大小
    try:
        file_size_before = os.path.getsize(apk_path)
        install_info['file_size_before'] = file_size_before
        install_info['file_size_before_formatted'] = format_size(file_size_before)
    except Exception:
        file_size_before = None
    
    # 获取设备信息
    try:
        android_version = get_platform_version(device_id)
        install_info['android_version'] = android_version
    except Exception as e:
        print(f"获取设备信息失败: {e}")
    
    # 启动安装进程，使用基本安装选项
    result = subprocess.run(['adb', '-s', device_id, 'install', '-g', '-r', '-t', apk_path],
                          capture_output=True, text=True)
    
    # 检查安装结果
    if "Success" in result.stdout:
        print("APK安装成功")
        install_info['install_status'] = "成功"
        install_info['install_method'] = "标准安装"
        
        # 获取安装后APK大小（方式2：通过adb shell获取已安装APK大小）
        installed_size = get_apk_size_adb(device_id, package_name)
        if installed_size is not None:
            print(f"APK文件大小（安装后）: {installed_size} 字节 ({format_size(installed_size)})")
            install_info['installed_size'] = installed_size
            install_info['installed_size_formatted'] = format_size(installed_size)
            
            # 对比安装前后大小差异
            if file_size_before is not None:
                size_diff = installed_size - file_size_before
                diff_percentage = (size_diff / file_size_before) * 100
                print(f"安装前后大小差异: {size_diff} 字节 ({format_size(size_diff)}), {diff_percentage:.2f}%")
                install_info['size_diff'] = size_diff
                install_info['size_diff_formatted'] = format_size(size_diff)
                install_info['size_diff_percentage'] = f"{diff_percentage:.2f}%"
        
        # 保存安装信息到JSON
        save_apk_info_to_json(install_info, device_info, result_dir)
        
        return True
    elif "INSTALL_FAILED_ALREADY_EXISTS" in result.stdout:
        print("应用已存在，尝试先卸载再安装...")
        install_info['install_status'] = "失败-应用已存在"
        install_info['error_message'] = "INSTALL_FAILED_ALREADY_EXISTS"
        save_apk_info_to_json(install_info, device_info, result_dir)
        
        subprocess.run(['adb', '-s', device_id, 'uninstall', package_name])
        return install_apk(device_id, apk_path, package_name, result_dir, device_info)
    else:
        error_msg = result.stderr if result.stderr else result.stdout
        print(f"安装失败，错误信息: {error_msg}")
        install_info['install_status'] = "失败"
        install_info['error_message'] = error_msg
        
        # 如果是流式安装失败，尝试使用普通安装方式
        if "Performing Streamed Install" in error_msg:
            print("流式安装失败，尝试使用普通安装方式...")
            install_info['retry_method'] = "普通安装"
            
            result = subprocess.run(['adb', '-s', device_id, 'install', '-r', '-t', apk_path],
                                  capture_output=True, text=True)
            if "Success" in result.stdout:
                print("使用普通安装方式成功")
                install_info['install_status'] = "成功"
                install_info['install_method'] = "普通安装（重试）"
                
                # 获取安装后APK大小
                installed_size = get_apk_size_adb(device_id, package_name)
                if installed_size is not None:
                    print(f"APK文件大小（安装后）: {installed_size} 字节 ({format_size(installed_size)})")
                    install_info['installed_size'] = installed_size
                    install_info['installed_size_formatted'] = format_size(installed_size)
                    
                    # 对比安装前后大小差异
                    if file_size_before is not None:
                        size_diff = installed_size - file_size_before
                        diff_percentage = (size_diff / file_size_before) * 100
                        print(f"安装前后大小差异: {size_diff} 字节 ({format_size(size_diff)}), {diff_percentage:.2f}%")
                        install_info['size_diff'] = size_diff
                        install_info['size_diff_formatted'] = format_size(size_diff)
                        install_info['size_diff_percentage'] = f"{diff_percentage:.2f}%"
                
                # 保存安装信息到JSON
                save_apk_info_to_json(install_info, device_info, result_dir)
                
                return True
        
        # 保存失败信息到JSON
        save_apk_info_to_json(install_info, device_info, result_dir)
        return False

def save_apk_info_to_json(apk_info, device_info=None, result_dir=None):
    """将APK信息保存到JSON文件中"""
    # 如果提供了结果目录，则将文件保存在该目录中
    if result_dir and os.path.isdir(result_dir):
        json_file = os.path.join(result_dir, "apk_info.json")
    else:
        json_file = "apk_info.json"
    
    # 添加时间戳
    apk_info['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 如果有设备信息，添加到APK信息中
    if device_info:
        apk_info['device_info'] = device_info
    
    # 检查文件是否存在，如果存在则读取现有数据
    existing_data = []
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
        except Exception as e:
            print(f"读取现有JSON文件失败: {e}")
            existing_data = []
    
    # 添加新数据
    existing_data.append(apk_info)
    
    # 保存到文件
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
        print(f"APK信息已保存到 {json_file}")
    except Exception as e:
        print(f"保存APK信息到JSON文件失败: {e}")

def get_system_type():
    """获取当前操作系统类型"""
    system = platform.system().lower()
    if 'windows' in system:
        return 'windows'
    elif 'darwin' in system:
        return 'mac'
    elif 'linux' in system:
        return 'linux'
    else:
        return 'unknown'

def get_package_name(apk_path):
    """从APK文件中提取package name和其他信息，并获取APK文件大小"""
    try:
        system_type = get_system_type()
        
        if system_type == 'mac':
            # 在Mac上，aapt可能在Android SDK的build-tools目录下
            # 尝试使用环境变量中的aapt或指定路径的aapt
            try:
                result = subprocess.run(['aapt', 'dump', 'badging', apk_path], 
                                      capture_output=True, text=True)
            except FileNotFoundError:
                # 如果直接调用失败，尝试查找Android SDK路径
                android_home = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
                if android_home:
                    # 查找最新的build-tools版本
                    build_tools_dir = os.path.join(android_home, 'build-tools')
                    if os.path.exists(build_tools_dir):
                        versions = os.listdir(build_tools_dir)
                        if versions:
                            latest_version = sorted(versions)[-1]
                            aapt_path = os.path.join(build_tools_dir, latest_version, 'aapt')
                            if os.path.exists(aapt_path):
                                result = subprocess.run([aapt_path, 'dump', 'badging', apk_path], 
                                                      capture_output=True, text=True)
                            else:
                                print(f"错误：在 {aapt_path} 未找到aapt工具")
                                return None
                        else:
                            print(f"错误：在 {build_tools_dir} 未找到build-tools版本")
                            return None
                    else:
                        print(f"错误：未找到build-tools目录 {build_tools_dir}")
                        return None
                else:
                    print("错误：未设置ANDROID_HOME或ANDROID_SDK_ROOT环境变量")
                    return None
        else:
            # 其他系统直接尝试使用aapt
            result = subprocess.run(['aapt', 'dump', 'badging', apk_path], 
                                  capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"错误：获取APK信息失败：{result.stderr}")
            return None
        
        package_info = {}
        for line in result.stdout.split('\n'):
            if line.startswith('package: name='):
                package_info['name'] = line.split("'")[1]
                package_info['versionCode'] = line.split("versionCode='")[1].split("'")[0]
                package_info['versionName'] = line.split("versionName='")[1].split("'")[0]
            elif line.startswith('application-label:'):
                package_info['label'] = line.split("'")[1]
        
        if not package_info:
            return None
            
        print("APK包信息:")
        print(f"包名: {package_info.get('name', '未知')}")
        print(f"版本号: {package_info.get('versionCode', '未知')}")
        print(f"版本名称: {package_info.get('versionName', '未知')}")
        print(f"应用名称: {package_info.get('label', '未知')}")
        
        # 获取APK文件大小（方式1：直接获取文件大小）
        try:
            file_size_bytes = os.path.getsize(apk_path)
            print(f"APK文件大小（安装前）: {file_size_bytes} 字节 ({format_size(file_size_bytes)})")
            package_info['file_size'] = file_size_bytes
            package_info['file_size_formatted'] = format_size(file_size_bytes)
            package_info['apk_path'] = apk_path
        except Exception as e:
            print(f"获取APK文件大小失败: {e}")
            package_info['file_size'] = None
        
        # APK基本信息已获取完成
        
        return package_info['name']
    except Exception as e:
        print(f"错误：解析APK信息时发生异常：{str(e)}")
        return None

def format_size(size_bytes):
    """将字节大小转换为更易读的格式"""
    if size_bytes < 1024:
        return f"{size_bytes} 字节"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def get_apk_size_adb(device_id, package_name):
    """使用ADB获取已安装APK的大小"""
    try:
        # 1. 获取APK文件路径
        command_path = ['adb', '-s', device_id, 'shell', 'pm', 'path', package_name]
        process_path = subprocess.run(command_path, capture_output=True, text=True, check=True)
        output_path = process_path.stdout.strip()

        # 提取APK文件路径
        match_path = re.search(r"package:(.*\.apk)", output_path)
        if not match_path:
            print(f"错误：无法找到包名 '{package_name}' 对应的APK文件路径。")
            return None
        apk_path = match_path.group(1)

        # 2. 获取文件大小
        command_size = ['adb', '-s', device_id, 'shell', 'ls', '-l', apk_path]
        process_size = subprocess.run(command_size, capture_output=True, text=False, check=True)
        try:
            # 尝试使用UTF-8解码
            output_size = process_size.stdout.decode('utf-8', errors='replace').strip()
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试使用其他编码
            try:
                output_size = process_size.stdout.decode('gbk', errors='replace').strip()
            except UnicodeDecodeError:
                # 最后尝试使用latin1（可以解码任何字节序列）
                output_size = process_size.stdout.decode('latin1').strip()

        # 解析文件大小
        # 添加调试信息
        print(f"ls -l 命令输出: {output_size}")
        # 修改正则表达式以匹配Android设备上ls -l命令的输出格式
        size_match = re.search(r"^\S+\s+\S+\s+\S+\s+\S+\s+(\d+)\s+", output_size)
        if not size_match:
            print(f"错误：无法解析APK文件 '{apk_path}' 的大小。")
            return None
        apk_size_bytes = int(size_match.group(1))
        return apk_size_bytes

    except subprocess.CalledProcessError as e:
        print(f"ADB命令执行出错：{e}")
        print(f"错误输出：{e.stderr}")
        return None
    except Exception as e:
        print(f"发生未知错误：{e}")
        return None

def main():
    import argparse
    import get_device_info
    
    # 根据操作系统类型设置默认APK目录
    system_type = get_system_type()
    if system_type == 'windows':
        default_apk_dir = "D:\\UnityProjects\\HexaMatch"
    elif system_type == 'mac':
        default_apk_dir = os.path.expanduser("/Volumes/MacEx/TestAutoAPK")
    else:  # Linux或其他系统
        default_apk_dir = os.path.expanduser("~/UnityProjects/HexaMatch")
    
    parser = argparse.ArgumentParser(description='APK自动安装工具')
    parser.add_argument('--apk-dir', default=default_apk_dir, help=f'APK文件目录，默认为{default_apk_dir}')
    parser.add_argument('--analyze', '-a', action='store_true', help='安装后是否进行性能分析')
    parser.add_argument('--duration', '-d', type=int, default=60, help='性能测试持续时间（秒），默认60秒')
    parser.add_argument('--interval', '-i', type=int, default=5, help='数据收集间隔（秒），默认5秒')
    args = parser.parse_args()
    
    print("开始执行自动安装脚本...")
    # 指定APK文件目录
    apk_directory = args.apk_dir

    print(f"正在检查目录: {apk_directory}")
    # 获取最新的APK文件
    apk_path = get_latest_apk(apk_directory)
    if not apk_path:
        print(f"错误：在目录 {apk_directory} 中未找到APK文件")
        return
    
    # 验证APK文件是否存在且可访问
    if not os.path.exists(apk_path):
        print(f"错误：APK文件不存在或无法访问：{apk_path}")
        return
    
    print(f"找到最新的APK文件：{os.path.basename(apk_path)}")

    # 自动获取package name
    package_name = get_package_name(apk_path)
    if not package_name:
        print("错误：无法从APK文件中获取包名")
        return
    print(f"自动获取的包名: {package_name}")

    # 获取已连接的设备
    devices = get_connected_devices()
    if not devices:
        print("错误：没有找到已连接的设备")
        return

    print(f"找到 {len(devices)} 个设备")

    # 对每个设备进行操作
    for device_id in devices:
        print(f"\n处理设备：{device_id}")
        
        # 获取设备信息
        print(f"正在获取设备 {device_id} 的信息...")
        device_info = get_device_info.get_device_info(device_id)
        if not device_info:
            print(f"错误：无法获取设备 {device_id} 的信息")
            continue
        
        # 创建以设备型号+当前时间命名的文件夹
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        device_model = device_info['model']['full_name'].replace(' ', '_')
        result_dir = f"{device_model}_{timestamp}"
        os.makedirs(result_dir, exist_ok=True)
        print(f"创建结果目录: {result_dir}")
        
        # 保存设备信息到新文件夹
        device_info_file = os.path.join(result_dir, f"device_info_{device_model}.json")
        with open(device_info_file, 'w', encoding='utf-8') as f:
            json.dump(device_info, f, indent=2, ensure_ascii=False)
        print(f"设备信息已保存到: {device_info_file}")

        # 检查并卸载已存在的应用
        check_and_uninstall_app(device_id, package_name)

        # 安装新应用
        if install_apk(device_id, apk_path, package_name, result_dir, device_info):
            print(f"设备 {device_id} 安装成功")
            
            # 如果指定了性能分析，则进行性能分析
            if args.analyze:
                print(f"开始对设备 {device_id} 上的应用 {package_name} 进行性能分析...")
                try:
                    # 创建截图文件夹
                    screenshot_dir = os.path.join(result_dir, "screen_shot")
                    os.makedirs(screenshot_dir, exist_ok=True)
                    print(f"截图将保存在: {screenshot_dir}")
        
                    
                    # 导入性能分析模块
                    import performance_analysis
                    
                    # 检查应用是否已安装
                    if not performance_analysis.is_app_installed(device_id, package_name):
                        print(f"错误：应用 {package_name} 未在设备 {device_id} 上安装")
                        continue
                    
                    # 启动应用
                    if not performance_analysis.launch_app(device_id, package_name):
                        print(f"错误：无法在设备 {device_id} 上启动应用 {package_name}")
                        continue

                    import threading
                    import queue
                    
                    # 创建一个事件来控制截图线程
                    screenshot_stop_event = threading.Event()
                    
                    # 定义截图线程函数
                    def screenshot_thread(device_id, screenshot_dir, stop_event):
                        start_time = time.time()
                        print("开始定时截图...")
                        while not stop_event.is_set():
                            current_time = time.time()
                            if current_time - start_time > 10:  # 10秒超时控制
                                print("截图时间已达到10秒，自动停止")
                                break
                            timestamp = int((current_time - start_time) * 1000)  # 毫秒时间戳
                            screenshot_file = os.path.join(screenshot_dir, f"{timestamp}.png")
                            subprocess.run(['adb', '-s', device_id, 'shell', 'screencap', '-p', '/sdcard/screenshot.png'])
                            subprocess.run(['adb', '-s', device_id, 'pull', '/sdcard/screenshot.png', screenshot_file])
                            time.sleep(0.05)  # 50ms间隔
                        print("截图完成")
                    
                    # 启动截图线程
                    screenshot_thread = threading.Thread(
                        target=screenshot_thread,
                        args=(device_id, screenshot_dir, screenshot_stop_event)
                    )
                    screenshot_thread.daemon = True
                    screenshot_thread.start()
                    
                    # 等待应用完全启动
                    print("等待应用完全启动...")
                    time.sleep(3)
                    
                    # 收集性能数据
                    csv_file = performance_analysis.collect_performance_data(device_id, package_name, args.duration, args.interval, result_dir)
                    
                    # 停止截图线程
                    screenshot_stop_event.set()
                    screenshot_thread.join()
                    
                    # 生成性能报告
                    report_file = performance_analysis.generate_performance_report(csv_file)
                    
                    print(f"设备 {device_id} 的性能分析完成，报告保存在 {report_file}")
                except Exception as e:
                    print(f"性能分析过程中发生错误：{str(e)}")
        else:
            print(f"设备 {device_id} 安装失败")

if __name__ == "__main__":
    main()