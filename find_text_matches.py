#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速文本匹配工具

这个脚本用于快速从JSON文件中查找包含指定文本的图片。
支持多语言文本匹配（如英文、中文、阿拉伯语等）。
直接返回包含目标文本的图片文件名列表。
"""

import json
import argparse

def load_text_data(json_file):
    """加载JSON文件中的文本数据"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_text_matches(text_data, target_text, case_sensitive=False):
    """查找包含目标文本的图片
    
    Args:
        text_data: JSON文件中的文本数据
        target_text: 要查找的目标文本
        case_sensitive: 是否区分大小写
    
    Returns:
        list: 包含目标文本的图片文件名列表
    """
    matches = []
    
    if not case_sensitive:
        target_text = target_text.lower()
    
    for image_name, data in text_data.items():
        # 获取图片的原始文本
        raw_texts = data.get('raw_texts', [])
        
        # 如果不区分大小写，转换为小写
        if not case_sensitive:
            raw_texts = [text.lower() for text in raw_texts]
        
        # 检查是否包含目标文本
        if any(target_text in text for text in raw_texts):
            matches.append(image_name)
    
    return matches

def main():
    parser = argparse.ArgumentParser(description='快速查找包含指定文本的图片')
    parser.add_argument('--json', '-j', required=True, help='包含文本数据的JSON文件路径')
    parser.add_argument('--text', '-t', required=True, help='要查找的目标文本')
    parser.add_argument('--case-sensitive', '-c', action='store_true', help='是否区分大小写')
    
    args = parser.parse_args()
    
    # 加载文本数据
    text_data = load_text_data(args.json)
    
    # 查找匹配的图片
    matches = find_text_matches(text_data, args.text, args.case_sensitive)
    
    # 输出结果
    if matches:
        print('\n找到以下图片包含文本 "%s":' % args.text)
        for image_name in matches:
            print(image_name)
    else:
        print('\n未找到包含文本 "%s" 的图片' % args.text)

if __name__ == '__main__':
    main()