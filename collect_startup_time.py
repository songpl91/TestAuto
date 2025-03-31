#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
应用启动时间测量工具

本脚本用于测量Android应用的启动时间，支持两种启动模式：
1. 冷启动（Cold Start）：完全清除应用缓存和进程，模拟首次启动或长时间未使用后的启动场景。
   - 执行force-stop停止应用
   - 执行pm clear清除应用数据和缓存
   - 释放系统缓存
   - 等待足够时间确保资源完全释放
   这种模式与PerfDog等专业性能测试工具的冷启动测量方式更为接近。

2. 热启动（Hot Start）：仅停止应用进程但不清除缓存，模拟短时间内重新启动应用的场景。
   - 仅执行force-stop停止应用
   - 保留应用缓存和数据

使用-c/--cold参数启用冷启动模式（默认），使用--hot参数启用热启动模式。
"""

import subprocess
import re
import json
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

def run_adb_command(command, device_id=None):
    """执行adb命令并返回结果
    
    Args:
        command: 要执行的adb命令（不包含'adb'前缀）
        device_id: 设备ID，如果提供则针对特定设备执行命令
        
    Returns:
        命令执行的输出结果（字符串）
    """
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
    """获取所有已连接的设备ID
    
    Returns:
        设备ID列表
    """
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

def collect_startup_time(device_id, package_name, activity_name, repeat_count=5, cold_start=True):
    """收集应用启动时间（TTID和TTFD）
    
    Args:
        device_id: 设备ID
        package_name: 应用包名
        activity_name: 活动名称
        repeat_count: 重复测量次数
        
    Returns:
        包含启动时间数据的字典
    """
    print(f"开始收集应用 {package_name}/{activity_name} 在设备 {device_id} 上的启动时间数据，重复 {repeat_count} 次")
    
    # 如果是冷启动模式，先清理后台进程，确保测量环境一致
    if cold_start:
        print("清理后台进程...")
        run_adb_command("shell am kill-all", device_id)
        time.sleep(1)  # 等待进程清理完成
    
    # 构建完整的组件名称
    if activity_name.startswith('.'):
        # 如果以点开头，直接附加到包名后面
        component = f"{package_name}/{package_name}{activity_name}"
    elif '.' in activity_name and not activity_name.startswith(package_name):
        # 如果包含点但不是以包名开头，假设是完整的类名
        component = f"{package_name}/{activity_name}"
    else:
        # 其他情况，添加包名前缀
        component = f"{package_name}/{activity_name}"
    
    # 收集启动时间数据
    results = []
    for i in range(repeat_count):
        print(f"\n执行第 {i+1}/{repeat_count} 次测量...")
        
        # 强制停止应用
        print(f"强制停止应用 {package_name}...")
        run_adb_command(f"shell am force-stop {package_name}", device_id)
        
        # 如果是冷启动模式，还需要清除缓存和释放内存
        if cold_start:
            print(f"清除应用缓存 {package_name}...")
            run_adb_command(f"shell pm clear {package_name}", device_id)
            
            # 释放内存，确保系统资源充足
            print("释放系统内存...")
            run_adb_command("shell echo 3 > /proc/sys/vm/drop_caches", device_id)
            time.sleep(3)  # 增加等待时间，确保应用完全停止和缓存清除完成
        else:
            time.sleep(1)  # 热启动模式下，只需短暂等待应用停止
        
        # 执行启动命令并收集启动时间
        print(f"启动活动 {component} 并收集启动时间...")
        # 不使用管道和grep，直接获取完整输出
        command = f"shell am start-activity -W -S -R 1 -n {component}"
        output = run_adb_command(command, device_id)
        
        if not output:
            print("警告：未能获取启动时间数据，跳过此次测量")
            continue
        
        # 在Python中处理输出，查找TotalTime和WaitTime
        # 解析输出结果
        print(f"命令输出: {output}")
        this_time_match = re.search(r'ThisTime:\s+(\d+)', output)
        total_time_match = re.search(r'TotalTime:\s+(\d+)', output)
        wait_time_match = re.search(r'WaitTime:\s+(\d+)', output)
        
        result = {
            "iteration": i + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if total_time_match:
            result["this_time_match"] = this_time_match.group(1)  # TTID (Time To Initial Display)
            print(f"TTID: {result['this_time_match']} ms")
        
        # if wait_time_match:
        #     result["wait_time_ms"] = wait_time_match.group(1)  # TTFD (Time To Full Display)
        #     print(f"TTFD: {result['wait_time_ms']} ms")
        
        results.append(result)
        
        # 等待一段时间再进行下一次测量
        if i < repeat_count - 1:
            time.sleep(2)
    
    return results

def calculate_statistics(results):
    """计算启动时间的统计数据
    
    Args:
        results: 启动时间数据列表
        
    Returns:
        包含统计数据的字典
    """
    if not results:
        return {}
    
    # 提取TTID和TTFD数据
    ttid_values = [r.get("total_time_ms") for r in results if "total_time_ms" in r]
    ttfd_values = [r.get("wait_time_ms") for r in results if "wait_time_ms" in r]
    
    stats = {}
    
    # 计算TTID统计数据
    if ttid_values:
        stats["ttid"] = {
            "min": min(ttid_values),
            "max": max(ttid_values),
            "avg": sum(ttid_values) / len(ttid_values),
            "values": ttid_values
        }
    
    # 计算TTFD统计数据
    if ttfd_values:
        stats["ttfd"] = {
            "min": min(ttfd_values),
            "max": max(ttfd_values),
            "avg": sum(ttfd_values) / len(ttfd_values),
            "values": ttfd_values
        }
    
    return stats

def save_results(results, stats, package_name, device_id, output_dir=None):
    """保存测量结果和统计数据
    
    Args:
        results: 启动时间数据列表
        stats: 统计数据字典
        package_name: 应用包名
        device_id: 设备ID
        output_dir: 输出目录
        
    Returns:
        保存的文件路径
    """
    # 使用指定的输出目录或创建新的目录
    if output_dir:
        results_dir = Path(output_dir)
    else:
        # 使用设备ID和时间戳创建目录名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_dir = Path(f"startup_time_{device_id}_{timestamp}")
    
    # 确保目录存在
    results_dir.mkdir(exist_ok=True, parents=True)
    print(f"\n创建结果目录: {results_dir}")
    
    # 保存详细结果
    results_file = results_dir / f"{device_id}_{package_name}_startup_time_details.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"详细启动时间数据已保存到: {results_file}")
    
    # 保存统计数据
    stats_file = results_dir / f"{device_id}_{package_name}_startup_time_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"启动时间统计数据已保存到: {stats_file}")
    
    return str(results_dir)

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='收集Android应用的启动时间（TTID和TTFD）')
    parser.add_argument('-p', '--package', required=True, help='应用包名，例如：com.example.package')
    parser.add_argument('-a', '--activity', help='活动名称，例如：.MainActivity（如果省略，将使用包名的主活动）')
    parser.add_argument('-d', '--device', help='设备ID（如果省略，将使用第一个连接的设备）')
    parser.add_argument('-r', '--repeat', type=int, default=5, help='重复测量次数（默认：5）')
    parser.add_argument('-o', '--output', help='输出目录路径')
    parser.add_argument('-c', '--cold', action='store_true', default=True, help='使用真正的冷启动模式（清除缓存和释放内存，默认：开启）')
    parser.add_argument('--hot', action='store_false', dest='cold', help='使用热启动模式（只停止应用但不清除缓存）')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 获取设备ID
    device_id = args.device
    if not device_id:
        devices = get_connected_devices()
        if not devices:
            print("错误：未找到已连接的设备，请连接设备后重试")
            return 1
        device_id = devices[0]
        print(f"使用设备: {device_id}")
    
    # 获取活动名称
    activity_name = args.activity
    if not activity_name:
        activity_name = ".MainActivity"  # 使用默认的主活动名称
        print(f"未指定活动名称，使用默认值: {activity_name}")
    
    # 收集启动时间数据
    print(f"启动模式: {'冷启动（清除缓存）' if args.cold else '热启动（不清除缓存）'}")
    results = collect_startup_time(device_id, args.package, activity_name, args.repeat, args.cold)
    
    if not results:
        print("错误：未能收集到任何启动时间数据")
        return 1
    
    # 计算统计数据
    stats = calculate_statistics(results)
    
    # 保存结果
    save_results(results, stats, args.package, device_id, args.output)
    
    # 输出统计摘要
    print("\n启动时间统计摘要:")
    if "ttid" in stats:
        print(f"TTID (Time To Initial Display):")
        print(f"  最小值: {stats['ttid']['min']} ms")
        print(f"  最大值: {stats['ttid']['max']} ms")
        print(f"  平均值: {stats['ttid']['avg']:.2f} ms")
    
    if "ttfd" in stats:
        print(f"TTFD (Time To Full Display):")
        print(f"  最小值: {stats['ttfd']['min']} ms")
        print(f"  最大值: {stats['ttfd']['max']} ms")
        print(f"  平均值: {stats['ttfd']['avg']:.2f} ms")
    
    return 0

if __name__ == "__main__":
    exit(main())