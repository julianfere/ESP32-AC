#include <Arduino.h>
#include <WiFi.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include "Config.h"
#include "AcController.h"
#include "RgbLed.h"
#include "TemperatureSensor.h"
#include "MqttManager.h"
#include "SensorBuffer.h"
#include "Config.h"

#define IR_SEND_PIN 4
#define DHT_PIN 5
#define PIN_RED 16
#define PIN_GREEN 17
#define PIN_BLUE 18

AcController aire(IR_SEND_PIN);
RgbLed led(PIN_RED, PIN_GREEN, PIN_BLUE);
TemperatureSensor sensor(DHT_PIN);
MqttManager mqtt(MQTT_BROKER, MQTT_PORT, DEVICE_ID);

// ============================================
#pragma region BUFFERS PARA PROMEDIOS
// ============================================
CircularBuffer<float, 10> tempBuffer;
CircularBuffer<float, 10> humBuffer;

// ============================================
// NTP CLIENT
// ============================================
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, NTP_SERVER, NTP_OFFSET, NTP_UPDATE_INTERVAL);

// ============================================
// VARIABLES GLOBALES
// ============================================
unsigned long lastSample = 0;
unsigned long lastHeartbeat = 0;
int sampleInterval = SAMPLE_INTERVAL_MS;
int avgSamples = SAMPLES_FOR_AVERAGE;

// ============================================
#pragma region CALLBACKS MQTT
// ============================================

void onAcCommandReceived(bool turnOn)
{
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  Serial.print("📡 Comando AC recibido: ");
  Serial.println(turnOn ? "ENCENDER" : "APAGAR");

  bool success = false;
  if (turnOn)
  {
    success = aire.encender();
  }
  else
  {
    success = aire.apagar();
  }

  if (success)
  {
    // Parpadeo LED para confirmar
    led.blink(0, 255, 0, 2, 150);

    // Confirmar estado al backend
    unsigned long timestamp = timeClient.getEpochTime();
    mqtt.publishAcStatus(aire.estaEncendido(), timestamp);
  }
  else
  {
    // Error - parpadeo rojo
    led.blink(255, 0, 0, 3, 100);
  }

  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

void onLedCommandReceived(uint8_t r, uint8_t g, uint8_t b, bool enabled)
{
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  Serial.print("💡 Comando LED recibido: RGB(");
  Serial.print(r);
  Serial.print(", ");
  Serial.print(g);
  Serial.print(", ");
  Serial.print(b);
  Serial.println(")");

  led.setEnabledFeedback(enabled);

  led.setColor(r, g, b);
  mqtt.publishLedStatus(r, g, b, enabled);

  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

void onConfigUpdateReceived(int newSampleInterval, int newAvgSamples)
{
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  Serial.println("⚙️  Configuración actualizada:");
  Serial.print("   Sample Interval: ");
  Serial.print(newSampleInterval);
  Serial.println("s");
  Serial.print("   Avg Samples: ");
  Serial.println(newAvgSamples);

  sampleInterval = newSampleInterval * 1000; // Convertir a ms
  avgSamples = newAvgSamples;

  // Limpiar buffers al cambiar configuración
  tempBuffer.clear();
  humBuffer.clear();

  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

// ============================================
#pragma region SETUP
// ============================================

void setup()
{
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n");
  Serial.println("╔════════════════════════════════════╗");
  Serial.println("║   SISTEMA DE CLIMA INTELIGENTE    ║");
  Serial.println("║         ESP32 + MQTT v1.0          ║");
  Serial.println("╚════════════════════════════════════╝");
  Serial.println();

  // ============================================
  // CONECTAR WiFi
  // ============================================
  Serial.print("📶 Conectando a WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int wifiRetries = 0;
  while (WiFi.status() != WL_CONNECTED && wifiRetries < 30)
  {
    delay(500);
    Serial.print(".");
    wifiRetries++;
  }

  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("\n✗ No se pudo conectar a WiFi");
    Serial.println("Reiniciando en 5 segundos...");
    delay(5000);
    ESP.restart();
  }

  Serial.println(" ✓");
  Serial.print("   IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("   RSSI: ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
  Serial.println();

  // ============================================
  // INICIALIZAR NTP
  // ============================================
  Serial.print("🕐 Sincronizando hora NTP...");
  timeClient.begin();
  timeClient.update();
  Serial.println(" ✓");
  Serial.print("   Hora actual: ");
  Serial.println(timeClient.getFormattedTime());
  Serial.println();

  // ============================================
  // INICIALIZAR HARDWARE
  // ============================================
  Serial.println("🔧 Inicializando hardware:");
  sensor.begin();
  led.begin();
  aire.begin();
  Serial.println();

  // ============================================
  // CONECTAR MQTT
  // ============================================
  Serial.println("🌐 Conectando a MQTT Broker:");
  Serial.print("   Broker: ");
  Serial.print(MQTT_BROKER);
  Serial.print(":");
  Serial.println(MQTT_PORT);
  Serial.print("   Device ID: ");
  Serial.println(DEVICE_ID);

  mqtt.begin();

  // Configurar callbacks
  mqtt.setAcCommandCallback(onAcCommandReceived);
  mqtt.setLedCommandCallback(onLedCommandReceived);
  mqtt.setConfigUpdateCallback(onConfigUpdateReceived);
  Serial.println();

  // ============================================
  // SEÑAL DE INICIO
  // ============================================
  Serial.println("✅ Sistema iniciado correctamente");
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  Serial.println();

  // Parpadeo verde de confirmación
  led.blink(255, 255, 255, 6, 50);

  // Publicar estado inicial
  unsigned long timestamp = timeClient.getEpochTime();
  mqtt.publishAcStatus(aire.estaEncendido(), timestamp);

  uint8_t r, g, b;
  led.getColor(r, g, b);
  mqtt.publishLedStatus(r, g, b, true);
}

// ============================================
#pragma region LOOP PRINCIPAL
// ============================================

void loop()
{
  unsigned long now = millis();

  // Mantener conexión MQTT
  mqtt.loop();

  // Actualizar hora NTP
  timeClient.update();

  // ============================================
  // TOMAR MUESTRAS DE SENSORES
  // ============================================
  if (now - lastSample >= sampleInterval)
  {
    lastSample = now;

    if (sensor.leer())
    {
      float temp = sensor.getTemperatura();
      float hum = sensor.getHumedad();
      unsigned long timestamp = timeClient.getEpochTime();

      // Mostrar datos
      sensor.imprimirDatos();

      // Enviar medición raw a MQTT
      mqtt.publishTemperature(temp, hum, timestamp);

      // Agregar a buffers
      tempBuffer.push(temp);
      humBuffer.push(hum);

      // Si completamos las muestras necesarias, enviar promedio
      if (tempBuffer.size() >= avgSamples)
      {
        float avgTemp = tempBuffer.average(avgSamples);
        float avgHum = humBuffer.average(avgSamples);

        mqtt.publishAverage(avgTemp, avgHum, avgSamples, timestamp);

        // Limpiar buffers
        tempBuffer.clear();
        humBuffer.clear();
      }
    }
    else
    {
      // Error en lectura - LED rojo
      if (sensor.hayErrores())
      {
        led.setRojo();
      }
    }
  }

  // ============================================
  // HEARTBEAT DEL SISTEMA
  // ============================================
  if (now - lastHeartbeat >= HEARTBEAT_INTERVAL_MS)
  {
    lastHeartbeat = now;

    int rssi = WiFi.RSSI();
    mqtt.publishHeartbeat(now / 1000, rssi);

    Serial.print("💓 Heartbeat | Uptime: ");
    Serial.print(now / 1000);
    Serial.print("s | RSSI: ");
    Serial.print(rssi);
    Serial.print(" dBm | Free Heap: ");
    Serial.print(ESP.getFreeHeap());
    Serial.println(" bytes");
  }

  // Pequeño delay para no saturar el CPU
  delay(10);
}