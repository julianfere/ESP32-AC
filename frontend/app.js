// Configuración de la API
const API_BASE_URL = 'http://localhost:8000';

// Variable global para el dispositivo seleccionado
let selectedDevice = '';

// ============================================
// FUNCIONES DE UTILIDAD
// ============================================

function showResponse(elementId, data, isError = false) {
    const element = document.getElementById(elementId);
    element.className = `response ${isError ? 'error' : 'success'}`;
    element.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

function getSelectedDevice() {
    const deviceSelect = document.getElementById('deviceSelect');
    return deviceSelect.value;
}

function updateColorPreview() {
    const r = parseInt(document.getElementById('redValue').value) || 0;
    const g = parseInt(document.getElementById('greenValue').value) || 0;
    const b = parseInt(document.getElementById('blueValue').value) || 0;

    const colorPreview = document.getElementById('colorPreview');
    colorPreview.style.backgroundColor = `rgb(${r}, ${g}, ${b})`;
}

async function makeRequest(url, method = 'GET', body = null) {
    try {
        console.log(`Haciendo request ${method} a: ${API_BASE_URL}${url}`);

        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };

        if (body) {
            options.body = JSON.stringify(body);
            console.log('Body:', body);
        }

        const response = await fetch(`${API_BASE_URL}${url}`, options);
        console.log('Response status:', response.status);

        const data = await response.json();
        console.log('Response data:', data);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${JSON.stringify(data)}`);
        }

        return data;
    } catch (error) {
        console.error('Error en makeRequest:', error);
        throw error;
    }
}

// ============================================
// FUNCIONES DE DISPOSITIVOS
// ============================================

async function loadDevices() {
    try {
        console.log('Cargando dispositivos...');
        const response = await makeRequest('/devices');
        console.log('Respuesta recibida:', response);

        // Extraer el array de dispositivos de la respuesta
        const devices = response.devices || response;
        console.log('Array de dispositivos:', devices);

        const deviceSelect = document.getElementById('deviceSelect');

        // Limpiar opciones existentes
        deviceSelect.innerHTML = '<option value="">-- Seleccionar dispositivo --</option>';

        // Verificar si devices es un array
        if (Array.isArray(devices) && devices.length > 0) {
            // Agregar cada dispositivo
            devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.device_id;
                option.textContent = `${device.device_id} - ${device.name} (${device.location || 'Sin ubicación'})`;
                deviceSelect.appendChild(option);
                console.log(`Dispositivo agregado: ${device.device_id}`);
            });
            showResponse('healthResponse', { message: `${devices.length} dispositivos cargados exitosamente`, devices: devices });
        } else {
            showResponse('healthResponse', { message: 'No se encontraron dispositivos', response: response });
        }

    } catch (error) {
        console.error('Error cargando dispositivos:', error);
        showResponse('healthResponse', { error: error.message }, true);
    }
}

async function loadDeviceInfo() {
    const deviceId = getSelectedDevice();
    const deviceInfo = document.getElementById('deviceInfo');

    if (!deviceId) {
        deviceInfo.style.display = 'none';
        return;
    }

    try {
        const device = await makeRequest(`/devices/${deviceId}`);
        deviceInfo.style.display = 'block';
        deviceInfo.innerHTML = `
            <strong>Dispositivo:</strong> ${device.device_id}<br>
            <strong>Ubicación:</strong> ${device.location || 'No especificada'}<br>
            <strong>Última conexión:</strong> ${device.last_seen || 'Nunca'}<br>
            <strong>Estado:</strong> ${device.is_online ? '🟢 Conectado' : '🔴 Desconectado'}
        `;
        selectedDevice = deviceId;
    } catch (error) {
        deviceInfo.style.display = 'block';
        deviceInfo.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
    }
}

// ============================================
// FUNCIONES DE MEDICIONES
// ============================================

async function getMeasurements() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    try {
        const measurements = await makeRequest(`/devices/${deviceId}/measurements`);
        showResponse('measurementsResponse', measurements);
    } catch (error) {
        showResponse('measurementsResponse', { error: error.message }, true);
    }
}

async function getLatestMeasurement() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    try {
        const measurement = await makeRequest(`/devices/${deviceId}/measurements/latest`);
        showResponse('measurementsResponse', measurement);
    } catch (error) {
        showResponse('measurementsResponse', { error: error.message }, true);
    }
}

async function getAverages() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    try {
        const averages = await makeRequest(`/devices/${deviceId}/averages`);
        showResponse('measurementsResponse', averages);
    } catch (error) {
        showResponse('measurementsResponse', { error: error.message }, true);
    }
}

async function getStats() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    try {
        const stats = await makeRequest(`/devices/${deviceId}/stats`);
        showResponse('measurementsResponse', stats);
    } catch (error) {
        showResponse('measurementsResponse', { error: error.message }, true);
    }
}

// ============================================
// FUNCIONES DE AIRE ACONDICIONADO
// ============================================

async function sendACCommand(action) {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    try {
        const result = await makeRequest(`/devices/${deviceId}/ac/command`, 'POST', { action: action });
        showResponse('acResponse', result);
    } catch (error) {
        showResponse('acResponse', { error: error.message }, true);
    }
}

async function getACStatus() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    try {
        const status = await makeRequest(`/devices/${deviceId}/ac/status`);
        showResponse('acResponse', status);
    } catch (error) {
        showResponse('acResponse', { error: error.message }, true);
    }
}

async function getACHistory() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    try {
        const history = await makeRequest(`/devices/${deviceId}/ac/history`);
        showResponse('acResponse', history);
    } catch (error) {
        showResponse('acResponse', { error: error.message }, true);
    }
}

// ============================================
// FUNCIONES DE LED
// ============================================

async function sendLEDCommand() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    const r = parseInt(document.getElementById('redValue').value) || 0;
    const g = parseInt(document.getElementById('greenValue').value) || 0;
    const b = parseInt(document.getElementById('blueValue').value) || 0;

    try {
        const result = await makeRequest(`/devices/${deviceId}/led/command`, 'POST', { r, g, b });
        showResponse('ledResponse', result);
    } catch (error) {
        showResponse('ledResponse', { error: error.message }, true);
    }
}

// ============================================
// FUNCIONES DE CONFIGURACIÓN
// ============================================

async function updateConfig() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    const sampleInterval = parseInt(document.getElementById('sampleInterval').value);
    const avgSamples = parseInt(document.getElementById('avgSamples').value);

    if (!sampleInterval || !avgSamples) {
        alert('Por favor ingresa valores válidos para la configuración');
        return;
    }

    try {
        const result = await makeRequest(`/devices/${deviceId}/config`, 'POST', {
            sample_interval: sampleInterval,
            avg_samples: avgSamples
        });
        showResponse('configResponse', result);
    } catch (error) {
        showResponse('configResponse', { error: error.message }, true);
    }
}

async function rebootDevice() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    if (!confirm('¿Estás seguro de que quieres reiniciar el dispositivo?')) {
        return;
    }

    try {
        const result = await makeRequest(`/devices/${deviceId}/reboot`, 'POST');
        showResponse('configResponse', result);
    } catch (error) {
        showResponse('configResponse', { error: error.message }, true);
    }
}

// ============================================
// FUNCIONES DE PROGRAMACIONES
// ============================================

async function getSchedules() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    try {
        const schedules = await makeRequest(`/devices/${deviceId}/schedules`);
        showResponse('scheduleResponse', schedules);
    } catch (error) {
        showResponse('scheduleResponse', { error: error.message }, true);
    }
}

async function createSchedule() {
    const deviceId = getSelectedDevice();
    if (!deviceId) {
        alert('Por favor selecciona un dispositivo primero');
        return;
    }

    const name = document.getElementById('scheduleName').value;
    const action = document.getElementById('scheduleAction').value;
    const time = document.getElementById('scheduleTime').value;

    if (!name || !time) {
        alert('Por favor completa el nombre y la hora de la programación');
        return;
    }

    // Obtener días seleccionados
    const daysOfWeek = [];
    for (let i = 1; i <= 7; i++) {
        const checkbox = document.getElementById(`day${i}`);
        if (checkbox.checked) {
            daysOfWeek.push(i);
        }
    }

    if (daysOfWeek.length === 0) {
        alert('Por favor selecciona al menos un día de la semana');
        return;
    }

    try {
        const result = await makeRequest(`/devices/${deviceId}/schedules`, 'POST', {
            name: name,
            action: action,
            time: time,
            days_of_week: daysOfWeek
        });
        showResponse('scheduleResponse', result);

        // Limpiar el formulario
        document.getElementById('scheduleName').value = '';
        document.getElementById('scheduleTime').value = '';
        for (let i = 1; i <= 7; i++) {
            document.getElementById(`day${i}`).checked = false;
        }
    } catch (error) {
        showResponse('scheduleResponse', { error: error.message }, true);
    }
}

// ============================================
// FUNCIONES DEL SISTEMA
// ============================================

async function checkHealth() {
    try {
        const health = await makeRequest('/health');
        showResponse('healthResponse', health);
    } catch (error) {
        showResponse('healthResponse', { error: error.message }, true);
    }
}

async function testConnection() {
    try {
        console.log('Probando conexión...');
        showResponse('healthResponse', { message: 'Probando conexión con la API...' });

        // Probar endpoint básico
        const health = await makeRequest('/health');
        console.log('Health check exitoso:', health);

        // Probar endpoint de dispositivos
        const response = await makeRequest('/devices');
        console.log('Respuesta de dispositivos:', response);

        // Extraer el array de dispositivos
        const devices = response.devices || response;
        console.log('Array de dispositivos extraído:', devices);

        showResponse('healthResponse', {
            message: 'Conexión exitosa ✅',
            api_health: health,
            devices_count: Array.isArray(devices) ? devices.length : 'Error en formato',
            devices: devices
        });

        // Actualizar select de dispositivos
        if (Array.isArray(devices)) {
            const deviceSelect = document.getElementById('deviceSelect');
            deviceSelect.innerHTML = '<option value="">-- Seleccionar dispositivo --</option>';

            devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.device_id;
                option.textContent = `${device.device_id} - ${device.name} (${device.location || 'Sin ubicación'})`;
                deviceSelect.appendChild(option);
                console.log(`Dispositivo agregado en test: ${device.device_id}`);
            });
        }

    } catch (error) {
        console.error('Error en test de conexión:', error);
        showResponse('healthResponse', {
            message: 'Error de conexión ❌',
            error: error.message,
            api_url: API_BASE_URL
        }, true);
    }
}

// ============================================
// INICIALIZACIÓN
// ============================================

// Cargar dispositivos al iniciar la página
window.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado, inicializando...');

    // Verificar que los elementos necesarios existan
    const deviceSelect = document.getElementById('deviceSelect');
    const healthResponse = document.getElementById('healthResponse');

    if (!deviceSelect) {
        console.error('No se encontró el elemento deviceSelect');
        return;
    }

    if (!healthResponse) {
        console.error('No se encontró el elemento healthResponse');
        return;
    }

    console.log('Elementos DOM encontrados, cargando dispositivos...');
    loadDevices();
    updateColorPreview();
});

// Auto-refresh cada 30 segundos para mantener datos actualizados
setInterval(function() {
    if (selectedDevice) {
        loadDeviceInfo();
    }
}, 30000);