"""
Scheduler service para ejecutar programaciones automáticas
"""
import asyncio
import json
from datetime import datetime, time as dt_time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, Schedule, AcEvent, SleepTimer
from mqtt_client import get_mqtt_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerService:
    """Servicio que ejecuta schedules automáticamente"""

    def __init__(self):
        self.running = False
        self.task = None
        self._executed_today = set()  # Para evitar ejecutar el mismo schedule múltiples veces

    async def start(self):
        """Iniciar el scheduler"""
        if self.running:
            logger.warning("Scheduler ya está corriendo")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("✓ Scheduler iniciado")

    async def stop(self):
        """Detener el scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("✓ Scheduler detenido")

    async def _run_scheduler(self):
        """Loop principal del scheduler"""
        logger.info("🕐 Scheduler loop iniciado - revisando cada minuto")

        while self.running:
            try:
                await self._check_and_execute_schedules()
                await self._check_and_execute_sleep_timers()

                # Esperar hasta el próximo minuto
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error en scheduler loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(60)  # Continuar a pesar de errores

    async def _check_and_execute_schedules(self):
        """Revisar y ejecutar schedules que correspondan ahora"""
        # Usar datetime.now() para hora local del servidor
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_weekday = now.isoweekday()  # 1=Lunes, 7=Domingo
        current_date = now.date()

        # Limpiar el set de ejecutados si cambió el día
        if not hasattr(self, '_last_check_date') or self._last_check_date != current_date:
            self._executed_today = set()
            self._last_check_date = current_date
            logger.info(f"📅 Nueva fecha: {current_date} - limpiando schedules ejecutados")

        async with AsyncSessionLocal() as session:
            # Obtener todos los schedules activos
            result = await session.execute(
                select(Schedule).where(Schedule.is_active == True)
            )
            schedules = result.scalars().all()

            if not schedules:
                return

            logger.debug(f"🔍 Revisando {len(schedules)} schedules activos a las {current_time}")

            for schedule in schedules:
                try:
                    # Crear un ID único para este schedule en este día
                    schedule_today_id = f"{schedule.id}_{current_date}"

                    # Si ya fue ejecutado hoy, saltar
                    if schedule_today_id in self._executed_today:
                        continue

                    # Verificar si la hora coincide
                    if schedule.time != current_time:
                        continue

                    # Verificar si el día de la semana coincide
                    days_of_week = json.loads(schedule.days_of_week) if schedule.days_of_week else []
                    if days_of_week and current_weekday not in days_of_week:
                        logger.debug(f"Schedule '{schedule.name}' no aplica para hoy ({current_weekday})")
                        continue

                    # Ejecutar el schedule
                    logger.info(f"⚡ Ejecutando schedule: '{schedule.name}' - {schedule.action} - Device: {schedule.device_id}")
                    await self._execute_schedule(session, schedule)

                    # Marcar como ejecutado hoy
                    self._executed_today.add(schedule_today_id)

                except Exception as e:
                    logger.error(f"Error ejecutando schedule {schedule.id}: {e}")
                    import traceback
                    traceback.print_exc()

    async def _execute_schedule(self, session: AsyncSession, schedule: Schedule):
        """Ejecutar un schedule específico"""
        mqtt = get_mqtt_client()

        if not mqtt:
            logger.error("MQTT client no disponible")
            return

        # Enviar comando MQTT
        success = mqtt.send_ac_command(schedule.device_id, schedule.action)

        if not success:
            logger.error(f"Fallo al enviar comando MQTT para schedule {schedule.id}")
            return

        # Guardar evento en la base de datos
        ac_event = AcEvent(
            device_id=schedule.device_id,
            action=schedule.action,
            triggered_by=f'schedule:{schedule.id}',
            timestamp=datetime.utcnow()
        )
        session.add(ac_event)
        await session.commit()

        logger.info(f"✓ Schedule ejecutado exitosamente: {schedule.name} ({schedule.action})")

    async def _check_and_execute_sleep_timers(self):
        """Revisar y ejecutar sleep timers que ya deben ejecutarse"""
        now = datetime.utcnow()

        async with AsyncSessionLocal() as session:
            # Obtener todos los sleep timers pendientes que ya deberían ejecutarse
            result = await session.execute(
                select(SleepTimer)
                .where(SleepTimer.is_executed == False)
                .where(SleepTimer.execute_at <= now)
            )
            timers = result.scalars().all()

            if not timers:
                return

            logger.info(f"⏰ Encontrados {len(timers)} sleep timers para ejecutar")

            for timer in timers:
                try:
                    logger.info(f"⚡ Ejecutando sleep timer: Device {timer.device_id} - {timer.action}")
                    await self._execute_sleep_timer(session, timer)

                    # Marcar como ejecutado y eliminar
                    await session.delete(timer)
                    await session.commit()

                except Exception as e:
                    logger.error(f"Error ejecutando sleep timer {timer.id}: {e}")
                    import traceback
                    traceback.print_exc()

    async def _execute_sleep_timer(self, session: AsyncSession, timer: SleepTimer):
        """Ejecutar un sleep timer específico"""
        mqtt = get_mqtt_client()

        if not mqtt:
            logger.error("MQTT client no disponible")
            return

        # Enviar comando MQTT
        success = mqtt.send_ac_command(timer.device_id, timer.action)

        if not success:
            logger.error(f"Fallo al enviar comando MQTT para sleep timer {timer.id}")
            return

        # Guardar evento en la base de datos
        ac_event = AcEvent(
            device_id=timer.device_id,
            action=timer.action,
            triggered_by=f'sleep_timer:{timer.id}',
            timestamp=datetime.utcnow()
        )
        session.add(ac_event)
        await session.commit()

        logger.info(f"✓ Sleep timer ejecutado exitosamente: {timer.action} for device {timer.device_id}")


# Instancia global del scheduler
_scheduler_instance = None


def get_scheduler() -> SchedulerService:
    """Obtener instancia del scheduler"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService()
    return _scheduler_instance
