#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import glob
import cv2
import numpy as np
import difflib
import json
import re
from collections import defaultdict

def get_similarity_ratio(str1, str2):
    """
    计算两个字符串的相似度
    
    Args:
        str1: 第一个字符串
        str2: 第二个字符串
        
    Returns:
        相似度比率，0.0到1.0之间
    """
    return difflib.SequenceMatcher(None, str1, str2).ratio()

def preprocess_image(image, method='default'):
    """
    对图像进行预处理以提高OCR识别率
    
    Args:
        image: PIL图像对象
        method: 预处理方法，可选值：'default', 'adaptive', 'otsu', 'canny'
        
    Returns:
        预处理后的PIL图像对象
    """
    # 转换为OpenCV格式进行处理
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # 转为灰度图
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # 根据不同方法处理图像
    if method == 'default':
        # 应用自适应阈值处理
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        
        # 降噪
        processed = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
        
    elif method == 'adaptive':
        # 使用不同参数的自适应阈值
        processed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                        cv2.THRESH_BINARY, 15, 8)
        
    elif method == 'otsu':
        # 使用Otsu's二值化
        _, processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
    elif method == 'canny':
        # 使用Canny边缘检测增强文本边缘
        processed = cv2.Canny(gray, 100, 200)
        # 膨胀操作使文字更粗
        kernel = np.ones((2, 2), np.uint8)
        processed = cv2.dilate(processed, kernel, iterations=1)
        # 反转颜色使文字为黑色
        processed = 255 - processed
    
    # 转回PIL格式
    processed_img = Image.fromarray(processed)
    
    # 增强对比度
    enhancer = ImageEnhance.Contrast(processed_img)
    processed_img = enhancer.enhance(2.0)
    
    # 锐化
    processed_img = processed_img.filter(ImageFilter.SHARPEN)
    
    # 调整亮度
    brightness_enhancer = ImageEnhance.Brightness(processed_img)
    processed_img = brightness_enhancer.enhance(1.2)
    
    return processed_img

def resize_for_ocr(image):
    """
    调整图像大小以提高OCR识别率
    
    Args:
        image: PIL图像对象
        
    Returns:
        调整大小后的PIL图像对象列表
    """
    resized_images = []
    
    # 原始图像
    resized_images.append(image)
    
    # 放大图像 - 对小文本有帮助
    width, height = image.size
    resized_images.append(image.resize((int(width * 1.5), int(height * 1.5)), Image.LANCZOS))
    
    # 缩小图像 - 有时对大文本有帮助
    resized_images.append(image.resize((int(width * 0.8), int(height * 0.8)), Image.LANCZOS))
    
    return resized_images

def extract_text_from_image(image_path):
    """
    从图像中提取所有可能的文本
    
    Args:
        image_path: 图像文件路径
        
    Returns:
        提取的文本列表和清理后的合并文本
    """
    try:
        # 打开图片
        img = Image.open(image_path)
        
        # 尝试不同的处理方法来提高识别率
        texts = []
        
        # 定义精简的OCR配置
        ocr_configs = [
            r'--oem 3 --psm 6',  # 假设文本是一个统一的文本块
            r'--oem 3 --psm 11',  # 稀疏文本，不限制检测
            r'-l eng --oem 3 --psm 6'  # 明确指定英语
        ]
        
        # 获取不同尺寸的图像
        resized_images = resize_for_ocr(img)
        
        # 对每个尺寸的图像应用不同的预处理方法
        for resized_img in resized_images:
            # 精简预处理方法
            processed_images = [
                resized_img,  # 原始图像
                preprocess_image(resized_img, 'default'),  # 默认预处理
                preprocess_image(resized_img, 'adaptive')  # 自适应处理
            ]
            
            # 对每个处理后的图像应用不同的OCR配置
            for processed_img in processed_images:
                for config in ocr_configs:
                    text = pytesseract.image_to_string(processed_img, config=config)
                    if text.strip():  # 只添加非空结果
                        texts.append(text)
        
        # 合并所有识别结果并转为小写
        all_text = ' '.join(texts).lower()
        
        # 清理文本，移除特殊字符和多余空格
        cleaned_text = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in all_text)
        cleaned_text = ' '.join(cleaned_text.split())
        
        return texts, cleaned_text
        
    except Exception as e:
        print(f"处理图片 {os.path.basename(image_path)} 时出错: {str(e)}")
        return [], ""

def extract_text_from_image_wrapper(args):
    """多线程处理的包装函数"""
    image_path, search_text = args
    file_name = os.path.basename(image_path)
    raw_texts, cleaned_text = extract_text_from_image(image_path)
    
    # 如果指定了搜索文本，使用更复杂的匹配逻辑检查是否匹配
    if search_text:
        # 确保搜索文本为小写，以便不区分大小写比较
        search_text_lower = search_text.lower()
        search_words = search_text_lower.split()
        
        # 检查是否包含搜索文本
        match_found = False
        
        # 使用与match_text_in_extracted_data相同的匹配逻辑
        # 简化版的匹配逻辑，只检查基本匹配
        if search_text_lower in cleaned_text.lower():
            match_found = True
        else:
            # 检查每个单词是否匹配
            for word in search_words:
                # 对于长词，使用模糊匹配
                if len(word) > 2:
                    for text_word in cleaned_text.lower().split():
                        # 计算相似度
                        similarity = get_similarity_ratio(word, text_word)
                        if similarity >= 0.7:  # 对于长词使用较高的阈值
                            match_found = True
                            break
                # 对于短词，使用更宽松的匹配
                else:
                    if word in cleaned_text.lower().split():
                        match_found = True
                        break
                
                # 如果找到匹配，跳出循环
                if match_found:
                    break
            
            # 额外检查原始文本中是否有匹配
            if not match_found:
                for raw_text in raw_texts:
                    raw_text = raw_text.lower()
                    if search_text_lower in raw_text:
                        match_found = True
                        break
        
        if match_found:
            return file_name, {
                "raw_texts": raw_texts,
                "cleaned_text": cleaned_text,
                "path": image_path,
                "matched": True
            }
    
    return file_name, {
        "raw_texts": raw_texts,
        "cleaned_text": cleaned_text,
        "path": image_path,
        "matched": False
    }

def extract_all_texts_from_folder(folder_path, search_text=None):
    """
    从文件夹中提取所有图片的文本
    
    Args:
        folder_path: 图片文件夹路径
        search_text: 要搜索的文本，如果提供则启用提前退出机制
        
    Returns:
        图片文件名到文本的映射字典
    """
    # 获取文件夹中所有PNG图片并按数字大小排序
    image_files = glob.glob(os.path.join(folder_path, "*.png"))
    image_files.sort(key=lambda x: float(os.path.splitext(os.path.basename(x))[0]))
    
    # 存储图片文本信息
    image_texts = {}
    
    print(f"正在从文件夹提取文本: {folder_path}")
    print(f"共找到 {len(image_files)} 张图片待处理...\n")
    
    # 顺序处理每个图片
    for i, image_path in enumerate(image_files):
        file_name = os.path.basename(image_path)
        result = extract_text_from_image_wrapper((image_path, search_text))[1]
        
        # 如果找到匹配且启用了提前退出，则立即返回该结果
        if search_text and result.get('matched', False):
            print(f"\n在图片 {file_name} 中找到匹配文本，提前结束处理")
            # 只返回包含匹配的图片，而不是所有已处理的图片
            return {file_name: result}
        
        image_texts[file_name] = result
        
        # 显示进度
        if (i + 1) % 5 == 0 or i == len(image_files) - 1:
            print(f"已处理: {i + 1}/{len(image_files)} 张图片")
    
    return image_texts

def save_extracted_texts(image_texts, output_file):
    """
    将提取的文本保存到JSON文件
    
    Args:
        image_texts: 图片文本字典
        output_file: 输出文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(image_texts, f, ensure_ascii=False, indent=2)
    
    print(f"\n文本提取结果已保存到: {output_file}")

def load_extracted_texts(input_file):
    """
    从JSON文件加载提取的文本
    
    Args:
        input_file: 输入文件路径
        
    Returns:
        图片文本字典
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def match_text_in_extracted_data(image_texts, search_text, partial_match=True):
    """
    在提取的文本数据中查找匹配的图片
    
    Args:
        image_texts: 图片文本字典
        search_text: 要查找的文字
        partial_match: 是否允许部分匹配
        
    Returns:
        包含匹配文字的图片文件名列表
    """
    # 确保搜索文本为小写，以便不区分大小写比较
    search_text = search_text.lower()
    search_words = search_text.split()
    
    # 存储匹配的图片
    matching_images = []
    
    print(f"\n查找文字: '{search_text}'")
    print(f"部分匹配模式: {'开启' if partial_match else '关闭'}")
    
    # 遍历所有图片的文本
    for file_name, text_data in image_texts.items():
        cleaned_text = text_data["cleaned_text"]
        raw_texts = text_data["raw_texts"]
        
        # 检查是否包含搜索文本
        match_found = False
        match_details = []
        
        # 增强的匹配算法
        if partial_match and search_words:
            # 部分匹配模式：只要有一个单词匹配即可
            for word in search_words:
                # 对于短词（如'ok'），使用更宽松的匹配
                if len(word) <= 2:
                    # 检查是否有完全匹配
                    if word in cleaned_text.split():
                        match_found = True
                        match_details.append(f"短词完全匹配: '{word}'")
                        break
                    
                    # 检查是否有近似匹配（允许一些OCR错误）
                    for text_word in cleaned_text.split():
                        # 使用模糊匹配计算相似度
                        similarity = get_similarity_ratio(word, text_word)
                        # 对于非常短的文本，使用较低的阈值
                        if similarity >= 0.5:
                            match_found = True
                            match_details.append(f"短词模糊匹配: '{text_word}' 与 '{word}' 的相似度为 {similarity:.2f}")
                            break
                        # 检查包含关系，特别是对于'ok'这样的短词
                        elif len(text_word) <= 5 and (word in text_word or text_word in word):
                            match_found = True
                            match_details.append(f"短词包含匹配: '{text_word}' 与 '{word}'")
                            break
                            
                    # 额外检查原始文本中是否有匹配
                    if not match_found:
                        for raw_text in raw_texts:
                            raw_text = raw_text.lower()
                            if word in raw_text:
                                match_found = True
                                match_details.append(f"原始文本匹配: '{word}'")
                                break
                else:  # 对于长词，使用更灵活的匹配
                    # 直接包含匹配
                    if word in cleaned_text:
                        match_found = True
                        match_details.append(f"长词包含匹配: '{word}'")
                        break
                        
                    # 检查是否有相似的词
                    for text_word in cleaned_text.split():
                        # 计算相似度
                        similarity = get_similarity_ratio(word, text_word)
                        if similarity >= 0.7:  # 对于长词使用较高的阈值
                            match_found = True
                            match_details.append(f"长词模糊匹配: '{text_word}' 与 '{word}' 的相似度为 {similarity:.2f}")
                            break
                            
                    # 检查是否有分词问题（如'welcome'被识别为'wel come'）
                    if not match_found and len(word) > 4:
                        # 尝试将长词分成两部分检查
                        for i in range(2, len(word)-1):
                            part1, part2 = word[:i], word[i:]
                            if part1 in cleaned_text and part2 in cleaned_text:
                                match_found = True
                                match_details.append(f"分词匹配: '{word}' 被分为 '{part1}' 和 '{part2}'")
                                break
                                
                    # 额外检查原始文本中是否有匹配
                    if not match_found:
                        for raw_text in raw_texts:
                            raw_text = raw_text.lower()
                            if word in raw_text:
                                match_found = True
                                match_details.append(f"原始文本匹配: '{word}'")
                                break
        else:
            # 完全匹配模式：必须包含完整的搜索文本
            # 对于短文本，尝试更灵活的匹配
            if len(search_text) <= 5:
                # 检查是否有完全匹配
                if search_text in cleaned_text:
                    match_found = True
                    match_details.append(f"完全匹配: '{search_text}'")
                else:
                    # 检查是否有近似匹配
                    words = cleaned_text.split()
                    for word in words:
                        # 使用模糊匹配计算相似度
                        similarity = get_similarity_ratio(search_text, word)
                        # 对于非常短的文本（如'ok'），使用较低的阈值
                        threshold = 0.6 if len(search_text) <= 2 else 0.75
                        
                        if similarity >= threshold:
                            match_found = True
                            match_details.append(f"模糊匹配: '{word}' 与 '{search_text}' 的相似度为 {similarity:.2f}")
                            break
                        # 额外检查包含关系
                        elif (search_text in word or word in search_text):
                            match_found = True
                            match_details.append(f"包含匹配: '{word}' 包含或被包含于 '{search_text}'")
                            break
                            
                    # 额外检查原始文本中是否有匹配
                    if not match_found:
                        for raw_text in raw_texts:
                            raw_text = raw_text.lower()
                            if search_text in raw_text:
                                match_found = True
                                match_details.append(f"原始文本匹配: '{search_text}'")
                                break
            else:
                # 对于长文本，使用常规匹配和相似度检查
                if search_text in cleaned_text:
                    match_found = True
                    match_details.append(f"完全匹配: '{search_text}'")
                else:
                    # 对长文本进行分段比较
                    text_segments = [cleaned_text[i:i+len(search_text)+5] for i in range(0, len(cleaned_text), len(search_text)//2) if i+len(search_text) <= len(cleaned_text)]
                    for segment in text_segments:
                        similarity = get_similarity_ratio(search_text, segment)
                        if similarity >= 0.8:  # 长文本使用更高的阈值
                            match_found = True
                            match_details.append(f"长文本模糊匹配: 相似度为 {similarity:.2f}")
                            break
                            
                    # 额外检查原始文本中是否有匹配
                    if not match_found:
                        for raw_text in raw_texts:
                            raw_text = raw_text.lower()
                            if search_text in raw_text:
                                match_found = True
                                match_details.append(f"原始文本匹配: '{search_text}'")
                                break
        
        if match_found:
            matching_images.append(file_name)
            print(f"找到匹配图片: {file_name}")
            print(f"匹配详情: {', '.join(match_details)}")
            print(f"识别的文字片段: {cleaned_text[:200].strip()}...\n")
    
    return matching_images

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='在图片中查找包含特定文字的图片（两阶段处理）')
    parser.add_argument('folder', help='图片文件夹路径')
    parser.add_argument('--text', help='要查找的文字')
    parser.add_argument('--exact', action='store_true', help='使用精确匹配模式（默认为部分匹配）')
    parser.add_argument('--save', action='store_true', help='保存匹配结果到文件')
    parser.add_argument('--extract-only', action='store_true', help='仅提取文本，不进行匹配')
    parser.add_argument('--use-cache', help='使用已提取的文本缓存文件')
    parser.add_argument('--output', help='输出文件名', default='extracted_texts.json')
    parser.add_argument('--startup-time-json', help='启动时长JSON文件名', default='startup_time.json')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    matching_images = []
    
    # 检查是否使用缓存
    if args.use_cache:
        print(f"从缓存加载提取的文本: {args.use_cache}")
        image_texts = load_extracted_texts(args.use_cache)
        
        # 如果只是提取文本，则结束
        if args.extract_only:
            return
            
        # 如果提供了搜索文本，则进行匹配
        if args.text:
            # 在提取的文本中查找匹配
            matching_images = match_text_in_extracted_data(image_texts, args.text, not args.exact)
    else:
        # 如果提供了搜索文本，extract_all_texts_from_folder会在找到第一个匹配时提前返回
        image_texts = extract_all_texts_from_folder(args.folder, args.text if args.text else None)
        
        # 在图片所在目录保存提取的文本
        output_file = os.path.join(args.folder, args.output)
        save_extracted_texts(image_texts, output_file)
        
        # 如果只是提取文本，则结束
        if args.extract_only:
            return
            
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
                
            # 保存结果到文件
            if args.save:
                result_file = f"search_result_{args.text.replace(' ', '_')}.txt"
                with open(result_file, 'w', encoding='utf-8') as f:
                    f.write(f"搜索文件夹: {args.folder}\n")
                    f.write(f"搜索文字: '{args.text}'\n\n")
                    f.write(f"找到 {len(matching_images)} 张匹配图片:\n")
                    for img in matching_images:
                        f.write(f"- {img}\n")
                print(f"\n结果已保存到文件: {result_file}")
                
            # 将匹配的图片文件名转换为启动时长格式并保存为JSON
            startup_times = {}
            # 只取第一个匹配的图片文件名作为启动时长
            for filename in matching_images:
                # 使用正则表达式提取文件名中的数字部分
                match = re.match(r'(\d+)\.png', filename)
                if match:
                    time_ms = int(match.group(1))
                    # 使用新格式的启动时长
                    startup_times = {"startupTime": f"{time_ms}ms"}
                    break
            
            # 保存为JSON文件到图片所在的文件夹中
            startup_time_file = os.path.join(args.folder, args.startup_time_json)
            with open(startup_time_file, 'w', encoding='utf-8') as f:
                json.dump(startup_times, f, ensure_ascii=False, indent=2)
            print(f"\n启动时长数据已保存到: {startup_time_file}")
        else:
            print(f"没有找到包含文字 '{args.text}' 的图片")
    else:
        print("\n未提供搜索文本，仅完成文本提取。使用 --text 参数指定要搜索的文本。")

if __name__ == "__main__":
    main()