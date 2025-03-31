import subprocess
import os
import time
import re
import csv
import datetime
import argparse
from pathlib import Path

def run_adb_command(command, device_id=None):
    """执行adb命令并返回结果"""
    cmd = ['adb']
    if device_id:
        cmd.extend(['-s', device_id])
    
    # 处理管道命令
    if '|' in command:
        # 对于包含管道的命令，需要使用shell=True
        full_cmd = ' '.join(cmd) + ' ' + command
        try:
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"执行命令失败: {full_cmd}")
                return ""
            return result.stdout.strip()
        except Exception as e:
            print(f"执行命令失败: {full_cmd}")
            print(f"错误信息: {str(e)}")
            return ""
    else:
        # 对于不包含管道的普通命令
        cmd.extend(command.split())
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"执行命令失败: {' '.join(cmd)}")
                return ""
            return result.stdout.strip()
        except Exception as e:
            print(f"执行命令失败: {' '.join(cmd)}")
            print(f"错误信息: {str(e)}")
            return ""

def get_connected_devices():
    """获取所有已连接的设备ID"""
    try:
        print("正在检查ADB设备连接状态...")
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"错误：执行adb devices命令失败：{result.stderr}")
            return []
        
        devices = []
        for line in result.stdout.split('\n')[1:]:  # 跳过第一行的"List of devices attached"
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

def is_app_installed(device_id, package_name):
    """检查应用是否已安装"""
    result = subprocess.run(['adb', '-s', device_id, 'shell', 'pm', 'list', 'packages', package_name],
                            capture_output=True, text=True)
    return package_name in result.stdout

def launch_app(device_id, package_name):
    """启动应用"""
    print(f"正在启动应用 {package_name} 在设备 {device_id} 上...")
    # 获取应用的主Activity
    result = subprocess.run(
        ['adb', '-s', device_id, 'shell', 'cmd', 'package', 'resolve-activity', '--brief', package_name],
        capture_output=True, text=True
    )
    
    activity_line = result.stdout.strip()
    if not activity_line or "No activity found" in activity_line:
        print(f"错误：无法找到应用 {package_name} 的主Activity")
        # 尝试使用monkey启动应用
        print("尝试使用monkey启动应用...")
        subprocess.run(['adb', '-s', device_id, 'shell', 'monkey', '-p', package_name, '-c', 'android.intent.category.LAUNCHER', '1'],
                      capture_output=True)
        return True
    
    # 解析主Activity
    activity = activity_line.split('/')[-1]
    if activity.startswith('.'):
        activity = package_name + activity
    
    # 启动应用
    launch_result = subprocess.run(
        ['adb', '-s', device_id, 'shell', 'am', 'start', '-n', f"{package_name}/{activity}"],
        capture_output=True, text=True
    )
    
    if "Error" in launch_result.stdout or "Error" in launch_result.stderr:
        print(f"错误：启动应用失败：{launch_result.stderr if launch_result.stderr else launch_result.stdout}")
        return False
    
    print("应用启动成功")
    return True

def get_memory_info(device_id, package_name):
    """获取应用内存使用情况"""
    result = subprocess.run(
        ['adb', '-s', device_id, 'shell', 'dumpsys', 'meminfo', package_name],
        capture_output=True, text=True
    )
    
    output = result.stdout
    
    # 解析内存信息
    memory_data = {}
    
    # 提取总内存使用量
    total_match = re.search(r'TOTAL\s+([\d,]+)', output)
    if total_match:
        memory_data['total'] = int(total_match.group(1).replace(',', ''))
    
    # 提取Java堆内存
    java_heap_match = re.search(r'Java Heap:\s+([\d,]+)', output)
    if java_heap_match:
        memory_data['java_heap'] = int(java_heap_match.group(1).replace(',', ''))
    
    # 提取原生堆内存
    native_heap_match = re.search(r'Native Heap:\s+([\d,]+)', output)
    if native_heap_match:
        memory_data['native_heap'] = int(native_heap_match.group(1).replace(',', ''))
    
    # 提取PSS总和
    pss_total_match = re.search(r'TOTAL PSS:\s+([\d,]+)', output)
    if pss_total_match:
        memory_data['pss_total'] = int(pss_total_match.group(1).replace(',', ''))
    
    return memory_data

def save_detailed_memory_info(device_id, package_name, timestamp, results_dir):
    """获取并保存应用的详细内存信息"""
    # 执行adb shell dumpsys meminfo命令获取完整内存信息
    result = subprocess.run(
        ['adb', '-s', device_id, 'shell', 'dumpsys', 'meminfo', package_name],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"错误：获取应用 {package_name} 的详细内存信息失败")
        return
    
    # 确保结果目录存在
    if not os.path.exists(results_dir):
        print(f"创建详细内存信息目录: {results_dir}")
        os.makedirs(results_dir, exist_ok=True)
    
    # 创建详细内存信息文件
    meminfo_file = results_dir / f"{device_id}_{package_name}_meminfo_{timestamp.replace(':', '-').replace(' ', '_')}.txt"
    
    # 写入详细内存信息
    with open(meminfo_file, 'w', encoding='utf-8') as f:
        f.write(f"===== 应用 {package_name} 在设备 {device_id} 上的详细内存信息 =====\n")
        f.write(f"采集时间: {timestamp}\n\n")
        f.write(result.stdout)
    
    print(f"详细内存信息已保存到 {meminfo_file}")
    return str(meminfo_file)

def get_cpu_info(device_id, package_name):
    """获取应用CPU使用情况"""
    result = subprocess.run(
        ['adb', '-s', device_id, 'shell', 'dumpsys', 'cpuinfo', '|', 'grep', package_name],
        capture_output=True, text=True, shell=True
    )
    
    output = result.stdout
    
    # 解析CPU信息
    cpu_data = {}
    
    # 提取CPU使用百分比
    cpu_match = re.search(r'(\d+(?:\.\d+)?)%', output)
    if cpu_match:
        cpu_data['cpu_percentage'] = float(cpu_match.group(1))
    else:
        cpu_data['cpu_percentage'] = 0.0
    
    return cpu_data

def get_fps_info(device_id, package_name):
    """获取应用FPS信息"""
    # 清除之前的图形信息
    subprocess.run(
        ['adb', '-s', device_id, 'shell', 'dumpsys', 'gfxinfo', package_name, 'reset'],
        capture_output=True
    )
    
    # 等待一段时间收集数据
    time.sleep(1)
    
    # 获取图形信息
    result = subprocess.run(
        ['adb', '-s', device_id, 'shell', 'dumpsys', 'gfxinfo', package_name],
        capture_output=True, text=True
    )
    
    output = result.stdout
    
    # 解析FPS信息
    fps_data = {}
    
    # 提取总帧数和慢帧数
    total_frames_match = re.search(r'Total frames rendered: (\d+)', output)
    janky_frames_match = re.search(r'Janky frames: (\d+) \((\d+\.\d+)%\)', output)
    
    if total_frames_match:
        fps_data['total_frames'] = int(total_frames_match.group(1))
    else:
        fps_data['total_frames'] = 0
    
    if janky_frames_match:
        fps_data['janky_frames'] = int(janky_frames_match.group(1))
        fps_data['janky_percent'] = float(janky_frames_match.group(2))
    else:
        fps_data['janky_frames'] = 0
        fps_data['janky_percent'] = 0.0
    
    return fps_data

def get_battery_info(device_id):
    """获取电池信息"""
    result = subprocess.run(
        ['adb', '-s', device_id, 'shell', 'dumpsys', 'battery'],
        capture_output=True, text=True
    )
    
    output = result.stdout
    
    # 解析电池信息
    battery_data = {}
    
    # 提取电池电量
    level_match = re.search(r'level: (\d+)', output)
    if level_match:
        battery_data['level'] = int(level_match.group(1))
    
    # 提取电池温度
    temperature_match = re.search(r'temperature: (\d+)', output)
    if temperature_match:
        # 电池温度通常以0.1°C为单位
        battery_data['temperature'] = float(temperature_match.group(1)) / 10.0
    
    return battery_data

def collect_performance_data(device_id, package_name, duration, interval=5, result_dir=None):
    """收集性能数据"""
    print(f"开始收集应用 {package_name} 在设备 {device_id} 上的性能数据，持续 {duration} 秒，间隔 {interval} 秒")
    
    # 使用指定的结果目录或创建新的目录
    if result_dir and os.path.isdir(result_dir):
        results_dir = Path(result_dir)
    else:
        # 使用设备型号和时间戳创建更有意义的目录名
        device_model = run_adb_command('shell getprop ro.product.model', device_id).replace(' ', '_')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        results_dir = Path(f"{device_model}_{timestamp}")
        results_dir.mkdir(exist_ok=True)
        print(f"创建结果目录: {results_dir}")
    
    # 创建CSV文件
    csv_file = results_dir / f"{device_id}_{package_name}_performance.csv"
    
    # 创建详细内存信息目录
    meminfo_dir = results_dir / "meminfo_details"
    if not os.path.exists(meminfo_dir):
        print(f"创建详细内存信息目录: {meminfo_dir}")
        os.makedirs(meminfo_dir, exist_ok=True)
    
    with open(csv_file, 'w', newline='') as f:
        fieldnames = ['timestamp', 'memory_total', 'memory_java_heap', 'memory_native_heap', 'memory_pss_total', 
                     'cpu_percentage', 'total_frames', 'janky_frames', 'janky_percent', 'battery_level', 'battery_temperature']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        start_time = time.time()
        end_time = start_time + duration
        
        while time.time() < end_time:
            current_time = time.time()
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 收集各项性能数据
            memory_data = get_memory_info(device_id, package_name)
            cpu_data = get_cpu_info(device_id, package_name)
            fps_data = get_fps_info(device_id, package_name)
            battery_data = get_battery_info(device_id)
            
            # 保存详细内存信息
            try:
                save_detailed_memory_info(device_id, package_name, timestamp, meminfo_dir)
            except Exception as e:
                print(f"保存详细内存信息时出错: {str(e)}")
                # 确保目录存在
                os.makedirs(meminfo_dir, exist_ok=True)
                # 重试一次
                save_detailed_memory_info(device_id, package_name, timestamp, meminfo_dir)
            
            # 写入CSV
            row_data = {
                'timestamp': timestamp,
                'memory_total': memory_data.get('total', 0),
                'memory_java_heap': memory_data.get('java_heap', 0),
                'memory_native_heap': memory_data.get('native_heap', 0),
                'memory_pss_total': memory_data.get('pss_total', 0),
                'cpu_percentage': cpu_data.get('cpu_percentage', 0),
                'total_frames': fps_data.get('total_frames', 0),
                'janky_frames': fps_data.get('janky_frames', 0),
                'janky_percent': fps_data.get('janky_percent', 0),
                'battery_level': battery_data.get('level', 0),
                'battery_temperature': battery_data.get('temperature', 0)
            }
            
            writer.writerow(row_data)
            f.flush()  # 确保数据立即写入文件
            
            # 打印当前状态
            print(f"[{timestamp}] 内存: {memory_data.get('total', 0)/1024:.2f} MB, "
                  f"CPU: {cpu_data.get('cpu_percentage', 0):.1f}%, "
                  f"卡顿帧: {fps_data.get('janky_percent', 0):.1f}%, "
                  f"电池: {battery_data.get('level', 0)}%, "
                  f"温度: {battery_data.get('temperature', 0):.1f}°C")
            
            # 计算下一次收集时间
            next_time = current_time + interval
            sleep_time = max(0, next_time - time.time())
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    print(f"性能数据收集完成，结果保存在 {csv_file}")
    print(f"详细内存信息保存在 {meminfo_dir} 目录下")
    return str(csv_file)

def generate_performance_report(csv_file):
    """生成性能报告"""
    if not os.path.exists(csv_file):
        print(f"错误：找不到CSV文件 {csv_file}")
        return
    
    print(f"正在生成性能报告，基于 {csv_file}...")
    
    # 读取CSV数据
    data = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    
    if not data:
        print("错误：CSV文件中没有数据")
        return
    
    # 计算统计数据
    memory_values = [float(row['memory_total']) for row in data]
    cpu_values = [float(row['cpu_percentage']) for row in data]
    janky_values = [float(row['janky_percent']) for row in data]
    battery_temp_values = [float(row['battery_temperature']) for row in data]
    
    # 创建报告文件
    report_file = os.path.splitext(csv_file)[0] + "_report.txt"
    
    # 获取详细内存信息目录路径
    csv_path = Path(csv_file)
    meminfo_dir = csv_path.parent / "meminfo_details"
    
    with open(report_file, 'w', encoding='utf-8-sig') as f:
        f.write("===== 应用性能分析报告 =====\n\n")
        f.write(f"分析时间: {data[0]['timestamp']} 至 {data[-1]['timestamp']}\n")
        f.write(f"样本数量: {len(data)}\n\n")
        
        f.write("===== 内存使用情况 =====\n")
        f.write(f"平均内存使用: {sum(memory_values) / len(memory_values) / 1024:.2f} MB\n")
        f.write(f"最大内存使用: {max(memory_values) / 1024:.2f} MB\n")
        f.write(f"最小内存使用: {min(memory_values) / 1024:.2f} MB\n")
        f.write(f"详细内存信息: 已保存在 {meminfo_dir} 目录下\n\n")
        
        f.write("===== CPU使用情况 =====\n")
        f.write(f"平均CPU使用率: {sum(cpu_values) / len(cpu_values):.2f}%\n")
        f.write(f"最大CPU使用率: {max(cpu_values):.2f}%\n")
        f.write(f"最小CPU使用率: {min(cpu_values):.2f}%\n\n")
        
        f.write("===== 流畅度分析 =====\n")
        f.write(f"平均卡顿帧比例: {sum(janky_values) / len(janky_values):.2f}%\n")
        f.write(f"最大卡顿帧比例: {max(janky_values):.2f}%\n")
        f.write(f"最小卡顿帧比例: {min(janky_values):.2f}%\n\n")
        
        f.write("===== 设备温度 =====\n")
        f.write(f"平均电池温度: {sum(battery_temp_values) / len(battery_temp_values):.2f}°C\n")
        f.write(f"最高电池温度: {max(battery_temp_values):.2f}°C\n")
        f.write(f"最低电池温度: {min(battery_temp_values):.2f}°C\n\n")
        
        f.write("===== 性能评估 =====\n")
        # 内存评估
        avg_memory_mb = sum(memory_values) / len(memory_values) / 1024
        if avg_memory_mb > 500:
            memory_assessment = "内存使用较高，建议优化内存使用"
        elif avg_memory_mb > 200:
            memory_assessment = "内存使用正常"
        else:
            memory_assessment = "内存使用良好"
        f.write(f"内存评估: {memory_assessment}\n")
        
        # CPU评估
        avg_cpu = sum(cpu_values) / len(cpu_values)
        if avg_cpu > 30:
            cpu_assessment = "CPU使用率较高，建议检查是否有耗CPU的操作"
        elif avg_cpu > 15:
            cpu_assessment = "CPU使用率正常"
        else:
            cpu_assessment = "CPU使用率良好"
        f.write(f"CPU评估: {cpu_assessment}\n")
        
        # 流畅度评估
        avg_janky = sum(janky_values) / len(janky_values)
        if avg_janky > 20:
            janky_assessment = "卡顿较严重，建议优化渲染性能"
        elif avg_janky > 10:
            janky_assessment = "有轻微卡顿，可以考虑优化"
        else:
            janky_assessment = "流畅度良好"
        f.write(f"流畅度评估: {janky_assessment}\n")
        
        # 温度评估
        avg_temp = sum(battery_temp_values) / len(battery_temp_values)
        if avg_temp > 40:
            temp_assessment = "设备温度较高，应用可能导致设备发热严重"
        elif avg_temp > 35:
            temp_assessment = "设备温度偏高，但在可接受范围内"
        else:
            temp_assessment = "设备温度正常"
        f.write(f"温度评估: {temp_assessment}\n")
        
        # 添加详细内存信息说明
        f.write("\n===== 详细内存信息说明 =====\n")
        f.write("本次性能测试过程中，已收集应用的完整内存信息 (dumpsys meminfo)，\n")
        f.write(f"这些详细信息保存在 {meminfo_dir} 目录下，\n")
        f.write("文件命名格式为：设备ID_包名_meminfo_时间戳.txt\n")
        f.write("这些文件包含应用运行时的完整内存分配情况，可用于深入分析内存使用模式和潜在问题。\n")
    
    print(f"性能报告已生成: {report_file}")
    return report_file

def main():
    parser = argparse.ArgumentParser(description='应用性能分析工具')
    parser.add_argument('--package', '-p', help='应用包名，如不提供则尝试从auto_install.py获取')
    parser.add_argument('--duration', '-d', type=int, default=60, help='性能测试持续时间（秒），默认60秒')
    parser.add_argument('--interval', '-i', type=int, default=5, help='数据收集间隔（秒），默认5秒')
    parser.add_argument('--apk-dir', help='APK文件目录，用于自动获取包名')
    args = parser.parse_args()
    
    # 获取已连接的设备
    devices = get_connected_devices()
    if not devices:
        print("错误：没有找到已连接的设备")
        return
    
    package_name = args.package
    
    # 如果未提供包名，尝试从auto_install.py获取或从APK目录获取
    if not package_name:
        if args.apk_dir:
            # 导入auto_install模块中的函数
            try:
                import auto_install
                apk_path = auto_install.get_latest_apk(args.apk_dir)
                if apk_path:
                    package_name = auto_install.get_package_name(apk_path)
            except (ImportError, AttributeError) as e:
                print(f"警告：无法从auto_install模块获取包名：{e}")
        
        if not package_name:
            print("错误：未提供应用包名，且无法自动获取")
            return
    
    print(f"将对应用 {package_name} 进行性能分析")
    
    # 对每个设备进行操作
    for device_id in devices:
        print(f"\n处理设备：{device_id}")
        
        # 检查应用是否已安装
        if not is_app_installed(device_id, package_name):
            print(f"错误：应用 {package_name} 未在设备 {device_id} 上安装")
            continue
        
        # 启动应用
        if not launch_app(device_id, package_name):
            print(f"错误：无法在设备 {device_id} 上启动应用 {package_name}")
            continue
        
        # 等待应用完全启动
        print("等待应用完全启动...")
        time.sleep(3)
        
        # 收集性能数据
        csv_file = collect_performance_data(device_id, package_name, args.duration, args.interval)
        
        # 生成性能报告
        report_file = generate_performance_report(csv_file)
        
        print(f"设备 {device_id} 的性能分析完成，报告保存在 {report_file}")

if __name__ == "__main__":
    main()