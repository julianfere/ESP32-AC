"""
Utilidades para manejo de fechas, timezone de Argentina y helpers comunes
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict
from fastapi import HTTPException

# Timezone de Argentina
ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def now_argentina():
    """
    Obtener el datetime actual en timezone de Argentina

    Returns:
        datetime: Datetime actual con timezone de Argentina
    """
    return datetime.now(ARGENTINA_TZ)


def to_argentina_tz(dt: datetime) -> datetime:
    """
    Convertir un datetime a timezone de Argentina

    Args:
        dt: Datetime a convertir (puede ser naive o aware)

    Returns:
        datetime: Datetime convertido a timezone de Argentina
    """
    if dt.tzinfo is None:
        # Si es naive, asumir que ya está en Argentina y agregar timezone
        return dt.replace(tzinfo=ARGENTINA_TZ)
    else:
        # Si ya tiene timezone, convertir a Argentina
        return dt.astimezone(ARGENTINA_TZ)


def from_timestamp_argentina(timestamp: int) -> datetime:
    """
    Convertir un timestamp Unix a datetime en timezone de Argentina

    Args:
        timestamp: Timestamp Unix en segundos

    Returns:
        datetime: Datetime en timezone de Argentina
    """
    return datetime.fromtimestamp(timestamp, tz=ARGENTINA_TZ)


def parse_iso_date(date_str: str) -> datetime:
    """
    Parsear string de fecha ISO, removiendo info de timezone

    Args:
        date_str: String de fecha en formato ISO (ej: "2024-01-01T00:00:00Z")

    Returns:
        datetime: Datetime parseado
    """
    clean_date = date_str.replace('Z', '').split('+')[0]
    return datetime.fromisoformat(clean_date)


def parse_message_timestamp(payload: Dict[str, Any]) -> datetime:
    """
    Extraer y parsear timestamp de un payload MQTT

    Args:
        payload: Diccionario con datos del mensaje MQTT

    Returns:
        datetime: Timestamp parseado en timezone de Argentina
    """
    timestamp_raw = payload.get('timestamp', int(now_argentina().timestamp()))
    if isinstance(timestamp_raw, int):
        return from_timestamp_argentina(timestamp_raw)
    else:
        return now_argentina()


def check_mqtt_success(success: bool, operation: str = "MQTT command"):
    """
    Verificar éxito de operación MQTT, lanzar HTTPException si falla

    Args:
        success: Resultado de la operación MQTT
        operation: Descripción de la operación para el mensaje de error

    Raises:
        HTTPException: Si la operación falló (status 503)
    """
    if not success:
        raise HTTPException(status_code=503, detail=f"Failed to send {operation}")


def validate_action(action: str, valid_actions: list = None):
    """
    Validar parámetro de acción

    Args:
        action: Acción a validar
        valid_actions: Lista de acciones válidas (default: ['on', 'off'])

    Raises:
        HTTPException: Si la acción no es válida (status 400)
    """
    if valid_actions is None:
        valid_actions = ['on', 'off']
    if action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Action must be one of: {', '.join(valid_actions)}"
        )


def validate_rgb_color(r: int, g: int, b: int):
    """
    Validar valores de color RGB

    Args:
        r, g, b: Valores de color (0-255)

    Raises:
        HTTPException: Si algún valor está fuera de rango (status 400)
    """
    if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
        raise HTTPException(status_code=400, detail="RGB values must be 0-255")


def validate_delay_minutes(delay: int, min_val: int = 1, max_val: int = 1440):
    """
    Validar delay en minutos

    Args:
        delay: Valor de delay a validar
        min_val: Valor mínimo permitido
        max_val: Valor máximo permitido

    Raises:
        HTTPException: Si el delay está fuera de rango (status 400)
    """
    if delay < min_val or delay > max_val:
        raise HTTPException(
            status_code=400,
            detail=f"Delay must be between {min_val} and {max_val} minutes"
        )


def serialize_device(device) -> dict:
    """
    Convertir modelo Device a diccionario para respuesta API

    Args:
        device: Instancia de Device

    Returns:
        dict: Diccionario con datos del dispositivo
    """
    return {
        "device_id": device.device_id,
        "name": device.name,
        "location": device.location,
        "is_online": device.is_online,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None
    }


def serialize_measurement(measurement) -> dict:
    """
    Convertir modelo Measurement a diccionario para respuesta API

    Args:
        measurement: Instancia de Measurement

    Returns:
        dict: Diccionario con datos de la medición
    """
    return {
        "temperature": measurement.temperature,
        "humidity": measurement.humidity,
        "timestamp": measurement.timestamp.isoformat()
    }


def serialize_measurement_average(average) -> dict:
    """
    Convertir modelo MeasurementAverage a diccionario para respuesta API

    Args:
        average: Instancia de MeasurementAverage

    Returns:
        dict: Diccionario con datos del promedio
    """
    return {
        "avg_temperature": average.avg_temperature,
        "avg_humidity": average.avg_humidity,
        "sample_count": average.sample_count,
        "period_start": average.period_start.isoformat(),
        "period_end": average.period_end.isoformat()
    }


def serialize_ac_event(event) -> dict:
    """
    Convertir modelo AcEvent a diccionario para respuesta API

    Args:
        event: Instancia de AcEvent

    Returns:
        dict: Diccionario con datos del evento
    """
    return {
        "action": event.action,
        "triggered_by": event.triggered_by,
        "timestamp": event.timestamp.isoformat()
    }
