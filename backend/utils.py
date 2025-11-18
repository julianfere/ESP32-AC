"""
Utilidades para manejo de fechas y timezone de Argentina
"""
from datetime import datetime
from zoneinfo import ZoneInfo

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
