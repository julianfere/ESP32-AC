#ifndef TEMPERATURE_SENSOR_H
#define TEMPERATURE_SENSOR_H

#include <Arduino.h>
#include <DHT.h>

class TemperatureSensor
{
private:
  DHT dht;
  uint8_t pin;
  float ultimaTemperatura;
  float ultimaHumedad;
  int erroresConsecutivos;
  static const int MAX_ERRORES = 5;

public:
  TemperatureSensor(uint8_t pin, uint8_t tipo = DHT22)
      : dht(pin, tipo), pin(pin), ultimaTemperatura(NAN), ultimaHumedad(NAN), erroresConsecutivos(0) {}

  void begin()
  {
    dht.begin();
    Serial.println("✓ Sensor DHT11 iniciado");
  }

  bool leer()
  {
    float temp = dht.readTemperature();
    float hum = dht.readHumidity();

    if (isnan(temp) || isnan(hum))
    {
      erroresConsecutivos++;
      Serial.print("✗ Error al leer DHT11 (");
      Serial.print(erroresConsecutivos);
      Serial.println(" consecutivos)");

      if (erroresConsecutivos >= MAX_ERRORES)
      {
        Serial.println("⚠️ Sensor DHT11 posiblemente desconectado");
      }
      return false;
    }

    // Validar rangos razonables
    if (temp < -40 || temp > 80 || hum < 0 || hum > 100)
    {
      Serial.println("✗ Lectura fuera de rango válido");
      return false;
    }

    ultimaTemperatura = temp;
    ultimaHumedad = hum;
    erroresConsecutivos = 0;
    return true;
  }

  float getTemperatura() const
  {
    return ultimaTemperatura;
  }

  float getHumedad() const
  {
    return ultimaHumedad;
  }

  bool hayErrores() const
  {
    return erroresConsecutivos >= MAX_ERRORES;
  }

  void imprimirDatos() const
  {
    if (!isnan(ultimaTemperatura) && !isnan(ultimaHumedad))
    {
      Serial.print("🌡️  Temperatura: ");
      Serial.print(ultimaTemperatura, 1);
      Serial.print("°C  💧 Humedad: ");
      Serial.print(ultimaHumedad, 1);
      Serial.println("%");
    }
  }
};

#endif