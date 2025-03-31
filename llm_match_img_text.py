import argparse
import os
import ollama
import base64

def encode_image_to_base64(image_path):
    """将图片文件编码为 Base64 字符串。"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def find_matching_image(folder_path, target_string):
    """
    遍历指定文件夹中的图片，使用 Ollama 调用 gemma3:12b 进行图片识别，
    返回第一个包含匹配字符的文件名。

    Args:
        folder_path (str): 图片文件夹的路径。
        target_string (str): 要匹配的目标字符。

    Returns:
        str or None: 第一个匹配到的文件名，如果没有找到则返回 None。
    """
    if not os.path.isdir(folder_path):
        print(f"错误: 文件夹路径 '{folder_path}' 不存在。")
        return None

    image_extensions = ['.png', '.jpg', '.jpeg', '.gif']

    try:
        for filename in os.listdir(folder_path):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(folder_path, filename)
                try:
                    base64_image = encode_image_to_base64(image_path)
                    prompt = f"请识别这张图片中的文字。如果识别到文字，请判断是否包含 '{target_string}'。如果包含，请简洁地回答 '包含'，否则回答 '不包含'。"

                    response = ollama.chat(
                        model='gemma3:12b',
                        messages=[
                            {
                                'role': 'user',
                                'content': prompt,
                                'images': [base64_image],
                            },
                        ]
                    )
                    recognition_result = response['message']['content'].strip().lower()

                    if '包含' in recognition_result:
                        return filename
                    elif '不包含' in recognition_result:
                        continue # 继续检查下一个文件
                    else:
                        print(f"警告: 无法明确判断图片 '{filename}' 是否包含目标字符。LLM 回复: {recognition_result}")

                except FileNotFoundError:
                    print(f"错误: 图片文件 '{image_path}' 在处理过程中未找到。")
                except ollama.OllamaAPIError as e:
                    print(f"Ollama API 错误: {e}")
                    return None # 遇到 API 错误直接返回 None，可以根据需求调整
                except Exception as e:
                    print(f"处理图片 '{filename}' 时发生未知错误: {e}")

    except Exception as e:
        print(f"遍历文件夹时发生错误: {e}")

    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用 Ollama 调用 gemma3:12b 进行图片文字匹配。")
    parser.add_argument("folder_path", help="包含图片的文件夹路径")
    parser.add_argument("target_string", help="要匹配的目标字符")
    args = parser.parse_args()

    found_filename = find_matching_image(args.folder_path, args.target_string)

    if found_filename:
        print(found_filename)
    else:
        print(None)