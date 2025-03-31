# 手游性能分析仪表板

这是一个简单有效的可视化面板，用于分析Unity手游性能数据。该面板支持按设备型号、时间段等维度筛选和对比数据，包括内存、CPU使用率、帧率等关键指标的可视化图表。

## 功能特点

- 多设备数据支持：自动识别并加载TestAuto目录下的所有设备测试数据
- 多维度筛选：支持按设备型号、时间段进行数据筛选
- 性能指标可视化：内存使用、CPU使用率、帧率、电池等关键指标的图表展示
- 数据摘要：自动计算并显示所选指标的平均值、最大值和最小值
- 响应式设计：适配不同屏幕尺寸的设备

## 使用方法

### 安装依赖

```bash
pip install flask
```

### 运行面板

```bash
cd /Volumes/MacEx/Work/TestAuto/performance_dashboard
python app.py
```

启动后，在浏览器中访问 http://localhost:5000 即可打开仪表板。

### 使用说明

1. 在左侧筛选面板中选择设备型号
2. 选择要查看的性能指标（内存、CPU、帧率等）
3. 可选择时间范围进行数据筛选
4. 点击"应用筛选"按钮更新图表和数据摘要
5. 图表下方会显示所选指标的平均值、最大值和最小值

## 目录结构

```
performance_dashboard/
├── app.py                 # Flask应用主文件
├── data_processor.py      # 数据处理模块
├── static/               # 静态资源
│   ├── css/              # CSS样式文件
│   └── js/               # JavaScript文件
└── templates/            # HTML模板
    └── index.html        # 主页面模板
```

## 扩展性

该面板采用模块化设计，便于后续扩展和维护：

- 添加新的性能指标：修改app.py中的get_metrics函数
- 支持新的数据源：扩展data_processor.py中的数据处理逻辑
- 增加新的可视化图表：在dashboard.js中添加新的图表类型和处理逻辑