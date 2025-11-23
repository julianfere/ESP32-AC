#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Forward declarations para callbacks
typedef void (*AcCommandCallback)(bool turnOn, uint8_t temperature, const String& mode, const String& fanSpeed);
typedef void (*LedCommandCallback)(uint8_t r, uint8_t g, uint8_t b, bool enabled);
typedef void (*ConfigUpdateCallback)(int sampleInterval, int avgSamples);

class MqttManager
{
private:
  WiFiClient wifiClient;
  PubSubClient mqtt;
  String deviceId;

  // Callbacks
  AcCommandCallback acCallback;
  LedCommandCallback ledCallback;
  ConfigUpdateCallback configCallback;

  // Para hacer accesible el callback estático
  static MqttManager *instance;

  void reconnect()
  {
    int retries = 0;
    while (!mqtt.connected() && retries < 3)
    {
      Serial.print("Conectando a MQTT...");

      // Last Will Testament: avisa si se desconecta inesperadamente
      String lwt = deviceId + "/system/status";

      if (mqtt.connect(deviceId.c_str(), lwt.c_str(), 1, true, "offline"))
      {
        Serial.println(" ✓ conectado");

        // Publicar que estamos online
        String statusTopic = deviceId + "/system/status";
        mqtt.publish(statusTopic.c_str(), "online", true);

        subscribeToTopics();
      }
      else
      {
        Serial.print(" ✗ falló, rc=");
        Serial.println(mqtt.state());
        retries++;
        delay(2000);
      }
    }
  }

  void subscribeToTopics()
  {
    mqtt.subscribe((deviceId + "/ac/command").c_str(), 1);
    mqtt.subscribe((deviceId + "/led/command").c_str(), 1);
    mqtt.subscribe((deviceId + "/config/update").c_str(), 1);
    mqtt.subscribe((deviceId + "/system/reboot").c_str(), 1);

    Serial.println("Suscrito a topics de comando");
  }

  static void messageCallback(char *topic, byte *payload, unsigned int length)
  {
    if (instance)
    {
      instance->handleMessage(topic, payload, length);
    }
  }

  void handleMessage(char *topic, byte *payload, unsigned int length)
  {
    // Convertir payload a string
    char message[length + 1];
    memcpy(message, payload, length);
    message[length] = '\0';

    Serial.print("📨 Mensaje recibido [");
    Serial.print(topic);
    Serial.print("]: ");
    Serial.println(message);

    String topicStr = String(topic);

    // Parsear JSON
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, message);

    if (error)
    {
      Serial.print("Error parseando JSON: ");
      Serial.println(error.c_str());
      return;
    }

    // Manejar comandos
    if (topicStr.endsWith("/ac/command"))
    {
      String action = doc["action"].as<String>();
      uint8_t temperature = doc["temperature"] | 24;
      String mode = doc["mode"] | "cool";
      String fanSpeed = doc["fan_speed"] | "auto";

      if (acCallback)
      {
        acCallback(action == "on", temperature, mode, fanSpeed);
      }
    }
    else if (topicStr.endsWith("/led/command"))
    {
      if (ledCallback)
      {
        uint8_t r = doc["r"] | 0;
        uint8_t g = doc["g"] | 0;
        uint8_t b = doc["b"] | 0;
        bool enabled = doc["enabled"] | true;
        ledCallback(r, g, b, enabled);
      }
    }
    else if (topicStr.endsWith("/config/update"))
    {
      if (configCallback)
      {
        int interval = doc["sample_interval"] | 30;
        int samples = doc["avg_samples"] | 10;
        configCallback(interval, samples);
      }
    }
    else if (topicStr.endsWith("/system/reboot"))
    {
      if (doc["confirm"] == true)
      {
        Serial.println("🔄 Reiniciando por comando remoto...");
        delay(1000);
        ESP.restart();
      }
    }
  }

public:
  MqttManager(const char *broker, int port, String devId)
      : mqtt(wifiClient), deviceId(devId),
        acCallback(nullptr), ledCallback(nullptr), configCallback(nullptr)
  {
    mqtt.setServer(broker, port);
    mqtt.setCallback(messageCallback);
    mqtt.setKeepAlive(60);
    mqtt.setSocketTimeout(15);
    instance = this;
  }

  void begin()
  {
    reconnect();
  }

  void loop()
  {
    if (!mqtt.connected())
    {
      reconnect();
    }
    mqtt.loop();
  }

  bool isConnected()
  {
    return mqtt.connected();
  }

  // Publicar temperatura individual
  void publishTemperature(float temp, float hum, unsigned long timestamp)
  {
    if (!mqtt.connected())
      return;

    StaticJsonDocument<128> doc;
    doc["temperature"] = round(temp * 10) / 10.0; // 1 decimal
    doc["humidity"] = round(hum * 10) / 10.0;
    doc["timestamp"] = timestamp;

    char buffer[150];
    serializeJson(doc, buffer);

    String topic = deviceId + "/sensor/raw";
    mqtt.publish(topic.c_str(), buffer, false);
  }

  // Publicar promedio
  void publishAverage(float avgTemp, float avgHum, int samples, unsigned long timestamp)
  {
    if (!mqtt.connected())
      return;

    StaticJsonDocument<128> doc;
    doc["temp"] = round(avgTemp * 10) / 10.0;
    doc["hum"] = round(avgHum * 10) / 10.0;
    doc["samples"] = samples;
    doc["timestamp"] = timestamp;

    char buffer[150];
    serializeJson(doc, buffer);

    String topic = deviceId + "/sensor/avg";
    mqtt.publish(topic.c_str(), buffer, false);

    Serial.print("📊 Promedio enviado: ");
    Serial.print(avgTemp);
    Serial.print("°C, ");
    Serial.print(avgHum);
    Serial.println("%");
  }

  // Publicar estado del AC (con retained flag)
  void publishAcStatus(bool isOn, uint8_t temperature, const String& mode, const String& fanSpeed, unsigned long timestamp)
  {
    if (!mqtt.connected())
      return;

    StaticJsonDocument<256> doc;
    doc["state"] = isOn ? "on" : "off";
    doc["temperature"] = temperature;
    doc["mode"] = mode;
    doc["fan_speed"] = fanSpeed;
    doc["confirmed"] = true;
    doc["timestamp"] = timestamp;

    char buffer[256];
    serializeJson(doc, buffer);

    String topic = deviceId + "/ac/status";
    mqtt.publish(topic.c_str(), buffer, true); // retained = true

    Serial.printf("❄️ Estado AC publicado: %s, %d°C, %s, %s\n",
                  isOn ? "ON" : "OFF", temperature, mode.c_str(), fanSpeed.c_str());
  }

  // Publicar estado del LED
  void publishLedStatus(uint8_t r, uint8_t g, uint8_t b, bool enabled)
  {
    if (!mqtt.connected())
      return;

    StaticJsonDocument<128> doc;
    doc["r"] = r;
    doc["g"] = g;
    doc["b"] = b;
    doc["enabled"] = enabled;

    char buffer[128];
    serializeJson(doc, buffer);

    String topic = deviceId + "/led/status";
    mqtt.publish(topic.c_str(), buffer, true); // retained = true
  }

  // Heartbeat del sistema
  void publishHeartbeat(unsigned long uptime, int rssi)
  {
    if (!mqtt.connected())
      return;

    StaticJsonDocument<128> doc;
    doc["uptime"] = uptime;
    doc["wifi_rssi"] = rssi;
    doc["free_heap"] = ESP.getFreeHeap();

    char buffer[150];
    serializeJson(doc, buffer);

    String topic = deviceId + "/system/heartbeat";
    mqtt.publish(topic.c_str(), buffer, false);
  }

  // Setters para callbacks
  void setAcCommandCallback(AcCommandCallback callback)
  {
    acCallback = callback;
  }

  void setLedCommandCallback(LedCommandCallback callback)
  {
    ledCallback = callback;
  }

  void setConfigUpdateCallback(ConfigUpdateCallback callback)
  {
    configCallback = callback;
  }

  String getDeviceId()
  {
    return deviceId;
  }
};

// Inicializar puntero estático
MqttManager *MqttManager::instance = nullptr;

#endif