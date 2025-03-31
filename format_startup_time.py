#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
import argparse

def extract_time_from_filename(filename):
    """
    从文件名中提取时间数值
    
    Args:
        filename: 图片文件名，如 "7855.png"
        
    Returns:
        提取的时间数值，如 7855
    """
    # 使用正则表达式提取文件名中的数字部分
    match = re.match(r'(\d+)\.png', filename)
    if match:
        return int(match.group(1))
    return None

def format_startup_time(image_files):
    """
    将图片文件名转换为启动时长格式
    
    Args:
        image_files: 图片文件名列表
        
    Returns:
        格式化后的启动时长字典，新格式为 {"startupTime": "XXXXms"}
    """
    # 只取第一个匹配的图片文件名作为启动时长
    for filename in image_files:
        time_ms = extract_time_from_filename(filename)
        if time_ms is not None:
            # 返回新格式的启动时长
            return {"startupTime": f"{time_ms}ms"}
    
    # 如果没有找到有效的时间，返回空字典
    return {}

def save_to_json(data, output_file="startup_time.json"):
    """
    将数据保存为JSON文件
    
    Args:
        data: 要保存的数据
        output_file: 输出文件名
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"启动时长数据已保存到: {output_file}")

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='将图片文件名转换为启动时长格式并保存为JSON')
    parser.add_argument('--files', nargs='+', help='图片文件名列表')
    parser.add_argument('--result-file', help='extract_and_match_text.py生成的结果文件')
    parser.add_argument('--output', help='输出JSON文件名', default='startup_time.json')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    image_files = []
    
    # 如果提供了文件列表，直接使用
    if args.files:
        image_files = args.files
    # 如果提供了结果文件，从文件中读取
    elif args.result_file:
        with open(args.result_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('- '):
                    image_files.append(line[2:].strip())
    # 如果没有提供任何输入，显示帮助信息
    else:
        parser.print_help()
        return
    
    # 格式化启动时长
    startup_times = format_startup_time(image_files)
    
    # 保存到JSON文件
    save_to_json(startup_times, args.output)

if __name__ == "__main__":
    main()