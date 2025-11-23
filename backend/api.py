from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database import (
    get_session, Device, Measurement, MeasurementAverage,
    AcEvent, AcState, Schedule, LedConfig, SleepTimer
)
from mqtt_client import get_mqtt_client
from scheduler import get_scheduler
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from utils import (
    now_argentina, parse_iso_date, check_mqtt_success,
    validate_action, validate_rgb_color, validate_delay_minutes,
    serialize_device, serialize_measurement, serialize_measurement_average,
    serialize_ac_event
)
from scheduler import save_ac_event

app = FastAPI(title="Sistema de Clima Inteligente API", version="1.0.0")

# ============================================
# STARTUP Y SHUTDOWN
# ============================================

@app.on_event("startup")
async def startup_event():
    """Iniciar servicios al arrancar la aplicación"""
    scheduler = get_scheduler()
    await scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Detener servicios al cerrar la aplicación"""
    scheduler = get_scheduler()
    await scheduler.stop()

# Configurar path al frontend
# Dentro del contenedor Docker, el frontend está en /app/frontend
frontend_path = Path(__file__).parent / "frontend"
print(f"Frontend path: {frontend_path}")
print(f"Frontend exists: {frontend_path.exists()}")
# CORS para permitir requests desde frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos del frontend
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# ============================================
# MODELOS PYDANTIC
# ============================================

class AcCommandRequest(BaseModel):
    action: str  # 'on' or 'off'
    temperature: Optional[int] = 24  # 17-30°C
    mode: Optional[str] = 'cool'  # cool/heat/auto/fan/dry
    fan_speed: Optional[str] = 'auto'  # auto/low/medium/high

class LedCommandRequest(BaseModel):
    r: int
    g: int
    b: int
    enabled: bool

class ConfigUpdateRequest(BaseModel):
    sample_interval: int  # en segundos
    avg_samples: int

class ScheduleCreate(BaseModel):
    name: str
    action: str  # 'on' or 'off'
    days_of_week: List[int]  # [1,2,3,4,5] = lun-vie
    time: str  # "08:00"

class SleepTimerCreate(BaseModel):
    action: str  # 'on' or 'off'
    delay_minutes: int  # cuántos minutos hasta ejecutar

# ============================================
# ENDPOINTS: DISPOSITIVOS
# ============================================

@app.get("/devices")
async def get_devices(session: AsyncSession = Depends(get_session)):
    """Obtener todos los dispositivos"""
    result = await session.execute(select(Device))
    devices = result.scalars().all()
    return {
        "devices": [serialize_device(d) for d in devices]
    }

@app.get("/devices/{device_id}")
async def get_device(device_id: str, session: AsyncSession = Depends(get_session)):
    """Obtener info de un dispositivo específico"""
    result = await session.execute(
        select(Device).where(Device.device_id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return serialize_device(device)

# ============================================
# ENDPOINTS: MEDICIONES
# ============================================

@app.get("/devices/{device_id}/measurements")
async def get_measurements(
    device_id: str,
    limit: int = Query(100, ge=1, le=1000),
    from_date: Optional[str] = Query(None, description="ISO format datetime (e.g., 2024-01-01T00:00:00)"),
    to_date: Optional[str] = Query(None, description="ISO format datetime (e.g., 2024-01-02T00:00:00)"),
    session: AsyncSession = Depends(get_session)
):
    """Obtener mediciones de un dispositivo, filtradas por fecha o límite"""
    query = select(Measurement).where(Measurement.device_id == device_id)

    # Filtrar por fechas si se proporcionan
    if from_date:
        try:
            from_dt = parse_iso_date(from_date)
            query = query.where(Measurement.timestamp >= from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format")

    if to_date:
        try:
            to_dt = parse_iso_date(to_date)
            query = query.where(Measurement.timestamp <= to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format")

    query = query.order_by(desc(Measurement.timestamp))

    # Solo aplicar limit si no hay filtro de fechas
    if not from_date and not to_date:
        query = query.limit(limit)

    result = await session.execute(query)
    measurements = result.scalars().all()

    return {
        "device_id": device_id,
        "count": len(measurements),
        "measurements": [serialize_measurement(m) for m in reversed(measurements)]
    }

@app.get("/devices/{device_id}/measurements/latest")
async def get_latest_measurement(
    device_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Obtener última medición de un dispositivo"""
    result = await session.execute(
        select(Measurement)
        .where(Measurement.device_id == device_id)
        .order_by(desc(Measurement.timestamp))
        .limit(1)
    )
    measurement = result.scalar_one_or_none()
    
    if not measurement:
        raise HTTPException(status_code=404, detail="No measurements found")
    
    result = serialize_measurement(measurement)
    result["device_id"] = device_id
    return result

@app.get("/devices/{device_id}/averages")
async def get_averages(
    device_id: str,
    hours: int = Query(24, ge=1, le=168),  # Máximo 1 semana
    session: AsyncSession = Depends(get_session)
):
    """Obtener promedios de las últimas N horas"""
    since = now_argentina() - timedelta(hours=hours)
    
    result = await session.execute(
        select(MeasurementAverage)
        .where(MeasurementAverage.device_id == device_id)
        .where(MeasurementAverage.period_end >= since)
        .order_by(MeasurementAverage.period_end)
    )
    averages = result.scalars().all()
    
    return {
        "device_id": device_id,
        "period_hours": hours,
        "count": len(averages),
        "averages": [serialize_measurement_average(a) for a in averages]
    }

@app.get("/devices/{device_id}/stats")
async def get_device_stats(
    device_id: str,
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_session)
):
    """Obtener estadísticas del dispositivo"""
    since = now_argentina() - timedelta(hours=hours)
    
    # Estadísticas de temperatura
    temp_stats = await session.execute(
        select(
            func.avg(Measurement.temperature).label('avg_temp'),
            func.min(Measurement.temperature).label('min_temp'),
            func.max(Measurement.temperature).label('max_temp'),
            func.avg(Measurement.humidity).label('avg_hum')
        )
        .where(Measurement.device_id == device_id)
        .where(Measurement.timestamp >= since)
    )
    stats = temp_stats.first()
    
    # Tiempo AC encendido
    ac_on_time = await session.execute(
        select(func.count(AcEvent.id))
        .where(AcEvent.device_id == device_id)
        .where(AcEvent.action == 'on')
        .where(AcEvent.timestamp >= since)
    )
    ac_on_count = ac_on_time.scalar()
    
    return {
        "device_id": device_id,
        "period_hours": hours,
        "temperature": {
            "average": round(stats.avg_temp, 1) if stats.avg_temp else None,
            "min": round(stats.min_temp, 1) if stats.min_temp else None,
            "max": round(stats.max_temp, 1) if stats.max_temp else None
        },
        "humidity": {
            "average": round(stats.avg_hum, 1) if stats.avg_hum else None
        },
        "ac_activations": ac_on_count
    }

# ============================================
# ENDPOINTS: CONTROL AC
# ============================================

@app.post("/devices/{device_id}/ac/command")
async def send_ac_command(
    device_id: str,
    command: AcCommandRequest,
    session: AsyncSession = Depends(get_session)
):
    """Enviar comando al aire acondicionado"""
    mqtt = get_mqtt_client()

    validate_action(command.action)

    # Validar temperatura
    if command.temperature < 17 or command.temperature > 30:
        raise HTTPException(status_code=400, detail="Temperature must be between 17 and 30°C")

    # Validar modo
    valid_modes = ['cool', 'heat', 'auto', 'fan', 'dry']
    if command.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Mode must be one of: {valid_modes}")

    # Validar fan speed
    valid_fan_speeds = ['auto', 'low', 'medium', 'high']
    if command.fan_speed not in valid_fan_speeds:
        raise HTTPException(status_code=400, detail=f"Fan speed must be one of: {valid_fan_speeds}")

    # Enviar comando MQTT con parámetros extendidos
    success = mqtt.send_ac_command(
        device_id, command.action, command.temperature, command.mode, command.fan_speed
    )
    check_mqtt_success(success, "AC command")

    # Actualizar estado en BD
    result = await session.execute(
        select(AcState).where(AcState.device_id == device_id)
    )
    ac_state = result.scalar_one_or_none()

    if not ac_state:
        ac_state = AcState(device_id=device_id)
        session.add(ac_state)

    ac_state.is_on = command.action == 'on'
    ac_state.temperature = command.temperature
    ac_state.mode = command.mode
    ac_state.fan_speed = command.fan_speed
    ac_state.last_updated = now_argentina()

    # Guardar evento con parámetros
    event = AcEvent(
        device_id=device_id,
        action=command.action,
        temperature=command.temperature,
        mode=command.mode,
        fan_speed=command.fan_speed,
        triggered_by='manual'
    )
    session.add(event)
    await session.commit()

    return {
        "device_id": device_id,
        "action": command.action,
        "temperature": command.temperature,
        "mode": command.mode,
        "fan_speed": command.fan_speed,
        "status": "command_sent"
    }

@app.get("/devices/{device_id}/ac/status")
async def get_ac_status(
    device_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Obtener estado actual del AC"""
    result = await session.execute(
        select(AcState).where(AcState.device_id == device_id)
    )
    ac_state = result.scalar_one_or_none()

    if not ac_state:
        return {
            "device_id": device_id,
            "state": "unknown",
            "is_on": False,
            "temperature": 24,
            "mode": "cool",
            "fan_speed": "auto",
            "last_update": None
        }

    return {
        "device_id": device_id,
        "state": "on" if ac_state.is_on else "off",
        "is_on": ac_state.is_on,
        "temperature": ac_state.temperature,
        "mode": ac_state.mode,
        "fan_speed": ac_state.fan_speed,
        "last_update": ac_state.last_updated.isoformat() if ac_state.last_updated else None
    }

@app.get("/devices/{device_id}/ac/history")
async def get_ac_history(
    device_id: str,
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session)
):
    """Obtener historial de eventos del AC"""
    result = await session.execute(
        select(AcEvent)
        .where(AcEvent.device_id == device_id)
        .order_by(desc(AcEvent.timestamp))
        .limit(limit)
    )
    events = result.scalars().all()
    
    return {
        "device_id": device_id,
        "count": len(events),
        "events": [serialize_ac_event(e) for e in events]
    }

# ============================================
# ENDPOINTS: CONTROL LED
# ============================================

@app.post("/devices/{device_id}/led/command")
async def send_led_command(device_id: str, command: LedCommandRequest):
    """Enviar comando al LED"""
    mqtt = get_mqtt_client()

    validate_rgb_color(command.r, command.g, command.b)

    success = mqtt.send_led_command(device_id, command.r, command.g, command.b, command.enabled)
    check_mqtt_success(success, "LED command")
    
    return {
        "device_id": device_id,
        "color": {"r": command.r, "g": command.g, "b": command.b},
        "status": "command_sent"
    }

# ============================================
# ENDPOINTS: CONFIGURACIÓN
# ============================================

@app.post("/devices/{device_id}/config")
async def update_device_config(device_id: str, config: ConfigUpdateRequest):
    """Actualizar configuración del dispositivo"""
    mqtt = get_mqtt_client()
    
    success = mqtt.send_config_update(
        device_id,
        config.sample_interval,
        config.avg_samples
    )
    check_mqtt_success(success, "config update")
    
    return {
        "device_id": device_id,
        "config": {
            "sample_interval": config.sample_interval,
            "avg_samples": config.avg_samples
        },
        "status": "command_sent"
    }

@app.post("/devices/{device_id}/reboot")
async def reboot_device(device_id: str):
    """Reiniciar dispositivo"""
    mqtt = get_mqtt_client()

    success = mqtt.send_reboot_command(device_id)
    check_mqtt_success(success, "reboot command")
    
    return {
        "device_id": device_id,
        "status": "reboot_command_sent"
    }

# ============================================
# ENDPOINTS: PROGRAMACIÓN
# ============================================

@app.get("/devices/{device_id}/schedules")
async def get_schedules(
    device_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Obtener programaciones de un dispositivo"""
    result = await session.execute(
        select(Schedule).where(Schedule.device_id == device_id)
    )
    schedules = result.scalars().all()
    
    return {
        "device_id": device_id,
        "schedules": [
            {
                "id": s.id,
                "name": s.name,
                "action": s.action,
                "days_of_week": s.days_of_week,
                "time": s.time,
                "is_active": s.is_active
            }
            for s in schedules
        ]
    }

@app.post("/devices/{device_id}/schedules")
async def create_schedule(
    device_id: str,
    schedule: ScheduleCreate,
    session: AsyncSession = Depends(get_session)
):
    """Crear nueva programación"""
    import json
    
    new_schedule = Schedule(
        device_id=device_id,
        name=schedule.name,
        action=schedule.action,
        days_of_week=json.dumps(schedule.days_of_week),
        time=schedule.time,
        is_active=True
    )
    session.add(new_schedule)
    await session.commit()
    await session.refresh(new_schedule)
    
    return {
        "id": new_schedule.id,
        "device_id": device_id,
        "message": "Schedule created successfully"
    }

@app.delete("/devices/{device_id}/schedules/{schedule_id}")
async def delete_schedule(
    device_id: str,
    schedule_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Eliminar programación"""
    result = await session.execute(
        select(Schedule)
        .where(Schedule.id == schedule_id)
        .where(Schedule.device_id == device_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await session.delete(schedule)
    await session.commit()

    return {"message": "Schedule deleted successfully"}

# ============================================
# ENDPOINTS: SLEEP TIMER
# ============================================

@app.get("/devices/{device_id}/sleep-timers")
async def get_sleep_timers(
    device_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Obtener sleep timers activos de un dispositivo"""
    result = await session.execute(
        select(SleepTimer)
        .where(SleepTimer.device_id == device_id)
        .where(SleepTimer.is_executed == False)
        .order_by(SleepTimer.execute_at)
    )
    timers = result.scalars().all()

    now = now_argentina()

    return {
        "device_id": device_id,
        "timers": [
            {
                "id": t.id,
                "action": t.action,
                "execute_at": t.execute_at.isoformat(),
                "created_at": t.created_at.isoformat(),
                "remaining_seconds": max(0, int((t.execute_at - now).total_seconds()))
            }
            for t in timers
        ]
    }

@app.post("/devices/{device_id}/sleep-timers")
async def create_sleep_timer(
    device_id: str,
    timer: SleepTimerCreate,
    session: AsyncSession = Depends(get_session)
):
    """Crear un sleep timer (temporizador de una sola ejecución)"""
    validate_action(timer.action)
    validate_delay_minutes(timer.delay_minutes)

    execute_at = now_argentina() + timedelta(minutes=timer.delay_minutes)

    new_timer = SleepTimer(
        device_id=device_id,
        action=timer.action,
        execute_at=execute_at
    )
    session.add(new_timer)
    await session.commit()
    await session.refresh(new_timer)

    return {
        "id": new_timer.id,
        "device_id": device_id,
        "action": timer.action,
        "execute_at": execute_at.isoformat(),
        "delay_minutes": timer.delay_minutes,
        "message": f"Sleep timer created: {timer.action} in {timer.delay_minutes} minutes"
    }

@app.delete("/devices/{device_id}/sleep-timers/{timer_id}")
async def cancel_sleep_timer(
    device_id: str,
    timer_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Cancelar un sleep timer"""
    result = await session.execute(
        select(SleepTimer)
        .where(SleepTimer.id == timer_id)
        .where(SleepTimer.device_id == device_id)
        .where(SleepTimer.is_executed == False)
    )
    timer = result.scalar_one_or_none()

    if not timer:
        raise HTTPException(status_code=404, detail="Sleep timer not found or already executed")

    await session.delete(timer)
    await session.commit()

    return {"message": "Sleep timer cancelled successfully"}

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    mqtt = get_mqtt_client()
    scheduler = get_scheduler()
    return {
        "status": "healthy",
        "mqtt_connected": mqtt.connected if mqtt else False,
        "scheduler_running": scheduler.running if scheduler else False,
        "timestamp": now_argentina().isoformat()
    }

@app.get("/")
async def root():
    """Servir el frontend"""
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "Sistema de Clima Inteligente API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/api")
async def api_info():
    """Información de la API"""
    return {
        "message": "Sistema de Clima Inteligente API",
        "version": "1.0.0",
        "docs": "/docs"
    }