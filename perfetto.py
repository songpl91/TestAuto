import subprocess
import time
import os
import json
import sys
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
    
    if '|' in command:
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

def generate_perfetto_config(data_sources):
    """生成Perfetto配置文件内容
    
    Args:
        data_sources: 需要采集的数据源列表
        
    Returns:
        配置文件内容字符串
    """
    config = {
        "buffers": [{
            "size_kb": 63488,
            "fill_policy": "RING_BUFFER"
        }],
        "data_sources": []
    }
    
    for source in data_sources:
        if source == "cpu":
            config["data_sources"].append({
                "config": {
                    "name": "linux.process_stats",
                    "target_buffer": 0,
                    "process_stats_config": {
                        "proc_stats_poll_ms": 1000
                    }
                }
            })
        elif source == "gfx":
            config["data_sources"].append({
                "config": {
                    "name": "android.gpu.memory",
                    "target_buffer": 0
                }
            })
        elif source == "binder":
            config["data_sources"].append({
                "config": {
                    "name": "android.binder",
                    "target_buffer": 0
                }
            })
    
    return json.dumps(config, indent=2)

def enable_perfetto_trace(duration=20, device_id=None, data_sources=None):
    """
    启用Perfetto跟踪并拉取Trace文件
    
    Args:
        duration: 跟踪时长（秒）
        device_id: 指定设备ID，如果为None则使用第一个连接的设备
        data_sources: 需采集的数据源列表（如['gfx', 'binder']）
    """
    try:
        # 检查设备连接状态
        devices_output = run_adb_command("devices")
        if not devices_output:
            raise Exception("未检测到连接的Android设备")
            
        # 获取设备ID
        if not device_id:
            device_lines = [line for line in devices_output.split('\n') if '\t' in line]
            if not device_lines:
                raise Exception("未检测到可用的Android设备")
            device_id = device_lines[0].split('\t')[0]

        # 检查设备状态
        device_state = run_adb_command(f"get-state", device_id)
        if device_state != "device":
            raise Exception(f"设备 {device_id} 状态异常: {device_state}")

        # 检查并尝试获取root权限
        print("正在检查设备权限...")
        root_result = run_adb_command("shell whoami", device_id).strip()
        if root_result != "root":
            print("尝试获取root权限...")
            root_response = run_adb_command("root", device_id)
            if "cannot" in root_response.lower() or "不能" in root_response:
                print("警告：设备不支持root权限，将以非root模式继续执行")
            else:
                time.sleep(3)  # 等待root权限生效
                root_result = run_adb_command("shell whoami", device_id).strip()
                if root_result != "root":
                    print("警告：无法获取root权限，将以非root模式继续执行")
        
        # 尝试remount系统分区
        print("正在重新挂载系统分区...")
        remount_result = run_adb_command("remount", device_id)
        if not remount_result:
            print("警告：remount可能失败，尝试使用替代路径")

        # 生成并上传配置文件
        if not data_sources:
            data_sources = ["cpu", "gfx", "binder"]
        config_content = generate_perfetto_config(data_sources)
        # 使用应用数据目录作为配置文件路径
        config_path = "/data/local/tmp/perfetto_config.txt"
        
        # 将配置写入临时文件并上传
        temp_config = "perfetto_config_temp.txt"
        with open(temp_config, "w") as f:
            f.write(config_content)
        run_adb_command(f"push {temp_config} {config_path}", device_id)
        os.remove(temp_config)

        # 生成输出文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trace_path = f"/data/local/tmp/trace_{timestamp}"
        # 确保目标目录存在并设置权限
        run_adb_command(f"shell mkdir -p /data/local/tmp", device_id)
        run_adb_command(f"shell chmod 777 /data/local/tmp", device_id)
        
        local_dir = os.path.join(os.getcwd(), "perfetto_traces")
        os.makedirs(local_dir, exist_ok=True)
        local_trace_path = os.path.join(local_dir, f"trace_{device_id}_{timestamp}.perfetto-trace")

        # 构建并执行Perfetto命令
        print(f"开始抓取性能数据，持续时间: {duration}秒...")
        perfetto_cmd = f"shell perfetto --txt -c {config_path} -o {trace_path} -t {duration}s"
        try:
            cmd_parts = ['adb', '-s', device_id] + perfetto_cmd.split()
            process = subprocess.Popen(cmd_parts, stderr=subprocess.PIPE)
            # 检查是否有立即错误
            time.sleep(2)
            if process.poll() is not None:
                error = process.stderr.read().decode().strip()
                if error:
                    raise Exception(f"Perfetto启动失败: {error}")
        except Exception as e:
            print(f"执行Perfetto命令时出错: {str(e)}")
            raise

        # 等待跟踪完成
        for remaining in range(duration, 0, -1):
            print(f"\r剩余时间: {remaining}秒", end="")
            time.sleep(1)
        print("\n等待数据处理...")
        time.sleep(5)

        # 拉取Trace文件
        run_adb_command(f"pull {trace_path} {local_trace_path}", device_id)
        run_adb_command(f"shell rm {trace_path}", device_id)
        print(f"\nTrace文件已保存至: {local_trace_path}")

    except Exception as e:
        print(f"操作失败: {str(e)}")
        raise

def check_python_environment():
    """检查Python环境"""
    try:
        import sys
        if sys.version_info[0] < 3:
            print("错误：请使用Python 3运行此脚本")
            sys.exit(1)
        return True
    except Exception as e:
        print(f"检查Python环境时出错: {str(e)}")
        return False

if __name__ == "__main__":
    if not check_python_environment():
        print("请确保正确安装Python 3并将其添加到系统环境变量中")
        print("运行命令示例: python perfetto.py")
        sys.exit(1)
    
    try:
        # 示例配置：采集CPU、GPU、Binder数据，持续30秒
        enable_perfetto_trace(duration=30, data_sources=["cpu", "gfx", "binder"])
    except Exception as e:
        print(f"\n执行失败: {str(e)}")
        print("\n请检查以下可能的问题:")
        print("1. 确保已正确安装Python 3")
        print("2. 确保设备已正确连接并启用USB调试")
        print("3. 确保已安装ADB并添加到系统环境变量")
        sys.exit(1)