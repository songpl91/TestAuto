import os
import json
import csv
import re
from datetime import datetime
from pathlib import Path

class DataProcessor:
    def __init__(self, base_dir):
        """
        初始化数据处理器
        :param base_dir: 测试数据的基础目录
        """
        self.base_dir = Path(base_dir)
        self.device_folders = self._get_device_folders()
    
    def _get_device_folders(self):
        """
        获取所有设备文件夹
        :return: 设备文件夹列表
        """
        device_folders = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and re.match(r'.*_\d{8}_\d{6}$', item.name):
                device_folders.append(item)
        return device_folders
    
    def get_device_info(self, device_folder):
        """
        获取设备信息
        :param device_folder: 设备文件夹路径
        :return: 设备信息字典
        """
        device_info_files = list(device_folder.glob('device_info_*.json'))
        if not device_info_files:
            return None
        
        with open(device_info_files[0], 'r') as f:
            device_info = json.load(f)
        return device_info
    
    def get_performance_data(self, device_folder):
        """
        获取性能数据
        :param device_folder: 设备文件夹路径
        :return: 性能数据列表
        """
        performance_files = list(device_folder.glob('*_performance.csv'))
        if not performance_files:
            return []
        
        performance_data = []
        with open(performance_files[0], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 转换数据类型
                for key in row:
                    if key == 'timestamp':
                        continue
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        pass
                performance_data.append(row)
        return performance_data
    
    def get_all_devices_data(self):
        """
        获取所有设备的数据
        :return: 设备数据字典，格式为 {device_name: {info: {...}, performance: [...]}}
        """
        all_data = {}
        for device_folder in self.device_folders:
            device_info = self.get_device_info(device_folder)
            if not device_info:
                continue
            
            device_name = device_info['model']['full_name']
            performance_data = self.get_performance_data(device_folder)
            
            all_data[device_name] = {
                'info': device_info,
                'performance': performance_data,
                'folder_name': device_folder.name
            }
        
        return all_data
    
    def get_time_range(self, device_data):
        """
        获取性能数据的时间范围
        :param device_data: 设备性能数据
        :return: (开始时间, 结束时间)
        """
        if not device_data or not device_data.get('performance'):
            return None, None
        
        performance = device_data['performance']
        start_time = datetime.strptime(performance[0]['timestamp'], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(performance[-1]['timestamp'], '%Y-%m-%d %H:%M:%S')
        
        return start_time, end_time
    
    def filter_data_by_time(self, performance_data, start_time, end_time):
        """
        按时间范围过滤性能数据
        :param performance_data: 性能数据列表
        :param start_time: 开始时间
        :param end_time: 结束时间
        :return: 过滤后的性能数据列表
        """
        filtered_data = []
        for data in performance_data:
            data_time = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
            if start_time <= data_time <= end_time:
                filtered_data.append(data)
        
        return filtered_data