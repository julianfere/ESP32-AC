import paho.mqtt.client as mqtt
import json
import asyncio
import os
from typing import Callable, Dict, Any
from datetime import datetime
from utils import now_argentina

class MQTTClient:
    """Cliente MQTT para comunicación con dispositivos ESP32"""

    def __init__(self, broker_host: str, broker_port: int = 1883,
                 username: str = None, password: str = None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password

        # Estado de conexión
        self.connected = False
        self.client = None

        # Callbacks para diferentes topics
        self.callbacks: Dict[str, Callable] = {}

    def connect(self):
        """Conectar al broker MQTT"""
        try:
            self.client = mqtt.Client()

            # Configurar autenticación si está disponible
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            # Configurar callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            # Conectar
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()

            print(f"🔄 Conectando a MQTT broker: {self.broker_host}:{self.broker_port}")
            return True

        except Exception as e:
            print(f"✗ Error conectando a MQTT: {e}")
            return False

    def disconnect(self):
        """Desconectar del broker MQTT"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        """Callback cuando se conecta al broker"""
        if rc == 0:
            self.connected = True
            print("✓ Conectado al broker MQTT")

            # Suscribirse a todos los topics registrados
            for topic_pattern in self.callbacks.keys():
                client.subscribe(topic_pattern)
                print(f"📡 Suscrito a: {topic_pattern}")
        else:
            print(f"✗ Error conectando a MQTT (código {rc})")

    def _on_disconnect(self, client, userdata, rc):
        """Callback cuando se desconecta del broker"""
        self.connected = False
        print("🔌 Desconectado del broker MQTT")

    def _on_message(self, client, userdata, msg):
        """Callback cuando llega un mensaje"""
        try:
            topic = msg.topic
            payload_str = msg.payload.decode('utf-8')

            print(f"📨 Mensaje MQTT recibido: topic={topic}, payload={payload_str}")

            # Intentar parsear JSON
            try:
                payload = json.loads(payload_str)
            except:
                payload = payload_str

            # Extraer device_id del topic (formato: device_id/...)
            topic_parts = topic.split('/')
            if len(topic_parts) >= 2:
                device_id = topic_parts[0]

                print(f"🆔 Device ID extraído: {device_id}")

                # Crear mensaje estructurado
                message = {
                    'device_id': device_id,
                    'topic': topic,
                    'payload': payload,
                    'timestamp': now_argentina()
                }

                print(f"📦 Mensaje estructurado: {message}")

                # Buscar callback apropiado
                callback_found = False
                for pattern, callback in self.callbacks.items():
                    print(f"🔍 Comparando topic '{topic}' con patrón '{pattern}'")
                    if self._topic_matches(topic, pattern):
                        print(f"✅ Match encontrado! Ejecutando callback para patrón: {pattern}")
                        callback_found = True

                        # Ejecutar callback
                        if asyncio.iscoroutinefunction(callback):
                            print(f"🔄 Ejecutando callback asíncrono...")
                            # Siempre usar hilo separado para callbacks asíncronos
                            import threading
                            def run_async():
                                try:
                                    asyncio.run(callback(message))
                                    print(f"✅ Callback asíncrono completado exitosamente")
                                except Exception as e:
                                    print(f"✗ Error en callback asíncrono: {e}")
                                    import traceback
                                    traceback.print_exc()

                            thread = threading.Thread(target=run_async, daemon=True)
                            thread.start()
                            print(f"🚀 Callback asíncrono iniciado en hilo separado")
                        else:
                            print(f"🔄 Ejecutando callback síncrono...")
                            try:
                                callback(message)
                                print(f"✅ Callback síncrono completado")
                            except Exception as e:
                                print(f"✗ Error en callback síncrono: {e}")
                                import traceback
                                traceback.print_exc()
                        break

                if not callback_found:
                    print(f"⚠️ No se encontró callback para topic: {topic}")

        except Exception as e:
            print(f"✗ Error procesando mensaje MQTT: {e}")

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Verificar si un topic coincide con un patrón"""
        # Convertir patrón MQTT a regex simple
        # + = cualquier cosa excepto /
        # # = cualquier cosa
        pattern = pattern.replace('+', '[^/]+').replace('#', '.*')

        import re
        return bool(re.match(f"^{pattern}$", topic))

    def register_callback(self, topic_pattern: str, callback: Callable):
        """Registrar callback para un patrón de topic"""
        self.callbacks[topic_pattern] = callback

        # Si ya estamos conectados, suscribirse inmediatamente
        if self.connected and self.client:
            self.client.subscribe(topic_pattern)
            print(f"📡 Suscrito a: {topic_pattern}")

    def publish(self, topic: str, payload: Any, qos: int = 0) -> bool:
        """Publicar mensaje en un topic"""
        if not self.connected or not self.client:
            print("✗ No conectado al broker MQTT")
            return False

        try:
            # Convertir payload a JSON si es necesario
            if isinstance(payload, (dict, list)):
                payload_str = json.dumps(payload)
            else:
                payload_str = str(payload)

            result = self.client.publish(topic, payload_str, qos)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"📤 Enviado: {topic} -> {payload_str[:50]}...")
                return True
            else:
                print(f"✗ Error enviando mensaje: {result.rc}")
                return False

        except Exception as e:
            print(f"✗ Error publicando mensaje: {e}")
            return False

    # Métodos de conveniencia para comandos específicos
    def send_ac_command(self, device_id: str, action: str) -> bool:
        """Enviar comando de aire acondicionado"""
        topic = f"{device_id}/ac/command"
        payload = {
            "action": action,
            "timestamp": int(now_argentina().timestamp())
        }
        return self.publish(topic, payload)

    def send_led_command(self, device_id: str, r: int, g: int, b: int, enabled: bool) -> bool:
        """Enviar comando de LED"""
        topic = f"{device_id}/led/command"
        payload = {
            "r": r,
            "g": g,
            "b": b,
            "enabled": enabled,
            "timestamp": int(now_argentina().timestamp())
        }
        return self.publish(topic, payload)

    def send_config_update(self, device_id: str, sample_interval: int, avg_samples: int) -> bool:
        """Enviar actualización de configuración"""
        topic = f"{device_id}/config/update"
        payload = {
            "sample_interval": sample_interval,
            "avg_samples": avg_samples,
            "timestamp": int(now_argentina().timestamp())
        }
        return self.publish(topic, payload)

    def send_reboot_command(self, device_id: str) -> bool:
        """Enviar comando de reinicio"""
        topic = f"{device_id}/system/command"
        payload = {
            "action": "reboot",
            "timestamp": int(now_argentina().timestamp())
        }
        return self.publish(topic, payload)


# Instancia global del cliente MQTT
_mqtt_client = None

def init_mqtt_client() -> MQTTClient:
    """Inicializar cliente MQTT global"""
    global _mqtt_client

    if _mqtt_client is None:
        # Obtener configuración desde variables de entorno
        broker_host = os.getenv("MQTT_BROKER_HOST", "localhost")
        broker_port = int(os.getenv("MQTT_BROKER_PORT", 1883))
        username = os.getenv("MQTT_USERNAME")
        password = os.getenv("MQTT_PASSWORD")

        _mqtt_client = MQTTClient(
            broker_host=broker_host,
            broker_port=broker_port,
            username=username,
            password=password
        )

        # Cliente MQTT configurado

    return _mqtt_client

def get_mqtt_client() -> MQTTClient:
    """Obtener instancia del cliente MQTT"""
    global _mqtt_client
    if _mqtt_client is None:
        _mqtt_client = init_mqtt_client()
    return _mqtt_client


# Importar register_handlers desde message_handlers.py
from message_handlers import register_handlers