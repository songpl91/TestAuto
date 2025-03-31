// 全局变量
let performanceChart = null;
let currentDevices = []; // 支持多设备选择
let currentMetric = null;
let allDevicesData = {};
let deviceColors = [
    'rgb(75, 192, 192)',   // 青绿色
    'rgb(255, 99, 132)',    // 粉红色
    'rgb(54, 162, 235)',    // 蓝色
    'rgb(255, 159, 64)',    // 橙色
    'rgb(153, 102, 255)',   // 紫色
    'rgb(255, 205, 86)',    // 黄色
    'rgb(201, 203, 207)'    // 灰色
];

// 页面加载完成后执行
$(document).ready(function() {
    // 加载设备列表
    loadDevices();
    
    // 加载性能指标列表
    loadMetrics();
    
    // 绑定事件处理函数
    $('#deviceSelect').change(onDeviceChange);
    $('#timeRangeSelect').change(onTimeRangeChange);
    $('#applyFilters').click(applyFilters);
    $('#compareDevicesBtn').click(toggleDeviceComparison);
    $('#metricSelect').change(onMetricChange);
    
    // 初始化设备选择区域
    initDeviceSelection();
});

// 初始化设备选择区域
function initDeviceSelection() {
    // 创建设备选择区域
    const deviceSelectionArea = $(`
        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">设备选择</h5>
                <div>
                    <button id="compareDevicesBtn" class="btn btn-sm btn-outline-primary">对比模式</button>
                </div>
            </div>
            <div class="card-body">
                <div id="singleDeviceSelect">
                    <div class="form-group">
                        <label for="deviceSelect">选择设备</label>
                        <select class="form-control" id="deviceSelect">
                            <option value="">加载中...</option>
                        </select>
                    </div>
                </div>
                <div id="multiDeviceSelect" style="display:none;">
                    <div class="form-group">
                        <label>选择多个设备进行对比</label>
                        <div id="deviceCheckboxes" class="mt-2">
                            <div class="text-center">加载中...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);
    
    // 替换原有的设备选择下拉框
    $('#deviceSelectContainer').html(deviceSelectionArea);
    
    // 加载设备列表
    loadDevices();
}

// 切换设备对比模式
function toggleDeviceComparison() {
    const isCompareMode = $('#multiDeviceSelect').is(':visible');
    
    if (isCompareMode) {
        // 切换到单设备模式
        $('#compareDevicesBtn').text('对比模式');
        $('#singleDeviceSelect').show();
        $('#multiDeviceSelect').hide();
        currentDevices = currentDevices.slice(0, 1); // 只保留第一个设备
    } else {
        // 切换到多设备对比模式
        $('#compareDevicesBtn').text('单设备模式');
        $('#singleDeviceSelect').hide();
        $('#multiDeviceSelect').show();
    }
    
    // 如果已选择性能指标，则重新加载图表
    if (currentMetric && currentDevices.length > 0) {
        applyFilters();
    }
}

// 加载设备列表
function loadDevices() {
    $.ajax({
        url: '/api/devices',
        method: 'GET',
        success: function(devices) {
            // 存储所有设备数据
            devices.forEach(device => {
                allDevicesData[device.folder_name] = device;
            });
            
            if (devices.length === 0) {
                $('#deviceSelect').html('<option value="">没有可用设备</option>');
                $('#deviceCheckboxes').html('<div class="text-center">没有可用设备</div>');
                return;
            }
            
            // 更新单设备下拉选择框
            const deviceSelect = $('#deviceSelect');
            deviceSelect.empty();
            deviceSelect.append('<option value="">请选择设备</option>');
            devices.forEach(device => {
                deviceSelect.append(`<option value="${device.folder_name}">${device.name} (Android ${device.android_version})</option>`);
            });
            
            // 更新多设备复选框
            const deviceCheckboxes = $('#deviceCheckboxes');
            deviceCheckboxes.empty();
            devices.forEach((device, index) => {
                const checkboxId = `device-${index}`;
                const checkboxColor = deviceColors[index % deviceColors.length];
                deviceCheckboxes.append(`
                    <div class="form-check mb-2">
                        <input class="form-check-input device-checkbox" type="checkbox" value="${device.folder_name}" id="${checkboxId}" data-index="${index}">
                        <label class="form-check-label" for="${checkboxId}" style="color: ${checkboxColor}">
                            ${device.name} (Android ${device.android_version})
                        </label>
                    </div>
                `);
            });
            
            // 绑定复选框事件
            $('.device-checkbox').change(function() {
                const deviceFolder = $(this).val();
                const isChecked = $(this).prop('checked');
                const deviceIndex = parseInt($(this).data('index'));
                
                if (isChecked) {
                    // 添加设备到当前选择
                    if (!currentDevices.includes(deviceFolder)) {
                        currentDevices.push(deviceFolder);
                        // 加载设备信息
                        loadDeviceInfo(deviceFolder, deviceIndex);
                    }
                } else {
                    // 从当前选择中移除设备
                    currentDevices = currentDevices.filter(d => d !== deviceFolder);
                }
                
                // 如果已选择性能指标，则重新加载图表
                if (currentMetric) {
                    applyFilters();
                }
            });
        },
        error: function(error) {
            console.error('加载设备列表失败:', error);
            $('#deviceSelect').html('<option value="">加载失败</option>');
            $('#deviceCheckboxes').html('<div class="text-center">加载失败</div>');
        }
    });
}

// 加载性能指标列表
function loadMetrics() {
    $.ajax({
        url: '/api/metrics',
        method: 'GET',
        success: function(metrics) {
            const metricSelect = $('#metricSelect');
            metricSelect.empty();
            
            if (metrics.length === 0) {
                metricSelect.append('<option value="">没有可用指标</option>');
                return;
            }
            
            metricSelect.append('<option value="">请选择性能指标</option>');
            
            // 按类别分组
            const categories = {};
            metrics.forEach(metric => {
                if (!categories[metric.category]) {
                    categories[metric.category] = [];
                }
                categories[metric.category].push(metric);
            });
            
            // 添加分组选项
            for (const category in categories) {
                const optgroup = $(`<optgroup label="${category}"></optgroup>`);
                categories[category].forEach(metric => {
                    optgroup.append(`<option value="${metric.id}">${metric.name}</option>`);
                });
                metricSelect.append(optgroup);
            }
            
            // 绑定性能指标选择事件
            metricSelect.change(function() {
                const metricId = $(this).val();
                if (metricId && currentDevices.length > 0) {
                    // 如果已选择设备，则自动应用筛选
                    currentMetric = metricId;
                    applyFilters();
                }
            });
        },
        error: function(error) {
            console.error('加载性能指标失败:', error);
            $('#metricSelect').html('<option value="">加载失败</option>');
        }
    });
}

// 设备变更事件处理
function onDeviceChange() {
    const deviceFolder = $('#deviceSelect').val();
    if (!deviceFolder) {
        $('#deviceInfo').html('<p>请选择设备查看详细信息</p>');
        currentDevices = [];
        return;
    }
    
    // 更新当前设备选择
    currentDevices = [deviceFolder];
    
    // 加载设备信息
    loadDeviceInfo(deviceFolder, 0);
    
    // 如果已选择性能指标，则重新加载图表
    if (currentMetric) {
        applyFilters();
    } else {
        // 检查是否已选择性能指标
        const metricId = $('#metricSelect').val();
        if (metricId) {
            // 如果已选择性能指标，则自动应用筛选
            currentMetric = metricId;
            applyFilters();
        }
    }
}

// 加载设备信息
function loadDeviceInfo(deviceFolder, deviceIndex) {
    $.ajax({
        url: `/api/device/${deviceFolder}/info`,
        method: 'GET',
        success: function(deviceInfo) {
            // 在单设备模式下显示设备信息
            if ($('#singleDeviceSelect').is(':visible')) {
                displayDeviceInfo(deviceInfo);
            }
            
            // 存储设备信息到全局变量
            allDevicesData[deviceFolder] = deviceInfo;
        },
        error: function(error) {
            console.error('加载设备信息失败:', error);
            if ($('#singleDeviceSelect').is(':visible')) {
                $('#deviceInfo').html('<p>加载设备信息失败</p>');
            }
        }
    });
}

// 显示设备信息
function displayDeviceInfo(deviceInfo) {
    const model = deviceInfo.model;
    const android = deviceInfo.android;
    const memory = deviceInfo.memory;
    const screen = deviceInfo.screen;
    
    let html = `
        <div class="device-info">
            <p><strong>设备名称:</strong> ${model.full_name}</p>
            <p><strong>设备ID:</strong> ${deviceInfo.device_id}</p>
            <p><strong>Android版本:</strong> ${android.version} (API ${android.sdk_level})</p>
            <p><strong>内存:</strong> ${(memory.total_memory_gb).toFixed(2)} GB</p>
            <p><strong>屏幕分辨率:</strong> ${screen.resolution}</p>
        </div>
    `;
    
    $('#deviceInfo').html(html);
}

// 时间范围变更事件处理
function onTimeRangeChange() {
    const timeRange = $('#timeRangeSelect').val();
    if (timeRange === 'custom') {
        $('#customTimeRange').show();
    } else {
        $('#customTimeRange').hide();
    }
}

// 性能指标变更事件处理
function onMetricChange() {
    const metricId = $('#metricSelect').val();
    if (!metricId) {
        return;
    }
    
    // 如果已选择设备，则自动应用筛选
    if (currentDevices.length > 0) {
        applyFilters();
    }
}

// 应用筛选条件
function applyFilters() {
    const metricId = $('#metricSelect').val();
    
    // 检查是否选择了设备和指标
    if (currentDevices.length === 0 || !metricId) {
        alert('请选择设备和性能指标');
        return;
    }
    
    currentMetric = metricId;
    
    // 构建查询参数
    let params = {};
    const timeRange = $('#timeRangeSelect').val();
    if (timeRange === 'custom') {
        const startTime = $('#startTime').val();
        const endTime = $('#endTime').val();
        if (startTime && endTime) {
            params.start_time = startTime.replace('T', ' ');
            params.end_time = endTime.replace('T', ' ');
        }
    }
    
    // 显示加载状态
    $('#performanceChart').parent().addClass('loading');
    $('#performanceChart').hide();
    $('#performanceSummary').hide();
    
    // 创建一个Promise数组来存储所有设备的数据加载请求
    const dataPromises = currentDevices.map(deviceFolder => {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: `/api/device/${deviceFolder}/performance`,
                method: 'GET',
                data: params,
                success: function(performanceData) {
                    resolve({
                        deviceFolder: deviceFolder,
                        data: performanceData
                    });
                },
                error: function(error) {
                    console.error(`加载设备 ${deviceFolder} 性能数据失败:`, error);
                    reject(error);
                }
            });
        });
    });
    
    // 等待所有数据加载完成
    Promise.all(dataPromises)
        .then(results => {
            // 移除加载状态
            $('#performanceChart').parent().removeClass('loading');
            $('#performanceChart').show();
            $('#performanceSummary').show();
            
            // 过滤掉没有数据的结果
            const validResults = results.filter(result => result.data && result.data.length > 0);
            
            if (validResults.length === 0) {
                alert('所选时间范围内没有性能数据');
                return;
            }
            
            // 更新图表
            updateChartWithMultipleDevices(validResults, metricId);
            
            // 更新性能数据摘要 (使用第一个设备的数据)
            if (validResults.length > 0) {
                updatePerformanceSummary(validResults[0].data, metricId);
            }
        })
        .catch(error => {
            // 移除加载状态
            $('#performanceChart').parent().removeClass('loading');
            $('#performanceChart').show();
            $('#performanceSummary').show();
            
            console.error('加载性能数据失败:', error);
            alert('加载性能数据失败');
        });
}

// 更新图表 (单设备版本)
function updateChart(performanceData, metricId) {
    // 准备图表数据
    const labels = performanceData.map(data => data.timestamp);
    const values = performanceData.map(data => data[metricId]);
    
    // 获取指标名称
    let metricName = $('#metricSelect option:selected').text();
    
    // 销毁旧图表
    if (performanceChart) {
        performanceChart.destroy();
    }
    
    // 创建新图表
    const ctx = document.getElementById('performanceChart').getContext('2d');
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: metricName,
                data: values,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1,
                pointRadius: 2,
                borderWidth: 2,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `${$('#deviceSelect option:selected').text()} - ${metricName}`
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: metricName
                    },
                    beginAtZero: true
                }
            }
        }
    });
    
    // 更新图表标题
    $('#chartTitle').text(`${$('#deviceSelect option:selected').text()} - ${metricName}`);
}

// 更新图表 (多设备版本)
function updateChartWithMultipleDevices(results, metricId) {
    // 获取指标名称
    let metricName = $('#metricSelect option:selected').text();
    
    // 销毁旧图表
    if (performanceChart) {
        performanceChart.destroy();
    }
    
    // 准备数据集
    const datasets = [];
    
    // 找出所有时间戳的并集
    let allTimestamps = new Set();
    results.forEach(result => {
        result.data.forEach(data => {
            allTimestamps.add(data.timestamp);
        });
    });
    
    // 转换为数组并排序
    allTimestamps = Array.from(allTimestamps).sort();
    
    // 为每个设备创建数据集
    results.forEach((result, index) => {
        // 查找设备名称
        let deviceName = '';
        // 遍历设备数据查找匹配的设备
        Object.values(allDevicesData).forEach(device => {
            if (device.folder_name === result.deviceFolder) {
                deviceName = device.name;
            }
        });
        
        // 如果找不到设备名称，使用文件夹名称
        if (!deviceName) {
            deviceName = result.deviceFolder;
        }
        
        // 选择颜色
        const colorIndex = index % deviceColors.length;
        const borderColor = deviceColors[colorIndex];
        const backgroundColor = borderColor.replace('rgb', 'rgba').replace(')', ', 0.2)');
        
        // 创建一个映射，将时间戳映射到数据点
        const dataMap = {};
        result.data.forEach(data => {
            dataMap[data.timestamp] = data[metricId];
        });
        
        // 为所有时间戳创建数据点，如果没有数据则为null
        const dataPoints = allTimestamps.map(timestamp => {
            return dataMap[timestamp] !== undefined ? dataMap[timestamp] : null;
        });
        
        // 添加到数据集
        datasets.push({
            label: deviceName,
            data: dataPoints,
            borderColor: borderColor,
            backgroundColor: backgroundColor,
            tension: 0.1,
            pointRadius: 2,
            borderWidth: 2,
            fill: false,
            spanGaps: true
        });
    });
    
    // 创建新图表
    const ctx = document.getElementById('performanceChart').getContext('2d');
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allTimestamps,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `设备性能对比 - ${metricName}`
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: 20
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: metricName
                    },
                    beginAtZero: true
                }
            }
        }
    });
    
    // 更新图表标题
    if (results.length > 1) {
        $('#chartTitle').text(`设备性能对比 - ${metricName}`);
    } else if (results.length === 1) {
        // 查找设备名称
        let deviceName = '';
        // 遍历设备数据查找匹配的设备
        Object.values(allDevicesData).forEach(device => {
            if (device.folder_name === results[0].deviceFolder) {
                deviceName = device.name;
            }
        });
        $('#chartTitle').text(`${deviceName || results[0].deviceFolder} - ${metricName}`);
    }
}

// 更新性能数据摘要
function updatePerformanceSummary(performanceData, metricId) {
    // 计算平均值、最大值和最小值
    const values = performanceData.map(data => parseFloat(data[metricId]));
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const max = Math.max(...values);
    const min = Math.min(...values);
    
    // 更新UI
    $('#avgValue').text(avg.toFixed(2));
    $('#maxValue').text(max.toFixed(2));
    $('#minValue').text(min.toFixed(2));
}