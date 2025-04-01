#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
游戏帧率测试工具

本脚本用于在Android设备上测量游戏应用的帧率(FPS)。
主要功能：
1. 自动检测所有已连接的Android设备
2. 获取每个设备的详细信息
3. 在每个设备上安装指定的APK
4. 收集每个设备上应用的帧率数据
5. 检测卡顿情况和帧率分布
6. 将结果保存为JSON格式，文件名包含设备全名和设备ID

使用方法：
python test_frame.py --apk-dir <APK目录> --activity <主活动名> --duration <测试时长(秒)> --results-dir <结果保存目录>
"""

import subprocess
import os
import glob
import time
import re
import json
import platform
import statistics
import random
from datetime import datetime
from pathlib import Path
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor

def get_latest_apk(directory):
    """获取指定目录下最新的APK文件"""
    apk_files = glob.glob(os.path.join(directory, '*.apk'))
    if not apk_files:
        return None
    return max(apk_files, key=os.path.getmtime)

def run_adb_command(command, device_id=None):
    """执行adb命令并返回结果"""
    # 检查系统类型，确保ADB命令能在不同平台正确执行
    system_type = get_system_type()
    
    # 构建基本命令
    cmd = ['adb']
    if device_id:
        cmd.extend(['-s', device_id])
    
    if '|' in command:
        # 对于包含管道的命令，需要使用shell=True
        if system_type == 'windows':
            # Windows下可能需要使用cmd /c
            full_cmd = ' '.join(cmd) + ' ' + command
        else:
            # Mac和Linux可以直接使用管道
            full_cmd = ' '.join(cmd) + ' ' + command
            
        try:
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception as e:
            print(f"执行命令失败: {full_cmd}\n错误信息: {str(e)}")
            return ""
    else:
        # 对于不包含管道的简单命令
        cmd.extend(command.split())
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception as e:
            print(f"执行命令失败: {' '.join(cmd)}\n错误信息: {str(e)}")
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
        for line in result.stdout.split('\n')[1:]:
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

def get_device_info(device_id):
    """获取设备详细信息"""
    try:
        info = {
            'device_id': device_id,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'model': {}
        }
        
        # 获取设备型号信息
        manufacturer = run_adb_command('shell getprop ro.product.manufacturer', device_id)
        model = run_adb_command('shell getprop ro.product.model', device_id)
        brand = run_adb_command('shell getprop ro.product.brand', device_id)
        
        info['model']['manufacturer'] = manufacturer
        info['model']['model'] = model
        info['model']['brand'] = brand
        info['model']['full_name'] = f"{brand}_{model}"
        
        # 获取设备屏幕刷新率
        refresh_output = run_adb_command('shell dumpsys display | grep "mDisplayInfo"', device_id)
        refresh_match = re.search(r'fps=(\d+\.?\d*)', refresh_output)
        if refresh_match:
            info['model']['refresh_rate'] = float(refresh_match.group(1))
        else:
            info['model']['refresh_rate'] = 60.0  # 默认值
        
        return info
    except Exception as e:
        print(f"获取设备信息失败: {str(e)}")
        return None

def get_system_type():
    """获取当前系统类型"""
    system = platform.system().lower()
    if system == 'darwin':
        return 'mac'
    elif system == 'windows':
        return 'windows'
    elif system == 'linux':
        return 'linux'
    else:
        return 'unknown'

def get_package_name(apk_path):
    """从APK文件中提取package name"""
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
        
        for line in result.stdout.split('\n'):
            if line.startswith('package: name='):
                return line.split("'")[1]
        return None
    except Exception as e:
        print(f"错误：解析APK信息时发生异常：{str(e)}")
        return None

def install_apk(device_id, apk_path, package_name):
    """在指定设备上安装APK"""
    print(f"正在向设备 {device_id} 安装 {os.path.basename(apk_path)}")
    
    # 先尝试卸载已存在的应用
    run_adb_command(f"shell pm uninstall {package_name}", device_id)
    
    # 安装新应用
    result = run_adb_command(f"install -r -t {apk_path}", device_id)
    return "Success" in result

def collect_fps_data(device_id, package_name, duration=60, interval=1):
    """收集指定设备上的帧率数据"""
    results = []
    fps_values = []
    frame_times = []
    jank_count = 0
    total_frames = 0
    
    print(f"设备 {device_id} - 开始收集帧率数据，持续 {duration} 秒...")
    
    # 启用帧率统计功能
    run_adb_command(f"shell setprop debug.hwui.profile true", device_id)
    run_adb_command(f"shell setprop debug.hwui.renderer.profile true", device_id)
    run_adb_command(f"shell setprop debug.egl.trace 1", device_id)
    
    # 启用gfxinfo统计
    run_adb_command(f"shell service call SurfaceFlinger 1008 i32 1", device_id)  # 启用帧率统计
    
    # 清除之前的图形信息
    run_adb_command(f"shell dumpsys gfxinfo {package_name} reset", device_id)
    
    # 收集指定时长的帧率数据
    start_time = time.time()
    iterations = 0
    prev_total_frames = 0
    accumulated_frames = 0
    accumulated_janky = 0
    
    while time.time() - start_time < duration:
        # 等待指定的间隔时间
        time.sleep(interval)
        iterations += 1
        
        # 获取图形信息 - 尝试多种方式获取帧率数据
        # 1. 首先尝试标准gfxinfo
        output = run_adb_command(f"shell dumpsys gfxinfo {package_name}", device_id)
        
        # 2. 如果没有足够信息，尝试framestats
        if "Total frames rendered" not in output:
            output += run_adb_command(f"shell dumpsys gfxinfo {package_name} framestats", device_id)
        
        # 解析帧率信息
        # 提取总帧数和慢帧数
        total_frames_match = re.search(r'Total frames rendered: (\d+)', output)
        janky_frames_match = re.search(r'Janky frames: (\d+) \((\d+\.\d+)%\)', output)
        
        # 尝试提取帧时间分布
        frame_time_data = {}
        frame_time_section = False
        for line in output.split('\n'):
            if 'Frame time histogram' in line:
                frame_time_section = True
                continue
            if frame_time_section and re.match(r'\s+\d+ms=\d+', line.strip()):
                parts = line.strip().split('=')
                if len(parts) == 2:
                    time_ms = parts[0].strip().rstrip('ms')
                    count = parts[1].strip()
                    frame_time_data[time_ms] = int(count)
            elif frame_time_section and line.strip() == "":
                frame_time_section = False
        
        # 提取详细的帧时间数据（如果可用）
        detailed_frame_times = []
        frame_times_section = False
        for line in output.split('\n'):
            if 'HISTOGRAM' in line or 'Framestats:' in line:
                frame_times_section = True
                continue
            if frame_times_section and (re.match(r'\s+\d+\.\d+ms', line.strip()) or 
                                        re.match(r'\s*\d+,\s*\d+,\s*\d+', line.strip())):
                # 处理不同格式的帧时间数据
                if 'ms' in line:
                    time_value = float(line.strip().rstrip('ms'))
                    detailed_frame_times.append(time_value)
                    frame_times.append(time_value)
                else:
                    # 处理framestats格式的数据，通常是逗号分隔的数值
                    parts = line.strip().split(',')
                    if len(parts) >= 3:  # 确保有足够的数据
                        try:
                            # 通常第3列是VSYNC到渲染完成的时间（单位：纳秒）
                            time_value = float(parts[2].strip()) / 1000000  # 转换为毫秒
                            detailed_frame_times.append(time_value)
                            frame_times.append(time_value)
                        except (ValueError, IndexError):
                            pass
            elif frame_times_section and line.strip() == "":
                frame_times_section = False
        
        # 计算当前迭代的帧率
        current_total_frames = int(total_frames_match.group(1)) if total_frames_match else 0
        current_janky_frames = int(janky_frames_match.group(1)) if janky_frames_match else 0
        current_janky_percent = float(janky_frames_match.group(2)) if janky_frames_match else 0.0
        
        # 如果无法从dumpsys获取帧数，尝试通过详细帧时间数据计算
        if current_total_frames == 0 and detailed_frame_times:
            current_total_frames = len(detailed_frame_times)
        
        # 计算这个间隔的帧数和帧率
        frames_in_interval = current_total_frames - prev_total_frames
        
        # 如果帧数计算为负数或零，可能是因为重置了计数器，尝试使用备选方法获取
        if frames_in_interval <= 0:
            # 尝试使用SurfaceFlinger获取帧率
            window_name = run_adb_command(f"shell dumpsys SurfaceFlinger | grep {package_name} | head -1", device_id)
            window_name = window_name.strip().split()[0] if window_name else ""
            
            if window_name:
                # 清除之前的延迟数据
                run_adb_command(f"shell dumpsys SurfaceFlinger --latency-clear {window_name}", device_id)
                time.sleep(interval * 0.8)  # 等待收集数据，稍微短一点以确保在下一次迭代前完成
                
                # 获取延迟数据
                sf_output = run_adb_command(f"shell dumpsys SurfaceFlinger --latency {window_name}", device_id)
                
                # 计算帧数 - 每三行数据代表一帧
                valid_lines = [line for line in sf_output.split('\n') if re.match(r'\s*\d+', line.strip())]
                frames_in_interval = len(valid_lines) // 3
            
            # 如果仍然无法获取，标记为无法获取
            if frames_in_interval <= 0:
                frames_in_interval = 0
                print(f"设备 {device_id} - 警告：无法获取帧率数据")
        
        fps_in_interval = frames_in_interval / interval if interval > 0 else 0
        fps_values.append(fps_in_interval)
        
        # 更新总计数
        prev_total_frames = current_total_frames
        accumulated_frames += frames_in_interval
        
        # 处理卡顿帧数 - 如果无法直接获取
        if current_janky_frames == 0:
            if frames_in_interval <= 0:
                # 如果帧数无法获取，卡顿数据也标记为无法获取
                current_janky_percent = None
                print(f"设备 {device_id} - 警告：无法获取卡顿帧数据")
            else:
                # 如果有帧数但无卡顿数据，标记为无法获取卡顿数据
                current_janky_percent = None
                print(f"设备 {device_id} - 警告：无法获取卡顿帧数据，但帧数正常")
                # 不累加估计的卡顿帧数
        else:
            accumulated_janky += (current_janky_frames - jank_count)
            jank_count = current_janky_frames
        
        # 记录这次迭代的结果
        result = {
            "iteration": iterations,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fps": fps_in_interval,
            "total_frames": accumulated_frames,  # 使用累积值
            "janky_frames": accumulated_janky,  # 使用累积值
            "janky_percent": current_janky_percent,
            "frame_time_distribution": frame_time_data,
            "detailed_frame_times": detailed_frame_times if detailed_frame_times else None
        }
        
        results.append(result)
        print(f"设备 {device_id} - 迭代 {iterations}: FPS: {fps_in_interval:.1f}, 卡顿: {current_janky_percent:.1f}%")
        
        # 重置图形信息，准备下一次收集
        run_adb_command(f"shell dumpsys gfxinfo {package_name} reset", device_id)
    
    # 测试结束后，关闭性能监控
    run_adb_command(f"shell setprop debug.hwui.profile false", device_id)
    run_adb_command(f"shell setprop debug.hwui.renderer.profile false", device_id)
    run_adb_command(f"shell setprop debug.egl.trace 0", device_id)
    run_adb_command(f"shell service call SurfaceFlinger 1008 i32 0", device_id)  # 关闭帧率统计
    
    return results, fps_values, frame_times, accumulated_janky, accumulated_frames

def process_device(device_id, apk_path, package_name, activity_name, duration, results_dir=None):
    """处理单个设备的完整流程"""
    try:
        # 获取设备信息
        device_info = get_device_info(device_id)
        if not device_info:
            print(f"设备 {device_id} - 错误：无法获取设备信息")
            return
        
        # 安装APK
        if not install_apk(device_id, apk_path, package_name):
            print(f"设备 {device_id} - 错误：APK安装失败")
            return
        
        # 启用性能监控所需的系统属性
        print(f"设备 {device_id} - 启用性能监控...")
        run_adb_command(f"shell setprop debug.hwui.profile true", device_id)
        run_adb_command(f"shell setprop debug.hwui.renderer.profile true", device_id)
        run_adb_command(f"shell setprop debug.egl.trace 1", device_id)
        
        # 构建完整的组件名称
        if activity_name.startswith('.'):
            component = f"{package_name}/{package_name}{activity_name}"
        elif '.' in activity_name and not activity_name.startswith(package_name):
            component = f"{package_name}/{activity_name}"
        else:
            component = f"{package_name}/{activity_name}"
        
        # 启动应用
        print(f"设备 {device_id} - 启动应用: {component}")
        run_adb_command(f"shell am force-stop {package_name}", device_id)
        time.sleep(1)
        run_adb_command(f"shell am start -n {component}", device_id)
        
        # 等待应用完全启动
        print(f"设备 {device_id} - 等待应用启动...")
        time.sleep(5)
        
        # 收集帧率数据
        fps_results, fps_values, frame_times, jank_count, total_frames = collect_fps_data(
            device_id, package_name, duration, interval=1
        )
        
        # 计算统计数据
        stats = {}
        if fps_values:
            stats["min_fps"] = min(fps_values)
            stats["max_fps"] = max(fps_values)
            stats["avg_fps"] = statistics.mean(fps_values)
            stats["median_fps"] = statistics.median(fps_values)
            if len(fps_values) > 1:
                stats["stdev_fps"] = statistics.stdev(fps_values)
            else:
                stats["stdev_fps"] = 0
        
        # 计算帧时间统计
        if frame_times:
            stats["min_frame_time"] = min(frame_times)
            stats["max_frame_time"] = max(frame_times)
            stats["avg_frame_time"] = statistics.mean(frame_times)
            stats["median_frame_time"] = statistics.median(frame_times)
            if len(frame_times) > 1:
                stats["stdev_frame_time"] = statistics.stdev(frame_times)
            else:
                stats["stdev_frame_time"] = 0
        
        # 计算帧率稳定性指标
        if fps_values and len(fps_values) > 1:
            # 计算帧率变化率
            fps_changes = [abs(fps_values[i] - fps_values[i-1]) for i in range(1, len(fps_values))]
            stats["fps_stability"] = 1.0 - (statistics.mean(fps_changes) / stats["avg_fps"] if stats["avg_fps"] > 0 else 0)
            # 帧率稳定性百分比
            stats["fps_stability_percent"] = stats["fps_stability"] * 100
        
        # 准备完整的结果数据
        result_data = {
            "device_info": device_info,
            "test_info": {
                "package_name": package_name,
                "activity_name": activity_name,
                "apk_file": os.path.basename(apk_path),
                "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration": duration
            },
            "fps_results": fps_results,
            "statistics": stats,
            "summary": {
                "total_frames": total_frames,
                "janky_frames": jank_count,
                "janky_percent": (jank_count / total_frames * 100) if total_frames > 0 else 0
            }
        }
        
        # 保存结果到JSON文件
        device_name = device_info['model']['full_name']
        
        # 如果未指定结果目录，则根据系统类型确定默认路径
        if not results_dir:
            system_type = get_system_type()
            if system_type == 'mac':
                # 在Mac上使用当前目录或指定目录
                results_dir = os.path.join(os.getcwd(), 'results')
            elif system_type == 'windows':
                # 在Windows上使用文档目录
                results_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'TestAutoResults')
            else:  # Linux或其他系统
                results_dir = os.path.join(os.path.expanduser('~'), 'TestAutoResults')
        
        # 确保结果目录存在
        os.makedirs(results_dir, exist_ok=True)
        
        result_file = os.path.join(results_dir, f"fps_results_{device_name}_{device_id}.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"设备 {device_id} - 结果已保存到: {result_file}")
        print(f"设备 {device_id} - 测试摘要:")
        print(f"  平均帧率: {stats.get('avg_fps', 0):.1f} FPS")
        print(f"  最低帧率: {stats.get('min_fps', 0):.1f} FPS")
        print(f"  最高帧率: {stats.get('max_fps', 0):.1f} FPS")
        print(f"  帧率稳定性: {stats.get('fps_stability_percent', 0):.1f}%")
        print(f"  卡顿帧比例: {result_data['summary']['janky_percent']:.1f}%")
        
    except Exception as e:
        print(f"设备 {device_id} - 处理过程中发生错误：{str(e)}")

def main():
    # 检测当前系统类型
    system_type = get_system_type()
    print(f"当前运行平台: {system_type.upper()}")
    
    parser = argparse.ArgumentParser(description='游戏帧率测试工具')
    
    # 根据系统类型设置默认APK目录
    if system_type == 'mac':
        default_apk_dir = "/Volumes/MacEx/TestAutoAPK"
    elif system_type == 'windows':
        default_apk_dir = "D:\\UnityProjects\\HexaMatch"
    else:  # Linux或其他系统
        default_apk_dir = os.path.expanduser("~/TestAutoAPK")
    
    # 设置默认结果目录
    if system_type == 'mac':
        default_results_dir = os.path.join(os.getcwd(), 'results')
    elif system_type == 'windows':
        default_results_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'TestAutoResults')
    else:  # Linux或其他系统
        default_results_dir = os.path.join(os.path.expanduser('~'), 'TestAutoResults')
    
    parser.add_argument('--apk-dir', default=default_apk_dir, help=f'APK文件所在目录 (默认: {default_apk_dir})')
    parser.add_argument('--activity', default='com.unity3d.player.UnityPlayerActivity', help='启动活动名称，默认为UnityPlayerActivity')
    parser.add_argument('--duration', type=int, default=60, help='帧率测试持续时间(秒)，默认为60秒')
    parser.add_argument('--results-dir', default=default_results_dir, help=f'结果文件保存目录 (默认: {default_results_dir})')
    args = parser.parse_args()
    
    print(f"APK目录: {args.apk_dir}")
    print(f"结果保存目录: {args.results_dir}")
    print(f"测试持续时间: {args.duration}秒")
    
    # 确保结果目录存在
    os.makedirs(args.results_dir, exist_ok=True)
    
    # 获取最新的APK文件
    apk_path = get_latest_apk(args.apk_dir)
    if not apk_path:
        print(f"错误：在目录 {args.apk_dir} 中未找到APK文件")
        return
    
    # 获取包名
    package_name = get_package_name(apk_path)
    if not package_name:
        print("错误：无法从APK文件中获取包名")
        return
    
    # 获取已连接的设备
    devices = get_connected_devices()
    if not devices:
        print("错误：未找到已连接的设备")
        return
    
    print(f"\n开始在 {len(devices)} 个设备上测量帧率...")
    
    # 使用线程池并行处理多个设备
    with ThreadPoolExecutor(max_workers=len(devices)) as executor:
        futures = []
        for device_id in devices:
            future = executor.submit(
                process_device,
                device_id,
                apk_path,
                package_name,
                args.activity,
                args.duration,
                args.results_dir
            )
            futures.append(future)
        
        # 等待所有设备处理完成
        for future in futures:
            future.result()
    
    print("\n所有设备的帧率测量已完成！")

if __name__ == "__main__":
    main()