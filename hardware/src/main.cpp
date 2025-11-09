#include <Arduino.h>
#include "AcController.h"
#include "RgbLed.h"
#include "TemperatureSensor.h"

#define IR_SEND_PIN 4
#define DHT_PIN 5
#define PIN_RED 16
#define PIN_GREEN 17
#define PIN_BLUE 18

AcController aire(IR_SEND_PIN);
RgbLed led(PIN_RED, PIN_GREEN, PIN_BLUE);
TemperatureSensor sensor(DHT_PIN);

void actualizarLedSegunTemperatura(float temperatura)
{
  if (temperatura < 20)
  {
    led.setAzul(); // Frío
  }
  else if (temperatura < 25)
  {
    led.setVerde(); // Agradable
  }
  else if (temperatura < 30)
  {
    led.setAmarillo(); // Cálido
  }
  else
  {
    led.setRojo(); // Caliente
  }
}

void setup()
{
  Serial.begin(115200);
  Serial.println("Iniciando sistema...");

  // Inicializar componentes
  sensor.begin();
  led.begin();
  aire.begin();

  Serial.println("Sistema iniciado correctamente");
}

void loop()
{
  // Leer sensor
  if (sensor.leer())
  {
    // Mostrar datos
    sensor.imprimirDatos();

    // Actualizar LED según temperatura
    actualizarLedSegunTemperatura(sensor.getTemperatura());
  }
  else
  {
    // Error en lectura - LED rojo
    led.setRojo();
  }

  delay(2000);
}
