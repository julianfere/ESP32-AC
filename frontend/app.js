const { render, h, useState, useEffect, useRef, html } = window.preact;

// Configuración
const API_BASE_URL = window.location.protocol + '//' + window.location.host;
const DEVICE_ID = 'room_01';

// ============================================
// COMPONENTE: Toast Notification
// ============================================

const Toast = ({ message, type, onClose }) => {
    useEffect(() => {
        const timer = setTimeout(onClose, 4000);
        return () => clearTimeout(timer);
    }, []);

    const colors = {
        success: 'bg-green-600',
        error: 'bg-red-600',
        info: 'bg-blue-600',
        warning: 'bg-yellow-600'
    };

    const icons = {
        success: html`<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>`,
        error: html`<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>`,
        info: html`<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>`,
        warning: html`<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>`
    };

    return html`
        <div class="${colors[type]} text-white px-6 py-4 rounded-lg shadow-lg flex items-center space-x-3 min-w-[300px] animate-slide-in">
            <svg class="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                ${icons[type]}
            </svg>
            <span class="flex-1">${message}</span>
        </div>
    `;
};

// ============================================
// COMPONENTE: Dashboard Card
// ============================================

const DashboardCard = ({ title, value, gradient, icon }) => {
    return html`
        <div class="bg-gradient-to-br ${gradient} rounded-xl shadow-xl p-6">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-white text-sm font-medium opacity-90">${title}</p>
                    <p class="text-white text-3xl font-bold mt-1">${value}</p>
                </div>
                <svg class="w-12 h-12 text-white opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    ${icon}
                </svg>
            </div>
        </div>
    `;
};

// ============================================
// COMPONENTE: Chart
// ============================================

const ChartComponent = ({ title, data, color, chartId }) => {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        if (!canvasRef.current || !data || data.length === 0) return;

        if (chartRef.current) {
            chartRef.current.destroy();
        }

        const ctx = canvasRef.current.getContext('2d');
        chartRef.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => new Date(d.timestamp).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })),
                datasets: [{
                    label: title,
                    data: data.map(d => d.value),
                    borderColor: color,
                    backgroundColor: color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#e5e7eb' } }
                },
                scales: {
                    y: {
                        ticks: { color: '#9ca3af' },
                        grid: { color: '#374151' }
                    },
                    x: {
                        ticks: { color: '#9ca3af' },
                        grid: { color: '#374151' }
                    }
                }
            }
        });

        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, [data]);

    return html`
        <div class="bg-gray-800 rounded-xl shadow-xl p-6 border border-gray-700">
            <h3 class="text-lg font-semibold mb-4 flex items-center">
                <svg class="w-5 h-5 mr-2" style="color: ${color}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"></path>
                </svg>
                ${title}
            </h3>
            <div style="height: 250px; position: relative;">
                <canvas ref=${canvasRef}></canvas>
            </div>
        </div>
    `;
};

// ============================================
// COMPONENTE: AC Control Tab
// ============================================

const ACControlTab = ({ onCommand, history }) => {
    return html`
        <div>
            <h3 class="text-xl font-semibold mb-6 flex items-center">
                <svg class="w-6 h-6 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5"></path>
                </svg>
                Control de Aire Acondicionado
            </h3>
            <div class="flex gap-4 mb-6">
                <button
                    onClick=${() => onCommand('on')}
                    class="flex-1 px-6 py-4 bg-green-600 hover:bg-green-700 text-white rounded-lg font-semibold flex items-center justify-center space-x-2"
                >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    <span>Encender AC</span>
                </button>
                <button
                    onClick=${() => onCommand('off')}
                    class="flex-1 px-6 py-4 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold flex items-center justify-center space-x-2"
                >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                    <span>Apagar AC</span>
                </button>
            </div>

            <h4 class="text-lg font-semibold mb-4 mt-8">Historial de Comandos</h4>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead class="bg-gray-700">
                        <tr>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Acción</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Activado Por</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Fecha/Hora</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-700">
                        ${history && history.length > 0 ? history.map(event => html`
                            <tr class="hover:bg-gray-700">
                                <td class="px-4 py-3">
                                    <span class="px-3 py-1 rounded-full text-xs font-semibold ${event.action === 'on' ? 'bg-green-600' : 'bg-red-600'}">
                                        ${event.action === 'on' ? 'Encendido' : 'Apagado'}
                                    </span>
                                </td>
                                <td class="px-4 py-3 text-gray-300">${event.triggered_by}</td>
                                <td class="px-4 py-3 text-gray-400">${new Date(event.timestamp).toLocaleString()}</td>
                            </tr>
                        `) : html`
                            <tr>
                                <td colspan="3" class="px-4 py-8 text-center text-gray-400">No hay historial disponible</td>
                            </tr>
                        `}
                    </tbody>
                </table>
            </div>
        </div>
    `;
};

// ============================================
// COMPONENTE: Sleep Timer Tab
// ============================================

const SleepTimerTab = ({ timers, onLoadTimers, onCreateTimer, onCancelTimer }) => {
    const [action, setAction] = useState('off');
    const [delayMinutes, setDelayMinutes] = useState(30);
    const [remainingTime, setRemainingTime] = useState({});

    // Cargar timers al montar
    useEffect(() => {
        onLoadTimers();
        const interval = setInterval(onLoadTimers, 30000); // Actualizar cada 30 segundos
        return () => clearInterval(interval);
    }, []);

    // Actualizar tiempo restante cada segundo
    useEffect(() => {
        const interval = setInterval(() => {
            const newRemainingTime = {};
            timers.forEach(timer => {
                newRemainingTime[timer.id] = timer.remaining_seconds - 1;
            });
            setRemainingTime(newRemainingTime);
        }, 1000);
        return () => clearInterval(interval);
    }, [timers]);

    // Inicializar tiempo restante cuando cambian los timers
    useEffect(() => {
        const newRemainingTime = {};
        timers.forEach(timer => {
            newRemainingTime[timer.id] = timer.remaining_seconds;
        });
        setRemainingTime(newRemainingTime);
    }, [timers]);

    const handleCreate = () => {
        if (delayMinutes < 1 || delayMinutes > 1440) {
            return;
        }
        onCreateTimer(action, delayMinutes);
    };

    const formatTime = (seconds) => {
        if (seconds <= 0) return 'Ejecutando...';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    };

    const presetMinutes = [15, 30, 60, 120];

    return html`
        <div>
            <h3 class="text-xl font-semibold mb-6 flex items-center">
                <svg class="w-6 h-6 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                Temporizador de Apagado
            </h3>

            <div class="bg-gray-700 rounded-lg p-4 mb-6">
                <p class="text-gray-300 text-sm mb-2">
                    Configura el AC para que se apague (o encienda) automáticamente después de un tiempo determinado.
                    Ideal para antes de dormir.
                </p>
            </div>

            <!-- Crear nuevo timer -->
            <div class="bg-gray-800 rounded-xl shadow-xl p-6 border border-gray-700 mb-6">
                <h4 class="text-lg font-semibold mb-4">Crear Temporizador</h4>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                        <label class="block text-sm font-medium mb-2">Acción</label>
                        <select
                            value=${action}
                            onChange=${e => setAction(e.target.value)}
                            class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2"
                        >
                            <option value="off">Apagar AC</option>
                            <option value="on">Encender AC</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-2">Tiempo (minutos)</label>
                        <input
                            type="number"
                            min="1"
                            max="1440"
                            value=${delayMinutes}
                            onInput=${e => setDelayMinutes(parseInt(e.target.value))}
                            class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2"
                        />
                    </div>
                </div>

                <!-- Botones de presets -->
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-2">Presets rápidos</label>
                    <div class="flex gap-2 flex-wrap">
                        ${presetMinutes.map(minutes => html`
                            <button
                                onClick=${() => setDelayMinutes(minutes)}
                                class="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm"
                            >
                                ${minutes < 60 ? `${minutes} min` : `${minutes / 60}h`}
                            </button>
                        `)}
                    </div>
                </div>

                <button
                    onClick=${handleCreate}
                    class="w-full px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-semibold"
                >
                    Crear Temporizador
                </button>
            </div>

            <!-- Lista de timers activos -->
            <div class="bg-gray-800 rounded-xl shadow-xl p-6 border border-gray-700">
                <h4 class="text-lg font-semibold mb-4">Temporizadores Activos</h4>
                ${timers && timers.length > 0 ? html`
                    <div class="space-y-3">
                        ${timers.map(timer => html`
                            <div class="bg-gray-700 rounded-lg p-4 flex items-center justify-between">
                                <div class="flex-1">
                                    <div class="flex items-center space-x-2 mb-2">
                                        <span class="px-3 py-1 rounded-full text-xs font-semibold ${timer.action === 'on' ? 'bg-green-600' : 'bg-red-600'}">
                                            ${timer.action === 'on' ? 'Encender' : 'Apagar'}
                                        </span>
                                        <span class="text-2xl font-bold text-primary-400">
                                            ${formatTime(remainingTime[timer.id] || timer.remaining_seconds)}
                                        </span>
                                    </div>
                                    <div class="text-sm text-gray-400">
                                        Se ejecutará a las ${new Date(timer.execute_at).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                </div>
                                <button
                                    onClick=${() => onCancelTimer(timer.id)}
                                    class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold ml-4"
                                >
                                    Cancelar
                                </button>
                            </div>
                        `)}
                    </div>
                ` : html`
                    <div class="text-center py-8 text-gray-400">
                        <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <p>No hay temporizadores activos</p>
                    </div>
                `}
            </div>
        </div>
    `;
};

// ============================================
// COMPONENTE: LED Control Tab
// ============================================

const LEDControlTab = ({ onSend }) => {
    const [r, setR] = useState(255);
    const [g, setG] = useState(255);
    const [b, setB] = useState(255);

    const previewColor = `rgb(${r}, ${g}, ${b})`;

    // Convertir RGB a formato hex para el color picker
    const rgbToHex = (r, g, b) => {
        return '#' + [r, g, b].map(x => {
            const hex = x.toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        }).join('');
    };

    // Convertir hex a RGB
    const hexToRgb = (hex) => {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    };

    const handleColorPickerChange = (e) => {
        const rgb = hexToRgb(e.target.value);
        if (rgb) {
            setR(rgb.r);
            setG(rgb.g);
            setB(rgb.b);
        }
    };

    const currentHex = rgbToHex(r, g, b);

    return html`
        <div>
            <h3 class="text-xl font-semibold mb-6 flex items-center">
                <svg class="w-6 h-6 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                </svg>
                Control de LED RGB
            </h3>

            <!-- Color Picker -->
            <div class="mb-6">
                <label class="block text-sm font-medium mb-2">Selector de Color</label>
                <div class="flex items-center gap-4">
                    <input
                        type="color"
                        value=${currentHex}
                        onInput=${handleColorPickerChange}
                        class="w-24 h-24 rounded-lg cursor-pointer bg-gray-700 border-2 border-gray-600"
                        style="padding: 4px;"
                    />
                    <div class="flex-1">
                        <div class="h-24 rounded-lg border-2 border-gray-600" style="background-color: ${previewColor}"></div>
                    </div>
                    <div class="text-center">
                        <p class="text-sm text-gray-400 mb-1">Código Hex</p>
                        <p class="text-lg font-mono font-semibold">${currentHex.toUpperCase()}</p>
                        <p class="text-sm text-gray-400 mt-2">RGB</p>
                        <p class="text-sm font-mono">${r}, ${g}, ${b}</p>
                    </div>
                </div>
            </div>

            <!-- Sliders RGB (opcional para ajuste fino) -->
            <details class="mb-6">
                <summary class="cursor-pointer text-sm font-medium text-gray-400 hover:text-gray-200 mb-4">
                    Ajuste fino con sliders RGB
                </summary>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
                    <div>
                        <label class="block text-sm font-medium mb-2">Rojo (0-255)</label>
                        <input type="range" min="0" max="255" value=${r} onInput=${e => setR(parseInt(e.target.value) || 0)} class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-red-600" />
                        <input type="number" min="0" max="255" value=${r} onInput=${e => setR(parseInt(e.target.value) || 0)} class="mt-2 w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2" />
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-2">Verde (0-255)</label>
                        <input type="range" min="0" max="255" value=${g} onInput=${e => setG(parseInt(e.target.value) || 0)} class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-600" />
                        <input type="number" min="0" max="255" value=${g} onInput=${e => setG(parseInt(e.target.value) || 0)} class="mt-2 w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2" />
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-2">Azul (0-255)</label>
                        <input type="range" min="0" max="255" value=${b} onInput=${e => setB(parseInt(e.target.value) || 0)} class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600" />
                        <input type="number" min="0" max="255" value=${b} onInput=${e => setB(parseInt(e.target.value) || 0)} class="mt-2 w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2" />
                    </div>
                </div>
            </details>

            <button
                onClick=${() => onSend(r, g, b)}
                class="w-full px-8 py-4 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-semibold"
            >
                Aplicar Color al LED
            </button>
        </div>
    `;
};

// ============================================
// COMPONENTE: Config Tab
// ============================================

const ConfigTab = ({ onUpdate, onReboot }) => {
    const [sampleInterval, setSampleInterval] = useState(30);
    const [avgSamples, setAvgSamples] = useState(10);

    return html`
        <div>
            <h3 class="text-xl font-semibold mb-6 flex items-center">
                <svg class="w-6 h-6 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                </svg>
                Configuración del Dispositivo
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                    <label class="block text-sm font-medium mb-2">Intervalo de muestreo (segundos)</label>
                    <input type="number" value=${sampleInterval} onInput=${e => setSampleInterval(parseInt(e.target.value))} class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2" />
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2">Muestras para promedio</label>
                    <input type="number" value=${avgSamples} onInput=${e => setAvgSamples(parseInt(e.target.value))} class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2" />
                </div>
            </div>
            <div class="flex gap-4">
                <button
                    onClick=${() => onUpdate(sampleInterval, avgSamples)}
                    class="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-semibold"
                >
                    Actualizar Configuración
                </button>
                <button
                    onClick=${onReboot}
                    class="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold"
                >
                    Reiniciar Dispositivo
                </button>
            </div>
        </div>
    `;
};

// ============================================
// COMPONENTE: Schedules Tab
// ============================================

const SchedulesTab = ({ schedules, onLoadSchedules, onCreateSchedule, onDeleteSchedule }) => {
    const [name, setName] = useState('');
    const [action, setAction] = useState('on');
    const [time, setTime] = useState('');
    const [selectedDays, setSelectedDays] = useState([]);

    const dayNames = ['', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

    const toggleDay = (day) => {
        if (selectedDays.includes(day)) {
            setSelectedDays(selectedDays.filter(d => d !== day));
        } else {
            setSelectedDays([...selectedDays, day]);
        }
    };

    const handleCreate = () => {
        if (!name || !time || selectedDays.length === 0) {
            return;
        }
        onCreateSchedule(name, action, time, selectedDays);
        // Limpiar formulario
        setName('');
        setTime('');
        setSelectedDays([]);
    };

    useEffect(() => {
        onLoadSchedules();
    }, []);

    return html`
        <div>
            <h3 class="text-xl font-semibold mb-6 flex items-center">
                <svg class="w-6 h-6 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
                Programaciones del AC
            </h3>

            <!-- Lista de programaciones -->
            <div class="mb-8">
                <h4 class="text-lg font-semibold mb-4">Programaciones Activas</h4>
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-gray-700">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Nombre</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Acción</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Hora</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Días</th>
                                <th class="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Acciones</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-700">
                            ${schedules && schedules.length > 0 ? schedules.map(schedule => {
        const days = JSON.parse(schedule.days_of_week || '[]');
        const daysText = days.map(d => dayNames[d]).join(', ');
        return html`
                                    <tr class="hover:bg-gray-700">
                                        <td class="px-4 py-3 text-gray-300">${schedule.name}</td>
                                        <td class="px-4 py-3">
                                            <span class="px-3 py-1 rounded-full text-xs font-semibold ${schedule.action === 'on' ? 'bg-green-600' : 'bg-red-600'}">
                                                ${schedule.action === 'on' ? 'Encender' : 'Apagar'}
                                            </span>
                                        </td>
                                        <td class="px-4 py-3 text-gray-300">${schedule.time}</td>
                                        <td class="px-4 py-3 text-gray-400">${daysText}</td>
                                        <td class="px-4 py-3">
                                            <button
                                                onClick=${() => onDeleteSchedule(schedule.id)}
                                                class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm"
                                            >
                                                Eliminar
                                            </button>
                                        </td>
                                    </tr>
                                `;
    }) : html`
                                <tr>
                                    <td colspan="5" class="px-4 py-8 text-center text-gray-400">No hay programaciones</td>
                                </tr>
                            `}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Crear nueva programación -->
            <h4 class="text-lg font-semibold mb-4">Crear Nueva Programación</h4>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div>
                    <label class="block text-sm font-medium mb-2">Nombre</label>
                    <input
                        type="text"
                        value=${name}
                        onInput=${e => setName(e.target.value)}
                        placeholder="Ej: Encender mañana"
                        class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2"
                    />
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2">Acción</label>
                    <select
                        value=${action}
                        onChange=${e => setAction(e.target.value)}
                        class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2"
                    >
                        <option value="on">Encender</option>
                        <option value="off">Apagar</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2">Hora</label>
                    <input
                        type="time"
                        value=${time}
                        onInput=${e => setTime(e.target.value)}
                        class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-4 py-2"
                    />
                </div>
            </div>

            <div class="mb-6">
                <label class="block text-sm font-medium mb-2">Días de la semana</label>
                <div class="flex gap-2 flex-wrap">
                    ${[1, 2, 3, 4, 5, 6, 7].map(day => html`
                        <button
                            onClick=${() => toggleDay(day)}
                            class="px-4 py-2 rounded-lg cursor-pointer ${selectedDays.includes(day) ? 'bg-primary-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}"
                        >
                            ${dayNames[day]}
                        </button>
                    `)}
                </div>
            </div>

            <button
                onClick=${handleCreate}
                class="w-full px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-semibold"
            >
                Crear Programación
            </button>
        </div>
    `;
};

// ============================================
// COMPONENTE PRINCIPAL: APP
// ============================================

const App = () => {
    const [deviceInfo, setDeviceInfo] = useState(null);
    const [latestData, setLatestData] = useState(null);
    const [measurements, setMeasurements] = useState([]);
    const [acStatus, setAcStatus] = useState('unknown');
    const [acHistory, setAcHistory] = useState([]);
    const [schedules, setSchedules] = useState([]);
    const [sleepTimers, setSleepTimers] = useState([]);
    const [activeTab, setActiveTab] = useState('ac');
    const [toasts, setToasts] = useState([]);

    // Toast helper
    const showToast = (message, type = 'success') => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, message, type }]);
    };

    const removeToast = (id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    // API helper
    const apiRequest = async (url, method = 'GET', body = null) => {
        try {
            const options = {
                method,
                headers: { 'Content-Type': 'application/json' }
            };
            if (body) options.body = JSON.stringify(body);

            const response = await fetch(`${API_BASE_URL}${url}`, options);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    };

    // Load device data
    const loadData = async () => {
        try {
            const [device, latest, measurementsData, status, history] = await Promise.all([
                apiRequest(`/devices/${DEVICE_ID}`),
                apiRequest(`/devices/${DEVICE_ID}/measurements/latest`),
                apiRequest(`/devices/${DEVICE_ID}/measurements?limit=50`),
                apiRequest(`/devices/${DEVICE_ID}/ac/status`),
                apiRequest(`/devices/${DEVICE_ID}/ac/history?limit=20`)
            ]);

            setDeviceInfo(device);
            setLatestData(latest);
            setMeasurements(measurementsData.measurements || []);
            setAcStatus(status.state);
            setAcHistory(history.events || []);
        } catch (error) {
            showToast(`Error cargando datos: ${error.message}`, 'error');
        }
    };

    // AC Commands
    const sendACCommand = async (action) => {
        try {
            await apiRequest(`/devices/${DEVICE_ID}/ac/command`, 'POST', { action });
            showToast(`AC ${action === 'on' ? 'encendido' : 'apagado'} exitosamente`, 'success');
            setTimeout(loadData, 500);
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    };

    // LED Command
    const sendLEDCommand = async (r, g, b) => {
        try {
            await apiRequest(`/devices/${DEVICE_ID}/led/command`, 'POST', { r, g, b });
            showToast(`Color LED aplicado: RGB(${r}, ${g}, ${b})`, 'success');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    };

    // Config Commands
    const updateConfig = async (sampleInterval, avgSamples) => {
        try {
            await apiRequest(`/devices/${DEVICE_ID}/config`, 'POST', {
                sample_interval: sampleInterval,
                avg_samples: avgSamples
            });
            showToast('Configuración actualizada', 'success');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    };

    const rebootDevice = async () => {
        if (!confirm('¿Estás seguro de reiniciar el dispositivo?')) return;
        try {
            await apiRequest(`/devices/${DEVICE_ID}/reboot`, 'POST');
            showToast('Comando de reinicio enviado', 'success');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    };

    // Schedule Commands
    const loadSchedules = async () => {
        try {
            const response = await apiRequest(`/devices/${DEVICE_ID}/schedules`);
            setSchedules(response.schedules || []);
        } catch (error) {
            console.error('Error loading schedules:', error);
        }
    };

    const createSchedule = async (name, action, time, daysOfWeek) => {
        try {
            await apiRequest(`/devices/${DEVICE_ID}/schedules`, 'POST', {
                name,
                action,
                time,
                days_of_week: daysOfWeek
            });
            showToast('Programación creada exitosamente', 'success');
            loadSchedules();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    };

    const deleteSchedule = async (scheduleId) => {
        if (!confirm('¿Estás seguro de eliminar esta programación?')) return;
        try {
            await apiRequest(`/devices/${DEVICE_ID}/schedules/${scheduleId}`, 'DELETE');
            showToast('Programación eliminada', 'success');
            loadSchedules();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    };

    // Sleep Timer Commands
    const loadSleepTimers = async () => {
        try {
            const response = await apiRequest(`/devices/${DEVICE_ID}/sleep-timers`);
            setSleepTimers(response.timers || []);
        } catch (error) {
            console.error('Error loading sleep timers:', error);
        }
    };

    const createSleepTimer = async (action, delayMinutes) => {
        try {
            await apiRequest(`/devices/${DEVICE_ID}/sleep-timers`, 'POST', {
                action,
                delay_minutes: delayMinutes
            });
            showToast(`Temporizador creado: ${action === 'on' ? 'encender' : 'apagar'} en ${delayMinutes} minutos`, 'success');
            loadSleepTimers();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    };

    const cancelSleepTimer = async (timerId) => {
        try {
            await apiRequest(`/devices/${DEVICE_ID}/sleep-timers/${timerId}`, 'DELETE');
            showToast('Temporizador cancelado', 'success');
            loadSleepTimers();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    };

    // Initial load and auto-refresh
    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 30000);
        return () => clearInterval(interval);
    }, []);

    // Prepare chart data
    const tempChartData = measurements.map(m => ({ timestamp: m.timestamp, value: parseInt(m.temperature) }));
    const humidityChartData = measurements.map(m => ({ timestamp: m.timestamp, value: parseInt(m.humidity) }));

    // Get gradient class for AC card
    const acCardGradient = acStatus === 'on' ? 'from-blue-500 to-cyan-600' : 'from-gray-600 to-gray-700';
    const acCardValue = acStatus === 'on' ? 'Encendido' : acStatus === 'off' ? 'Apagado' : 'Desconocido';

    // Get gradient class for device card
    const deviceOnline = deviceInfo?.is_online;
    const deviceGradient = deviceOnline ? 'from-green-500 to-emerald-600' : 'from-gray-600 to-gray-700';
    const deviceValue = deviceOnline ? 'Online' : 'Offline';

    return html`
        <div>
            <!-- Header -->
            <header class="bg-gray-800 border-b border-gray-700 sticky top-0 z-50">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <svg class="w-8 h-8 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                            </svg>
                            <h1 class="text-2xl font-bold text-white">Sistema de Clima Inteligente</h1>
                        </div>
                        <button
                            onClick=${loadData}
                            class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg flex items-center space-x-2"
                        >
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                            </svg>
                            <span>Actualizar</span>
                        </button>
                    </div>
                </div>
            </header>

            <!-- Main Content -->
            <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

                <!-- Device Info -->
                ${deviceInfo && html`
                    <div class="bg-gray-800 rounded-xl shadow-xl p-6 mb-8 border border-gray-700">
                        <h2 class="text-xl font-semibold mb-4">Dispositivo</h2>
                        <div class="p-4 rounded-lg ${deviceOnline ? 'bg-green-900/30 border border-green-700' : 'bg-red-900/30 border border-red-700'}">
                            <div class="flex items-center justify-between">
                                <div>
                                    <p class="font-semibold">${deviceInfo.name}</p>
                                    <p class="text-sm text-gray-400">${deviceInfo.location || 'Sin ubicación'}</p>
                                </div>
                                <div class="text-right">
                                    <div class="flex items-center space-x-2">
                                        <span class="w-3 h-3 rounded-full ${deviceOnline ? 'bg-green-500' : 'bg-red-500'}"></span>
                                        <span class="font-semibold">${deviceOnline ? 'Online' : 'Offline'}</span>
                                    </div>
                                    <p class="text-xs text-gray-400 mt-1">${deviceInfo.last_seen ? new Date(deviceInfo.last_seen).toLocaleString() : 'Nunca'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `}

                <!-- Dashboard Cards -->
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    ${DashboardCard({
        title: 'Temperatura',
        value: latestData ? `${latestData.temperature.toFixed(1)}°C` : '--°C',
        gradient: 'from-orange-500 to-red-600',
        icon: html`<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>`
    })}
                    ${DashboardCard({
        title: 'Humedad',
        value: latestData ? `${latestData.humidity.toFixed(1)}%` : '--%',
        gradient: 'from-blue-500 to-cyan-600',
        icon: html`<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"></path>`
    })}
                    ${DashboardCard({
        title: 'Aire Acondicionado',
        value: acCardValue,
        gradient: acCardGradient,
        icon: html`<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5"></path>`
    })}
                    ${DashboardCard({
        title: 'Estado',
        value: deviceValue,
        gradient: deviceGradient,
        icon: html`<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>`
    })}
                </div>

                <!-- Charts -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                    ${ChartComponent({
        title: 'Histórico de Temperatura',
        data: tempChartData,
        color: 'rgb(249, 115, 22)',
        chartId: 'temp'
    })}
                    ${ChartComponent({
        title: 'Histórico de Humedad',
        data: humidityChartData,
        color: 'rgb(59, 130, 246)',
        chartId: 'humidity'
    })}
                </div>

                <!-- Tabs -->
                <div class="bg-gray-800 rounded-xl shadow-xl border border-gray-700 mb-8">
                    <div class="border-b border-gray-700">
                        <nav class="flex space-x-1 p-2 overflow-x-auto">
                            ${['ac', 'timer', 'led', 'schedules', 'config'].map(tab => html`
                                <button
                                    onClick=${() => setActiveTab(tab)}
                                    class="px-6 py-3 rounded-lg font-medium whitespace-nowrap ${activeTab === tab ? 'bg-primary-600 text-white' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'}"
                                >
                                    ${tab === 'ac' ? 'Control AC' : tab === 'timer' ? 'Temporizador' : tab === 'led' ? 'Control LED' : tab === 'schedules' ? 'Programaciones' : 'Configuración'}
                                </button>
                            `)}
                        </nav>
                    </div>
                    <div class="p-6">
                        ${activeTab === 'ac' && ACControlTab({ onCommand: sendACCommand, history: acHistory })}
                        ${activeTab === 'timer' && SleepTimerTab({ timers: sleepTimers, onLoadTimers: loadSleepTimers, onCreateTimer: createSleepTimer, onCancelTimer: cancelSleepTimer })}
                        ${activeTab === 'led' && LEDControlTab({ onSend: sendLEDCommand })}
                        ${activeTab === 'schedules' && SchedulesTab({ schedules, onLoadSchedules: loadSchedules, onCreateSchedule: createSchedule, onDeleteSchedule: deleteSchedule })}
                        ${activeTab === 'config' && ConfigTab({ onUpdate: updateConfig, onReboot: rebootDevice })}
                    </div>
                </div>

            </main>

            <!-- Toast Container -->
            <div class="fixed bottom-4 right-4 z-50 space-y-2">
                ${toasts.map(toast => html`
                    <${Toast}
                        key=${toast.id}
                        message=${toast.message}
                        type=${toast.type}
                        onClose=${() => removeToast(toast.id)}
                    />
                `)}
            </div>
        </div>
    `;
};

// Render the app
setTimeout(() => {
    render(html`<${App} />`, document.getElementById('app'));
}, 100);
