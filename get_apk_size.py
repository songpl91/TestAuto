import subprocess
import re

def get_apk_size_adb(package_name):
    """
    使用 ADB 获取已安装 APK 的大小。

    Args:
        package_name: 要查询的应用的包名。

    Returns:
        APK 的大小（以字节为单位），如果出错则返回 None。
    """
    try:
        # 1. 获取 APK 文件路径
        command_path = f"adb shell pm path {package_name}"
        process_path = subprocess.run(command_path, shell=True, capture_output=True, text=True, check=True)
        output_path = process_path.stdout.strip()

        # 提取 APK 文件路径
        match_path = re.search(r"package:(.*\.apk)", output_path)
        if not match_path:
            print(f"错误：无法找到包名 '{package_name}' 对应的 APK 文件路径。")
            return None
        apk_path = match_path.group(1)

        # 2. 获取文件大小
        command_size = f"adb shell ls -l {apk_path}"
        process_size = subprocess.run(command_size, shell=True, capture_output=True, text=True, check=True)
        output_size = process_size.stdout.strip()

        # 解析文件大小
        size_match = re.search(r"^\S+\s+\S+\s+\S+\s+(\d+)\s+", output_size)
        if not size_match:
            print(f"错误：无法解析 APK 文件 '{apk_path}' 的大小。")
            return None
        apk_size_bytes = int(size_match.group(1))
        return apk_size_bytes

    except subprocess.CalledProcessError as e:
        print(f"ADB 命令执行出错：{e}")
        print(f"错误输出：{e.stderr}")
        return None
    except FileNotFoundError:
        print("错误：未找到 ADB 工具。请确保 ADB 已添加到系统环境变量中。")
        return None
    except Exception as e:
        print(f"发生未知错误：{e}")
        return None

if __name__ == "__main__":
    package_name_to_query = input("请输入要查询的应用包名：")
    apk_size = get_apk_size_adb(package_name_to_query)

    if apk_size is not None:
        print(f"应用包名：{package_name_to_query}")
        print(f"APK 大小：{apk_size} 字节")

        # 可选：将字节转换为更易读的格式
        def format_size(size_bytes):
            if size_bytes < 1024:
                return f"{size_bytes} 字节"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.2f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.2f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

        formatted_size = format_size(apk_size)
        print(f"APK 大小（格式化后）：{formatted_size}")