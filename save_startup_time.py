#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
import argparse
from extract_and_match_text import extract_all_texts_from_folder, load_extracted_texts, match_text_in_extracted_data

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

def save_to_json(data, output_file="startup_time.json", folder_path=None):
    """
    将数据保存为JSON文件
    
    Args:
        data: 要保存的数据
        output_file: 输出文件名
        folder_path: 图片文件夹路径，如果提供，则将文件保存到该文件夹中
    """
    # 如果提供了文件夹路径，则将文件保存到该文件夹中
    if folder_path:
        # 确保文件夹路径存在
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        output_file = os.path.join(folder_path, output_file)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"启动时长数据已保存到: {output_file}")

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='在图片中查找包含特定文字的图片并将结果保存为启动时长格式')
    parser.add_argument('folder', help='图片文件夹路径')
    parser.add_argument('--text', help='要查找的文字')
    parser.add_argument('--exact', action='store_true', help='使用精确匹配模式（默认为部分匹配）')
    parser.add_argument('--use-cache', help='使用已提取的文本缓存文件')
    parser.add_argument('--output', help='输出JSON文件名', default='startup_time.json')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    matching_images = []
    
    # 检查是否使用缓存
    if args.use_cache:
        print(f"从缓存加载提取的文本: {args.use_cache}")
        image_texts = load_extracted_texts(args.use_cache)
        
        # 如果提供了搜索文本，则进行匹配
        if args.text:
            # 在提取的文本中查找匹配
            matching_images = match_text_in_extracted_data(image_texts, args.text, not args.exact)
    else:
        # 如果提供了搜索文本，extract_all_texts_from_folder会在找到第一个匹配时提前返回
        image_texts = extract_all_texts_from_folder(args.folder, args.text if args.text else None)
        
        # 如果提供了搜索文本，直接从image_texts中获取匹配的图片名称
        if args.text:
            # 如果使用了search_text参数，extract_all_texts_from_folder会在找到第一个匹配时提前返回
            # 所以这里直接使用keys作为匹配的图片名称
            matching_images = list(image_texts.keys())
    
    # 输出结果
    if args.text:
        print("\n搜索结果:")
        if matching_images:
            print(f"找到 {len(matching_images)} 张包含文字 '{args.text}' 的图片:")
            for img in matching_images:
                print(f"- {img}")
                
            # 格式化启动时长并保存为JSON
            startup_times = format_startup_time(matching_images)
            # 将文件保存到图片所在的文件夹中
            save_to_json(startup_times, args.output, args.folder)
        else:
            print(f"没有找到包含文字 '{args.text}' 的图片")
    else:
        print("\n未提供搜索文本，无法生成启动时长数据。使用 --text 参数指定要搜索的文本。")

if __name__ == "__main__":
    main()