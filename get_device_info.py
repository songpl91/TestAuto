#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import re
import json
import os
import sys
from datetime import datetime

def run_adb_command(command, device_id=None):
    """
    执行adb命令并返回结果
    
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
            # 使用text=False避免编码问题
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=False)
            if result.returncode != 0:
                print(f"执行命令失败: {full_cmd}")
                print(f"错误信息: {result.stderr.decode('utf-8', errors='replace') if result.stderr else '未知错误'}")
                return ""
            
            # 尝试多种编码方式解码输出
            if result.stdout:
                try:
                    # 首先尝试UTF-8
                    return result.stdout.decode('utf-8', errors='replace').strip()
                except UnicodeDecodeError:
                    try:
                        # 然后尝试GBK（中文环境常用）
                        return result.stdout.decode('gbk', errors='replace').strip()
                    except UnicodeDecodeError:
                        # 最后使用latin1（可以解码任何字节序列）
                        return result.stdout.decode('latin1').strip()
            return ""
        except Exception as e:
            print(f"执行命令失败: {full_cmd}")
            print(f"错误信息: {str(e)}")
            return ""
    else:
        # 对于不包含管道的普通命令
        cmd.extend(command.split())
        try:
            # 使用text=False避免编码问题
            result = subprocess.run(cmd, capture_output=True, text=False)
            if result.returncode != 0:
                print(f"执行命令失败: {' '.join(cmd)}")
                print(f"错误信息: {result.stderr.decode('utf-8', errors='replace') if result.stderr else '未知错误'}")
                return ""
            
            # 尝试多种编码方式解码输出
            if result.stdout:
                try:
                    # 首先尝试UTF-8
                    return result.stdout.decode('utf-8', errors='replace').strip()
                except UnicodeDecodeError:
                    try:
                        # 然后尝试GBK（中文环境常用）
                        return result.stdout.decode('gbk', errors='replace').strip()
                    except UnicodeDecodeError:
                        # 最后使用latin1（可以解码任何字节序列）
                        return result.stdout.decode('latin1').strip()
            return ""
        except Exception as e:
            print(f"执行命令失败: {' '.join(cmd)}")
            print(f"错误信息: {str(e)}")
            return ""

def get_connected_devices():
    """
    获取所有已连接的设备ID
    
    Returns:
        设备ID列表
    """
    try:
        # 使用text=False避免编码问题，然后手动处理解码
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=False)
        if result.returncode != 0:
            print(f"执行adb devices命令失败：{result.stderr.decode('utf-8', errors='replace') if result.stderr else '未知错误'}")
            return []
        
        # 尝试多种编码方式解码输出
        output = ""
        if result.stdout:
            try:
                # 首先尝试UTF-8
                output = result.stdout.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                try:
                    # 然后尝试GBK（中文环境常用）
                    output = result.stdout.decode('gbk', errors='replace')
                except UnicodeDecodeError:
                    # 最后使用latin1（可以解码任何字节序列）
                    output = result.stdout.decode('latin1')
        
        devices = []
        for line in output.split('\n')[1:]:  # 跳过第一行的"List of devices attached"
            if line.strip() and 'device' in line and not 'offline' in line:
                devices.append(line.split()[0])
        return devices
    except Exception as e:
        print(f"获取设备列表时出错: {str(e)}")
        return []

def get_device_model(device_id):
    """
    获取设备型号
    
    Args:
        device_id: 设备ID
        
    Returns:
        设备型号信息
    """
    manufacturer = run_adb_command('shell getprop ro.product.manufacturer', device_id)
    model = run_adb_command('shell getprop ro.product.model', device_id)
    brand = run_adb_command('shell getprop ro.product.brand', device_id)
    return {
        'manufacturer': manufacturer,
        'model': model,
        'brand': brand,
        'full_name': f"{manufacturer} {model}"
    }

def get_android_version(device_id):
    """
    获取Android版本信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        Android版本信息
    """
    version = run_adb_command('shell getprop ro.build.version.release', device_id)
    sdk = run_adb_command('shell getprop ro.build.version.sdk', device_id)
    security_patch = run_adb_command('shell getprop ro.build.version.security_patch', device_id)
    build_id = run_adb_command('shell getprop ro.build.id', device_id)
    
    return {
        'version': version,
        'sdk_level': sdk,
        'security_patch': security_patch,
        'build_id': build_id
    }

def get_memory_info(device_id):
    """
    获取设备内存信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        内存信息字典
    """
    # 获取完整的/proc/meminfo信息
    meminfo_output = run_adb_command('shell cat /proc/meminfo', device_id)
    
    # 初始化内存信息字典
    meminfo_dict = {
        # 基本内存信息
        'total_memory_kb': 0,          # 设备总物理内存(KB)
        'free_memory_kb': 0,           # 当前空闲内存(KB)
        'available_memory_kb': 0,      # 可用内存(KB)，应用程序可以使用的内存
        'buffers_kb': 0,               # 缓冲区内存(KB)，用于文件系统元数据
        'cached_kb': 0,                # 缓存内存(KB)，用于文件内容缓存
        'swap_cached_kb': 0,           # 交换缓存(KB)，已从交换空间读取但仍保留在交换列表中的内存
        'active_kb': 0,                # 活跃内存(KB)，最近使用的内存页
        'inactive_kb': 0,              # 非活跃内存(KB)，较长时间未使用的内存页
        'swap_total_kb': 0,            # 交换空间总大小(KB)
        'swap_free_kb': 0,             # 可用交换空间(KB)
        'dirty_kb': 0,                 # 脏页内存(KB)，等待写入磁盘的内存页
        'writeback_kb': 0,             # 回写内存(KB)，正在写入磁盘的内存页
        'anon_pages_kb': 0,            # 匿名页内存(KB)，未映射到文件的内存页
        'mapped_kb': 0,                # 映射内存(KB)，映射到文件的内存页
        'shmem_kb': 0,                 # 共享内存(KB)
        'slab_kb': 0,                  # 内核数据结构缓存(KB)
        'sreclaimable_kb': 0,          # 可回收的slab内存(KB)
        'sunreclaim_kb': 0,            # 不可回收的slab内存(KB)
        'kernel_stack_kb': 0,          # 内核栈内存(KB)
        'page_tables_kb': 0,           # 页表内存(KB)，用于虚拟内存管理
        'cma_total_kb': 0,             # 连续内存分配器总内存(KB)
        'cma_free_kb': 0,              # 连续内存分配器可用内存(KB)
        'vmalloc_total_kb': 0,         # 虚拟内存分配总空间(KB)
        'vmalloc_used_kb': 0,          # 已使用的虚拟内存(KB)
        'vmalloc_chunk_kb': 0,         # 最大连续虚拟内存块(KB)
        
        # 计算得出的值
        'total_memory_gb': 0,          # 设备总物理内存(GB)
        'available_memory_gb': 0,      # 可用内存(GB)
        'used_memory_kb': 0,           # 已使用内存(KB)，计算得出
        'used_memory_gb': 0,           # 已使用内存(GB)，计算得出
        'memory_usage_percent': 0      # 内存使用率(%)，计算得出
    }
    
    # 解析/proc/meminfo输出
    if meminfo_output:
        lines = meminfo_output.strip().split('\n')
        for line in lines:
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                value_str = parts[1].strip()
                value = 0
                if 'kB' in value_str:
                    value = int(value_str.replace('kB', '').strip())
                
                # 映射/proc/meminfo中的键到我们的字典
                if key == 'MemTotal':
                    meminfo_dict['total_memory_kb'] = value
                elif key == 'MemFree':
                    meminfo_dict['free_memory_kb'] = value
                elif key == 'MemAvailable':
                    meminfo_dict['available_memory_kb'] = value
                elif key == 'Buffers':
                    meminfo_dict['buffers_kb'] = value
                elif key == 'Cached':
                    meminfo_dict['cached_kb'] = value
                elif key == 'SwapCached':
                    meminfo_dict['swap_cached_kb'] = value
                elif key == 'Active':
                    meminfo_dict['active_kb'] = value
                elif key == 'Inactive':
                    meminfo_dict['inactive_kb'] = value
                elif key == 'SwapTotal':
                    meminfo_dict['swap_total_kb'] = value
                elif key == 'SwapFree':
                    meminfo_dict['swap_free_kb'] = value
                elif key == 'Dirty':
                    meminfo_dict['dirty_kb'] = value
                elif key == 'Writeback':
                    meminfo_dict['writeback_kb'] = value
                elif key == 'AnonPages':
                    meminfo_dict['anon_pages_kb'] = value
                elif key == 'Mapped':
                    meminfo_dict['mapped_kb'] = value
                elif key == 'Shmem':
                    meminfo_dict['shmem_kb'] = value
                elif key == 'Slab':
                    meminfo_dict['slab_kb'] = value
                elif key == 'SReclaimable':
                    meminfo_dict['sreclaimable_kb'] = value
                elif key == 'SUnreclaim':
                    meminfo_dict['sunreclaim_kb'] = value
                elif key == 'KernelStack':
                    meminfo_dict['kernel_stack_kb'] = value
                elif key == 'PageTables':
                    meminfo_dict['page_tables_kb'] = value
                elif key == 'CmaTotal':
                    meminfo_dict['cma_total_kb'] = value
                elif key == 'CmaFree':
                    meminfo_dict['cma_free_kb'] = value
                elif key == 'VmallocTotal':
                    meminfo_dict['vmalloc_total_kb'] = value
                elif key == 'VmallocUsed':
                    meminfo_dict['vmalloc_used_kb'] = value
                elif key == 'VmallocChunk':
                    meminfo_dict['vmalloc_chunk_kb'] = value
    
    # 计算派生值
    total_kb = meminfo_dict['total_memory_kb']
    available_kb = meminfo_dict['available_memory_kb']
    used_kb = total_kb - available_kb
    
    meminfo_dict['total_memory_gb'] = round(total_kb / 1024 / 1024, 2)
    meminfo_dict['available_memory_gb'] = round(available_kb / 1024 / 1024, 2)
    meminfo_dict['used_memory_kb'] = used_kb
    meminfo_dict['used_memory_gb'] = round(used_kb / 1024 / 1024, 2)
    meminfo_dict['memory_usage_percent'] = round(used_kb / total_kb * 100, 2) if total_kb > 0 else 0
    
    # 获取内存使用情况的额外信息
    mem_info_output = run_adb_command('shell dumpsys meminfo', device_id)
    
    return meminfo_dict

def get_cpu_info(device_id):
    """
    获取CPU信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        CPU信息字典
    """
    # 获取CPU型号
    cpu_hardware = run_adb_command('shell cat /proc/cpuinfo | grep Hardware', device_id)
    cpu_model = ""
    if cpu_hardware:
        match = re.search(r'Hardware\s*:\s*(.+)', cpu_hardware)
        if match:
            cpu_model = match.group(1).strip()
    
    # 获取CPU核心数
    cpu_cores_output = run_adb_command('shell cat /proc/cpuinfo | grep processor | wc -l', device_id)
    cpu_cores = int(cpu_cores_output) if cpu_cores_output.isdigit() else 0
    
    # 获取CPU频率
    cpu_freq = []
    for i in range(cpu_cores):
        freq_output = run_adb_command(f'shell cat /sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq', device_id)
        if freq_output and freq_output.isdigit():
            cpu_freq.append(int(freq_output) / 1000)  # 转换为MHz
    
    # 获取CPU使用率
    cpu_usage_output = run_adb_command('shell top -n 1 | grep %cpu', device_id)
    cpu_usage = ""
    if cpu_usage_output:
        cpu_usage = cpu_usage_output.strip()
    
    return {
        'model': cpu_model,
        'cores': cpu_cores,
        'frequencies_mhz': cpu_freq,
        'usage_info': cpu_usage
    }

def get_gpu_info(device_id):
    """
    获取GPU信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        GPU信息字典
    """
    # 尝试从dumpsys获取GPU信息
    gpu_info_output = run_adb_command('shell dumpsys SurfaceFlinger', device_id)
    
    gpu_model = ""
    gpu_vendor = ""
    
    # 尝试从不同属性中获取GPU信息
    gpu_model_prop = run_adb_command('shell getprop ro.hardware.vulkan', device_id)
    if not gpu_model_prop:
        gpu_model_prop = run_adb_command('shell getprop ro.board.platform', device_id)
    
    gpu_vendor_prop = run_adb_command('shell getprop ro.hardware.egl', device_id)
    
    # 从dumpsys输出中提取GPU信息
    if gpu_info_output:
        # 尝试匹配常见的GPU信息格式
        gpu_match = re.search(r'GLES:\s*([^\n]+)', gpu_info_output)
        if gpu_match:
            gpu_model = gpu_match.group(1).strip()
    
    return {
        'model': gpu_model if gpu_model else gpu_model_prop,
        'vendor': gpu_vendor if gpu_vendor else gpu_vendor_prop,
        'renderer': run_adb_command('shell getprop ro.opengles.version', device_id)
    }

def get_storage_info(device_id):
    """
    获取存储信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        存储信息字典
    """
    # 获取内部存储信息
    storage_output = run_adb_command('shell df /data', device_id)
    
    internal_total = 0
    internal_used = 0
    internal_available = 0
    
    if storage_output:
        lines = storage_output.strip().split('\n')
        if len(lines) >= 2:
            parts = re.split(r'\s+', lines[1].strip())
            if len(parts) >= 4:
                try:
                    internal_total = int(parts[1]) * 1024  # 转换为字节
                    internal_used = int(parts[2]) * 1024
                    internal_available = int(parts[3]) * 1024
                except (ValueError, IndexError):
                    pass
    
    # 获取SD卡信息（如果存在）
    sdcard_output = run_adb_command('shell df /storage/sdcard0 2>/dev/null || df /storage/sdcard1 2>/dev/null || df /sdcard 2>/dev/null', device_id)
    
    sdcard_total = 0
    sdcard_used = 0
    sdcard_available = 0
    
    if sdcard_output and 'No such file or directory' not in sdcard_output:
        lines = sdcard_output.strip().split('\n')
        if len(lines) >= 2:
            parts = re.split(r'\s+', lines[1].strip())
            if len(parts) >= 4:
                try:
                    sdcard_total = int(parts[1]) * 1024  # 转换为字节
                    sdcard_used = int(parts[2]) * 1024
                    sdcard_available = int(parts[3]) * 1024
                except (ValueError, IndexError):
                    pass
    
    return {
        'internal': {
            'total_bytes': internal_total,
            'total_gb': round(internal_total / (1024**3), 2),
            'used_bytes': internal_used,
            'used_gb': round(internal_used / (1024**3), 2),
            'available_bytes': internal_available,
            'available_gb': round(internal_available / (1024**3), 2),
            'usage_percent': round(internal_used / internal_total * 100, 2) if internal_total > 0 else 0
        },
        'sdcard': {
            'total_bytes': sdcard_total,
            'total_gb': round(sdcard_total / (1024**3), 2),
            'used_bytes': sdcard_used,
            'used_gb': round(sdcard_used / (1024**3), 2),
            'available_bytes': sdcard_available,
            'available_gb': round(sdcard_available / (1024**3), 2),
            'usage_percent': round(sdcard_used / sdcard_total * 100, 2) if sdcard_total > 0 else 0
        } if sdcard_total > 0 else None
    }

def get_screen_info(device_id):
    """
    获取屏幕信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        屏幕信息字典
    """
    # 获取屏幕分辨率
    resolution_output = run_adb_command('shell wm size', device_id)
    width, height = 0, 0
    if resolution_output:
        match = re.search(r'Physical size: (\d+)x(\d+)', resolution_output)
        if match:
            width, height = int(match.group(1)), int(match.group(2))
    
    # 获取屏幕密度
    density_output = run_adb_command('shell wm density', device_id)
    density = 0
    if density_output:
        match = re.search(r'Physical density: (\d+)', density_output)
        if match:
            density = int(match.group(1))
    
    # 获取刷新率
    refresh_rate = ""
    try:
        refresh_output = run_adb_command('shell dumpsys display | grep "mDisplayInfo"', device_id)
        match = re.search(r'fps=(\d+\.?\d*)', refresh_output)
        if match:
            refresh_rate = match.group(1)
    except:
        pass
    
    return {
        'resolution': f"{width}x{height}",
        'width': width,
        'height': height,
        'density': density,
        'density_dpi': f"{density}dpi",
        'refresh_rate': refresh_rate
    }

def get_battery_info(device_id):
    """
    获取电池信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        电池信息字典
    """
    battery_output = run_adb_command('shell dumpsys battery', device_id)
    
    battery_info = {
        'level': 0,
        'temperature': 0,
        'status': 'unknown',
        'power_source': 'unknown'
    }
    
    if battery_output:
        level_match = re.search(r'level: (\d+)', battery_output)
        if level_match:
            battery_info['level'] = int(level_match.group(1))
        
        temp_match = re.search(r'temperature: (\d+)', battery_output)
        if temp_match:
            # 转换为摄氏度（原始值通常是10倍的摄氏度）
            battery_info['temperature'] = int(temp_match.group(1)) / 10.0
        
        status_match = re.search(r'status: (\d+)', battery_output)
        if status_match:
            status_code = int(status_match.group(1))
            status_map = {1: 'unknown', 2: 'charging', 3: 'discharging', 4: 'not charging', 5: 'full'}
            battery_info['status'] = status_map.get(status_code, 'unknown')
        
        ac_match = re.search(r'AC powered: (\w+)', battery_output)
        usb_match = re.search(r'USB powered: (\w+)', battery_output)
        wireless_match = re.search(r'Wireless powered: (\w+)', battery_output)
        
        if ac_match and ac_match.group(1).lower() == 'true':
            battery_info['power_source'] = 'AC'
        elif usb_match and usb_match.group(1).lower() == 'true':
            battery_info['power_source'] = 'USB'
        elif wireless_match and wireless_match.group(1).lower() == 'true':
            battery_info['power_source'] = 'Wireless'
        else:
            battery_info['power_source'] = 'Battery'
    
    return battery_info

def get_network_info(device_id):
    """
    获取网络信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        网络信息字典
    """
    # 获取WiFi信息
    wifi_output = run_adb_command('shell dumpsys wifi | grep "mNetworkInfo"', device_id)
    wifi_connected = 'state: CONNECTED' in wifi_output
    
    # 获取WiFi名称（如果已连接）
    wifi_ssid = ""
    if wifi_connected:
        ssid_output = run_adb_command('shell dumpsys wifi | grep "SSID"', device_id)
        ssid_match = re.search(r'SSID: (.+?),', ssid_output)
        if ssid_match:
            wifi_ssid = ssid_match.group(1).strip('"')
    
    # 获取移动网络信息
    mobile_output = run_adb_command('shell dumpsys telephony.registry | grep "mServiceState"', device_id)
    mobile_type = ""
    if mobile_output:
        if 'LTE' in mobile_output:
            mobile_type = '4G'
        elif '5G' in mobile_output:
            mobile_type = '5G'
        elif 'UMTS' in mobile_output or 'HSDPA' in mobile_output or 'HSPA' in mobile_output:
            mobile_type = '3G'
        elif 'EDGE' in mobile_output:
            mobile_type = '2G'
    
    # 获取IP地址
    ip_output = run_adb_command('shell ip addr show wlan0', device_id)
    ip_address = ""
    if ip_output:
        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_output)
        if ip_match:
            ip_address = ip_match.group(1)
    
    return {
        'wifi': {
            'connected': wifi_connected,
            'ssid': wifi_ssid if wifi_connected else ""
        },
        'mobile': {
            'connected': bool(mobile_type),
            'type': mobile_type
        },
        'ip_address': ip_address
    }

def get_device_info(device_id=None):
    """
    获取设备的完整信息
    
    Args:
        device_id: 设备ID，如果为None则使用第一个连接的设备
        
    Returns:
        设备信息字典
    """
    # 如果没有提供设备ID，获取第一个连接的设备
    if not device_id:
        devices = get_connected_devices()
        if not devices:
            print("错误：未找到已连接的设备")
            return None
        device_id = devices[0]
        print(f"使用设备: {device_id}")
    
    # 收集所有设备信息
    device_info = {
        'device_id': device_id,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'model': get_device_model(device_id),
        'android': get_android_version(device_id),
        'memory': get_memory_info(device_id),
        'cpu': get_cpu_info(device_id),
        'gpu': get_gpu_info(device_id),
        'storage': get_storage_info(device_id),
        'screen': get_screen_info(device_id),
        'battery': get_battery_info(device_id),
        'network': get_network_info(device_id)
    }
    
    return device_info

def print_device_info(device_info, format_json=False):
    """
    打印设备信息
    
    Args:
        device_info: 设备信息字典
        format_json: 是否以JSON格式输出
    """
    if not device_info:
        return
    
    if format_json:
        print(json.dumps(device_info, indent=2, ensure_ascii=False))
        return
    
    print("\n" + "=" * 50)
    print(f"设备信息报告 - {device_info['timestamp']}")
    print("=" * 50)
    
    print(f"\n设备ID: {device_info['device_id']}")
    
    # 打印设备型号信息
    model = device_info['model']
    print("\n[设备型号]")
    print(f"制造商: {model['manufacturer']}")
    print(f"品牌: {model['brand']}")
    print(f"型号: {model['model']}")
    print(f"完整名称: {model['full_name']}")
    
    # 打印Android版本信息
    android = device_info['android']
    print("\n[Android版本]")
    print(f"版本: {android['version']}")
    print(f"SDK级别: {android['sdk_level']}")
    print(f"安全补丁级别: {android['security_patch']}")
    print(f"构建ID: {android['build_id']}")
    
    # 打印内存信息
    memory = device_info['memory']
    print("\n[内存信息]")
    print(f"总内存: {memory['total_memory_gb']} GB ({memory['total_memory_kb']} KB)")
    print(f"可用内存: {memory['available_memory_gb']} GB ({memory['available_memory_kb']} KB)")
    print(f"空闲内存: {memory.get('free_memory_kb', 0) / 1024:.2f} MB ({memory.get('free_memory_kb', 0)} KB)")
    print(f"已用内存: {memory['used_memory_gb']} GB ({memory['used_memory_kb']} KB)")
    print(f"内存使用率: {memory['memory_usage_percent']}%")
    print(f"缓冲区: {memory.get('buffers_kb', 0) / 1024:.2f} MB ({memory.get('buffers_kb', 0)} KB)")
    print(f"缓存: {memory.get('cached_kb', 0) / 1024:.2f} MB ({memory.get('cached_kb', 0)} KB)")
    print(f"交换空间总量: {memory.get('swap_total_kb', 0) / 1024:.2f} MB ({memory.get('swap_total_kb', 0)} KB)")
    print(f"交换空间可用: {memory.get('swap_free_kb', 0) / 1024:.2f} MB ({memory.get('swap_free_kb', 0)} KB)")
    print(f"活跃内存: {memory.get('active_kb', 0) / 1024:.2f} MB ({memory.get('active_kb', 0)} KB)")
    print(f"非活跃内存: {memory.get('inactive_kb', 0) / 1024:.2f} MB ({memory.get('inactive_kb', 0)} KB)")
    
    # 打印CPU信息
    cpu = device_info['cpu']
    print("\n[CPU信息]")
    print(f"型号: {cpu['model']}")
    print(f"核心数: {cpu['cores']}")
    if cpu['frequencies_mhz']:
        print(f"当前频率: {', '.join([f'{freq} MHz' for freq in cpu['frequencies_mhz']])}")
    if cpu['usage_info']:
        print(f"使用情况: {cpu['usage_info']}")
    
    # 打印GPU信息
    gpu = device_info['gpu']
    print("\n[GPU信息]")
    print(f"型号: {gpu['model']}")
    print(f"厂商: {gpu['vendor']}")
    print(f"OpenGL ES版本: {gpu['renderer']}")
    
    # 打印存储信息
    storage = device_info['storage']
    print("\n[存储信息]")
    print("内部存储:")
    print(f"  总空间: {storage['internal']['total_gb']} GB")
    print(f"  已用空间: {storage['internal']['used_gb']} GB")
    print(f"  可用空间: {storage['internal']['available_gb']} GB")
    print(f"  使用率: {storage['internal']['usage_percent']}%")
    
    if storage['sdcard']:
        print("SD卡:")
        print(f"  总空间: {storage['sdcard']['total_gb']} GB")
        print(f"  已用空间: {storage['sdcard']['used_gb']} GB")
        print(f"  可用空间: {storage['sdcard']['available_gb']} GB")
        print(f"  使用率: {storage['sdcard']['usage_percent']}%")
    
    # 打印屏幕信息
    screen = device_info['screen']
    print("\n[屏幕信息]")
    print(f"分辨率: {screen['resolution']}")
    print(f"屏幕密度: {screen['density_dpi']}")
    if screen['refresh_rate']:
        print(f"刷新率: {screen['refresh_rate']} Hz")
    
    # 打印电池信息
    battery = device_info['battery']
    print("\n[电池信息]")
    print(f"电量: {battery['level']}%")
    print(f"温度: {battery['temperature']}°C")
    print(f"状态: {battery['status']}")
    print(f"电源: {battery['power_source']}")
    
    # 打印网络信息
    network = device_info['network']
    print("\n[网络信息]")
    print(f"WiFi连接: {'是' if network['wifi']['connected'] else '否'}")
    if network['wifi']['connected']:
        print(f"WiFi名称: {network['wifi']['ssid']}")
    print(f"移动网络: {'是' if network['mobile']['connected'] else '否'}")
    if network['mobile']['connected']:
        print(f"网络类型: {network['mobile']['type']}")
    if network['ip_address']:
        print(f"IP地址: {network['ip_address']}")
    
    print("\n" + "=" * 50 + "\n")

def save_device_info(device_info, output_file=None):
    """
    保存设备信息到文件
    
    Args:
        device_info: 设备信息字典
        output_file: 输出文件路径，如果为None则自动生成
    """
    if not device_info:
        return
    
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model = device_info['model']['model'].replace(' ', '_')
        output_file = f"device_info_{model}_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(device_info, f, indent=2, ensure_ascii=False)
    
    print(f"设备信息已保存到: {output_file}")

def main():
    """
    主函数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='获取Android设备信息')
    parser.add_argument('-d', '--device', help='指定设备ID')
    parser.add_argument('-j', '--json', action='store_true', help='以JSON格式输出')
    parser.add_argument('-o', '--output', help='保存结果到指定文件')
    parser.add_argument('-l', '--list', action='store_true', help='列出所有已连接的设备')
    
    args = parser.parse_args()
    
    if args.list:
        devices = get_connected_devices()
        if devices:
            print("已连接的设备:")
            for i, device in enumerate(devices):
                print(f"{i+1}. {device}")
        else:
            print("未找到已连接的设备")
        return
    
    device_info = get_device_info(args.device)
    
    if device_info:
        print_device_info(device_info, args.json)
        
        if args.output:
            save_device_info(device_info, args.output)
        elif not args.json:  # 如果不是JSON输出，默认保存到文件
            save_device_info(device_info)

if __name__ == '__main__':
    main()