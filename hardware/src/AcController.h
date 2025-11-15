#ifndef AC_CONTROLLER_H
#define AC_CONTROLLER_H

#include <Arduino.h>
#include <IRremote.hpp>

class AcController
{
private:
  uint8_t irPin;
  bool encendido;
  unsigned long ultimoCambio;
  const unsigned long MIN_DELAY_BETWEEN_COMMANDS = 2000; // 2 segundos entre comandos

  const uint16_t comandoEncender[227] = {
      3100, 1600, 500, 1100, 450, 1100, 450, 300, 500, 350, 450, 350, 450, 1100,
      450, 350, 450, 350, 450, 1150, 400, 1150, 400, 400, 400, 1150, 450, 350,
      450, 350, 450, 1100, 450, 1150, 400, 400, 400, 1150, 400, 1150, 400, 400,
      400, 400, 400, 1150, 450, 350, 450, 350, 450, 1100, 450, 350, 450, 350,
      450, 350, 450, 350, 450, 350, 450, 350, 450, 350, 400, 400, 400, 400,
      400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400,
      400, 400, 400, 1150, 400, 400, 400, 400, 400, 1150, 450, 350, 450, 350,
      400, 400, 400, 1150, 450, 350, 450, 350, 450, 350, 450, 350, 450, 350,
      450, 350, 450, 350, 400, 400, 400, 400, 400, 1150, 450, 350, 450, 350,
      450, 350, 450, 350, 450, 350, 450, 350, 450, 350, 400, 400, 400, 400,
      400, 400, 400, 1150, 400, 400, 450, 350, 450, 350, 450, 350, 400, 400,
      400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400,
      400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400,
      400, 400, 400, 400, 400, 400, 350, 450, 400, 400, 350, 450, 400, 400,
      400, 400, 400, 400, 350, 450, 350, 450, 350, 450, 350, 450, 350, 1200,
      400, 1150, 400, 1150, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400,
      400, 400, 400};

  const uint16_t comandoApagar[227] = {
      3100, 1600, 450, 1100, 500, 1100, 450, 350, 450, 350, 450, 350, 450, 1100,
      450, 400, 400, 350, 450, 1150, 400, 1150, 400, 400, 400, 1150, 400, 400,
      400, 400, 400, 1150, 400, 1150, 400, 400, 450, 1150, 400, 1150, 400, 400,
      400, 400, 400, 1150, 400, 400, 400, 400, 400, 1150, 400, 400, 400, 400,
      400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400,
      400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400,
      400, 400, 400, 400, 400, 400, 400, 350, 400, 1200, 400, 400, 400, 400,
      400, 1150, 400, 1150, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400,
      400, 400, 400, 400, 400, 400, 400, 400, 400, 1150, 400, 450, 350, 400,
      400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400,
      400, 400, 400, 1150, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400,
      400, 400, 400, 400, 400, 400, 400, 400, 350, 450, 350, 450, 350, 450,
      350, 450, 350, 450, 350, 450, 350, 450, 350, 450, 350, 450, 350, 450,
      350, 450, 350, 450, 350, 450, 350, 450, 350, 400, 400, 400, 400, 400,
      400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 1150,
      400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 400, 350, 500,
      300, 450, 400};

public:
  AcController(uint8_t pin) : irPin(pin), encendido(false), ultimoCambio(0) {}

  void begin()
  {
    IrSender.begin(irPin);
    Serial.println("✓ Controlador AC iniciado");
  }

  bool encender()
  {
    // Evitar comandos muy seguidos
    if (millis() - ultimoCambio < MIN_DELAY_BETWEEN_COMMANDS)
    {
      Serial.println("⚠️ Esperando delay mínimo entre comandos AC");
      return false;
    }

    if (encendido)
    {
      Serial.println("ℹ️ AC ya está encendido");
      return true;
    }

    Serial.println("📡 Enviando comando: Encender AC");
    IrSender.sendRaw(comandoEncender, 227, 38);
    encendido = true;
    ultimoCambio = millis();
    return true;
  }

  bool apagar()
  {
    if (millis() - ultimoCambio < MIN_DELAY_BETWEEN_COMMANDS)
    {
      Serial.println("⚠️ Esperando delay mínimo entre comandos AC");
      return false;
    }

    if (!encendido)
    {
      Serial.println("ℹ️ AC ya está apagado");
      return true;
    }

    Serial.println("📡 Enviando comando: Apagar AC");
    IrSender.sendRaw(comandoApagar, 227, 38);
    encendido = false;
    ultimoCambio = millis();
    return true;
  }

  bool estaEncendido() const
  {
    return encendido;
  }

  void setEstado(bool estado)
  {
    encendido = estado;
  }
};

#endif