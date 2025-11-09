#ifndef RGB_LED_H
#define RGB_LED_H

#include <Arduino.h>

class RgbLed
{
private:
  uint8_t pinRed;
  uint8_t pinGreen;
  uint8_t pinBlue;

  uint8_t channelRed;
  uint8_t channelGreen;
  uint8_t channelBlue;

  uint8_t currentR;
  uint8_t currentG;
  uint8_t currentB;

  static const uint16_t PWM_FREQ = 5000;
  static const uint8_t PWM_RESOLUTION = 8;

public:
  RgbLed(uint8_t red, uint8_t green, uint8_t blue,
         uint8_t chRed = 0, uint8_t chGreen = 1, uint8_t chBlue = 2)
      : pinRed(red), pinGreen(green), pinBlue(blue),
        channelRed(chRed), channelGreen(chGreen), channelBlue(chBlue),
        currentR(0), currentG(0), currentB(0) {}

  void begin()
  {
    // Configurar canales PWM
    ledcSetup(channelRed, PWM_FREQ, PWM_RESOLUTION);
    ledcSetup(channelGreen, PWM_FREQ, PWM_RESOLUTION);
    ledcSetup(channelBlue, PWM_FREQ, PWM_RESOLUTION);

    // Asociar canales a pines
    ledcAttachPin(pinRed, channelRed);
    ledcAttachPin(pinGreen, channelGreen);
    ledcAttachPin(pinBlue, channelBlue);

    // Apagar el LED al inicio
    setColor(0, 0, 0);

    Serial.println("✓ LED RGB iniciado");
  }

  void setColor(uint8_t red, uint8_t green, uint8_t blue)
  {
    currentR = red;
    currentG = green;
    currentB = blue;

    ledcWrite(channelRed, red);
    ledcWrite(channelGreen, green);
    ledcWrite(channelBlue, blue);
  }

  void getColor(uint8_t &red, uint8_t &green, uint8_t &blue)
  {
    red = currentR;
    green = currentG;
    blue = currentB;
  }

  // Colores predefinidos
  void setRojo() { setColor(255, 0, 0); }
  void setVerde() { setColor(0, 255, 0); }
  void setAzul() { setColor(0, 0, 255); }
  void setAmarillo() { setColor(255, 255, 0); }
  void setMagenta() { setColor(255, 0, 255); }
  void setCian() { setColor(0, 255, 255); }
  void setBlanco() { setColor(255, 255, 255); }
  void setApagado() { setColor(0, 0, 0); }

  // Efecto de parpadeo
  void blink(uint8_t r, uint8_t g, uint8_t b, int times = 3, int delayMs = 200)
  {
    for (int i = 0; i < times; i++)
    {
      setColor(r, g, b);
      delay(delayMs);
      setApagado();
      delay(delayMs);
    }
  }
};

#endif