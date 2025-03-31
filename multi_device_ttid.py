#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多设备TTID测量工具

本脚本用于在多个Android设备上并行测量应用的TTID（Time To Initial Display）。
主要功能：
1. 自动检测所有已连接的Android设备
2. 获取每个设备的详细信息
3. 在每个设备上安装指定的APK
4. 收集每个设备上应用的TTID数据
5. 将结果保存为JSON格式，文件名包含设备全名和设备ID
"""

import subprocess
import os
import glob
import time
import re
import json
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
    cmd = ['adb']
    if device_id:
        cmd.extend(['-s', device_id])
    
    if '|' in command:
        full_cmd = ' '.join(cmd) + ' ' + command
        try:
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception as e:
            print(f"执行命令失败: {full_cmd}\n错误信息: {str(e)}")
            return ""
    else:
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
        
        return info
    except Exception as e:
        print(f"获取设备信息失败: {str(e)}")
        return None

def get_package_name(apk_path):
    """从APK文件中提取package name"""
    try:
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

def collect_ttid(device_id, package_name, activity_name, repeat_count=5):
    """收集指定设备上的TTID数据"""
    results = []
    
    # 构建完整的组件名称
    if activity_name.startswith('.'):
        component = f"{package_name}/{package_name}{activity_name}"
    elif '.' in activity_name and not activity_name.startswith(package_name):
        component = f"{package_name}/{activity_name}"
    else:
        component = f"{package_name}/{activity_name}"
    
    for i in range(repeat_count):
        print(f"设备 {device_id} - 执行第 {i+1}/{repeat_count} 次TTID测量...")
        
        # 强制停止应用
        run_adb_command(f"shell am force-stop {package_name}", device_id)
        time.sleep(1)
        
        # 启动应用并收集启动时间
        command = f"shell am start-activity -W -S -R 1 -n {component}"
        output = run_adb_command(command, device_id)
        
        if not output:
            print(f"设备 {device_id} - 警告：未能获取启动时间数据，跳过此次测量")
            continue
        
        # 解析输出结果
        this_time_match = re.search(r'ThisTime:\s+(\d+)', output)
        total_time_match = re.search(r'TotalTime:\s+(\d+)', output)
        
        result = {
            "iteration": i + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if this_time_match:
            result["ttid_ms"] = int(this_time_match.group(1))
            print(f"设备 {device_id} - TTID: {result['ttid_ms']} ms")
        
        results.append(result)
        time.sleep(2)
    
    return results

def process_device(device_id, apk_path, package_name, activity_name, repeat_count):
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
        
        # 收集TTID数据
        ttid_results = collect_ttid(device_id, package_name, activity_name, repeat_count)
        
        # 计算统计数据
        ttid_values = [r["ttid_ms"] for r in ttid_results if "ttid_ms" in r]
        stats = {
            "min_ttid": min(ttid_values) if ttid_values else None,
            "max_ttid": max(ttid_values) if ttid_values else None,
            "avg_ttid": sum(ttid_values) / len(ttid_values) if ttid_values else None
        }
        
        # 准备完整的结果数据
        result_data = {
            "device_info": device_info,
            "test_info": {
                "package_name": package_name,
                "activity_name": activity_name,
                "apk_file": os.path.basename(apk_path),
                "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "repeat_count": repeat_count
            },
            "ttid_results": ttid_results,
            "statistics": stats
        }
        
        # 保存结果到JSON文件
        device_name = device_info['model']['full_name']
        result_file = f"ttid_results_{device_name}_{device_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"设备 {device_id} - 结果已保存到: {result_file}")
        
    except Exception as e:
        print(f"设备 {device_id} - 处理过程中发生错误：{str(e)}")

def main():
    parser = argparse.ArgumentParser(description='多设备TTID测量工具')
    parser.add_argument('--apk-dir', default="D:\\UnityProjects\\HexaMatch", help='APK文件所在目录')
    parser.add_argument('--activity', default='com.unity3d.player.UnityPlayerActivity', help='启动活动名称，默认为.MainActivity')
    parser.add_argument('--repeat', type=int, default=5, help='每个设备重复测量次数，默认为5次')
    args = parser.parse_args()
    
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
    
    print(f"\n开始在 {len(devices)} 个设备上并行测量TTID...")
    
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
                args.repeat
            )
            futures.append(future)
        
        # 等待所有设备处理完成
        for future in futures:
            future.result()
    
    print("\n所有设备的TTID测量已完成！")

if __name__ == "__main__":
    main()