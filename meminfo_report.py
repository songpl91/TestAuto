#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import csv
import glob
from datetime import datetime
import argparse


def extract_meminfo(file_path):
    """从内存信息文件中提取关键内存数据"""
    data = {}
    
    # 从文件名中提取设备ID和时间信息
    filename = os.path.basename(file_path)
    match = re.search(r'(.+?)_com\.kiwifun\.game\.android\.hexacrush\.puzzles_meminfo_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.txt', filename)
    if match:
        data['device_id'] = match.group(1)
        date_str = match.group(2)
        time_str = match.group(3).replace('-', ':')
        data['timestamp'] = f"{date_str} {time_str}"
        data['collection_time'] = f"{date_str} {time_str}"  # 默认与timestamp相同
    else:
        data['device_id'] = 'unknown'
        data['timestamp'] = 'unknown'
        data['collection_time'] = 'unknown'
    
    # 初始化所有可能的字段为0，确保CSV格式一致
    fields = [
        'pid', 'total_pss', 'total_private_dirty', 'total_private_clean', 'total_swap_pss',
        'native_heap_pss', 'native_heap_private_dirty', 'native_heap_size', 'native_heap_alloc', 'native_heap_free',
        'dalvik_heap_pss', 'dalvik_heap_private_dirty', 'dalvik_heap_size', 'dalvik_heap_alloc', 'dalvik_heap_free',
        'graphics_pss', 'egl_mtrack_pss', 'gl_mtrack_pss', 'java_heap_pss', 'code_pss', 'stack_pss',
        'private_other_pss', 'system_pss'
    ]
    
    for field in fields:
        data[field] = '0'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 提取采集时间
            time_match = re.search(r'采集时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', content)
            if time_match:
                data['collection_time'] = time_match.group(1)
            
            # 提取进程ID
            pid_match = re.search(r'\*\* MEMINFO in pid (\d+)', content)
            if pid_match:
                data['pid'] = pid_match.group(1)
            
            # 提取总PSS
            total_match = re.search(r'TOTAL\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', content)
            if total_match:
                data['total_pss'] = total_match.group(1)
                data['total_private_dirty'] = total_match.group(2)
                data['total_private_clean'] = total_match.group(3)
                data['total_swap_pss'] = total_match.group(4)
            
            # 提取Native Heap信息 - 处理不同格式
            native_heap_match = re.search(r'Native Heap\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)', content)
            if native_heap_match:
                data['native_heap_pss'] = native_heap_match.group(1)
                data['native_heap_private_dirty'] = native_heap_match.group(2)
                data['native_heap_size'] = native_heap_match.group(3)
                data['native_heap_alloc'] = native_heap_match.group(4)
                data['native_heap_free'] = native_heap_match.group(5)
            else:
                # 尝试另一种格式
                native_heap_match = re.search(r'Native Heap\s+(\d+)\s+(\d+)\s+\d+\s+\d+', content)
                if native_heap_match:
                    data['native_heap_pss'] = native_heap_match.group(1)
                    data['native_heap_private_dirty'] = native_heap_match.group(2)
            
            # 提取Dalvik Heap信息 - 处理不同格式
            dalvik_heap_match = re.search(r'Dalvik Heap\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)', content)
            if dalvik_heap_match:
                data['dalvik_heap_pss'] = dalvik_heap_match.group(1)
                data['dalvik_heap_private_dirty'] = dalvik_heap_match.group(2)
                data['dalvik_heap_size'] = dalvik_heap_match.group(3)
                data['dalvik_heap_alloc'] = dalvik_heap_match.group(4)
                data['dalvik_heap_free'] = dalvik_heap_match.group(5)
            else:
                # 尝试另一种格式
                dalvik_heap_match = re.search(r'Dalvik Heap\s+(\d+)\s+(\d+)\s+\d+\s+\d+', content)
                if dalvik_heap_match:
                    data['dalvik_heap_pss'] = dalvik_heap_match.group(1)
                    data['dalvik_heap_private_dirty'] = dalvik_heap_match.group(2)
            
            # 提取Graphics信息
            graphics_match = re.search(r'Graphics:\s+(\d+)', content)
            if graphics_match:
                data['graphics_pss'] = graphics_match.group(1)
            
            # 提取EGL和GL mtrack信息
            egl_match = re.search(r'EGL mtrack\s+(\d+)\s+(\d+)', content)
            if egl_match:
                data['egl_mtrack_pss'] = egl_match.group(1)
            
            gl_match = re.search(r'GL mtrack\s+(\d+)\s+(\d+)', content)
            if gl_match:
                data['gl_mtrack_pss'] = gl_match.group(1)
            
            # 提取App Summary信息
            java_heap_match = re.search(r'Java Heap:\s+(\d+)', content)
            if java_heap_match:
                data['java_heap_pss'] = java_heap_match.group(1)
            
            code_match = re.search(r'Code:\s+(\d+)', content)
            if code_match:
                data['code_pss'] = code_match.group(1)
            
            stack_match = re.search(r'Stack:\s+(\d+)', content)
            if stack_match:
                data['stack_pss'] = stack_match.group(1)
            
            private_other_match = re.search(r'Private Other:\s+(\d+)', content)
            if private_other_match:
                data['private_other_pss'] = private_other_match.group(1)
            
            system_match = re.search(r'System:\s+(\d+)', content)
            if system_match:
                data['system_pss'] = system_match.group(1)
            
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
    
    return data


def process_meminfo_folder(folder_path, output_csv, device_folder=None):
    """处理指定文件夹中的所有内存信息文件，并将结果写入CSV文件
    
    Args:
        folder_path: meminfo_details文件夹路径
        output_csv: 输出CSV文件名或路径
        device_folder: 设备文件夹路径，如果提供，CSV将保存在此文件夹中
    """
    # 获取所有内存信息文件
    file_pattern = os.path.join(folder_path, '*_meminfo_*.txt')
    files = glob.glob(file_pattern)
    
    # 按文件名排序
    files.sort()
    
    if not files:
        print(f"在 {folder_path} 中未找到内存信息文件")
        return
    
    # 预定义CSV的列名，确保所有CSV文件具有相同的列结构
    fieldnames = [
        'device_id', 'timestamp', 'collection_time', 'pid',
        'total_pss', 'total_private_dirty', 'total_private_clean', 'total_swap_pss',
        'native_heap_pss', 'native_heap_private_dirty', 'native_heap_size', 'native_heap_alloc', 'native_heap_free',
        'dalvik_heap_pss', 'dalvik_heap_private_dirty', 'dalvik_heap_size', 'dalvik_heap_alloc', 'dalvik_heap_free',
        'graphics_pss', 'egl_mtrack_pss', 'gl_mtrack_pss',
        'java_heap_pss', 'code_pss', 'stack_pss', 'private_other_pss', 'system_pss'
    ]
    
    # 提取所有文件的内存信息
    all_data = []
    for i, file_path in enumerate(files, 1):
        data = extract_meminfo(file_path)
        if data:
            # 确保所有字段都存在
            for field in fieldnames:
                if field not in data:
                    data[field] = '0'
            all_data.append(data)
            print(f"已处理 {i}/{len(files)}: {os.path.basename(file_path)}")
        else:
            print(f"警告: 无法从文件提取数据: {os.path.basename(file_path)}")
    
    if not all_data:
        print("未能从文件中提取到有效的内存信息")
        return
    
    # 确定CSV文件的完整路径
    if device_folder and not os.path.isabs(output_csv):
        # 如果提供了设备文件夹路径且输出路径不是绝对路径，则将CSV保存到设备文件夹中
        full_output_path = os.path.join(device_folder, output_csv)
    else:
        # 否则使用提供的输出路径
        full_output_path = output_csv
    
    # 写入CSV文件
    with open(full_output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for data in all_data:
            writer.writerow(data)
    
    print(f"\n内存信息已保存到 {full_output_path}")


def main():
    parser = argparse.ArgumentParser(description='从meminfo_details文件夹中提取内存信息并生成CSV报告')
    parser.add_argument('--folder', '-f', help='包含meminfo_details的文件夹路径（默认：当前目录）', default='.')
    parser.add_argument('--output', '-o', help='输出CSV文件路径（默认：meminfo_report.csv）', default='meminfo_report.csv')
    parser.add_argument('--device', '-d', help='处理特定设备文件夹（例如：Xiaomi_MI_6_20250328_201058）')
    
    args = parser.parse_args()
    
    base_folder = args.folder
    output_csv = args.output
    
    if args.device:
        # 处理特定设备的meminfo_details文件夹
        device_path = os.path.join(base_folder, args.device)
        device_folder = os.path.join(device_path, 'meminfo_details')
        if os.path.isdir(device_folder):
            print(f"正在处理设备 {args.device} 的内存信息文件...")
            # 将CSV文件保存到设备文件夹中
            process_meminfo_folder(device_folder, output_csv, device_path)
        else:
            print(f"错误：未找到设备文件夹 {device_folder}")
    else:
        # 查找所有设备文件夹
        device_folders = []
        for item in os.listdir(base_folder):
            meminfo_folder = os.path.join(base_folder, item, 'meminfo_details')
            if os.path.isdir(meminfo_folder):
                device_folders.append((item, meminfo_folder))
        
        if not device_folders:
            print(f"在 {base_folder} 中未找到包含meminfo_details的设备文件夹")
            return
        
        # 如果只有一个设备文件夹，直接处理
        if len(device_folders) == 1:
            device_name, meminfo_folder = device_folders[0]
            device_path = os.path.join(base_folder, device_name)
            print(f"正在处理设备 {device_name} 的内存信息文件...")
            process_meminfo_folder(meminfo_folder, output_csv, device_path)
        else:
            # 如果有多个设备文件夹，为每个设备生成单独的CSV文件并保存到对应设备文件夹中
            print(f"找到 {len(device_folders)} 个包含meminfo_details的设备文件夹")
            for device_name, meminfo_folder in device_folders:
                device_path = os.path.join(base_folder, device_name)
                device_output = f"meminfo_report.csv"
                print(f"\n正在处理设备 {device_name} 的内存信息文件...")
                process_meminfo_folder(meminfo_folder, device_output, device_path)


if __name__ == "__main__":
    main()