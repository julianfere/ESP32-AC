"""
ESP-AC Telegram Bot
Provides remote access to ESP-AC backend via Telegram Mini App
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

import aiohttp
from aiohttp import web
from aiohttp_cors import setup as cors_setup, ResourceOptions
from telegram import Update, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
DEFAULT_DEVICE_ID = os.getenv("DEFAULT_DEVICE_ID", "ESP32-001")
ALERT_CHECK_INTERVAL = int(os.getenv("ALERT_CHECK_INTERVAL", "300"))  # seconds
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com/webapp")  # Update in production
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8443"))
WEBAPP_DIR = Path(__file__).parent / "bot" / "webapp"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global state for alerts
alert_settings: Dict[str, Any] = {
    "enabled": False,
    "threshold_high": 30.0,
    "threshold_low": 18.0,
    "last_alert_sent": None,
    "cooldown_minutes": 30,
}


class BackendAPIClient:
    """Client to communicate with ESP-AC backend API"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to backend"""
        session = await self.get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            raise

    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device current status"""
        latest = await self._request("GET", f"/devices/{device_id}/measurements/latest")
        ac_status = await self._request("GET", f"/devices/{device_id}/ac/status")

        return {
            "temperature": latest.get("temperature"),
            "humidity": latest.get("humidity"),
            "timestamp": latest.get("timestamp"),
            "ac_status": ac_status.get("current_status"),
        }

    async def send_ac_command(self, device_id: str, action: str,
                              temperature: int = 24, mode: str = 'cool',
                              fan_speed: str = 'auto') -> Dict[str, Any]:
        """Send AC command with extended parameters"""
        return await self._request(
            "POST",
            f"/devices/{device_id}/ac/command",
            json={
                "action": action,
                "temperature": temperature,
                "mode": mode,
                "fan_speed": fan_speed
            }
        )

    async def get_ac_state(self, device_id: str) -> Dict[str, Any]:
        """Get current AC state"""
        return await self._request("GET", f"/devices/{device_id}/ac/status")

    async def get_measurements(self, device_id: str, limit: int = 50) -> list:
        """Get recent measurements"""
        return await self._request(
            "GET",
            f"/devices/{device_id}/measurements?limit={limit}"
        )

    async def get_stats(self, device_id: str) -> Dict[str, Any]:
        """Get device statistics"""
        return await self._request("GET", f"/devices/{device_id}/stats")

    async def get_schedules(self, device_id: str) -> list:
        """Get active schedules"""
        return await self._request("GET", f"/devices/{device_id}/schedules")

    async def create_schedule(self, device_id: str, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new schedule"""
        return await self._request(
            "POST",
            f"/devices/{device_id}/schedules",
            json=schedule_data
        )

    async def delete_schedule(self, device_id: str, schedule_id: int) -> Dict[str, Any]:
        """Delete schedule"""
        return await self._request(
            "DELETE",
            f"/devices/{device_id}/schedules/{schedule_id}"
        )

    async def create_sleep_timer(self, device_id: str, minutes: int) -> Dict[str, Any]:
        """Create sleep timer"""
        return await self._request(
            "POST",
            f"/devices/{device_id}/sleep-timers",
            json={"minutes": minutes, "action": "off"}
        )

    async def get_health(self) -> Dict[str, Any]:
        """Get system health"""
        return await self._request("GET", "/health")


# Initialize API client
api_client = BackendAPIClient(BACKEND_API_URL)


def require_auth(func):
    """Decorator to check if user is authorized"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if user_id != TELEGRAM_USER_ID:
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            await update.message.reply_text(
                "❌ No estás autorizado para usar este bot.\n"
                f"Tu User ID: {user_id}"
            )
            return

        return await func(update, context)

    return wrapper


@require_auth
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_name = update.effective_user.first_name

    # Create keyboard with Mini App button
    keyboard = [
        [KeyboardButton(
            text="🎛️ Abrir Panel de Control",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )],
        [KeyboardButton(text="📊 Estado Rápido")],
        [KeyboardButton(text="❄️ AC ON"), KeyboardButton(text="🔥 AC OFF")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"¡Hola {user_name}! 👋\n\n"
        f"Bienvenido al panel de control ESP-AC.\n\n"
        f"🎛️ **Panel Completo**: Usa el botón 'Abrir Panel de Control' para acceder a todas las funciones\n"
        f"⚡ **Controles Rápidos**: Usa los botones de abajo o comandos:\n\n"
        f"• /status - Ver temperatura y estado del AC\n"
        f"• /ac_on [temp] - Encender AC\n"
        f"• /ac_off - Apagar AC\n"
        f"• /ac_set <temp> [modo] [fan] - Control avanzado\n"
        f"• /timer <minutos> - Programar apagado automático\n"
        f"• /alerts - Configurar alertas de temperatura\n"
        f"• /health - Estado del sistema\n\n"
        f"Dispositivo configurado: `{DEFAULT_DEVICE_ID}`",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


@require_auth
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    try:
        await update.message.reply_text("⏳ Obteniendo datos...")

        status = await api_client.get_device_status(DEFAULT_DEVICE_ID)

        temp = status.get("temperature")
        humidity = status.get("humidity")
        ac_status = status.get("ac_status")
        timestamp = status.get("timestamp")

        # Temperature emoji based on value
        temp_emoji = "🥶" if temp < 20 else "🌡️" if temp < 26 else "🔥"
        ac_emoji = "❄️" if ac_status == "on" else "⚫"

        response = (
            f"📊 **Estado Actual**\n\n"
            f"{temp_emoji} **Temperatura**: {temp}°C\n"
            f"💧 **Humedad**: {humidity}%\n"
            f"{ac_emoji} **AC**: {ac_status.upper()}\n"
            f"🕐 **Última lectura**: {timestamp}\n\n"
            f"Dispositivo: `{DEFAULT_DEVICE_ID}`"
        )

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await update.message.reply_text(
            f"❌ Error al obtener el estado: {str(e)}"
        )


@require_auth
async def ac_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ac_on command - optionally with temperature"""
    try:
        # Get current state to preserve settings
        ac_state = await api_client.get_ac_state(DEFAULT_DEVICE_ID)
        temperature = ac_state.get('temperature', 24)
        mode = ac_state.get('mode', 'cool')
        fan_speed = ac_state.get('fan_speed', 'auto')

        # Parse optional temperature argument
        if context.args and len(context.args) >= 1:
            try:
                temperature = int(context.args[0])
                if temperature < 17 or temperature > 30:
                    await update.message.reply_text("❌ La temperatura debe estar entre 17 y 30°C")
                    return
            except ValueError:
                pass

        await update.message.reply_text(f"❄️ Encendiendo AC a {temperature}°C...")

        result = await api_client.send_ac_command(
            DEFAULT_DEVICE_ID, "on", temperature, mode, fan_speed
        )

        await update.message.reply_text(
            f"✅ AC encendido\n"
            f"🌡️ Temperatura: {result.get('temperature')}°C\n"
            f"📍 Modo: {result.get('mode')}\n"
            f"🌀 Ventilador: {result.get('fan_speed')}"
        )

    except Exception as e:
        logger.error(f"Error sending AC ON command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_auth
async def ac_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ac_off command"""
    try:
        # Get current state to preserve settings
        ac_state = await api_client.get_ac_state(DEFAULT_DEVICE_ID)
        temperature = ac_state.get('temperature', 24)
        mode = ac_state.get('mode', 'cool')
        fan_speed = ac_state.get('fan_speed', 'auto')

        await update.message.reply_text("🔥 Apagando AC...")

        result = await api_client.send_ac_command(
            DEFAULT_DEVICE_ID, "off", temperature, mode, fan_speed
        )

        await update.message.reply_text("✅ AC apagado")

    except Exception as e:
        logger.error(f"Error sending AC OFF command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_auth
async def ac_set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ac_set command for fine control"""
    if not context.args:
        await update.message.reply_text(
            "⚙️ **Control Avanzado del AC**\n\n"
            "Uso: /ac_set <temp> [modo] [ventilador]\n\n"
            "**Ejemplos:**\n"
            "• /ac_set 24 - Solo temperatura\n"
            "• /ac_set 22 cool auto - Completo\n\n"
            "**Modos:** cool, auto, fan, dry\n"
            "**Ventilador:** auto, low, medium, high",
            parse_mode="Markdown"
        )
        return

    try:
        # Get current state
        ac_state = await api_client.get_ac_state(DEFAULT_DEVICE_ID)
        temperature = ac_state.get('temperature', 24)
        mode = ac_state.get('mode', 'cool')
        fan_speed = ac_state.get('fan_speed', 'auto')

        # Parse arguments
        if len(context.args) >= 1:
            temperature = int(context.args[0])
            if temperature < 17 or temperature > 30:
                await update.message.reply_text("❌ Temperatura: 17-30°C")
                return

        if len(context.args) >= 2:
            mode = context.args[1].lower()
            if mode not in ['cool', 'auto', 'fan', 'dry']:
                await update.message.reply_text("❌ Modo inválido (cool, auto, fan, dry)")
                return

        if len(context.args) >= 3:
            fan_speed = context.args[2].lower()
            if fan_speed not in ['auto', 'low', 'medium', 'high']:
                await update.message.reply_text("❌ Ventilador inválido")
                return

        await update.message.reply_text(f"⚙️ Configurando AC...")

        result = await api_client.send_ac_command(
            DEFAULT_DEVICE_ID, "on", temperature, mode, fan_speed
        )

        mode_icons = {'cool': '❄️', 'heat': '🔥', 'auto': '🔄', 'fan': '🌀', 'dry': '💧'}
        mode_icon = mode_icons.get(result.get('mode'), '⚙️')

        await update.message.reply_text(
            f"✅ AC configurado\n\n"
            f"🌡️ **Temperatura**: {result.get('temperature')}°C\n"
            f"{mode_icon} **Modo**: {result.get('mode')}\n"
            f"🌀 **Ventilador**: {result.get('fan_speed')}",
            parse_mode="Markdown"
        )

    except ValueError:
        await update.message.reply_text("❌ Temperatura debe ser un número")
    except Exception as e:
        logger.error(f"Error setting AC: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_auth
async def timer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /timer <minutes> command"""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "⏱️ Uso: /timer <minutos>\n"
            "Ejemplo: /timer 30 (apagar AC en 30 minutos)"
        )
        return

    try:
        minutes = int(context.args[0])

        if minutes < 1 or minutes > 1440:
            await update.message.reply_text(
                "❌ El tiempo debe estar entre 1 y 1440 minutos (24 horas)"
            )
            return

        result = await api_client.create_sleep_timer(DEFAULT_DEVICE_ID, minutes)

        await update.message.reply_text(
            f"⏱️ Timer configurado\n\n"
            f"El AC se apagará en **{minutes} minutos**\n"
            f"Hora de ejecución: {result.get('execute_at')}"
        )

    except ValueError:
        await update.message.reply_text("❌ Por favor ingresa un número válido de minutos")
    except Exception as e:
        logger.error(f"Error creating timer: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_auth
async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alerts command - configure temperature alerts"""
    global alert_settings

    if not context.args:
        # Show current configuration
        status = "✅ Activadas" if alert_settings["enabled"] else "❌ Desactivadas"

        await update.message.reply_text(
            f"🔔 **Configuración de Alertas**\n\n"
            f"Estado: {status}\n"
            f"Umbral Alto: {alert_settings['threshold_high']}°C\n"
            f"Umbral Bajo: {alert_settings['threshold_low']}°C\n"
            f"Cooldown: {alert_settings['cooldown_minutes']} minutos\n\n"
            f"**Comandos:**\n"
            f"• /alerts on - Activar alertas\n"
            f"• /alerts off - Desactivar alertas\n"
            f"• /alerts set <bajo> <alto> - Configurar umbrales\n"
            f"  Ejemplo: /alerts set 18 30",
            parse_mode="Markdown"
        )
        return

    command = context.args[0].lower()

    if command == "on":
        alert_settings["enabled"] = True
        await update.message.reply_text("✅ Alertas activadas")

    elif command == "off":
        alert_settings["enabled"] = False
        await update.message.reply_text("❌ Alertas desactivadas")

    elif command == "set" and len(context.args) == 3:
        try:
            low = float(context.args[1])
            high = float(context.args[2])

            if low >= high:
                await update.message.reply_text("❌ El umbral bajo debe ser menor que el alto")
                return

            alert_settings["threshold_low"] = low
            alert_settings["threshold_high"] = high

            await update.message.reply_text(
                f"✅ Umbrales configurados:\n"
                f"Bajo: {low}°C\n"
                f"Alto: {high}°C"
            )
        except ValueError:
            await update.message.reply_text("❌ Por favor ingresa valores numéricos válidos")
    else:
        await update.message.reply_text(
            "❌ Comando no reconocido\n"
            "Usa /alerts para ver la ayuda"
        )


@require_auth
async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /health command"""
    try:
        health = await api_client.get_health()

        mqtt_status = "✅" if health.get("mqtt_connected") else "❌"
        scheduler_status = "✅" if health.get("scheduler_running") else "❌"

        await update.message.reply_text(
            f"🏥 **Estado del Sistema**\n\n"
            f"{mqtt_status} **MQTT**: {'Conectado' if health.get('mqtt_connected') else 'Desconectado'}\n"
            f"{scheduler_status} **Scheduler**: {'Ejecutando' if health.get('scheduler_running') else 'Detenido'}\n"
            f"⏰ **Timestamp**: {health.get('timestamp')}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error getting health: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_auth
async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle keyboard button presses"""
    text = update.message.text

    if text == "📊 Estado Rápido":
        await status_command(update, context)
    elif text == "❄️ AC ON":
        await ac_on_command(update, context)
    elif text == "🔥 AC OFF":
        await ac_off_command(update, context)


async def check_temperature_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Background task to check temperature and send alerts"""
    global alert_settings

    if not alert_settings["enabled"]:
        return

    # Check cooldown
    if alert_settings["last_alert_sent"]:
        last_alert = datetime.fromisoformat(alert_settings["last_alert_sent"])
        cooldown = timedelta(minutes=alert_settings["cooldown_minutes"])

        if datetime.now() - last_alert < cooldown:
            return  # Still in cooldown

    try:
        status = await api_client.get_device_status(DEFAULT_DEVICE_ID)
        temp = status.get("temperature")

        if temp is None:
            return

        message = None

        if temp >= alert_settings["threshold_high"]:
            message = (
                f"🔥 **ALERTA: Temperatura Alta**\n\n"
                f"Temperatura actual: {temp}°C\n"
                f"Umbral: {alert_settings['threshold_high']}°C\n\n"
                f"Considera encender el AC."
            )
        elif temp <= alert_settings["threshold_low"]:
            message = (
                f"🥶 **ALERTA: Temperatura Baja**\n\n"
                f"Temperatura actual: {temp}°C\n"
                f"Umbral: {alert_settings['threshold_low']}°C\n\n"
                f"Considera apagar el AC."
            )

        if message:
            await context.bot.send_message(
                chat_id=TELEGRAM_USER_ID,
                text=message,
                parse_mode="Markdown"
            )
            alert_settings["last_alert_sent"] = datetime.now().isoformat()
            logger.info(f"Alert sent: Temperature {temp}°C")

    except Exception as e:
        logger.error(f"Error in alert check: {e}")


async def post_init(application: Application):
    """Post initialization - schedule background tasks"""
    # Schedule alert checker
    application.job_queue.run_repeating(
        check_temperature_alerts,
        interval=ALERT_CHECK_INTERVAL,
        first=10,  # First run after 10 seconds
    )
    logger.info(f"Alert checker scheduled (interval: {ALERT_CHECK_INTERVAL}s)")


async def post_shutdown(application: Application):
    """Cleanup on shutdown"""
    await api_client.close()
    logger.info("Bot shutdown complete")


# ===== Web App Server for Mini App =====

async def serve_webapp(request):
    """Serve the Mini App HTML"""
    index_path = WEBAPP_DIR / "index.html"
    if not index_path.exists():
        raise web.HTTPNotFound(text="Mini App not found")
    return web.FileResponse(index_path)


async def serve_static(request):
    """Serve static files (CSS, JS)"""
    # Obtener el path completo de la request
    path = request.path

    # Extraer el nombre del archivo
    if path.startswith('/webapp/'):
        filename = path.replace('/webapp/', '')
    else:
        filename = path.lstrip('/')

    # Security: prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        raise web.HTTPForbidden()

    file_path = WEBAPP_DIR / filename

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise web.HTTPNotFound()

    # Set proper content type
    content_type = 'text/plain'
    if filename.endswith('.css'):
        content_type = 'text/css'
    elif filename.endswith('.js'):
        content_type = 'application/javascript'
    elif filename.endswith('.json'):
        content_type = 'application/json'
    elif filename.endswith('.png'):
        content_type = 'image/png'
    elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
        content_type = 'image/jpeg'

    logger.info(f"Serving static file: {filename} as {content_type}")
    return web.FileResponse(file_path, headers={'Content-Type': content_type})


async def proxy_device_measurements_latest(request):
    """Proxy: Get latest measurements"""
    device_id = request.match_info['device_id']
    try:
        data = await api_client._request("GET", f"/devices/{device_id}/measurements/latest")
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def proxy_device_ac_status(request):
    """Proxy: Get AC status"""
    device_id = request.match_info['device_id']
    try:
        data = await api_client._request("GET", f"/devices/{device_id}/ac/status")
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def proxy_device_ac_command(request):
    """Proxy: Send AC command"""
    device_id = request.match_info['device_id']
    try:
        body = await request.json()
        data = await api_client._request("POST", f"/devices/{device_id}/ac/command", json=body)
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def proxy_device_measurements(request):
    """Proxy: Get measurements history"""
    device_id = request.match_info['device_id']
    limit = request.query.get('limit', '50')
    try:
        data = await api_client._request("GET", f"/devices/{device_id}/measurements?limit={limit}")
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def proxy_device_stats(request):
    """Proxy: Get device statistics"""
    device_id = request.match_info['device_id']
    try:
        data = await api_client._request("GET", f"/devices/{device_id}/stats")
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def proxy_device_schedules(request):
    """Proxy: Get/Create schedules"""
    device_id = request.match_info['device_id']
    try:
        if request.method == 'GET':
            data = await api_client._request("GET", f"/devices/{device_id}/schedules")
        else:  # POST
            body = await request.json()
            data = await api_client._request("POST", f"/devices/{device_id}/schedules", json=body)
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def proxy_device_schedule_delete(request):
    """Proxy: Delete schedule"""
    device_id = request.match_info['device_id']
    schedule_id = request.match_info['schedule_id']
    try:
        data = await api_client._request("DELETE", f"/devices/{device_id}/schedules/{schedule_id}")
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def proxy_device_timer(request):
    """Proxy: Create sleep timer"""
    device_id = request.match_info['device_id']
    try:
        body = await request.json()
        data = await api_client._request("POST", f"/devices/{device_id}/sleep-timers", json=body)
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_alerts_config(request):
    """Handle alerts configuration"""
    global alert_settings

    if request.method == 'GET':
        return web.json_response(alert_settings)
    else:  # POST
        try:
            body = await request.json()
            alert_settings.update(body)
            return web.json_response({"status": "ok", "settings": alert_settings})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)


async def webapp_health(request):
    """Health check for web app server"""
    return web.json_response({"status": "ok", "service": "telegram-bot-webapp"})


@web.middleware
async def cors_middleware(request, handler):
    """CORS middleware"""
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex

    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Telegram-Init-Data'
    response.headers['Access-Control-Max-Age'] = '3600'

    return response


def create_webapp():
    """Create web application for Mini App"""
    app = web.Application(middlewares=[cors_middleware])

    # Serve Mini App
    app.router.add_get('/webapp', serve_webapp)
    app.router.add_get('/webapp/', serve_webapp)

    # Serve static files - FIX: La ruta correcta sin /webapp/
    app.router.add_get('/style.css', serve_static)
    app.router.add_get('/app.js', serve_static)

    # También servir desde /webapp/ por si acaso
    app.router.add_get('/webapp/style.css', serve_static)
    app.router.add_get('/webapp/app.js', serve_static)

    # API proxy endpoints
    app.router.add_get('/api/device/{device_id}/measurements/latest', proxy_device_measurements_latest)
    app.router.add_get('/api/device/{device_id}/ac/status', proxy_device_ac_status)
    app.router.add_post('/api/device/{device_id}/ac/command', proxy_device_ac_command)
    app.router.add_get('/api/device/{device_id}/measurements', proxy_device_measurements)
    app.router.add_get('/api/device/{device_id}/stats', proxy_device_stats)
    app.router.add_get('/api/device/{device_id}/schedules', proxy_device_schedules)
    app.router.add_post('/api/device/{device_id}/schedules', proxy_device_schedules)
    app.router.add_delete('/api/device/{device_id}/schedules/{schedule_id}', proxy_device_schedule_delete)
    app.router.add_post('/api/device/{device_id}/timer', proxy_device_timer)
    app.router.add_post('/api/device/{device_id}/sleep-timers', proxy_device_timer)

    # Alerts configuration
    app.router.add_route('*', '/api/alerts/config', handle_alerts_config)

    # Health check
    app.router.add_get('/health', webapp_health)

    return app


async def run_webapp_server():
    """Run the web app server"""
    app = create_webapp()
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', WEBAPP_PORT)
    await site.start()

    logger.info(f"Mini App server started on http://0.0.0.0:{WEBAPP_PORT}")
    logger.info(f"Mini App URL: http://0.0.0.0:{WEBAPP_PORT}/webapp")


def main():
    """Start the bot"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

    if TELEGRAM_USER_ID == 0:
        raise ValueError("TELEGRAM_USER_ID not set in environment")

    logger.info(f"Starting ESP-AC Telegram Bot")
    logger.info(f"Authorized User ID: {TELEGRAM_USER_ID}")
    logger.info(f"Backend API: {BACKEND_API_URL}")
    logger.info(f"Default Device: {DEFAULT_DEVICE_ID}")

    # Create application
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("ac_on", ac_on_command))
    application.add_handler(CommandHandler("ac_off", ac_off_command))
    application.add_handler(CommandHandler("ac_set", ac_set_command))
    application.add_handler(CommandHandler("timer", timer_command))
    application.add_handler(CommandHandler("alerts", alerts_command))
    application.add_handler(CommandHandler("health", health_command))

    # Register message handler for keyboard buttons
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_button_press
    ))

    # Start the web app server in background
    logger.info("Starting Mini App web server...")
    asyncio.get_event_loop().create_task(run_webapp_server())

    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
