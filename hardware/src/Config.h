#ifndef CONFIG_H
#define CONFIG_H

// ============================================
// CONFIGURACIÓN WiFi
// ============================================
#define WIFI_SSID "FereCasa_IoT"
#define WIFI_PASSWORD "0042070239"

// ============================================
// CONFIGURACIÓN MQTT
// ============================================
#define MQTT_BROKER "192.168.0.149"
#define MQTT_PORT 1883
#define DEVICE_ID "room_01"

// ============================================
// PINES HARDWARE
// ============================================
#define IR_SEND_PIN 4
#define DHT_PIN 5
#define PIN_RED 16
#define PIN_GREEN 17
#define PIN_BLUE 18

// ============================================
// CONFIGURACIÓN SENSORES
// ============================================
#define SAMPLES_FOR_AVERAGE 10
#define SAMPLE_INTERVAL_MS 30000    // 30 segundos entre mediciones
#define HEARTBEAT_INTERVAL_MS 60000 // 1 minuto - heartbeat del sistema

// ============================================
// NTP para sincronización de tiempo
// ============================================
#define NTP_SERVER "pool.ntp.org"
#define NTP_OFFSET (-3 * 3600)    // UTC-3 (Argentina) - Cambiar según tu zona horaria
#define NTP_UPDATE_INTERVAL 60000 // Actualizar cada minuto

#endif