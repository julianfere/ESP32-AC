// ESP-AC Mini App - Preact Version
const { h, render } = preact;
const { useState, useEffect, useRef } = preactHooks;
const html = htm.bind(h);

// Lucide Icon component
function Icon({ name, size = 24, className = '' }) {
    const iconRef = useRef(null);

    useEffect(() => {
        if (iconRef.current && window.lucide) {
            iconRef.current.innerHTML = '';
            const icon = document.createElement('i');
            icon.setAttribute('data-lucide', name);
            icon.style.width = `${size}px`;
            icon.style.height = `${size}px`;
            iconRef.current.appendChild(icon);
            window.lucide.createIcons();
        }
    }, [name]);

    return html`<span ref=${iconRef} class="icon ${className}" style="display: inline-flex; align-items: center; justify-content: center;"></span>`;
}

// Telegram Web App API
const tg = window.Telegram.WebApp;

// Configuration
const API_BASE_URL = '/api';
const DEFAULT_DEVICE_ID = 'room_01';
const deviceId = DEFAULT_DEVICE_ID;

function parseTime(timestamp) {
    return new Date(timestamp);
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
        throw error;
    }
}

// Toast Component
function Toast({ message, type, visible }) {
    if (!visible) return null;
    return html`<div class="toast ${type}">${message}</div>`;
}

// Loading Component
function Loading() {
    return html`
        <div class="loading">
            <div class="spinner"></div>
            <p>Cargando datos...</p>
        </div>
    `;
}

// Status Card Component
function StatusCard({ temperature, humidity, timestamp }) {
    const formattedTime = timestamp
        ? parseTime(timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
        : '--';

    return html`
        <div class="card status-card">
            <h2><${Icon} name="bar-chart-3" size=${20} /> Estado Actual</h2>
            <div class="status-grid">
                <div class="status-item gradient-orange">
                    <span class="status-icon"><${Icon} name="thermometer" size=${32} /></span>
                    <div class="status-value">
                        <span>${temperature?.toFixed(1) || '--'}</span>
                        <span class="unit">°C</span>
                    </div>
                    <span class="status-label">Temperatura</span>
                </div>
                <div class="status-item gradient-blue">
                    <span class="status-icon"><${Icon} name="droplets" size=${32} /></span>
                    <div class="status-value">
                        <span>${humidity?.toFixed(0) || '--'}</span>
                        <span class="unit">%</span>
                    </div>
                    <span class="status-label">Humedad</span>
                </div>
            </div>
            <div class="last-update">
                Última actualización: <span>${formattedTime}</span>
            </div>
        </div>
    `;
}

// AC Control Card Component
function ACControlCard({ acStatus, acState, onAcCommand, onTimer, onStateChange }) {
    const modes = [
        { value: 'cool', label: 'Frío', icon: '❄️' },
        { value: 'auto', label: 'Auto', icon: '🔄' },
        { value: 'fan', label: 'Vent', icon: '🌀' },
        { value: 'dry', label: 'Seco', icon: '💧' }
    ];

    const fanSpeeds = [
        { value: 'auto', label: 'Auto' },
        { value: 'low', label: 'Bajo' },
        { value: 'medium', label: 'Medio' },
        { value: 'high', label: 'Alto' }
    ];

    return html`
        <div class="card ac-control-card">
            <h2><${Icon} name="snowflake" size=${20} /> Control de AC</h2>

            <!-- Temperature Display -->
            <div class="temp-display">
                <div class="temp-value">${acState.temperature}°</div>
                <div class="temp-controls">
                    <button class="temp-btn minus" onClick=${() => onStateChange({ temperature: Math.max(17, acState.temperature - 1) })}>
                        −
                    </button>
                    <button class="temp-btn plus" onClick=${() => onStateChange({ temperature: Math.min(30, acState.temperature + 1) })}>
                        +
                    </button>
                </div>
            </div>

            <!-- Power Buttons -->
            <div class="ac-buttons">
                <button class="btn btn-cool btn-large" onClick=${() => onAcCommand('on', acState.temperature, acState.mode, acState.fan_speed)}>
                    <span class="btn-icon">❄️</span>
                    ENCENDER
                </button>
                <button class="btn btn-warm btn-large" onClick=${() => onAcCommand('off', acState.temperature, acState.mode, acState.fan_speed)}>
                    <span class="btn-icon">⏻</span>
                    APAGAR
                </button>
            </div>

            <!-- Mode Selection -->
            <div class="mode-section">
                <label>Modo</label>
                <div class="mode-buttons">
                    ${modes.map(mode => html`
                        <button
                            class="mode-btn ${acState.mode === mode.value ? 'active' : ''}"
                            onClick=${() => onStateChange({ mode: mode.value })}
                        >
                            <span class="mode-icon">${mode.icon}</span>
                            <span class="mode-label">${mode.label}</span>
                        </button>
                    `)}
                </div>
            </div>

            <!-- Fan Speed -->
            <div class="fan-section">
                <label>Ventilador</label>
                <div class="fan-buttons">
                    ${fanSpeeds.map(speed => html`
                        <button
                            class="fan-btn ${acState.fan_speed === speed.value ? 'active' : ''}"
                            onClick=${() => onStateChange({ fan_speed: speed.value })}
                        >
                            ${speed.label}
                        </button>
                    `)}
                </div>
            </div>

            <!-- Quick Timer -->
            <div class="quick-timer">
                <label><${Icon} name="timer" size=${16} /> Apagar en:</label>
                <div class="timer-buttons">
                    <button class="btn btn-timer" onClick=${() => onTimer(30)}>30m</button>
                    <button class="btn btn-timer" onClick=${() => onTimer(60)}>1h</button>
                    <button class="btn btn-timer" onClick=${() => onTimer(120)}>2h</button>
                </div>
            </div>
        </div>
    `;
}

// Chart Card Component
function ChartCard({ period, onPeriodChange }) {
    const chartRef = useRef(null);
    const chartInstance = useRef(null);

    useEffect(() => {
        loadChartData(period);
    }, [period]);

    async function loadChartData(period) {
        try {
            // Calculate date range based on period
            const now = new Date();
            let fromDate;

            if (period === 'hour') {
                fromDate = new Date(now.getTime() - 60 * 60 * 1000); // 1 hour ago
            } else if (period === 'day') {
                fromDate = new Date(now.getTime() - 24 * 60 * 60 * 1000); // 24 hours ago
            } else if (period === 'week') {
                fromDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
            }

            const fromDateStr = fromDate.toISOString();
            const toDateStr = now.toISOString();

            const res = await apiRequest(`/device/${deviceId}/measurements?from_date=${fromDateStr}&to_date=${toDateStr}`);

            // Sort by timestamp ascending (oldest first)
            const sortedMeasurements = res.measurements.sort((a, b) =>
                new Date(a.timestamp) - new Date(b.timestamp)
            );

            const labels = sortedMeasurements.map(m => {
                const date = parseTime(m.timestamp);
                if (period === 'hour') {
                    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
                } else if (period === 'week') {
                    return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
                }
                return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
            });

            const temperatures = sortedMeasurements.map(m => ({ value: parseFloat(m.temperature), timestamp: m.timestamp }));
            const humidities = sortedMeasurements.map(m => ({ value: parseFloat(m.humidity), timestamp: m.timestamp }));
            updateChart(labels, temperatures, humidities);
        } catch (error) {
            console.error('Failed to load chart data:', error);
        }
    }

    function updateChart(labels, temperatures, humidities) {
        if (!chartRef.current) return;
        const ctx = chartRef.current.getContext('2d');

        const tempHourly = Object.values(
            temperatures.reduce((a, x) => {
                const hourKey = x.timestamp.slice(0, 13);
                a[hourKey] ??= x;
                return a;
            }, {})
        );

        const humidityHourly = Object.values(
            humidities.reduce((a, x) => {
                const hourKey = x.timestamp.slice(0, 13);
                a[hourKey] ??= x;
                return a;
            }, {})
        );

        // === GRADIENTES ===
        const gTemp = ctx.createLinearGradient(0, 0, 0, chartRef.current.height);
        gTemp.addColorStop(0, 'rgba(249,115,22,0.3)');
        gTemp.addColorStop(1, 'rgba(249,115,22,0)');

        const gHum = ctx.createLinearGradient(0, 0, 0, chartRef.current.height);
        gHum.addColorStop(0, 'rgba(59,130,246,0.3)');
        gHum.addColorStop(1, 'rgba(59,130,246,0)');

        // === ESCALAS DINÁMICAS ===
        const tempMin = Math.min(...tempHourly.map(x => x.value));
        const tempMax = Math.max(...tempHourly.map(x => x.value));

        const humMin = Math.min(...humidityHourly.map(x => x.value));
        const humMax = Math.max(...humidityHourly.map(x => x.value));

        if (chartInstance.current) {
            chartInstance.current.destroy();
        }

        chartInstance.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Temperatura (°C)',
                        data: tempHourly.map(d => d.value),
                        borderColor: 'rgb(249,115,22)',
                        backgroundColor: gTemp,
                        tension: 0.3,
                        fill: true,
                        borderWidth: 2,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Humedad (%)',
                        data: humidityHourly.map(d => d.value),
                        borderColor: 'rgb(59,130,246)',
                        backgroundColor: gHum,
                        tension: 0.3,
                        fill: true,
                        borderWidth: 2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        labels: { color: '#e5e7eb' }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#9ca3af',
                            maxTicksLimit: 8
                        },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    y: {
                        type: 'linear',
                        position: 'left',
                        ticks: {
                            color: '#f97316',
                            callback: v => v + '°C'
                        },
                        suggestedMin: tempMin - 1,
                        suggestedMax: tempMax + 1,
                        grid: { color: 'rgba(255,255,255,0.06)' }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        ticks: {
                            color: '#3b82f6',
                            callback: v => v + '%'
                        },
                        suggestedMin: humMin - 2,
                        suggestedMax: humMax + 2,
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    return html`
        <div class="card chart-card">
            <h2><${Icon} name="trending-up" size=${20} /> Historial de Temperatura</h2>
            <div class="chart-container">
                <canvas ref=${chartRef}></canvas>
            </div>
            <div class="chart-controls">
                <button class="btn btn-small ${period === 'hour' ? 'active' : ''}"
                    onClick=${() => onPeriodChange('hour')}>1 Hora</button>
                <button class="btn btn-small ${period === 'day' ? 'active' : ''}"
                    onClick=${() => onPeriodChange('day')}>24 Horas</button>
                <button class="btn btn-small ${period === 'week' ? 'active' : ''}"
                    onClick=${() => onPeriodChange('week')}>7 Días</button>
            </div>
        </div>
    `;
}

// Schedules Card Component
function SchedulesCard({ schedules, onAdd, onDelete }) {
    const days = ['D', 'L', 'M', 'M', 'J', 'V', 'S'];

    return html`
        <div class="card schedules-card">
            <div class="card-header">
                <h2><${Icon} name="clock" size=${20} /> Programaciones</h2>
                <button class="btn btn-small btn-primary" onClick=${onAdd}>+ Agregar</button>
            </div>
            <div class="schedules-list">
                ${schedules.length === 0
            ? html`<div class="empty-state">No hay programaciones configuradas</div>`
            : schedules.map(schedule => {
                const selectedDays = JSON.parse(schedule.days_of_week || '[]')
                    .map(d => days[d])
                    .join(', ');
                return html`
                            <div class="schedule-item" key=${schedule.id}>
                                <div class="schedule-info">
                                    <div class="schedule-name">${schedule.name}</div>
                                    <div class="schedule-details">
                                        ${schedule.time} • ${selectedDays}
                                    </div>
                                </div>
                                <span class="schedule-action ${schedule.action}">
                                    ${schedule.action.toUpperCase()}
                                </span>
                                <button class="schedule-delete" onClick=${() => onDelete(schedule.id)}>
                                    ×
                                </button>
                            </div>
                        `;
            })
        }
            </div>
        </div>
    `;
}

// Schedule Modal Component
function ScheduleModal({ visible, onClose, onSave, showToast }) {
    const [name, setName] = useState('');
    const [action, setAction] = useState('on');
    const [time, setTime] = useState('');
    const [selectedDays, setSelectedDays] = useState([]);

    function toggleDay(day) {
        setSelectedDays(prev =>
            prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day]
        );
    }

    async function handleSave() {
        if (!name || !time || selectedDays.length === 0) {
            showToast('Por favor completa todos los campos', 'error');
            return;
        }
        await onSave({ name, action, time, days_of_week: selectedDays, is_active: true });
        setName('');
        setAction('on');
        setTime('');
        setSelectedDays([]);
    }

    if (!visible) return null;

    return html`
        <div class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Nueva Programación</h3>
                    <button class="close-btn" onClick=${onClose}>×</button>
                </div>
                <div class="modal-body">
                    <div class="input-group">
                        <label>Nombre:</label>
                        <input type="text" value=${name} onInput=${e => setName(e.target.value)}
                            placeholder="Ej: Apagar por la noche" />
                    </div>
                    <div class="input-group">
                        <label>Acción:</label>
                        <select value=${action} onChange=${e => setAction(e.target.value)}>
                            <option value="on">Encender AC</option>
                            <option value="off">Apagar AC</option>
                        </select>
                    </div>
                    <div class="input-group">
                        <label>Hora:</label>
                        <input type="time" value=${time} onInput=${e => setTime(e.target.value)} />
                    </div>
                    <div class="input-group">
                        <label>Días de la semana:</label>
                        <div class="days-selector">
                            ${[1, 2, 3, 4, 5, 6, 0].map(day => html`
                                <label class="day-checkbox" key=${day}>
                                    <input type="checkbox"
                                        checked=${selectedDays.includes(day)}
                                        onChange=${() => toggleDay(day)} />
                                    ${['D', 'L', 'M', 'M', 'J', 'V', 'S'][day]}
                                </label>
                            `)}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onClick=${onClose}>Cancelar</button>
                    <button class="btn btn-primary" onClick=${handleSave}>Guardar</button>
                </div>
            </div>
        </div>
    `;
}

// Alerts Card Component
function AlertsCard({ showToast }) {
    const [enabled, setEnabled] = useState(false);
    const [high, setHigh] = useState(30);
    const [low, setLow] = useState(18);

    async function saveAlerts() {
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

    return html`
        <div class="card alerts-card">
            <h2><${Icon} name="bell" size=${20} /> Alertas de Temperatura</h2>
            <div class="alert-toggle">
                <label class="switch">
                    <input type="checkbox" checked=${enabled} onChange=${e => setEnabled(e.target.checked)} />
                    <span class="slider"></span>
                </label>
                <span class="toggle-label">Alertas Activadas</span>
            </div>
            ${enabled && html`
                <div class="alert-settings">
                    <div class="input-group">
                        <label><${Icon} name="thermometer-sun" size=${16} /> Temperatura Alta (°C):</label>
                        <input type="number" min="20" max="40" step="0.5"
                            value=${high} onInput=${e => setHigh(parseFloat(e.target.value))} />
                    </div>
                    <div class="input-group">
                        <label><${Icon} name="thermometer-snowflake" size=${16} /> Temperatura Baja (°C):</label>
                        <input type="number" min="10" max="30" step="0.5"
                            value=${low} onInput=${e => setLow(parseFloat(e.target.value))} />
                    </div>
                    <button class="btn btn-primary" onClick=${saveAlerts}>Guardar Configuración</button>
                </div>
            `}
        </div>
    `;
}

// Stats Card Component
function StatsCard({ stats }) {
    return html`
        <div class="card stats-card">
            <h2><${Icon} name="pie-chart" size=${20} /> Estadísticas</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Temp. Mínima</span>
                    <span class="stat-value">${stats.temperature?.min?.toFixed(1) || '--'}°C</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Temp. Máxima</span>
                    <span class="stat-value">${stats.temperature?.max?.toFixed(1) || '--'}°C</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Temp. Promedio</span>
                    <span class="stat-value">${stats.temperature?.average?.toFixed(1) || '--'}°C</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Hum. Promedio</span>
                    <span class="stat-value">${stats.humidity?.average?.toFixed(0) || '--'}%</span>
                </div>
            </div>
        </div>
    `;
}

// Main App Component
function App() {
    const [loading, setLoading] = useState(true);
    const [temperature, setTemperature] = useState(null);
    const [humidity, setHumidity] = useState(null);
    const [timestamp, setTimestamp] = useState(null);
    const [acStatus, setAcStatus] = useState(null);
    const [acState, setAcState] = useState({ temperature: 24, mode: 'cool', fan_speed: 'auto' });
    const [stats, setStats] = useState({ temperature: {}, humidity: {} });
    const [schedules, setSchedules] = useState([]);
    const [chartPeriod, setChartPeriod] = useState('day');
    const [modalVisible, setModalVisible] = useState(false);
    const [toast, setToast] = useState({ message: '', type: 'info', visible: false });

    function updateAcState(newState) {
        setAcState(prev => ({ ...prev, ...newState }));
        tg.HapticFeedback.selectionChanged();
    }

    function showToast(message, type = 'info') {
        setToast({ message, type, visible: true });
        setTimeout(() => setToast(prev => ({ ...prev, visible: false })), 3000);
    }

    async function loadCurrentStatus() {
        try {
            const [latest, acRes] = await Promise.all([
                apiRequest(`/device/${deviceId}/measurements/latest`),
                apiRequest(`/device/${deviceId}/ac/status`),
            ]);
            setTemperature(latest.temperature);
            setHumidity(latest.humidity);
            setTimestamp(latest.timestamp);
            setAcStatus(acRes.state || acRes.current_status);
            if (acRes.temperature) {
                setAcState({
                    temperature: acRes.temperature,
                    mode: acRes.mode || 'cool',
                    fan_speed: acRes.fan_speed || 'auto'
                });
            }
        } catch (error) {
            console.error('Failed to load status:', error);
        }
    }

    async function loadStats() {
        try {
            const res = await apiRequest(`/device/${deviceId}/stats`);
            setStats(res);
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    async function loadSchedules() {
        try {
            const res = await apiRequest(`/device/${deviceId}/schedules`);
            setSchedules(res.schedules);
        } catch (error) {
            console.error('Failed to load schedules:', error);
        }
    }

    async function sendAcCommand(action, temperature = acState.temperature, mode = acState.mode, fan_speed = acState.fan_speed) {
        try {
            tg.HapticFeedback.impactOccurred('medium');
            await apiRequest(`/device/${deviceId}/ac/command`, {
                method: 'POST',
                body: JSON.stringify({ action, temperature, mode, fan_speed }),
            });
            showToast(`AC ${action === 'on' ? 'encendido' : 'apagado'}: ${temperature}°C`, 'success');
            setTimeout(loadCurrentStatus, 1000);
        } catch (error) {
            console.error('Failed to send AC command:', error);
            showToast(error.message, 'error');
        }
    }

    async function createTimer(minutes) {
        try {
            tg.HapticFeedback.impactOccurred('light');
            await apiRequest(`/device/${deviceId}/timer`, {
                method: 'POST',
                body: JSON.stringify({ delay_minutes: minutes, action: 'off' }),
            });
            const hours = Math.floor(minutes / 60);
            const mins = minutes % 60;
            let timeStr = '';
            if (hours > 0) timeStr += `${hours}h `;
            if (mins > 0) timeStr += `${mins}min`;
            showToast(`Timer configurado: apagar en ${timeStr}`, 'success');
        } catch (error) {
            console.error('Failed to create timer:', error);
            showToast(error.message, 'error');
        }
    }

    async function saveSchedule(scheduleData) {
        try {
            await apiRequest(`/device/${deviceId}/schedules`, {
                method: 'POST',
                body: JSON.stringify(scheduleData),
            });
            showToast('Programación creada correctamente', 'success');
            setModalVisible(false);
            loadSchedules();
            tg.HapticFeedback.notificationOccurred('success');
        } catch (error) {
            console.error('Failed to save schedule:', error);
            tg.HapticFeedback.notificationOccurred('error');
        }
    }

    async function deleteSchedule(scheduleId) {
        if (!confirm('¿Estás seguro de eliminar esta programación?')) return;
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

    useEffect(() => {
        tg.ready();
        tg.expand();

        async function loadAllData() {
            await Promise.all([
                loadCurrentStatus(),
                loadStats(),
                loadSchedules(),
            ]);
            setLoading(false);
        }

        loadAllData();

        const interval = setInterval(() => {
            loadCurrentStatus();
            loadStats();
        }, 30000);

        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return html`<${Loading} />`;
    }

    return html`
        <div id="dashboard">
            <${StatusCard}
                temperature=${temperature}
                humidity=${humidity}
                timestamp=${timestamp}
            />
            <${ACControlCard}
                acStatus=${acStatus}
                acState=${acState}
                onAcCommand=${sendAcCommand}
                onTimer=${createTimer}
                onStateChange=${updateAcState}
            />
            <${ChartCard}
                period=${chartPeriod}
                onPeriodChange=${setChartPeriod}
            />
            <${SchedulesCard}
                schedules=${schedules}
                onAdd=${() => { setModalVisible(true); tg.HapticFeedback.impactOccurred('light'); }}
                onDelete=${deleteSchedule}
            />
            <${AlertsCard} showToast=${showToast} />
            <${StatsCard} stats=${stats} />
            <${ScheduleModal}
                visible=${modalVisible}
                onClose=${() => setModalVisible(false)}
                onSave=${saveSchedule}
                showToast=${showToast}
            />
            <${Toast} message=${toast.message} type=${toast.type} visible=${toast.visible} />
        </div>
    `;
}

// Render the app
render(html`<${App} />`, document.getElementById('app'));
