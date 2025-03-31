from flask import Flask, render_template, jsonify, request
import os
import json
from pathlib import Path
from data_processor import DataProcessor

app = Flask(__name__)

# 初始化数据处理器
base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent
data_processor = DataProcessor(base_dir)

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/devices')
def get_devices():
    """获取所有设备信息"""
    all_data = data_processor.get_all_devices_data()
    devices = []
    
    for device_name, data in all_data.items():
        device_info = data['info']
        devices.append({
            'name': device_name,
            'id': device_info['device_id'],
            'android_version': device_info['android']['version'],
            'folder_name': data['folder_name']
        })
    
    return jsonify(devices)

@app.route('/api/device/<folder_name>/info')
def get_device_info(folder_name):
    """获取指定设备的详细信息"""
    device_folder = base_dir / folder_name
    device_info = data_processor.get_device_info(device_folder)
    
    if not device_info:
        return jsonify({'error': '设备信息不存在'}), 404
    
    return jsonify(device_info)

@app.route('/api/device/<folder_name>/performance')
def get_device_performance(folder_name):
    """获取指定设备的性能数据"""
    device_folder = base_dir / folder_name
    performance_data = data_processor.get_performance_data(device_folder)
    
    # 获取查询参数
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    # 如果有时间范围参数，过滤数据
    if start_time and end_time:
        from datetime import datetime
        start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        performance_data = data_processor.filter_data_by_time(performance_data, start, end)
    
    return jsonify(performance_data)

@app.route('/api/metrics')
def get_metrics():
    """获取可用的性能指标"""
    metrics = [
        {'id': 'memory_total', 'name': '总内存 (KB)', 'category': '内存'},
        {'id': 'memory_java_heap', 'name': 'Java堆内存 (KB)', 'category': '内存'},
        {'id': 'memory_native_heap', 'name': '原生堆内存 (KB)', 'category': '内存'},
        {'id': 'memory_pss_total', 'name': 'PSS总内存 (KB)', 'category': '内存'},
        {'id': 'cpu_percentage', 'name': 'CPU使用率 (%)', 'category': 'CPU'},
        {'id': 'total_frames', 'name': '总帧数', 'category': '流畅度'},
        {'id': 'janky_frames', 'name': '卡顿帧数', 'category': '流畅度'},
        {'id': 'janky_percent', 'name': '卡顿帧比例 (%)', 'category': '流畅度'},
        {'id': 'battery_level', 'name': '电池电量 (%)', 'category': '电池'},
        {'id': 'battery_temperature', 'name': '电池温度 (°C)', 'category': '电池'}
    ]
    
    return jsonify(metrics)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)