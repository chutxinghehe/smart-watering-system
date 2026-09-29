/**
 * Smart Watering Dashboard - JavaScript
 * Xử lý fetch API, update real-time data, render chart
 */

// Config
const API_BASE = '';  // Same domain, no need prefix
const REFRESH_INTERVAL = 5000;  // 5 seconds

// Chart instance
let historyChart = null;

// ============= INIT =============

document.addEventListener('DOMContentLoaded', function() {
    console.log('🌱 Dashboard initialized');
    
    // Initialize chart
    initChart();
    
    // Fetch initial data
    fetchCurrentData();
    fetchHistoryData();
    
    // Start auto-refresh
    setInterval(fetchCurrentData, REFRESH_INTERVAL);
    
    // Refresh chart every 30 seconds
    setInterval(fetchHistoryData, 30000);
});

// ============= FETCH DATA =============

/**
 * Fetch current sensor data và update cards
 */
async function fetchCurrentData() {
    try {
        const response = await fetch(`${API_BASE}/api/current`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch current data');
        }
        
        const data = await response.json();
        updateCards(data);
        updateServerStatus(true);
        
    } catch (error) {
        console.error('❌ Error fetching current data:', error);
        updateServerStatus(false);
    }
}

/**
 * Fetch history data và update chart
 */
async function fetchHistoryData() {
    try {
        const response = await fetch(`${API_BASE}/api/history?hours=24`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch history');
        }
        
        const history = await response.json();
        updateChart(history);
        
    } catch (error) {
        console.error('❌ Error fetching history:', error);
    }
}

// ============= UPDATE UI =============

/**
 * Update sensor cards với data mới
 */
function updateCards(data) {
    const { moisture, temperature, humidity, timestamp } = data;
    
    // Update moisture
    const moistureEl = document.getElementById('moisture-value');
    const moistureBar = document.getElementById('moisture-bar');
    const moistureStatus = document.getElementById('moisture-status');
    
    moistureEl.textContent = `${moisture.toFixed(1)}%`;
    moistureBar.style.width = `${moisture}%`;
    
    // Color coding cho moisture bar
    moistureBar.classList.remove('low', 'medium', 'high');
    if (moisture < 30) {
        moistureBar.classList.add('low');
        moistureStatus.textContent = '⚠️ Cần tưới ngay!';
        moistureStatus.style.color = '#ef4444';
    } else if (moisture < 60) {
        moistureBar.classList.add('medium');
        moistureStatus.textContent = 'Độ ẩm trung bình';
        moistureStatus.style.color = '#f59e0b';
    } else {
        moistureBar.classList.add('high');
        moistureStatus.textContent = '✅ Độ ẩm tốt';
        moistureStatus.style.color = '#10b981';
    }
    
    // Update temperature
    document.getElementById('temp-value').textContent = `${temperature.toFixed(1)}°C`;
    
    // Update humidity
    document.getElementById('humidity-value').textContent = `${humidity.toFixed(1)}%`;
    
    // Update last update time
    const updateTime = new Date(timestamp).toLocaleString('vi-VN');
    document.getElementById('last-update').textContent = updateTime;
}

/**
 * Update server status indicator
 */
function updateServerStatus(isOnline) {
    const statusEl = document.getElementById('server-status');
    
    if (isOnline) {
        statusEl.textContent = '●';
        statusEl.className = 'status-ok';
    } else {
        statusEl.textContent = '●';
        statusEl.className = 'status-error';
    }
}

// ============= CHART =============

/**
 * Initialize Chart.js
 */
function initChart() {
    const ctx = document.getElementById('historyChart').getContext('2d');
    
    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Độ ẩm đất (%)',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Nhiệt độ (°C)',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Độ ẩm không khí (%)',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false  // Dùng custom legend
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Thời gian'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Giá trị'
                    },
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

/**
 * Update chart với history data
 */
function updateChart(history) {
    if (!historyChart || history.length === 0) {
        return;
    }
    
    // Parse labels và data
    const labels = history.map(item => {
        const date = new Date(item.timestamp);
        return date.toLocaleTimeString('vi-VN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    });
    
    const moistureData = history.map(item => item.moisture);
    const tempData = history.map(item => item.temperature);
    const humidityData = history.map(item => item.humidity);
    
    // Update chart
    historyChart.data.labels = labels;
    historyChart.data.datasets[0].data = moistureData;
    historyChart.data.datasets[1].data = tempData;
    historyChart.data.datasets[2].data = humidityData;
    historyChart.update();
}

// ============= CONTROL =============

/**
 * Control pump (manual)
 * @param {string} action - 'on' hoặc 'off'
 */
async function controlPump(action) {
    console.log(`🎮 Manual control: ${action}`);
    
    try {
        const response = await fetch(`${API_BASE}/api/control`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action })
        });
        
        if (!response.ok) {
            throw new Error('Control failed');
        }
        
        const result = await response.json();
        console.log('✅ Control success:', result);
        
        // Update pump status indicator
        updatePumpStatus(action);
        
        // Show notification
        showNotification(`Đã ${action === 'on' ? 'BẬT' : 'TẮT'} bơm nước`);
        
    } catch (error) {
        console.error('❌ Error controlling pump:', error);
        showNotification('Lỗi điều khiển bơm!', 'error');
    }
}

/**
 * Update pump status indicator
 */
function updatePumpStatus(action) {
    const indicator = document.getElementById('pump-indicator');
    const text = document.getElementById('pump-text');
    
    indicator.classList.remove('on', 'off');
    
    if (action === 'on') {
        indicator.classList.add('on');
        text.textContent = 'Đang bật';
        text.style.color = '#10b981';
    } else {
        indicator.classList.add('off');
        text.textContent = 'Đang tắt';
        text.style.color = '#ef4444';
    }
}

/**
 * Show notification (simple alert for now)
 */
function showNotification(message, type = 'success') {
    // Simple alert - có thể replace bằng toast notification library
    alert(message);
}
