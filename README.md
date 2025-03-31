# TestAuto - Android应用自动化测试与性能分析工具

## 项目概述

TestAuto是一个功能强大的Android应用自动化测试与性能分析工具集，专为移动应用开发者和测试工程师设计。它提供了一系列自动化工具，用于应用安装、UI测试、性能监控、数据收集和可视化分析，帮助开发团队全面评估应用性能，提高应用质量。

## 主要功能

### 1. 应用自动化安装与管理
- 自动检测并连接Android设备
- 批量安装APK到多台设备
- 获取设备信息和APK详情

### 2. 自动化UI测试
- 基于Appium的UI自动化测试
- 支持元素定位、点击、输入等操作
- 自定义测试用例编写

### 3. 屏幕截图与分析
- 高频率自动截图功能
- 截图文本提取与匹配
- 应用启动时间分析

### 4. 性能监控与分析
- 内存使用情况监控(meminfo)
- 性能数据收集与报告生成
- 多设备性能对比分析

### 5. 数据可视化
- 基于Flask的Web仪表盘
- 性能数据图表展示
- 多设备数据对比

## 安装指南

### 前提条件
- Python 3.8+
- Android SDK 和 ADB 工具
- Appium Server (用于UI测试)
- 已连接的Android设备或模拟器

### 安装步骤

1. 克隆项目仓库
```bash
git clone https://github.com/yourusername/TestAuto.git
cd TestAuto
```

2. 安装依赖包
```bash
pip install -r requirements.txt
```

3. 配置Android SDK和ADB
确保Android SDK已安装，并且ADB已添加到系统PATH中。

4. 安装Appium (用于UI测试)
```bash
npm install -g appium
```

## 使用指南

### 应用安装

```bash
# 自动安装最新APK到所有连接的设备
python auto_install.py --apk_dir /path/to/apk/folder

# 批量安装APK到指定设备
python batch_install.py --apk_path /path/to/app.apk --device_id device_id_1 device_id_2
```

### 自动截图

```bash
# 执行自动截图，间隔10毫秒，持续5秒
python auto_screenshot.py --output_dir ./screenshots --interval 10 --duration 5
```

### 性能监控

```bash
# 收集应用内存信息
python performance_analysis.py --package com.example.app --duration 60

# 生成内存报告
python meminfo_report.py --input_dir ./meminfo_details --output report.csv
```

### 启动性能仪表盘

```bash
# 启动Web仪表盘
cd performance_dashboard
python app.py
```
然后在浏览器中访问 http://localhost:5000 查看性能数据可视化界面。

## 项目结构

```
TestAuto/
├── auto_install.py          # 自动安装APK工具
├── auto_screenshot.py       # 自动截图工具
├── batch_install.py         # 批量安装APK工具
├── extract_and_match_text.py # 截图文本提取与匹配
├── find_text_matches.py     # 文本匹配工具
├── format_startup_time.py   # 启动时间格式化工具
├── get_apk_size.py          # 获取APK大小工具
├── get_device_info.py       # 获取设备信息工具
├── llm_match_img_text.py    # 基于LLM的图像文本匹配
├── meminfo_report.py        # 内存信息报告生成工具
├── performance_analysis.py  # 性能分析工具
├── requirements.txt         # 项目依赖
├── save_startup_time.py     # 保存启动时间工具
├── test.py                  # Appium测试示例
└── performance_dashboard/   # 性能数据可视化仪表盘
    ├── app.py               # Flask应用入口
    ├── data_processor.py    # 数据处理模块
    └── templates/           # 前端模板
        └── index.html       # 仪表盘主页
```

## 测试结果示例

项目会在执行测试后生成设备特定的文件夹，包含以下内容：

```
device_name_timestamp/
├── device_info_device_name.json    # 设备信息
├── apk_info.json                   # APK信息
├── *_performance.csv               # 性能数据CSV
├── *_performance_report.txt        # 性能报告
├── meminfo_details/                # 内存详情文件夹
│   └── *_meminfo_*.txt             # 内存快照文件
└── screen_shot/                    # 截图文件夹
    ├── *.png                       # 截图文件
    ├── extracted_texts.json        # 提取的文本
    └── startup_time.json           # 启动时间数据
```

## Appium UI测试示例

```python
# test.py示例
import unittest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

# 配置Appium连接参数
capabilities = dict(
    platformName='Android',
    automationName='uiautomator2',
    deviceName='Android',
    appPackage='com.example.app',
    appActivity='.MainActivity'
)

# 执行UI测试
class TestAppium(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Remote('http://127.0.0.1:4723', 
                                      options=UiAutomator2Options().load_capabilities(capabilities))
    
    def test_app_launch(self):
        # 测试应用启动并查找元素
        el = self.driver.find_element(by=AppiumBy.ID, value='com.example.app:id/welcome_text')
        self.assertIsNotNone(el)
```

## 贡献指南

欢迎贡献代码、报告问题或提出改进建议。请遵循以下步骤：

1. Fork项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 详情请参阅 [LICENSE](LICENSE) 文件

## 联系方式

如有任何问题或建议，请通过以下方式联系我们：

- 项目维护者: [Your Name](mailto:your.email@example.com)
- 项目仓库: [GitHub](https://github.com/yourusername/TestAuto)