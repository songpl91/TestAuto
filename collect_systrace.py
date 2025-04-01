import os
import sys
import subprocess
import argparse
import time
import glob
import re
import json
import platform
from datetime import datetime
from pathlib import Path
import random

def find_python27():
    """查找Python 2.7的路径"""
    # 常见的Python 2.7安装路径
    possible_paths = [
        'C:\\Python27\\python.exe',
        'C:\\Program Files\\Python27\\python.exe',
        'C:\\Program Files (x86)\\Python27\\python.exe',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # 从PATH环境变量中查找
    try:
        python27_path = subprocess.check_output(['where', 'python2.7.exe'], shell=True, text=True).strip().split('\n')[0]
        if os.path.exists(python27_path):
            return python27_path
    except:
        pass
    
    return None

def get_unity_android_sdk_path():
    """获取Unity Android SDK路径"""
    # Unity Android SDK的可能安装路径
    program_files = os.environ.get('ProgramFiles', '')
    program_files_x86 = os.environ.get('ProgramFiles(x86)', '')
    unity_sdk_paths = [
        # Unity Hub安装路径
        os.path.join(program_files, 'Unity', 'Hub', 'Editor', '*', 'Editor', 'Data', 'PlaybackEngines', 'AndroidPlayer', 'SDK'),
        os.path.join(program_files_x86, 'Unity', 'Hub', 'Editor', '*', 'Editor', 'Data', 'PlaybackEngines', 'AndroidPlayer', 'SDK'),
        # Unity直接安装路径
        os.path.join(program_files, 'Unity*', 'Editor', 'Data', 'PlaybackEngines', 'AndroidPlayer', 'SDK'),
        os.path.join(program_files_x86, 'Unity*', 'Editor', 'Data', 'PlaybackEngines', 'AndroidPlayer', 'SDK'),
        # 自定义安装路径
        os.path.join('C:', 'Program Files', 'Unity*', 'Editor', 'Data', 'PlaybackEngines', 'AndroidPlayer', 'SDK'),
        os.path.join('C:', 'Program Files (x86)', 'Unity*', 'Editor', 'Data', 'PlaybackEngines', 'AndroidPlayer', 'SDK')
    ]
    
    for base_path in unity_sdk_paths:
        try:
            # 使用glob模块来处理通配符
            paths = glob.glob(base_path)
            for path in paths:
                if os.path.exists(path):
                    # 检查多个可能的systrace.py位置
                    possible_paths = [
                        os.path.join(path, 'platform-tools', 'systrace.py'),
                        os.path.join(path, 'platform-tools', 'systrace', 'systrace.py'),
                        os.path.join(path, 'tools', 'systrace', 'systrace.py')
                    ]
                    for systrace_path in possible_paths:
                        if os.path.exists(systrace_path):
                            return path
        except Exception as e:
            print(f"查找Unity SDK路径时出错: {e}")
            continue
    return None

def get_systrace_path():
    """获取systrace.py的路径"""
    # 首先尝试从Unity Android SDK获取路径
    unity_sdk_path = get_unity_android_sdk_path()
    if unity_sdk_path:
        # 检查多个可能的systrace.py位置
        possible_paths = [
            os.path.join(unity_sdk_path, 'platform-tools', 'systrace.py'),
            os.path.join(unity_sdk_path, 'platform-tools', 'systrace', 'systrace.py'),
            os.path.join(unity_sdk_path, 'tools', 'systrace', 'systrace.py')
        ]
        for systrace_path in possible_paths:
            if os.path.exists(systrace_path):
                return systrace_path
    
    # 如果Unity SDK中没有找到，则尝试从环境变量获取
    for env_var in ['ANDROID_SDK_ROOT', 'ANDROID_HOME']:
        android_sdk_root = os.environ.get(env_var, '')
        if android_sdk_root:
            # 检查多个可能的systrace.py位置
            possible_paths = [
                os.path.join(android_sdk_root, 'platform-tools', 'systrace.py'),
                os.path.join(android_sdk_root, 'platform-tools', 'systrace', 'systrace.py'),
                os.path.join(android_sdk_root, 'tools', 'systrace', 'systrace.py')
            ]
            for systrace_path in possible_paths:
                if os.path.exists(systrace_path):
                    return systrace_path
    
    return None

def get_available_categories():
    """获取可用的跟踪类别"""
    systrace_path = get_systrace_path()
    if not systrace_path:
        print(f"错误: 未找到systrace.py，请确保已安装Unity并配置了Android SDK，或正确设置ANDROID_SDK_ROOT环境变量")
        sys.exit(1)
    
    try:
        python27_path = find_python27()
        if not python27_path:
            print("错误: 未找到Python 2.7，请确保已安装Python 2.7")
            sys.exit(1)
            
        result = subprocess.run([python27_path, systrace_path, '--list-categories'],
                               capture_output=True, text=True)
        print("可用的跟踪类别:")
        print(result.stdout)
    except Exception as e:
        print(f"获取跟踪类别时出错: {e}")
        sys.exit(1)

def check_python27_dependencies():
    """检查Python 2.7环境中的必要依赖项"""
    missing_deps = []
    
    # 检查win32con
    try:
        import win32con
    except ImportError:
        missing_deps.append("pywin32==228")
    
    # 检查six模块
    try:
        import six
    except ImportError:
        missing_deps.append("six")
    
    # 如果有缺失的依赖项，显示警告
    if missing_deps:
        print("警告: 未找到以下Python包，某些功能可能不可用:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\n请在Python 2.7环境中运行以下命令安装:")
        print(f"pip install {' '.join(missing_deps)}")
    
    # 即使缺少依赖项，也返回True以继续执行
    return True

def install_python27_dependencies(python27_path):
    """尝试自动安装Python 2.7所需的依赖项"""
    missing_deps = []
    
    # 检查win32con
    try:
        import win32con
    except ImportError:
        missing_deps.append("pywin32==228")
    
    # 检查six模块
    try:
        import six
    except ImportError:
        missing_deps.append("six")
    
    if missing_deps:
        print(f"尝试自动安装缺失的依赖项: {', '.join(missing_deps)}...")
        try:
            # 使用Python 2.7安装依赖项
            pip_cmd = [python27_path, '-m', 'pip', 'install'] + missing_deps
            result = subprocess.run(pip_cmd, check=True, capture_output=True, text=True)
            print("依赖项安装成功！")
            return True
        except subprocess.CalledProcessError as e:
            print(f"自动安装依赖项失败: {e}")
            print("请手动安装以下依赖项:")
            print(f"使用Python 2.7运行: pip install {' '.join(missing_deps)}")
            return False
        except Exception as e:
            print(f"安装依赖项时发生错误: {e}")
            return False
    return True

def check_and_install_pywin32(python27_path):
    """检查并安装pywin32模块"""
    print("检查Python 2.7环境中的pywin32模块...")
    
    # 检查是否已安装pywin32模块
    check_script = """
try:
    import win32con
    print("1")
except ImportError:
    print("0")
"""
    try:
        result = subprocess.run(
            [python27_path, "-c", check_script],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stdout.strip() == "0":
            print("未找到pywin32模块，正在尝试安装...")
            try:
                pip_cmd = [python27_path, "-m", "pip", "install", "pywin32==228"]
                install_result = subprocess.run(pip_cmd, check=True, capture_output=True, text=True)
                print("pywin32模块安装成功！")
                return True
            except Exception as e:
                print(f"安装pywin32模块失败: {e}")
                print("请手动运行以下命令安装pywin32模块:")
                print(f"{python27_path} -m pip install pywin32==228")
                return False
        else:
            print("已安装pywin32模块")
            return True
    except Exception as e:
        print(f"检查pywin32模块时出错: {e}")
        return False

def check_and_install_six(python27_path):
    """检查并安装six模块"""
    print("检查Python 2.7环境中的six模块...")
    
    # 检查是否已安装six模块
    check_script = """
try:
    import six
    print("1")
except ImportError:
    print("0")
"""
    try:
        result = subprocess.run(
            [python27_path, "-c", check_script],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stdout.strip() == "0":
            print("未找到six模块，正在尝试安装...")
            try:
                pip_cmd = [python27_path, "-m", "pip", "install", "six"]
                install_result = subprocess.run(pip_cmd, check=True, capture_output=True, text=True)
                print("six模块安装成功！")
                return True
            except Exception as e:
                print(f"安装six模块失败: {e}")
                print("请手动运行以下命令安装six模块:")
                print(f"{python27_path} -m pip install six")
                return False
        else:
            print("已安装six模块")
            return True
    except Exception as e:
        print(f"检查six模块时出错: {e}")
        return False

def collect_trace(package_name, duration=10, categories=None):
    """收集应用的性能跟踪数据"""
    print(f"正在收集{package_name}的Systrace数据...")
    
    try:
        # 确保设备已连接
        try:
            check_cmd = ['adb', 'devices']
            device_result = subprocess.run(check_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            devices = device_result.stdout.strip().split('\n')
            if len(devices) <= 1:
                print("错误: 未检测到连接的设备。")
                return None
            else:
                print(f"已连接设备: {devices[1:]}") 
        except Exception as e:
            print(f"检查设备连接时出错: {e}")
            return None
        
        # 启动应用以确保它正在运行
        print("确保应用正在运行...")
        main_activity = get_main_activity(package_name)
        start_cmd = [
            'adb', 'shell', 'am', 'start', '-n', main_activity
        ]
        
        # 给应用启动一些时间
        try:
            subprocess.run(start_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            print(f"已启动应用 {main_activity}，等待3秒钟稳定...")
            time.sleep(3)
            
            # 尝试触发一些UI交互，确保应用有活动
            print("触发应用界面活动，以确保有数据可收集...")
            try:
                # 点击屏幕中心
                subprocess.run(['adb', 'shell', 'input', 'tap', '540', '1000'], capture_output=True)
                time.sleep(0.5)
                
                # 上下滑动
                subprocess.run(['adb', 'shell', 'input', 'swipe', '540', '1200', '540', '800', '300'], 
                              capture_output=True)
            except Exception as e:
                print(f"触发界面活动时出错: {e}，将继续测试")
        except Exception as e:
            print(f"启动应用时出错: {e}")
            # 继续执行，因为应用可能已经在运行
            
        # 设置默认类别
        if not categories:
            categories = 'gfx,view,sched,freq,idle,app'
            
        # 准备创建结果文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'systrace_{package_name}_{timestamp}.html'
        
        # 尝试使用不同的方法收集systrace数据
        methods = ["systrace_py", "atrace_app", "perfetto", "simpleperf"]
        success = False
        
        for method in methods:
            if success:
                break
                
            print(f"尝试使用{method}方法收集性能数据...")
            
            if method == "systrace_py":
                # 尝试使用systrace.py
                success = _try_systrace_py(package_name, duration, categories, output_file)
            elif method == "atrace_app":
                # 尝试使用adb shell atrace直接收集
                success = _try_atrace_app(package_name, duration, categories, output_file)
            elif method == "perfetto":
                # 尝试使用perfetto收集
                success = _try_perfetto(package_name, duration, categories, output_file)
            elif method == "simpleperf":
                # 尝试使用simpleperf收集
                success = _try_simpleperf(package_name, duration, output_file)
        
        if success:
            return output_file
        else:
            # 所有方法都失败了，生成一个空结果文件和报告
            print("警告: 所有性能数据收集方法都失败了")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n<html>\n<head>\n")
                f.write("<title>Performance Data Collection Failed</title>\n")
                f.write("<style>pre { white-space: pre-wrap; word-wrap: break-word; }</style>\n")
                f.write("</head>\n<body>\n")
                f.write("<h1>性能数据收集失败</h1>\n")
                f.write("<p>尝试了多种方法，但都无法收集到性能数据。可能的原因:</p>\n")
                f.write("<ul>\n")
                f.write("<li>设备权限问题或开发者选项未启用</li>\n")
                f.write("<li>Android版本与收集工具不兼容</li>\n")
                f.write("<li>应用使用了特殊的渲染或性能优化机制</li>\n")
                f.write("<li>设备本身限制了性能数据收集</li>\n")
                f.write("</ul>\n")
                f.write("</body>\n</html>")
                
            print(f"已创建失败报告: {output_file}")
            return None
            
    except Exception as e:
        print(f"收集Systrace数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def _try_systrace_py(package_name, duration, categories, output_file):
    """尝试使用systrace.py收集数据"""
    try:
        # 确定systrace.py的位置
        android_sdk = None
        for env_var in ['ANDROID_HOME', 'ANDROID_SDK_ROOT']:
            if os.environ.get(env_var):
                android_sdk = os.environ.get(env_var)
                break
                
        if not android_sdk:
            print("警告: 未找到Android SDK环境变量。尝试查找系统中的platform-tools目录...")
            # 尝试一些常见位置
            common_locations = [
                os.path.expanduser("~/Android/Sdk"),
                "C:\\Android\\Sdk",
                "D:\\Android\\Sdk",
                os.path.expanduser("~/Library/Android/sdk"),
                "/Users/Shared/Android/Sdk",
                "/opt/android-sdk",
                "/usr/local/android-sdk"
            ]
            for location in common_locations:
                if os.path.exists(location):
                    android_sdk = location
                    print(f"找到Android SDK位置: {android_sdk}")
                    break
                    
        if not android_sdk:
            print("错误: 无法找到Android SDK。请设置ANDROID_HOME或ANDROID_SDK_ROOT环境变量。")
            return False
            
        # 尝试找到systrace.py
        potential_paths = [
            os.path.join(android_sdk, "platform-tools", "systrace", "systrace.py"),
            os.path.join(android_sdk, "tools", "systrace", "systrace.py"),
            os.path.join(android_sdk, "platform-tools", "systrace"),
            os.path.join(android_sdk, "platform-tools", "systrace.py")
        ]
        
        systrace_path = None
        for path in potential_paths:
            if os.path.exists(path):
                systrace_path = path
                break
                
        if not systrace_path:
            print("警告: 无法找到systrace.py。")
            return False
        
        # 准备命令
        cmd = [
            'python', systrace_path,
            '-a', package_name,
            '-b', '16384',
            '--time', str(duration),
            '-o', output_file
        ]
        
        # 添加类别（确保是字符串而非列表）
        if isinstance(categories, list):
            cmd.append(','.join(categories))
        else:
            cmd.append(categories)
        
        print(f"执行命令: {' '.join(cmd)}")
        print(f"收集数据中，将持续{duration}秒...")
        
        # 设置环境变量以解决可能的编码问题
        my_env = os.environ.copy()
        my_env['PYTHONIOENCODING'] = 'utf-8'
        
        # 执行命令
        result = subprocess.run(
            cmd,
            env=my_env,
            capture_output=True,
            check=False
        )
        
        # 检查文件是否生成
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"Systrace数据已保存到: {output_file}")
            return True
        else:
            print(f"Systrace.py执行完成但未生成有效文件")
            return False
            
    except Exception as e:
        print(f"使用systrace.py收集数据出错: {e}")
        return False

def _try_atrace_app(package_name, duration, categories, output_file):
    """尝试使用adb shell atrace直接收集数据"""
    try:
        # 确保categories是字符串
        cat_str = categories
        if isinstance(categories, list):
            cat_str = ' '.join(categories)
            
        # 检查atrace是否可用
        check_cmd = ['adb', 'shell', 'which', 'atrace']
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if check_result.returncode != 0 or not check_result.stdout.strip():
            print("警告: 设备上未找到atrace命令")
            return False
            
        print("使用atrace命令收集数据...")
        
        # 获取设备支持的category列表
        check_categories_cmd = ['adb', 'shell', 'atrace', '--list_categories']
        try:
            categories_result = subprocess.run(check_categories_cmd, capture_output=True, text=True, timeout=5)
            supported_categories = []
            
            if categories_result.returncode == 0:
                for line in categories_result.stdout.split('\n'):
                    if ':' in line:
                        cat = line.split(':')[0].strip()
                        if cat:
                            supported_categories.append(cat)
                print(f"设备支持的category: {', '.join(supported_categories)}")
            
            # 如果没有获取到支持的类别，使用一些常见的安全类别
            if not supported_categories:
                supported_categories = ['gfx', 'view', 'input', 'sched', 'freq']
                
            # 过滤掉不支持的类别
            filtered_categories = []
            for cat in cat_str.replace(',', ' ').split():
                if cat in supported_categories:
                    filtered_categories.append(cat)
                else:
                    print(f"注意: 跳过不支持的category: {cat}")
                    
            if not filtered_categories:
                # 如果所有请求的类别都不支持，使用一些基本类别
                filtered_categories = ['gfx', 'view']
                filtered_categories = [c for c in filtered_categories if c in supported_categories]
                if not filtered_categories:
                    filtered_categories = [supported_categories[0]] if supported_categories else []
                    
            if not filtered_categories:
                print("错误: 无法找到设备支持的任何跟踪类别")
                return False
                
        except Exception as e:
            print(f"获取支持的category失败: {e}")
            # 使用保守的默认类别
            filtered_categories = ['gfx', 'view']
        
        # 清理之前的跟踪
        subprocess.run(['adb', 'shell', 'atrace', '--async_stop'], capture_output=True)
        time.sleep(1)
        
        # 开始异步跟踪
        atrace_cmd = [
            'adb', 'shell', 'atrace', 
            '--async_start', 
            '-a', package_name, 
            '-b', '16384'
        ]
        
        # 添加-c参数和过滤后的类别
        if filtered_categories:
            atrace_cmd.append('-c')
            atrace_cmd.extend(filtered_categories)
        
        print(f"执行命令: {' '.join(atrace_cmd)}")
        subprocess.run(atrace_cmd, check=True)
        
        # 等待收集数据
        print(f"正在收集数据，将持续{duration}秒...")
        time.sleep(duration)
        
        # 停止跟踪并收集数据
        print("正在读取跟踪数据...")
        atrace_stop_cmd = [
            'adb', 'shell', 'atrace', '--async_dump'
        ]
        atrace_result = subprocess.run(
            atrace_stop_cmd, 
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 保存结果
        if atrace_result.stdout:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n<html>\n<head>\n")
                f.write("<title>Atrace Results</title>\n")
                f.write("<style>pre { white-space: pre-wrap; word-wrap: break-word; }</style>\n")
                f.write("</head>\n<body>\n")
                f.write("<h1>Atrace Performance Data</h1>\n")
                f.write("<pre>\n")
                f.write(atrace_result.stdout)
                f.write("\n</pre>\n</body>\n</html>")
                
            print(f"Atrace数据已保存到: {output_file}")
            return True
        else:
            print("Atrace未返回任何数据")
            return False
            
    except Exception as e:
        print(f"使用atrace收集数据出错: {e}")
        return False

def _try_perfetto(package_name, duration, categories, output_file):
    """尝试使用perfetto收集数据"""
    try:
        # 检查perfetto是否可用
        check_cmd = ['adb', 'shell', 'which', 'perfetto']
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if check_result.returncode != 0 or not check_result.stdout.strip():
            print("警告: 设备上未找到perfetto命令")
            return False
            
        print("使用perfetto命令收集数据...")
        
        # 创建临时配置文件
        config = f"""buffers {{
          size_kb: 63488
          fill_policy: RING_BUFFER
        }}
        data_sources {{
          config {{
            name: "linux.ftrace"
            ftrace_config {{
              ftrace_events: "sched/sched_switch"
              ftrace_events: "power/suspend_resume"
              ftrace_events: "sched/sched_wakeup"
              ftrace_events: "sched/sched_wakeup_new"
              ftrace_events: "sched/sched_waking"
              ftrace_events: "sched/sched_process_exit"
              ftrace_events: "sched/sched_process_free"
              ftrace_events: "task/task_newtask"
              ftrace_events: "task/task_rename"
              ftrace_events: "sched/sched_blocked_reason"
              ftrace_events: "sched/sched_cpu_hotplug"
              buffer_size_kb: 2048
              drain_period_ms: 250
            }}
          }}
        }}
        duration_ms: {duration * 1000}
        """
        
        # 将配置写入临时文件
        config_file = 'perfetto_config.txt'
        with open(config_file, 'w') as f:
            f.write(config)
            
        # 将配置推送到设备
        push_cmd = ['adb', 'push', config_file, '/data/local/tmp/']
        subprocess.run(push_cmd, check=True)
        
        # 检查perfetto版本和支持的参数
        version_cmd = ['adb', 'shell', 'perfetto', '--version']
        try:
            version_result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=2)
            has_txt_option = False  # 默认假设不支持--txt选项
        except:
            # 如果版本检查失败，假设是较新版本
            has_txt_option = False
        
        # 运行perfetto (不使用--txt选项，因为许多设备不支持)
        perfetto_cmd = [
            'adb', 'shell', 'perfetto',
            '-c', '/data/local/tmp/perfetto_config.txt', 
            '-o', '/data/local/tmp/trace.perfetto'
        ]
        
        print(f"执行命令: {' '.join(perfetto_cmd)}")
        print(f"正在收集数据，将持续{duration}秒...")
        
        # 执行perfetto命令
        subprocess.run(perfetto_cmd, check=True, timeout=duration + 10)
        
        # 将结果拉取到本地
        trace_file = 'trace.perfetto'
        pull_cmd = ['adb', 'pull', '/data/local/tmp/trace.perfetto', trace_file]
        subprocess.run(pull_cmd, check=True)
        
        # 检查文件是否成功生成
        if os.path.exists(trace_file) and os.path.getsize(trace_file) > 0:
            # 简单转换为HTML格式
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n<html>\n<head>\n")
                f.write("<title>Perfetto Results</title>\n")
                f.write("<style>body { font-family: monospace; }</style>\n")
                f.write("</head>\n<body>\n")
                f.write("<h1>Perfetto Performance Data</h1>\n")
                f.write("<p>收集到的原始Perfetto数据。请使用Perfetto UI（https://ui.perfetto.dev/）打开trace.perfetto文件进行详细分析。</p>\n")
                f.write("<p>原始Perfetto文件: " + trace_file + "</p>\n")
                f.write("</body>\n</html>")
            
            print(f"Perfetto数据已保存到: {trace_file}")
            print(f"HTML报告已保存到: {output_file}")
            return True
        else:
            print("Perfetto未能生成有效的跟踪文件")
            return False
            
    except Exception as e:
        print(f"使用perfetto收集数据出错: {e}")
        return False
        
def _try_simpleperf(package_name, duration, output_file):
    """尝试使用simpleperf收集CPU分析数据"""
    try:
        # 检查simpleperf是否可用
        check_cmd = ['adb', 'shell', 'which', 'simpleperf']
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if check_result.returncode != 0 or not check_result.stdout.strip():
            print("警告: 设备上未找到simpleperf命令")
            return False
            
        print("使用simpleperf命令收集CPU性能数据...")
        
        # 获取应用进程ID
        pid_cmd = ['adb', 'shell', 'pidof', package_name]
        pid_result = subprocess.run(pid_cmd, capture_output=True, text=True)
        
        if pid_result.returncode != 0 or not pid_result.stdout.strip():
            print("警告: 无法获取应用进程ID，尝试通过ps命令获取")
            
            # 备用方式获取PID
            ps_cmd = ['adb', 'shell', 'ps', '|', 'grep', package_name]
            ps_result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
            
            if not ps_result.stdout.strip():
                print("错误: 应用进程未运行")
                return False
                
            # 解析PS输出获取PID
            pid = None
            for line in ps_result.stdout.split('\n'):
                if package_name in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = parts[1]
                        break
            
            if not pid:
                print("错误: 无法从PS输出中获取PID")
                return False
        else:
            pid = pid_result.stdout.strip()
            
        print(f"应用进程ID: {pid}")
        
        # 执行simpleperf
        simpleperf_cmd = [
            'adb', 'shell',
            'simpleperf', 'record',
            '-p', pid,
            '--duration', str(duration),
            '-o', '/data/local/tmp/perf.data',
            '--call-graph', 'fp',
            '--app', package_name
        ]
        
        print(f"执行命令: {' '.join(simpleperf_cmd)}")
        print(f"正在收集CPU性能数据，将持续{duration}秒...")
        
        # 执行simpleperf命令
        subprocess.run(simpleperf_cmd, check=True, timeout=duration + 5)
        
        # 将结果拉取到本地
        perf_file = 'perf.data'
        pull_cmd = ['adb', 'pull', '/data/local/tmp/perf.data', perf_file]
        subprocess.run(pull_cmd, check=True)
        
        # 生成报告
        report_cmd = ['adb', 'shell', 'simpleperf', 'report', '-i', '/data/local/tmp/perf.data', '--sort', 'comm,pid,tid,symbol']
        report_result = subprocess.run(report_cmd, capture_output=True, text=True)
        
        # 检查文件是否成功生成
        if os.path.exists(perf_file) and os.path.getsize(perf_file) > 0:
            # 生成HTML报告
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n<html>\n<head>\n")
                f.write("<title>Simpleperf CPU Profile</title>\n")
                f.write("<style>pre { white-space: pre-wrap; word-wrap: break-word; }</style>\n")
                f.write("</head>\n<body>\n")
                f.write("<h1>CPU性能分析报告</h1>\n")
                f.write("<p>原始性能数据文件: " + perf_file + "</p>\n")
                f.write("<pre>\n")
                f.write(report_result.stdout)
                f.write("\n</pre>\n</body>\n</html>")
            
            print(f"CPU性能分析数据已保存到: {perf_file}")
            print(f"报告已保存到: {output_file}")
            return True
        else:
            print("Simpleperf未能生成有效的性能数据文件")
            return False
            
    except Exception as e:
        print(f"使用simpleperf收集数据出错: {e}")
        return False

def get_fps(package_name, duration=10):
    """获取应用的帧率信息"""
    print(f"正在获取{package_name}的帧率信息...")
    
    try:
        # 先确保应用已经启动并处于前台
        main_activity = get_main_activity(package_name)
        start_cmd = [
            'adb', 'shell', 'am', 'start', '-n', main_activity
        ]
        
        try:
            subprocess.run(start_cmd, capture_output=True, text=True)
            print(f"已启动应用: {main_activity}，等待应用稳定...")
            time.sleep(5)  # 给应用足够的启动时间
            
            # 尝试触发更多UI交互，确保有渲染发生
            print("尝试触发应用界面活动...")
            for _ in range(3):  # 多次尝试以确保有活动
                try:
                    # 点击屏幕中心
                    subprocess.run(['adb', 'shell', 'input', 'tap', '540', '1000'], 
                                  capture_output=True)
                    time.sleep(0.5)
                    
                    # 上下滑动
                    subprocess.run(['adb', 'shell', 'input', 'swipe', '540', '1200', '540', '800', '300'],
                                  capture_output=True)
                    time.sleep(0.5)
                    
                    # 左右滑动
                    subprocess.run(['adb', 'shell', 'input', 'swipe', '300', '1000', '800', '1000', '300'],
                                  capture_output=True)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"触发UI活动时出错: {e}，继续测试")
        except Exception as e:
            print(f"启动应用时出错: {e}")
        
        # 重置计数器
        reset_cmd = [
            'adb', 'shell', 'dumpsys', 'gfxinfo', package_name, 'reset'
        ]
        print("重置图形统计信息...")
        subprocess.run(reset_cmd, capture_output=True, text=True)
        
        # 检测设备是否支持gfxinfo
        precheck_cmd = ['adb', 'shell', 'dumpsys', 'gfxinfo', package_name]
        precheck_result = subprocess.run(precheck_cmd, capture_output=True, text=True)
        supports_gfxinfo = True
        
        if "Couldn't find package:" in precheck_result.stdout or "No process found for:" in precheck_result.stdout:
            print("警告: 设备不支持gfxinfo或无法找到应用进程")
            supports_gfxinfo = False
        
        # 准备收集数据
        if supports_gfxinfo:
            # 确保在收集过程中应用保持活动
            segments = 3
            segment_duration = max(3, duration // segments)  # 至少3秒一段
            
            for i in range(segments):
                print(f"帧率收集进度: {i+1}/{segments}...")
                
                # 每个片段都模拟一些用户操作
                try:
                    # 随机点击屏幕
                    x = random.randint(300, 800)
                    y = random.randint(800, 1200)
                    subprocess.run(['adb', 'shell', 'input', 'tap', str(x), str(y)], 
                                  capture_output=True)
                    time.sleep(0.7)
                    
                    # 随机滑动
                    x1 = random.randint(300, 800)
                    y1 = random.randint(800, 1200)
                    x2 = random.randint(300, 800)
                    y2 = random.randint(800, 1200)
                    subprocess.run(['adb', 'shell', 'input', 'swipe', 
                                   str(x1), str(y1), str(x2), str(y2), '300'],
                                  capture_output=True)
                except Exception as e:
                    print(f"模拟操作时出错: {e}")
                
                # 等待指定时间
                time.sleep(segment_duration - 1)  # 减去操作时间
                
            print("收集完成，正在获取帧率数据...")
            
            # 收集帧率数据
            fps_cmd = [
                'adb', 'shell', 'dumpsys', 'gfxinfo', package_name
            ]
            fps_result = subprocess.run(fps_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            fps_data = fps_result.stdout
            
            # 检查是否有有效的帧数据
            total_frames = 0
            janky_frames = 0
            
            # 尝试解析标准帧数据格式
            if "Total frames rendered" in fps_data:
                for line in fps_data.split('\n'):
                    if "Total frames rendered:" in line:
                        try:
                            total_frames = int(line.split(':')[1].strip())
                        except:
                            pass
                    if "Janky frames:" in line:
                        try:
                            janky_part = line.split(':')[1].strip()
                            if '(' in janky_part:
                                janky_frames = int(janky_part.split('(')[0].strip())
                        except:
                            pass
            
            # 为Unity应用检查替代方法
            if total_frames == 0 and "Unity" in fps_data:
                print("检测到Unity应用，尝试使用替代方法收集帧率...")
                
                # 尝试第二种方法 - Surfaceflinger
                try:
                    sf_cmd = ['adb', 'shell', 'dumpsys', 'SurfaceFlinger', '--latency']
                    sf_result = subprocess.run(sf_cmd, capture_output=True, text=True)
                    
                    # 简单分析以估计帧率
                    lines = sf_result.stdout.strip().split('\n')
                    if len(lines) > 10:  # 有足够的数据行
                        # 非常简单的估计 - 实际项目中应该使用更复杂的算法
                        total_frames = len(lines) - 1  # 减去标题行
                        fps_data += f"\n\n估计的Unity帧数 (从SurfaceFlinger获取): {total_frames}"
                except Exception as e:
                    print(f"SurfaceFlinger分析出错: {e}")
            
            # 如果仍然没有帧数据，尝试备用方法
            if total_frames == 0:
                print("警告: 未检测到任何帧，尝试备用方法...")
                
                # 备用方法 - 重新激活应用并尝试更积极的交互
                try:
                    # 重新激活并重置
                    subprocess.run(start_cmd, capture_output=True, text=True)
                    print("使用备用方法收集帧率，激活应用中...")
                    subprocess.run(reset_cmd, capture_output=True, text=True)
                    time.sleep(1)
                    
                    # 更激进的交互模式
                    for _ in range(10):
                        # 随机点击
                        x = random.randint(200, 900)
                        y = random.randint(600, 1400)
                        subprocess.run(['adb', 'shell', 'input', 'tap', str(x), str(y)], 
                                      capture_output=True)
                        time.sleep(0.3)
                        
                        # 随机滑动
                        x1 = random.randint(200, 900)
                        y1 = random.randint(600, 1400)
                        x2 = random.randint(200, 900)
                        y2 = random.randint(600, 1400)
                        subprocess.run(['adb', 'shell', 'input', 'swipe', 
                                       str(x1), str(y1), str(x2), str(y2), '200'],
                                      capture_output=True)
                        time.sleep(0.3)
                    
                    # 再次收集
                    fps_result = subprocess.run(fps_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                    backup_fps_data = fps_result.stdout
                    
                    # 再次尝试解析
                    if "Total frames rendered" in backup_fps_data:
                        for line in backup_fps_data.split('\n'):
                            if "Total frames rendered:" in line:
                                try:
                                    total_frames = int(line.split(':')[1].strip())
                                except:
                                    pass
                            if "Janky frames:" in line:
                                try:
                                    janky_part = line.split(':')[1].strip()
                                    if '(' in janky_part:
                                        janky_frames = int(janky_part.split('(')[0].strip())
                                except:
                                    pass
                    
                    fps_data = backup_fps_data
                    
                except Exception as e:
                    print(f"备用方法出错: {e}")
            
            # 为Unity或其他特殊应用尝试第三种方法 - UI绘制分析
            if total_frames == 0:
                try:
                    # 尝试通过View绘制统计分析帧率
                    view_cmd = ['adb', 'shell', 'dumpsys', 'activity', package_name]
                    view_result = subprocess.run(view_cmd, capture_output=True, text=True)
                    
                    # 模拟一个总帧数值 - 这是为了生成报告而做的
                    # 实际上，这应该基于更复杂的分析确定真实帧率
                    if "View hierarchy:" in view_result.stdout:
                        fps_data += "\n\n检测到应用UI视图活动，但无法获取准确帧率。"
                        fps_data += "\n应用可能使用特殊渲染技术，标准Android帧率测量不适用。"
                except Exception as e:
                    print(f"UI分析出错: {e}")
            
            # 保存帧率数据
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            fps_file = f'fps_data_{package_name}_{timestamp}.txt'
            with open(fps_file, 'w', encoding='utf-8') as f:
                f.write(fps_data)
            
            # 保存framestats数据 (如果可用)
            try:
                framestats_cmd = [
                    'adb', 'shell', 'dumpsys', 'gfxinfo', package_name, 'framestats'
                ]
                framestats_result = subprocess.run(framestats_cmd, capture_output=True, text=True)
                
                if framestats_result.stdout.strip() and len(framestats_result.stdout) > 50:
                    framestats_file = f'framestats_{package_name}_{timestamp}.txt'
                    with open(framestats_file, 'w', encoding='utf-8') as f:
                        f.write(framestats_result.stdout)
                    print(f"帧统计数据已保存到: {framestats_file}")
            except Exception as e:
                print(f"保存framestats出错: {e}")
            
            # 分析和总结
            if total_frames > 0:
                jank_percent = (janky_frames / total_frames) * 100 if total_frames > 0 else 0
                print(f"FPS统计:")
                print(f"总帧数: {total_frames}")
                print(f"卡顿帧: {janky_frames} ({jank_percent:.1f}%)")
                
                # 计算估计的FPS (大致估计)
                estimated_fps = total_frames / duration
                print(f"估计帧率: {estimated_fps:.1f} FPS")
            else:
                if "Unity" in fps_data:
                    print("FPS统计:")
                    print("Unity应用帧率无法通过标准Android API获取")
                    print("建议使用Unity分析工具或第三方工具获取准确帧率")
                else:
                    print("FPS统计:")
                    print("备用方法也未能收集到帧数据，应用可能没有活跃的图形绘制")
                    print("或者使用了自定义渲染方式，无法被系统统计工具捕获")
            
            print(f"详细的图形信息已保存到: {fps_file}")
            
            return (total_frames, janky_frames, fps_file)
        else:
            # 设备不支持gfxinfo的情况
            print("设备不支持gfxinfo或应用未运行")
            
            # 创建一个简单的报告
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            fps_file = f'fps_data_{package_name}_{timestamp}.txt'
            with open(fps_file, 'w', encoding='utf-8') as f:
                f.write("设备不支持gfxinfo或应用未运行\n")
                f.write("无法收集帧率数据\n")
            
            print(f"详细信息已保存到: {fps_file}")
            return (0, 0, fps_file)
            
    except Exception as e:
        print(f"获取帧率信息时出错: {e}")
        import traceback
        traceback.print_exc()
        
        # 创建错误报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fps_file = f'fps_data_{package_name}_{timestamp}.txt'
        with open(fps_file, 'w', encoding='utf-8') as f:
            f.write(f"获取帧率信息时出错: {e}\n")
            f.write(traceback.format_exc())
        
        print(f"错误信息已保存到: {fps_file}")
        return (0, 0, fps_file)

def get_main_activity(package_name):
    """获取应用的主Activity"""
    try:
        # 方法1: 使用cmd package resolve-activity
        cmd = f'adb shell cmd package resolve-activity --brief {package_name} | tail -n 1'
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            universal_newlines=True,
            encoding='utf-8',
            errors='replace',
            check=True, 
            shell=True
        )
        
        activity = result.stdout.strip()
        # 确保不要在activity路径中重复包名
        if activity and '/' in activity:
            # 检查是否重复了包名路径
            if activity.startswith(f"{package_name}/{package_name}"):
                # 修复重复的包名问题
                correct_activity = activity.replace(f"{package_name}/{package_name}/", f"{package_name}/")
                print(f"修复了重复的包名路径: {activity} -> {correct_activity}")
                return correct_activity
            return activity
        
        # 方法2: 使用dumpsys package
        cmd2 = f'adb shell "dumpsys package {package_name} | grep -A 1 android.intent.action.MAIN | grep Activity"'
        result = subprocess.run(
            cmd2, 
            capture_output=True, 
            universal_newlines=True,
            encoding='utf-8',
            errors='replace',
            check=True, 
            shell=True
        )
        
        activity_line = result.stdout.strip()
        if activity_line:
            activity_name = activity_line.split()[1]
            # 确保活动名称格式正确
            if '/' not in activity_name:
                activity_name = f"{package_name}/{activity_name}"
            # 检查是否重复了包名路径
            if activity_name.startswith(f"{package_name}/{package_name}"):
                # 修复重复的包名问题
                correct_activity = activity_name.replace(f"{package_name}/{package_name}/", f"{package_name}/")
                print(f"修复了重复的包名路径: {activity_name} -> {correct_activity}")
                return correct_activity
            return activity_name
    except Exception as e:
        print(f"无法获取主Activity: {e}")
    
    # 返回默认格式的Activity名称，确保格式正确
    default_activity = f"{package_name}/com.unity3d.player.UnityPlayerActivity"
    print(f"使用默认Activity: {default_activity}")
    return default_activity

def get_startup_metrics(package_name, max_retries=3):
    """获取应用的启动时间指标"""
    print(f"正在获取{package_name}的启动指标...")
    
    try:
        # 确保设备已连接
        try:
            check_cmd = ['adb', 'devices']
            device_result = subprocess.run(check_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if len(device_result.stdout.strip().split('\n')) <= 1:
                print("错误: 未检测到连接的设备。")
                return None
        except Exception as e:
            print(f"检查设备连接时出错: {e}")
            return None
            
        # 强制停止应用，确保是冷启动
        print(f"强制停止应用 {package_name}...")
        stop_cmd = ['adb', 'shell', 'am', 'force-stop', package_name]
        subprocess.run(stop_cmd, capture_output=True)
        
        # 清除应用缓存以确保完全冷启动
        print("清除应用缓存...")
        clear_cmd = ['adb', 'shell', 'pm', 'clear', package_name]
        subprocess.run(clear_cmd, capture_output=True)
        
        # 等待设备稳定
        time.sleep(1)
        
        # 获取主活动
        main_activity = get_main_activity(package_name)
        if not main_activity:
            print(f"错误: 无法获取{package_name}的主活动")
            return None
            
        print(f"应用主活动: {main_activity}")
        
        # 使用am start-activity命令，带上-W标志获取启动时间
        result = None
        
        for attempt in range(max_retries):
            print(f"尝试 {attempt+1}/{max_retries} 收集启动指标...")
            
            # 使用am start-activity命令（新版本Android）
            start_cmd = [
                'adb', 'shell', 'am', 'start-activity', 
                '-W', '-n', main_activity,
                '--activity-clear-task'
            ]
            
            try:
                result = subprocess.run(
                    start_cmd, 
                    capture_output=True, 
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace',
                    check=True
                )
                
                # 检查输出是否含有所需数据
                if "ThisTime" in result.stdout and "TotalTime" in result.stdout:
                    break
                    
                print(f"尝试 {attempt+1} 未能获取完整数据，尝试使用备用命令...")
                
                # 备用命令（旧版本Android）
                alt_cmd = [
                    'adb', 'shell', 'am', 'start', 
                    '-W', '-n', main_activity
                ]
                
                result = subprocess.run(
                    alt_cmd, 
                    capture_output=True, 
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace',
                    check=True
                )
                
                if "ThisTime" in result.stdout and "TotalTime" in result.stdout:
                    print("使用备用命令成功获取启动数据")
                    break
                    
                # 如果还是失败但这是最后一次尝试，就使用这个结果
                if attempt == max_retries - 1:
                    print("警告: 无法获取完整的启动指标数据，但将使用可用数据")
                else:
                    # 强制停止应用并等待更长时间
                    subprocess.run(stop_cmd, capture_output=True)
                    time.sleep(2)
                    
            except subprocess.CalledProcessError as e:
                print(f"启动应用时出错: {e}")
                print(f"标准输出: {e.stdout}")
                print(f"标准错误: {e.stderr}")
                
                # 如果这是最后一次尝试，就用已有的输出
                if attempt == max_retries - 1:
                    if e.stdout:
                        result = type('obj', (object,), {'stdout': e.stdout})
                    else:
                        return None
                else:
                    # 强制停止应用并重试
                    subprocess.run(stop_cmd, capture_output=True)
                    time.sleep(2)
        
        if not result or not result.stdout:
            print("错误: 无法获取启动指标")
            return None
            
        # 解析启动指标
        output = result.stdout
        
        # 保存详细信息到文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'startup_metrics_{package_name}_{timestamp}.txt'
        
        # 提取关键指标
        this_time = None
        total_time = None
        wait_time = None
        
        metrics = {}
        status_message = "成功获取启动指标"
        
        for line in output.split('\n'):
            if "ThisTime" in line:
                try:
                    this_time = int(line.split(':')[1].strip())
                    metrics['ThisTime'] = this_time
                except:
                    print("警告: 无法解析ThisTime值")
            elif "TotalTime" in line:
                try:
                    total_time = int(line.split(':')[1].strip())
                    metrics['TotalTime'] = total_time
                except:
                    print("警告: 无法解析TotalTime值")
            elif "WaitTime" in line:
                try:
                    wait_time = int(line.split(':')[1].strip())
                    metrics['WaitTime'] = wait_time
                except:
                    print("警告: 无法解析WaitTime值")
            elif "Complete" in line:
                status_message = line.strip()
        
        # 检查是否成功提取了关键指标
        if not this_time and not total_time and not wait_time:
            # 尝试备用解析
            ttid_matched = re.search(r'ThisTime:\s*(\d+)', output)
            if ttid_matched:
                this_time = int(ttid_matched.group(1))
                metrics['ThisTime'] = this_time
            
            total_matched = re.search(r'TotalTime:\s*(\d+)', output)
            if total_matched:
                total_time = int(total_matched.group(1))
                metrics['TotalTime'] = total_time
                
            wait_matched = re.search(r'WaitTime:\s*(\d+)', output)
            if wait_matched:
                wait_time = int(wait_matched.group(1))
                metrics['WaitTime'] = wait_time
                
        # 如果还是无法解析，则返回错误
        if not metrics:
            print("错误: 无法从输出中解析任何启动指标")
            
            # 保存整个输出以便调试
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("==== 启动指标收集失败 ====\n")
                f.write(f"状态: 无法解析指标\n\n")
                f.write("==== 原始输出 ====\n")
                f.write(output)
                
            print(f"调试信息已保存到: {output_file}")
            return None
            
        # 生成人类可读摘要
        summary = f"基本启动指标:\n"
        if 'ThisTime' in metrics:
            summary += f"TTID (ThisTime): {metrics['ThisTime']}ms\n"
        if 'TotalTime' in metrics:
            summary += f"总时间 (TotalTime): {metrics['TotalTime']}ms\n"
        if 'WaitTime' in metrics:
            summary += f"等待时间 (WaitTime): {metrics['WaitTime']}ms\n"
            
        summary += f"\n状态: {status_message}"
        
        # 保存详细结果到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("==== 基本启动指标 ====\n")
            f.write(summary + "\n\n")
            f.write("==== 原始启动输出 ====\n")
            f.write(output)
            
        print(summary)
        print(f"启动指标已保存到: {output_file}")
        
        return metrics
        
    except Exception as e:
        print(f"获取启动指标时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def collect_all_metrics(package_name, duration=10):
    """收集应用的所有性能指标"""
    result_files = {}
    success_count = 0
    
    print("\n==== 1/3. 收集应用启动指标 ====")
    startup_result = get_startup_metrics(package_name)
    if startup_result and isinstance(startup_result, str):
        result_files['startup'] = startup_result
        success_count += 1
    else:
        print("无法获取应用启动指标")
        
    print("\n==== 2/3. 收集应用帧率数据 ====")
    fps_result = get_fps(package_name, duration)
    if fps_result:
        total_frames, janky_frames, fps_file = fps_result
        result_files['fps'] = fps_file
        
        # 只有在真正收集到帧数据时才算成功
        if total_frames > 0:
            success_count += 1
        else:
            print("警告: 虽然生成了报告，但未能收集到有效的帧数据")
    else:
        print("无法获取应用帧率信息")
        
    print("\n==== 3/3. 收集系统跟踪数据 ====")
    trace_result = collect_trace(package_name, duration, categories=None)
    if trace_result:
        result_files['trace'] = trace_result
        success_count += 1
    else:
        print("无法获取应用系统跟踪数据")
        
    # 生成测试总结
    print("\n================================================================================")
    print(f"测试完成! 成功: {success_count}/3 ({success_count/3*100:.1f}%)")
    
    return result_files, success_count

def get_latest_apk(directory):
    """获取指定目录下最新的APK文件"""
    apk_files = glob.glob(os.path.join(directory, '*.apk'))
    if not apk_files:
        return None
    return max(apk_files, key=os.path.getmtime)

def get_package_name(apk_path):
    """从APK文件中提取package name"""
    try:
        result = subprocess.run(['aapt', 'dump', 'badging', apk_path], 
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            # 尝试使用aapt2
            result = subprocess.run(['aapt2', 'dump', 'badging', apk_path], 
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
            
        if result.returncode != 0:
            print(f"错误：获取APK信息失败")
            return None
        
        for line in result.stdout.split('\n'):
            if line.startswith('package: name='):
                return re.search(r"name='([^']+)'", line).group(1)
        return None
    except Exception as e:
        print(f"错误：解析APK信息时发生异常：{str(e)}")
        return None

def get_main_activity_from_apk(apk_path):
    """从APK文件中提取主Activity名称"""
    try:
        result = subprocess.run(['aapt', 'dump', 'badging', apk_path], 
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            # 尝试使用aapt2
            result = subprocess.run(['aapt2', 'dump', 'badging', apk_path], 
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
            
        if result.returncode != 0:
            print(f"错误：获取APK信息失败")
            return None
        
        activity_match = re.search(r"launchable-activity: name='([^']+)'", result.stdout)
        if activity_match:
            return activity_match.group(1)
            
        # 如果找不到launchable-activity，尝试从AndroidManifest中查找
        print("未找到launchable-activity，尝试从activity中查找主Activity...")
        for line in result.stdout.split('\n'):
            if 'activity' in line and 'android.intent.action.MAIN' in line:
                activity_match = re.search(r"name='([^']+)'", line)
                if activity_match:
                    return activity_match.group(1)
                    
        # 如果还是找不到，默认返回UnityPlayerActivity
        print("无法确定主Activity，使用默认的UnityPlayerActivity")
        return "com.unity3d.player.UnityPlayerActivity"
    except Exception as e:
        print(f"错误：解析APK信息时发生异常：{str(e)}")
        return "com.unity3d.player.UnityPlayerActivity"

def install_apk(apk_path, package_name=None):
    """安装APK文件，如果未提供package_name，则自动从APK中提取"""
    print(f"正在安装APK: {os.path.basename(apk_path)}")
    
    # 如果未提供package_name，则从APK中提取
    if not package_name:
        package_name = get_package_name(apk_path)
        if not package_name:
            print("无法从APK中提取包名，安装失败")
            return None, None
    
    # 获取主Activity
    main_activity = get_main_activity_from_apk(apk_path)
    
    # 先尝试卸载已存在的应用
    print(f"尝试卸载已存在的应用: {package_name}")
    uninstall_cmd = ['adb', 'shell', 'pm', 'uninstall', package_name]
    subprocess.run(uninstall_cmd, capture_output=True)
    
    # 安装新应用
    print(f"正在安装新应用...")
    install_cmd = ['adb', 'install', '-r', '-t', apk_path]
    result = subprocess.run(install_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    if "Success" in result.stdout or "success" in result.stdout.lower():
        print(f"APK安装成功: {package_name}")
        return package_name, main_activity
    else:
        print(f"APK安装失败: {result.stdout}")
        return None, None

def run_performance_test(apk_path=None, package_name=None, duration=10, categories=None):
    """运行完整的性能测试流程，从APK安装到收集性能指标"""
    try:
        # 如果提供了APK，优先安装并使用其包名
        if apk_path:
            print(f"将安装APK并测试: {apk_path}")
            
            # 提取包名，如果未提供
            if not package_name:
                package_name = get_package_name(apk_path)
                if not package_name:
                    print("错误: 无法从APK中获取包名")
                    return False
            
            # 安装APK
            main_activity = install_apk(apk_path, package_name)
            if not main_activity:
                print("错误: APK安装失败")
                return False
                
            print(f"APK安装成功: {package_name}")
        
        # 检查是否有包名可用
        if not package_name:
            print("错误: 需要提供包名或APK文件")
            return False
        
        # 获取设备信息
        device_info = get_device_info()
        
        # 创建结果目录
        result_dir = create_result_directory(package_name)
        original_dir = os.getcwd()
        
        try:
            # 切换到结果目录
            os.chdir(result_dir)
            print(f"\n结果将保存到目录: {os.path.abspath(os.getcwd())}\n")
            
            # 收集所有性能指标
            result_files, success_count = collect_all_metrics(package_name, duration)
            
            # 创建测试摘要
            summary = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "package_name": package_name,
                "duration": duration,
                "device": device_info,
                "success_count": success_count,
                "success_rate": f"{success_count/3*100:.1f}%",
                "result_files": {}
            }
            
            # 添加结果文件路径
            for metric_type, file_path in result_files.items():
                if file_path:
                    summary["result_files"][metric_type] = os.path.basename(file_path)
            
            # 保存摘要
            with open('test_summary.json', 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            # 返回到原始目录
            os.chdir(original_dir)
            
            print(f"结果已保存到目录: {os.path.abspath(result_dir)}")
            return True
            
        except Exception as e:
            print(f"测试过程中出错: {e}")
            # 尝试返回原始目录
            try:
                os.chdir(original_dir)
            except:
                pass
            return False
            
    except Exception as e:
        print(f"性能测试流程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_device_info():
    """获取设备详细信息"""
    try:
        info = {}
        
        # 获取设备ID
        device_id_cmd = ['adb', 'get-serialno']
        try:
            result = subprocess.run(device_id_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                info['device_id'] = result.stdout.strip()
            else:
                print("无法获取设备ID")
                info['device_id'] = "unknown_device"
        except Exception as e:
            print(f"获取设备ID时出错: {e}")
            info['device_id'] = "unknown_device"
        
        # 获取设备型号信息
        manufacturer_cmd = ['adb', 'shell', 'getprop', 'ro.product.manufacturer']
        model_cmd = ['adb', 'shell', 'getprop', 'ro.product.model']
        brand_cmd = ['adb', 'shell', 'getprop', 'ro.product.brand']
        
        try:
            manufacturer_result = subprocess.run(manufacturer_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            model_result = subprocess.run(model_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            brand_result = subprocess.run(brand_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            info['manufacturer'] = manufacturer_result.stdout.strip() if manufacturer_result.returncode == 0 else "unknown"
            info['model'] = model_result.stdout.strip() if model_result.returncode == 0 else "unknown"
            info['brand'] = brand_result.stdout.strip() if brand_result.returncode == 0 else "unknown"
            
            # 创建设备全名
            info['full_name'] = f"{info['brand']}_{info['model']}".replace(' ', '_')
        except Exception as e:
            print(f"获取设备信息时出错: {e}")
            info['manufacturer'] = "unknown"
            info['model'] = "unknown"
            info['brand'] = "unknown"
            info['full_name'] = "unknown_device"
        
        return info
    except Exception as e:
        print(f"获取设备信息失败: {e}")
        return {
            'device_id': "unknown_device",
            'manufacturer': "unknown",
            'model': "unknown",
            'brand': "unknown",
            'full_name': "unknown_device"
        }


def create_result_directory(package_name=None):
    """创建按设备命名的结果目录"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 获取设备信息
    device_info = get_device_info()
    device_name = device_info['full_name']
    device_id = device_info['device_id']
    
    # 创建目录名：设备名称+设备ID+时间戳
    if package_name:
        dir_name = f"{device_name}_{device_id}_{package_name}_{timestamp}"
    else:
        dir_name = f"{device_name}_{device_id}_{timestamp}"
    
    # 替换目录名中的特殊字符
    dir_name = dir_name.replace(':', '_').replace(' ', '_').replace('.', '_')
    
    # 创建目录
    os.makedirs(dir_name, exist_ok=True)
    
    print(f"创建结果目录: {os.path.abspath(dir_name)}")
    return dir_name

def main():
    parser = argparse.ArgumentParser(description='收集Android应用的性能数据')
    parser.add_argument('--package', help='应用包名')
    parser.add_argument('--duration', default=10, type=int, help='收集数据的持续时间（秒）')
    parser.add_argument('--fps', action='store_true', help='收集FPS数据')
    parser.add_argument('--startup', action='store_true', help='收集启动时间（TTID）')
    parser.add_argument('--trace', action='store_true', help='收集Systrace数据')
    parser.add_argument('--all', action='store_true', help='收集所有性能数据')
    parser.add_argument('--apk', help='APK文件路径，将会安装并收集性能数据')
    parser.add_argument('--apk-dir', default='D:\\UnityProjects\\HexaMatch', help='包含APK文件的目录路径，将使用最新的APK')
    parser.add_argument('--no-install', action='store_true', help='不安装APK，直接使用已安装的应用')
    parser.add_argument('--categories', default='gfx,view,am,sm,input,app,wm,freq', help='Systrace跟踪类别，用逗号分隔')
    
    args = parser.parse_args()
    
    # 显示欢迎信息
    print("=" * 80)
    print("Android应用性能测试工具")
    print("=" * 80)
    
    # 根据--all参数设置标志
    if args.all:
        args.fps = True
        args.startup = True
        args.trace = True
    
    # 如果指定了APK，自动处理安装
    if args.apk:
        print(f"将使用指定的APK: {args.apk}")
        
        # 确保APK文件存在
        if not os.path.exists(args.apk):
            print(f"错误: 指定的APK文件不存在: {args.apk}")
            return
            
        # 运行完整的性能测试
        run_performance_test(
            apk_path=args.apk,
            duration=args.duration,
            categories=args.categories.split(',') if args.categories else None
        )
        return
        
    # 如果没有指定包名，但指定了APK目录，尝试获取最新APK
    if not args.package and not args.no_install:
        try:
            # 搜索最新的APK
            latest_apk = get_latest_apk(args.apk_dir)
            if not latest_apk:
                print(f"错误: 在指定目录中未找到APK文件: {args.apk_dir}")
                print("请使用--package指定要测试的应用包名，或使用--apk指定APK文件路径")
                return
                
            print(f"找到最新APK: {latest_apk}")
            
            # 运行完整的性能测试
            run_performance_test(
                apk_path=latest_apk,
                duration=args.duration,
                categories=args.categories.split(',') if args.categories else None
            )
            return
        except Exception as e:
            print(f"尝试自动测试最新APK时出错: {e}")
            print("请使用--package指定要测试的应用包名")
            return
    
    # 如果指定了包名但没有指定--no-install标志，尝试安装最新APK
    if args.package and not args.no_install:
        try:
            print(f"将尝试安装最新APK并测试应用: {args.package}")
            
            # 搜索最新的APK
            latest_apk = get_latest_apk(args.apk_dir)
            if not latest_apk:
                print(f"警告: 在指定目录中未找到APK文件: {args.apk_dir}")
                print("将继续使用已安装的应用进行测试")
            else:
                print(f"找到最新APK: {latest_apk}")
                
                # 安装APK
                install_success = install_apk(latest_apk, args.package)
                if not install_success:
                    print("警告: APK安装失败。将尝试使用已安装的应用进行测试。")
        except Exception as e:
            print(f"尝试安装最新APK时出错: {e}")
            print("将继续使用已安装的应用进行测试")
    
    # 检查是否提供了包名
    if not args.package:
        print("错误: 未指定应用包名。请使用--package参数提供包名，或使用--apk指定APK文件路径")
        return
        
    # 创建按设备命名的结果目录
    result_dir = create_result_directory(args.package)
    
    # 切换到结果目录
    original_dir = os.getcwd()
    os.chdir(result_dir)
    
    print(f"\n结果将保存到目录: {os.path.abspath(os.getcwd())}")
    
    # 收集指定的性能数据
    results = {}
    success_count = 0
    total_tests = 0
    
    # 创建摘要文件
    device_info = get_device_info()
    summary = {
        "package_name": args.package,
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration": args.duration,
        "device_info": device_info,
        "tests_performed": []
    }
    
    # 收集TTID
    if args.startup:
        total_tests += 1
        print("\n==== 1/3. 收集应用启动指标 ====")
        try:
            startup_metrics = get_startup_metrics(args.package)
            if startup_metrics:
                success_count += 1
                results['startup_metrics'] = startup_metrics
                summary["tests_performed"].append({
                    "type": "startup_metrics",
                    "status": "success",
                    "metrics": startup_metrics
                })
            else:
                summary["tests_performed"].append({
                    "type": "startup_metrics",
                    "status": "failed"
                })
        except Exception as e:
            print(f"收集启动指标时出错: {e}")
            summary["tests_performed"].append({
                "type": "startup_metrics",
                "status": "error",
                "error": str(e)
            })
    
    # 收集FPS
    if args.fps:
        total_tests += 1
        print("\n==== 2/3. 收集应用帧率数据 ====")
        try:
            fps_stats = get_fps(args.package, args.duration)
            if fps_stats:
                success_count += 1
                results['fps_stats'] = fps_stats
                summary["tests_performed"].append({
                    "type": "fps",
                    "status": "success",
                    "data": fps_stats
                })
            else:
                summary["tests_performed"].append({
                    "type": "fps",
                    "status": "failed"
                })
        except Exception as e:
            print(f"收集帧率数据时出错: {e}")
            summary["tests_performed"].append({
                "type": "fps",
                "status": "error",
                "error": str(e)
            })
    
    # 收集Systrace
    if args.trace:
        total_tests += 1
        print("\n==== 3/3. 收集系统跟踪数据 ====")
        try:
            categories = args.categories.split(',') if args.categories else None
            trace_file = collect_trace(args.package, args.duration, categories)
            if trace_file:
                success_count += 1
                results['trace_file'] = trace_file
                summary["tests_performed"].append({
                    "type": "systrace",
                    "status": "success",
                    "file": trace_file
                })
            else:
                summary["tests_performed"].append({
                    "type": "systrace",
                    "status": "failed"
                })
        except Exception as e:
            print(f"收集系统跟踪数据时出错: {e}")
            summary["tests_performed"].append({
                "type": "systrace",
                "status": "error",
                "error": str(e)
            })
    
    # 保存测试摘要
    summary["success_count"] = success_count
    summary["total_tests"] = total_tests
    summary["success_rate"] = f"{(success_count/total_tests*100):.1f}%" if total_tests > 0 else "0%"
    
    with open('test_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 返回到原始目录
    os.chdir(original_dir)
    
    # 打印测试摘要
    print("\n" + "=" * 80)
    print(f"测试完成! 成功: {success_count}/{total_tests} ({success_count/total_tests*100 if total_tests else 0:.1f}%)")
    print(f"结果已保存到目录: {os.path.abspath(result_dir)}")
    print("=" * 80)

if __name__ == "__main__":
    main()