// ESP-AC Mini App JavaScript

// Telegram Web App API
const tg = window.Telegram.WebApp;

// Configuration
const API_BASE_URL = '/api';  // Proxy through bot server
const DEFAULT_DEVICE_ID = 'room_01';  // Will be loaded from config
let deviceId = DEFAULT_DEVICE_ID;

// Chart instance
let tempChart = null;

// State
let currentData = {
    temperature: null,
    humidity: null,
    acStatus: null,
    timestamp: null,
};

// Utility function to parse UTC timestamps
function parseUTCTimestamp(timestamp) {
    // Ensure timestamp has 'Z' suffix for proper UTC parsing
    const utcTimestamp = timestamp.includes('Z') ? timestamp : timestamp + 'Z';
    return new Date(utcTimestamp);
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Telegram Web App
    tg.ready();
    tg.expand();

    // Setup event listeners
    setupEventListeners();

    // Load initial data
    await loadAllData();

    // Hide loading, show dashboard
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');

    // Auto refresh every 30 seconds
    setInterval(refreshData, 30000);
});

// Setup Event Listeners
function setupEventListeners() {
    // AC Control
    document.getElementById('ac-on-btn').addEventListener('click', () => sendAcCommand('on'));
    document.getElementById('ac-off-btn').addEventListener('click', () => sendAcCommand('off'));

    // Timer buttons
    document.querySelectorAll('.btn-timer').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const minutes = parseInt(e.target.dataset.minutes);
            createSleepTimer(minutes);
        });
    });

    // Chart period buttons
    document.querySelectorAll('.chart-controls .btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.chart-controls .btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const period = e.target.dataset.period;
            loadChartData(period);
        });
    });

    // Schedule buttons
    document.getElementById('add-schedule-btn').addEventListener('click', openScheduleModal);
    document.getElementById('close-schedule-modal').addEventListener('click', closeScheduleModal);
    document.getElementById('cancel-schedule-btn').addEventListener('click', closeScheduleModal);
    document.getElementById('save-schedule-btn').addEventListener('click', saveSchedule);

    // Alerts
    document.getElementById('alerts-enabled').addEventListener('change', (e) => {
        const settings = document.getElementById('alert-settings');
        if (e.target.checked) {
            settings.classList.remove('hidden');
        } else {
            settings.classList.add('hidden');
        }
    });

    document.getElementById('save-alerts-btn').addEventListener('click', saveAlertSettings);
}

// API Functions
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-Init-Data': tg.initData,
                ...options.headers,
            },
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Request failed:', error);
        showToast(error.message, 'error');
        throw error;
    }
}

async function loadAllData() {
    try {
        await Promise.all([
            loadCurrentStatus(),
            loadStats(),
            loadSchedules(),
            loadChartData('day'),
        ]);
    } catch (error) {
        console.error('Failed to load data:', error);
    }
}

async function refreshData() {
    try {
        await Promise.all([
            loadCurrentStatus(),
            loadStats(),
        ]);
    } catch (error) {
        console.error('Failed to refresh data:', error);
    }
}

async function loadCurrentStatus() {
    try {
        const [latest, acStatus] = await Promise.all([
            apiRequest(`/device/${deviceId}/measurements/latest`),
            apiRequest(`/device/${deviceId}/ac/status`),
        ]);

        currentData.temperature = latest.temperature;
        currentData.humidity = latest.humidity;
        currentData.timestamp = latest.timestamp;
        currentData.acStatus = acStatus.current_status;

        updateStatusDisplay();
    } catch (error) {
        console.error('Failed to load status:', error);
    }
}

function updateStatusDisplay() {
    // Temperature
    const tempEl = document.getElementById('temperature');
    const tempIconEl = document.getElementById('temp-icon');
    tempEl.textContent = currentData.temperature?.toFixed(1) || '--';

    // Temperature icon based on value
    if (currentData.temperature !== null) {
        if (currentData.temperature < 20) {
            tempIconEl.textContent = '🥶';
        } else if (currentData.temperature < 26) {
            tempIconEl.textContent = '🌡️';
        } else {
            tempIconEl.textContent = '🔥';
        }
    }

    // Humidity
    document.getElementById('humidity').textContent =
        currentData.humidity?.toFixed(0) || '--';

    // Timestamp
    if (currentData.timestamp) {
        const date = parseUTCTimestamp(currentData.timestamp);
        document.getElementById('last-update').textContent =
            date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    }

    // AC Status
    const acStatusEl = document.getElementById('ac-status-text');
    acStatusEl.textContent = currentData.acStatus === 'on' ? 'ENCENDIDO' : 'APAGADO';
    acStatusEl.className = `ac-status-value ${currentData.acStatus}`;
}

async function loadStats() {
    try {
        const res = await apiRequest(`/device/${deviceId}/stats`);

        document.getElementById('stat-min-temp').textContent =
            `${res.temperature.min?.toFixed(1) || '--'}°C`;
        document.getElementById('stat-max-temp').textContent =
            `${res.temperature.max?.toFixed(1) || '--'}°C`;
        document.getElementById('stat-avg-temp').textContent =
            `${res.temperature.average?.toFixed(1) || '--'}°C`;
        document.getElementById('stat-hum-avg').textContent =
            res.humidity.average?.toFixed(0) + '%' || '--%';
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function loadChartData(period = 'day') {
    try {
        let limit = 50;
        if (period === 'hour') limit = 12;
        if (period === 'day') limit = 48;
        if (period === 'week') limit = 168;

        const res = await apiRequest(`/device/${deviceId}/measurements?limit=${limit}`);
        // Reverse to show oldest first
        res.measurements.reverse();

        const labels = res.measurements.map(m => {
            const date = parseUTCTimestamp(m.timestamp);
            if (period === 'hour') {
                return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
            } else if (period === 'week') {
                return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
            }
            return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
        });

        const temperatures = res.measurements.map(m => parseInt(m.temperature));

        updateChart(labels, temperatures);
    } catch (error) {
        console.error('Failed to load chart data:', error);
    }
}

function updateChart(labels, data) {
    const ctx = document.getElementById('temp-chart').getContext('2d');

    if (tempChart) {
        tempChart.destroy();
    }

    tempChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Temperatura (°C)',
                data: data,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function (value) {
                            return value + '°C';
                        }
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 8,
                    }
                }
            },
        }
    });
}

async function sendAcCommand(action) {
    try {
        tg.HapticFeedback.impactOccurred('medium');

        const result = await apiRequest(`/device/${deviceId}/ac`, {
            method: 'POST',
            body: JSON.stringify({ action }),
        });

        showToast(`AC ${action === 'on' ? 'encendido' : 'apagado'} correctamente`, 'success');

        // Refresh status after a short delay
        setTimeout(loadCurrentStatus, 1000);
    } catch (error) {
        console.error('Failed to send AC command:', error);
    }
}

async function createSleepTimer(minutes) {
    try {
        tg.HapticFeedback.impactOccurred('light');

        await apiRequest(`/device/${deviceId}/timer`, {
            method: 'POST',
            body: JSON.stringify({ minutes }),
        });

        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        let timeStr = '';
        if (hours > 0) timeStr += `${hours}h `;
        if (mins > 0) timeStr += `${mins}min`;

        showToast(`Timer configurado: apagar en ${timeStr}`, 'success');
    } catch (error) {
        console.error('Failed to create timer:', error);
    }
}

async function loadSchedules() {
    try {
        const res = await apiRequest(`/device/${deviceId}/schedules`);
        const schedules = res.schedules;
        const listEl = document.getElementById('schedules-list');

        if (schedules.length === 0) {
            listEl.innerHTML = '<div class="empty-state">No hay programaciones configuradas</div>';
            return;
        }
        console.log(schedules);
        listEl.innerHTML = schedules.map(schedule => {
            const days = ['D', 'L', 'M', 'M', 'J', 'V', 'S'];
            const selectedDays = JSON.parse(schedule.days_of_week || '[]')
                .map(d => days[d])
                .join(', ');

            return `
                <div class="schedule-item">
                    <div class="schedule-info">
                        <div class="schedule-name">${schedule.name}</div>
                        <div class="schedule-details">
                            ${schedule.time} • ${selectedDays}
                        </div>
                    </div>
                    <span class="schedule-action ${schedule.action}">${schedule.action.toUpperCase()}</span>
                    <button class="schedule-delete" onclick="deleteSchedule(${schedule.id})">
                        ×
                    </button>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load schedules:', error);
    }
}

function openScheduleModal() {
    document.getElementById('schedule-modal').classList.remove('hidden');
    tg.HapticFeedback.impactOccurred('light');
}

function closeScheduleModal() {
    document.getElementById('schedule-modal').classList.add('hidden');
    // Reset form
    document.getElementById('schedule-name').value = '';
    document.getElementById('schedule-action').value = 'on';
    document.getElementById('schedule-time').value = '';
    document.querySelectorAll('.day-checkbox input').forEach(cb => cb.checked = false);
}

async function saveSchedule() {
    const name = document.getElementById('schedule-name').value;
    const action = document.getElementById('schedule-action').value;
    const time = document.getElementById('schedule-time').value;
    const days = Array.from(document.querySelectorAll('.day-checkbox input:checked'))
        .map(cb => parseInt(cb.value));

    if (!name || !time || days.length === 0) {
        showToast('Por favor completa todos los campos', 'error');
        return;
    }

    try {
        await apiRequest(`/device/${deviceId}/schedules`, {
            method: 'POST',
            body: JSON.stringify({
                name,
                action,
                time,
                days_of_week: days,
                is_active: true,
            }),
        });

        showToast('Programación creada correctamente', 'success');
        closeScheduleModal();
        loadSchedules();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Failed to save schedule:', error);
        tg.HapticFeedback.notificationOccurred('error');
    }
}

async function deleteSchedule(scheduleId) {
    if (!confirm('¿Estás seguro de eliminar esta programación?')) {
        return;
    }

    try {
        await apiRequest(`/device/${deviceId}/schedules/${scheduleId}`, {
            method: 'DELETE',
        });

        showToast('Programación eliminada', 'success');
        loadSchedules();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Failed to delete schedule:', error);
        tg.HapticFeedback.notificationOccurred('error');
    }
}

async function saveAlertSettings() {
    const enabled = document.getElementById('alerts-enabled').checked;
    const high = parseFloat(document.getElementById('alert-high').value);
    const low = parseFloat(document.getElementById('alert-low').value);

    if (low >= high) {
        showToast('El umbral bajo debe ser menor que el alto', 'error');
        return;
    }

    try {
        await apiRequest('/alerts/config', {
            method: 'POST',
            body: JSON.stringify({
                enabled,
                threshold_high: high,
                threshold_low: low,
            }),
        });

        showToast('Configuración de alertas guardada', 'success');
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Failed to save alert settings:', error);
        tg.HapticFeedback.notificationOccurred('error');
    }
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// Make deleteSchedule available globally
window.deleteSchedule = deleteSchedule;
