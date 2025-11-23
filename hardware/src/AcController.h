#ifndef AC_CONTROLLER_H
#define AC_CONTROLLER_H

#include <Arduino.h>
#include <IRremote.hpp>

// Midea AC Protocol Constants
enum class AcMode : uint8_t
{
  COOL = 0b0000,
  HEAT = 0b1100,
  AUTO = 0b1000,
  FAN = 0b0100,
  DRY = 0b0010
};

enum class FanSpeed : uint8_t
{
  AUTO = 0b1011,
  F_LOW = 0b1001,
  MEDIUM = 0b0101,
  F_HIGH = 0b0011
};

class AcController
{
private:
  uint8_t irPin;
  bool encendido;
  uint8_t temperatura; // 17-30°C
  AcMode modo;
  FanSpeed fanSpeed;
  unsigned long ultimoCambio;
  const unsigned long MIN_DELAY_BETWEEN_COMMANDS = 2000;

  // Midea protocol timing (in microseconds)
  // T = 21 pulses at 38kHz ≈ 553µs
  static const uint16_t T_UNIT = 553;
  static const uint16_t HEADER_MARK = T_UNIT * 8;  // 4424µs
  static const uint16_t HEADER_SPACE = T_UNIT * 8; // 4424µs
  static const uint16_t BIT_MARK = T_UNIT;         // 553µs
  static const uint16_t ONE_SPACE = T_UNIT * 3;    // 1659µs
  static const uint16_t ZERO_SPACE = T_UNIT;       // 553µs

  // Temperature lookup table (17-30°C -> nibble value)
  const uint8_t tempToNibble[14] = {
      0b0000, // 17°C
      0b0001, // 18°C
      0b0011, // 19°C
      0b0010, // 20°C
      0b0110, // 21°C
      0b0111, // 22°C
      0b0101, // 23°C
      0b0100, // 24°C
      0b1100, // 25°C
      0b1101, // 26°C
      0b1001, // 27°C
      0b1000, // 28°C
      0b1010, // 29°C
      0b1011  // 30°C
  };

  void buildCommand(uint8_t *data, bool powerOn)
  {
    // Byte 0: Magic number
    data[0] = 0xB2;

    // Byte 1: [fan_speed (4 bits)][state (4 bits)]
    uint8_t stateNibble = powerOn ? 0b1111 : 0b1011;
    data[1] = (static_cast<uint8_t>(fanSpeed) << 4) | stateNibble;

    // Byte 2: [temperature (4 bits)][mode (4 bits)]
    uint8_t tempNibble;
    if (!powerOn)
    {
      tempNibble = 0b1110; // Off state
    }
    else
    {
      int tempIndex = constrain(temperatura - 17, 0, 13);
      tempNibble = tempToNibble[tempIndex];
    }
    data[2] = (tempNibble << 4) | static_cast<uint8_t>(modo);
  }

  void sendMideaCommand(const uint8_t *data)
  {
    // Calculate raw signal length
    // Header (2) + 6 bytes * 8 bits * 2 (mark+space) + stop bit (2) = 100
    // Repeated twice = 200 + gap between = ~201
    uint16_t rawData[200];
    int idx = 0;

    // Send twice for redundancy
    for (int repeat = 0; repeat < 2; repeat++)
    {
      // Header
      rawData[idx++] = HEADER_MARK;
      rawData[idx++] = HEADER_SPACE;

      // Send 3 data bytes, each followed by its complement
      for (int i = 0; i < 3; i++)
      {
        // Original byte
        for (int bit = 7; bit >= 0; bit--)
        {
          rawData[idx++] = BIT_MARK;
          rawData[idx++] = (data[i] & (1 << bit)) ? ONE_SPACE : ZERO_SPACE;
        }
        // Inverted byte
        uint8_t inverted = ~data[i];
        for (int bit = 7; bit >= 0; bit--)
        {
          rawData[idx++] = BIT_MARK;
          rawData[idx++] = (inverted & (1 << bit)) ? ONE_SPACE : ZERO_SPACE;
        }
      }

      // Stop bit
      rawData[idx++] = BIT_MARK;

      // Gap between repetitions (or final space)
      if (repeat == 0)
      {
        rawData[idx++] = HEADER_SPACE;
      }
    }

    IrSender.sendRaw(rawData, idx, 38);
  }

public:
  AcController(uint8_t pin) : irPin(pin), encendido(false), temperatura(24),
                              modo(AcMode::COOL), fanSpeed(FanSpeed::AUTO),
                              ultimoCambio(0) {}

  void begin()
  {
    IrSender.begin(irPin);
    Serial.println("✓ Controlador AC Midea iniciado");
  }

  bool enviarComando(bool powerOn, uint8_t temp, const String &modeStr, const String &fanStr)
  {
    if (millis() - ultimoCambio < MIN_DELAY_BETWEEN_COMMANDS)
    {
      Serial.println("⚠️ Esperando delay mínimo entre comandos AC");
      return false;
    }

    // Parse mode
    if (modeStr == "cool")
      modo = AcMode::COOL;
    else if (modeStr == "heat")
      modo = AcMode::HEAT;
    else if (modeStr == "auto")
      modo = AcMode::AUTO;
    else if (modeStr == "fan")
      modo = AcMode::FAN;
    else if (modeStr == "dry")
      modo = AcMode::DRY;

    // Parse fan speed
    if (fanStr == "auto")
      fanSpeed = FanSpeed::AUTO;
    else if (fanStr == "low")
      fanSpeed = FanSpeed::F_LOW;
    else if (fanStr == "medium")
      fanSpeed = FanSpeed::MEDIUM;
    else if (fanStr == "high")
      fanSpeed = FanSpeed::F_HIGH;

    // Set temperature
    temperatura = constrain(temp, 17, 30);
    encendido = powerOn;

    // Build and send command
    uint8_t data[3];
    buildCommand(data, powerOn);

    Serial.printf("📡 Enviando comando AC: power=%s, temp=%d°C, mode=%s, fan=%s\n",
                  powerOn ? "ON" : "OFF", temperatura, modeStr.c_str(), fanStr.c_str());
    Serial.printf("   Data: 0x%02X 0x%02X 0x%02X\n", data[0], data[1], data[2]);

    sendMideaCommand(data);
    ultimoCambio = millis();
    return true;
  }

  // Legacy methods for backward compatibility
  bool encender()
  {
    return enviarComando(true, temperatura, getModoStr(), getFanStr());
  }

  bool apagar()
  {
    return enviarComando(false, temperatura, getModoStr(), getFanStr());
  }

  bool estaEncendido() const { return encendido; }
  uint8_t getTemperatura() const { return temperatura; }
  AcMode getModo() const { return modo; }
  FanSpeed getFanSpeed() const { return fanSpeed; }

  String getModoStr() const
  {
    switch (modo)
    {
    case AcMode::COOL:
      return "cool";
    case AcMode::HEAT:
      return "heat";
    case AcMode::AUTO:
      return "auto";
    case AcMode::FAN:
      return "fan";
    case AcMode::DRY:
      return "dry";
    default:
      return "cool";
    }
  }

  String getFanStr() const
  {
    switch (fanSpeed)
    {
    case FanSpeed::AUTO:
      return "auto";
    case FanSpeed::F_LOW:
      return "low";
    case FanSpeed::MEDIUM:
      return "medium";
    case FanSpeed::F_HIGH:
      return "high";
    default:
      return "auto";
    }
  }

  void setEstado(bool estado) { encendido = estado; }
  void setTemperatura(uint8_t temp) { temperatura = constrain(temp, 17, 30); }

  void setModo(const String &modeStr)
  {
    if (modeStr == "cool")
      modo = AcMode::COOL;
    else if (modeStr == "heat")
      modo = AcMode::HEAT;
    else if (modeStr == "auto")
      modo = AcMode::AUTO;
    else if (modeStr == "fan")
      modo = AcMode::FAN;
    else if (modeStr == "dry")
      modo = AcMode::DRY;
  }

  void setFanSpeed(const String &fanStr)
  {
    if (fanStr == "auto")
      fanSpeed = FanSpeed::AUTO;
    else if (fanStr == "low")
      fanSpeed = FanSpeed::F_LOW;
    else if (fanStr == "medium")
      fanSpeed = FanSpeed::MEDIUM;
    else if (fanStr == "high")
      fanSpeed = FanSpeed::F_HIGH;
  }
};

#endif
