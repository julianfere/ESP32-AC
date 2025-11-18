from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database import (
    get_session, Device, Measurement, MeasurementAverage,
    AcEvent, Schedule, LedConfig, SleepTimer
)
from mqtt_client import get_mqtt_client
from scheduler import get_scheduler
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from utils import now_argentina

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

class LedCommandRequest(BaseModel):
    r: int
    g: int
    b: int

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
        "devices": [
            {
                "device_id": d.device_id,
                "name": d.name,
                "location": d.location,
                "is_online": d.is_online,
                "last_seen": d.last_seen.isoformat() if d.last_seen else None
            }
            for d in devices
        ]
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
    
    return {
        "device_id": device.device_id,
        "name": device.name,
        "location": device.location,
        "is_online": device.is_online,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None
    }

# ============================================
# ENDPOINTS: MEDICIONES
# ============================================

@app.get("/devices/{device_id}/measurements")
async def get_measurements(
    device_id: str,
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session)
):
    """Obtener últimas mediciones de un dispositivo"""
    result = await session.execute(
        select(Measurement)
        .where(Measurement.device_id == device_id)
        .order_by(desc(Measurement.timestamp))
        .limit(limit)
    )
    measurements = result.scalars().all()
    
    return {
        "device_id": device_id,
        "count": len(measurements),
        "measurements": [
            {
                "temperature": m.temperature,
                "humidity": m.humidity,
                "timestamp": m.timestamp.isoformat()
            }
            for m in reversed(measurements)  # Orden cronológico
        ]
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
    
    return {
        "device_id": device_id,
        "temperature": measurement.temperature,
        "humidity": measurement.humidity,
        "timestamp": measurement.timestamp.isoformat()
    }

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
        "averages": [
            {
                "avg_temperature": a.avg_temperature,
                "avg_humidity": a.avg_humidity,
                "sample_count": a.sample_count,
                "period_start": a.period_start.isoformat(),
                "period_end": a.period_end.isoformat()
            }
            for a in averages
        ]
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
    
    if command.action not in ['on', 'off']:
        raise HTTPException(status_code=400, detail="Action must be 'on' or 'off'")
    
    # Enviar comando MQTT
    success = mqtt.send_ac_command(device_id, command.action)
    
    if not success:
        raise HTTPException(status_code=503, detail="Failed to send MQTT command")
    
    # Guardar evento (será actualizado cuando llegue confirmación)
    ac_event = AcEvent(
        device_id=device_id,
        action=command.action,
        triggered_by='manual',
        timestamp=now_argentina()
    )
    session.add(ac_event)
    await session.commit()
    
    return {
        "device_id": device_id,
        "action": command.action,
        "status": "command_sent"
    }

@app.get("/devices/{device_id}/ac/status")
async def get_ac_status(
    device_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Obtener último estado conocido del AC"""
    result = await session.execute(
        select(AcEvent)
        .where(AcEvent.device_id == device_id)
        .order_by(desc(AcEvent.timestamp))
        .limit(1)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        return {"device_id": device_id, "state": "unknown", "last_update": None}
    
    return {
        "device_id": device_id,
        "state": event.action,
        "last_update": event.timestamp.isoformat(),
        "triggered_by": event.triggered_by
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
        "events": [
            {
                "action": e.action,
                "triggered_by": e.triggered_by,
                "timestamp": e.timestamp.isoformat()
            }
            for e in events
        ]
    }

# ============================================
# ENDPOINTS: CONTROL LED
# ============================================

@app.post("/devices/{device_id}/led/command")
async def send_led_command(device_id: str, command: LedCommandRequest):
    """Enviar comando al LED"""
    mqtt = get_mqtt_client()
    
    # Validar rangos
    if not (0 <= command.r <= 255 and 0 <= command.g <= 255 and 0 <= command.b <= 255):
        raise HTTPException(status_code=400, detail="RGB values must be 0-255")
    
    success = mqtt.send_led_command(device_id, command.r, command.g, command.b)
    
    if not success:
        raise HTTPException(status_code=503, detail="Failed to send MQTT command")
    
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
    
    if not success:
        raise HTTPException(status_code=503, detail="Failed to send MQTT command")
    
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
    
    if not success:
        raise HTTPException(status_code=503, detail="Failed to send MQTT command")
    
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
    if timer.action not in ['on', 'off']:
        raise HTTPException(status_code=400, detail="Action must be 'on' or 'off'")

    if timer.delay_minutes < 1 or timer.delay_minutes > 1440:  # Máximo 24 horas
        raise HTTPException(status_code=400, detail="Delay must be between 1 and 1440 minutes")

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