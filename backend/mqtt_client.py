from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database import Device, Measurement, MeasurementAverage, AcEvent, AsyncSessionLocal
from datetime import datetime
from typing import Dict, Any
import json

class MessageHandler:
    """Manejador de mensajes MQTT"""
    
    @staticmethod
    async def handle_sensor_raw(message: Dict[str, Any]):
        """Manejar mediciones individuales del sensor"""
        device_id = message['device_id']
        payload = message['payload']
        
        try:
            temp = payload.get('temperature')
            hum = payload.get('humidity')
            timestamp_raw = payload.get('timestamp', int(datetime.utcnow().timestamp()))
            
            # Convertir timestamp a datetime
            if isinstance(timestamp_raw, int):
                timestamp = datetime.fromtimestamp(timestamp_raw)
            else:
                timestamp = datetime.utcnow()
            
            async with AsyncSessionLocal() as session:
                # Actualizar dispositivo
                await MessageHandler._update_device_status(session, device_id, True)
                
                # Guardar medición
                measurement = Measurement(
                    device_id=device_id,
                    temperature=temp,
                    humidity=hum,
                    timestamp=timestamp
                )
                session.add(measurement)
                await session.commit()
                
                print(f"📊 [{device_id}] Raw: {temp}°C, {hum}%")
        
        except Exception as e:
            print(f"✗ Error guardando medición raw: {e}")
    
    @staticmethod
    async def handle_sensor_avg(message: Dict[str, Any]):
        """Manejar promedios de mediciones"""
        device_id = message['device_id']
        payload = message['payload']
        
        try:
            avg_temp = payload.get('temp')
            avg_hum = payload.get('hum')
            samples = payload.get('samples', 0)
            timestamp_raw = payload.get('timestamp', int(datetime.utcnow().timestamp()))
            
            if isinstance(timestamp_raw, int):
                timestamp = datetime.fromtimestamp(timestamp_raw)
            else:
                timestamp = datetime.utcnow()
            
            async with AsyncSessionLocal() as session:
                # Calcular período (asumir 5 minutos atrás)
                from datetime import timedelta
                period_start = timestamp - timedelta(minutes=5)
                
                avg_measurement = MeasurementAverage(
                    device_id=device_id,
                    avg_temperature=avg_temp,
                    avg_humidity=avg_hum,
                    sample_count=samples,
                    period_start=period_start,
                    period_end=timestamp
                )
                session.add(avg_measurement)
                await session.commit()
                
                print(f"📈 [{device_id}] Promedio: {avg_temp}°C, {avg_hum}% ({samples} muestras)")
        
        except Exception as e:
            print(f"✗ Error guardando promedio: {e}")
    
    @staticmethod
    async def handle_ac_status(message: Dict[str, Any]):
        """Manejar estado del aire acondicionado"""
        device_id = message['device_id']
        payload = message['payload']
        
        try:
            state = payload.get('state')  # 'on' or 'off'
            confirmed = payload.get('confirmed', False)
            timestamp_raw = payload.get('timestamp', int(datetime.utcnow().timestamp()))
            
            if isinstance(timestamp_raw, int):
                timestamp = datetime.fromtimestamp(timestamp_raw)
            else:
                timestamp = datetime.utcnow()
            
            async with AsyncSessionLocal() as session:
                # Guardar evento
                ac_event = AcEvent(
                    device_id=device_id,
                    action=state,
                    triggered_by='confirmed' if confirmed else 'unknown',
                    timestamp=timestamp
                )
                session.add(ac_event)
                await session.commit()
                
                print(f"❄️  [{device_id}] AC: {state.upper()} {'✓ confirmado' if confirmed else ''}")
        
        except Exception as e:
            print(f"✗ Error guardando estado AC: {e}")
    
    @staticmethod
    async def handle_led_status(message: Dict[str, Any]):
        """Manejar estado del LED"""
        device_id = message['device_id']
        payload = message['payload']
        
        try:
            r = payload.get('r', 0)
            g = payload.get('g', 0)
            b = payload.get('b', 0)
            
            print(f"💡 [{device_id}] LED: RGB({r}, {g}, {b})")
            # Aquí podrías guardar en DB si quieres histórico de colores
        
        except Exception as e:
            print(f"✗ Error procesando estado LED: {e}")
    
    @staticmethod
    async def handle_system_status(message: Dict[str, Any]):
        """Manejar estado del sistema (online/offline)"""
        device_id = message['device_id']
        payload = message['payload']
        
        try:
            status = payload if isinstance(payload, str) else payload.get('status', 'unknown')
            is_online = (status == 'online')
            
            async with AsyncSessionLocal() as session:
                await MessageHandler._update_device_status(session, device_id, is_online)
                
                print(f"{'🟢' if is_online else '🔴'} [{device_id}] Sistema: {status}")
        
        except Exception as e:
            print(f"✗ Error actualizando estado del sistema: {e}")
    
    @staticmethod
    async def handle_heartbeat(message: Dict[str, Any]):
        """Manejar heartbeat del dispositivo"""
        device_id = message['device_id']
        payload = message['payload']
        
        try:
            uptime = payload.get('uptime', 0)
            rssi = payload.get('wifi_rssi', 0)
            free_heap = payload.get('free_heap', 0)
            
            async with AsyncSessionLocal() as session:
                # Actualizar last_seen
                await MessageHandler._update_device_status(session, device_id, True)
            
            # Log simplificado cada minuto
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            print(f"💓 [{device_id}] Uptime: {hours}h{minutes}m | RSSI: {rssi}dBm | Heap: {free_heap}")
        
        except Exception as e:
            print(f"✗ Error procesando heartbeat: {e}")
    
    @staticmethod
    async def _update_device_status(session: AsyncSession, device_id: str, is_online: bool):
        """Actualizar estado del dispositivo"""
        # Buscar dispositivo
        result = await session.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if device:
            # Actualizar existente
            device.last_seen = datetime.utcnow()
            device.is_online = is_online
        else:
            # Crear nuevo
            device = Device(
                device_id=device_id,
                name=device_id,
                last_seen=datetime.utcnow(),
                is_online=is_online
            )
            session.add(device)
        
        await session.commit()


# Registrar todos los handlers
def register_handlers(mqtt_client):
    """Registrar todos los manejadores de mensajes"""
    handler = MessageHandler()
    
    mqtt_client.register_callback("+/sensor/raw", handler.handle_sensor_raw)
    mqtt_client.register_callback("+/sensor/avg", handler.handle_sensor_avg)
    mqtt_client.register_callback("+/ac/status", handler.handle_ac_status)
    mqtt_client.register_callback("+/led/status", handler.handle_led_status)
    mqtt_client.register_callback("+/system/status", handler.handle_system_status)
    mqtt_client.register_callback("+/system/heartbeat", handler.handle_heartbeat)
    
    print("✓ Todos los handlers MQTT registrados")