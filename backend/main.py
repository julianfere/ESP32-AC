import asyncio
import uvicorn
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

from database import init_db
from mqtt_client import init_mqtt_client
from message_handlers import register_handlers
from api import app

async def startup():
    """Inicializar aplicación"""
      # Inicializar base de datos
    print("Inicializando base de datos...")
    await init_db()
    print()
    
    # Inicializar cliente MQTT
    print("Inicializando cliente MQTT...")
    mqtt_client = init_mqtt_client()
    
    # Registrar handlers de mensajes
    register_handlers(mqtt_client)
    
    # Conectar a broker MQTT
    mqtt_client.connect()
    print()
    
    print("Backend iniciado correctamente\n")
    print("📡 API disponible en: http://localhost:8000")

if __name__ == "__main__":
    # Ejecutar startup
    asyncio.run(startup())
    
    # Iniciar servidor FastAPI
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )