// TemperatureSensor.h
#ifndef TEMPERATURE_SENSOR_H
#define TEMPERATURE_SENSOR_H

#include <Arduino.h>
#include <DHT.h>

class TemperatureSensor
{
private:
  DHT dht;
  float ultimaTemperatura;
  float ultimaHumedad;

public:
  TemperatureSensor(uint8_t pin, uint8_t tipo = DHT11)
      : dht(pin, tipo), ultimaTemperatura(NAN), ultimaHumedad(NAN) {}

  void begin()
  {
    dht.begin();
  }

  bool leer()
  {
    ultimaTemperatura = dht.readTemperature();
    ultimaHumedad = dht.readHumidity();

    if (isnan(ultimaTemperatura) || isnan(ultimaHumedad))
    {
      Serial.println("Error al leer el DHT11");
      return false;
    }
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

  void imprimirDatos() const
  {
    if (!isnan(ultimaTemperatura) && !isnan(ultimaHumedad))
    {
      Serial.print("Temperatura: ");
      Serial.print(ultimaTemperatura);
      Serial.print("°C  Humedad: ");
      Serial.print(ultimaHumedad);
      Serial.println("%");
    }
  }
};

#endif